"""
Job Orchestration API for GKE
Handles job submission to Cloud Tasks for GPU processing
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import logging

from services.job_submission_service import job_submission_service
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/jobs", tags=["Job Orchestration"])

# ===== REQUEST/RESPONSE MODELS =====

class IndividualPredictionRequest(BaseModel):
    """Request for individual Boltz-2 prediction"""
    protein_sequence: str = Field(..., min_length=10, max_length=5000)
    ligand_smiles: str = Field(..., min_length=1, max_length=500)
    ligand_name: Optional[str] = Field(None, max_length=100)
    user_id: str = Field(default="anonymous")
    priority: Literal["normal", "high"] = Field(default="normal")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class BatchPredictionRequest(BaseModel):
    """Request for batch Boltz-2 predictions"""
    batch_name: str = Field(..., max_length=200)
    protein_sequence: str = Field(..., min_length=10, max_length=5000)
    ligands: List[Dict[str, str]] = Field(..., min_items=1, max_items=1000)
    user_id: str = Field(default="anonymous")
    max_concurrent: int = Field(default=10, ge=1, le=50)
    priority: Literal["normal", "high"] = Field(default="normal")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class JobResponse(BaseModel):
    """Response for job submission"""
    job_id: str
    status: str
    job_type: str
    created_at: str
    estimated_completion_time: Optional[str] = None
    queue_position: Optional[int] = None

class BatchResponse(BaseModel):
    """Response for batch submission"""
    batch_id: str
    status: str
    total_ligands: int
    queued_jobs: int
    estimated_completion_time: Optional[str] = None

class JobStatusResponse(BaseModel):
    """Detailed job status response"""
    job_id: str
    job_type: str
    status: str
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: Optional[Dict[str, int]] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ===== ENDPOINTS =====

@router.post("/predict", response_model=JobResponse)
async def submit_individual_prediction(
    request: IndividualPredictionRequest,
    background_tasks: BackgroundTasks
) -> JobResponse:
    """
    Submit an individual Boltz-2 prediction job
    
    This endpoint:
    1. Creates a job record in Firestore
    2. Queues the job in Cloud Tasks
    3. Returns job ID for tracking
    """
    try:
        logger.info(f"📝 Submitting individual prediction for user {request.user_id}")
        
        # Submit job through service
        result = await job_submission_service.submit_individual_job(
            protein_sequence=request.protein_sequence,
            ligand_smiles=request.ligand_smiles,
            ligand_name=request.ligand_name,
            user_id=request.user_id,
            parameters=request.parameters,
            priority=request.priority
        )
        
        return JobResponse(
            job_id=result["job_id"],
            status=result["status"],
            job_type="INDIVIDUAL",
            created_at=datetime.utcnow().isoformat(),
            estimated_completion_time=result.get("estimated_completion_time"),
            queue_position=result.get("queue_position")
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to submit individual prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/batch", response_model=BatchResponse)
async def submit_batch_prediction(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks
) -> BatchResponse:
    """
    Submit a batch of Boltz-2 predictions
    
    This endpoint:
    1. Creates batch parent and child job records
    2. Queues jobs respecting max_concurrent limit
    3. Returns batch ID for tracking
    """
    try:
        logger.info(f"📦 Submitting batch '{request.batch_name}' with {len(request.ligands)} ligands")
        
        # Validate ligands
        for idx, ligand in enumerate(request.ligands):
            if "smiles" not in ligand:
                raise ValueError(f"Ligand {idx} missing required 'smiles' field")
        
        # Submit batch through service
        result = await job_submission_service.submit_batch_job(
            batch_name=request.batch_name,
            protein_sequence=request.protein_sequence,
            ligands=request.ligands,
            user_id=request.user_id,
            parameters=request.parameters,
            max_concurrent=request.max_concurrent,
            priority=request.priority
        )
        
        return BatchResponse(
            batch_id=result["batch_id"],
            status=result["status"],
            total_ligands=result["total_ligands"],
            queued_jobs=result["queued_jobs"],
            estimated_completion_time=result.get("estimated_completion_time")
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to submit batch prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get detailed status of a job or batch
    
    Returns current status, progress, and results if completed
    """
    try:
        # Get job from database
        job = unified_job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Format response based on job type
        response = JobStatusResponse(
            job_id=job["job_id"],
            job_type=job["job_type"],
            status=job["status"],
            created_at=job["created_at"].isoformat() if hasattr(job["created_at"], 'isoformat') else str(job["created_at"]),
            updated_at=job.get("updated_at", job["created_at"]).isoformat() if hasattr(job.get("updated_at", job["created_at"]), 'isoformat') else str(job.get("updated_at", job["created_at"])),
            started_at=job.get("started_at").isoformat() if job.get("started_at") and hasattr(job.get("started_at"), 'isoformat') else None,
            completed_at=job.get("completed_at").isoformat() if job.get("completed_at") and hasattr(job.get("completed_at"), 'isoformat') else None,
            error=job.get("error")
        )
        
        # Add progress for batch jobs
        if job["job_type"] == "BATCH_PARENT":
            response.progress = job.get("progress")
        
        # Add results if completed
        if job["status"] == "completed":
            if job["job_type"] == "BATCH_PARENT":
                response.results = job.get("batch_results")
            else:
                response.results = job.get("results")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/{batch_id}/children")
