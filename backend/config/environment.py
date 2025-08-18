"""
Environment configuration for OMTX-Hub
Handles loading of environment variables securely
"""

import os
import subprocess
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class EnvironmentConfig:
    """Secure environment configuration"""
    
    @staticmethod
    def get_modal_token() -> Optional[str]:
        """Get Modal token from CLI profile"""
        try:
            # Check if Modal CLI is configured
            result = subprocess.run(
                ["modal", "whoami"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                return "configured"  # Token is available via CLI
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    
    @staticmethod
    def get_modal_environment() -> str:
        """Get Modal environment name"""
        return os.getenv("MODAL_ENVIRONMENT", "main")
    
    @staticmethod
    def get_huggingface_token() -> Optional[str]:
        """Get HuggingFace token from environment"""
        return os.getenv("HUGGINGFACE_TOKEN")
    
    @staticmethod
    def get_database_url() -> Optional[str]:
        """Get database URL from environment"""
        return os.getenv("DATABASE_URL")
    
    @staticmethod
    def get_redis_url() -> Optional[str]:
        """Get Redis URL from environment"""
        return os.getenv("REDIS_URL", "redis://localhost:6379")
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode"""
        return os.getenv("ENVIRONMENT", "development") == "development"
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production mode"""
        return os.getenv("ENVIRONMENT") == "production"

def validate_environment():
    """Validate that required environment variables are set"""
    missing_vars = []
    
    # Check for Modal CLI configuration
    modal_status = EnvironmentConfig.get_modal_token()
    if not modal_status:
        missing_vars.append("Modal CLI configuration")
    
    # Optional but recommended
    if not EnvironmentConfig.get_huggingface_token():
        print("Warning: HUGGINGFACE_TOKEN not set. Some models may not download properly.")
    
    if missing_vars:
        print(f"Missing required configuration: {', '.join(missing_vars)}")
        print("Please run: modal token set --<token-id>--token-secret <secret> --profile=omtx-ai")
        print("Then run: modal profile activate omtx-ai")
        return False
    
    return True 