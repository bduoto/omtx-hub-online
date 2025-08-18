#!/usr/bin/env python3
"""
Setup Modal authentication for Docker containers
"""

import subprocess
import sys

def setup_modal_auth():
    """Setup Modal authentication using profile-based approach"""
    
    print("Setting up Modal authentication...")
    print("This will configure Modal with profile-based authentication")
    
    # Set up profile
    try:
        subprocess.run([
            "modal", "token", "set", 
            "--profile=omtx-ai"
        ], check=True)
        print("Modal authentication configured successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Modal authentication: {e}")
        return False
    
    # Test Modal import
    try:
        import modal
        print("Modal imported successfully!")
        print(f"Modal version: {modal.__version__}")
    except ImportError as e:
        print(f"Failed to import Modal: {e}")
        return False
    
    # Activate profile
    try:
        subprocess.run([
            "modal", "profile", "activate", "omtx-ai"
        ], check=True)
        print("Modal authentication setup complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error activating Modal profile: {e}")
        return False

if __name__ == "__main__":
    success = setup_modal_auth()
    sys.exit(0 if success else 1) 