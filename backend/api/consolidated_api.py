"""
Consolidated OMTX-Hub API v1
Clean, minimal API focused on Boltz-2 with extensibility for RFAntibody and Chai-1

FROM: 101 scattered endpoints across v2/v3/legacy
TO: 11 core endpoints with unified job model
"""

from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import logging

# Import our services
from database.async_job_manager import AsyncJobManager
from services.gcp_storage_service import GCPStorageService
from tasks.task_handlers import TaskHandlerRegistry

# Import authentication
from auth import get_current_user, get_current_user_id, require_admin_role
from typing import Optional as Opt

# Simplified authentication for single-user deployment
DEPLOYMENT_USER_ID = "omtx_deployment_user"

async def get_optional_user_id(user_id: Optional[str] = None):
    """Get deployment user ID - always returns the same user for single-user deployment"""
    return DEPLOYMENT_USER_ID

async def get_optional_user(user: Optional[dict] = None):
    """Get deployment user - always returns the same user for single-user deployment"""
    return {
        "id": DEPLOYMENT_USER_ID, 
        "email": "deployment@omtx.ai", 
        "is_deployment_user": True
    }

logger = logging.getLogger(__name__)

# Import Firestore for migration
try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False

# Import our NEW Cloud Tasks integration
try:
    from services.job_submission_service import job_submission_service
    CLOUD_TASKS_AVAILABLE = True
    logger.info("✅ Cloud Tasks integration available")
except ImportError as e:
    CLOUD_TASKS_AVAILABLE = False
    logger.warning(f"⚠️ Cloud Tasks not available: {e}")

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["OMTX-Hub v1 API"])

# Initialize services
job_manager = AsyncJobManager()
storage_service = GCPStorageService()
task_registry = TaskHandlerRegistry()

# ===== REQUEST/RESPONSE MODELS =====

class PredictionRequest(BaseModel):
    """Unified prediction request for all models"""
    # Model selection
    model: Literal["boltz2", "rfantibody", "chai1"] = Field(..., description="Prediction model")
    
    # Core inputs (model-specific validation happens in handlers)
    protein_sequence: str = Field(..., description="Protein sequence in FASTA format")
    ligand_smiles: Optional[str] = Field(None, description="Ligand SMILES (for Boltz-2)")
    
    # Job metadata
    job_name: str = Field(..., description="Human-readable job name")
    user_id: str = Field(default="default", description="User identifier")
    
    # Model parameters (model-specific)
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Model-specific parameters")

class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""
    # Model selection
    model: Literal["boltz2", "rfantibody", "chai1"] = Field(..., description="Prediction model")
    
    # Core inputs
    protein_sequence: str = Field(..., description="Protein sequence in FASTA format")
    ligands: List[Dict[str, str]] = Field(..., description="List of ligands with name/smiles")
    
    # Batch metadata
    batch_name: str = Field(..., description="Human-readable batch name")
    user_id: str = Field(default="default", description="User identifier")
    
    # Batch configuration
    max_concurrent: int = Field(default=5, description="Max concurrent jobs")
    priority: Literal["low", "normal", "high"] = Field(default="normal")
    
    # Model parameters
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class JobResponse(BaseModel):
    """Unified job response"""
    job_id: str
    status: Literal["pending", "running", "completed", "failed", "queued"]
    model: str
    job_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    estimated_completion_seconds: Optional[int] = None
    
    # Cloud Tasks integration fields
    message: Optional[str] = None
    queue_info: Optional[Dict[str, Any]] = None
    
    # Results (when completed)
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # File links
    download_links: Optional[Dict[str, str]] = None
    
    # Enhanced fields for complete job metadata
    input_data: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    task_type: Optional[str] = None

