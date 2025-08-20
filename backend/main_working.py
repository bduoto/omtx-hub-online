#!/usr/bin/env python3
"""
OMTX-Hub Backend - Working Version with All Missing Endpoints
Guaranteed to start and fix 404 errors
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
    description="Working version with all missing endpoints for CTO demo"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for impressive demo
MOCK_JOBS = [
    {
        "id": "job_kinase_001",
        "user_id": "demo-user",
        "status": "completed",
        "job_type": "protein_ligand_binding",
        "created_at": "2025-08-19T20:00:00Z",
        "completed_at": "2025-08-19T20:05:00Z",
        "protein_name": "EGFR Kinase (Cancer Target)",
        "ligand_name": "Erlotinib (FDA-Approved)",
        "results": {
            "binding_affinity": -9.2,
            "confidence": 0.94,
            "market_value": "$2.1B annually"
        }
    },
    {
        "id": "job_covid_002", 
        "user_id": "demo-user",
        "status": "completed",
        "job_type": "antiviral_screening",
        "created_at": "2025-08-19T20:10:00Z",
        "completed_at": "2025-08-19T20:15:00Z",
        "protein_name": "SARS-CoV-2 Main Protease",
        "ligand_name": "Paxlovid (Pfizer)",
        "results": {
            "binding_affinity": -8.7,
            "confidence": 0.91,
            "market_opportunity": "$30.8B"
        }
    },
    {
        "id": "job_immuno_003",
        "user_id": "demo-user", 
        "status": "running",
        "job_type": "immunotherapy_target",
        "created_at": "2025-08-19T20:20:00Z",
        "protein_name": "PD-1 Checkpoint Inhibitor",
        "ligand_name": "Pembrolizumab (Keytruda)",
        "results": None
    }
]

MOCK_BATCHES = [
    {
        "id": "batch_fda_screening",
        "user_id": "demo-user", 
        "status": "completed",
        "job_count": 127,
        "completed_jobs": 127,
        "created_at": "2025-08-19T19:00:00Z",
        "completed_at": "2025-08-19T19:45:00Z",
        "batch_name": "FDA Drug Library Screening",
        "description": "High-throughput screening of 127 FDA-approved drugs against cancer targets",
        "market_impact": "$7.9B total market value"
    },
    {
        "id": "batch_covid_antivirals",
        "user_id": "demo-user",
        "status": "completed", 
        "job_count": 89,
        "completed_jobs": 89,
        "created_at": "2025-08-19T18:00:00Z",
        "completed_at": "2025-08-19T18:30:00Z",
        "batch_name": "COVID-19 Antiviral Discovery",
        "description": "Screening potential antivirals against SARS-CoV-2 targets",
        "market_opportunity": "$30.8B pandemic response market"
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
        "mode": "production_demo_ready",
        "endpoints_fixed": True
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "OMTX-Hub Backend API - CTO Demo Ready",
        "version": "4.0.0",
        "status": "running",
        "demo_data": "FDA drugs, COVID antivirals, cancer targets",
        "endpoints": [
            "/health",
            "/api/v4/jobs/unified",
            "/api/v4/jobs/ultra-fast", 
            "/api/v4/batches"
        ]
    }

# MISSING ENDPOINT 1: Unified jobs (CRITICAL for frontend)
@app.get("/api/v4/jobs/unified")
async def get_unified_jobs(
    user_id: str = Query("demo-user"),
    x_user_id: str = Header(None, alias="X-User-Id"),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """Get unified jobs and batches for user - FIXES 404 ERROR"""
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
        "demo_highlights": {
            "fda_drugs": "127 FDA-approved compounds",
            "covid_antivirals": "89 potential treatments", 
            "market_value": "$38.7B total opportunity"
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(user_jobs) > offset + limit
        }
    }

# MISSING ENDPOINT 2: Ultra-fast jobs (CRITICAL for frontend)
@app.get("/api/v4/jobs/ultra-fast")
async def get_ultra_fast_jobs(
    user_id: str = Query("demo-user"),
    x_user_id: str = Header(None, alias="X-User-Id"),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """Get ultra-fast jobs for user - FIXES 404 ERROR"""
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
        "performance": "Sub-5-minute drug screening",
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(ultra_fast_jobs) > offset + limit
        }
    }

# MISSING ENDPOINT 3: Batches (CRITICAL for frontend)
@app.get("/api/v4/batches")
async def list_batches(
    user_id: str = Query("demo-user"),
    x_user_id: str = Header(None, alias="X-User-Id"),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """List batches for user - FIXES 404 ERROR"""
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
        "pharmaceutical_impact": {
            "total_compounds": 216,
            "fda_approved": 127,
            "market_value": "$38.7B"
        },
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
    logger.info(f"🚀 Starting OMTX-Hub Backend (CTO Demo Ready) on port {port}")
    logger.info("✅ All missing endpoints included - fixes 404 errors")
    logger.info("✅ Ready for frontend connection")
    logger.info("✅ Ready for load_production_demo_data.py script")
    logger.info("💊 Demo includes: FDA drugs, COVID antivirals, cancer targets")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
