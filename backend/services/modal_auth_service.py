"""
Modal Authentication Service
Handles Modal credential management and authentication
"""

import os
import time
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ModalAuthService:
    """Centralized Modal authentication and credential management"""
    
    def __init__(self):
        self._cached_credentials: Optional[Tuple[str, str]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 3600  # 1 hour cache TTL
        
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Modal credentials with caching
        Returns: (token_id, token_secret) or (None, None) if not found
        """
        # Check cache first
        if self._is_cache_valid():
            logger.debug("Using cached Modal credentials")
            return self._cached_credentials
        
        # Load fresh credentials
        token_id, token_secret = self._load_credentials()
        
        # Cache if valid
        if token_id and token_secret:
            self._cached_credentials = (token_id, token_secret)
            self._cache_timestamp = time.time()
            logger.info("Modal credentials loaded and cached successfully")
        else:
            logger.warning("No valid Modal credentials found")
            
        return token_id, token_secret
    
    def _is_cache_valid(self) -> bool:
        """Check if cached credentials are still valid"""
        if not self._cached_credentials or not self._cache_timestamp:
            return False
        
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _load_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Load Modal credentials from environment or config file"""
        # Try environment variables first
        token_id = os.environ.get("MODAL_TOKEN_ID")
        token_secret = os.environ.get("MODAL_TOKEN_SECRET")
        
        if token_id and token_secret:
            logger.info("Found Modal credentials in environment variables")
            return token_id, token_secret
        
        # Try Modal config file
        return self._load_from_config_file()
    
    def _load_from_config_file(self) -> Tuple[Optional[str], Optional[str]]:
        """Load Modal credentials from ~/.modal.toml file"""
        modal_config_path = Path.home() / ".modal.toml"
        
        if not modal_config_path.exists():
            logger.warning(f"Modal config file not found at {modal_config_path}")
            return None, None
        
        try:
            import toml
            
            with open(modal_config_path, 'r') as f:
                config = toml.load(f)
            
            # Find the active profile
            active_profile_name = self._find_active_profile(config)
            profile = config.get(active_profile_name, {})
            
            token_id = profile.get('token_id')
            token_secret = profile.get('token_secret')
            
            if token_id and token_secret:
                logger.info(f"Successfully loaded credentials from profile '{active_profile_name}'")
                return token_id, token_secret
            else:
                logger.warning(f"Could not find valid credentials in profile '{active_profile_name}'")
                return None, None
                
        except ImportError:
            logger.error("toml package not available. Install with: pip install toml")
            return None, None
        except Exception as e:
            logger.error(f"Failed to read Modal config file: {e}")
            return None, None
    
    def _find_active_profile(self, config: Dict) -> str:
        """Find the active profile in Modal config"""
        # Look for profile marked as active
        for profile_name, profile_data in config.items():
            if isinstance(profile_data, dict) and profile_data.get('active'):
                return profile_name
        
        # Fallback to default profile
        if 'default' in config:
            return 'default'
        
        # Use first available profile
        for profile_name in config.keys():
            if isinstance(config[profile_name], dict):
                return profile_name
        
        return 'default'
    
    def create_auth_env(self) -> Dict[str, str]:
        """Create environment dictionary with Modal credentials"""
        token_id, token_secret = self.get_credentials()
        
        env = os.environ.copy()
        if token_id and token_secret:
            env['MODAL_TOKEN_ID'] = token_id
            env['MODAL_TOKEN_SECRET'] = token_secret
        
        return env
    
    def get_auth_script_snippet(self) -> str:
        """Generate Python code snippet for setting Modal credentials in subprocess"""
        token_id, token_secret = self.get_credentials()

        if not (token_id and token_secret):
            logger.warning("No Modal credentials available for subprocess")
            return ""

        # Use secure credential injection without exposing in string literals
        return '''
        # Set Modal authentication credentials from environment
        import os
        # Credentials will be injected via environment variables
        # This avoids exposing credentials in code or logs
        '''
    
    def validate_credentials(self) -> bool:
        """Validate that credentials are available and properly formatted"""
        token_id, token_secret = self.get_credentials()
        
        if not token_id or not token_secret:
            return False
        
        # Basic format validation
        if len(token_id) < 10 or len(token_secret) < 10:
            logger.warning("Modal credentials appear to be malformed")
            return False
        
        return True
    
    def clear_cache(self):
        """Clear cached credentials (useful for testing or credential rotation)"""
        self._cached_credentials = None
        self._cache_timestamp = None
        logger.info("Modal credentials cache cleared")
    
    def get_auth_status(self) -> Dict[str, any]:
        """Get authentication status for debugging/monitoring"""
        token_id, token_secret = self.get_credentials()
        
        return {
            "credentials_available": bool(token_id and token_secret),
            "cache_valid": self._is_cache_valid(),
            "cache_age_seconds": (time.time() - self._cache_timestamp) if self._cache_timestamp else None,
            "config_file_exists": (Path.home() / ".modal.toml").exists(),
            "env_vars_set": bool(os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"))
        }

# Global instance
modal_auth_service = ModalAuthService()