class BatchResponse(BaseModel):
    """Unified batch response"""
    batch_id: str
    status: Literal["pending", "running", "completed", "failed", "queued"]
    model: str
    batch_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Progress tracking
    total_jobs: int
    completed_jobs: int = 0
    failed_jobs: int = 0
    running_jobs: int = 0
    
    # Cloud Tasks integration fields
    job_ids: Optional[List[str]] = None
    message: Optional[str] = None
    queue_info: Optional[Dict[str, Any]] = None
    
    # Batch results (when completed)
    summary: Optional[Dict[str, Any]] = None
    export_links: Optional[Dict[str, str]] = None

class JobListResponse(BaseModel):
    """Job list with pagination"""
    jobs: List[JobResponse]
    total: int
    page: int
    limit: int
    has_more: bool

class BatchListResponse(BaseModel):
    """Batch list with pagination"""
    batches: List[BatchResponse]
    total: int
    page: int
    limit: int
    has_more: bool

# ===== PREDICTION ENDPOINTS =====

@router.post("/predict", response_model=JobResponse)
async def submit_prediction(
    request: PredictionRequest,
    background_tasks: BackgroundTasks
    # Temporarily remove auth dependencies for testing
    # current_user_id: str = Depends(get_optional_user_id),
    # current_user: dict = Depends(get_optional_user)
) -> JobResponse:
    """
    Submit a single prediction job
    
    Supports:
    - Boltz-2: Protein-ligand binding predictions (via Cloud Tasks → Cloud Run GPU)
    - RFAntibody: Antibody design and optimization  
    - Chai-1: Multi-modal structure predictions
    """
    try:
        # Validate model-specific inputs
        if request.model == "boltz2" and not request.ligand_smiles:
            raise HTTPException(status_code=400, detail="Boltz-2 requires ligand_smiles")
        
        # NEW: Use Cloud Tasks for Boltz-2 jobs when available
        if request.model == "boltz2" and CLOUD_TASKS_AVAILABLE:
            logger.info(f"🚀 Submitting Boltz-2 job via Cloud Tasks: {request.job_name}")
            
            # Use default values for testing
            current_user_id = request.user_id or DEPLOYMENT_USER_ID
            auth_token = None  # No auth token for testing
            
            # Submit via Cloud Tasks → Cloud Run workflow
            result = await job_submission_service.submit_individual_job(
                protein_sequence=request.protein_sequence,
                ligand_smiles=request.ligand_smiles,
                ligand_name=None,  # Will be generated automatically
                job_name=request.job_name,  # Pass job_name correctly
                user_id=current_user_id,  # Use provided user_id or anonymous
                parameters=request.parameters,
                auth_token=auth_token  # Pass auth token for worker validation
            )
            
            return JobResponse(
                job_id=result["job_id"],
                status=result["status"],
                model=request.model,
                job_name=request.job_name,
                created_at=datetime.utcnow(),
                message=f"Job submitted via Cloud Tasks (estimated {result.get('estimated_completion_time', 'N/A')})",
                queue_info=result.get("queue_info", {})
            )
        
        else:
            # FALLBACK: Use original workflow for non-Boltz2 or when Cloud Tasks unavailable
            logger.info(f"📋 Using legacy workflow for {request.model}")
            
            # Create unified task data
            task_data = {
                "model_id": request.model,
                "task_type": _get_task_type(request.model),
                "job_name": request.job_name,
                "user_id": request.user_id,
                "input_data": {
                    "protein_sequence": request.protein_sequence,
                    "ligand_smiles": request.ligand_smiles,
                    **request.parameters
                }
            }
            
            # Submit to unified job manager
            job = await job_manager.create_job(task_data)
            
            # Trigger background processing
            background_tasks.add_task(_process_job, job["id"])
            
            return JobResponse(
                job_id=job["id"],
                status=job["status"],
                model=request.model,
                job_name=request.job_name,
                created_at=job["created_at"],
                updated_at=job["updated_at"],
                estimated_completion_seconds=_estimate_completion_time(request.model)
            )
        
    except Exception as e:
        logger.error(f"Prediction submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/batch", response_model=BatchResponse)
