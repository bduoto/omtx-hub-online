#!/usr/bin/env python3
"""
Debug script to examine batch storage structure and find ligand metadata
"""

import asyncio
import json
from services.gcp_storage_service import gcp_storage_service

async def examine_batch_storage(batch_id: str):
    """Examine the storage structure for a specific batch"""
    
    print(f"🔍 Examining storage structure for batch: {batch_id}")
    print("=" * 60)
    
    # Check what files exist in the batch directory
    try:
        # List files in batch directory
        batch_prefix = f"batches/{batch_id}/"
        print(f"\n📁 Files in {batch_prefix}:")
        
        # Try to list files (this might not work with our storage service)
        # So we'll try to download specific known files
        
        files_to_check = [
            f"batches/{batch_id}/batch_results.json",
            f"batches/{batch_id}/results/aggregated.json", 
            f"batches/{batch_id}/results/summary.json",
            f"batches/{batch_id}/metadata.json",
            f"batches/{batch_id}/batch_index.json"
        ]
        
        for file_path in files_to_check:
            try:
                print(f"\n📄 Checking: {file_path}")
                content = gcp_storage_service.storage.download_file(file_path)
                if content:
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    
                    # Parse JSON and show structure
                    data = json.loads(content)
                    print(f"✅ Found file with {len(str(content))} characters")
                    print(f"📊 JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Look for ligand data specifically
                    if 'individual_results' in data:
                        individual_results = data['individual_results']
                        if individual_results and len(individual_results) > 0:
                            first_result = individual_results[0]
                            print(f"🧪 First individual result keys: {list(first_result.keys())}")
                            
                            # Check for ligand info
                            for key in ['ligand_name', 'ligand_smiles', 'input_data', 'metadata', 'raw_modal_result']:
                                if key in first_result:
                                    value = first_result[key]
                                    if isinstance(value, dict):
                                        print(f"  📋 {key}: {list(value.keys())} (dict)")
                                    else:
                                        print(f"  📋 {key}: {value}")
                    
                    # Look for other ligand-related data
                    def search_for_ligand_data(obj, path=""):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if 'ligand' in key.lower() or 'smiles' in key.lower():
                                    print(f"  🔍 Found ligand field at {path}.{key}: {value}")
                                if isinstance(value, (dict, list)):
                                    search_for_ligand_data(value, f"{path}.{key}")
                        elif isinstance(obj, list) and obj:
                            search_for_ligand_data(obj[0], f"{path}[0]")
                    
                    search_for_ligand_data(data)
                else:
                    print(f"❌ File not found or empty")
                    
            except Exception as e:
                print(f"❌ Error reading {file_path}: {e}")
        
        # Also check individual job directories
        print(f"\n🔍 Checking individual job directories...")
        
        # Get job IDs from batch_results.json if we loaded it
        try:
            batch_results_content = gcp_storage_service.storage.download_file(f"batches/{batch_id}/batch_results.json")
            if batch_results_content:
                if isinstance(batch_results_content, bytes):
                    batch_results_content = batch_results_content.decode('utf-8')
                batch_data = json.loads(batch_results_content)
                
                job_ids = []
                if 'individual_results' in batch_data:
                    for result in batch_data['individual_results'][:2]:  # Check first 2 jobs
                        job_id = result.get('job_id')
                        if job_id:
                            job_ids.append(job_id)
                
                for job_id in job_ids:
                    print(f"\n📁 Checking job {job_id[:8]}...")
                    job_files = [
                        f"batches/{batch_id}/jobs/{job_id}/metadata.json",
                        f"batches/{batch_id}/jobs/{job_id}/results.json",
                        f"batches/{batch_id}/jobs/{job_id}/input_data.json",
                        f"jobs/{job_id}/metadata.json",
                        f"jobs/{job_id}/results.json"
                    ]
                    
                    for job_file in job_files:
                        try:
                            content = gcp_storage_service.storage.download_file(job_file)
                            if content:
                                if isinstance(content, bytes):
                                    content = content.decode('utf-8')
                                data = json.loads(content)
                                print(f"  ✅ {job_file}: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                                
                                # Look for ligand data
                                search_for_ligand_data(data, f"  ")
                            else:
                                print(f"  ❌ {job_file}: Not found")
                        except Exception as e:
                            print(f"  ❌ {job_file}: Error - {e}")
                            
        except Exception as e:
            print(f"❌ Error checking job directories: {e}")
            
    except Exception as e:
        print(f"❌ Error examining storage: {e}")

if __name__ == "__main__":
    # Use the batch ID from the logs
    batch_id = "a71c7777-b8e0-4d54-b97d-0c07474dd22b"
    asyncio.run(examine_batch_storage(batch_id))