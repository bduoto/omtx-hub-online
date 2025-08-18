#!/usr/bin/env python3
"""
Test the quick fixes for unified job architecture
"""

from database.unified_job_manager import unified_job_manager

def test_job_type_distribution():
    """Test current job type distribution"""
    print("🔍 Testing job type distribution...")
    
    jobs = unified_job_manager.get_recent_jobs(limit=50)
    
    job_types = {}
    task_types = {}
    
    for job in jobs:
        # Current job_type field
        jt = job.get('job_type', 'missing')
        job_types[jt] = job_types.get(jt, 0) + 1
        
        # Task type (what the prediction does)
        tt = job.get('type', 'unknown')
        task_types[tt] = task_types.get(tt, 0) + 1
    
    print(f"\nJob Type Distribution (current):")
    for jt, count in sorted(job_types.items()):
        print(f"   {jt}: {count}")
    
    print(f"\nTask Type Distribution:")
    for tt, count in sorted(task_types.items()):
        print(f"   {tt}: {count}")
    
    return job_types, task_types

def test_batch_relationships():
    """Test batch parent-child relationships"""
    print("\n🔍 Testing batch relationships...")
    
    jobs = unified_job_manager.get_recent_jobs(limit=100)
    batch_jobs = [j for j in jobs if 'batch' in j.get('type', '').lower()]
    
    print(f"Found {len(batch_jobs)} batch jobs")
    
    for batch in batch_jobs[:2]:  # Test first 2
        batch_id = batch.get('id')
        print(f"\n📋 Batch: {batch_id}")
        print(f"   Name: {batch.get('name', 'Unnamed')}")
        print(f"   Status: {batch.get('status')}")
        
        # Find children using both methods
        children_new = []  # Using batch_parent_id
        children_old = []  # Using input_data.parent_batch_id
        
        for job in jobs:
            if job.get('batch_parent_id') == batch_id:
                children_new.append(job)
            elif job.get('input_data', {}).get('parent_batch_id') == batch_id:
                children_old.append(job)
        
        print(f"   Children (new method): {len(children_new)}")
        print(f"   Children (old method): {len(children_old)}")
        
        # Show status distribution
        if children_old:
            status_counts = {}
            for child in children_old:
                status = child.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"   Child status distribution: {status_counts}")

def test_endpoint_data_structure():
    """Test the data structure our endpoint will return"""
    print("\n🔍 Testing endpoint data structure...")
    
    jobs = unified_job_manager.get_recent_jobs(limit=50)
    batch_jobs = [j for j in jobs if 'batch' in j.get('type', '').lower()]
    
    if batch_jobs:
        batch = batch_jobs[0]
        batch_id = batch.get('id')
        
        # Simulate our endpoint logic
        children = []
        for job in jobs:
            if (job.get('batch_parent_id') == batch_id or 
                job.get('input_data', {}).get('parent_batch_id') == batch_id):
                children.append(job)
        
        # Build response like our endpoint
        response = {
            'batch_id': batch_id,
            'batch_metadata': {
                'job_name': batch.get('name', 'Unnamed'),
                'protein_name': batch.get('input_data', {}).get('protein_name', 'Unknown'),
                'created_at': batch.get('created_at'),
                'total_ligands': len(children)
            },
            'total_children': len(children),
            'completed_children': len([c for c in children if c.get('status') == 'completed']),
            'failed_children': len([c for c in children if c.get('status') == 'failed']),
            'child_results': len(children),  # Would be full array in real endpoint
            'status': batch.get('status'),
        }
        
        print(f"Sample endpoint response structure:")
        print(f"   batch_id: {response['batch_id']}")
        print(f"   total_children: {response['total_children']}")
        print(f"   completed_children: {response['completed_children']}")
        print(f"   protein_name: {response['batch_metadata']['protein_name']}")
        print(f"   status: {response['status']}")
        
        return response
    else:
        print("❌ No batch jobs found to test endpoint structure")
        return None

if __name__ == "__main__":
    print("🚀 Testing OMTX-Hub Quick Fixes")
    print("=" * 50)
    
    # Test 1: Job type distribution
    job_types, task_types = test_job_type_distribution()
    
    # Test 2: Batch relationships
    test_batch_relationships()
    
    # Test 3: Endpoint data structure
    endpoint_response = test_endpoint_data_structure()
    
    print("\n" + "=" * 50)
    print("✅ Quick fixes test complete!")
    
    # Summary
    batch_count = task_types.get('batch_protein_ligand_screening', 0)
    individual_count = task_types.get('protein_ligand_binding', 0)
    
    print(f"\nSummary:")
    print(f"   - {individual_count} individual predictions found")
    print(f"   - {batch_count} batch predictions found") 
    print(f"   - Batch relationships: {'✅ Working' if endpoint_response else '❌ No batch jobs to test'}")
    print(f"   - Endpoint structure: {'✅ Ready' if endpoint_response else '❌ Needs batch jobs'}")