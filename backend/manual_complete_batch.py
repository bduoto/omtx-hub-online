#!/usr/bin/env python3
"""
Manually complete a stuck batch that's at 99% completion
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def manually_complete_batch():
    """Manually complete the stuck batch"""
    
    batch_id = "9ae28e33-589e-42e0-8c84-a7e504bd73dc"
    
    print(f"🔧 Manually completing batch {batch_id}")
    
    try:
        from config.gcp_database import gcp_database
        from services.batch_file_scanner import batch_file_scanner
        from scripts.create_legacy_batch_results import create_batch_results_for_batch
        
        # Step 1: Update batch parent status to completed
        print(f"📝 Updating batch parent status to completed...")
        batch_ref = gcp_database.db.collection('jobs').document(batch_id)
        batch_ref.update({
            'status': 'completed',
            'completed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        print(f"✅ Updated batch parent status")
        
        # Step 2: Generate batch_results.json with comprehensive fields
        print(f"📊 Generating batch_results.json with comprehensive field extraction...")
        success = await create_batch_results_for_batch(batch_id)
        
        if success:
            print(f"✅ Successfully generated batch_results.json")
        else:
            print(f"❌ Failed to generate batch_results.json")
            return False
        
        # Step 3: Verify the completion
        print(f"🔍 Verifying batch completion...")
        
        # Check child job status
        child_jobs_query = (
            gcp_database.db.collection('jobs')
            .where('batch_parent_id', '==', batch_id)
        )
        
        child_docs = list(child_jobs_query.stream())
        total_jobs = len(child_docs)
        completed_jobs = len([doc for doc in child_docs if doc.to_dict().get('status') == 'completed'])
        
        print(f"📊 Final status: {completed_jobs}/{total_jobs} jobs completed")
        
        # Step 4: Clear any caches
        print(f"🧹 Clearing caches...")
        # We don't need to clear specific caches since the API will pick up the new batch_results.json
        
        print(f"🎉 BATCH COMPLETION SUCCESS!")
        print(f"   Batch ID: {batch_id}")
        print(f"   Status: completed")
        print(f"   Jobs: {completed_jobs}/{total_jobs}")
        print(f"   Batch results generated with comprehensive fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Error manually completing batch: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(manually_complete_batch())