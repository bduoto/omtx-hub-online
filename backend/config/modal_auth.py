"""
Handles Modal authentication for the entire application.
"""
import os
import toml
import logging

logger = logging.getLogger(__name__)

def authenticate_modal():
    """
    Loads Modal credentials from the user's config file and sets them
    as environment variables for the application. This ensures that any
    part of the application that uses the Modal client is authenticated.
    
    This function will prioritize credentials from the .toml file over
    any existing environment variables to ensure a consistent configuration.
    """
    modal_config_path = os.path.expanduser("~/.modal.toml")
    logger.info("Attempting to load Modal credentials for the application...")

    if os.path.exists(modal_config_path):
        try:
            logger.info(f"Reading credentials from {modal_config_path}")
            config = toml.load(modal_config_path)
            
            active_profile_name = next((p for p, d in config.items() if d.get('active')), "default")
            profile = config.get(active_profile_name, {})
            
            modal_token_id = profile.get('token_id')
            modal_token_secret = profile.get('token_secret')

            if modal_token_id and modal_token_secret:
                os.environ['MODAL_TOKEN_ID'] = modal_token_id
                os.environ['MODAL_TOKEN_SECRET'] = modal_token_secret
                logger.info(f"✅ Successfully loaded and set Modal credentials from profile '{active_profile_name}'.")
            else:
                logger.warning(f"Could not find 'token_id' or 'token_secret' in active profile '{active_profile_name}' in {modal_config_path}.")

        except Exception as e:
            logger.error(f"Failed to read or parse Modal config at {modal_config_path}: {e}")
    else:
        logger.warning(f"Modal config file not found at {modal_config_path}. Using environment variables if available.") 