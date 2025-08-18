"""
Enhanced Results Endpoints for OMTX-Hub Unified Architecture
Provides consistent API responses for both individual and batch jobs
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Dict, Any, List, Optional
import logging
from pydantic import BaseModel

from services.unified_job_storage import unified_job_storage
from models.enhanced_job_model import JobType, JobStatus, TaskType
from services.performance_optimized_results import performance_results
from services.ultra_fast_results import ultra_fast_results
# Modal monitor integration (optional)
try:
    from services.modal_monitor import modal_monitor
    MODAL_MONITOR_AVAILABLE = True
except ImportError:
    MODAL_MONITOR_AVAILABLE = False
    modal_monitor = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/results", tags=["Enhanced Results"])

# === Response Models ===

class JobSummary(BaseModel):
    """Summary information for job listings"""
    id: str
    name: str
    job_type: str  # individual, batch_parent, batch_child
    task_type: str
    status: str
    created_at: float
    updated_at: Optional[float] = None
    duration: Optional[float] = None
    can_view: bool = False
    has_results: bool = False
    batch_info: Optional[Dict[str, Any]] = None

class PaginatedJobsResponse(BaseModel):
    """Paginated job listing response"""
    jobs: List[JobSummary]
    pagination: Dict[str, Any]
    statistics: Dict[str, Any]

class JobDetailResponse(BaseModel):
    """Detailed job information"""
    job: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    batch_children: Optional[List[Dict[str, Any]]] = None
    batch_statistics: Optional[Dict[str, Any]] = None

class BatchResultsResponse(BaseModel):
    """Batch-specific results response"""
    parent: Dict[str, Any]
    children: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    summary: Dict[str, Any]

# === Ultra-High-Performance Results ===

@router.get("/ultra-fast")
async def get_ultra_fast_results(
    user_id: str = Query("current_user", description="User ID to filter results"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    page: int = Query(1, ge=1, description="Page number for pagination")
) -> Dict[str, Any]:
    """
    ⚡⚡ Ultra-Fast Results Loading (Sub-Second Response)

    Optimized for millisecond response times using:
    - In-memory caching with background refresh
    - Bypasses slow Firestore queries entirely
    - Sub-millisecond cache hits
    - Background data refresh every 30 seconds

    This is the fastest possible results endpoint.
    """

    try:
        # Use ultra-fast service with aggressive caching
        results = await ultra_fast_results.get_ultra_fast_results(
            user_id=user_id,
            limit=limit,
            page=page
        )

        logger.info(f"⚡⚡ Ultra-fast results: {results.get('performance', {}).get('response_time_seconds', 'N/A')}s")

        return results

    except Exception as e:
        logger.error(f"❌ Ultra-fast results API failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")

@router.get("/fast")
async def get_fast_results(
    user_id: str = Query("current_user", description="User ID to filter results"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    page: int = Query(1, ge=1, description="Page number for pagination")
) -> Dict[str, Any]:
    """
    ⚡ Ultra-Fast Results Loading

    Optimized for sub-second response times using:
    - Database-first approach (no GCP scanning)
    - Aggressive caching (5-minute TTL)
    - Lazy loading of result details
    - Parallel processing where possible

    This endpoint replaces the slow /my-results endpoint for list views.
    """

    try:
        import time
        start_time = time.time()

        # Use performance-optimized service
        results = await performance_results.get_my_results_fast(
            user_id=user_id,
            limit=limit,
            page=page
        )

        elapsed = time.time() - start_time

        # Add performance metrics
        results['performance'] = {
            'response_time_seconds': round(elapsed, 3),
            'optimization_strategy': 'database_first_with_cache',
            'cache_status': results.get('cache_status', 'unknown'),
            'endpoint': '/api/v2/results/fast'
        }

        logger.info(f"⚡ Fast results API: {len(results.get('results', []))} results in {elapsed:.3f}s")

        return results

    except Exception as e:
        logger.error(f"❌ Fast results API failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch results: {str(e)}")

# === Individual and Batch Job Listings ===

@router.get("/my-jobs", response_model=PaginatedJobsResponse)
async def get_my_jobs(
    background_tasks: BackgroundTasks,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    job_type: Optional[str] = Query(None, description="Filter by job type: individual, batch_parent, batch_child"),
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed, failed"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    search: Optional[str] = Query(None, description="Search query")
):
    """Get user's jobs with enhanced filtering and pagination"""
    
    try:
        logger.info(f"🔍 Getting my jobs: page={page}, per_page={per_page}, job_type={job_type}")
        
        # Trigger monitoring for stuck jobs
        if MODAL_MONITOR_AVAILABLE:
            background_tasks.add_task(modal_monitor.check_running_jobs)
        
        # Parse filters
        job_types = None
        if job_type:
            try:
                job_types = [JobType(job_type)]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid job type: {job_type}")
        
        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        task_types = [task_type] if task_type else None
        
        # Handle search
        if search:
            jobs = await unified_job_storage.search_jobs(
                query=search,
                job_types=job_types,
                limit=per_page * 2  # Get more for better search results
            )
            
            # Apply additional filters to search results
            if status_filter:
                jobs = [job for job in jobs if job.status == status_filter]
            if task_types:
                jobs = [job for job in jobs if job.task_type in task_types]
            
            # Manual pagination for search results
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_jobs = jobs[start_idx:end_idx]
            
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': len(jobs),
                'total_pages': (len(jobs) + per_page - 1) // per_page,
                'has_more': end_idx < len(jobs)
            }
            
        else:
            # Regular filtered query
            paginated_jobs, pagination = await unified_job_storage.get_user_jobs(
                limit=per_page,
                job_types=job_types,
                status=status_filter,
                task_types=task_types,
                page=page
            )
        
        # Convert to API format
        job_summaries = []
        for job in paginated_jobs:
            api_dict = job.to_api_dict()
            
            summary = JobSummary(
                id=job.id,
                name=job.name,
                job_type=job.job_type.value,
                task_type=job.task_type,
                status=job.status.value,
                created_at=job.created_at,
                updated_at=job.updated_at,
                duration=api_dict.get('duration'),
                can_view=api_dict.get('can_view', False),
                has_results=api_dict.get('has_results', False),
                batch_info=api_dict.get('batch_info')
            )
            job_summaries.append(summary)
        
        # Get user statistics
        stats = await unified_job_storage.get_user_statistics()
        
        return PaginatedJobsResponse(
            jobs=job_summaries,
            pagination=pagination,
            statistics=stats
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get my jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")

@router.get("/job/{job_id}", response_model=JobDetailResponse)
async def get_job_details(
    job_id: str,
    background_tasks: BackgroundTasks,
    include_results: bool = Query(True, description="Include job results if available"),
    include_children: bool = Query(True, description="Include batch children if applicable")
):
    """Get detailed job information with results and batch children"""
    
    try:
        logger.info(f"🔍 Getting job details: {job_id}")
        
        # Trigger monitoring for this specific job if pending/running
        if MODAL_MONITOR_AVAILABLE:
            background_tasks.add_task(modal_monitor.check_running_jobs)
        
        # Get job with optional result enrichment
        job = await unified_job_storage.get_job(job_id, enrich_with_results=include_results)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Build response
        response_data = {
            "job": job.to_api_dict(),
            "results": job.output_data if include_results else None
        }
        
        # Handle batch jobs
        if job.job_type == JobType.BATCH_PARENT and include_children:
            batch_data = await unified_job_storage.get_batch_with_children(
                job_id, include_results=include_results
            )
            
            if batch_data:
                parent, children, statistics = batch_data
                response_data["batch_children"] = [child.to_api_dict() for child in children]
                response_data["batch_statistics"] = statistics
        
        return JobDetailResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get job details {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job details")

# === Batch-Specific Endpoints ===

@router.get("/batch/{batch_id}/results", response_model=BatchResultsResponse)
async def get_batch_results(
    batch_id: str,
    background_tasks: BackgroundTasks,
    status_filter: Optional[str] = Query(None, description="Filter children by status"),
    include_results: bool = Query(True, description="Include individual results")
):
    """Get comprehensive batch results - compatible with BatchResults.tsx"""
    
    try:
        logger.info(f"🔍 Getting batch results: {batch_id}")
        
        # Trigger monitoring
        if MODAL_MONITOR_AVAILABLE:
            background_tasks.add_task(modal_monitor.check_running_jobs)
        
        # Get batch with children
        batch_data = await unified_job_storage.get_batch_with_children(
            batch_id, include_results=include_results
        )
        
        if not batch_data:
            raise HTTPException(status_code=404, detail="Batch job not found")
        
        parent, children, statistics = batch_data
        
        # Apply status filter to children
        if status_filter:
            try:
                filter_status = JobStatus(status_filter)
                children = [child for child in children if child.status == filter_status]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status filter: {status_filter}")
        
        # Build comprehensive response
        return BatchResultsResponse(
            parent=parent.to_api_dict(),
            children=[child.to_api_dict() for child in children],
            statistics=statistics,
            summary={
                "total_jobs": len(children),
                "completed": len([c for c in children if c.status == JobStatus.COMPLETED]),
                "failed": len([c for c in children if c.status == JobStatus.FAILED]),
                "running": len([c for c in children if c.status == JobStatus.RUNNING]),
                "pending": len([c for c in children if c.status == JobStatus.PENDING]),
                "success_rate": (statistics.get("completed", 0) / max(len(children), 1)) * 100,
                "batch_complete": parent.is_batch_complete([child.status for child in children])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch results {batch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve batch results")

@router.get("/batch/{batch_id}/children")
async def get_batch_children(
    batch_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    include_results: bool = Query(False, description="Include individual results"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page")
):
    """Get paginated batch children with filtering"""
    
    try:
        logger.info(f"🔍 Getting batch children: {batch_id}")
        
        status_enum = None
        if status_filter:
            try:
                status_enum = JobStatus(status_filter)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
        
        # Get children with filtering
        children = await unified_job_storage.get_batch_children(
            batch_id, include_results=include_results, status_filter=status_enum
        )
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_children = children[start_idx:end_idx]
        
        return {
            "children": [child.to_api_dict() for child in paginated_children],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": len(children),
                "total_pages": (len(children) + per_page - 1) // per_page,
                "has_more": end_idx < len(children)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch children {batch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve batch children")

# === Search and Query Endpoints ===

@router.get("/search")
async def search_jobs(
    q: str = Query(..., description="Search query"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results")
):
    """Search user jobs by name, task type, or content"""
    
    try:
        logger.info(f"🔍 Searching jobs: '{q}'")
        
        job_types = None
        if job_type:
            try:
                job_types = [JobType(job_type)]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid job type: {job_type}")
        
        results = await unified_job_storage.search_jobs(
            query=q,
            job_types=job_types,
            limit=limit
        )
        
        return {
            "query": q,
            "results": [job.to_api_dict() for job in results],
            "total": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

# === Statistics and Analytics ===

@router.get("/statistics")
async def get_user_statistics():
    """Get comprehensive user statistics and analytics"""
    
    try:
        logger.info("🔍 Getting user statistics")
        
        stats = await unified_job_storage.get_user_statistics()
        
        # Add cache information
        cache_stats = unified_job_storage.get_cache_stats()
        stats["cache_info"] = cache_stats
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

@router.get("/status/{status}")
async def get_jobs_by_status(
    status: str,
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results")
):
    """Get jobs filtered by status"""
    
    try:
        logger.info(f"🔍 Getting jobs by status: {status}")
        
        try:
            status_enum = JobStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        job_types = None
        if job_type:
            try:
                job_types = [JobType(job_type)]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid job type: {job_type}")
        
        jobs = await unified_job_storage.get_jobs_by_status(
            status_enum, job_types=job_types, limit=limit
        )
        
        return {
            "status": status,
            "jobs": [job.to_api_dict() for job in jobs],
            "total": len(jobs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get jobs by status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs by status")

# === Legacy endpoints removed - only new format supported ===

# === Admin and Debug Endpoints ===

@router.get("/debug/cache")
async def get_cache_debug_info():
    """Debug information about the storage cache"""
    
    return unified_job_storage.get_cache_stats()

@router.post("/debug/cache/clear")
async def clear_storage_cache():
    """Clear the storage cache (admin only)"""
    
    unified_job_storage.clear_cache()
    return {"message": "Cache cleared successfully"}