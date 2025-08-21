#!/usr/bin/env python3
"""
Startup script for GPU Worker Service
Handles initialization gracefully and starts the Flask app
"""

import os
import sys
import logging
from main import app, initialize_services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        logger.info("🚀 Starting GPU Worker Service")
        
        # Initialize services (graceful fallback)
        logger.info("🔧 Initializing services...")
        services_ready = initialize_services()
        
        if services_ready:
            logger.info("✅ All services initialized successfully")
        else:
            logger.warning("⚠️ Some services failed to initialize - running in degraded mode")
        
        # Get port from environment
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"🌐 Starting Flask app on 0.0.0.0:{port}")
        
        # Start the Flask application
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=False, 
            threaded=True,
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start GPU Worker Service: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()