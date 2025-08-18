"""
Quick fix for individual jobs API - extract individual jobs from batch child jobs
"""

from fastapi import APIRouter, Query
from database.unified_job_manager import unified_job_manager

router = APIRouter()

@router.get("/individual-jobs")
async def get_individual_jobs(user_id: str = "current_user", limit: int = Query(200, ge=1, le=500)):
    """
    Get individual jobs by extracting BATCH_CHILD jobs and treating them as individual results.
    This is a temporary fix until we have proper individual job storage.
    """
    
    try:
        # Get all jobs for user (using the correct method from unified batch API)
        all_jobs = unified_job_manager.primary_backend.get_user_jobs(user_id, limit=1000)
        
        # Filter for BATCH_CHILD jobs (these are individual predictions within batches)
        individual_jobs = []
        for job in all_jobs:
            job_type = job.get('job_type')
            
            # Include BATCH_CHILD jobs as individual jobs
            if job_type == 'BATCH_CHILD':
                # Convert batch child to individual job format
                individual_job = {
                    'id': job.get('id'),
                    'job_name': f"Individual: {job.get('name', 'Unnamed')}",
                    'name': job.get('name', 'Unnamed Job'),
                    'task_type': job.get('task_type', 'protein_ligand_binding'),
                    'status': job.get('status', 'pending'),
                    'created_at': job.get('created_at'),
                    'updated_at': job.get('updated_at'),
                    'user_id': job.get('user_id'),
                    'results': job.get('output_data', {}),
                    'inputs': job.get('input_data', {}),
                    'batch_parent_id': job.get('batch_parent_id'),
                    'ligand_name': job.get('input_data', {}).get('ligand_name', 'Unknown'),
                    'protein_name': job.get('input_data', {}).get('protein_name', 'Unknown')
                }
                individual_jobs.append(individual_job)
            
            # Also include any true INDIVIDUAL jobs if they exist
            elif job_type == 'INDIVIDUAL':
                individual_jobs.append({
                    'id': job.get('id'),
                    'job_name': job.get('name', 'Unnamed Job'),
                    'name': job.get('name', 'Unnamed Job'),
                    'task_type': job.get('task_type', 'unknown'),
                    'status': job.get('status', 'pending'),
                    'created_at': job.get('created_at'),
                    'updated_at': job.get('updated_at'),
                    'user_id': job.get('user_id'),
                    'results': job.get('output_data', {}),
                    'inputs': job.get('input_data', {})
                })
        
        # Limit results
        individual_jobs = individual_jobs[:limit]
        
        return {
            'results': individual_jobs,
            'total': len(individual_jobs),
            'source': 'batch-child-extraction',
            'message': f'Extracted {len(individual_jobs)} individual jobs from batch child jobs'
        }
        
    except Exception as e:
        return {
            'results': [],
            'total': 0,
            'error': str(e),
            'source': 'error'
        }