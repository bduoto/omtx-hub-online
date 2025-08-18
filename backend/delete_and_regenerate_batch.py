#!/usr/bin/env python3
"""
Delete existing batch_results.json and regenerate with comprehensive fields
"""

import os
import sys
import asyncio

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def delete_and_regenerate():
    """Delete existing batch results and regenerate with comprehensive fields"""
    
    batch_id = "2b4036e5-d3c8-4620-9d84-47f99c7f01ca"
    
    print(f"🗑️  Deleting existing batch_results.json for {batch_id}")
    
    try:
        from services.gcp_storage_service import gcp_storage_service
        
        # Delete existing batch_results.json
        delete_path = f"batches/{batch_id}/batch_results.json"
        delete_success = gcp_storage_service.storage.delete_file(delete_path)
        
        if delete_success:
            print(f"✅ Deleted existing batch_results.json")
        else:
            print(f"⚠️  Could not delete or file doesn't exist")
        
        # Now regenerate with comprehensive fields
        from scripts.create_legacy_batch_results import create_batch_results_for_batch
        
        print(f"🔄 Regenerating with comprehensive field extraction...")
        success = await create_batch_results_for_batch(batch_id)
        
        if success:
            print(f"✅ Successfully regenerated batch_results.json with comprehensive fields")
        else:
            print(f"❌ Failed to regenerate batch_results.json")
            
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(delete_and_regenerate())