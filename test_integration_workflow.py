#!/usr/bin/env python3
"""
Test the complete GKE → Cloud Tasks → Cloud Run workflow
"""

import sys
import os
import json
import asyncio
import logging
sys.path.append('backend')

from services.job_submission_service import JobSubmissionService
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_individual_job():
    """Test individual job submission and processing"""
    logger.info("🚀 Testing Individual Job Workflow")
    
    try:
        # Initialize service
        job_service = JobSubmissionService()
        logger.info(f"✅ Job service initialized with GPU worker: {job_service.gpu_worker_url}")
        
        # Submit an individual job
        result = await job_service.submit_individual_job(
            protein_sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            ligand_smiles="CCO",  # ethanol
            job_name="Integration Test Individual",
            user_id="test_user",
            parameters={"max_steps": 100, "confidence_threshold": 0.7}
        )
        
        logger.info(f"✅ Individual job submitted: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Individual job test failed: {e}")
        raise

async def test_batch_job():
    """Test batch job submission and processing"""
    logger.info("🚀 Testing Batch Job Workflow")
    
    try:
        # Initialize service
        job_service = JobSubmissionService()
        
        # Submit a batch job
        ligands = [
            {"name": "ethanol", "smiles": "CCO"},
            {"name": "methanol", "smiles": "CO"},
            {"name": "isopropanol", "smiles": "CC(C)O"}
        ]
        
        result = await job_service.submit_batch_job(
            batch_name="Integration Test Batch",
            protein_sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            ligands=ligands,
            user_id="test_user",
            parameters={"max_steps": 100}
        )
        
        logger.info(f"✅ Batch job submitted: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Batch job test failed: {e}")
        raise

async def check_job_status(job_id: str, timeout: int = 60):
    """Monitor job status until completion or timeout"""
    logger.info(f"🔍 Monitoring job {job_id} for up to {timeout} seconds")
    
    db = firestore.Client(project='om-models')
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            job_doc = db.collection('jobs').document(job_id).get()
            
            if job_doc.exists:
                job_data = job_doc.to_dict()
                status = job_data.get('status', 'unknown')
                
                logger.info(f"📊 Job {job_id} status: {status}")
                
                if status in ['completed', 'failed']:
                    logger.info(f"✅ Job {job_id} finished with status: {status}")
                    return job_data
                    
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            logger.warning(f"⚠️ Error checking job status: {e}")
            await asyncio.sleep(5)
    
    logger.warning(f"⏰ Timeout waiting for job {job_id}")
    return None

async def main():
    """Run complete integration tests"""
    logger.info("🎯 Starting Complete Integration Workflow Tests")
    
    try:
        # Test 1: Individual Job
        logger.info("\n" + "="*50)
        logger.info("TEST 1: Individual Job Submission")
        logger.info("="*50)
        
        individual_result = await test_individual_job()
        individual_job_id = individual_result['job_id']
        
        # Monitor individual job for 2 minutes
        individual_status = await check_job_status(individual_job_id, timeout=120)
        
        # Test 2: Batch Job
        logger.info("\n" + "="*50)
        logger.info("TEST 2: Batch Job Submission")
        logger.info("="*50)
        
        batch_result = await test_batch_job()
        batch_id = batch_result['batch_id']
        child_job_ids = batch_result['job_ids']
        
        # Monitor batch parent
        logger.info(f"🔍 Monitoring batch parent: {batch_id}")
        batch_status = await check_job_status(batch_id, timeout=60)
        
        # Monitor first child job
        if child_job_ids:
            first_child = child_job_ids[0]
            logger.info(f"🔍 Monitoring first child job: {first_child}")
            child_status = await check_job_status(first_child, timeout=120)
        
        logger.info("\n" + "="*50)
        logger.info("🎉 INTEGRATION TESTS COMPLETE")
        logger.info("="*50)
        
        # Summary
        print("\n📊 TEST RESULTS SUMMARY:")
        print(f"✅ Individual Job ID: {individual_job_id}")
        print(f"✅ Batch Job ID: {batch_id}")
        print(f"✅ Child Job IDs: {child_job_ids}")
        print(f"🌐 GPU Worker URL: {JobSubmissionService().gpu_worker_url}")
        
        if individual_status:
            print(f"📈 Individual Job Status: {individual_status.get('status', 'unknown')}")
        if batch_status:
            print(f"📈 Batch Job Status: {batch_status.get('status', 'unknown')}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration tests failed: {e}")
        return False

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)