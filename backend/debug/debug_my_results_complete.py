#!/usr/bin/env python3
"""
Complete debug of My Results flow
"""

import requests
import json

def debug_complete_flow():
    """Debug the complete My Results flow"""
    
    print("\n" + "="*70)
    print("COMPLETE MY RESULTS DEBUG")
    print("="*70)
    
    # 1. Test API endpoint
    print("\n🌐 Step 1: Testing API endpoint...")
    
    try:
        url = "http://localhost:8000/api/v2/my-results?user_id=current_user"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print(f"✅ API Working:")
            print(f"   Status: {response.status_code}")
            print(f"   Total: {data.get('total', 0)}")
            print(f"   Source: {data.get('source', 'unknown')}")
            print(f"   Results count: {len(results)}")
            
            if results:
                print(f"\n📊 Sample job data:")
                sample = results[0]
                print(f"   ID: {sample.get('id', 'missing')}")
                print(f"   Job ID: {sample.get('job_id', 'missing')}")
                print(f"   Name: {sample.get('job_name', 'missing')}")
                print(f"   Task: {sample.get('task_type', 'missing')}")
                print(f"   Status: {sample.get('status', 'missing')}")
                print(f"   Files: {sample.get('file_count', 0)}")
                print(f"   Has Results: {'results' in sample and bool(sample['results'])}")
                
                # Check results structure
                if sample.get('results'):
                    results_data = sample['results']
                    print(f"   Results keys: {list(results_data.keys())[:5]}")
                    print(f"   Affinity: {results_data.get('affinity', 'N/A')}")
                    print(f"   Confidence: {results_data.get('confidence', 'N/A')}")
                
            return results
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ API Request failed: {e}")
        return []

def test_frontend_compatibility(results):
    """Test if the API data is compatible with frontend expectations"""
    
    print(f"\n🎯 Step 2: Testing frontend compatibility...")
    
    if not results:
        print("❌ No results to test")
        return
    
    # Simulate frontend mapping
    try:
        for i, saved_job in enumerate(results[:2]):
            print(f"\n   Job {i+1} Mapping Test:")
            
            # Check required fields for frontend
            required_fields = ['id', 'job_id', 'task_type', 'job_name', 'status', 'created_at']
            missing_fields = []
            
            for field in required_fields:
                if field not in saved_job or not saved_job[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields present")
            
            # Simulate frontend job row creation
            inputs = saved_job.get('inputs', {})
            protein_name = inputs.get('protein_name', inputs.get('target_name', ''))
            job_base_name = saved_job.get('job_name', f"{saved_job.get('task_type', 'Unknown')} Prediction")
            enhanced_name = f"{job_base_name} ({protein_name})" if protein_name else job_base_name
            
            # Create frontend job object
            frontend_job = {
                'id': saved_job.get('id'),
                'name': enhanced_name,
                'type': saved_job.get('task_type', 'unknown'),
                'status': saved_job.get('status', 'unknown'),
                'submitted': saved_job.get('created_at', 'unknown'),
                'original': saved_job
            }
            
            print(f"   Frontend job created:")
            print(f"      ID: {frontend_job['id']}")
            print(f"      Name: {frontend_job['name']}")
            print(f"      Type: {frontend_job['type']}")
            print(f"      Status: {frontend_job['status']}")
            
    except Exception as e:
        print(f"   ❌ Frontend mapping failed: {e}")

def test_navigation_data(results):
    """Test if data is ready for navigation to results pages"""
    
    print(f"\n🧭 Step 3: Testing navigation data...")
    
    if not results:
        print("❌ No results to test")
        return
    
    sample = results[0]
    
    # Check if we have results data for navigation
    has_results_data = 'results' in sample and sample['results']
    has_job_id = 'job_id' in sample and sample['job_id']
    has_task_type = 'task_type' in sample and sample['task_type']
    
    print(f"   Navigation Requirements:")
    print(f"   ✅ Has job_id: {has_job_id} ({sample.get('job_id', 'missing')})")
    print(f"   ✅ Has task_type: {has_task_type} ({sample.get('task_type', 'missing')})")
    print(f"   ✅ Has results: {has_results_data}")
    
    if has_results_data and has_job_id and has_task_type:
        print(f"   ✅ Ready for navigation to results page!")
        
        # Test navigation payload
        navigation_state = {
            'savedJob': sample,
            'viewMode': True,
            'predictionResult': sample['results'],
            'taskType': sample['task_type']
        }
        
        print(f"   Navigation state prepared with {len(navigation_state)} fields")
    else:
        print(f"   ❌ Missing data for navigation")

if __name__ == "__main__":
    results = debug_complete_flow()
    test_frontend_compatibility(results)
    test_navigation_data(results)
    
    print("\n" + "="*70)
    print("🎯 SUMMARY")
    print("="*70)
    print("If all steps show ✅, the My Results page should work correctly.")
    print("The user may need to refresh their browser to see the jobs.")
    print("="*70)