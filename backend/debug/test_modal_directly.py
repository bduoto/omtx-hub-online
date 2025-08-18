#!/usr/bin/env python3
import requests
import json

def test_modal_completion():
    """Test if the Modal monitor can detect completed jobs"""
    
    print("🔍 Testing Modal job completion detection...")
    
    # Get jobs with Modal call IDs
    response = requests.get("http://localhost:8000/api/v2/jobs/status/running")
    if response.status_code != 200:
        print(f"❌ Failed to get running jobs: {response.status_code}")
        return
    
    data = response.json()
    print(f"Running jobs found: {data['count']}")
    
    # Find jobs with Modal call IDs
    jobs_with_modal_ids = []
    for job in data['jobs'][:10]:  # Check first 10
        if job.get('type') == 'protein_ligand_binding':
            # Get job details
            job_response = requests.get(f"http://localhost:8000/api/v2/jobs/{job['id']}")
            if job_response.status_code == 200:
                job_details = job_response.json()
                modal_id = None
                
                # Check for Modal call ID
                if job_details.get('result_data'):
                    modal_id = job_details['result_data'].get('modal_call_id')
                
                if modal_id:
                    jobs_with_modal_ids.append({
                        'job_id': job['id'],  
                        'modal_call_id': modal_id,
                        'name': job.get('name', 'unknown')
                    })
    
    print(f"Jobs with Modal call IDs: {len(jobs_with_modal_ids)}")
    
    if jobs_with_modal_ids:
        for job in jobs_with_modal_ids[:3]:
            print(f"Job: {job['job_id']} -> Modal: {job['modal_call_id']}")
    
    # Trigger batch processing to force Modal monitor to run
    print("\n🚀 Triggering batch processing...")
    trigger_response = requests.post("http://localhost:8000/api/v2/trigger-batch-processing")
    if trigger_response.status_code == 200:
        print("✅ Batch processing triggered")
        
        # Wait a moment then check if any jobs changed status
        import time
        time.sleep(5)
        
        print("\n🔍 Checking for status changes...")
        for job in jobs_with_modal_ids[:3]:
            job_response = requests.get(f"http://localhost:8000/api/v2/jobs/{job['job_id']}")
            if job_response.status_code == 200:
                job_data = job_response.json()
                print(f"Job {job['job_id']}: {job_data.get('status', 'unknown')}")
                if job_data.get('result_data', {}).get('files_stored_to_gcp'):
                    print(f"  ✅ Files stored to GCP")
                else:
                    print(f"  ❌ No GCP storage flag")
    else:
        print(f"❌ Failed to trigger batch processing: {trigger_response.status_code}")

if __name__ == "__main__":
    test_modal_completion()