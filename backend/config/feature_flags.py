"""
Feature Flags Configuration
Controls rollout of new separated results API
"""

import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class FeatureFlags:
    """Centralized feature flag management"""
    
    def __init__(self):
        # Load flags from environment variables
        self.flags = {
            # Use new separated results API endpoints
            'use_separated_results_api': self._get_bool_env('USE_SEPARATED_RESULTS_API', False),
            
            # Show My Batches tab in frontend
            'show_my_batches_tab': self._get_bool_env('SHOW_MY_BATCHES_TAB', True),
            
            # Enable batch grouping in results
            'enable_batch_grouping': self._get_bool_env('ENABLE_BATCH_GROUPING', True),
            
            # Use enhanced job classifier
            'use_job_classifier': self._get_bool_env('USE_JOB_CLASSIFIER', True),
            
            # Enable v3 API endpoints
            'enable_v3_api': self._get_bool_env('ENABLE_V3_API', True),
            
            # Percentage of users to enable new API for (0-100)
            'v3_api_rollout_percentage': int(os.getenv('V3_API_ROLLOUT_PERCENTAGE', '100'))
        }
        
        logger.info(f"📋 Feature flags loaded: {self.flags}")
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ['true', '1', 'yes', 'on']
    
    def is_enabled(self, flag_name: str, user_id: str = None) -> bool:
        """
        Check if a feature flag is enabled
        Can optionally check user-specific rollout
        """
        if flag_name not in self.flags:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False
        
        # Check basic flag value
        if not self.flags[flag_name]:
            return False
        
        # Check percentage rollout for v3 API
        if flag_name == 'enable_v3_api' and user_id:
            rollout_percentage = self.flags.get('v3_api_rollout_percentage', 100)
            if rollout_percentage < 100:
                # Simple hash-based rollout
                user_hash = hash(user_id) % 100
                return user_hash < rollout_percentage
        
        return True
    
    def get_all_flags(self) -> Dict[str, Any]:
        """Get all current feature flag values"""
        return self.flags.copy()
    
    def update_flag(self, flag_name: str, value: Any) -> bool:
        """
        Update a feature flag value (for testing/admin purposes)
        In production, this should be protected
        """
        if flag_name in self.flags:
            old_value = self.flags[flag_name]
            self.flags[flag_name] = value
            logger.info(f"🔄 Updated feature flag {flag_name}: {old_value} -> {value}")
            return True
        return False
    
    def get_client_flags(self, user_id: str = None) -> Dict[str, Any]:
        """
        Get feature flags safe to send to frontend client
        Excludes sensitive server-side flags
        """
        client_safe_flags = {
            'show_my_batches_tab': self.is_enabled('show_my_batches_tab', user_id),
            'use_v3_api': self.is_enabled('enable_v3_api', user_id),
            'enable_batch_grouping': self.is_enabled('enable_batch_grouping', user_id)
        }
        return client_safe_flags

# Global instance
feature_flags = FeatureFlags()

# Export convenience functions
def is_feature_enabled(flag_name: str, user_id: str = None) -> bool:
    """Check if a feature is enabled"""
    return feature_flags.is_enabled(flag_name, user_id)

def get_client_flags(user_id: str = None) -> Dict[str, Any]:
    """Get client-safe feature flags"""
    return feature_flags.get_client_flags(user_id)