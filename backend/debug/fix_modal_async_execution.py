#!/usr/bin/env python3
"""
Fix Modal async execution to properly use .spawn() for non-blocking calls
and store results to GCP when jobs complete
"""

import os
import json

def fix_subprocess_runner():
    """Update modal_subprocess_runner.py to use spawn() for async execution"""
    
    file_path = "services/modal_subprocess_runner.py"
    
    print(f"\n1. Updating {file_path} to use spawn() for async execution...")
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace .remote() with .spawn() for async execution
    updated_content = content.replace(
        'result = modal_function.remote(**params)',
        '''# Use spawn() for async execution to get call ID
        call = modal_function.spawn(**params)
        modal_call_id = call.object_id
        
        print(f"Modal call started with ID: {modal_call_id}")
        
        # Return immediately with call ID for async monitoring
        result = {
            "status": "running",
            "modal_call_id": modal_call_id,
            "message": "Modal prediction started, monitoring in background"
        }'''
    )
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("✅ Updated subprocess runner to use spawn()")

def fix_task_handler_storage():
    """Fix task handlers to not store results immediately for async jobs"""
    
    file_path = "tasks/task_handlers.py"
    
    print(f"\n2. Updating {file_path} to handle async storage properly...")
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the storage logic to only store when results are actually available
    old_code = '''            # Store results to GCP if successful
            if job_id and isinstance(result_data, dict) and result_data.get('structure_file_base64'):
                from services.gcp_storage_service import gcp_storage_service
                await gcp_storage_service.store_job_results(job_id, result_data, 'protein_ligand_binding')'''
    
    new_code = '''            # Only store results to GCP if we have actual results (not async)
            if job_id and isinstance(result_data, dict) and result_data.get('structure_file_base64'):
                # This is a synchronous result with actual data
                from services.gcp_storage_service import gcp_storage_service
                await gcp_storage_service.store_job_results(job_id, result_data, 'protein_ligand_binding')
            elif job_id and isinstance(result_data, dict) and result_data.get('status') == 'running':
                # This is an async job - results will be stored by modal monitor when complete
                logger.info(f"🔄 Async job {job_id} started, results will be stored when complete")'''
    
    updated_content = content.replace(old_code, new_code)
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print("✅ Updated task handler storage logic")

def verify_modal_monitor_storage():
    """Verify modal monitor properly stores results when jobs complete"""
    
    file_path = "services/modal_monitor.py"
    
    print(f"\n3. Checking {file_path} for proper GCP storage integration...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if storage is properly called
    if 'await gcp_storage_service.store_job_results' in content:
        print("✅ Modal monitor has GCP storage integration")
    else:
        print("❌ Modal monitor missing GCP storage integration")
        
    # Check if Modal results are properly retrieved
    if 'modal_result[\'result\']' in content:
        print("✅ Modal monitor retrieves results correctly")
    else:
        print("❌ Modal monitor may not retrieve results correctly")

def create_test_script():
    """Create a test script to verify the fixes"""
    
    test_script = '''#!/usr/bin/env python3
"""Test script to verify Modal async execution and GCP storage"""

import asyncio
import time
import json
from database.unified_job_manager import unified_job_manager
from tasks.task_handlers import task_handler_registry
from services.modal_monitor import modal_monitor
from config.gcp_storage import gcp_storage

async def test_async_modal_execution():
    """Test the complete async flow"""
    
    print("\\n" + "="*60)
    print("TESTING ASYNC MODAL EXECUTION WITH GCP STORAGE")
    print("="*60)
    
    # Create test job
    job_id = f"test_async_{int(time.time())}"
    job_data = {
        'id': job_id,
        'name': 'Test Async Modal Execution',
        'type': 'protein_ligand_binding',
        'status': 'pending',
        'model_name': 'boltz2',
        'input_data': {
            'protein_sequence': 'MGQPGNGSAFLLAPNGSHAPDHDVTQER',
            'ligand_smiles': 'CNCC(O)c1ccc(O)c(O)c1',
            'protein_name': 'test_async_protein'
        },
        'created_at': time.time()
    }
    
    created_job_id = unified_job_manager.create_job(job_data)
    print(f"✅ Created job: {created_job_id}")
    
    # Execute prediction
    handler = task_handler_registry.get_handler('protein_ligand_binding')
    result = await handler(
        job_id=created_job_id,
        task_type='protein_ligand_binding',
        input_data=job_data['input_data'],
        job_name=job_data['name'],
        use_msa=False,
        use_potentials=True
    )
    
    print(f"\\n📊 Initial result:")
    print(f"   Status: {result.get('status')}")
    print(f"   Modal Call ID: {result.get('modal_call_id')}")
    
    if result.get('status') == 'running':
        print("\\n✅ Async execution started successfully!")
        
        # Wait a bit then check monitor
        print("\\n⏳ Waiting 10 seconds then checking monitor...")
        await asyncio.sleep(10)
        
        # Run monitor check
        await modal_monitor.check_and_update_jobs()
        
        # Check job status
        job = unified_job_manager.get_job(created_job_id)
        print(f"\\n📊 Job status after monitor check: {job.get('status')}")
        
        # Check GCP storage
        job_files = gcp_storage.list_job_files(created_job_id)
        print(f"\\n📁 Files in GCP storage: {len(job_files)}")
        for file in job_files:
            print(f"   - {file['name']}")
    else:
        print("\\n❌ Job did not start async execution")
    
    print("\\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_async_modal_execution())
'''
    
    with open('test_async_modal_execution.py', 'w') as f:
        f.write(test_script)
    
    print("\n4. Created test_async_modal_execution.py")
    print("   Run it with: python3 test_async_modal_execution.py")

if __name__ == "__main__":
    print("Starting Modal async execution fixes...")
    
    # Apply fixes
    fix_subprocess_runner()
    fix_task_handler_storage()
    verify_modal_monitor_storage()
    create_test_script()
    
    print("\n✅ All fixes applied!")
    print("\nNext steps:")
    print("1. Test with: python3 test_async_modal_execution.py")
    print("2. Monitor logs to verify async execution")
    print("3. Check GCP bucket for stored results")