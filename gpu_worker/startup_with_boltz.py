#!/usr/bin/env python3
"""
Startup script that installs Boltz-2 on first run if not available
This allows us to deploy quickly and install Boltz at runtime
"""

import os
import sys
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_boltz():
    """Install Boltz-2 with CUDA support at runtime"""
    try:
        logger.info("🔧 Installing Boltz-2 with CUDA support...")
        
        # Install Boltz with CUDA extras
        cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "boltz[cuda]==2.1.1"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("✅ Boltz-2 installed successfully!")
            return True
        else:
            logger.error(f"❌ Boltz-2 installation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Boltz-2 installation timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Boltz-2 installation error: {e}")
        return False

def check_boltz_available():
    """Check if Boltz-2 is already installed"""
    try:
        import boltz
        logger.info("✅ Boltz-2 already available")
        return True
    except ImportError:
        logger.info("⚠️ Boltz-2 not found, will install")
        return False

def main():
    """Main startup sequence"""
    logger.info("🚀 Starting GPU worker with Boltz-2 auto-install...")
    
    # Check if Boltz is available
    if not check_boltz_available():
        # Install Boltz if not available
        if os.getenv("INSTALL_BOLTZ", "true").lower() == "true":
            success = install_boltz()
            if not success:
                logger.warning("⚠️ Continuing with mock predictions only")
        else:
            logger.info("ℹ️ Boltz installation disabled, using mock predictions")
    
    # Start the main application
    logger.info("🏃 Starting main application...")
    
    # Import and run the main Flask app
    try:
        os.chdir("/app")
        import simple_main
        # This will start the Flask app
        simple_main.app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
    except Exception as e:
        logger.error(f"❌ Failed to start main application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()