"""
Async Prediction API using Cloud Run Jobs
Handles job submission and status checking for GPU predictions
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from services.cloud_tasks_service import CloudTasksService

# Configure logging
logger = logging.getLogger(__name__)

# API Router
router = APIRouter(prefix="/api/v1", tags=["async-predictions"])

# Pydantic models
class PredictionRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, max_length=5000)
    ligand_smiles: str = Field(..., min_length=1, max_length=500)
    ligand_name: Optional[str] = Field(None, max_length=100)
    user_id: Optional[str] = Field(None, max_length=50)

class BatchPredictionRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, max_length=5000)
    ligands: List[Dict[str, str]] = Field(..., min_items=1, max_items=100)
    user_id: Optional[str] = Field(None, max_length=50)
    batch_name: Optional[str] = Field(None, max_length=100)

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    results: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None
    files_available: Optional[bool] = None
    gcp_results_path: Optional[str] = None

# Initialize services - Use Cloud Tasks for queue management
tasks_service = CloudTasksService()

@router.post("/predict/async", summary="Submit async prediction job")
async def submit_prediction_job(request: PredictionRequest) -> Dict[str, Any]:
    """
    Submit a protein-ligand prediction job for async GPU processing
    
    Returns job ID immediately - use /jobs/{job_id} to check status
    """
    try:
        # Generate unique job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"📤 Submitting async prediction job: {job_id}")
        
        # Submit to Cloud Tasks queue for processing
        result = tasks_service.submit_prediction_task(
            job_id=job_id,
            protein_sequence=request.protein_sequence,
            ligand_smiles=request.ligand_smiles,
            ligand_name=request.ligand_name,
            user_id=request.user_id
        )
        
        if result["success"]:
            return {
                "job_id": job_id,
                "status": "submitted",
                "message": "Job submitted for GPU processing",
                "estimated_completion_time": "1-3 minutes",
                "status_url": f"/api/v1/jobs/{job_id}",
                "submitted_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to submit job: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Job submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/batch/async", summary="Submit async batch prediction")
async def submit_batch_prediction_job(request: BatchPredictionRequest) -> Dict[str, Any]:
    """
    Submit multiple protein-ligand predictions as a batch for async processing
    
    Returns batch ID immediately - individual jobs are processed in parallel
    """
    try:
        # Generate unique batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"📦 Submitting batch job: {batch_id} ({len(request.ligands)} ligands)")
        
        # Submit batch to Cloud Tasks queue for parallel processing
        result = tasks_service.submit_batch_tasks(
            batch_id=batch_id,
            protein_sequence=request.protein_sequence,
            ligands=request.ligands,
            user_id=request.user_id
        )
        
        if result["success"]:
            return {
                "batch_id": batch_id,
                "total_jobs": result["total_jobs"],
                "submitted_jobs": result["submitted_jobs"],
                "status": "processing",
                "message": f"Batch submitted with {result['submitted_jobs']} jobs",
                "estimated_completion_time": "2-5 minutes",
                "status_url": f"/api/v1/batches/{batch_id}",
                "jobs_url": f"/api/v1/batches/{batch_id}/jobs",
                "submitted_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to submit batch: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"❌ Batch submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}", summary="Get job status and results")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the status and results of a submitted prediction job

    Returns job status, results (if completed), and processing information
    """
    try:
        # Get job directly from Firestore
        from google.cloud import firestore
        db_client = firestore.Client()

        job_doc = db_client.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            raise HTTPException(status_code=404, detail="Job not found")

        job_data = job_doc.to_dict()

        # Extract results from output_data or legacy results field
        output_data = job_data.get("output_data", {})
        results = output_data.get("results", job_data.get("results", {}))

        # Enhanced response with file information
        response_data = {
            "job_id": job_id,
            "status": job_data.get("status"),
            "results": results,
            "created_at": job_data.get("created_at"),
            "completed_at": job_data.get("completed_at"),
            "processing_time_seconds": job_data.get("execution_time_seconds") or job_data.get("processing_time_seconds")
        }

        # Add file information if available
        if output_data.get("files_stored_to_gcp"):
            response_data["files_available"] = True
            response_data["gcp_results_path"] = output_data.get("gcp_results_path")

        return JobStatusResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batches/{batch_id}", summary="Get batch status")
async def get_batch_status(batch_id: str) -> Dict[str, Any]:
    """
    Get the status of a batch prediction job
    
    Returns overall batch progress and individual job statuses
    """
    try:
        from google.cloud import firestore
        db_client = firestore.Client()
        
        # Get batch document
        batch_doc = db_client.collection("batches").document(batch_id).get()
        
        if not batch_doc.exists:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch_data = batch_doc.to_dict()
        
        # Get individual job statuses
        job_ids = batch_data.get("job_ids", [])
        job_statuses = []

        for job_id in job_ids:
            job_doc = db_client.collection("jobs").document(job_id).get()
            if job_doc.exists:
                job_data = job_doc.to_dict()
                output_data = job_data.get("output_data", {})
                results = output_data.get("results", job_data.get("results", {}))

                job_statuses.append({
                    "job_id": job_id,
                    "status": job_data.get("status"),
                    "results": results
                })
        
        return {
            "batch_id": batch_id,
            "status": batch_data.get("status"),
            "total_jobs": batch_data.get("total_jobs", 0),
            "completed_jobs": batch_data.get("completed_jobs", 0),
            "failed_jobs": batch_data.get("failed_jobs", 0),
            "progress_percentage": (batch_data.get("completed_jobs", 0) / max(batch_data.get("total_jobs", 1), 1)) * 100,
            "created_at": batch_data.get("created_at"),
            "completed_at": batch_data.get("completed_at"),
            "jobs": job_statuses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", summary="List user jobs")
async def list_jobs(user_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """
    List recent jobs for a user or all jobs (admin)
    """
    try:
        from google.cloud import firestore
        db_client = firestore.Client()
        
        query = db_client.collection("jobs").order_by("created_at", direction=firestore.Query.DESCENDING)
        
        if user_id:
            query = query.where("user_id", "==", user_id)
        
        query = query.limit(limit)
        
        docs = query.stream()
        jobs = []
        
        for doc in docs:
            job_data = doc.to_dict()
            jobs.append({
                "job_id": doc.id,
                "status": job_data.get("status"),
                "job_type": job_data.get("job_type"),
                "created_at": job_data.get("created_at"),
                "completed_at": job_data.get("completed_at"),
                "processing_time_seconds": job_data.get("processing_time_seconds"),
                "user_id": job_data.get("user_id")
            })
        
        return {
            "jobs": jobs,
            "count": len(jobs),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}", summary="Cancel job")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel a running job (if possible)
    """
    try:
        from google.cloud import firestore
        db_client = firestore.Client()
        
        # Update job status to cancelled
        job_ref = db_client.collection("jobs").document(job_id)
        job_doc = job_ref.get()
        
        if not job_doc.exists:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job_doc.to_dict()
        
        if job_data.get("status") in ["completed", "failed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Job cannot be cancelled")
        
        job_ref.update({
            "status": "cancelled",
            "cancelled_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))