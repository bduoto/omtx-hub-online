import os
import time
import asyncio
from typing import List, Dict, Any, Optional
import logging

# Modal imports
import modal
from modal import Image, Volume, Secret, gpu, method, enter

# Enable Modal output for debugging
modal.enable_output()

# Import base class
# from models.model_registry import BaseModelHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modal app configuration - persistent app that keeps prediction history
APP_NAME = "omtx-hub-boltz2-persistent"
app = modal.App(APP_NAME)

# Create volume for model weights following official Modal example
boltz2_volume = Volume.from_name("boltz-models", create_if_missing=True)
MODEL_DIR = "/models/boltz"

# Define the container image with Boltz-2 dependencies
boltz2_image = (
    modal.Image.debian_slim(python_version="3.12")
    .run_commands(
        "uv pip install --system --compile-bytecode boltz==2.1.1"
    )
)

# Import libraries within the image
with boltz2_image.imports():
    import torch
    import numpy as np
    from typing import List, Dict, Any
    import logging
    import sys
    import yaml
    import tempfile
    import os
    import subprocess
    import json
    from pathlib import Path
    # Import Boltz-2
    import boltz

# class Boltz2Model(BaseModelHandler):
#     """Boltz-2 model handler for biomolecular interaction prediction
#     
#     Boltz-2 is a new biomolecular foundation model that goes beyond AlphaFold3 
#     and Boltz-1 by jointly modeling complex structures and binding affinities. 
#     It's the first deep learning model to approach the accuracy of physics-based 
#     free-energy perturbation (FEP) methods, while running 1000x faster.
#     
#     Key features:
#     - Binding affinity prediction (affinity_pred_value and affinity_probability_binary)
#     - Structure prediction
#     - Support for MSA server integration
#     - MIT licensed for academic and commercial use
#     """
#     
#     def __init__(self):
#         self.model = None
#         self.is_initialized = False
#     
#     @property
#     def model_name(self) -> str:
#         return "Boltz-2"
#     
#     @property
#     def model_version(self) -> str:
#         return "1.0.0"
#     
#     @property
#     def model_category(self) -> str:
#         return "Structure Prediction"
#     
#     @property
#     def supported_inputs(self) -> List[str]:
#         return ["protein_sequences", "ligands", "use_msa_server", "use_potentials"]
#     
#     async def predict(
#         self,
#         protein_sequences: List[str],
#         ligands: List[str],
#         use_msa_server: bool = True,
#         use_potentials: bool = False
#     ) -> Dict[str, Any]:
#         """
#         Run Boltz-2 prediction using Modal
#         
#         Args:
#             protein_sequences: List of protein sequences
#             ligands: List of ligand SMILES or names
#             use_msa_server: Whether to use MSA server
#             use_potentials: Whether to use potential energy calculations
#             
#         Returns:
#             Dictionary containing prediction results
#         """
#         try:
#             logger.info(f"Starting Boltz-2 prediction for {len(protein_sequences)} sequences and {len(ligands)} ligands")
#             
#             # Call the Modal function for real prediction
#             with app.run():
#                 result = boltz2_predict_modal.remote(
#                     protein_sequences=protein_sequences,
#                     ligands=ligands,
#                     use_msa_server=use_msa_server,
#                     use_potentials=use_potentials
#                 )
#             
#             logger.info(f"Boltz-2 prediction completed successfully")
#             return result
#             
#         except Exception as e:
#             logger.error(f"Error in Boltz-2 prediction: {str(e)}")
#             raise

