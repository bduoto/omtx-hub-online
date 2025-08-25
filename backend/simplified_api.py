"""
Simplified API for OMTX-Hub
Handles core endpoints needed by frontend
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OMTX-Hub API",
    description="Simplified API for Boltz-2 predictions",
    version="1.0.0"
)

# Add CORS middleware - CRITICAL for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo
jobs_db = {}
batches_db = {}

# Pydantic models
class PredictionRequest(BaseModel):
    model: str = Field(default="boltz2")
    protein_sequence: str = Field(..., min_length=1)
    ligand_smiles: str = Field(..., min_length=1)
    job_name: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class BatchPredictionRequest(BaseModel):
    model: str = Field(default="boltz2")
    batch_name: str
    protein_sequence: str
    ligands: List[Dict[str, str]]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    max_concurrent: int = Field(default=5)
    priority: str = Field(default="normal")

class JobResponse(BaseModel):
    job_id: str
    status: str
    model: str
    job_name: Optional[str]
    created_at: datetime
    message: Optional[str] = None

class BatchResponse(BaseModel):
    batch_id: str
    status: str
    model: str
    total_jobs: int
    message: Optional[str] = None

# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Main prediction endpoint
@app.post("/api/v1/predict", response_model=JobResponse)
async def submit_prediction(request: PredictionRequest):
    """Submit a single prediction job"""
    try:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Store job
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "model": request.model,
            "job_name": request.job_name,
            "protein_sequence": request.protein_sequence,
            "ligand_smiles": request.ligand_smiles,
            "created_at": datetime.utcnow(),
            "user_id": "demo_user"
        }
        
        logger.info(f"✅ Job submitted: {job_id}")
        
        return JobResponse(
            job_id=job_id,
            status="processing",
            model=request.model,
            job_name=request.job_name,
            created_at=datetime.utcnow(),
            message="Job submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Batch prediction endpoint
@app.post("/api/v1/predict/batch", response_model=BatchResponse)
async def submit_batch_prediction(request: BatchPredictionRequest):
    """Submit a batch prediction job"""
    try:
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        # Create batch
        batches_db[batch_id] = {
            "batch_id": batch_id,
            "status": "processing",
            "model": request.model,
            "batch_name": request.batch_name,
            "total_jobs": len(request.ligands),
            "completed_jobs": 0,
            "created_at": datetime.utcnow(),
            "user_id": "demo_user"
        }
        
        # Create individual jobs
        job_ids = []
        for i, ligand in enumerate(request.ligands):
            job_id = f"{batch_id}_job_{i+1}"
            jobs_db[job_id] = {
                "job_id": job_id,
                "status": "processing",
                "model": request.model,
                "batch_id": batch_id,
                "protein_sequence": request.protein_sequence,
                "ligand_smiles": ligand.get("smiles"),
                "ligand_name": ligand.get("name", f"ligand_{i+1}"),
                "created_at": datetime.utcnow()
            }
            job_ids.append(job_id)
        
        batches_db[batch_id]["job_ids"] = job_ids
        
        logger.info(f"✅ Batch submitted: {batch_id} with {len(job_ids)} jobs")
        
        return BatchResponse(
            batch_id=batch_id,
            status="processing",
            model=request.model,
            total_jobs=len(request.ligands),
            message=f"Batch submitted with {len(request.ligands)} jobs"
        )
        
    except Exception as e:
        logger.error(f"Error submitting batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# List jobs endpoint - FIXED for frontend
@app.get("/api/v1/jobs")
async def list_jobs(
    user_id: str = Query(default="current_user"),
    limit: int = Query(default=200, ge=1, le=500),
    page: int = Query(default=1, ge=1)
):
    """List user jobs - fixed for frontend compatibility"""
    try:
        # Return sample data for demo
        sample_jobs = []
        
        # Add some completed jobs
        for i in range(5):
            job_id = f"demo_job_{i+1}"
            sample_jobs.append({
                "job_id": job_id,
                "status": "completed",
                "model": "boltz2",
                "job_name": f"Demo Job {i+1}",
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "results": {
                    "affinity": round(random.uniform(-10, -5), 2),
                    "confidence": round(random.uniform(0.7, 0.95), 2)
                }
            })
        
        # Add actual jobs from memory
        for job in list(jobs_db.values())[:limit]:
            sample_jobs.append({
                "job_id": job["job_id"],
                "status": job["status"],
                "model": job.get("model", "boltz2"),
                "job_name": job.get("job_name"),
                "created_at": job["created_at"].isoformat()
            })
        
        return {
            "jobs": sample_jobs,
            "total": len(sample_jobs),
            "page": page,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        # Return empty list instead of error
        return {
            "jobs": [],
            "total": 0,
            "page": page,
            "limit": limit
        }

# Get job status
@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and results"""
    if job_id in jobs_db:
        job = jobs_db[job_id]
        
        # Simulate completion after some time
        created_at = job["created_at"]
        elapsed = (datetime.utcnow() - created_at).total_seconds()
        
        if elapsed > 10 and job["status"] == "processing":
            job["status"] = "completed"
            job["completed_at"] = datetime.utcnow()
            job["results"] = {
                "affinity": round(random.uniform(-10, -5), 2),
                "confidence": round(random.uniform(0.7, 0.95), 2),
                "ptm": round(random.uniform(0.6, 0.8), 2),
                "iptm": round(random.uniform(0.65, 0.85), 2)
            }
        
        return job
    else:
        # Return a mock completed job for demo
        return {
            "job_id": job_id,
            "status": "completed",
            "model": "boltz2",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "results": {
                "affinity": -7.5,
                "confidence": 0.85,
                "ptm": 0.72,
                "iptm": 0.75
            }
        }

# List batches
@app.get("/api/v1/batches")
async def list_batches(
    user_id: str = Query(default="current_user"),
    limit: int = Query(default=200)
):
    """List user batches"""
    try:
        sample_batches = []
        
        # Add actual batches
        for batch in list(batches_db.values())[:limit]:
            sample_batches.append({
                "batch_id": batch["batch_id"],
                "status": batch["status"],
                "batch_name": batch.get("batch_name"),
                "total_jobs": batch.get("total_jobs", 0),
                "completed_jobs": batch.get("completed_jobs", 0),
                "created_at": batch["created_at"].isoformat()
            })
        
        return {
            "batches": sample_batches,
            "total": len(sample_batches)
        }
        
    except Exception as e:
        logger.error(f"Error listing batches: {e}")
        return {
            "batches": [],
            "total": 0
        }

# Get batch status
@app.get("/api/v1/batches/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get batch status"""
    if batch_id in batches_db:
        batch = batches_db[batch_id]
        
        # Update completion status
        if "job_ids" in batch:
            completed = sum(1 for jid in batch["job_ids"] 
                          if jobs_db.get(jid, {}).get("status") == "completed")
            batch["completed_jobs"] = completed
            
            if completed == batch["total_jobs"]:
                batch["status"] = "completed"
        
        return batch
    else:
        return {
            "batch_id": batch_id,
            "status": "completed",
            "total_jobs": 10,
            "completed_jobs": 10,
            "created_at": datetime.utcnow().isoformat()
        }

# Files endpoint for downloads
@app.get("/api/v1/files/{job_id}/{file_type}")
async def get_file(job_id: str, file_type: str):
    """Get job files (mock for demo)"""
    return {
        "job_id": job_id,
        "file_type": file_type,
        "url": f"https://storage.googleapis.com/hub-job-files/{job_id}/{file_type}",
        "content": "Mock file content for demo"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)