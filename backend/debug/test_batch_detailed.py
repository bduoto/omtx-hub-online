#!/usr/bin/env python3
"""
Detailed test of batch screening to find the exact issue
"""

import json
import requests
import time

# Test the fixed validation
request_data = {
    "model_id": "boltz2",
    "task_type": "batch_protein_ligand_screening",
    "input_data": {
        "protein_name": "Carbonic Anhydrase II",
        "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
        "ligands": [
            {"name": "Ligand1", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}
        ],
        "use_msa": True,
        "use_potentials": False
    },
    "job_name": "DetailedTest",
    "use_msa": True,
    "use_potentials": False
}

print("🚀 Sending minimal batch screening request...")
print(f"📋 Request: {json.dumps(request_data, indent=2)}")

try:
    start_time = time.time()
    response = requests.post(
        "http://localhost:8000/api/v2/predict",
        json=request_data,
        headers={"Content-Type": "application/json"},
        timeout=30  # 30 second timeout
    )
    
    elapsed = time.time() - start_time
    print(f"⏱️ Response time: {elapsed:.2f}s")
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS - Job submitted!")
        print(f"📋 Response: {json.dumps(result, indent=2)}")
        
        # If we get a job_id, check its status
        if 'job_id' in result:
            job_id = result['job_id']
            print(f"\n🔍 Checking job status for: {job_id}")
            time.sleep(2)
            
            status_response = requests.get(f"http://localhost:8000/api/v2/jobs/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"📊 Job status: {json.dumps(status_data, indent=2)}")
    else:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"📋 Error response: {response.text}")
        
except requests.exceptions.Timeout:
    print("⏱️ Request timeout after 30 seconds")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()