# Modal function for Boltz-2 predictions following official example
@app.function(
    gpu="A100-40GB",
    image=boltz2_image,
    volumes={MODEL_DIR: boltz2_volume},
    timeout=30 * 60  # 30 minutes timeout since Boltz-2 predictions take around 20 minutes
)
def boltz2_predict_modal(
    protein_sequences: List[str],
    ligands: List[str],
    use_msa_server: bool = True,
    use_potentials: bool = False
) -> Dict[str, Any]:
    """
    Modal function for Boltz-2 predictions using real model.
    Returns both output parameter values and structure file content.
    """
    # Force rebuild timestamp: 2025-07-09 20:10:00
    try:
        import time
        import random
        import yaml
        import shlex
        import subprocess
        import base64
        from pathlib import Path
        
        # Sequential job tracking for persistent Modal app
        start_time = time.time()
        execution_timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        
        logger.info("Starting new Boltz-2 prediction job")
        logger.info(f"Starting real Boltz-2 Modal prediction...")
        logger.info(f"Execution timestamp: {execution_timestamp}")
        logger.info(f"Protein sequences: {len(protein_sequences)}")
        logger.info(f"Ligands: {len(ligands)}")
        logger.info(f"Use MSA server: {use_msa_server}")
        logger.info(f"Use potentials: {use_potentials}")
        
        # Generate truly unique ID for this prediction job
        unique_id = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        logger.info(f"Job ID: {unique_id}")
        
        # Generate input YAML following official Boltz-2 schema
        input_yaml = {
            "version": 1,
            "sequences": []
        }
        
        # Add protein sequences
        for i, seq in enumerate(protein_sequences):
            input_yaml["sequences"].append({
                "protein": {
                    "id": chr(65 + i),  # A, B, C, etc.
                    "sequence": seq
                }
            })
        
        # Add ligand sequences
        ligand_start_idx = len(protein_sequences)
        for i, ligand in enumerate(ligands):
            input_yaml["sequences"].append({
                "ligand": {
                    "id": chr(65 + ligand_start_idx + i),  # Continue from protein chains
                    "smiles": ligand
                }
            })
        
        # Add affinity prediction if we have both proteins and ligands
        if protein_sequences and ligands:
            input_yaml["properties"] = [{
                "affinity": {
                    "binder": chr(65 + ligand_start_idx)  # First ligand chain
                }
            }]
        
        # Create input file
        input_file = f"/tmp/input_{unique_id}.yaml"
        with open(input_file, "w") as f:
            yaml.dump(input_yaml, f)
        
        logger.info(f"Created input file: {input_file}")
        logger.info(f"Input YAML content: {yaml.dump(input_yaml, default_flow_style=False)}")
        
        # Set up output directory following official Boltz-2 CLI behavior
        base_output_dir = f"/tmp/boltz_output_{unique_id}"
        os.makedirs(base_output_dir, exist_ok=True)
        
        # Build Boltz-2 command following official CLI exactly
        cmd_parts = [
            "boltz", "predict", input_file,
            "--out_dir", base_output_dir,
            "--model", "boltz2",
            "--diffusion_samples", "1",  # Default is 1, not 5
            "--recycling_steps", "3",
            "--sampling_steps", "200"
        ]
        
        # Add optional flags based on parameters
        if use_msa_server:
            cmd_parts.append("--use_msa_server")
        if use_potentials:
            cmd_parts.append("--use_potentials")
        
        cmd = " ".join(cmd_parts)
        logger.info(f"Executing Boltz-2 command: {cmd}")
        
        # Execute Boltz-2 prediction
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        logger.info(f"Boltz-2 command completed with return code: {result.returncode}")
        logger.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR: {result.stderr}")
        
        # Following official Boltz-2 CLI output structure:
        # {base_output_dir}/boltz_results_{input_stem}/predictions/{record_id}/
        input_stem = Path(input_file).stem
        record_id = input_stem  # Record ID is the input filename stem
        
        # Official CLI creates boltz_results_{input_stem} subdirectory
        boltz_results_dir = Path(base_output_dir) / f"boltz_results_{input_stem}"
        predictions_dir = boltz_results_dir / "predictions" / record_id
        
        logger.info(f"Looking for predictions in: {predictions_dir}")
        
        # Enhanced file discovery based on official Boltz-2 CLI structure
        structure_files = []
        confidence_files = []
        affinity_files = []
        
        if predictions_dir.exists():
            # Official naming pattern: {record_id}_model_{rank}.cif
            structure_files = sorted(predictions_dir.glob(f"{record_id}_model_*.cif"))
            confidence_files = sorted(predictions_dir.glob(f"confidence_{record_id}_model_*.json"))
            affinity_files = list(predictions_dir.glob(f"affinity_{record_id}.json"))
            
            logger.info(f"Found {len(structure_files)} structure files")
            logger.info(f"Found {len(confidence_files)} confidence files")
            logger.info(f"Found {len(affinity_files)} affinity files")
        
        # Check alternative locations as fallback
        alternative_locations = [
            boltz_results_dir / "predictions",
            boltz_results_dir,
            base_output_dir,
            "/tmp/boltz_outputs",
            "/tmp/outputs"
        ]
        
        if not structure_files:
            logger.warning("No files found in expected location, checking alternatives...")
            for alt_dir in alternative_locations:
                alt_path = Path(alt_dir)
                if alt_path.exists():
                    # Look for both .cif and .pdb files as fallback
                    alt_structures = list(alt_path.glob("*.cif")) + list(alt_path.glob("*.pdb"))
                    if alt_structures:
                        structure_files.extend(alt_structures)
                        logger.info(f"Found additional structures in {alt_dir}: {[f.name for f in alt_structures]}")
                        break
        
        if not structure_files:
            # List all files for debugging
            logger.error("No structure files found. Directory structure:")
            for root, dirs, files in os.walk(base_output_dir):
                logger.error(f"  {root}/")
                for file in files:
                    logger.error(f"    {file}")
            
            raise ValueError(f"No structure files generated by Boltz-2. Command output: {result.stdout}")
        
        # Process primary structure file (model_0 = highest confidence)
        primary_structure = structure_files[0]
        logger.info(f"Primary structure file: {primary_structure}")
        
        # Read structure content
        with open(primary_structure, "r") as f:
            structure_content = f.read()
        
        # Encode as base64
        structure_file_base64 = base64.b64encode(structure_content.encode()).decode()
        
        # Parse confidence scores following official JSON structure
        confidence_score = 0.0
        ptm_score = 0.0
        iptm_score = 0.0
        plddt_score = 0.0
        ligand_iptm_score = 0.0
        protein_iptm_score = 0.0
        complex_iplddt_score = 0.0
        complex_pde_score = 0.0
        complex_ipde_score = 0.0
        chains_ptm = {}
        pair_chains_iptm = {}
        
        if confidence_files:
            try:
                with open(confidence_files[0], "r") as f:
                    confidence_data = json.load(f)
                    confidence_score = confidence_data.get("confidence_score", 0.0)
                    ptm_score = confidence_data.get("ptm", 0.0)
                    iptm_score = confidence_data.get("iptm", 0.0)
                    plddt_score = confidence_data.get("complex_plddt", 0.0)
                    ligand_iptm_score = confidence_data.get("ligand_iptm", 0.0)
                    protein_iptm_score = confidence_data.get("protein_iptm", 0.0)
                    complex_iplddt_score = confidence_data.get("complex_iplddt", 0.0)
                    complex_pde_score = confidence_data.get("complex_pde", 0.0)
                    complex_ipde_score = confidence_data.get("complex_ipde", 0.0)
                    chains_ptm = confidence_data.get("chains_ptm", {})
                    pair_chains_iptm = confidence_data.get("pair_chains_iptm", {})
                    
                logger.info(f"Confidence scores - Overall: {confidence_score:.4f}, PTM: {ptm_score:.4f}, pLDDT: {plddt_score:.4f}")
            except Exception as e:
                logger.warning(f"Error parsing confidence file: {e}")
        
        # Parse affinity scores following official JSON structure
        affinity_value = None
        affinity_probability = None
        affinity_value1 = None
        affinity_probability1 = None
        affinity_value2 = None
        affinity_probability2 = None
        
        if affinity_files:
            try:
                with open(affinity_files[0], "r") as f:
                    affinity_data = json.load(f)
                    affinity_value = affinity_data.get("affinity_pred_value")
                    affinity_probability = affinity_data.get("affinity_probability_binary")
                    affinity_value1 = affinity_data.get("affinity_pred_value1")
                    affinity_probability1 = affinity_data.get("affinity_probability_binary1")
                    affinity_value2 = affinity_data.get("affinity_pred_value2")
                    affinity_probability2 = affinity_data.get("affinity_probability_binary2")
                    
                logger.info(f"Affinity scores - Value: {affinity_value}, Probability: {affinity_probability}")
            except Exception as e:
                logger.warning(f"Error parsing affinity file: {e}")
        
        # Process all structure files (ranked by confidence)
        all_structures = []
        for i, struct_file in enumerate(structure_files):
            try:
                with open(struct_file, "r") as f:
                    content = f.read()
                
                # Get corresponding confidence (models are already ranked)
                model_confidence = 0.0
                if i < len(confidence_files):
                    try:
                        with open(confidence_files[i], "r") as f:
                            conf_data = json.load(f)
                            model_confidence = conf_data.get("confidence_score", 0.0)
                    except:
                        pass
                
                all_structures.append({
                    "model_id": i,
                    "file_path": str(struct_file),
                    "confidence": model_confidence,
                    "content": content,
                    "base64": base64.b64encode(content.encode()).decode(),
                    "rank": i  # model_0 = highest confidence
                })
                
            except Exception as e:
                logger.warning(f"Error processing structure {struct_file}: {e}")
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        logger.info(f"Boltz-2 prediction completed successfully!")
        logger.info(f"Total execution time: {execution_time:.2f} seconds")
        logger.info(f"Generated {len(all_structures)} structure models")
        logger.info(f"Confidence score: {confidence_score:.4f}")
        if affinity_value is not None:
            logger.info(f"Affinity value: {affinity_value:.4f}")
        
        return {
            "job_id": unique_id,
            "status": "completed",
            "affinity": affinity_value,
            "affinity_probability": affinity_probability,
            "affinity_ensemble": {
                "affinity_pred_value": affinity_value,
                "affinity_probability_binary": affinity_probability,
                "affinity_pred_value1": affinity_value1,
                "affinity_probability_binary1": affinity_probability1,
                "affinity_pred_value2": affinity_value2,
                "affinity_probability_binary2": affinity_probability2
            },
            "confidence": confidence_score,
            "confidence_metrics": {
                "confidence_score": confidence_score,
                "ptm": ptm_score,
                "iptm": iptm_score,
                "ligand_iptm": ligand_iptm_score,
                "protein_iptm": protein_iptm_score,
                "complex_plddt": plddt_score,
                "complex_iplddt": complex_iplddt_score,
                "complex_pde": complex_pde_score,
                "complex_ipde": complex_ipde_score,
                "chains_ptm": chains_ptm,
                "pair_chains_iptm": pair_chains_iptm
            },
            "ptm_score": ptm_score,
            "iptm_score": iptm_score,
            "plddt_score": plddt_score,
            "ligand_iptm_score": ligand_iptm_score,
            "protein_iptm_score": protein_iptm_score,
            "structure_file": str(primary_structure),
            "structure_file_content": structure_content,
            "structure_file_base64": structure_file_base64,
            "structure_files": {
                "primary_structure": {
                    "path": str(primary_structure),
                    "content": structure_content,
                    "base64": structure_file_base64,
                    "filename": primary_structure.name,
                    "type": primary_structure.suffix.lstrip('.')
                }
            },
            "all_structures": all_structures,  # Ranked by confidence (model_0 = best)
            "structure_count": len(all_structures),
            "prediction_id": f"boltz2_{unique_id}",
            "protein_sequences": protein_sequences,
            "ligands": ligands,
            "parameters": {
                "use_msa_server": use_msa_server,
                "use_potentials": use_potentials,
                "gpu_used": "A100-40GB",
                "model": "boltz2",
                "diffusion_samples": 1,
                "recycling_steps": 3,
                "sampling_steps": 200
            },
            "execution_time": execution_time,
            "execution_timestamp": execution_timestamp,
            "boltz_output": result.stdout,
            "boltz_error": result.stderr,
            "output_directory": str(boltz_results_dir),
            "input_file": input_file,
            "input_yaml": input_yaml,
            "record_id": record_id
        }
    except Exception as e:
        logger.error(f"Error in Boltz-2 Modal prediction: {str(e)}")
        raise

# FastAPI endpoint for Boltz-2 predictions
@app.function()
async def boltz2_predict_endpoint(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    FastAPI endpoint for Boltz-2 predictions
    """
    try:
        # Extract parameters from request
        protein_sequences = request_data.get("protein_sequences", [])
        ligands = request_data.get("ligands", [])
        use_msa_server = request_data.get("use_msa_server", True)
        use_potentials = request_data.get("use_potentials", False)
        
        # Call the Modal prediction function
        result = boltz2_predict_modal.remote(
            protein_sequences=protein_sequences,
            ligands=ligands,
            use_msa_server=use_msa_server,
            use_potentials=use_potentials
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in Boltz-2 endpoint: {str(e)}")
        return {"error": str(e)} 