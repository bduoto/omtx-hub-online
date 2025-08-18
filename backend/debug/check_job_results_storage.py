#!/usr/bin/env python3
"""
Check how job results are being stored in the database
"""

import os
import sys
from datetime import datetime

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.gcp_database import gcp_database
from database.unified_job_manager import unified_job_manager

def check_job_storage():
    """Check how job results are being stored for the 300 ligand batch"""
    
    batch_id = "aeb49e8f-f117-4834-bb73-9d7216a7ef95"
    
    print(f"🔍 Checking job storage for batch {batch_id}")
    
    # Get child jobs
    child_jobs_query = (gcp_database.db.collection('jobs')
                       .where('batch_parent_id', '==', batch_id)
                       .limit(5))  # Just check first 5 jobs
    
    child_jobs_docs = list(child_jobs_query.stream())
    print(f"📊 Found {len(child_jobs_docs)} child jobs")
    
    for doc in child_jobs_docs:
        job_data = doc.to_dict()
        job_id = doc.id
        
        print(f"\n🔧 Job {job_id[:8]}:")
        print(f"   Status: {job_data.get('status')}")
        print(f"   Has completed_at: {bool(job_data.get('completed_at'))}")
        print(f"   Has has_results: {job_data.get('has_results')}")
        print(f"   Has results: {bool(job_data.get('results'))}")
        print(f"   Has output_data: {bool(job_data.get('output_data'))}")
        
        # Check output_data contents
        output_data = job_data.get('output_data', {})
        if output_data:
            print(f"   Output data keys: {list(output_data.keys())}")
            print(f"   Output has_results: {output_data.get('has_results')}")
            print(f"   Output results: {bool(output_data.get('results'))}")
            print(f"   Output raw_modal_result: {bool(output_data.get('raw_modal_result'))}")
        
        # Check if results are stored directly in job
        results = job_data.get('results')
        if results:
            print(f"   Results type: {type(results)}")
            if isinstance(results, dict):
                print(f"   Results keys: {list(results.keys())}")
                print(f"   Has affinity: {bool(results.get('affinity'))}")
                print(f"   Has structure: {bool(results.get('structure_file_base64'))}")
        else:
            print(f"   No results found in job data")
            
        # Check various result storage patterns
        patterns_found = []
        
        if job_data.get('has_results'):
            patterns_found.append("has_results=True")
        if job_data.get('results'):
            patterns_found.append("direct results field")
        if output_data.get('results'):
            patterns_found.append("output_data.results")
        if output_data.get('raw_modal_result'):
            patterns_found.append("output_data.raw_modal_result")
        if job_data.get('status') == 'completed':
            patterns_found.append("status=completed")
            
        print(f"   Patterns found: {patterns_found}")
        
        # Calculate has_results using the reconstruction logic
        has_results_calc = bool(
            job_data.get('has_results') or
            job_data.get('output_data', {}).get('results') or
            job_data.get('results') or
            job_data.get('output_data', {}).get('raw_modal_result') or
            (job_data.get('status') == 'completed' and job_data.get('output_data', {}).get('has_results'))
        )
        
        print(f"   Calculated has_results: {has_results_calc}")

if __name__ == "__main__":
    check_job_storage()