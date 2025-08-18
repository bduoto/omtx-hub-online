"""
Service to run Modal predictions in a subprocess to avoid auth conflicts.
"""

import os
import json
import asyncio
import tempfile
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

async def run_modal_prediction_subprocess(
    protein_sequences: List[str],
    ligands: List[str],
    use_msa_server: bool = True,
    use_potentials: bool = False
) -> Dict[str, Any]:
    """Run Boltz-2 Modal prediction in a subprocess to avoid FastAPI auth conflicts"""
    
    modal_config_path = os.path.expanduser("~/.modal.toml")
    modal_token_id = os.environ.get("MODAL_TOKEN_ID")
    modal_token_secret = os.environ.get("MODAL_TOKEN_SECRET")
    
    # Add robust credential loading with detailed logging
    logger.info("Attempting to load Modal credentials for subprocess...")
    if not (modal_token_id and modal_token_secret):
        logger.info("MODAL_TOKEN_ID or MODAL_TOKEN_SECRET not found in environment.")
        if os.path.exists(modal_config_path):
            try:
                logger.info(f"Reading credentials from {modal_config_path}")
                import toml
                with open(modal_config_path, 'r') as f:
                    config = toml.load(f)
                    # Find the active profile to get the correct tokens
                    active_profile_name = next((p for p, d in config.items() if d.get('active')), "default")
                    profile = config.get(active_profile_name, {})
                    
                    modal_token_id = profile.get('token_id')
                    modal_token_secret = profile.get('token_secret')

                    if modal_token_id and modal_token_secret:
                        logger.info(f"Successfully loaded credentials for profile '{active_profile_name}'.")
                    else:
                        logger.warning(f"Could not find 'token_id' or 'token_secret' in active profile '{active_profile_name}'.")

            except Exception as e:
                logger.error(f"Failed to read or parse Modal config at {modal_config_path}: {e}")
        else:
            logger.warning(f"Modal config file not found at {modal_config_path}")
    else:
        logger.info("Found Modal credentials in environment variables.")

    # Create temporary file for the prediction script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        
        # Securely construct the authentication part of the script
        auth_script = ""
        if modal_token_id and modal_token_secret:
            logger.info("Injecting loaded credentials into subprocess script.")
            auth_script = f"""
        os.environ['MODAL_TOKEN_ID'] = "{modal_token_id}"
        os.environ['MODAL_TOKEN_SECRET'] = "{modal_token_secret}"
"""
        else:
            logger.warning("No Modal credentials found to inject into subprocess.")

        prediction_script = f"""
import json
import sys
import os

def run_prediction():
    try:
        # Set Modal environment variables explicitly if found
        {auth_script}
        
        # --- START OF FINAL DEBUGGING ---
        print("--- Subprocess Debug ---")
        print(f"Attempting to authenticate with MODAL_TOKEN_ID set: {bool(os.environ.get('MODAL_TOKEN_ID'))}")
        # --- END OF FINAL DEBUGGING ---

        # IMPORTANT: Import modal *after* setting credentials
        import modal
        
        # Load Modal function 
        boltz2_predict_modal = modal.Function.from_name(
            "omtx-hub-boltz2-persistent", 
            "boltz2_predict_modal"
        )
        
        result = boltz2_predict_modal.remote(
            protein_sequences={protein_sequences},
            ligands={ligands},
            use_msa_server={use_msa_server},
            use_potentials={use_potentials}
        )
        
        print(json.dumps(result, default=str))
        
    except Exception as e:
        print(json.dumps({{"error": str(e)}}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_prediction()
"""
        f.write(prediction_script)
        script_path = f.name
    
    try:
        env = os.environ.copy()
        if modal_token_id and modal_token_secret:
            env['MODAL_TOKEN_ID'] = modal_token_id
            env['MODAL_TOKEN_SECRET'] = modal_token_secret
        
        process = await asyncio.create_subprocess_exec(
            'python3', script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        # --- START OF FINAL FIX ---
        # Decode and log the output from the subprocess for debugging
        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()

        if stdout_str:
            logger.info(f"Subprocess STDOUT: {stdout_str}")
        if stderr_str:
            logger.error(f"Subprocess STDERR: {stderr_str}")
        # --- END OF FINAL FIX ---

        if process.returncode == 0:
            return json.loads(stdout.decode())
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"Modal prediction failed: {error_msg}")
            
    finally:
        os.unlink(script_path) 