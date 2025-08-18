#!/usr/bin/env python3
"""
Debug batch results structure to see actual comprehensive fields
"""

import os
import sys
import json

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_batch_results_structure():
    """Debug the batch results structure"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Debugging batch results structure for {batch_id}")
    
    try:
        from services.gcp_storage_service import gcp_storage_service
        
        # Download the batch_results.json file
        batch_results_path = f"batches/{batch_id}/batch_results.json"
        batch_results_data = gcp_storage_service.storage.download_file(batch_results_path)
        
        if not batch_results_data:
            print(f"❌ Could not find batch_results.json at {batch_results_path}")
            return False
        
        if isinstance(batch_results_data, bytes):
            batch_results_data = batch_results_data.decode('utf-8')
        
        batch_results = json.loads(batch_results_data)
        
        print(f"📋 Batch results top-level keys: {list(batch_results.keys())}")
        
        # Look at jobs (the actual key in parent-level batch results)
        jobs = batch_results.get('jobs', [])
        print(f"📊 Found {len(jobs)} jobs")
        
        # Find first job with completed status and actual data
        completed_job = None
        for job in jobs:
            if job.get('has_results') and job.get('affinity') and job.get('affinity') != 0:
                completed_job = job
                break
        
        if completed_job:
            print(f"\n📋 COMPLETED JOB STRUCTURE FOR {completed_job['job_id'][:8]}:")
            print(f"   All keys: {list(completed_job.keys())}")
            
            # Check comprehensive fields specifically
            comprehensive_fields = [
                'affinity_prob', 'ens_affinity', 'ens_prob', 'ens_aff_2', 'ens_prob_2', 
                'ens_aff_1', 'ens_prob_1', 'iptm_score', 'ligand_iptm', 'complex_iplddt', 
                'complex_ipde', 'complex_plddt', 'ptm_score', 'plddt_score'
            ]
            
            print(f"\n📈 COMPREHENSIVE FIELDS IN BATCH_RESULTS.JSON:")
            for field in comprehensive_fields:
                value = completed_job.get(field)
                print(f"   {field}: {value} ({type(value).__name__})")
            
            # Check raw_modal_result structure
            raw_modal = completed_job.get('raw_modal_result', {})
            print(f"\n📋 raw_modal_result keys: {list(raw_modal.keys()) if raw_modal else 'None'}")
            
            if raw_modal:
                # Check affinity_ensemble and confidence_metrics
                affinity_ensemble = raw_modal.get('affinity_ensemble', {})
                confidence_metrics = raw_modal.get('confidence_metrics', {})
                
                print(f"\n📋 affinity_ensemble: {affinity_ensemble} ({type(affinity_ensemble).__name__})")
                print(f"📋 confidence_metrics: {confidence_metrics} ({type(confidence_metrics).__name__})")
                
                if isinstance(affinity_ensemble, dict):
                    print(f"   affinity_ensemble keys: {list(affinity_ensemble.keys())}")
                
                if isinstance(confidence_metrics, dict):
                    print(f"   confidence_metrics keys: {list(confidence_metrics.keys())}")
        else:
            print(f"❌ No completed jobs with actual data found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_batch_results_structure()