#!/usr/bin/env python3
"""
Find and restore missing 300 ligand trim25 batch from recent orphaned jobs
"""

import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.gcp_database import gcp_database
from database.unified_job_manager import unified_job_manager

def find_recent_300_ligand_batch():
    """Find orphaned jobs from the recent 300 ligand batch"""
    
    # Look for jobs created in the last 6 hours
    six_hours_ago = datetime.utcnow() - timedelta(hours=6)
    
    print(f"🔍 Searching for orphaned jobs created after {six_hours_ago}")
    
    # Query for recent jobs that might be from the terminated batch
    jobs_query = (gcp_database.db.collection('jobs')
                 .where('created_at', '>=', six_hours_ago)
                 .limit(500))  # Get recent jobs
    
    jobs_docs = list(jobs_query.stream())
    print(f"📊 Found {len(jobs_docs)} recent jobs")
    
    # Group jobs by potential batch patterns
    potential_batches = {}
    orphaned_jobs = []
    
    for doc in jobs_docs:
        job_data = doc.to_dict()
        job_id = doc.id
        
        # Check if this job has batch characteristics
        batch_parent_id = job_data.get('batch_parent_id')
        job_name = job_data.get('name', '')
        task_type = job_data.get('task_type', '')
        
        # Look for batch-related jobs
        if batch_parent_id:
            # This is a child job - check if parent exists
            if batch_parent_id not in potential_batches:
                potential_batches[batch_parent_id] = []
            potential_batches[batch_parent_id].append({
                'job_id': job_id,
                'name': job_name,
                'task_type': task_type,
                'status': job_data.get('status'),
                'created_at': job_data.get('created_at'),
                'input_data': job_data.get('input_data', {})
            })
        elif 'batch' in job_name.lower() or task_type == 'batch_protein_ligand_screening':
            # Potential batch parent or orphaned job
            orphaned_jobs.append({
                'job_id': job_id,
                'name': job_name,
                'task_type': task_type,
                'status': job_data.get('status'),
                'created_at': job_data.get('created_at'),
                'input_data': job_data.get('input_data', {})
            })
    
    print(f"\n🔍 Analysis Results:")
    print(f"   Potential batch groups: {len(potential_batches)}")
    print(f"   Orphaned batch-related jobs: {len(orphaned_jobs)}")
    
    # Find the 300 ligand batch
    target_batch = None
    target_batch_id = None
    
    for batch_id, child_jobs in potential_batches.items():
        if len(child_jobs) >= 280 and len(child_jobs) <= 320:  # Around 300 ligands
            print(f"\n🎯 FOUND 300 LIGAND BATCH!")
            print(f"   Batch ID: {batch_id}")
            print(f"   Child jobs: {len(child_jobs)}")
            
            # Check if the parent exists
            try:
                parent_job = unified_job_manager.get_job(batch_id)
                if parent_job:
                    print(f"   ✅ Parent exists: {parent_job.get('name', 'No name')}")
                else:
                    print(f"   ❌ MISSING PARENT - needs restoration")
                    target_batch = child_jobs
                    target_batch_id = batch_id
            except Exception as e:
                print(f"   ❌ MISSING PARENT - needs restoration (error: {e})")
                target_batch = child_jobs
                target_batch_id = batch_id
                
            # Show sample jobs
            print(f"   Sample jobs:")
            for i, job in enumerate(child_jobs[:5]):
                print(f"     {i+1}. {job['name']} - {job['status']}")
                
            break
    
    # If no batch found in potential_batches, check orphaned jobs
    if not target_batch:
        print(f"\n🔍 Checking orphaned jobs for patterns...")
        for job in orphaned_jobs:
            print(f"   - {job['name']} ({job['task_type']}) - {job['status']}")
    
    return target_batch_id, target_batch

def create_missing_batch_parent(batch_id, child_jobs):
    """Create the missing batch parent record"""
    
    if not child_jobs:
        print("❌ No child jobs to create batch from")
        return None
        
    # Analyze child jobs to determine batch characteristics
    total_ligands = len(child_jobs)
    completed_jobs = len([j for j in child_jobs if j['status'] == 'completed'])
    failed_jobs = len([j for j in child_jobs if j['status'] == 'failed'])
    running_jobs = len([j for j in child_jobs if j['status'] in ['running', 'pending']])
    
    # Get batch name from first child job
    first_job = child_jobs[0]
    batch_name = f"trim25_300_ligand_screen_restored_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
    
    # Create batch parent record
    batch_data = {
        'id': batch_id,
        'name': batch_name,
        'task_type': 'batch_protein_ligand_screening',
        'status': 'completed' if running_jobs == 0 else 'running',
        'job_type': 'BATCH_PARENT',
        'created_at': first_job['created_at'],
        'updated_at': datetime.utcnow(),
        'total_ligands': total_ligands,
        'progress': {
            'total_jobs': total_ligands,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'running_jobs': running_jobs,
            'pending_jobs': 0
        },
        'batch_summary': {
            'total_ligands': total_ligands,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'execution_time': 0
        },
        'input_data': first_job.get('input_data', {}),
        'restored': True,
        'restoration_timestamp': datetime.utcnow()
    }
    
    print(f"\n🔧 Creating batch parent record:")
    print(f"   ID: {batch_id}")
    print(f"   Name: {batch_name}")
    print(f"   Total ligands: {total_ligands}")
    print(f"   Completed: {completed_jobs}")
    print(f"   Failed: {failed_jobs}")
    print(f"   Running: {running_jobs}")
    
    try:
        # Store the batch parent
        doc_ref = gcp_database.db.collection('jobs').document(batch_id)
        doc_ref.set(batch_data)
        print(f"✅ Batch parent created successfully!")
        return batch_data
    except Exception as e:
        print(f"❌ Error creating batch parent: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting 300 ligand batch restoration...")
    
    # Find the missing batch
    batch_id, child_jobs = find_recent_300_ligand_batch()
    
    if batch_id and child_jobs:
        print(f"\n🎯 Found target batch: {batch_id} with {len(child_jobs)} jobs")
        
        # Create the missing parent
        parent_data = create_missing_batch_parent(batch_id, child_jobs)
        
        if parent_data:
            print(f"\n✅ SUCCESS! Batch restored:")
            print(f"   Batch ID: {batch_id}")
            print(f"   Access URL: /results/{batch_id}")
            print(f"   Status: {parent_data['status']}")
            print(f"   Total jobs: {parent_data['total_ligands']}")
    else:
        print(f"\n❌ Could not find 300 ligand batch in recent jobs")
        print(f"   Try checking the last 24 hours or look for different patterns")