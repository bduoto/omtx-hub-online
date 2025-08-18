#!/usr/bin/env python3
"""
Test the updated extraction functions with a real result file
"""

import os
import sys
import json

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_extraction():
    """Test extraction with actual result file"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    job_id = "0c49ee35-9752-4600-a18d-d1bf981a3c14"  # Known to exist
    
    print(f"🧪 Testing extraction for job {job_id}")
    
    try:
        from services.batch_file_scanner import batch_file_scanner
        from google.cloud import storage
        
        # Get the actual result file
        client = storage.Client()
        bucket = client.bucket('hub-job-files')
        result_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
        
        content = bucket.blob(result_path).download_as_text()
        result_data = json.loads(content)
        
        print(f"📄 Raw modal result keys: {list(result_data.get('raw_modal_result', {}).keys())}")
        
        # Test extraction
        affinity = batch_file_scanner._extract_affinity(result_data)
        confidence = batch_file_scanner._extract_confidence(result_data)
        
        print(f"🎯 Extracted affinity: {affinity}")
        print(f"🎯 Extracted confidence: {confidence}")
        
        # Show what's actually in raw_modal_result
        raw_modal = result_data.get('raw_modal_result', {})
        if raw_modal:
            print(f"\n📊 Raw modal result values:")
            if 'affinity' in raw_modal:
                print(f"   affinity: {raw_modal['affinity']} ({type(raw_modal['affinity'])})")
            if 'confidence' in raw_modal:
                print(f"   confidence: {raw_modal['confidence']} ({type(raw_modal['confidence'])})")
            if 'binding_affinity' in raw_modal:
                print(f"   binding_affinity: {raw_modal['binding_affinity']} ({type(raw_modal['binding_affinity'])})")
            if 'prediction_confidence' in raw_modal:
                print(f"   prediction_confidence: {raw_modal['prediction_confidence']} ({type(raw_modal['prediction_confidence'])})")
        
        # Also check top-level
        print(f"\n📋 Top-level values:")
        print(f"   prediction_confidence: {result_data.get('prediction_confidence')} ({type(result_data.get('prediction_confidence'))})")
        print(f"   binding_affinity: {result_data.get('binding_affinity')} ({type(result_data.get('binding_affinity'))})")
        
        return affinity, confidence
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    test_extraction()