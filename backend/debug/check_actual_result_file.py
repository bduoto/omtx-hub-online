#!/usr/bin/env python3
"""
Check the actual content of a result file to understand the data structure
"""

import os
import sys
import json

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_actual_result_file():
    """Check the content of an actual result file"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🔍 Checking actual result file content for batch {batch_id}")
    
    try:
        from services.gcp_storage_service import gcp_storage_service
        
        # Try to find one of the actual result files
        # From the test output, we know there are 44 files, let's find one
        test_job_ids = [
            "1000",  # From the test output, this had status "completed"
            "f1e6e25a-53a5-47f5-b1ba-eb44a8e6c1df",
            "e9d7c8b6-4a2f-4f1e-9c8d-7b5a3f2e1d9c"
        ]
        
        for job_id in test_job_ids:
            result_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
            print(f"\n🧪 Trying path: {result_path}")
            
            try:
                content = gcp_storage_service.storage.download_file(result_path)
                if content:
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    
                    result_data = json.loads(content)
                    print(f"✅ Found result file for job {job_id}")
                    print(f"📄 File content keys: {list(result_data.keys())}")
                    
                    # Show the structure
                    for key, value in result_data.items():
                        if isinstance(value, dict):
                            print(f"   {key}: {list(value.keys())}")
                        elif isinstance(value, (int, float)):
                            print(f"   {key}: {value}")
                        else:
                            print(f"   {key}: {type(value)} (length: {len(str(value)) if value else 0})")
                    
                    # Look for affinity/confidence specifically
                    if 'affinity' in result_data:
                        print(f"\n🎯 Affinity: {result_data['affinity']}")
                    if 'confidence' in result_data:
                        print(f"🎯 Confidence: {result_data['confidence']}")
                    if 'binding_affinity' in result_data:
                        print(f"🎯 Binding affinity: {result_data['binding_affinity']}")
                    if 'prediction_confidence' in result_data:
                        print(f"🎯 Prediction confidence: {result_data['prediction_confidence']}")
                    if 'affinity_ensemble' in result_data:
                        print(f"🎯 Affinity ensemble: {result_data['affinity_ensemble']}")
                    
                    return result_data
                    
            except Exception as e:
                print(f"❌ Error checking {result_path}: {e}")
        
        print(f"❌ No result files found for any test job IDs")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    check_actual_result_file()