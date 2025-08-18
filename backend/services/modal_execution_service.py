"""
Modal Execution Service
Central orchestrator for all Modal predictions with clean interfaces
"""

import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from services.modal_subprocess_runner import modal_subprocess_runner
from services.modal_prediction_adapters import Boltz2Adapter, RFAntibodyAdapter, Chai1Adapter

logger = logging.getLogger(__name__)

class ModalExecutionService:
    """Central service for executing Modal predictions with model-specific adapters"""
    
    def __init__(self):
        self.config = self._load_config()
        self.adapters = self._initialize_adapters()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Modal models configuration from YAML file"""
        config_path = Path(__file__).parent.parent / "config" / "modal_models.yaml"
        
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
    
    def _initialize_adapters(self) -> Dict[str, Any]:
        """Initialize model-specific adapters"""
        adapters = {}
        
        models_config = self.config.get('models', {})
        
        # Initialize Boltz-2 adapter
        if 'boltz2' in models_config:
            adapters['boltz2'] = Boltz2Adapter(models_config['boltz2'])
            logger.debug("Initialized Boltz-2 adapter")
        
        # Initialize RFAntibody adapter
        if 'rfantibody' in models_config:
            adapters['rfantibody'] = RFAntibodyAdapter(models_config['rfantibody'])
            logger.debug("Initialized RFAntibody adapter")
        
        # Initialize Chai-1 adapter
        if 'chai1' in models_config:
            adapters['chai1'] = Chai1Adapter(models_config['chai1'])
            logger.debug("Initialized Chai-1 adapter")
        
        logger.info(f"Initialized {len(adapters)} Modal prediction adapters")
        return adapters
    
    async def execute_prediction(
        self,
        model_type: str,
        parameters: Dict[str, Any],
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a Modal prediction with the specified model
        
        Args:
            model_type: Type of model ('boltz2', 'rfantibody', 'chai1')
            parameters: Input parameters for the prediction
            job_id: Optional job ID for tracking
            
        Returns:
            Standardized prediction result
        """
        logger.info(f"Executing {model_type} prediction (job_id: {job_id})")
        
        # Validate model type
        if model_type not in self.adapters:
            available_models = list(self.adapters.keys())
            raise ValueError(f"Unsupported model type '{model_type}'. Available: {available_models}")
        
        adapter = self.adapters[model_type]
        model_config = self.config['models'][model_type]
        
        try:
            # Prepare parameters using model-specific adapter
            logger.debug(f"Preparing parameters for {model_type}")
            modal_parameters = adapter.prepare_parameters(parameters)
            
            # Execute Modal function via subprocess
            logger.debug(f"Executing Modal function: {model_config['app_name']}.{model_config['function_name']}")
            execution_result = await modal_subprocess_runner.execute_modal_function(
                app_name=model_config['app_name'],
                function_name=model_config['function_name'],
                parameters=modal_parameters,
                timeout=model_config.get('timeout', 3600)
            )
            
            # Process result using model-specific adapter
            logger.debug(f"Processing {model_type} result")
            modal_result = execution_result.get('result', {})
            processed_result = adapter.process_result(modal_result)
            
            # Add execution metadata
            processed_result.update({
                "modal_call_id": execution_result.get('modal_call_id'),
                "subprocess_attempt": execution_result.get('attempt', 1),
                "execution_status": execution_result.get('status', 'unknown')
            })
            
            # Add execution context
            processed_result = adapter.add_execution_context(processed_result, job_id)
            
            logger.info(f"{model_type} prediction completed successfully")
            return processed_result
            
        except Exception as e:
            logger.error(f"{model_type} prediction failed: {e}")
            
            # Return standardized error result
            error_result = {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "model_type": model_type,
                "job_id": job_id,
                "modal_call_id": None
            }
            
            # Add model info
            error_result = adapter.add_execution_context(error_result, job_id)
            
            return error_result
    
    def get_supported_models(self) -> Dict[str, Dict[str, Any]]:
        """Get information about supported models"""
        models_info = {}
        
        for model_type, adapter in self.adapters.items():
            models_info[model_type] = adapter.get_model_info()
        
        return models_info
    
    def get_model_config(self, model_type: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        if model_type not in self.config.get('models', {}):
            raise ValueError(f"Model type '{model_type}' not found in configuration")
        
        return self.config['models'][model_type]
    
    def validate_model_input(self, model_type: str, input_data: Dict[str, Any]) -> None:
        """Validate input data for a specific model"""
        if model_type not in self.adapters:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        adapter = self.adapters[model_type]
        adapter.validate_input(input_data)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get overall service status"""
        from services.modal_auth_service import modal_auth_service
        
        auth_status = modal_auth_service.get_auth_status()
        
        return {
            "service_status": "healthy",
            "supported_models": list(self.adapters.keys()),
            "config_loaded": bool(self.config),
            "adapters_initialized": len(self.adapters),
            "authentication": auth_status,
            "execution_config": self.config.get('execution', {}),
            "logging_config": self.config.get('logging', {})
        }

# Global instance
modal_execution_service = ModalExecutionService()