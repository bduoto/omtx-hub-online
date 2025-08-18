#!/usr/bin/env python3
"""
Test script to debug Modal prediction storage to GCP bucket
Traces the complete flow from Modal submission to GCP storage
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import necessary modules
from database.unified_job_manager import unified_job_manager
from config.gcp_storage import gcp_storage
from services.modal_monitor import modal_monitor
from tasks.task_handlers import task_handler_registry

async def test_modal_to_gcp_flow():
    """Test complete flow from Modal submission to GCP storage"""
    
    print("\n" + "="*60)
    print("TESTING MODAL -> GCP STORAGE FLOW")
    print("="*60)
    
    # 1. Check GCP storage availability
    print("\n1. Checking GCP Storage...")
    if not gcp_storage.available:
        print("❌ GCP Storage not available!")
        return
    print("✅ GCP Storage connected")
    print(f"   Bucket: {gcp_storage.bucket_name}")
    
    # 2. Create a test job
    print("\n2. Creating test job...")
    job_id = f"test_modal_gcp_{int(time.time())}"
    job_data = {
        'id': job_id,
        'name': 'Test Modal GCP Flow',
        'type': 'protein_ligand_binding',
        'status': 'pending',
        'model_name': 'boltz2',
        'input_data': {
            'task_type': 'protein_ligand_binding',
            'input_data': {
                'protein_sequence': 'MGQPGNGSAFLLAPNGSHAPDHDVTQERDEVWVVGMGIVMSLIVLAIVFGNVLVITAIAKFERLQTVTNYFITSLACADLVMGLAVVPFGAAHILMKMWTFGNFWCEFWTSIDVLCVTASIETLCVIAVDRYFAITSPFKYQSLLTKNKARVIILMVWIVSGLTSFLPIQMHWYRATHQEAINCYANETCCDFFTNQAYAIASSIVSFYVPLVIMVFVYSRVFQEAKRQLQKIDKSEGRFHVQNLSQVEQDGRTGHGLRRSSKFCLKEHKALKTLGIIMGTFTLCWLPFFIVNIVHVIQDNLIRKEVYILLNWIGYVNSGFNPLIYCRSPDFRIAFQELLCLRRSSLKAYGNGYSSNGNTGEQSGYHVEQEKENKLLCEDLPGTEDFVGHQGTVPSDNIDSQGRNCSTNDSLL',
                'ligand_smiles': 'CNCC(O)c1ccc(O)c(O)c1',
                'protein_name': 'test_protein'
            },
            'job_name': 'Test Modal GCP Flow',
            'use_msa': False,
            'use_potentials': True
        },
        'created_at': time.time()
    }
    
    created_job_id = unified_job_manager.create_job(job_data)
    print(f"✅ Job created: {created_job_id}")
    
    # 3. Submit to Modal
    print("\n3. Submitting to Modal...")
    try:
        handler = task_handler_registry.get_handler('protein_ligand_binding')
        result = await handler(
            job_id=created_job_id,
            task_type='protein_ligand_binding',
            input_data=job_data['input_data']['input_data'],
            job_name=job_data['name'],
            use_msa=False,
            use_potentials=True
        )
        
        print(f"✅ Modal submission result:")
        print(f"   Status: {result.get('status')}")
        print(f"   Modal Call ID: {result.get('modal_call_id')}")
        
        # 4. Check if Modal call ID was stored
        print("\n4. Checking job record for Modal call ID...")
        job = unified_job_manager.get_job(created_job_id)
        if job and job.get('results', {}).get('modal_call_id'):
            print(f"✅ Modal call ID stored in job: {job['results']['modal_call_id']}")
        else:
            print("❌ Modal call ID NOT stored in job record!")
            print(f"   Job results: {job.get('results', {}) if job else 'No job found'}")
        
        # 5. Monitor for completion
        print("\n5. Monitoring Modal job completion...")
        if result.get('modal_call_id'):
            # Run modal monitor to check completion
            await modal_monitor.check_and_update_jobs()
            
            # Check job status after monitoring
            job = unified_job_manager.get_job(created_job_id)
            print(f"   Job status after monitoring: {job.get('status') if job else 'No job'}")
            
            # 6. Check GCP storage for results
            print("\n6. Checking GCP storage for results...")
            job_files = gcp_storage.list_job_files(created_job_id)
            
            if job_files:
                print(f"✅ Found {len(job_files)} files in GCP:")
                for file in job_files:
                    print(f"   - {file['name']} ({file['size']} bytes)")
                    
                # Check metadata.json
                metadata_path = f"jobs/{created_job_id}/metadata.json"
                metadata_content = gcp_storage.download_file(metadata_path)
                if metadata_content:
                    metadata = json.loads(metadata_content.decode('utf-8'))
                    print(f"\n   Metadata stored at: {datetime.fromisoformat(metadata.get('stored_at', ''))}")
                    print(f"   Task type: {metadata.get('task_type')}")
            else:
                print("❌ No files found in GCP storage!")
                
                # Debug: List all files in jobs/ directory
                print("\n   Debugging - Listing all jobs in GCP:")
                blobs = list(gcp_storage.bucket.list_blobs(prefix="jobs/", max_results=10))
                for blob in blobs:
                    print(f"   - {blob.name}")
        
        # 7. Check result retrieval
        print("\n7. Testing result retrieval...")
        from services.gcp_results_indexer import gcp_results_indexer
        user_results = await gcp_results_indexer.get_user_results("current_user", limit=5)
        
        found_test_job = False
        for result in user_results.get('results', []):
            if result.get('job_id') == created_job_id:
                found_test_job = True
                print(f"✅ Test job found in results:")
                print(f"   - Status: {result.get('status')}")
                print(f"   - Files: {result.get('file_count')} files")
                break
        
        if not found_test_job:
            print("❌ Test job NOT found in user results!")
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

async def check_modal_result_storage():
    """Check how Modal results are being stored"""
    
    print("\n" + "="*60)
    print("CHECKING MODAL RESULT STORAGE MECHANISM")
    print("="*60)
    
    # Check modal execution service
    print("\n1. Checking Modal execution service...")
    try:
        from services.modal_execution_service import modal_execution_service
        print("✅ Modal execution service available")
        
        # Check if it has storage methods
        if hasattr(modal_execution_service, 'store_results'):
            print("   - Has store_results method")
        else:
            print("   - NO store_results method found")
            
    except Exception as e:
        print(f"❌ Error loading modal execution service: {e}")
    
    # Check task handlers for storage logic
    print("\n2. Checking task handlers for storage logic...")
    handler = task_handler_registry.get_handler('protein_ligand_binding')
    if handler:
        # Get the handler source
        import inspect
        source = inspect.getsource(handler)
        if 'gcp_storage' in source or 'store_results' in source:
            print("✅ Task handler has storage logic")
        else:
            print("❌ Task handler missing storage logic")
    
    # Check modal monitor for result retrieval
    print("\n3. Checking modal monitor for result storage...")
    import inspect
    monitor_source = inspect.getsource(modal_monitor.check_and_update_jobs)
    if 'gcp_storage' in monitor_source:
        print("✅ Modal monitor has GCP storage integration")
    else:
        print("❌ Modal monitor missing GCP storage integration")

if __name__ == "__main__":
    print("Starting Modal -> GCP Storage Flow Test...")
    
    # Run both tests
    asyncio.run(test_modal_to_gcp_flow())
    asyncio.run(check_modal_result_storage())