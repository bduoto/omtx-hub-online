#!/usr/bin/env python3
"""
Check a specific job that should have completed results
"""

import os
import sys

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.gcp_database import gcp_database

def check_specific_job():
    """Check a specific job that showed completed_at in the API"""
    
    # Job from API that showed completed_at: "2025-08-15T12:07:34.092876"
    job_id = "9d07765d-75ca-481c-8e2b-c7595f078651"  # Job 296
    
    print(f"🔍 Checking specific job {job_id}")
    
    # Get job from database
    job_ref = gcp_database.db.collection('jobs').document(job_id)
    job_doc = job_ref.get()
    
    if not job_doc.exists:
        print(f"❌ Job {job_id} not found in database")
        return
    
    job_data = job_doc.to_dict()
    
    print(f"\n📋 Job Data Analysis:")
    print(f"   ID: {job_id}")
    print(f"   Name: {job_data.get('name')}")
    print(f"   Status: {job_data.get('status')}")
    print(f"   Job Type: {job_data.get('job_type')}")
    print(f"   Task Type: {job_data.get('task_type')}")
    print(f"   Batch Parent: {job_data.get('batch_parent_id')}")
    
    # Check timestamps
    print(f"\n⏰ Timestamps:")
    print(f"   Created: {job_data.get('created_at')}")
    print(f"   Updated: {job_data.get('updated_at')}")
    print(f"   Started: {job_data.get('started_at')}")
    print(f"   Completed: {job_data.get('completed_at')}")
    
    # Check all possible result locations
    print(f"\n🔍 Result Storage Analysis:")
    print(f"   has_results (root): {job_data.get('has_results')}")
    print(f"   results (root): {bool(job_data.get('results'))}")
    print(f"   output_data exists: {bool(job_data.get('output_data'))}")
    
    output_data = job_data.get('output_data', {})
    if output_data:
        print(f"   output_data keys: {list(output_data.keys())}")
        print(f"   output_data.has_results: {output_data.get('has_results')}")
        print(f"   output_data.results: {bool(output_data.get('results'))}")
        print(f"   output_data.raw_modal_result: {bool(output_data.get('raw_modal_result'))}")
        print(f"   output_data.files_stored_to_gcp: {output_data.get('files_stored_to_gcp')}")
        
        # Check for modal call ID
        print(f"   modal_call_id: {output_data.get('modal_call_id')}")
    
    # Check if there are any results fields
    results = job_data.get('results')
    if results:
        print(f"\n📊 Results Found:")
        print(f"   Results type: {type(results)}")
        if isinstance(results, dict):
            print(f"   Results keys: {list(results.keys())[:10]}")  # First 10 keys
    
    # Check the current completion status according to reconstruction logic
    has_results_calc = bool(
        job_data.get('has_results') or
        job_data.get('output_data', {}).get('results') or
        job_data.get('results') or
        job_data.get('output_data', {}).get('raw_modal_result') or
        (job_data.get('status') == 'completed' and job_data.get('output_data', {}).get('has_results'))
    )
    
    print(f"\n🎯 Reconstruction Logic Result:")
    print(f"   Would be included in results: {has_results_calc}")
    
    # Print the full job data for this specific job (truncated)
    print(f"\n📄 Full Job Data (keys):")
    all_keys = sorted(job_data.keys())
    print(f"   {all_keys}")

if __name__ == "__main__":
    check_specific_job()