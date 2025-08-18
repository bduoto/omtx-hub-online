#!/usr/bin/env python3
"""
Complete any stuck batch that should be finished
Enhanced version that finds and completes stuck batches automatically
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def find_and_complete_stuck_batches():
    """Find and complete all stuck batches"""
    
    print(f"🔧 Searching for stuck batches...")
    
    try:
        from config.gcp_database import gcp_database
        
        # Get all batch parents
        batch_parents = gcp_database.db.collection('jobs').where('job_type', '==', 'BATCH_PARENT').stream()
        
        stuck_batches = []
        
        for doc in batch_parents:
            batch = doc.to_dict()
            batch_id = doc.id
            batch_status = batch.get('status', 'unknown')
            
            # Get child jobs
            child_jobs = list(
                gcp_database.db.collection('jobs')
                .where('batch_parent_id', '==', batch_id)
                .stream()
            )
            
            total_jobs = len(child_jobs)
            
            if total_jobs == 0:
                continue
                
            completed = sum(1 for j in child_jobs if j.to_dict().get('status') == 'completed')
            running = sum(1 for j in child_jobs if j.to_dict().get('status') == 'running')
            failed = sum(1 for j in child_jobs if j.to_dict().get('status') == 'failed')
            pending = sum(1 for j in child_jobs if j.to_dict().get('status') == 'pending')
            
            completion_rate = completed / total_jobs * 100
            all_jobs_done = (completed + failed) == total_jobs
            
            # Check if batch should be completed
            should_be_completed = (
                # All jobs are done (completed or failed)
                all_jobs_done or
                # 99%+ completion rate
                completion_rate >= 99 or
                # For 100-job batches, 99+ completed
                (total_jobs >= 95 and completed >= 99)
            )
            
            if should_be_completed and batch_status != 'completed':
                created_at = batch.get('created_at')
                if hasattr(created_at, 'timestamp'):
                    created_str = datetime.fromtimestamp(created_at.timestamp()).strftime('%Y-%m-%d %H:%M')
                else:
                    created_str = 'Unknown'
                
                print(f"🚨 FOUND STUCK BATCH: {batch_id}")
                print(f"   Name: {batch.get('job_name', 'Unknown')}")
                print(f"   Status: {batch_status} (should be completed)")
                print(f"   Created: {created_str}")
                print(f"   Total Jobs: {total_jobs}")
                print(f"   Completed: {completed} ({completion_rate:.1f}%)")
                print(f"   Failed: {failed}")
                print(f"   Running: {running}")
                print(f"   Pending: {pending}")
                print(f"   All Done: {all_jobs_done}")
                print()
                
                stuck_batches.append({
                    'batch_id': batch_id,
                    'total_jobs': total_jobs,
                    'completed': completed,
                    'failed': failed,
                    'completion_rate': completion_rate
                })
        
        if not stuck_batches:
            print("✅ No stuck batches found")
            return True
        
        print(f"Found {len(stuck_batches)} stuck batch(es). Completing them...")
        print()
        
        # Complete each stuck batch
        for batch_info in stuck_batches:
            success = await complete_single_batch(batch_info['batch_id'])
            if success:
                print(f"✅ Successfully completed batch {batch_info['batch_id']}")
            else:
                print(f"❌ Failed to complete batch {batch_info['batch_id']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error finding stuck batches: {e}")
        import traceback
        traceback.print_exc()
        return False

async def complete_single_batch(batch_id: str):
    """Complete a single stuck batch"""
    
    try:
        from config.gcp_database import gcp_database
        from scripts.create_legacy_batch_results import create_batch_results_for_batch
        
        print(f"📝 Updating batch parent status to completed...")
        batch_ref = gcp_database.db.collection('jobs').document(batch_id)
        batch_ref.update({
            'status': 'completed',
            'completed_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        print(f"✅ Updated batch parent status")
        
        print(f"📊 Generating batch_results.json with comprehensive field extraction...")
        success = await create_batch_results_for_batch(batch_id)
        
        if success:
            print(f"✅ Successfully generated batch_results.json")
        else:
            print(f"❌ Failed to generate batch_results.json")
            return False
        
        # Verify the completion
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
        
        print(f"🎉 BATCH COMPLETION SUCCESS!")
        print(f"   Batch ID: {batch_id}")
        print(f"   Status: completed")
        print(f"   Jobs: {completed_jobs}/{total_jobs}")
        print(f"   Batch results generated with comprehensive fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Error completing batch {batch_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(find_and_complete_stuck_batches())