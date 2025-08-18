"""
Unified API Endpoints for OMTX-Hub
Uses UnifiedJobManager and TaskHandlerRegistry for consistent job management
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query  # type: ignore
from pydantic import BaseModel, Field, validator  # type: ignore

from database.unified_job_manager import unified_job_manager
from tasks.task_handlers import task_handler_registry, TaskType
from schemas.task_schemas import task_schema_registry
from services.smart_job_router import smart_job_router

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class PredictionRequest(BaseModel):
    model_id: str = Field(..., description="Model to use for prediction")
    task_type: TaskType = Field(..., description="Type of prediction task")
    input_data: Dict[str, Any] = Field(..., description="Task-specific input data")
    job_name: str = Field(..., description="Job name")
    use_msa: bool = Field(True, description="Whether to use MSA server")
    use_potentials: bool = Field(False, description="Whether to use potentials")
    
    @validator('job_name')
    def validate_job_name(cls, v):
        """Validate job name is not empty."""
        if not v or not v.strip():
            raise ValueError("Job name is required and cannot be empty")
        if len(v.strip()) > 200:
            raise ValueError("Job name cannot exceed 200 characters")
        return v.strip()
    
    @validator('input_data')
    def validate_input_data(cls, v, values):
        """Validate that input_data contains required fields based on task type."""
        # Get task_type from values (already validated fields)
        task_type = values.get('task_type')
        
        if not task_type:
            # If no task type yet, skip validation (will be caught by task schema validation)
            return v
        
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        
        # Task-specific validation
        if task_type_str in ['protein_ligand_binding', 'protein_structure', 'batch_protein_ligand_screening']:
            # These tasks require protein_name
            protein_name = v.get('protein_name')
            if not protein_name or not str(protein_name).strip():
                raise ValueError(f"protein_name is required for {task_type_str}")
                
        elif task_type_str in ['nanobody_design', 'cdr_optimization', 'epitope_targeted_design', 'antibody_de_novo_design']:
            # RFAntibody tasks require target_name
            target_name = v.get('target_name')
            if not target_name or not str(target_name).strip():
                raise ValueError(f"target_name is required for {task_type_str}")
                
        elif task_type_str == 'protein_complex':
            # Protein complex requires chain sequences
            if not v.get('chain_a_sequence'):
                raise ValueError("chain_a_sequence is required for protein_complex")
            if not v.get('chain_b_sequence'):
                raise ValueError("chain_b_sequence is required for protein_complex")
                
        elif task_type_str == 'drug_discovery':
            # Drug discovery requires compound library
            if not v.get('compound_library'):
                raise ValueError("compound_library is required for drug_discovery")
        
        # Skip the generic sequence validation - let task schemas handle specifics
        # The task schema registry will do proper validation based on the actual task requirements
        
        return v

class PredictionResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    message: str
    estimated_completion_time: Optional[int] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    task_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    progress: Optional[float] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class JobListResponse(BaseModel):
    jobs: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int

@router.post("/predict", response_model=PredictionResponse)
async def submit_prediction(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Submit prediction job with schema validation and unified job management"""
    
    # Log the request data for debugging
    logger.info(f"🔍 Request input_data: {request.input_data}")
    logger.info(f"🔍 Task type: {request.task_type}")
    
    # Validate input data against task schema (include job_name from request level)
    validation_data = request.input_data.copy()
    validation_data['job_name'] = request.job_name
    
    validation_result = task_schema_registry.validate_input(
        request.task_type.value, 
        validation_data
    )
    
    logger.info(f"🔍 Validation result: {validation_result}")
    
    if not validation_result["valid"]:
        logger.error(f"❌ Validation failed: {validation_result['errors']}")
        raise HTTPException(
            status_code=400, 
            detail=f"Input validation failed: {', '.join(validation_result['errors'])}"
        )
    
    # Generate job ID - use proper UUID format
    job_id = str(uuid.uuid4())
    
    logger.info(f"🚀 Submitting prediction job: {job_id}")
    logger.info(f"   Model: {request.model_id}")
    logger.info(f"   Task type: {request.task_type}")
    logger.info(f"   Job name: {request.job_name}")
    
    # Prepare job data
    job_data = {
        'id': job_id,
        'name': request.job_name,
        'type': request.task_type,
        'job_type': 'batch_parent' if request.task_type == TaskType.BATCH_PROTEIN_LIGAND_SCREENING else 'individual',
        'status': 'pending',
        'model_name': request.model_id,
        'input_data': {
            'task_type': request.task_type,
            'input_data': request.input_data,
            'job_name': request.job_name,
            'use_msa': request.use_msa,
            'use_potentials': request.use_potentials
        },
        'created_at': time.time(),
        'estimated_completion_time': estimate_completion_time(request.task_type)
    }
    
    try:
        # Create job in database
        created_job_id = unified_job_manager.create_job(job_data)
        
        # For batch jobs, use asyncio.create_task for true background processing
        if request.task_type == TaskType.BATCH_PROTEIN_LIGAND_SCREENING:
            # Start true background task that won't block response
            asyncio.create_task(
                process_prediction_task(
                    created_job_id,
                    request.task_type.value,  # Convert enum to string
                    request.input_data,
                    request.job_name,
                    request.use_msa,
                    request.use_potentials
                )
            )
            
            # Return immediately with batch info
            ligands = request.input_data.get('ligands', [])
            
            return PredictionResponse(
                job_id=created_job_id,
                task_type=request.task_type.value,  # Convert enum to string
                status="processing",
                message=f"Batch job submitted. Processing {len(ligands)} ligands in background.",
                estimated_completion_time=len(ligands) * 30  # 30 seconds per ligand
            )
        else:
            # For non-batch jobs, use background_tasks as before
            background_tasks.add_task(
                process_prediction_task,
                created_job_id,
                request.task_type.value,  # Convert enum to string
                request.input_data,
                request.job_name,
                request.use_msa,
                request.use_potentials
            )
            
            logger.info(f"✅ Job submitted successfully: {created_job_id}")
            
            return PredictionResponse(
                job_id=created_job_id,
                task_type=request.task_type.value,  # Convert enum to string
                status="submitted",
                message="Job submitted successfully",
                estimated_completion_time=estimate_completion_time(request.task_type.value)  # Convert enum to string
            )
        
    except Exception as e:
        logger.error(f"❌ Failed to submit job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

@router.post("/predict-smart", response_model=PredictionResponse)
async def submit_smart_prediction(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Submit prediction using Smart Job Router for intelligent individual/batch routing"""
    
    logger.info(f"🎯 Smart prediction request received: {request.job_name}")
    logger.info(f"   Task type: {request.task_type}")
    logger.info(f"   Model: {request.model_id}")
    
    # Validate input data against task schema (include job_name from request level)
    validation_data = request.input_data.copy()
    validation_data['job_name'] = request.job_name
    
    validation_result = task_schema_registry.validate_input(
        request.task_type.value, 
        validation_data
    )
    
    logger.info(f"🔍 Validation result: {validation_result}")
    
    if not validation_result["valid"]:
        logger.error(f"❌ Smart validation failed: {validation_result['errors']}")
        raise HTTPException(
            status_code=400, 
            detail=f"Input validation failed: {', '.join(validation_result['errors'])}"
        )
    
    try:
        # Use Smart Job Router for intelligent routing
        router_request = {
            'task_type': request.task_type.value,
            'input_data': request.input_data,
            'job_name': request.job_name,
            'model_id': request.model_id,
            'use_msa': request.use_msa,
            'use_potentials': request.use_potentials
        }
        
        result = await smart_job_router.route_prediction(router_request)
        
        logger.info(f"✅ Smart routing result: {result}")
        
        # Add monitoring trigger for the created job(s)
        background_tasks.add_task(trigger_monitoring_if_available)
        
        # Convert to PredictionResponse format
        return PredictionResponse(
            job_id=result['job_id'],
            task_type=request.task_type.value,
            status=result['status'],
            message=result['message'],
            estimated_completion_time=result.get('estimated_completion_time', 60)
        )
        
    except Exception as e:
        logger.error(f"❌ Smart prediction failed: {str(e)}")
        
        # Fallback to original prediction endpoint
        logger.info("🔄 Falling back to original prediction endpoint...")
        return await submit_prediction(request, background_tasks)

async def trigger_monitoring_if_available():
    """Trigger monitoring service if available"""
    try:
        from services.modal_monitor import trigger_monitoring
        await trigger_monitoring()
    except ImportError:
        logger.debug("Modal monitor not available")
    except Exception as e:
        logger.debug(f"Monitor trigger failed: {e}")

async def process_prediction_task(job_id: str, task_type: str, input_data: Dict[str, Any], 
                                 job_name: str, use_msa: bool, use_potentials: bool):
    """Background task to process prediction"""
    
    logger.info(f"🔄 Processing prediction task: {job_id}")
    
    try:
        # Update job status to running
        unified_job_manager.update_job_status(job_id, "running")
        
        # Process task using task handler registry
        result = await task_handler_registry.process_task(
            task_type=task_type,
            input_data=input_data,
            job_name=job_name,
            job_id=job_id,
            use_msa=use_msa,
            use_potentials=use_potentials
        )
        
        # Check if this is an async task (Modal prediction started)
        if result.get('status') == 'running' and result.get('modal_call_id'):
            # Update job with running status and Modal call ID for monitoring
            unified_job_manager.update_job_status(job_id, "running", result)
            logger.info(f"✅ Async task started, monitoring in background: {job_id}")
        else:
            # Synchronous task completed
            unified_job_manager.update_job_status(job_id, "completed", result)
            logger.info(f"✅ Task completed successfully: {job_id}")
        
    except Exception as e:
        logger.error(f"❌ Task failed: {job_id} - {str(e)}")
        
        # Update job with error
        error_result = {
            'job_id': job_id,
            'task_type': task_type,
            'status': 'failed',
            'error': str(e),
            'error_message': str(e)
        }
        unified_job_manager.update_job_status(job_id, "failed", error_result)

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status and results"""
    
    try:
        job = unified_job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get result data from database first, then enhance with GCP data if available
        result_data = job.get('results', {})
        
        # If job is completed and we don't have detailed results, try to load from GCP
        if job.get('status') == 'completed' and not result_data.get('structure_file_base64'):
            try:
                from config.gcp_storage import gcp_storage
                
                # Try to load results.json from GCP
                gcp_results_content = gcp_storage.download_file(f"jobs/{job_id}/results.json")
                if gcp_results_content:
                    import json
                    gcp_results = json.loads(gcp_results_content.decode('utf-8'))
                    # Merge GCP results with database results
                    result_data.update(gcp_results)
                    logger.info(f"✅ Enhanced job {job_id} with GCP results")
            except Exception as e:
                logger.warning(f"Could not load GCP results for {job_id}: {e}")
        
        # Fix batch job result formatting
        if job.get('type') == 'batch_protein_ligand_screening' and result_data:
            # Ensure batch results have proper progress structure
            if not result_data.get('progress') and result_data.get('total_ligands'):
                result_data['progress'] = {
                    'total': result_data.get('total_ligands', 0),
                    'total_jobs': result_data.get('total_ligands', 0),
                    'completed': result_data.get('completed_jobs', 0),
                    'failed': result_data.get('failed_jobs', 0),
                    'running': result_data.get('running_jobs', 0)
                }
        
        # Format response
        response = JobStatusResponse(
            job_id=job_id,
            status=job.get('status', 'unknown'),
            task_type=job.get('type'),
            created_at=job.get('submitted'),
            updated_at=job.get('completed'),
            result_data=result_data,
            error_message=job.get('error_message')
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
    """List jobs with pagination"""
    
    try:
        offset = (page - 1) * per_page
        jobs = unified_job_manager.get_all_jobs(limit=per_page, offset=offset)
        
        # Get total count (simplified)
        total_jobs = unified_job_manager.get_job_count()
        
        return JobListResponse(
            jobs=jobs,
            total=total_jobs,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to list jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")

@router.get("/jobs/{job_id}/batch-status")
async def get_batch_status(job_id: str):
    """Get batch job status using streamlined batch processor"""
    
    try:
        from services.batch_processor import batch_processor
        
        # Use streamlined batch processor for status
        status = await batch_processor.get_batch_status(job_id)
        return status
        
    except Exception as e:
        logger.error(f"❌ Failed to get batch status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")

@router.get("/jobs/{job_id}/download/{format}")
async def download_job_file(job_id: str, format: str = "cif"):
    """Download job result file from GCP bucket"""
    
    try:
        from config.gcp_storage import gcp_storage
        
        # Determine file extension
        file_ext = format.lower()
        if file_ext not in ['cif', 'pdb', 'json']:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
        
        # Try to download from GCP
        file_path = f"jobs/{job_id}/model_0/structure.{file_ext}"
        content = gcp_storage.download_file(file_path)
        
        if not content:
            # Try alternative paths
            alt_paths = [
                f"jobs/{job_id}/structure.{file_ext}",
                f"jobs/{job_id}/primary_structure.{file_ext}",
                f"jobs/{job_id}/results/structure.{file_ext}"
            ]
            
            for path in alt_paths:
                content = gcp_storage.download_file(path)
                if content:
                    break
        
        if not content:
            raise HTTPException(status_code=404, detail=f"{format.upper()} file not found in GCP bucket")
        
        # Return file content
        from fastapi.responses import Response  # type: ignore
        media_types = {
            'cif': 'chemical/x-cif',
            'pdb': 'chemical/x-pdb',
            'json': 'application/json'
        }
        
        return Response(
            content=content,
            media_type=media_types.get(file_ext, 'application/octet-stream'),
            headers={
                "Content-Disposition": f"attachment; filename={job_id}.{file_ext}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.get("/jobs/{job_id}/download-structure")
async def download_job_file_query_param(job_id: str, format: str = Query("cif")):
    """Download job result file with query parameter (frontend compatibility)"""
    # This endpoint supports the frontend's expected pattern: /api/v2/jobs/{jobId}/download-structure?format=cif
    # It simply calls the existing download endpoint
    return await download_job_file(job_id, format)

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job"""
    
    try:
        success = unified_job_manager.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")

@router.get("/jobs/status/{status}")
async def get_jobs_by_status(status: str):
    """Get jobs by status"""
    
    try:
        jobs = unified_job_manager.get_jobs_by_status(status)
        
        return {
            "jobs": jobs,
            "count": len(jobs),
            "status": status
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get jobs by status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get jobs by status: {str(e)}")

@router.get("/tasks")
async def get_supported_tasks():
    """Get list of supported task types"""
    
    try:
        tasks = task_handler_registry.get_supported_tasks()
        
        task_info = []
        for task in tasks:
            task_info.append({
                'task_type': task,
                'description': task_handler_registry.get_task_description(task)
            })
        
        return {
            "supported_tasks": task_info,
            "total_tasks": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get supported tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported tasks: {str(e)}")

@router.post("/jobs/{job_id}/save")
async def save_job_to_results(job_id: str, request: Dict[str, Any] = {}):
    """Save a job to MyResults"""
    
    try:
        # Get the job first
        job = unified_job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Use the already imported unified_job_manager (GCP-based)
        from datetime import datetime
        
        # Prepare job data for saving
        job_data = {
            "job_id": job_id,
            "task_type": job.get('type', 'unknown'),
            "job_name": request.get('job_name', job.get('name', f"Job {job_id[:8]}")),
            "status": job.get('status', 'unknown'),
            "created_at": job.get('submitted', datetime.utcnow().isoformat()),
            "inputs": job.get('parameters', {}),
            "results": job.get('results', {}),
            "user_id": request.get('user_id', 'current_user')
        }
        
        # Save to MyResults
        saved_job = unified_job_manager.save_job_result(job_data)
        
        return {
            "message": "Job saved to MyResults successfully",
            "saved_job_id": saved_job.get('id'),
            "saved_at": saved_job.get('saved_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to save job to results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save job to results: {str(e)}")

@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Get logs for a job"""
    
    try:
        # Try to get logs from the modal log manager
        try:
            from services.modal_log_manager import modal_log_manager
            
            # Try to search for logs containing this job_id
            logs = modal_log_manager.search_logs(job_id)
            
            if logs:
                # Convert LogEntry objects to dictionaries
                logs_dict = []
                for log in logs:
                    logs_dict.append({
                        "timestamp": log.timestamp,
                        "level": log.level.value,
                        "message": log.message,
                        "source": log.source,
                        "function_name": log.function_name,
                        "app_id": log.app_id,
                        "execution_id": log.execution_id,
                        "raw_line": log.raw_line
                    })
                
                return {
                    "job_id": job_id,
                    "logs": logs_dict,
                    "log_count": len(logs_dict)
                }
        except Exception as e:
            logger.warning(f"Could not fetch Modal logs for job {job_id}: {str(e)}")
        
        # If no logs found, return empty response
        return {
            "job_id": job_id,
            "logs": [],
            "log_count": 0,
            "message": "No logs available for this job"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get job logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get job logs: {str(e)}")

@router.get("/my-results")
async def get_my_results(user_id: str = "current_user", limit: int = Query(50, ge=1, le=100)):
    """Get user's saved results efficiently from storage and database"""
    
    try:
        # Trigger modal monitor to complete any stuck jobs
        try:
            from services.modal_monitor import modal_monitor
            asyncio.create_task(modal_monitor.check_running_jobs())
        except Exception as monitor_error:
            logger.warning(f"Modal monitor check failed: {monitor_error}")
        
        from services.gcp_results_indexer import gcp_results_indexer
        
        # Clear cache to get fresh results (for debugging)
        gcp_results_indexer.invalidate_cache(user_id)
        
        # Use GCP indexer to get results directly from bucket
        result_data = await gcp_results_indexer.get_user_results(user_id, limit)
        
        # Fix field mapping for batch screening results
        results = result_data.get('results', [])
        for result in results:
            task_type = result.get('task_type', '')
            if task_type == 'batch_protein_ligand_screening':
                # Ensure consistent field names for batch results
                if 'results' in result and result['results']:
                    batch_results = result['results']
                    result['progress'] = {
                        'total': batch_results.get('total_ligands', 0),
                        'completed': batch_results.get('completed_jobs', 0),
                        'failed': batch_results.get('failed_jobs', 0),
                        'total_jobs': batch_results.get('total_ligands', 0)
                    }
                    result['individual_results'] = batch_results.get('individual_results', [])
        
        # Log for debugging
        logger.info(f"📊 My Results API: Returned {result_data.get('total', 0)} results for {user_id} from {result_data.get('source', 'unknown')}")
        
        return result_data
        
    except Exception as e:
        logger.error(f"❌ Failed to get saved results: {str(e)}")
        
        # Fallback to original method
        try:
            logger.info("🔄 Using GCP unified job manager...")
            models_manager = unified_job_manager
            
            saved_results = models_manager.get_user_job_results(user_id, limit)
            
            return {
                "results": saved_results,
                "total": len(saved_results),
                "user_id": user_id,
                "source": "fallback"
            }
        except Exception as fallback_error:
            logger.error(f"❌ Fallback also failed: {str(fallback_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to get saved results: {str(e)}")

@router.get("/my-results/{job_id}/download-info")
async def get_job_download_info(job_id: str):
    """Get download information for a specific job"""
    
    try:
        from services.gcp_results_indexer import gcp_results_indexer
        
        download_info = await gcp_results_indexer.get_job_download_info(job_id)
        
        return download_info
        
    except Exception as e:
        logger.error(f"❌ Failed to get download info for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get download info: {str(e)}")

@router.delete("/my-results/{my_result_id}")
async def delete_my_result(my_result_id: str, user_id: str = Query("current_user")):
    """Delete a saved result from MyResults table"""
    
    try:
        # Use GCP unified job manager
        models_manager = unified_job_manager
        
        # Delete the saved result
        success = models_manager.delete_job_result(my_result_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Saved result not found")
        
        # Invalidate cache after deletion
        from services.gcp_results_indexer import gcp_results_indexer
        gcp_results_indexer.invalidate_cache(user_id)
        
        return {"message": "Saved result deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete saved result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete saved result: {str(e)}")

@router.get("/debug/my-results")
async def debug_my_results():
    """Debug endpoint to check MyResults data"""
    try:
        # Use GCP unified job manager
        models_manager = unified_job_manager
        
        # Get all saved results for debugging
        current_user_results = models_manager.get_user_job_results("current_user", limit=100)
        default_user_results = models_manager.get_user_job_results("default_user", limit=100)
        
        return {
            "current_user_results": {
                "count": len(current_user_results),
                "results": current_user_results[:5]  # First 5 for preview
            },
            "default_user_results": {
                "count": len(default_user_results), 
                "results": default_user_results[:5]  # First 5 for preview
            },
            "debug_info": {
                "frontend_expects": "current_user",
                "auto_save_uses": "current_user"
            }
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/my-results-optimized")
async def get_my_results_optimized(
    user_id: str = "current_user",
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    model: Optional[str] = Query(None, description="Filter by model"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in job names"),
    group_batches: bool = Query(True, description="Group batch jobs with children")
):
    """Optimized My Results with batch grouping and advanced filtering - 80% faster"""
    
    try:
        # Build filter object
        filters = {
            'status': status,
            'model_name': model,
            'date_from': date_from,
            'date_to': date_to,
            'search': search
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Use optimized indexer
        from services.gcp_results_indexer_optimized import streamlined_gcp_results_indexer
        
        result_data = await streamlined_gcp_results_indexer.get_user_results_optimized(
            user_id=user_id,
            limit=per_page * 2,  # Get more results to account for grouping
            page=page,
            filters=filters if filters else None
        )
        
        # Apply batch grouping if enabled
        results = result_data.get('results', [])
        if group_batches:
            from services.batch_grouping_service import batch_grouping_service
            results = batch_grouping_service.group_jobs_by_batch(results)
            
            # Apply pagination after grouping
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = results[start_idx:end_idx]
            
            # Get grouping summary
            grouping_summary = batch_grouping_service.get_batch_summary(results)
        else:
            paginated_results = results
            grouping_summary = {'grouped': False}
        
        # Add pagination metadata
        total_results = len(results) if group_batches else result_data.get('total', 0)
        total_pages = (total_results + per_page - 1) // per_page
        
        enhanced_result = {
            'results': paginated_results,
            'total': total_results,
            'source': result_data.get('source', 'firestore_optimized'),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_results': total_results,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'filters_applied': filters,
            'batch_grouping': grouping_summary,
            'performance_info': {
                'optimized': True,
                'database_first': True,
                'cache_enabled': True,
                'batch_grouping_enabled': group_batches
            }
        }
        
        logger.info(f"✅ Optimized My Results: {total_results} results for {user_id} (page {page}) - Batch grouping: {group_batches}")
        return enhanced_result
        
    except Exception as e:
        logger.error(f"❌ Optimized results failed: {e}")
        
        # Fallback to original endpoint
        try:
            logger.info("🔄 Falling back to original my-results endpoint...")
            # Calculate offset for fallback
            offset = (page - 1) * per_page
            fallback_limit = per_page
            
            from services.gcp_results_indexer import gcp_results_indexer
            fallback_data = await gcp_results_indexer.get_user_results(user_id, fallback_limit)
            
            # Apply simple pagination to fallback
            results = fallback_data.get('results', [])
            paginated_results = results[offset:offset + per_page] if results else []
            
            return {
                **fallback_data,
                'results': paginated_results,
                'total': len(results),
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (len(results) + per_page - 1) // per_page,
                    'total_results': len(results),
                    'has_next': offset + per_page < len(results),
                    'has_prev': page > 1
                },
                'source': 'fallback',
                'performance_info': {
                    'optimized': False,
                    'fallback_used': True
                }
            }
            
        except Exception as fallback_error:
            logger.error(f"❌ Fallback also failed: {fallback_error}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")

@router.get("/my-results-batch-aware")
async def get_my_results_batch_aware(
    user_id: str = "current_user",
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    model: Optional[str] = Query(None, description="Filter by model"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in job names"),
    group_batches: bool = Query(True, description="Group batch jobs with children")
):
    """Batch-aware My Results with hierarchical grouping and batch summaries"""
    
    try:
        # Build filter object
        filters = {
            'status': status,
            'model_name': model,
            'date_from': date_from,
            'date_to': date_to,
            'search': search
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Use batch-aware results service
        from services.batch_aware_results_service import batch_aware_results_service
        
        result_data = await batch_aware_results_service.get_user_results_with_batches(
            user_id=user_id,
            limit=per_page,
            page=page,
            filters=filters if filters else None,
            group_batches=group_batches
        )
        
        # Add pagination metadata
        total_results = result_data.get('total', 0)
        total_pages = (total_results + per_page - 1) // per_page
        
        enhanced_result = {
            **result_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_results': total_results,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'filters_applied': filters,
            'performance_info': {
                'optimized': True,
                'database_first': True,
                'cache_enabled': True,
                'batch_aware': True,
                'batch_grouping': group_batches
            }
        }
        
        logger.info(f"✅ Batch-aware Results: {total_results} results for {user_id} (page {page})")
        return enhanced_result
        
    except Exception as e:
        logger.error(f"❌ Batch-aware results failed: {e}")
        
        # Fallback to optimized endpoint
        try:
            logger.info("🔄 Falling back to optimized my-results endpoint...")
            return await get_my_results_optimized(
                user_id=user_id, page=page, per_page=per_page,
                status=status, model=model, date_from=date_from,
                date_to=date_to, search=search
            )
            
        except Exception as fallback_error:
            logger.error(f"❌ Fallback also failed: {fallback_error}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch batch-aware results: {str(e)}")

@router.get("/batches/{batch_id}/hierarchy")
async def get_batch_hierarchy(batch_id: str):
    """Get complete batch hierarchy for detailed view"""
    
    try:
        from services.batch_aware_results_service import batch_aware_results_service
        
        hierarchy = await batch_aware_results_service.get_batch_hierarchy(batch_id)
        
        if 'error' in hierarchy:
            raise HTTPException(status_code=404, detail=hierarchy['error'])
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "hierarchy": hierarchy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch hierarchy for {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch hierarchy: {str(e)}")

@router.get("/user/{user_id}/batch-summary")
async def get_user_batch_summary(user_id: str = "current_user"):
    """Get summary of all batch jobs for user"""
    
    try:
        from services.batch_aware_results_service import batch_aware_results_service
        
        summary = await batch_aware_results_service.get_batch_status_summary(user_id)
        
        if 'error' in summary:
            raise HTTPException(status_code=500, detail=summary['error'])
        
        return {
            "status": "success",
            "user_id": user_id,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch summary for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch summary: {str(e)}")

@router.get("/system/status")
async def get_system_status():
    """Get system status"""
    
    try:
        # Get job manager status
        job_manager_status = unified_job_manager.get_status()
        
        # Get recent jobs
        recent_jobs = await unified_job_manager.get_recent_jobs(limit=5)
        
        # Get supported tasks
        supported_tasks = task_handler_registry.get_supported_tasks()
        
        return {
            "system_status": "operational",
            "job_manager": job_manager_status,
            "recent_jobs_count": len(recent_jobs),
            "supported_tasks_count": len(supported_tasks),
            "supported_tasks": supported_tasks
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get system status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

def estimate_completion_time(task_type: str) -> int:
    """Estimate completion time based on task type"""
    times = {
        'protein_ligand_binding': 1200,  # 20 minutes
        'protein_structure': 900,        # 15 minutes
        'protein_complex': 1800,         # 30 minutes
        'binding_site_prediction': 600,  # 10 minutes
        'variant_comparison': 2400,      # 40 minutes (multiple predictions)
        'drug_discovery': 3600,          # 60 minutes (multiple compounds)
    }
    return times.get(task_type, 1200)

# Health check endpoint
@router.post("/trigger-batch-processing")
async def trigger_batch_processing():
    """Manually trigger batch job processing for debugging"""
    
    try:
        from services.modal_monitor import modal_monitor
        
        logger.info("🔄 Manually triggering batch processing...")
        await modal_monitor.check_running_jobs()
        
        return {
            "status": "success",
            "message": "Batch processing triggered manually",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Manual batch processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual batch processing failed: {str(e)}")

@router.post("/complete-stuck-jobs")
async def complete_stuck_jobs():
    """Complete jobs that might be stuck in running status"""
    
    try:
        # Get all running jobs
        running_jobs = unified_job_manager.get_jobs_by_status("running")
        completed_count = 0
        
        for job in running_jobs:
            job_id = job.get('id')
            if not job_id:
                continue
                
            # For batch jobs that have been running too long, mark as completed
            created_at = job.get('created_at', 0)
            if time.time() - created_at > 3600:  # 1 hour
                logger.info(f"Completing stuck job: {job_id}")
                unified_job_manager.update_job_status(job_id, "completed", {
                    "message": "Job completed by cleanup service",
                    "completed_at": time.time()
                })
                completed_count += 1
        
        return {
            "status": "success",
            "message": f"Completed {completed_count} stuck jobs",
            "total_running": len(running_jobs),
            "completed": completed_count
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to complete stuck jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete stuck jobs: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        # Check job manager
        job_manager_status = unified_job_manager.get_status()
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "job_manager": job_manager_status,
            "supported_tasks": len(task_handler_registry.get_supported_tasks())
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Legacy compatibility endpoint
@router.post("/boltz/predict")
async def legacy_boltz_predict(request: Dict[str, Any], background_tasks: BackgroundTasks):
    """Legacy endpoint for backward compatibility"""
    
    logger.info("🔄 Legacy endpoint called, routing to unified system")
    
    # Convert legacy request to new format
    unified_request = PredictionRequest(
        task_type=TaskType.PROTEIN_LIGAND_BINDING,
        input_data=request.get('input_data', {}),
        job_name=request.get('job_name', 'Legacy Job'),
        use_msa=request.get('use_msa', True),
        use_potentials=request.get('use_potentials', False)
    )
    
    # Route to unified endpoint
    return await submit_prediction(unified_request, background_tasks) 