async def submit_batch_prediction(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks
    # Temporarily remove auth dependencies for testing
    # current_user_id: str = Depends(get_optional_user_id),
    # current_user: dict = Depends(get_optional_user)
) -> BatchResponse:
    """
    Submit a batch of predictions
    
    Creates multiple jobs and manages them as a cohesive batch
    - Boltz-2: Uses Cloud Tasks → Cloud Run GPU processing
    """
    try:
        # NEW: Use Cloud Tasks for Boltz-2 batch jobs when available
        if request.model == "boltz2" and CLOUD_TASKS_AVAILABLE:
            logger.info(f"🚀 Submitting Boltz-2 batch via Cloud Tasks: {request.batch_name} ({len(request.ligands)} ligands)")
            
            # Use default values for testing
            current_user_id = request.user_id or DEPLOYMENT_USER_ID
            auth_token = None  # No auth token for testing
            
            # Submit via Cloud Tasks → Cloud Run workflow
            result = await job_submission_service.submit_batch_job(
                batch_name=request.batch_name,
                protein_sequence=request.protein_sequence,
                ligands=request.ligands,
                user_id=current_user_id,  # Use provided user_id or anonymous
                parameters={
                    "max_concurrent": request.max_concurrent,
                    "priority": request.priority,
                    **request.parameters
                },
                auth_token=auth_token  # Pass auth token for worker validation
            )
            
            return BatchResponse(
                batch_id=result["batch_id"],
                status=result["status"],
                model=request.model,
                batch_name=request.batch_name,
                created_at=datetime.utcnow(),
                total_jobs=len(request.ligands),
                job_ids=result.get("job_ids", []),
                queue_info=result.get("queue_info", {}),
                message=f"Batch submitted via Cloud Tasks ({len(request.ligands)} jobs queued)"
            )
        
        else:
            # FALLBACK: Use original workflow for non-Boltz2 or when Cloud Tasks unavailable
            logger.info(f"📋 Using legacy workflow for {request.model} batch")
            
            # Create batch container
            batch_data = {
                "model_id": request.model,
                "task_type": f"batch_{_get_task_type(request.model)}",
                "job_name": request.batch_name,
                "user_id": request.user_id,
                "batch_config": {
                    "max_concurrent": request.max_concurrent,
                    "priority": request.priority,
                    "total_ligands": len(request.ligands)
                }
            }
            
            batch = await job_manager.create_batch(batch_data)
        
        # Create individual jobs
        job_ids = []
        for i, ligand in enumerate(request.ligands):
            job_data = {
                "model_id": request.model,
                "task_type": _get_task_type(request.model),
                "job_name": f"{request.batch_name} - {ligand['name']}",
                "user_id": request.user_id,
                "batch_id": batch["id"],
                "batch_index": i,
                "input_data": {
                    "protein_sequence": request.protein_sequence,
                    "ligand_smiles": ligand["smiles"],
                    "ligand_name": ligand["name"],
                    **request.parameters
                }
            }
            
            job = await job_manager.create_job(job_data)
            job_ids.append(job["id"])
        
        # Update batch with job IDs
        await job_manager.update_batch(batch["id"], {"job_ids": job_ids})
        
        # Trigger batch processing
        background_tasks.add_task(_process_batch, batch["id"], job_ids)
        
        return BatchResponse(
            batch_id=batch["id"],
            status="pending",
            model=request.model,
            batch_name=request.batch_name,
            created_at=batch["created_at"],
            updated_at=batch["updated_at"],
            total_jobs=len(request.ligands)
        )
        
    except Exception as e:
        logger.error(f"Batch submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== JOB MANAGEMENT ENDPOINTS =====

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str = Path(..., description="Job ID")):
    """Get job status and results"""
    try:
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Try to get input data from Firestore for Cloud Tasks jobs
        input_data = None
        if FIRESTORE_AVAILABLE:
            try:
                db = firestore.Client(project='om-models')
                job_ref = db.collection('jobs').document(job_id)
                firestore_doc = job_ref.get()
                
                if firestore_doc.exists:
                    firestore_data = firestore_doc.to_dict()
                    input_data = firestore_data.get('input_data')
                    logger.info(f"Found input_data in Firestore for job {job_id}")
                else:
                    logger.warning(f"No Firestore document found for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch input_data from Firestore for job {job_id}: {e}")
        
        # Build download links if completed
        download_links = None
        if job["status"] == "completed":
            download_links = {
                "structure": f"/api/v1/jobs/{job_id}/files/cif",
                "results": f"/api/v1/jobs/{job_id}/files/json",
                "pdb": f"/api/v1/jobs/{job_id}/files/pdb"
            }
        
        # Include input_data in results if available
        results = job.get("results", {})
        if input_data:
            results = {**results, "input_data": input_data}
        
        return JobResponse(
            job_id=job["id"],
            status=job["status"],
            model=job.get("model_id", "unknown"),
            job_name=job["job_name"],
            created_at=job["created_at"],
            updated_at=job["updated_at"],
            results=results,
            error_message=job.get("error"),
            download_links=download_links
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    user_id: str = Query(default="current_user", description="User ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=500, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    current_user_id: str = Depends(get_optional_user_id)
):
    """List user jobs with pagination"""
    try:
        # Handle special "current_user" value
        if user_id == "current_user":
            user_id = current_user_id
            
        offset = (page - 1) * limit
        
        jobs, total = await job_manager.list_jobs(
            user_id=user_id,
            offset=offset,
            limit=limit,
            status=status,
            model_id=model
        )
        
        job_responses = []
        
        # Enhanced job data retrieval with Firestore integration
        for job in jobs:
            download_links = None
            if job["status"] == "completed":
                download_links = {
                    "structure": f"/api/v1/jobs/{job['id']}/files/cif",
                    "results": f"/api/v1/jobs/{job['id']}/files/json"
                }
            
            # Enrich job data with Firestore metadata for complete job information
            enhanced_job = await _enrich_job_with_firestore_data(job)
            
            job_responses.append(JobResponse(
                job_id=enhanced_job["id"],
                status=enhanced_job["status"],
                model=enhanced_job.get("model", enhanced_job.get("model_id", "boltz2")),
                job_name=enhanced_job.get("job_name", "Unnamed Job"),
                created_at=enhanced_job["created_at"],
                updated_at=enhanced_job["updated_at"],
                results=enhanced_job.get("results") if enhanced_job["status"] == "completed" else None,
                download_links=download_links,
                input_data=enhanced_job.get("input_data"),  # Include input data
                parameters=enhanced_job.get("parameters", enhanced_job.get("input_data", {}).get("parameters")),  # Include parameters
                task_type=enhanced_job.get("task_type", enhanced_job.get("input_data", {}).get("parameters", {}).get("task_type", "boltz2"))  # Include task type
            ))
        
        return JobListResponse(
            jobs=job_responses,
            total=total,
            page=page,
            limit=limit,
            has_more=offset + limit < total
        )
        
    except Exception as e:
        logger.error(f"List jobs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str = Path(..., description="Job ID"),
    user_id: str = Query(default="anonymous", description="User ID for access control")
):
    """Delete a job and its associated files with user isolation"""
    try:
        # Verify job exists and get user
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user owns this job
        if job.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only delete your own jobs")
        
        # Delete from storage with user isolation
        await storage_service.delete_job_files(job_id, user_id)
        
        # Delete from database
        await job_manager.delete_job(job_id)
        
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== BATCH MANAGEMENT ENDPOINTS =====

@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(batch_id: str = Path(..., description="Batch ID")):
    """Get batch status and results"""
    try:
        batch = await job_manager.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Get batch job statistics
        try:
            stats = await job_manager.get_batch_stats(batch_id)
        except AttributeError:
            # Fallback if get_batch_stats method doesn't exist
            logger.warning(f"get_batch_stats method not available, using defaults for batch {batch_id}")
            stats = {"total": 0, "completed": 0, "failed": 0, "running": 0, "pending": 0}
        
        # Build export links if completed
        export_links = None
        if batch["status"] == "completed":
            export_links = {
                "csv": f"/api/v1/batches/{batch_id}/export?format=csv",
                "zip": f"/api/v1/batches/{batch_id}/export?format=zip",
                "json": f"/api/v1/batches/{batch_id}/export?format=json"
            }
        
        return BatchResponse(
            batch_id=batch["id"],
            status=batch["status"],
            model=batch.get("model_id", "unknown"),
            batch_name=batch["job_name"],
            created_at=batch["created_at"],
            updated_at=batch["updated_at"],
            total_jobs=stats["total"],
            completed_jobs=stats["completed"],
            failed_jobs=stats["failed"],
            running_jobs=stats["running"],
            summary=batch.get("summary"),
            export_links=export_links
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get batch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batches", response_model=BatchListResponse)
async def list_batches(
    user_id: str = Query(default="current_user", description="User ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=500, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    current_user_id: str = Depends(get_optional_user_id)
):
    """List user batches with pagination"""
    try:
        # Handle special "current_user" value
        if user_id == "current_user":
            user_id = current_user_id
            
        offset = (page - 1) * limit
        
        batches, total = await job_manager.list_batches(
            user_id=user_id,
            offset=offset,
            limit=limit,
            status=status,
            model_id=model
        )
        
        batch_responses = []
        for batch in batches:
            try:
                stats = await job_manager.get_batch_stats(batch["id"])
            except AttributeError:
                # Fallback if get_batch_stats method doesn't exist
                stats = {"total": 0, "completed": 0, "failed": 0, "running": 0, "pending": 0}
            
            export_links = None
            if batch["status"] == "completed":
                export_links = {
                    "csv": f"/api/v1/batches/{batch['id']}/export?format=csv",
                    "zip": f"/api/v1/batches/{batch['id']}/export?format=zip"
                }
            
            batch_responses.append(BatchResponse(
                batch_id=batch["id"],
                status=batch["status"],
                model=batch.get("model_id", "unknown"),
                batch_name=batch["job_name"],
                created_at=batch["created_at"],
                updated_at=batch["updated_at"],
                total_jobs=stats["total"],
                completed_jobs=stats["completed"],
                failed_jobs=stats["failed"],
                running_jobs=stats["running"],
                export_links=export_links
            ))
        
        return BatchListResponse(
            batches=batch_responses,
            total=total,
            page=page,
            limit=limit,
            has_more=offset + limit < total
        )
        
    except Exception as e:
        logger.error(f"List batches failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: str = Path(..., description="Batch ID")):
    """Delete a batch and all its jobs"""
    try:
        # Verify batch exists
        batch = await job_manager.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Delete all batch jobs and files
        await job_manager.delete_batch(batch_id)
        
        return {"message": "Batch deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete batch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== FILE DOWNLOAD ENDPOINTS =====

@router.get("/jobs/{job_id}/files/{file_type}")
async def download_job_file(
    job_id: str = Path(..., description="Job ID"),
    file_type: Literal["cif", "pdb", "json"] = Path(..., description="File type"),
    user_id: str = Query(default="anonymous", description="User ID for access control")
):
    """Download job result files with user isolation"""
    try:
        from fastapi.responses import Response
        
        # Verify job exists and is completed
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify user owns this job
        if job.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only access your own jobs")
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Get file from storage with user isolation
        file_content, content_type = await storage_service.get_job_file(job_id, file_type, user_id)
        
        filename = f"{job_id}.{file_type}"
        
        return Response(
            content=file_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batches/{batch_id}/export")
async def export_batch(
    batch_id: str = Path(..., description="Batch ID"),
    format: Literal["csv", "json", "zip"] = Query(..., description="Export format"),
    user_id: str = Query(default="anonymous", description="User ID for access control")
):
    """Export batch results with user isolation"""
    try:
        from fastapi.responses import Response
        
        # Verify batch exists and is completed
        batch = await job_manager.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Verify user owns this batch
        if batch.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only access your own batches")
        
        if batch["status"] != "completed":
            raise HTTPException(status_code=400, detail="Batch not completed")
        
        # Generate export with user isolation
        export_content, content_type = await storage_service.export_batch(batch_id, format, user_id)
        
        filename = f"{batch_id}_results.{format}"
        
        return Response(
            content=export_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export batch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== SYSTEM STATUS ENDPOINTS =====

@router.get("/system/status")
async def get_system_status():
    """Get detailed system status and health"""
    try:
        # Check system components
        db_healthy = await job_manager.health_check()
        storage_healthy = await storage_service.health_check()
        
        # Get system statistics
        stats = await job_manager.get_system_stats()
        
        return {
            "status": "healthy" if db_healthy and storage_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "storage": "healthy" if storage_healthy else "unhealthy"
            },
            "statistics": stats,
            "api_version": "v1"
        }
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# ===== MIGRATION ENDPOINTS =====

@router.post("/migrate-to-deployment-user")
async def migrate_all_jobs_to_deployment_user():
    """
    MIGRATION ENDPOINT: Migrate all jobs to deployment user
    This consolidates all historical results under the single deployment user
    """
    
    if not FIRESTORE_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Firestore not available for migration"
        )
    
    try:
        # Initialize Firestore
        db = firestore.Client(project='om-models')
        jobs_collection = db.collection('jobs')
        
        # Track statistics
        stats = {
            'total': 0,
            'migrated': 0,
            'already_deployment_user': 0,
            'errors': 0,
            'users_found': []
        }
        
        logger.info(f"🚀 Starting migration to deployment user: {DEPLOYMENT_USER_ID}")
        
        # Get all jobs
        all_jobs = jobs_collection.stream()
        users_found = set()
        
        # Process in batches for efficiency
        batch = db.batch()
        batch_count = 0
        
        for job_doc in all_jobs:
            try:
                job_data = job_doc.to_dict()
                job_id = job_doc.id
                stats['total'] += 1
                
                # Track original user
                original_user = job_data.get('user_id', 'unknown')
                users_found.add(original_user)
                
                # Check if already deployment user
                if original_user == DEPLOYMENT_USER_ID:
                    stats['already_deployment_user'] += 1
                else:
                    # Update to deployment user
                    job_ref = jobs_collection.document(job_id)
                    batch.update(job_ref, {
                        'user_id': DEPLOYMENT_USER_ID,
                        'original_user_id': original_user,
                        'migrated_at': firestore.SERVER_TIMESTAMP,
                        'migration_note': f'Migrated from {original_user} to deployment user'
                    })
                    stats['migrated'] += 1
                    batch_count += 1
                    
                    # Commit every 100 updates (Firestore limit is 500)
                    if batch_count >= 100:
                        batch.commit()
                        logger.info(f"✅ Committed batch of {batch_count} updates")
                        batch = db.batch()
                        batch_count = 0
                        
            except Exception as e:
                logger.error(f"❌ Error processing job {job_doc.id}: {e}")
                stats['errors'] += 1
        
        # Commit remaining updates
        if batch_count > 0:
            batch.commit()
            logger.info(f"✅ Committed final batch of {batch_count} updates")
        
        stats['users_found'] = list(users_found)
        
        logger.info(f"🎉 Migration complete: {stats}")
        
        return {
            'success': True,
            'message': f'Successfully migrated {stats["migrated"]} jobs to deployment user {DEPLOYMENT_USER_ID}',
            'deployment_user': DEPLOYMENT_USER_ID,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"💥 Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/migration-status")
async def get_migration_status():
    """
    Check current migration status
    """
    
    try:
        # Count deployment user jobs
        deployment_jobs, _ = await job_manager.list_jobs(
            user_id=DEPLOYMENT_USER_ID,
            limit=10000
        )
        
        # Check other known users
        other_users_jobs = {}
        known_users = ['test_user', 'current_user', 'anonymous', 'frontend_test']
        total_other = 0
        
        for user in known_users:
            try:
                jobs, _ = await job_manager.list_jobs(user_id=user, limit=1)
                if jobs:
                    # Get actual count by querying more
                    all_jobs, _ = await job_manager.list_jobs(user_id=user, limit=10000)
                    count = len(all_jobs)
                    if count > 0:
                        other_users_jobs[user] = count
                        total_other += count
            except:
                pass  # Skip if user doesn't exist
        
        migration_needed = total_other > 0
        
        return {
            'deployment_user': DEPLOYMENT_USER_ID,
            'deployment_user_jobs': len(deployment_jobs),
            'other_users': other_users_jobs,
            'total_other_users_jobs': total_other,
            'migration_needed': migration_needed,
            'status': 'Migration needed' if migration_needed else 'All jobs consolidated',
            'message': f'{total_other} jobs need migration' if migration_needed else f'All {len(deployment_jobs)} jobs belong to deployment user'
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== HELPER FUNCTIONS =====

async def _enrich_job_with_firestore_data(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich job data with complete metadata from Firestore
    This ensures jobs have job_name, input_data, parameters, task_type, etc.
    """
    if not FIRESTORE_AVAILABLE:
        return job
    
    try:
        db = firestore.Client(project='om-models')
        job_ref = db.collection('jobs').document(job["id"])
        firestore_doc = job_ref.get()
        
        if firestore_doc.exists:
            firestore_data = firestore_doc.to_dict()
            
            # Merge Firestore data with database job data
            enhanced_job = {**job}  # Start with database data
            
            # Override with Firestore data where available
            if firestore_data.get('job_name'):
                enhanced_job['job_name'] = firestore_data['job_name']
            
            if firestore_data.get('input_data'):
                enhanced_job['input_data'] = firestore_data['input_data']
            
            if firestore_data.get('model'):
                enhanced_job['model'] = firestore_data['model']
            
            # Extract task_type from parameters
            if firestore_data.get('input_data', {}).get('parameters', {}).get('task_type'):
                enhanced_job['task_type'] = firestore_data['input_data']['parameters']['task_type']
            
            if firestore_data.get('input_data', {}).get('parameters'):
                enhanced_job['parameters'] = firestore_data['input_data']['parameters']
            
            logger.debug(f"Enhanced job {job['id']} with Firestore data")
            return enhanced_job
        else:
            logger.debug(f"No Firestore document found for job {job['id']}")
            
    except Exception as e:
        logger.warning(f"Failed to enrich job {job['id']} with Firestore data: {e}")
    
    return job

def _get_task_type(model: str) -> str:
    """Map model to task type"""
    mapping = {
        "boltz2": "protein_ligand_binding",
        "rfantibody": "antibody_design",
        "chai1": "structure_prediction"
    }
    return mapping.get(model, "unknown")

def _estimate_completion_time(model: str) -> int:
    """Estimate completion time in seconds"""
    estimates = {
        "boltz2": 180,      # ~3 minutes
        "rfantibody": 120,   # ~2 minutes  
        "chai1": 240        # ~4 minutes
    }
    return estimates.get(model, 180)

async def _process_job(job_id: str):
    """Background job processing"""
    try:
        # Trigger the actual model execution
        await task_registry.process_job(job_id)
    except Exception as e:
        logger.error(f"Job processing failed for {job_id}: {e}")
        await job_manager.update_job(job_id, {
            "status": "failed",
            "error": str(e)
        })

async def _process_batch(batch_id: str, job_ids: List[str]):
    """Background batch processing"""
    try:
        # Process all jobs in the batch
        for job_id in job_ids:
            await _process_job(job_id)
        
        # Update batch status when all jobs complete
        await job_manager.update_batch_status(batch_id)
        
    except Exception as e:
        logger.error(f"Batch processing failed for {batch_id}: {e}")
        await job_manager.update_batch(batch_id, {
            "status": "failed",
            "error": str(e)
        })