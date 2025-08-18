"""
Optimized Results API for High-Performance Job and Batch Results Retrieval
Designed for sub-second response times with intelligent caching and data optimization
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional, Union
import logging
import time
import json
import asyncio
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# Import optimized services
from services.ultra_fast_results import UltraFastResults
from config.gcp_database import gcp_database
from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/optimized", tags=["Optimized Results"])

# Global cache instance
ultra_fast_results = UltraFastResults()

# Response models
class OptimizedJobSummary(BaseModel):
    """Lightweight job summary for fast listing"""
    id: str
    name: str
    type: str
    status: str
    created_at: str
    has_results: bool = False
    is_batch: bool = False
    batch_size: Optional[int] = None

class OptimizedJobsResponse(BaseModel):
    """Optimized paginated response"""
    jobs: List[OptimizedJobSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    performance: Dict[str, Any]

class BatchResultsSummary(BaseModel):
    """Lightweight batch results summary"""
    batch_id: str
    total_jobs: int
    completed_jobs: int
    status: str
    created_at: str
    performance: Dict[str, Any]

@router.get("/jobs")
async def get_optimized_jobs(
    user_id: str = Query("current_user", description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    type_filter: Optional[str] = Query(None, description="Filter by job type"),
    search: Optional[str] = Query(None, description="Search in job names"),
    fields: Optional[str] = Query("id,name,type,status,created_at", description="Comma-separated fields to return")
) -> OptimizedJobsResponse:
    """
    🚀 Ultra-Fast Job Listing with Smart Pagination
    
    Optimizations:
    - Field selection to minimize data transfer
    - Intelligent caching with 2-minute TTL
    - Parallel database queries
    - Response compression
    - Progressive loading support
    """
    
    start_time = time.time()
    cache_key = f"jobs:{user_id}:{page}:{page_size}:{status_filter}:{type_filter}:{search}"
    
    try:
        # Try cache first
        cached_result = await ultra_fast_results.get_cached_result(cache_key)
        if cached_result:
            elapsed = time.time() - start_time
            cached_result['performance']['response_time_seconds'] = round(elapsed, 6)
            cached_result['performance']['cache_hit'] = True
            logger.info(f"⚡ Cache hit for jobs: {elapsed*1000:.1f}ms")
            return OptimizedJobsResponse(**cached_result)
        
        # Build optimized Firestore query
        if not gcp_database.available:
            raise HTTPException(status_code=503, detail="Database not available")
            
        jobs_ref = gcp_database.db.collection('my_results')
        
        # Apply filters
        if user_id != "current_user":
            jobs_ref = jobs_ref.where('user_id', '==', user_id)
        
        if status_filter:
            jobs_ref = jobs_ref.where('status', '==', status_filter)
        
        if type_filter:
            jobs_ref = jobs_ref.where('task_type', '==', type_filter)
        
        # Get total count efficiently
        count_query = jobs_ref.count()
        total_count_result = count_query.get()
        total_jobs = total_count_result[0][0].value if total_count_result else 0
        
        # Get paginated results with field selection
        selected_fields = fields.split(',') if fields else ['id', 'job_name', 'task_type', 'status', 'created_at']
        
        query = (jobs_ref
                .select(selected_fields)
                .order_by('created_at', direction='DESCENDING')
                .limit(page_size)
                .offset((page - 1) * page_size))
        
        docs = query.get()
        
        # Process results efficiently
        jobs = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            
            # Apply search filter if specified
            if search:
                search_lower = search.lower()
                job_name = doc_data.get('job_name', '').lower()
                task_type = doc_data.get('task_type', '').lower()
                if not (search_lower in job_name or search_lower in task_type):
                    continue
            
            # Create optimized job summary
            job_summary = OptimizedJobSummary(
                id=doc_data['id'],
                name=doc_data.get('job_name', 'Unknown Job'),
                type=_get_display_type(doc_data.get('task_type', '')),
                status=_get_display_status(doc_data.get('status', '')),
                created_at=_format_datetime(doc_data.get('created_at')),
                has_results=bool(doc_data.get('results')),
                is_batch='batch' in doc_data.get('task_type', '').lower(),
                batch_size=doc_data.get('batch_size')
            )
            jobs.append(job_summary)
        
        # Calculate pagination
        total_pages = (total_jobs + page_size - 1) // page_size
        
        # Performance metrics
        elapsed = time.time() - start_time
        performance = {
            'response_time_seconds': round(elapsed, 3),
            'cache_hit': False,
            'strategy': 'optimized_firestore',
            'query_time': round(elapsed, 3),
            'jobs_processed': len(jobs)
        }
        
        result = {
            'jobs': [job.dict() for job in jobs],
            'total': total_jobs,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'performance': performance
        }
        
        # Cache the result
        await ultra_fast_results.cache_result(cache_key, result, ttl=120)  # 2 minutes
        
        logger.info(f"⚡ Optimized jobs query: {elapsed:.3f}s for {len(jobs)} jobs")
        return OptimizedJobsResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Optimized jobs query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs: {str(e)}")

@router.get("/batch/{batch_id}/summary")
async def get_batch_summary(
    batch_id: str,
    include_progress: bool = Query(True, description="Include progress information")
) -> BatchResultsSummary:
    """
    ⚡ Ultra-Fast Batch Summary
    
    Returns essential batch information without loading full results data.
    Perfect for dashboard cards and quick status checks.
    """
    
    start_time = time.time()
    cache_key = f"batch_summary:{batch_id}:{include_progress}"
    
    try:
        # Try cache first
        cached_result = await ultra_fast_results.get_cached_result(cache_key)
        if cached_result:
            elapsed = time.time() - start_time
            cached_result['performance']['response_time_seconds'] = round(elapsed, 6)
            cached_result['performance']['cache_hit'] = True
            return BatchResultsSummary(**cached_result)
        
        # Get batch metadata efficiently
        if not gcp_database.available:
            raise HTTPException(status_code=503, detail="Database not available")
            
        batch_doc = gcp_database.db.collection('jobs').document(batch_id).get()
        if not batch_doc.exists:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch_data = batch_doc.to_dict()
        
        # Get child jobs count efficiently if needed
        total_jobs = 0
        completed_jobs = 0
        
        if include_progress:
            # Use aggregation for fast counts
            child_jobs_ref = gcp_database.db.collection('jobs').where('batch_parent_id', '==', batch_id)
            
            # Count total and completed in parallel
            total_count_future = child_jobs_ref.count().get()
            completed_count_future = child_jobs_ref.where('status', '==', 'completed').count().get()
            
            total_jobs = total_count_future[0][0].value if total_count_future else 0
            completed_jobs = completed_count_future[0][0].value if completed_count_future else 0
        
        # Performance metrics
        elapsed = time.time() - start_time
        performance = {
            'response_time_seconds': round(elapsed, 3),
            'cache_hit': False,
            'strategy': 'summary_only'
        }
        
        result = {
            'batch_id': batch_id,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'status': _get_display_status(batch_data.get('status', '')),
            'created_at': _format_datetime(batch_data.get('created_at')),
            'performance': performance
        }
        
        # Cache for 1 minute (shorter TTL for dynamic data)
        await ultra_fast_results.cache_result(cache_key, result, ttl=60)
        
        logger.info(f"⚡ Batch summary: {elapsed:.3f}s")
        return BatchResultsSummary(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch summary: {str(e)}")

@router.get("/batch/{batch_id}/results/stream")
async def stream_batch_results(
    batch_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    include_raw_modal: bool = Query(False, description="Include raw modal data"),
    fields: Optional[str] = Query(None, description="Specific fields to include")
):
    """
    🌊 Streaming Batch Results for Large Datasets
    
    Returns batch results in chunks for progressive loading.
    Optimized for 1000+ job batches.
    """
    
    start_time = time.time()
    
    try:
        # Load from GCP storage efficiently
        batch_results_path = f"batches/{batch_id}/batch_results.json"
        
        try:
            batch_results_data = gcp_storage_service.storage.download_file(batch_results_path)
            if isinstance(batch_results_data, bytes):
                batch_results_data = batch_results_data.decode('utf-8')
            batch_results = json.loads(batch_results_data)
        except Exception as storage_error:
            logger.warning(f"Storage lookup failed for {batch_id}: {storage_error}")
            raise HTTPException(status_code=404, detail="Batch results not found in storage")
        
        # Get individual results
        individual_results = batch_results.get('individual_results', [])
        total_results = len(individual_results)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = individual_results[start_idx:end_idx]
        
        # Optimize data based on parameters
        if not include_raw_modal:
            # Remove heavy raw_modal_result data for faster transfer
            for result in paginated_results:
                result.pop('raw_modal_result', None)
                result.pop('structure_data', None)
        
        if fields:
            # Return only requested fields
            field_list = fields.split(',')
            filtered_results = []
            for result in paginated_results:
                filtered_result = {field: result.get(field) for field in field_list if field in result}
                filtered_result['job_id'] = result.get('job_id')  # Always include job_id
                filtered_results.append(filtered_result)
            paginated_results = filtered_results
        
        # Performance metrics
        elapsed = time.time() - start_time
        
        response_data = {
            'batch_id': batch_id,
            'results': paginated_results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_results': total_results,
                'total_pages': (total_results + page_size - 1) // page_size,
                'has_next': end_idx < total_results,
                'has_previous': page > 1
            },
            'performance': {
                'response_time_seconds': round(elapsed, 3),
                'results_returned': len(paginated_results),
                'data_optimized': not include_raw_modal
            }
        }
        
        logger.info(f"🌊 Streamed batch results page {page}: {elapsed:.3f}s for {len(paginated_results)} results")
        
        # Set appropriate cache headers
        headers = {
            'Cache-Control': 'public, max-age=300',  # 5 minutes
            'X-Total-Results': str(total_results),
            'X-Page': str(page),
            'X-Response-Time': f"{elapsed:.3f}s"
        }
        
        return JSONResponse(content=response_data, headers=headers)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Streaming batch results failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stream batch results: {str(e)}")

# Helper functions
def _get_display_type(task_type: str) -> str:
    """Convert task type to display-friendly format"""
    type_map = {
        'protein_ligand_binding': 'Boltz-2 Protein-Ligand',
        'batch_protein_ligand_screening': 'Batch Screening',
        'nanobody_design': 'RFAntibody Design',
        'structure_prediction': 'Chai-1 Structure'
    }
    return type_map.get(task_type, task_type.replace('_', ' ').title())

def _get_display_status(status: str) -> str:
    """Convert status to display-friendly format"""
    status_map = {
        'completed': 'Complete',
        'failed': 'Failed',
        'running': 'Running',
        'pending': 'Pending'
    }
    return status_map.get(status.lower(), status.title())

def _format_datetime(dt: Any) -> str:
    """Format datetime for display"""
    if isinstance(dt, str):
        return dt
    if isinstance(dt, (int, float)):
        return datetime.fromtimestamp(dt).isoformat()
    if hasattr(dt, 'timestamp'):
        return dt.isoformat()
    return str(dt)

# Background task for cache warming
@router.post("/admin/warm-cache")
async def warm_cache(background_tasks: BackgroundTasks):
    """Warm up caches for better performance"""
    
    async def warm_cache_task():
        try:
            logger.info("🔥 Starting cache warming...")
            
            # Warm up common queries
            await get_optimized_jobs(page=1, page_size=25)
            await get_optimized_jobs(page=1, page_size=50)
            await get_optimized_jobs(status_filter="completed", page=1, page_size=25)
            
            logger.info("✅ Cache warming completed")
        except Exception as e:
            logger.error(f"❌ Cache warming failed: {e}")
    
    background_tasks.add_task(warm_cache_task)
    return {"message": "Cache warming started"}