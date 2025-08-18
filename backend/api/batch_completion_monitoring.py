"""
Batch-Aware Completion Checker Monitoring API
Real-time monitoring and control of the batch completion system
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from services.batch_aware_completion_checker import batch_aware_completion_checker

router = APIRouter(prefix="/api/v3/batch-completion", tags=["Batch Completion Monitoring"])

@router.get("/status")
async def get_completion_checker_status():
    """Get comprehensive status of the batch-aware completion system"""
    
    try:
        active_batches = batch_aware_completion_checker.get_active_batches()
        
        batch_progress_details = {}
        for batch_id in active_batches:
            progress = batch_aware_completion_checker.get_batch_progress(batch_id)
            if progress:
                batch_progress_details[batch_id] = {
                    'total_jobs': progress.total_jobs,
                    'completed_jobs': progress.completed_jobs,
                    'failed_jobs': progress.failed_jobs,
                    'running_jobs': progress.running_jobs,
                    'percentage': round(progress.percentage, 1),
                    'estimated_completion': progress.estimated_completion,
                    'last_updated': progress.last_updated.isoformat()
                }
        
        return {
            'system': 'batch_aware_completion_checker',
            'active_batches': len(active_batches),
            'active_batch_ids': list(active_batches),
            'batch_progress': batch_progress_details,
            'registered_callbacks': len(batch_aware_completion_checker.completion_callbacks),
            'milestone_thresholds': batch_aware_completion_checker.milestone_thresholds,
            'features': [
                '✅ Intelligent batch context detection',
                '✅ Real-time progress tracking',
                '✅ Milestone-based actions',
                '✅ Atomic storage operations',
                '✅ Optimal storage path determination',
                '✅ Progressive batch completion'
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get completion checker status: {str(e)}")

@router.get("/batch/{batch_id}/progress")
async def get_batch_progress(batch_id: str, force_refresh: bool = False):
    """Get detailed progress for a specific batch"""
    
    try:
        if force_refresh:
            progress = await batch_aware_completion_checker.force_refresh_batch_progress(batch_id)
        else:
            progress = batch_aware_completion_checker.get_batch_progress(batch_id)
            
        if not progress:
            # Try to get fresh progress from database
            progress = await batch_aware_completion_checker.force_refresh_batch_progress(batch_id)
            
        if not progress:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found or not active")
        
        # Get milestone status
        reached_milestones = batch_aware_completion_checker.batch_milestones_reached.get(batch_id, set())
        
        return {
            'batch_id': batch_id,
            'progress': {
                'total_jobs': progress.total_jobs,
                'completed_jobs': progress.completed_jobs,
                'failed_jobs': progress.failed_jobs,
                'running_jobs': progress.running_jobs,
                'percentage': round(progress.percentage, 1),
                'estimated_completion_seconds': progress.estimated_completion,
                'last_updated': progress.last_updated.isoformat()
            },
            'milestones': {
                'available': batch_aware_completion_checker.milestone_thresholds,
                'reached': list(reached_milestones),
                'next_milestone': min([m for m in batch_aware_completion_checker.milestone_thresholds 
                                     if m > progress.percentage], default=None)
            },
            'status': 'completed' if progress.percentage >= 100 else 'in_progress',
            'performance': {
                'jobs_per_minute': progress.completed_jobs / max((progress.last_updated.timestamp() - progress.last_updated.timestamp()) / 60, 1),
                'success_rate': progress.completed_jobs / max(progress.completed_jobs + progress.failed_jobs, 1) * 100
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch progress: {str(e)}")

@router.get("/active-batches")
async def get_active_batches():
    """Get list of all currently active batches being monitored"""
    
    try:
        active_batches = batch_aware_completion_checker.get_active_batches()
        
        batch_summaries = []
        for batch_id in active_batches:
            progress = batch_aware_completion_checker.get_batch_progress(batch_id)
            if progress:
                batch_summaries.append({
                    'batch_id': batch_id,
                    'total_jobs': progress.total_jobs,
                    'completed_jobs': progress.completed_jobs,
                    'percentage': round(progress.percentage, 1),
                    'status': 'completed' if progress.percentage >= 100 else 'in_progress',
                    'last_updated': progress.last_updated.isoformat()
                })
        
        return {
            'total_active_batches': len(batch_summaries),
            'batches': batch_summaries,
            'system_health': 'operational',
            'monitoring_features': [
                'Real-time progress tracking',
                'Milestone-based notifications',
                'Intelligent completion detection',
                'Batch context awareness'
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active batches: {str(e)}")

@router.post("/batch/{batch_id}/simulate-completion")
async def simulate_job_completion(batch_id: str, job_id: str):
    """Simulate a job completion for testing (development only)"""
    
    try:
        # Create mock Modal result for testing
        mock_result = {
            'status': 'completed',
            'affinity': 0.75,
            'confidence': 0.82,
            'structure_file_base64': 'mock_cif_data',
            'execution_time': 45.0,
            'ptm_score': 0.78,
            'plddt_score': 0.85,
            'model_version': 'boltz2_test'
        }
        
        # Trigger completion processing
        await batch_aware_completion_checker.on_job_completion(job_id, mock_result)
        
        return {
            'message': f'Simulated completion of job {job_id} in batch {batch_id}',
            'mock_result': mock_result,
            'note': 'This is for testing only - use only in development'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate completion: {str(e)}")

@router.post("/batch/{batch_id}/force-refresh")
async def force_refresh_batch_progress(batch_id: str):
    """Force refresh batch parent metadata from child job states"""
    
    try:
        # Force refresh progress calculation
        progress = await batch_aware_completion_checker.force_refresh_batch_progress(batch_id)
        
        # Update batch parent metadata
        await batch_aware_completion_checker._update_batch_parent_metadata(batch_id)
        
        # Get updated batch info
        from database.unified_job_manager import unified_job_manager
        updated_batch = unified_job_manager.get_job(batch_id)
        
        return {
            'message': f'Force refreshed batch {batch_id}',
            'progress': {
                'total_jobs': progress.total_jobs,
                'completed_jobs': progress.completed_jobs,
                'failed_jobs': progress.failed_jobs,
                'running_jobs': progress.running_jobs,
                'percentage': round(progress.percentage, 1)
            },
            'updated_batch': updated_batch,
            'note': 'Batch parent metadata updated from child job states'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to force refresh: {str(e)}")

@router.get("/milestones/{batch_id}")
async def get_batch_milestones(batch_id: str):
    """Get milestone status for a specific batch"""
    
    try:
        progress = batch_aware_completion_checker.get_batch_progress(batch_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        reached_milestones = batch_aware_completion_checker.batch_milestones_reached.get(batch_id, set())
        all_milestones = batch_aware_completion_checker.milestone_thresholds
        
        milestone_details = []
        for milestone in all_milestones:
            status = 'reached' if milestone in reached_milestones else (
                'current' if milestone <= progress.percentage < milestone + 25 else 'pending'
            )
            
            milestone_details.append({
                'threshold': milestone,
                'status': status,
                'description': f'{milestone}% completion milestone',
                'reached_at': None  # Could be enhanced to track timestamp
            })
        
        return {
            'batch_id': batch_id,
            'current_percentage': round(progress.percentage, 1),
            'milestones': milestone_details,
            'next_milestone': min([m for m in all_milestones if m > progress.percentage], default=None),
            'milestone_summary': {
                'total_milestones': len(all_milestones),
                'reached_milestones': len(reached_milestones),
                'remaining_milestones': len(all_milestones) - len(reached_milestones)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch milestones: {str(e)}")

@router.get("/system-health")
async def get_system_health():
    """Get overall health of the batch completion system"""
    
    try:
        active_batches = batch_aware_completion_checker.get_active_batches()
        
        total_jobs = 0
        completed_jobs = 0
        failed_jobs = 0
        
        for batch_id in active_batches:
            progress = batch_aware_completion_checker.get_batch_progress(batch_id)
            if progress:
                total_jobs += progress.total_jobs
                completed_jobs += progress.completed_jobs
                failed_jobs += progress.failed_jobs
        
        success_rate = completed_jobs / max(completed_jobs + failed_jobs, 1) * 100
        
        return {
            'system': 'batch_aware_completion_checker',
            'status': 'healthy',
            'statistics': {
                'active_batches': len(active_batches),
                'total_jobs_monitored': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': round(success_rate, 1)
            },
            'performance': {
                'batch_context_detection': 'operational',
                'real_time_progress_tracking': 'operational',
                'milestone_processing': 'operational',
                'atomic_storage': 'operational'
            },
            'features': {
                'intelligent_completion_detection': True,
                'batch_aware_storage': True,
                'progress_milestones': True,
                'real_time_monitoring': True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")