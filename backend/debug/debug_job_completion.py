#!/usr/bin/env python3
"""
Debug job completion flow
"""

import asyncio
import json
from database.unified_job_manager import unified_job_manager
from services.modal_monitor import modal_monitor
from config.gcp_storage import gcp_storage

async def debug_job_completion():
    """Debug the job completion flow"""
    
    print("\n" + "="*60)
    print("DEBUGGING JOB COMPLETION FLOW")
    print("="*60)
    
    # 1. Check running jobs in database
    print("\n1. Checking running jobs in database...")
    try:
        running_jobs = unified_job_manager.get_jobs_by_status('running')
        
        if running_jobs:
            print(f"✅ Found {len(running_jobs)} running jobs:")
            for job in running_jobs:
                job_id = job.get('id')
                print(f"   📋 Job: {job_id}")
                print(f"      Status: {job.get('status')}")
                print(f"      Type: {job.get('type')}")
                
                # Check for Modal call ID
                results = job.get('results', {})
                modal_call_id = results.get('modal_call_id')
                if modal_call_id:
                    print(f"      Modal Call ID: {modal_call_id}")
                    
                    # Check if files exist in GCP
                    job_files = gcp_storage.list_job_files(job_id)
                    print(f"      GCP Files: {len(job_files)} files")
                    
                    if job_files:
                        file_names = [f['name'] for f in job_files]
                        print(f"        Files: {', '.join(file_names)}")
                        
                        # This job might be completed but not updated
                        print(f"      ⚠️  Job has GCP files but still marked as running!")
                else:
                    print(f"      ❌ No Modal call ID found")
        else:
            print("❌ No running jobs found in database")
    except Exception as e:
        print(f"❌ Error getting running jobs: {e}")
    
    # 2. Manually run modal monitor
    print("\n2. Running modal monitor check...")
    try:
        await modal_monitor.check_and_update_jobs()
        print("✅ Modal monitor check completed")
    except Exception as e:
        print(f"❌ Modal monitor error: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Check jobs again after monitor
    print("\n3. Checking jobs after monitor run...")
    try:
        running_jobs = unified_job_manager.get_jobs_by_status('running')
        completed_jobs = unified_job_manager.get_jobs_by_status('completed')
        
        print(f"   Running jobs: {len(running_jobs)}")
        print(f"   Completed jobs: {len(completed_jobs)}")
        
        if completed_jobs:
            print("   📊 Recent completed jobs:")
            for job in completed_jobs[-3:]:  # Last 3
                job_id = job.get('id')
                print(f"      - {job_id} ({job.get('type')})")
                
                # Check GCP files
                job_files = gcp_storage.list_job_files(job_id)
                print(f"        GCP files: {len(job_files)}")
                
    except Exception as e:
        print(f"❌ Error checking jobs after monitor: {e}")
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(debug_job_completion())