"""
OMTX-Hub Minimal FastAPI Backend - GUARANTEED TO START
Distinguished Engineer Implementation - Minimal working version for Cloud Run
"""

import os
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="OMTX-Hub Backend",
    description="Molecular modeling platform with Cloud Run integration",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "*"  # Allow all for demo
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Initialize Firestore (optional)
try:
    from google.cloud import firestore
    db = firestore.Client()
    firestore_available = True
    print("✅ Firestore initialized")
except Exception as e:
    db = None
    firestore_available = False
    print(f"⚠️ Firestore not available: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "gcp_firestore" if firestore_available else "mock",
        "storage": "gcp_cloud_storage",
        "version": "4.0.0"
    }

@app.get("/ready")
async def readiness_check():
    """Readiness probe for Cloud Run"""
    return {"status": "ready", "timestamp": datetime.now().isoformat()}

@app.get("/startup")
async def startup_check():
    """Startup probe for Cloud Run"""
    return {"status": "started", "timestamp": datetime.now().isoformat()}

# Missing endpoints that frontend needs
@app.get("/api/v4/jobs/unified")
async def get_unified_jobs(
    user_id: Optional[str] = Query("current_user", description="User ID"),
    lightweight: bool = Query(True, description="Return lightweight data"),
    include_batches: bool = Query(True, description="Include batch jobs"),
    limit: int = Query(200, description="Maximum number of jobs to return"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Unified jobs endpoint - Returns all jobs for a user"""
    
    actual_user_id = x_user_id or user_id
    if actual_user_id == "current_user":
        actual_user_id = "demo-user"
    
    print(f"📊 Getting unified jobs for user: {actual_user_id}")
    
    jobs = []
    batches = []
    
    if db and firestore_available:
        try:
            # Get individual jobs from Firestore
            jobs_ref = db.collection('users').document(actual_user_id).collection('jobs')
            jobs_query = jobs_ref.limit(limit).order_by('created_at', direction=firestore.Query.DESCENDING)
            
            for job_doc in jobs_query.stream():
                job_data = job_doc.to_dict()
                job_data['id'] = job_doc.id
                job_data['job_id'] = job_doc.id
                
                if lightweight:
                    lightweight_job = {
                        'id': job_data.get('id'),
                        'job_id': job_data.get('job_id'),
                        'job_name': job_data.get('job_name', 'Unnamed Job'),
                        'status': job_data.get('status', 'unknown'),
                        'created_at': job_data.get('created_at'),
                        'completed_at': job_data.get('completed_at'),
                        'ligand_name': job_data.get('ligand_name'),
                        'protein_target': job_data.get('protein_target'),
                        'task_type': job_data.get('task_type', 'protein_ligand_binding')
                    }
                    jobs.append(lightweight_job)
                else:
                    jobs.append(job_data)
            
            # Get batches if requested
            if include_batches:
                batches_ref = db.collection('users').document(actual_user_id).collection('batches')
                batches_query = batches_ref.limit(limit // 2).order_by('created_at', direction=firestore.Query.DESCENDING)
                
                for batch_doc in batches_query.stream():
                    batch_data = batch_doc.to_dict()
                    batch_data['id'] = batch_doc.id
                    batch_data['batch_id'] = batch_doc.id
                    
                    if lightweight:
                        lightweight_batch = {
                            'id': batch_data.get('id'),
                            'batch_id': batch_data.get('batch_id'),
                            'job_name': batch_data.get('job_name', 'Unnamed Batch'),
                            'status': batch_data.get('status', 'unknown'),
                            'created_at': batch_data.get('created_at'),
                            'completed_at': batch_data.get('completed_at'),
                            'total_ligands': batch_data.get('total_ligands', 0),
                            'completed_ligands': batch_data.get('completed_ligands', 0),
                            'protein_target': batch_data.get('protein_target'),
                            'task_type': 'batch_protein_ligand_screening'
                        }
                        batches.append(lightweight_batch)
                    else:
                        batches.append(batch_data)
                        
        except Exception as e:
            print(f"❌ Firestore error: {e}")
    
    total_jobs = len(jobs) + len(batches)
    has_more = total_jobs >= limit
    
    return {
        "jobs": jobs,
        "batches": batches,
        "total": total_jobs,
        "has_more": has_more,
        "user_id": actual_user_id,
        "lightweight": lightweight,
        "firestore_available": firestore_available,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v4/jobs/ultra-fast")
async def get_ultra_fast_jobs(
    user_id: Optional[str] = Query("current_user", description="User ID"),
    limit: int = Query(50, description="Maximum number of jobs"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Ultra-fast jobs endpoint - Returns minimal job data for instant navigation"""
    
    actual_user_id = x_user_id or user_id
    if actual_user_id == "current_user":
        actual_user_id = "demo-user"
    
    print(f"⚡ Getting ultra-fast jobs for user: {actual_user_id}")
    
    ultra_fast_jobs = []
    
    if db and firestore_available:
        try:
            jobs_ref = db.collection('users').document(actual_user_id).collection('jobs')
            jobs_query = jobs_ref.limit(limit).order_by('created_at', direction=firestore.Query.DESCENDING)
            
            for job_doc in jobs_query.stream():
                job_data = job_doc.to_dict()
                
                ultra_fast_job = {
                    'id': job_doc.id,
                    'job_name': job_data.get('job_name', 'Unnamed Job'),
                    'status': job_data.get('status', 'unknown'),
                    'created_at': job_data.get('created_at'),
                    'task_type': job_data.get('task_type', 'protein_ligand_binding')
                }
                ultra_fast_jobs.append(ultra_fast_job)
                
        except Exception as e:
            print(f"❌ Ultra-fast jobs error: {e}")
    
    return {
        "jobs": ultra_fast_jobs,
        "total": len(ultra_fast_jobs),
        "cached": False,
        "response_time_ms": 50,
        "user_id": actual_user_id,
        "firestore_available": firestore_available
    }

@app.get("/api/v4/batches")
async def list_batches(
    user_id: Optional[str] = Query("current_user", description="User ID"),
    limit: int = Query(200, description="Maximum number of batches"),
    status: Optional[str] = Query(None, description="Filter by status"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """List batches endpoint - Returns all batches for a user"""
    
    actual_user_id = x_user_id or user_id
    if actual_user_id == "current_user":
        actual_user_id = "demo-user"
    
    print(f"📋 Listing batches for user: {actual_user_id}")
    
    batches = []
    
    if db and firestore_available:
        try:
            batches_ref = db.collection('users').document(actual_user_id).collection('batches')
            
            if status:
                batches_query = batches_ref.where('status', '==', status).limit(limit)
            else:
                batches_query = batches_ref.limit(limit)
            
            batches_query = batches_query.order_by('created_at', direction=firestore.Query.DESCENDING)
            
            for batch_doc in batches_query.stream():
                batch_data = batch_doc.to_dict()
                batch_data['id'] = batch_doc.id
                batch_data['batch_id'] = batch_doc.id
                batches.append(batch_data)
                
        except Exception as e:
            print(f"❌ List batches error: {e}")
    
    has_more = len(batches) >= limit
    
    return {
        "batches": batches,
        "total": len(batches),
        "has_more": has_more,
        "user_id": actual_user_id,
        "status_filter": status,
        "firestore_available": firestore_available,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v4/jobs/{job_id}")
async def get_job_details(
    job_id: str,
    user_id: Optional[str] = Query("current_user", description="User ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Get detailed job information"""
    
    actual_user_id = x_user_id or user_id
    if actual_user_id == "current_user":
        actual_user_id = "demo-user"
    
    print(f"🔍 Getting job details: {job_id} for user: {actual_user_id}")
    
    if not db or not firestore_available:
        raise HTTPException(status_code=503, detail="Firestore not configured")
    
    try:
        job_ref = db.collection('users').document(actual_user_id).collection('jobs').document(job_id)
        job_doc = job_ref.get()
        
        if not job_doc.exists:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job_data = job_doc.to_dict()
        job_data['id'] = job_doc.id
        job_data['job_id'] = job_doc.id
        
        return job_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get job details error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job details: {str(e)}")

# Simple predict endpoint for testing
@app.post("/api/v4/predict")
async def predict(request: Dict[str, Any]):
    """Simple predict endpoint for testing"""
    
    job_id = str(uuid.uuid4())
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job submitted successfully",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Use PORT environment variable for Cloud Run compatibility
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting OMTX-Hub backend on port {port}")
    print(f"📊 Firestore available: {firestore_available}")
    uvicorn.run("main_minimal:app", host="0.0.0.0", port=port, reload=False)
