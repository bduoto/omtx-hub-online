#!/usr/bin/env python3
"""
Check what's actually stored for the trim25 1000 dataset
"""

import os
import sys

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.gcp_database import gcp_database

def check_trim25_1000_results():
    """Check what's actually stored for the trim25 1000 batch"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Checking actual data for batch {batch_id}")
    
    # Get child jobs
    child_jobs_query = (gcp_database.db.collection('jobs')
                       .where('batch_parent_id', '==', batch_id)
                       .limit(10))  # Check first 10 jobs
    
    child_jobs_docs = list(child_jobs_query.stream())
    print(f"📊 Found {len(child_jobs_docs)} child jobs")
    
    jobs_with_data = 0
    jobs_without_data = 0
    
    for doc in child_jobs_docs:
        job_data = doc.to_dict()
        job_id = doc.id
        
        # Check for results using the same logic as reconstruction
        has_results = bool(
            job_data.get('has_results') or
            job_data.get('output_data', {}).get('results') or
            job_data.get('results') or
            job_data.get('output_data', {}).get('raw_modal_result') or
            (job_data.get('status') == 'completed' and job_data.get('output_data', {}).get('has_results'))
        )
        
        if has_results:
            jobs_with_data += 1
            print(f"\n✅ Job {job_id[:8]} HAS RESULTS:")
            print(f"   Status: {job_data.get('status')}")
            print(f"   Has_results: {job_data.get('has_results')}")
            
            # Check results structure
            results = job_data.get('results')
            if results:
                print(f"   Results keys: {list(results.keys())[:5]}")
                print(f"   Affinity: {results.get('affinity')}")
                print(f"   Confidence: {results.get('confidence')}")
            
            output_data = job_data.get('output_data', {})
            if output_data.get('results'):
                output_results = output_data.get('results')
                print(f"   Output results keys: {list(output_results.keys())[:5]}")
                print(f"   Output affinity: {output_results.get('affinity')}")
            
        else:
            jobs_without_data += 1
            print(f"\n❌ Job {job_id[:8]} NO RESULTS:")
            print(f"   Status: {job_data.get('status')}")
            print(f"   Has_results: {job_data.get('has_results')}")
            print(f"   Output_data keys: {list(job_data.get('output_data', {}).keys())}")
    
    print(f"\n📈 Summary of first 10 jobs:")
    print(f"   Jobs with data: {jobs_with_data}")
    print(f"   Jobs without data: {jobs_without_data}")

if __name__ == "__main__":
    check_trim25_1000_results()