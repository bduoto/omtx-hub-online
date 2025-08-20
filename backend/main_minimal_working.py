#!/usr/bin/env python3
"""
Minimal OMTX-Hub Backend - Guaranteed to work
Includes all missing endpoints that frontend needs
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, Query, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="OMTX-Hub Backend",
    version="4.0.0",
    description="Minimal working version with all missing endpoints"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for demo
MOCK_JOBS = [
    {
        "id": "job_001",
        "user_id": "demo-user",
        "status": "completed",
        "job_type": "protein_ligand_binding",
        "created_at": "2025-08-19T20:00:00Z",
        "completed_at": "2025-08-19T20:05:00Z",
        "protein_name": "Kinase Inhibitor Target",
        "ligand_name": "FDA-Approved Drug",
        "results": {
            "binding_affinity": -8.5,
            "confidence": 0.92
        }
    },
    {
        "id": "job_002", 
        "user_id": "demo-user",
        "status": "running",
        "job_type": "protein_structure_prediction",
        "created_at": "2025-08-19T20:10:00Z",
        "protein_name": "COVID-19 Antiviral Target",
        "results": None
    }
]

MOCK_BATCHES = [
    {
        "id": "batch_001",
        "user_id": "demo-user", 
        "status": "completed",
        "job_count": 50,
        "completed_jobs": 50,
        "created_at": "2025-08-19T19:00:00Z",
        "completed_at": "2025-08-19T19:30:00Z",
        "batch_name": "FDA Drug Screening",
        "description": "High-throughput screening of FDA-approved drugs"
    }
]

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "mode": "minimal_working"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OMTX-Hub Backend API",
        "version": "4.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/api/v4/jobs/unified",
            "/api/v4/jobs/ultra-fast", 
            "/api/v4/batches"
        ]
    }

# Missing endpoint 1: Unified jobs
@app.get("/api/v4/jobs/unified")
async def get_unified_jobs(
    user_id: str = Query("demo-user"),
    x_user_id: str = Header(None, alias="X-User-Id"),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """Get unified jobs and batches for user"""
    effective_user_id = x_user_id or user_id
    
    # Filter jobs for user
    user_jobs = [job for job in MOCK_JOBS if job["user_id"] == effective_user_id]
    user_batches = [batch for batch in MOCK_BATCHES if batch["user_id"] == effective_user_id]
    
    return {
        "jobs": user_jobs[offset:offset+limit],
        "batches": user_batches[offset:offset+limit],
        "total_jobs": len(user_jobs),
        "total_batches": len(user_batches),
        "user_id": effective_user_id,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(user_jobs) > offset + limit
        }
    }

# Missing endpoint 2: Ultra-fast jobs
@app.get("/api/v4/jobs/ultra-fast")
async def get_ultra_fast_jobs(
    user_id: str = Query("demo-user"),
    x_user_id: str = Header(None, alias="X-User-Id"),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """Get ultra-fast jobs for user"""
    effective_user_id = x_user_id or user_id
    
    # Filter for ultra-fast jobs (completed quickly)
    ultra_fast_jobs = [
        job for job in MOCK_JOBS 
        if job["user_id"] == effective_user_id and job["status"] == "completed"
    ]
    
    return {
        "jobs": ultra_fast_jobs[offset:offset+limit],
        "total": len(ultra_fast_jobs),
        "user_id": effective_user_id,
        "filter": "ultra-fast",
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(ultra_fast_jobs) > offset + limit
        }
    }

# Missing endpoint 3: Batches
@app.get("/api/v4/batches")
async def list_batches(
    user_id: str = Query("demo-user"),
    x_user_id: str = Header(None, alias="X-User-Id"),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """List batches for user"""
    effective_user_id = x_user_id or user_id
    
    # Filter batches for user
    user_batches = [batch for batch in MOCK_BATCHES if batch["user_id"] == effective_user_id]
    
    # Filter by status if provided
    if status:
        user_batches = [batch for batch in user_batches if batch["status"] == status]
    
    return {
        "batches": user_batches[offset:offset+limit],
        "total": len(user_batches),
        "user_id": effective_user_id,
        "filter": {"status": status} if status else None,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(user_batches) > offset + limit
        }
    }

# Additional endpoints that might be needed
@app.get("/api/v4/jobs/{job_id}")
async def get_job(job_id: str, user_id: str = Query("demo-user")):
    """Get specific job details"""
    job = next((job for job in MOCK_JOBS if job["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/v4/batches/{batch_id}")
async def get_batch(batch_id: str, user_id: str = Query("demo-user")):
    """Get specific batch details"""
    batch = next((batch for batch in MOCK_BATCHES if batch["id"] == batch_id), None)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting OMTX-Hub Backend (minimal) on port {port}")
    logger.info("✅ All missing endpoints included")
    logger.info("✅ Ready for frontend connection")
    logger.info("✅ Ready for demo data loading")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
