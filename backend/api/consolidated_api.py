"""
Consolidated OMTX-Hub API v1
Clean, minimal API focused on Boltz-2 with extensibility for RFAntibody and Chai-1

FROM: 101 scattered endpoints across v2/v3/legacy
TO: 11 core endpoints with unified job model
"""

from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import logging

# Import our services
from database.async_job_manager import AsyncJobManager
from services.gcp_storage_service import GCPStorageService
from tasks.task_handlers import TaskHandlerRegistry

logger = logging.getLogger(__name__)

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
            
            # Submit via Cloud Tasks → Cloud Run workflow
            result = await job_submission_service.submit_individual_job(
                protein_sequence=request.protein_sequence,
                ligand_smiles=request.ligand_smiles,
                ligand_name=request.job_name,  # Use job_name as ligand_name
                user_id=request.user_id,
                parameters=request.parameters
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
            
            # Submit via Cloud Tasks → Cloud Run workflow
            result = await job_submission_service.submit_batch_job(
                batch_name=request.batch_name,
                protein_sequence=request.protein_sequence,
                ligands=request.ligands,
                user_id=request.user_id,
                parameters={
                    "max_concurrent": request.max_concurrent,
                    "priority": request.priority,
                    **request.parameters
                }
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
        
        # Build download links if completed
        download_links = None
        if job["status"] == "completed":
            download_links = {
                "structure": f"/api/v1/jobs/{job_id}/files/cif",
                "results": f"/api/v1/jobs/{job_id}/files/json",
                "pdb": f"/api/v1/jobs/{job_id}/files/pdb"
            }
        
        return JobResponse(
            job_id=job["id"],
            status=job["status"],
            model=job.get("model_id", "unknown"),
            job_name=job["job_name"],
            created_at=job["created_at"],
            updated_at=job["updated_at"],
            results=job.get("results"),
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
    user_id: str = Query(default="default", description="User ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    model: Optional[str] = Query(default=None, description="Filter by model")
):
    """List user jobs with pagination"""
    try:
        offset = (page - 1) * limit
        
        jobs, total = await job_manager.list_jobs(
            user_id=user_id,
            offset=offset,
            limit=limit,
            status=status,
            model_id=model
        )
        
        job_responses = []
        for job in jobs:
            download_links = None
            if job["status"] == "completed":
                download_links = {
                    "structure": f"/api/v1/jobs/{job['id']}/files/cif",
                    "results": f"/api/v1/jobs/{job['id']}/files/json"
                }
            
            job_responses.append(JobResponse(
                job_id=job["id"],
                status=job["status"],
                model=job.get("model_id", "unknown"),
                job_name=job["job_name"],
                created_at=job["created_at"],
                updated_at=job["updated_at"],
                results=job.get("results") if job["status"] == "completed" else None,
                download_links=download_links
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
async def delete_job(job_id: str = Path(..., description="Job ID")):
    """Delete a job and its associated files"""
    try:
        # Verify job exists and get user
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Delete from storage
        await storage_service.delete_job_files(job_id)
        
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
        stats = await job_manager.get_batch_stats(batch_id)
        
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
    user_id: str = Query(default="default", description="User ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    model: Optional[str] = Query(default=None, description="Filter by model")
):
    """List user batches with pagination"""
    try:
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
            stats = await job_manager.get_batch_stats(batch["id"])
            
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
    file_type: Literal["cif", "pdb", "json"] = Path(..., description="File type")
):
    """Download job result files"""
    try:
        from fastapi.responses import Response
        
        # Verify job exists and is completed
        job = await job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail="Job not completed")
        
        # Get file from storage
        file_content, content_type = await storage_service.get_job_file(job_id, file_type)
        
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
    format: Literal["csv", "json", "zip"] = Query(..., description="Export format")
):
    """Export batch results in various formats"""
    try:
        from fastapi.responses import Response
        
        # Verify batch exists and is completed
        batch = await job_manager.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        if batch["status"] != "completed":
            raise HTTPException(status_code=400, detail="Batch not completed")
        
        # Generate export
        export_content, content_type = await storage_service.export_batch(batch_id, format)
        
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

# ===== HELPER FUNCTIONS =====

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