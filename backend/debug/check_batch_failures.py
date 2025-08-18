#!/usr/bin/env python3
import requests
import json

# Get batch status
response = requests.get("http://localhost:8000/api/v2/jobs/TGOGyJaXoNav3C2lQAEV/batch-status")
if response.status_code == 200:
    data = response.json()
    
    print(f"Batch status: {data['status']}")
    print(f"Total jobs: {data['progress']['total']}")
    print(f"Failed jobs: {data['progress']['failed']}")
    
    # Check a few individual jobs
    for i, job in enumerate(data['individual_jobs'][:3]):
        job_id = job['id']
        print(f"\n{i+1}. Job {job_id}:")
        print(f"   Status: {job['status']}")
        print(f"   Name: {job.get('name', 'unknown')}")
        
        # Get full job details
        job_response = requests.get(f"http://localhost:8000/api/v2/jobs/{job_id}")
        if job_response.status_code == 200:
            job_details = job_response.json()
            if job_details.get('error_message'):
                print(f"   Error: {job_details['error_message']}")
            if job_details.get('result_data'):
                result = job_details['result_data']
                if isinstance(result, dict) and result.get('error'):
                    print(f"   Result Error: {result['error']}")
                if isinstance(result, dict) and result.get('error_message'):
                    print(f"   Error Message: {result['error_message']}")
        else:
            print(f"   Could not get job details: {job_response.status_code}")