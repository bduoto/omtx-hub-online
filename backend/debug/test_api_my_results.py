#!/usr/bin/env python3
"""
Test the My Results API directly
"""

import requests
import json

def test_my_results_api():
    """Test calling the My Results API directly"""
    
    print("\n" + "="*60)
    print("TESTING MY RESULTS API")
    print("="*60)
    
    # Test the API endpoint directly
    try:
        print("1. Testing /api/v2/my-results endpoint...")
        
        url = "http://localhost:8000/api/v2/my-results?user_id=current_user"
        response = requests.get(url, timeout=30)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"   ✅ API Response:")
            print(f"      Total: {data.get('total', 0)}")
            print(f"      Source: {data.get('source', 'unknown')}")
            print(f"      Results: {len(data.get('results', []))}")
            print(f"      User ID: {data.get('user_id', 'unknown')}")
            
            if data.get('results'):
                print(f"   📊 Sample results:")
                for i, result in enumerate(data['results'][:3]):
                    print(f"      {i+1}. ID: {result.get('job_id', 'unknown')}")
                    print(f"         Task: {result.get('task_type', 'unknown')}")
                    print(f"         Status: {result.get('status', 'unknown')}")
                    print(f"         Files: {result.get('file_count', 0)}")
                    print(f"         Name: {result.get('job_name', 'unknown')}")
            else:
                print("   ❌ No results returned")
                
        else:
            print(f"   ❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_my_results_api()