async def get_batch_children(
    batch_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get all child jobs for a batch
    
    Returns list of child jobs with their current status
    """
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        # Build query
        query = db.collection('jobs').where('batch_parent_id', '==', batch_id)
        
        if status:
            query = query.where('status', '==', status)
        
        query = query.limit(limit)
        
        # Get children
        children = []
        for doc in query.stream():
            child_data = doc.to_dict()
            children.append({
                "job_id": child_data["job_id"],
                "batch_index": child_data.get("batch_index"),
                "status": child_data["status"],
                "ligand_name": child_data["input_data"].get("ligand_name"),
                "created_at": str(child_data["created_at"]),
                "results": child_data.get("results") if child_data["status"] == "completed" else None
            })
        
        # Sort by batch index
        children.sort(key=lambda x: x.get("batch_index", 0))
        
        return {
            "batch_id": batch_id,
            "total_children": len(children),
            "children": children
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get batch children: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/retry")
async def retry_failed_job(job_id: str) -> JobResponse:
    """
    Retry a failed job
    
    Re-queues a failed job for processing
    """
    try:
        # Get job
        job = unified_job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if job["status"] not in ["failed", "error"]:
            raise HTTPException(status_code=400, detail=f"Job is not in failed state (current: {job['status']})")
        
        # Reset job status
        unified_job_manager.update_job_status(job_id, "pending", None)
        
        # Re-queue job
        from services.job_submission_service import job_submission_service
        
        task = job_submission_service._create_task(
            job_id=job_id,
            job_type=job["job_type"],
            batch_id=job.get("batch_parent_id"),
            priority="normal"
        )
        
        queue = job_submission_service.standard_queue
        response = job_submission_service.tasks_client.create_task(
            request={
                "parent": queue,
                "task": task
            }
        )
        
        # Update job status
        unified_job_manager.update_job_status(job_id, "queued", {
            "retry_attempt": job.get("retry_attempt", 0) + 1,
            "retried_at": datetime.utcnow().isoformat()
        })
        
        return JobResponse(
            job_id=job_id,
            status="queued",
            job_type=job["job_type"],
            created_at=str(job["created_at"]),
            estimated_completion_time=None,
            queue_position=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/stats")
async def get_queue_statistics() -> Dict[str, Any]:
    """
    Get queue statistics
    
    Returns current queue depth and processing stats
    """
    try:
        from google.cloud import tasks_v2
        
        client = tasks_v2.CloudTasksClient()
        project_id = "om-models"
        location = "us-central1"
        
        # Get standard queue stats
        standard_queue_path = client.queue_path(project_id, location, "gpu-job-queue")
        standard_queue = client.get_queue(request={"name": standard_queue_path})
        
        # Get priority queue stats
        priority_queue_path = client.queue_path(project_id, location, "gpu-job-queue-high")
        priority_queue = client.get_queue(request={"name": priority_queue_path})
        
        return {
            "standard_queue": {
                "name": "gpu-job-queue",
                "state": standard_queue.state.name,
                "tasks_count": standard_queue.stats.tasks_count if standard_queue.stats else 0,
                "max_dispatches_per_second": standard_queue.rate_limits.max_dispatches_per_second,
                "max_concurrent_dispatches": standard_queue.rate_limits.max_concurrent_dispatches
            },
            "priority_queue": {
                "name": "gpu-job-queue-high",
                "state": priority_queue.state.name,
                "tasks_count": priority_queue.stats.tasks_count if priority_queue.stats else 0,
                "max_dispatches_per_second": priority_queue.rate_limits.max_dispatches_per_second,
                "max_concurrent_dispatches": priority_queue.rate_limits.max_concurrent_dispatches
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))