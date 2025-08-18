#!/usr/bin/env python3
"""
Test batch submission API directly
"""

import requests
import json
import time

def test_batch_submission_api():
    """Test batch submission via API"""
    
    print("🧪 TESTING BATCH SUBMISSION API")
    print("=" * 50)
    
    # Test data
    batch_data = {
        "job_name": f"API Test Batch {int(time.time())}",
        "protein_sequence": "MKLLVLSLSLVLVLLLSHPQGSHM",
        "protein_name": "Test Protein",
        "ligands": [
            {"smiles": "CCO", "name": "Ethanol"},
            {"smiles": "CC(C)O", "name": "Isopropanol"}
        ],
        "model_name": "boltz2",
        "use_msa": True,
        "use_potentials": False
    }
    
    print(f"📝 Submitting batch: {batch_data['job_name']}")
    print(f"📝 Protein: {batch_data['protein_name']}")
    print(f"📝 Ligands: {len(batch_data['ligands'])} compounds")
    
    try:
        # Submit batch
        print("\n🚀 Submitting batch...")
        response = requests.post(
            "http://localhost:8000/api/v3/batches/submit",
            json=batch_data,
            timeout=60
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch submitted successfully!")
            print(f"✅ Batch ID: {result.get('batch_id')}")
            print(f"✅ Total jobs: {result.get('total_jobs', 0)}")
            print(f"✅ Success: {result.get('success', False)}")
            
            if result.get('execution_details'):
                details = result['execution_details']
                print(f"✅ Started jobs: {details.get('started_jobs', 0)}")
                print(f"✅ Failed jobs: {details.get('failed_jobs', 0)}")
            
            return result.get('batch_id')
            
        else:
            print(f"❌ Batch submission failed")
            print(f"❌ Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API error: {e}")
        return None

def test_batch_listing_api():
    """Test batch listing API"""
    
    print("\n🔍 TESTING BATCH LISTING API")
    print("=" * 50)
    
    try:
        # Get batches
        print("🚀 Fetching batches...")
        response = requests.get(
            "http://localhost:8000/api/v3/batches/?user_id=current_user&limit=10",
            timeout=30
        )
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batches retrieved successfully!")
            print(f"✅ Total batches: {result.get('total', 0)}")
            print(f"✅ Returned batches: {len(result.get('batches', []))}")
            
            for i, batch in enumerate(result.get('batches', [])[:3]):
                print(f"📊 Batch {i+1}: {batch.get('name', 'Unknown')}")
                print(f"   Status: {batch.get('status', 'Unknown')}")
                print(f"   Total jobs: {batch.get('total_jobs', 0)}")
                print(f"   Completed: {batch.get('completed_jobs', 0)}")
            
        else:
            print(f"❌ Batch listing failed")
            print(f"❌ Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API error: {e}")

if __name__ == "__main__":
    # Test batch submission
    batch_id = test_batch_submission_api()
    
    # Test batch listing
    test_batch_listing_api()
    
    print("\n" + "=" * 50)
    print("🎯 BATCH API TEST COMPLETED")
    print("=" * 50)
