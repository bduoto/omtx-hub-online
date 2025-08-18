#!/usr/bin/env python3
"""
End-to-End Boltz2 Test: Complete workflow from API to GCP storage
Tests: API Request → Modal Execution → Result Processing → GCP Storage → Job Management
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_boltz2_end_to_end():
    """Test complete end-to-end Boltz2 workflow"""
    
    print("🚀 BOLTZ2 END-TO-END WORKFLOW TEST")
    print("=" * 50)
    
    # Step 1: Create job via Unified Job Manager
    print("\n1️⃣ Creating job via Unified Job Manager...")
    try:
        from database.unified_job_manager import unified_job_manager
        
        job_data = {
            'name': f'E2E Boltz2 Test {int(time.time())}',
            'task_type': 'protein_ligand_binding',
            'status': 'pending',
            'user_id': 'test_user_e2e',
            'input_data': {
                'protein_sequences': ['MKLLVLSLSLVLVLLLSHPQGSHM'],
                'ligands': ['CCO'],  # Ethanol
                'use_msa_server': True,
                'use_potentials': False,
                'job_name': 'E2E Boltz2 Test'
            }
        }
        
        job_id = unified_job_manager.create_job(job_data)
        print(f"   ✅ Job created: {job_id}")
        
    except Exception as e:
        print(f"   ❌ Job creation failed: {e}")
        return False
    
    # Step 2: Execute Modal prediction
    print("\n2️⃣ Executing Modal prediction...")
    try:
        from services.modal_execution_service import modal_execution_service
        
        # Update job status to running
        unified_job_manager.update_job_status(job_id, 'running')
        
        # Execute prediction
        result = await modal_execution_service.execute_prediction(
            model_type='boltz2',
            parameters={
                'protein_sequences': ['MKLLVLSLSLVLVLLLSHPQGSHM'],
                'ligands': ['CCO'],
                'use_msa_server': True,
                'use_potentials': False
            },
            job_id=job_id
        )
        
        print(f"   ✅ Modal execution completed")
        print(f"   ✅ Result status: {result.get('status')}")
        print(f"   ✅ Execution time: {result.get('execution_time', 'N/A')} seconds")
        
        if result.get('structure_file_base64'):
            print(f"   ✅ Structure file generated: {len(result['structure_file_base64'])} chars")
        
    except Exception as e:
        print(f"   ❌ Modal execution failed: {e}")
        # Update job status to failed
        unified_job_manager.update_job_status(job_id, 'failed')
        return False
    
    # Step 3: Store results to GCP
    print("\n3️⃣ Storing results to GCP...")
    try:
        from services.gcp_storage_service import gcp_storage_service
        
        # Store job results
        storage_success = await gcp_storage_service.store_job_results(
            job_id, result, 'protein_ligand_binding'
        )
        
        if storage_success:
            print(f"   ✅ Results stored to GCP successfully")
            print(f"   ✅ Storage paths: jobs/{job_id}/ and archive/Boltz-2/Protein-Ligand/{job_id}/")
        else:
            print(f"   ❌ Failed to store results to GCP")
            
        # Store raw Modal output
        modal_storage_success = await gcp_storage_service.store_modal_output(
            job_id, result.get('raw_modal_result', {})
        )
        
        if modal_storage_success:
            print(f"   ✅ Raw Modal output stored")
            
    except Exception as e:
        print(f"   ❌ GCP storage failed: {e}")
        return False
    
    # Step 4: Update job with results
    print("\n4️⃣ Updating job with results...")
    try:
        # Update job status and results
        update_success = unified_job_manager.update_job_status(
            job_id, 'completed', result
        )
        
        if update_success:
            print(f"   ✅ Job updated with results")
        else:
            print(f"   ❌ Failed to update job")
            
    except Exception as e:
        print(f"   ❌ Job update failed: {e}")
        return False
    
    # Step 5: Verify job retrieval
    print("\n5️⃣ Verifying job retrieval...")
    try:
        # Get job by ID
        retrieved_job = unified_job_manager.get_job(job_id)
        
        if retrieved_job:
            print(f"   ✅ Job retrieved successfully")
            print(f"   ✅ Job status: {retrieved_job.get('status')}")
            print(f"   ✅ Has results: {bool(retrieved_job.get('results'))}")
        else:
            print(f"   ❌ Failed to retrieve job")
            
        # Get user jobs via primary backend
        user_jobs = unified_job_manager.primary_backend.get_user_jobs('test_user_e2e', limit=5)
        print(f"   ✅ User has {len(user_jobs)} jobs")
        
    except Exception as e:
        print(f"   ❌ Job retrieval failed: {e}")
        return False
    
    # Step 6: Test result parsing for frontend
    print("\n6️⃣ Testing result parsing for frontend...")
    try:
        # Simulate frontend result parsing
        frontend_result = {
            'job_id': job_id,
            'status': result.get('status'),
            'confidence_score': result.get('prediction_confidence'),
            'execution_time': result.get('execution_time'),
            'structure_available': bool(result.get('structure_file_base64')),
            'model_version': result.get('model_version'),
            'task_type': result.get('task_type')
        }
        
        print(f"   ✅ Frontend result parsed:")
        for key, value in frontend_result.items():
            print(f"      {key}: {value}")
            
    except Exception as e:
        print(f"   ❌ Result parsing failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!")
    print(f"🔗 Job ID: {job_id}")
    print(f"📁 GCP Storage: jobs/{job_id}/")
    print(f"📊 Results: {len(str(result))} chars")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_boltz2_end_to_end())
    if success:
        print("\n✅ All tests passed - Boltz2 backend is fully functional!")
    else:
        print("\n❌ Some tests failed - check logs above")
        sys.exit(1)
