#!/usr/bin/env python3

import requests
import json
import time

def test_batch_submission():
    print("Testing batch job submission...")
    
    batch_request = {
        "model_id": "boltz2",
        "task_type": "batch_protein_ligand_screening",
        "job_name": "Test Batch Job",
        "use_msa": True,
        "use_potentials": False,
        "input_data": {
            "protein_name": "Test Protein",
            "protein_sequence": "MGQPGNGSPLLAP",
            "ligands": [
                {"name": "Test Ligand 1", "smiles": "CCO"},
                {"name": "Test Ligand 2", "smiles": "CC(C)O"}
            ]
        }
    }
    
    try:
        print("Submitting batch job...")
        response = requests.post("http://localhost:8000/api/v2/predict", json=batch_request, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id')
            
            print(f"Batch job submitted successfully!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            
            time.sleep(5)
            
            print(f"Checking batch status...")
            status_response = requests.get(f"http://localhost:8000/api/v2/jobs/{job_id}/batch-status", timeout=30)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Batch status retrieved:")
                print(f"   Status: {status_data.get('status')}")
                print(f"   Total jobs: {status_data.get('progress', {}).get('total', 0)}")
                print(f"   Running: {status_data.get('progress', {}).get('running', 0)}")
                print(f"   Individual jobs: {len(status_data.get('individual_jobs', []))}")
                
                individual_jobs = status_data.get('individual_jobs', [])
                for job in individual_jobs:
                    job_id_short = job.get('id', 'unknown')
                    modal_call_id = job.get('modal_call_id', 'none')
                    status = job.get('status', 'unknown')
                    print(f"   - Job {job_id_short[:8]}: {status} (Modal: {modal_call_id})")
                
                return job_id
            else:
                print(f"Failed to get batch status: {status_response.status_code}")
                print(f"   Response: {status_response.text}")
        else:
            print(f"Failed to submit batch job: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return None

if __name__ == "__main__":
    test_batch_submission()