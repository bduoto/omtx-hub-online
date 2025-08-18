#!/usr/bin/env python3
"""
Debug the My Results flow
"""

import asyncio
import json
from config.gcp_storage import gcp_storage

async def debug_my_results():
    """Debug what the My Results indexer sees"""
    
    print("\n" + "="*60)
    print("DEBUGGING MY RESULTS INDEXER")
    print("="*60)
    
    if not gcp_storage.available:
        print("❌ GCP Storage not available!")
        return
    
    print("✅ GCP Storage connected")
    
    # 1. Check what's in the jobs/ directory
    print("\n1. Scanning jobs/ directory structure...")
    
    jobs_prefix = "jobs/"
    
    # List blobs with delimiter to see directories
    print(f"   Listing blobs with prefix '{jobs_prefix}' and delimiter '/'...")
    blobs_with_delimiter = list(gcp_storage.bucket.list_blobs(prefix=jobs_prefix, delimiter='/'))
    
    print(f"   Found {len(blobs_with_delimiter)} direct blobs")
    for blob in blobs_with_delimiter[:5]:  # Show first 5
        print(f"      - {blob.name}")
    
    # Check prefixes (directories)
    print(f"\n   Checking for directory prefixes...")
    prefix_result = gcp_storage.bucket.list_blobs(prefix=jobs_prefix, delimiter='/')
    prefixes = list(prefix_result.prefixes) if hasattr(prefix_result, 'prefixes') else []
    
    print(f"   Found {len(prefixes)} directory prefixes:")
    for prefix in prefixes[:10]:  # Show first 10
        job_id = prefix.replace(jobs_prefix, '').rstrip('/')
        print(f"      - {prefix} → job_id: '{job_id}'")
    
    # 2. Try the indexer method
    print(f"\n2. Testing GCP results indexer...")
    
    try:
        from services.gcp_results_indexer import gcp_results_indexer
        
        print("   Calling gcp_results_indexer.get_user_results()...")
        result = await gcp_results_indexer.get_user_results("current_user", limit=10)
        
        print(f"   ✅ Indexer returned:")
        print(f"      Total: {result.get('total', 0)}")
        print(f"      Source: {result.get('source')}")
        print(f"      Results count: {len(result.get('results', []))}")
        
        if result.get('results'):
            print(f"   📊 Sample results:")
            for i, job in enumerate(result['results'][:3]):
                print(f"      {i+1}. {job.get('job_id', 'unknown')} - {job.get('task_type', 'unknown')} - files: {job.get('file_count', 0)}")
        else:
            print("   ❌ No results found by indexer")
            
    except Exception as e:
        print(f"   ❌ Indexer error: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Manual job check
    print(f"\n3. Manual job file check...")
    
    if prefixes:
        # Pick the first job and check its files
        first_prefix = prefixes[0]
        job_id = first_prefix.replace(jobs_prefix, '').rstrip('/')
        
        print(f"   Checking files for job: {job_id}")
        
        job_files = gcp_storage.list_job_files(job_id)
        print(f"   Found {len(job_files)} files:")
        for file in job_files:
            print(f"      - {file['name']} ({file['size']} bytes)")
        
        # Try to read metadata
        metadata_path = f"jobs/{job_id}/metadata.json"
        metadata_content = gcp_storage.download_file(metadata_path)
        if metadata_content:
            try:
                metadata = json.loads(metadata_content.decode('utf-8'))
                print(f"   ✅ Metadata loaded:")
                print(f"      Task type: {metadata.get('task_type')}")
                print(f"      Status: {metadata.get('status')}")
                print(f"      Job name: {metadata.get('job_name')}")
            except Exception as e:
                print(f"   ❌ Failed to parse metadata: {e}")
        else:
            print(f"   ❌ No metadata.json found at {metadata_path}")
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(debug_my_results())