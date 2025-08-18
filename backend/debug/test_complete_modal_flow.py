#!/usr/bin/env python3
"""
Complete test of Modal prediction flow with GCP storage
Tests submission, async execution, monitoring, and storage
"""

import asyncio
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable some verbose loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('google').setLevel(logging.WARNING)

async def main():
    """Run complete Modal flow test"""
    
    print("\n" + "="*80)
    print("COMPLETE MODAL PREDICTION FLOW TEST")
    print("="*80)
    
    # Import after logging is configured
    from database.unified_job_manager import unified_job_manager
    from api.unified_endpoints import predict_unified
    from services.modal_monitor import modal_monitor
    from config.gcp_storage import gcp_storage
    from pydantic import BaseModel
    from typing import Dict, Any, Optional
    from enum import Enum
    
    # Define request models to match API
    class TaskType(str, Enum):
        PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    
    class PredictionRequest(BaseModel):
        model_id: str = "boltz2"
        task_type: TaskType
        input_data: Dict[str, Any]
        job_name: Optional[str] = None
        use_msa: bool = True
        use_potentials: bool = False
    
    # 1. Test API submission
    print("\n1. Testing API submission...")
    
    request = PredictionRequest(
        model_id="boltz2",
        task_type=TaskType.PROTEIN_LIGAND_BINDING,
        input_data={
            "protein_sequence": "MGQPGNGSAFLLAPNGSHAPDHDVTQERDEVWVVGMGIVMSLIVLAIVFGNVLVITAIAKFERLQTVTNYFITSLACADLVMGLAVVPFGAAHILMKMWTFGNFWCEFWTSIDVLCVTASIETLCVIAVDRYFAITSPFKYQSLLTKNKARVIILMVWIVSGLTSFLPIQMHWYRATHQEAINCYANETCCDFFTNQAYAIASSIVSFYVPLVIMVFVYSRVFQEAKRQLQKIDKSEGRFHVQNLSQVEQDGRTGHGLRRSSKFCLKEHKALKTLGIIMGTFTLCWLPFFIVNIVHVIQDNLIRKEVYILLNWIGYVNSGFNPLIYCRSPDFRIAFQELLCLRRSSLKAYGNGYSSNGNTGEQSGYHVEQEKENKLLCEDLPGTEDFVGHQGTVPSDNIDSQGRNCSTNDSLL",
            "ligand_smiles": "CNCC(O)c1ccc(O)c(O)c1",
            "protein_name": "test_beta2_adrenergic"
        },
        job_name="Complete Flow Test",
        use_msa=False,
        use_potentials=True
    )
    
    # Create mock background tasks
    class MockBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            # Start task in background
            asyncio.create_task(func(*args, **kwargs))
    
    background_tasks = MockBackgroundTasks()
    
    try:
        # Call the API endpoint directly
        response = await predict_unified(request, background_tasks)
        
        print(f"✅ API Response:")
        print(f"   Job ID: {response.job_id}")
        print(f"   Status: {response.status}")
        print(f"   Message: {response.message}")
        
        job_id = response.job_id
        
    except Exception as e:
        print(f"❌ API submission failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Check job record
    print("\n2. Checking job record...")
    await asyncio.sleep(2)  # Give background task time to start
    
    job = unified_job_manager.get_job(job_id)
    if job:
        print(f"✅ Job found in database:")
        print(f"   Status: {job.get('status')}")
        print(f"   Type: {job.get('type')}")
        
        # Check for Modal call ID
        results = job.get('results', {})
        modal_call_id = results.get('modal_call_id')
        if modal_call_id:
            print(f"   Modal Call ID: {modal_call_id}")
        else:
            print("   ⚠️  No Modal call ID found yet")
    else:
        print("❌ Job not found in database!")
        return
    
    # 3. Wait and run monitor
    print("\n3. Waiting for Modal execution and running monitor...")
    print("   ⏳ Waiting 30 seconds for Modal to process...")
    await asyncio.sleep(30)
    
    # Run modal monitor
    print("   🔍 Running modal monitor check...")
    await modal_monitor.check_and_update_jobs()
    
    # 4. Check job status after monitoring
    print("\n4. Checking job status after monitoring...")
    job = unified_job_manager.get_job(job_id)
    if job:
        print(f"✅ Job status: {job.get('status')}")
        
        if job.get('status') == 'completed':
            print("   🎉 Job completed successfully!")
        elif job.get('status') == 'running':
            print("   ⏳ Job still running, may need more time")
        else:
            print(f"   ⚠️  Unexpected status: {job.get('status')}")
    
    # 5. Check GCP storage
    print("\n5. Checking GCP storage for results...")
    
    if gcp_storage.available:
        job_files = gcp_storage.list_job_files(job_id)
        
        if job_files:
            print(f"✅ Found {len(job_files)} files in GCP:")
            for file in job_files:
                print(f"   - {file['name']} ({file['size']} bytes)")
            
            # Check for key files
            file_names = [f['name'] for f in job_files]
            expected_files = ['structure.cif', 'results.json', 'metadata.json']
            
            for expected in expected_files:
                if expected in file_names:
                    print(f"   ✅ {expected} present")
                else:
                    print(f"   ❌ {expected} missing")
            
            # Try to read results.json
            results_content = gcp_storage.download_file(f"jobs/{job_id}/results.json")
            if results_content:
                results_data = json.loads(results_content.decode('utf-8'))
                print("\n   📊 Results data sample:")
                print(f"      Affinity: {results_data.get('affinity', 'N/A')}")
                print(f"      Confidence: {results_data.get('confidence', 'N/A')}")
                print(f"      Structure files: {len(results_data.get('all_structures', []))}")
        else:
            print("❌ No files found in GCP storage")
            print("   This may indicate the results weren't stored properly")
    else:
        print("❌ GCP storage not available")
    
    # 6. Test retrieval via API
    print("\n6. Testing result retrieval via API...")
    
    from api.unified_endpoints import get_job_status
    try:
        job_status = await get_job_status(job_id)
        print(f"✅ Job status from API:")
        print(f"   Status: {job_status.status}")
        print(f"   Has result data: {'result_data' in job_status.dict()}")
        
        if job_status.result_data:
            print(f"   Result keys: {list(job_status.result_data.keys())[:5]}...")
    except Exception as e:
        print(f"❌ Failed to get job status: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
    # Summary
    print("\nSUMMARY:")
    if job and job.get('status') == 'completed' and job_files:
        print("✅ Full flow working correctly!")
        print("   - Job submitted successfully")
        print("   - Modal execution tracked")
        print("   - Results stored to GCP")
        print("   - Results retrievable via API")
    else:
        print("⚠️  Some issues detected:")
        if not job:
            print("   - Job not found in database")
        elif job.get('status') != 'completed':
            print(f"   - Job status is '{job.get('status')}', not 'completed'")
        if not job_files:
            print("   - No files found in GCP storage")

if __name__ == "__main__":
    print("Starting complete Modal flow test...")
    asyncio.run(main())