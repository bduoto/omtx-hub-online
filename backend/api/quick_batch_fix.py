"""
Quick Batch Results API Fix
Provides the minimal endpoint needed for BatchResults.tsx to work
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/v2/batch/{batch_id}/results")
async def get_batch_results_quick(batch_id: str) -> Dict[str, Any]:
    """Quick batch results endpoint for BatchResults.tsx"""
    
    try:
        logger.info(f"🔍 Getting batch results for: {batch_id}")
        
        # Get parent job
        parent_job = unified_job_manager.get_job(batch_id)
        if not parent_job:
            raise HTTPException(404, f"Batch job {batch_id} not found")
        
        logger.info(f"📋 Found parent job: {parent_job.get('name', 'Unnamed')}")
        
        # Find child jobs using batch_parent_id (new way) or fallback to old way
        child_jobs = []
        
        # Try new way first - using batch_parent_id field
        recent_jobs = unified_job_manager.get_recent_jobs(limit=200)  # Get more to find children
        for job in recent_jobs:
            if job.get('batch_parent_id') == batch_id:
                child_jobs.append(job)
        
        # If no children found with new way, try old way - check input_data
        if not child_jobs:
            logger.info("🔄 No children found with batch_parent_id, trying old method...")
            for job in recent_jobs:
                parent_id_in_input = job.get('input_data', {}).get('parent_batch_id')
                if parent_id_in_input == batch_id:
                    child_jobs.append(job)
        
        logger.info(f"👶 Found {len(child_jobs)} child jobs")
        
        # Sort children by batch_index if available
        child_jobs.sort(key=lambda x: x.get('batch_index', x.get('input_data', {}).get('batch_index', 0)))
        
        # Calculate statistics
        total_children = len(child_jobs)
        completed_children = len([j for j in child_jobs if j.get('status') == 'completed'])
        failed_children = len([j for j in child_jobs if j.get('status') == 'failed'])
        running_children = len([j for j in child_jobs if j.get('status') == 'running'])
        
        # Format child results for frontend
        child_results = []
        for child in child_jobs:
            child_result = {
                'job_id': child.get('id'),
                'status': child.get('status', 'unknown'),
                'ligand_info': {
                    'name': child.get('input_data', {}).get('ligand_name', 'Unknown'),
                    'smiles': child.get('input_data', {}).get('ligand_smiles', '')
                },
                'created_at': child.get('created_at'),
                'completed_at': child.get('completed_at'),
                'affinity': child.get('output_data', {}).get('affinity_pred_value') if child.get('output_data') else None,
                'confidence': child.get('output_data', {}).get('confidence_score') if child.get('output_data') else None
            }
            child_results.append(child_result)
        
        # Build response matching what BatchResults.tsx expects
        response = {
            'batch_id': batch_id,
            'batch_metadata': {
                'job_name': parent_job.get('name', 'Unnamed Batch'),
                'protein_name': parent_job.get('input_data', {}).get('protein_name', 'Unknown'),
                'created_at': parent_job.get('created_at'),
                'total_ligands': total_children
            },
            'total_children': total_children,
            'completed_children': completed_children, 
            'failed_children': failed_children,
            'running_children': running_children,
            'child_results': child_results,
            'status': parent_job.get('status', 'unknown'),
            'created_at': parent_job.get('created_at'),
            'aggregated_metrics': {
                'success_rate': (completed_children / total_children * 100) if total_children > 0 else 0,
                'completion_rate': ((completed_children + failed_children) / total_children * 100) if total_children > 0 else 0
            }
        }
        
        logger.info(f"✅ Returning batch results: {total_children} children, {completed_children} completed")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting batch results for {batch_id}: {e}")
        raise HTTPException(500, f"Failed to get batch results: {str(e)}")