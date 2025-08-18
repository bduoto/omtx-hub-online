#!/usr/bin/env python3
"""
Test frontend compatibility with the My Results API
"""

import json
import requests

def test_frontend_compatibility():
    """Test that the API response works with frontend expectations"""
    
    print("🧪 TESTING FRONTEND COMPATIBILITY")
    print("=" * 40)
    
    # Test frontend proxy
    print("1️⃣ Testing frontend proxy...")
    try:
        response = requests.get("http://localhost:8080/api/v2/my-results?user_id=current_user&limit=2")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: 200 OK")
            print(f"   📊 Results: {data.get('total', 0)}")
            print(f"   📈 Source: {data.get('source', 'unknown')}")
            
            # Check if results can be mapped to frontend format
            if data.get('results'):
                result = data['results'][0]
                
                # Simulate frontend mapping logic
                try:
                    inputs = result.get('inputs', {})
                    protein_name = inputs.get('protein_name') or inputs.get('target_name') or ''
                    job_base_name = result.get('job_name', 'Unknown Prediction')
                    enhanced_name = f"{job_base_name} ({protein_name})" if protein_name else job_base_name
                    
                    mapped_job = {
                        'id': result.get('id'),
                        'name': enhanced_name,
                        'type': result.get('task_type', 'unknown'),
                        'status': result.get('status', 'unknown'),
                        'submitted': result.get('created_at', ''),
                        'original': result
                    }
                    
                    print(f"   ✅ Frontend mapping successful:")
                    print(f"      Name: {mapped_job['name']}")
                    print(f"      Type: {mapped_job['type']}")
                    print(f"      Status: {mapped_job['status']}")
                    
                except Exception as mapping_error:
                    print(f"   ❌ Frontend mapping failed: {mapping_error}")
            
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed - frontend not running?")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test direct backend
    print(f"\n2️⃣ Testing direct backend...")
    try:
        response = requests.get("http://localhost:8000/api/v2/my-results?user_id=current_user&limit=2")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Direct backend working: {data.get('total', 0)} results")
        else:
            print(f"   ❌ Backend error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Backend error: {e}")
    
    print(f"\n✅ Compatibility test complete!")

if __name__ == "__main__":
    test_frontend_compatibility()