#!/usr/bin/env python3
"""
List the actual files in GCP storage to find a real job ID
"""

import os
import sys

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def list_actual_files():
    """List actual files in GCP storage"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"📁 Listing actual files in GCP storage for batch {batch_id}")
    
    try:
        from google.cloud import storage
        
        client = storage.Client()
        bucket = client.bucket('hub-job-files')
        prefix = f'batches/{batch_id}/jobs/'
        
        print(f"🔍 Searching prefix: {prefix}")
        
        result_files = []
        blobs = bucket.list_blobs(prefix=prefix)
        
        for blob in blobs:
            if blob.name.endswith('/results.json'):
                # Extract job ID from path
                job_id = blob.name.split('/')[-2]
                result_files.append(job_id)
                print(f"✅ Found result file: {job_id}")
                
                if len(result_files) >= 5:  # Just show first 5
                    break
        
        print(f"\n📊 Found {len(result_files)} result files")
        
        if result_files:
            # Check the first one
            first_job_id = result_files[0]
            print(f"\n🧪 Checking content of first file: {first_job_id}")
            
            result_path = f"batches/{batch_id}/jobs/{first_job_id}/results.json"
            content = bucket.blob(result_path).download_as_text()
            
            import json
            result_data = json.loads(content)
            
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
            
            return result_data
        else:
            print("❌ No result files found")
            return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    list_actual_files()