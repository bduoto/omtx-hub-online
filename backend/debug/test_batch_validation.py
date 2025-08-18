#!/usr/bin/env python3
"""
Test batch screening validation
"""

import json
import requests

def test_batch_screening():
    """Test batch screening with the exact frontend payload"""
    
    print("🔍 TESTING BATCH SCREENING VALIDATION")
    print("=" * 50)
    
    # Prepare request matching frontend
    request_data = {
        "model_id": "boltz2",
        "task_type": "batch_protein_ligand_screening",
        "input_data": {
            "protein_name": "Carbonic Anhydrase II",
            "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",
            "ligands": [
                {"name": "Ligand1", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
                {"name": "Ligand2", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"}
            ],
            "use_msa": True,
            "use_potentials": False
        },
        "job_name": "TestBatch123",
        "use_msa": True,
        "use_potentials": False
    }
    
    print("📋 Request data:")
    print(json.dumps(request_data, indent=2))
    
    try:
        # Send request
        response = requests.post(
            "http://localhost:8000/api/v2/predict",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: Job ID: {result.get('job_id')}")
            print(f"📋 Full response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"📋 Error response: {response.text}")
            
            # Try to parse error details
            try:
                error_data = response.json()
                if "detail" in error_data:
                    print(f"\n🔍 Error detail: {error_data['detail']}")
            except:
                pass
                
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_screening()