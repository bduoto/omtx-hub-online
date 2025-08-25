#!/usr/bin/env python3
"""
Dual Mode Entrypoint for Boltz-2 GPU Worker
Automatically detects whether to run as HTTP service or Cloud Run Job
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entrypoint that detects execution mode"""
    
    # Check if we're running as a Cloud Run Job (has job parameters in env)
    job_id = os.getenv("JOB_ID")
    protein_sequence = os.getenv("PROTEIN_SEQUENCE")
    ligand_smiles = os.getenv("LIGAND_SMILES")
    
    # Check for Cloud Tasks headers (when triggered via HTTP from Cloud Tasks)
    cloud_tasks_execution = os.getenv("HTTP_X_CLOUDTASKS_TASKNAME")
    
    if job_id and protein_sequence and ligand_smiles:
        # Cloud Run Job mode - direct execution with env vars
        logger.info("🎯 Cloud Run Job mode detected")
        logger.info(f"   Job ID: {job_id}")
        logger.info("   Starting job execution...")
        
        import job_main
        job_main.run_job()
        
    elif cloud_tasks_execution:
        # Cloud Tasks HTTP mode - process the request
        logger.info("☁️ Cloud Tasks HTTP mode detected")
        logger.info(f"   Task: {cloud_tasks_execution}")
        logger.info("   Starting HTTP service for Cloud Tasks...")
        
        # Start HTTP service to handle Cloud Tasks requests
        start_http_service()
        
    else:
        # Standard HTTP service mode
        logger.info("🌐 HTTP Service mode detected")
        logger.info(f"   Port: {os.getenv('PORT', 8080)}")
        logger.info("   Starting Boltz-2 prediction service...")
        
        start_http_service()

def start_http_service():
    """Start the HTTP service with Gunicorn"""
    import subprocess
    
    port = os.getenv('PORT', '8080')
    
    # Use Gunicorn for production
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "1",  # Single worker for GPU (can't share GPU)
        "--threads", "4",  # Multiple threads for concurrent requests
        "--timeout", "300",  # 5 minute timeout for predictions
        "--worker-class", "sync",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "simple_main:app"
    ]
    
    logger.info(f"Starting Gunicorn: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)