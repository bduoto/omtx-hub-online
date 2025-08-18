#!/usr/bin/env python3
"""
Check what files exist in GCP storage for the trim25 1000 batch
"""

import os
import sys

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gcp_storage_service import gcp_storage_service

def check_gcp_batch_files():
    """Check what files exist in GCP storage for the batch"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Checking GCP storage for batch {batch_id}")
    
    # Check for batch results.json
    try:
        batch_results_path = f"batches/{batch_id}/batch_results.json"
        batch_results_data = gcp_storage_service.storage.download_file(batch_results_path)
        if batch_results_data:
            print(f"✅ Found batch_results.json ({len(batch_results_data)} bytes)")
            
            # Parse and check contents
            import json
            if isinstance(batch_results_data, bytes):
                batch_results_data = batch_results_data.decode('utf-8')
            batch_results = json.loads(batch_results_data)
            
            print(f"   Individual results: {len(batch_results.get('individual_results', []))}")
            print(f"   Summary: {batch_results.get('summary', {}).keys()}")
            
            # Check a few individual results
            individual_results = batch_results.get('individual_results', [])
            if individual_results:
                print(f"\n📊 Sample results:")
                for i, result in enumerate(individual_results[:3]):
                    print(f"   {i+1}. Ligand: {result.get('ligand_name')} - Affinity: {result.get('affinity')} - Status: {result.get('status')}")
            
        else:
            print(f"❌ No batch_results.json found")
    except Exception as e:
        print(f"❌ Error accessing batch_results.json: {e}")
    
    # Check for individual job files
    try:
        jobs_path = f"batches/{batch_id}/jobs/"
        print(f"\n🔍 Checking for individual job files under {jobs_path}")
        
        # Try to list some job directories (this is a simple test)
        test_job_ids = [
            "c15ce144-0aaa-404d-baed-801c80823567",  # First job from API
            "8f36e661-836f-4c82-8f21-ce121a94c38f",  # Second job from API
        ]
        
        for job_id in test_job_ids:
            job_results_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
            try:
                job_results = gcp_storage_service.storage.download_file(job_results_path)
                if job_results:
                    print(f"   ✅ Found results for job {job_id[:8]}")
                else:
                    print(f"   ❌ No results for job {job_id[:8]}")
            except Exception as e:
                print(f"   ❌ Error checking job {job_id[:8]}: {e}")
                
    except Exception as e:
        print(f"❌ Error checking job files: {e}")

if __name__ == "__main__":
    check_gcp_batch_files()