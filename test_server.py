#!/usr/bin/env python3
"""
Simple test server for async prediction API
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OMTX-Hub Async Prediction Test API",
    description="Test API for async GPU predictions with Cloud Run Jobs"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models
class PredictionRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, max_length=5000)
    ligand_smiles: str = Field(..., min_length=1, max_length=500)
    ligand_name: Optional[str] = Field(None, max_length=100)
    user_id: Optional[str] = Field(None, max_length=50)

class BatchPredictionRequest(BaseModel):
    protein_sequence: str = Field(..., min_length=1, max_length=5000)
    ligands: List[Dict[str, str]] = Field(..., min_items=1, max_items=10)
    user_id: Optional[str] = Field(None, max_length=50)
    batch_name: Optional[str] = Field(None, max_length=100)

# In-memory job storage for testing
jobs_db = {}
batches_db = {}

@app.get("/")
async def root():
    return {"message": "OMTX-Hub Async Prediction Test API", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/predict/async")
async def submit_prediction_job(request: PredictionRequest) -> Dict[str, Any]:
    """Submit a protein-ligand prediction job for async GPU processing"""
    try:
        # Generate unique job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"📤 Submitting async prediction job: {job_id}")
        
        # Store job in memory (in production this would be Firestore)
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "submitted",
            "protein_sequence": request.protein_sequence,
            "ligand_smiles": request.ligand_smiles,
            "ligand_name": request.ligand_name,
            "user_id": request.user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # TODO: Here we would submit to Cloud Run Jobs
        # For now, just simulate the submission
        logger.info(f"   ✅ Job submitted to Cloud Run Jobs (simulated)")
        
        return {
            "job_id": job_id,
            "status": "submitted",
            "message": "Job submitted for GPU processing (simulation)",
            "estimated_completion_time": "1-3 minutes",
            "status_url": f"/api/v1/jobs/{job_id}",
            "submitted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Job submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predict/batch/async")
async def submit_batch_prediction_job(request: BatchPredictionRequest) -> Dict[str, Any]:
    """Submit multiple protein-ligand predictions as a batch"""
    try:
        # Generate unique batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"📦 Submitting batch job: {batch_id} ({len(request.ligands)} ligands)")
        
        # Store batch in memory
        job_ids = []
        for i, ligand in enumerate(request.ligands):
            job_id = f"{batch_id}_{i+1}"
            job_ids.append(job_id)
            
            jobs_db[job_id] = {
                "job_id": job_id,
                "status": "submitted",
                "batch_parent_id": batch_id,
                "protein_sequence": request.protein_sequence,
                "ligand_smiles": ligand.get("smiles"),
                "ligand_name": ligand.get("name", f"ligand_{i+1}"),
                "user_id": request.user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        
        batches_db[batch_id] = {
            "batch_id": batch_id,
            "status": "processing",
            "total_jobs": len(request.ligands),
            "completed_jobs": 0,
            "failed_jobs": 0,
            "job_ids": job_ids,
            "user_id": request.user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        logger.info(f"   ✅ Batch submitted to Cloud Run Jobs (simulated)")
        
        return {
            "batch_id": batch_id,
            "total_jobs": len(request.ligands),
            "submitted_jobs": len(job_ids),
            "status": "processing",
            "message": f"Batch submitted with {len(job_ids)} jobs (simulation)",
            "estimated_completion_time": "2-5 minutes",
            "status_url": f"/api/v1/batches/{batch_id}",
            "jobs_url": f"/api/v1/batches/{batch_id}/jobs",
            "submitted_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Batch submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status and results of a submitted prediction job"""
    try:
        if job_id not in jobs_db:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs_db[job_id]
        
        # Simulate job completion (in production, this would be updated by Cloud Run Job)
        import time
        created_at = job["created_at"]
        elapsed = (datetime.utcnow() - created_at).total_seconds()
        
        if elapsed > 30 and job["status"] == "submitted":  # After 30 seconds, mark as completed
            job["status"] = "completed"
            job["completed_at"] = datetime.utcnow()
            job["results"] = {
                "affinity": -8.2,
                "confidence": 0.78,
                "boltz_confidence": 0.72,
                "ptm": 0.68,
                "iptm": 0.70,
                "processing_time_seconds": elapsed,
                "real_boltz2": False,
                "note": "Simulation - would be real GPU prediction in production"
            }
        elif elapsed > 10 and job["status"] == "submitted":  # After 10 seconds, mark as processing
            job["status"] = "processing"
            job["processing_started_at"] = datetime.utcnow()
        
        return {
            "job_id": job_id,
            "status": job["status"],
            "results": job.get("results"),
            "created_at": job["created_at"],
            "completed_at": job.get("completed_at"),
            "processing_time_seconds": job.get("results", {}).get("processing_time_seconds")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/batches/{batch_id}")
async def get_batch_status(batch_id: str) -> Dict[str, Any]:
    """Get the status of a batch prediction job"""
    try:
        if batch_id not in batches_db:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch = batches_db[batch_id]
        job_ids = batch["job_ids"]
        
        # Update batch status based on individual jobs
        completed_jobs = 0
        failed_jobs = 0
        job_statuses = []
        
        for job_id in job_ids:
            if job_id in jobs_db:
                job = jobs_db[job_id]
                # Trigger job status update (simulated)
                await get_job_status(job_id)  # This will update the job status
                job = jobs_db[job_id]  # Get updated job
                
                if job["status"] == "completed":
                    completed_jobs += 1
                elif job["status"] == "failed":
                    failed_jobs += 1
                    
                job_statuses.append({
                    "job_id": job_id,
                    "status": job["status"],
                    "results": job.get("results")
                })
        
        # Update batch
        batch["completed_jobs"] = completed_jobs
        batch["failed_jobs"] = failed_jobs
        
        if completed_jobs == len(job_ids):
            batch["status"] = "completed"
            batch["completed_at"] = datetime.utcnow()
        
        progress_percentage = (completed_jobs / len(job_ids)) * 100
        
        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "total_jobs": batch["total_jobs"],
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "progress_percentage": progress_percentage,
            "created_at": batch["created_at"],
            "completed_at": batch.get("completed_at"),
            "jobs": job_statuses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/jobs")
async def list_jobs(user_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """List recent jobs for a user or all jobs"""
    try:
        jobs = list(jobs_db.values())
        
        if user_id:
            jobs = [job for job in jobs if job.get("user_id") == user_id]
        
        # Sort by created_at descending
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        jobs = jobs[:limit]
        
        return {
            "jobs": [
                {
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "job_type": "BATCH_CHILD" if job.get("batch_parent_id") else "INDIVIDUAL",
                    "created_at": job["created_at"],
                    "completed_at": job.get("completed_at"),
                    "user_id": job.get("user_id")
                }
                for job in jobs
            ],
            "count": len(jobs),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)