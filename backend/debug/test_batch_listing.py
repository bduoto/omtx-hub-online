#!/usr/bin/env python3
"""
Test batch listing to debug the issue
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

def test_batch_listing():
    """Test batch listing directly"""
    
    print("🔍 TESTING BATCH LISTING")
    print("=" * 50)
    
    try:
        from database.unified_job_manager import unified_job_manager
        
        # Get all jobs for debug_user
        print("📋 Getting all jobs for debug_user...")
        all_jobs = unified_job_manager.primary_backend.get_user_jobs('debug_user', limit=50)
        print(f"   Found {len(all_jobs)} total jobs")
        
        # Check job types
        job_types = {}
        task_types = {}
        batch_jobs = []
        
        for job in all_jobs:
            job_type = job.get('job_type', 'unknown')
            task_type = job.get('task_type', 'unknown')
            
            job_types[job_type] = job_types.get(job_type, 0) + 1
            task_types[task_type] = task_types.get(task_type, 0) + 1
            
            # Check if it's a batch job
            is_batch = (
                job.get('task_type', '').startswith('batch_') or 
                job.get('job_type') == 'batch_parent' or
                job.get('batch_id') or
                job.get('batch_parent_id')
            )
            
            if is_batch:
                batch_jobs.append(job)
                print(f"   📊 Batch job: {job.get('id', 'no-id')}")
                print(f"      Name: {job.get('name', job.get('job_name', 'no-name'))}")
                print(f"      Job type: {job.get('job_type', 'unknown')}")
                print(f"      Task type: {job.get('task_type', 'unknown')}")
                print(f"      Status: {job.get('status', 'unknown')}")
                print(f"      Batch parent ID: {job.get('batch_parent_id', 'none')}")
                print()
        
        print(f"📊 Job types found: {job_types}")
        print(f"📊 Task types found: {task_types}")
        print(f"📊 Batch jobs found: {len(batch_jobs)}")
        
        # Test the API logic
        print("\n🧪 Testing API logic...")
        
        # Separate batch parents from child jobs
        batch_parents = []
        child_jobs_by_parent = {}
        
        for job in batch_jobs:
            if job.get('job_type') == 'batch_parent' or job.get('task_type', '').startswith('batch_'):
                batch_parents.append(job)
                print(f"   📋 Batch parent: {job.get('id')} - {job.get('name', 'no-name')}")
            elif job.get('batch_parent_id'):
                parent_id = job.get('batch_parent_id')
                if parent_id not in child_jobs_by_parent:
                    child_jobs_by_parent[parent_id] = []
                child_jobs_by_parent[parent_id].append(job)
                print(f"   📝 Child job: {job.get('id')} -> parent: {parent_id}")
        
        print(f"📊 Batch parents: {len(batch_parents)}")
        print(f"📊 Child job groups: {len(child_jobs_by_parent)}")
        
        # Process batch data
        for parent in batch_parents:
            parent_id = parent.get('id')
            child_jobs = child_jobs_by_parent.get(parent_id, [])
            
            total_jobs = len(child_jobs)
            completed_jobs = len([c for c in child_jobs if c.get('status') == 'completed'])
            failed_jobs = len([c for c in child_jobs if c.get('status') == 'failed'])
            
            print(f"   📊 Batch {parent_id}:")
            print(f"      Total child jobs: {total_jobs}")
            print(f"      Completed: {completed_jobs}")
            print(f"      Failed: {failed_jobs}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🎯 BATCH LISTING TEST COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    test_batch_listing()
