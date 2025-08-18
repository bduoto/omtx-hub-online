"""
Base Modal Prediction Adapter
Abstract base class for model-specific adapters
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseModalAdapter(ABC):
    """Abstract base class for Modal prediction adapters"""
    
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.app_name = model_config['app_name']
        self.function_name = model_config['function_name']
        self.timeout = model_config.get('timeout', 3600)
        self.gpu = model_config.get('gpu', 'A100-40GB')
        self.description = model_config.get('description', '')
        self.expected_parameters = model_config.get('parameters', [])
    
    @abstractmethod
    def prepare_parameters(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare and validate parameters for Modal function call
        
        Args:
            input_data: Raw input data from API request
            
        Returns:
            Dict of parameters formatted for Modal function
        """
        pass
    
    @abstractmethod
    def process_result(self, modal_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize Modal function result
        
        Args:
            modal_result: Raw result from Modal function
            
        Returns:
            Processed result in standardized format
        """
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """
        Validate input data before processing
        
        Args:
            input_data: Input data to validate
            
        Raises:
            ValueError: If input data is invalid
        """
        if not isinstance(input_data, dict):
            raise ValueError("Input data must be a dictionary")
        
        # Check for required parameters (basic validation)
        missing_params = []
        for param in self.expected_parameters:
            if param not in input_data:
                missing_params.append(param)
        
        if missing_params:
            logger.warning(f"Missing parameters for {self.app_name}: {missing_params}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and configuration"""
        return {
            "app_name": self.app_name,
            "function_name": self.function_name,
            "description": self.description,
            "timeout": self.timeout,
            "gpu": self.gpu,
            "expected_parameters": self.expected_parameters
        }
    
    def extract_call_id(self, modal_result: Dict[str, Any]) -> Optional[str]:
        """
        Extract Modal call ID from result for job tracking
        
        Args:
            modal_result: Result from Modal function
            
        Returns:
            Modal call ID if found, None otherwise
        """
        if not isinstance(modal_result, dict):
            return None
        
        # Try common ID field names
        id_fields = ['modal_call_id', 'call_id', 'id', 'job_id']
        
        for field in id_fields:
            if field in modal_result and modal_result[field]:
                return str(modal_result[field])
        
        # Check execution metadata
        metadata = modal_result.get('_execution_metadata', {})
        for field in id_fields:
            if field in metadata and metadata[field]:
                return str(metadata[field])
        
        return None
    
    def add_execution_context(self, result: Dict[str, Any], job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add execution context to result
        
        Args:
            result: Processed result
            job_id: Optional job ID
            
        Returns:
            Result with added context
        """
        result['model_info'] = {
            "app_name": self.app_name,
            "function_name": self.function_name,
            "model_type": self.__class__.__name__.lower().replace('adapter', ''),
            "gpu": self.gpu
        }
        
        if job_id:
            result['job_id'] = job_id
        
        return result