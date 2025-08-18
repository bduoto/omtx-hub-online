#!/usr/bin/env python3
"""
Test the complete My Results flow end-to-end
"""

import asyncio
import json
import requests
from config.gcp_storage import gcp_storage

async def test_complete_flow():
    """Test the complete My Results flow"""
    
    print("\n" + "="*70)
    print("TESTING COMPLETE MY RESULTS FLOW")
    print("="*70)
    
    # 1. Check GCP bucket for jobs
    print("\n🔍 Step 1: Check GCP bucket for stored jobs...")
    
    if not gcp_storage.available:
        print("❌ GCP Storage not available!")
        return
    
    # Find jobs in bucket
    job_ids = set()
    blobs = gcp_storage.bucket.list_blobs(prefix="jobs/")
    
    for blob in blobs:
        if blob.name.startswith("jobs/") and '/' in blob.name[5:]:
            job_id = blob.name[5:].split('/')[0]
            if job_id:
                job_ids.add(job_id)
    
    print(f"✅ Found {len(job_ids)} jobs in GCP bucket")
    
    if not job_ids:
        print("❌ No jobs found in bucket - nothing to test!")
        return
    
    # Pick first job for detailed analysis
    test_job_id = list(job_ids)[0]
    print(f"🎯 Using job {test_job_id} for detailed testing")
    
    # 2. Check job files
    print(f"\n📁 Step 2: Check files for job {test_job_id}...")
    
    job_files = gcp_storage.list_job_files(test_job_id)
    print(f"✅ Found {len(job_files)} files:")
    
    file_types = {}
    for file in job_files:
        file_type = file['name'].split('.')[-1]
        file_types[file_type] = file_types.get(file_type, 0) + 1
        print(f"   - {file['name']} ({file['size']} bytes)")
    
    print(f"📊 File types: {file_types}")
    
    # 3. Check metadata
    print(f"\n📋 Step 3: Check metadata for job {test_job_id}...")
    
    metadata_content = gcp_storage.download_file(f"jobs/{test_job_id}/metadata.json")
    if metadata_content:
        metadata = json.loads(metadata_content.decode('utf-8'))
        print("✅ Metadata loaded:")
        print(f"   Task type: {metadata.get('task_type')}")
        print(f"   Job name: {metadata.get('job_name')}")
        print(f"   Status: {metadata.get('status')}")
        print(f"   Stored at: {metadata.get('stored_at')}")
    else:
        print("❌ No metadata.json found!")
        return
    
    # 4. Check results
    print(f"\n📊 Step 4: Check results for job {test_job_id}...")
    
    results_content = gcp_storage.download_file(f"jobs/{test_job_id}/results.json")
    if results_content:
        results = json.loads(results_content.decode('utf-8'))
        print("✅ Results loaded:")
        print(f"   Keys: {list(results.keys())}")
        print(f"   Affinity: {results.get('affinity', 'N/A')}")
        print(f"   Confidence: {results.get('confidence', 'N/A')}")
        print(f"   Structure available: {'structure_file_base64' in results}")
    else:
        print("❌ No results.json found!")
    
    # 5. Test indexer
    print(f"\n🔍 Step 5: Test GCP results indexer...")
    
    try:
        from services.gcp_results_indexer import gcp_results_indexer
        
        # Clear cache first
        gcp_results_indexer.invalidate_cache("current_user")
        
        # Get results
        indexer_results = await gcp_results_indexer.get_user_results("current_user", limit=10)
        
        print(f"✅ Indexer results:")
        print(f"   Total: {indexer_results.get('total', 0)}")
        print(f"   Source: {indexer_results.get('source')}")
        print(f"   Results count: {len(indexer_results.get('results', []))}")
        
        # Find our test job
        test_result = None
        for result in indexer_results.get('results', []):
            if result.get('job_id') == test_job_id:
                test_result = result
                break
        
        if test_result:
            print(f"✅ Found test job in indexer results:")
            print(f"   Job ID: {test_result.get('job_id')}")
            print(f"   Task type: {test_result.get('task_type')}")
            print(f"   Status: {test_result.get('status')}")
            print(f"   File count: {test_result.get('file_count')}")
            print(f"   Has results: {'results' in test_result}")
            
            if 'results' in test_result and test_result['results']:
                print(f"   Results keys: {list(test_result['results'].keys())}")
            else:
                print(f"   ❌ No results data in indexer response!")
        else:
            print(f"❌ Test job {test_job_id} not found in indexer results!")
            
    except Exception as e:
        print(f"❌ Indexer error: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Test API endpoint
    print(f"\n🌐 Step 6: Test My Results API endpoint...")
    
    try:
        url = "http://localhost:8000/api/v2/my-results?user_id=current_user"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            api_data = response.json()
            print(f"✅ API response:")
            print(f"   Total: {api_data.get('total', 0)}")
            print(f"   Results: {len(api_data.get('results', []))}")
            
            # Find our test job in API results
            api_test_result = None
            for result in api_data.get('results', []):
                if result.get('job_id') == test_job_id:
                    api_test_result = result
                    break
            
            if api_test_result:
                print(f"✅ Found test job in API results:")
                print(f"   Task type: {api_test_result.get('task_type')}")
                print(f"   Status: {api_test_result.get('status')}")
                print(f"   Has results: {'results' in api_test_result}")
                
                if 'results' in api_test_result and api_test_result['results']:
                    results_data = api_test_result['results']
                    print(f"   ✅ Results data available for frontend:")
                    print(f"      Affinity: {results_data.get('affinity', 'N/A')}")
                    print(f"      Confidence: {results_data.get('confidence', 'N/A')}")
                    print(f"      Structure: {'structure_file_base64' in results_data}")
                else:
                    print(f"   ❌ No results data in API response!")
            else:
                print(f"❌ Test job not found in API results!")
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API request failed: {e}")
    
    print("\n" + "="*70)
    print("🎯 SUMMARY")
    print("="*70)
    print("If all steps show ✅, then My Results should work correctly.")
    print("If any step shows ❌, that's where the issue is.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_complete_flow())