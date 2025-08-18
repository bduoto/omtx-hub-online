"""
Background Processor Control API
Allows safe control of job processing with NO Modal execution limits
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from services.safe_background_processor import safe_background_processor
from database.unified_job_manager import unified_job_manager

router = APIRouter(prefix="/api/v3/processor", tags=["Background Processor"])

class ProcessorStatus(BaseModel):
    processing: bool
    active_jobs: int
    max_concurrent_submissions: int
    modal_execution_limit: str
    safety_enabled: bool
    batch_support: str

class PendingJobsResponse(BaseModel):
    total_pending: int
    jobs: List[Dict[str, Any]]
    modal_scaling: str

@router.get("/status", response_model=ProcessorStatus)
async def get_processor_status():
    """Get background processor status - NO LIMITS on Modal execution"""
    
    status = safe_background_processor.get_status()
    
    return ProcessorStatus(
        processing=status['processing'],
        active_jobs=status['active_modal_jobs'],
        max_concurrent_submissions=status['max_concurrent_submissions'],
        modal_execution_limit=status['modal_execution_limit'],
        safety_enabled=status['safety_enabled'],
        batch_support=status['batch_support']
    )

@router.post("/start")
async def start_processor():
    """Start safe background processor - supports unlimited Modal scaling"""
    
    if safe_background_processor.processing:
        return {
            "message": "Processor already running",
            "status": safe_background_processor.get_status()
        }
    
    # Start in background
    import asyncio
    asyncio.create_task(safe_background_processor.start_processing())
    
    return {
        "message": "Safe background processor started",
        "features": [
            "✅ NO LIMITS on Modal execution",
            "✅ 1500+ job batches fully supported", 
            "✅ Modal auto-scaling enabled",
            "✅ Safety controls for job submission",
            "✅ Only processes jobs from last 24 hours"
        ]
    }

@router.post("/stop")
async def stop_processor():
    """Stop background processor (existing Modal jobs continue running)"""
    
    safe_background_processor.stop_processing()
    
    return {
        "message": "Background processor stopped",
        "note": "Existing Modal jobs will continue running to completion",
        "active_modal_jobs": len(safe_background_processor.active_modal_jobs)
    }

@router.get("/pending-jobs", response_model=PendingJobsResponse)
async def get_pending_jobs():
    """Get pending jobs that would be processed - ALL will be submitted to Modal"""
    
    pending_jobs = await safe_background_processor._get_safe_pending_jobs()
    
    return PendingJobsResponse(
        total_pending=len(pending_jobs),
        jobs=[
            {
                "id": job.get('id', job.get('job_id')),
                "job_name": job.get('job_name', 'Unnamed'),
                "job_type": job.get('job_type', job.get('task_type')),
                "created_at": job.get('created_at'),
                "status": job.get('status'),
                "input_data_size": len(str(job.get('input_data', {})))
            }
            for job in pending_jobs[:20]  # Show first 20
        ],
        modal_scaling="UNLIMITED - All jobs will be submitted to Modal for auto-scaling"
    )

@router.post("/process-batch/{batch_id}")
async def process_specific_batch(batch_id: str):
    """Process a specific batch manually - NO Modal limits"""
    
    try:
        # Get batch details first
        from api.unified_batch_api import unified_batch_processor
        status_result = await unified_batch_processor.get_batch_status(batch_id)
        
        if 'error' in status_result:
            raise HTTPException(status_code=404, detail=status_result['error'])
        
        child_jobs = status_result.get('child_jobs', [])
        pending_jobs = [job for job in child_jobs if job.get('status') == 'pending']
        
        if not pending_jobs:
            return {
                "message": f"No pending jobs found in batch {batch_id}",
                "batch_id": batch_id,
                "total_jobs": len(child_jobs),
                "pending_jobs": 0
            }
        
        # Process all pending jobs (no limits)
        processed = 0
        for job in pending_jobs:
            try:
                await safe_background_processor._process_single_job(job)
                processed += 1
                # Small delay to avoid overwhelming submission
                import asyncio
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"❌ Failed to process job {job.get('id')}: {e}")
        
        return {
            "message": f"Submitted {processed} jobs from batch {batch_id} to Modal",
            "batch_id": batch_id,
            "total_jobs": len(child_jobs),
            "jobs_submitted": processed,
            "modal_scaling": "UNLIMITED - Modal will auto-scale to handle all jobs",
            "note": "Jobs are now running on Modal with unlimited scaling"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/force-process-all")
async def force_process_all_pending():
    """Force process ALL pending jobs - supports massive batches"""
    
    try:
        pending_jobs = await safe_background_processor._get_safe_pending_jobs()
        
        if not pending_jobs:
            return {
                "message": "No pending jobs found",
                "total_processed": 0
            }
        
        processed = 0
        batch_jobs = 0
        individual_jobs = 0
        
        for job in pending_jobs:
            try:
                await safe_background_processor._process_single_job(job)
                processed += 1
                
                # Count job types
                job_type = str(job.get('job_type', '')).upper()
                if 'BATCH' in job_type:
                    batch_jobs += 1
                else:
                    individual_jobs += 1
                    
                # Small delay between submissions
                import asyncio
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"❌ Failed to process job {job.get('id')}: {e}")
        
        return {
            "message": f"Force processed {processed} pending jobs",
            "total_processed": processed,
            "batch_jobs": batch_jobs,
            "individual_jobs": individual_jobs,
            "modal_scaling": "UNLIMITED - All jobs submitted to Modal for auto-scaling",
            "performance": "Modal will handle 1500+ job batches efficiently",
            "note": "All jobs are now running on Modal's auto-scaling infrastructure"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/modal-stats")
async def get_modal_stats():
    """Get Modal execution statistics"""
    
    return {
        "modal_execution_limit": "UNLIMITED",
        "auto_scaling": "ENABLED", 
        "batch_support": "1500+ jobs fully supported",
        "concurrent_jobs": "No backend limits - Modal handles scaling",
        "gpu_allocation": "Modal manages A100 GPU allocation automatically",
        "performance": "Sub-linear scaling for large batches",
        "active_tracked_jobs": len(safe_background_processor.active_modal_jobs),
        "note": "Background processor only limits submission rate (10/batch), not Modal execution"
    }