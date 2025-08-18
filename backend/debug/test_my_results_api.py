#!/usr/bin/env python3
"""
Test the My Results API to ensure it's working properly with the updated frontend
"""

import asyncio
import json
import requests
from datetime import datetime

async def test_my_results_api():
    """Test the My Results API endpoint"""
    
    print("🧪 Testing My Results API functionality...\n")
    
    base_url = "http://localhost:8002"  # Update if your backend runs on different port
    
    # Test 1: Check if the API endpoint exists
    print("1️⃣ Testing API endpoint availability...")
    try:
        response = requests.get(f"{base_url}/api/v2/my-results?user_id=current_user")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API endpoint is working")
            print(f"   📊 Total results: {data.get('total', 0)}")
            print(f"   📋 Results count: {len(data.get('results', []))}")
            
            # Test 2: Check data structure
            results = data.get('results', [])
            if results:
                print(f"\n2️⃣ Testing data structure...")
                sample_result = results[0]
                required_fields = ['id', 'job_id', 'task_type', 'job_name', 'status', 'created_at', 'user_id']
                missing_fields = []
                
                for field in required_fields:
                    if field not in sample_result:
                        missing_fields.append(field)
                    else:
                        print(f"   ✅ {field}: {sample_result.get(field)}")
                
                if missing_fields:
                    print(f"   ❌ Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ All required fields present")
                
                # Test 3: Check if inputs/results are properly structured
                print(f"\n3️⃣ Testing inputs/results structure...")
                inputs = sample_result.get('inputs', {})
                results_data = sample_result.get('results', {})
                
                print(f"   📝 Inputs keys: {list(inputs.keys())}")
                print(f"   📈 Results keys: {list(results_data.keys())}")
                
                # Check for protein_name/target_name in inputs
                protein_name = inputs.get('protein_name') or inputs.get('target_name')
                if protein_name:
                    print(f"   ✅ Protein/Target name found: {protein_name}")
                else:
                    print(f"   ⚠️ No protein_name or target_name in inputs")
                
            print(f"\n4️⃣ Testing task type variety...")
            task_types = set(result.get('task_type') for result in results)
            print(f"   📊 Task types found: {list(task_types)}")
            
            # Test task type mapping (simulate frontend logic)
            task_type_mapping = {
                'protein_ligand_binding': 'Boltz-2 Protein-Ligand',
                'protein_structure': 'Boltz-2 Protein Structure',
                'batch_protein_ligand_screening': 'Batch Protein-Ligand Screening',
                'nanobody_design': 'RFAntibody Nanobody Design',
                'structure_prediction': 'Chai-1 Structure Prediction',
            }
            
            for task_type in task_types:
                display_name = task_type_mapping.get(task_type, task_type.replace('_', ' ').title())
                print(f"   🏷️ {task_type} → {display_name}")
                
        else:
            print(f"   ❌ API endpoint failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to backend at {base_url}")
        print(f"   💡 Make sure the backend server is running")
    except Exception as e:
        print(f"   ❌ Error testing API: {e}")
    
    # Test 5: Test deletion endpoint (check if it exists)
    print(f"\n5️⃣ Testing deletion endpoint...")
    try:
        # Don't actually delete, just check if endpoint exists with invalid ID
        response = requests.delete(f"{base_url}/api/v2/my-results/test-id?user_id=current_user")
        if response.status_code in [404, 400]:
            print(f"   ✅ Deletion endpoint exists (returned {response.status_code} as expected)")
        else:
            print(f"   ⚠️ Deletion endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing deletion endpoint: {e}")
    
    print(f"\n✅ My Results API test complete!")
    return True

if __name__ == "__main__":
    asyncio.run(test_my_results_api())