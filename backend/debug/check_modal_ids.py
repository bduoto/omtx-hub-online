#!/usr/bin/env python3
import requests
import json

# Get running jobs
response = requests.get("http://localhost:8000/api/v2/jobs/status/running")
if response.status_code == 200:
    data = response.json()
    print(f"Running jobs: {data['count']}")
    
    # Check first few running jobs for modal_call_id
    for job in data['jobs'][:5]:
        job_id = job['id']
        job_type = job.get('type', 'unknown')
        
        # Skip non-prediction jobs
        if job_type not in ['protein_ligand_binding', 'batch_protein_ligand_screening']:
            continue
            
        print(f"\nJob {job_id}:")
        print(f"  Type: {job_type}")
        print(f"  Name: {job.get('name', 'unknown')}")
        
        # Check for modal_call_id in different places
        modal_id = None
        if job.get('modal_call_id'):
            modal_id = job['modal_call_id']
            print(f"  Modal ID (top level): {modal_id}")
        
        if job.get('results'):
            results = job['results']
            if results.get('modal_call_id'):
                modal_id = results['modal_call_id']
                print(f"  Modal ID (in results): {modal_id}")
        
        if job.get('output_data'):
            output = job['output_data']
            if output.get('modal_call_id'):
                modal_id = output['modal_call_id']
                print(f"  Modal ID (in output_data): {modal_id}")
        
        if not modal_id:
            print("  Modal ID: NOT FOUND - This job won't be monitored!")