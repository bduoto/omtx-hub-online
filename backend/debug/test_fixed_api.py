#!/usr/bin/env python3
"""
Test the fixed API
"""

import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, '/Users/bryanduoto/Desktop/omtx-hub/backend')

# Import and run the API directly
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.unified_endpoints import router

app = FastAPI()
app.include_router(router, prefix="/api/v2")

client = TestClient(app)

def test_batch_api():
    """Test the batch API"""
    print("🧪 Testing fixed batch API...\n")
    
    request_body = {
        "model_id": "boltz2",
        "task_type": "batch_protein_ligand_screening",
        "input_data": {
            "protein_name": "Test Protein",
            "protein_sequence": "MKFLVNVALVFMVVYISYIYA",
            "ligands": [
                {"name": "Ethanol", "smiles": "CCO"},
                {"name": "Methanol", "smiles": "CO"}
            ],
            "use_msa": True,
            "use_potentials": False
        },
        "job_name": "Test Batch Job",
        "use_msa": True,
        "use_potentials": False
    }
    
    response = client.post("/api/v2/predict", json=request_body)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result}")
        print(f"\n✅ SUCCESS! API returns immediately!")
        print(f"Job ID: {result.get('job_id')}")
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_batch_api()