#!/usr/bin/env python3
"""
Test the API endpoint directly to find the hang
"""

import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.testclient import TestClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the actual API endpoint
import sys
sys.path.insert(0, '/Users/bryanduoto/Desktop/omtx-hub/backend')
from api.unified_endpoints import router, process_prediction_task

# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v2")

# Create test client
client = TestClient(app)

def test_batch_submission():
    """Test batch submission through actual API"""
    print("🧪 Testing API endpoint directly...\n")
    
    # Test data
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
    
    print("📤 Sending request to /api/v2/predict")
    print(f"Body: {json.dumps(request_body, indent=2)}")
    
    # Make the request with a timeout
    import time
    start_time = time.time()
    
    try:
        # Use a shorter timeout to catch hangs
        response = client.post(
            "/api/v2/predict",
            json=request_body,
            timeout=10.0  # 10 second timeout
        )
        
        elapsed = time.time() - start_time
        print(f"\n📥 Response received in {elapsed:.2f}s")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        
        if elapsed > 5:
            print("\n⚠️ WARNING: API took too long to respond")
            print("This would timeout in production!")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ Request failed after {elapsed:.2f}s")
        print(f"Error: {e}")
        
        if "timeout" in str(e).lower():
            print("\n🔍 DIAGNOSIS: API is hanging")
            print("The background task is likely blocking the response")

async def test_background_task_directly():
    """Test the background task directly"""
    print("\n\n🧪 Testing background task directly...\n")
    
    job_id = "test-direct-batch"
    
    # Test the actual background task function
    await process_prediction_task(
        job_id=job_id,
        task_type="batch_protein_ligand_screening",
        input_data={
            "protein_name": "Test Protein",
            "protein_sequence": "MKFLVNVALVFMVVYISYIYA",
            "ligands": [
                {"name": "Ethanol", "smiles": "CCO"},
                {"name": "Methanol", "smiles": "CO"}
            ],
            "use_msa": True,
            "use_potentials": False
        },
        job_name="Test Direct",
        use_msa=True,
        use_potentials=False
    )
    
    print("✅ Background task completed")

if __name__ == "__main__":
    # Test 1: Through API
    test_batch_submission()
    
    # Test 2: Direct background task
    print("\n" + "=" * 60)
    asyncio.run(test_background_task_directly())