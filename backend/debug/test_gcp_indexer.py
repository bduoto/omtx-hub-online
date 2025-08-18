#!/usr/bin/env python3
"""
Test GCP results indexer
"""

import asyncio
import json
from services.gcp_results_indexer import gcp_results_indexer
from config.gcp_storage import gcp_storage

async def test_gcp_indexer():
    """Test the GCP results indexer"""
    
    print("\n" + "="*60)
    print("TESTING GCP RESULTS INDEXER")
    print("="*60)
    
    # 1. Check GCP storage
    print("\n1. Checking GCP storage...")
    if not gcp_storage.available:
        print("❌ GCP storage not available!")
        return
    
    print("✅ GCP storage available")
    
    # 2. List files in jobs/ directory
    print("\n2. Listing files in jobs/ directory...")
    try:
        blobs = list(gcp_storage.bucket.list_blobs(prefix="jobs/", max_results=20))
        
        if blobs:
            print(f"✅ Found {len(blobs)} files in jobs/ directory:")
            
            # Group by job ID
            job_dirs = set()
            for blob in blobs:
                if "/" in blob.name[5:]:  # Skip "jobs/"
                    job_id = blob.name[5:].split("/")[0]
                    job_dirs.add(job_id)
                    
            print(f"   📁 Found {len(job_dirs)} job directories:")
            for job_id in sorted(job_dirs)[:5]:  # Show first 5
                print(f"      - {job_id}")
                
                # Check what files exist for this job
                job_files = gcp_storage.list_job_files(job_id)
                file_names = [f['name'] for f in job_files]
                print(f"        Files: {', '.join(file_names)}")
                
                # Check if metadata.json exists
                if 'metadata.json' in file_names:
                    metadata_content = gcp_storage.download_file(f"jobs/{job_id}/metadata.json")
                    if metadata_content:
                        metadata = json.loads(metadata_content.decode('utf-8'))
                        print(f"        Status: {metadata.get('status', 'unknown')}")
                        print(f"        Task: {metadata.get('task_type', 'unknown')}")
        else:
            print("❌ No files found in jobs/ directory")
    except Exception as e:
        print(f"❌ Error listing jobs: {e}")
    
    # 3. Test indexer
    print("\n3. Testing GCP results indexer...")
    try:
        results = await gcp_results_indexer.get_user_results("current_user", limit=10)
        
        print(f"✅ Indexer returned {results.get('total', 0)} results")
        print(f"   Source: {results.get('source', 'unknown')}")
        
        if results.get('results'):
            print(f"   📊 Sample results:")
            for i, result in enumerate(results['results'][:3]):
                print(f"      {i+1}. {result.get('job_id', 'unknown')} - {result.get('status', 'unknown')} - {result.get('task_type', 'unknown')}")
        else:
            print("   ❌ No results found by indexer")
            
    except Exception as e:
        print(f"❌ Indexer error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_gcp_indexer())