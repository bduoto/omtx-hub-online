#!/usr/bin/env python3
"""
Examine the actual structure of result files to understand available fields
"""

import os
import sys
import asyncio
import json

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def examine_result_structure():
    """Examine the structure of actual result files"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Examining result file structure for batch {batch_id}")
    
    try:
        from services.gcp_storage_service import gcp_storage_service
        
        # Get a list of job folders that have results
        job_folders = []
        try:
            # List batch job folders
            batch_path = f"batches/{batch_id}/jobs/"
            blobs = gcp_storage_service.storage.client.list_blobs(
                gcp_storage_service.storage.bucket_name, 
                prefix=batch_path
            )
            
            for blob in blobs:
                if blob.name.endswith('/results.json'):
                    # Extract job_id from path like: batches/{batch_id}/jobs/{job_id}/results.json
                    parts = blob.name.split('/')
                    if len(parts) >= 4:
                        job_id = parts[3]  # jobs/{job_id}/results.json
                        job_folders.append(job_id)
            
            print(f"📁 Found {len(job_folders)} jobs with result files")
            
            if job_folders:
                # Examine the first result file
                first_job_id = job_folders[0]
                result_path = f"batches/{batch_id}/jobs/{first_job_id}/results.json"
                
                print(f"🔍 Examining result file: {result_path}")
                
                result_content = gcp_storage_service.storage.download_file(result_path)
                if isinstance(result_content, bytes):
                    result_content = result_content.decode('utf-8')
                
                result_data = json.loads(result_content)
                
                print(f"\n📋 RESULT FILE STRUCTURE:")
                print(f"   Top-level keys: {list(result_data.keys())}")
                
                # Check if there's a raw_modal_result
                if 'raw_modal_result' in result_data:
                    raw_modal = result_data['raw_modal_result']
                    print(f"   raw_modal_result keys: {list(raw_modal.keys()) if isinstance(raw_modal, dict) else type(raw_modal)}")
                    
                    # Look for ensemble or complex data
                    for key, value in raw_modal.items():
                        if isinstance(value, dict) and len(value) > 0:
                            print(f"   raw_modal_result.{key}: {list(value.keys())}")
                        else:
                            print(f"   raw_modal_result.{key}: {type(value)} = {value}")
                
                # Check other top-level fields
                for key, value in result_data.items():
                    if key != 'raw_modal_result':
                        if isinstance(value, dict) and len(value) > 0:
                            print(f"   {key}: {list(value.keys())}")
                        else:
                            print(f"   {key}: {type(value)} = {value}")
                
                print(f"\n📄 FULL RESULT STRUCTURE (first 2000 chars):")
                pretty_json = json.dumps(result_data, indent=2)[:2000]
                print(pretty_json)
                if len(pretty_json) >= 2000:
                    print("... [truncated]")
            
        except Exception as storage_err:
            print(f"❌ Storage examination failed: {storage_err}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Examination failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(examine_result_structure())