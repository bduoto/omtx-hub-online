"""
Modal Models Configuration Loader
Loads configuration from modal_models.yaml for production services
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_modal_config() -> Dict[str, Any]:
    """Load Modal models configuration from YAML file"""
    config_path = Path(__file__).parent / "modal_models.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded Modal models configuration from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Modal models config not found at {config_path}")
        raise Exception(f"Modal models configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse Modal models config: {e}")
        raise Exception(f"Invalid YAML in Modal models configuration: {e}")
