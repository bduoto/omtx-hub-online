#!/usr/bin/env python3
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
    
    print("\n" + "="*60)
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
    
    print(f"\n📊 Initial result:")
    print(f"   Status: {result.get('status')}")
    print(f"   Modal Call ID: {result.get('modal_call_id')}")
    
    if result.get('status') == 'running':
        print("\n✅ Async execution started successfully!")
        
        # Wait a bit then check monitor
        print("\n⏳ Waiting 10 seconds then checking monitor...")
        await asyncio.sleep(10)
        
        # Run monitor check
        await modal_monitor.check_and_update_jobs()
        
        # Check job status
        job = unified_job_manager.get_job(created_job_id)
        print(f"\n📊 Job status after monitor check: {job.get('status')}")
        
        # Check GCP storage
        job_files = gcp_storage.list_job_files(created_job_id)
        print(f"\n📁 Files in GCP storage: {len(job_files)}")
        for file in job_files:
            print(f"   - {file['name']}")
    else:
        print("\n❌ Job did not start async execution")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_async_modal_execution())
