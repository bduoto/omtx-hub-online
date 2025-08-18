"""
Ultra-Fast Unified API - Single endpoint for all user job data
Implements aggressive memory caching for sub-millisecond response times.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from google.cloud import firestore

from database.unified_job_manager import unified_job_manager
from services.gcp_storage_service import gcp_storage_service
from services.batch_relationship_manager import batch_relationship_manager
from config.gcp_database import gcp_database

logger = logging.getLogger(__name__)

# In-memory cache that persists across requests
MEMORY_CACHE = {}
CACHE_TIMESTAMPS = {}
CACHE_TTL = 120  # 2 minutes
USER_ACTIVITY = defaultdict(float)  # Track user activity for smart caching

router = APIRouter(prefix="/api/v3/ultra-fast", tags=["Ultra Fast Unified API"])

class UnifiedJobResponse(BaseModel):
    """Response model for unified job data"""
    jobs: List[Dict[str, Any]]
    total: int
    performance: Dict[str, Any]
    cache_info: Dict[str, Any]

async def cleanup_cache():
    """Clean up expired cache entries"""
    now = time.time()
    expired_keys = [
        key for key, timestamp in CACHE_TIMESTAMPS.items()
        if now - timestamp > CACHE_TTL * 2  # Keep extra time for safety
    ]
    
    for key in expired_keys:
        MEMORY_CACHE.pop(key, None)
        CACHE_TIMESTAMPS.pop(key, None)
    
    if expired_keys:
        logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

@router.get("/individual-jobs", response_model=UnifiedJobResponse)
async def get_individual_jobs_only(
    user_id: str = Query("current_user", description="User ID"),
    lightweight: bool = Query(False, description="Return only essential fields for fast loading"),
    include_results: bool = Query(False, description="Include job results data"),
    limit: int = Query(1000, description="Maximum number of jobs to return", ge=1, le=5000)
) -> UnifiedJobResponse:
    """
    Get only individual jobs (INDIVIDUAL job_type) with results stored in hub-job-files/jobs/
    Used by My Results page - excludes batch jobs and failed jobs without results.
    """
    
    start_time = time.time()
    USER_ACTIVITY[user_id] = start_time
    
    # Generate cache key for individual jobs only
    cache_key = f"{user_id}:individual:{'light' if lightweight else 'full'}:{limit}:results={include_results}"
    now = time.time()
    
    # Check memory cache first
    if cache_key in MEMORY_CACHE:
        cached_time = CACHE_TIMESTAMPS.get(cache_key, 0)
        if now - cached_time < CACHE_TTL:
            result = MEMORY_CACHE[cache_key].copy()
            result['performance'].update({
                'response_time_seconds': round(time.time() - start_time, 6),
                'cache_hit': True,
                'cache_age_seconds': round(now - cached_time, 2)
            })
            logger.info(f"⚡ CACHE HIT (individual): {user_id} - {round((time.time() - start_time) * 1000, 2)}ms")
            return result
    
    try:
        if lightweight:
            jobs = await get_jobs_lightweight(user_id, limit)
        else:
            jobs = await get_jobs_with_details(user_id, limit, include_results, False)
        
        # Filter to only individual jobs with results
        individual_jobs = []
        for job in jobs:
            job_type = job.get('job_type', 'INDIVIDUAL')
            status = job.get('status', 'pending')
            
            # Only include INDIVIDUAL jobs that are completed with results
            # Check multiple indicators for result storage
            has_results = (
                job.get('files_stored_to_gcp') or 
                job.get('has_results') or 
                job.get('results_in_gcp') or
                job.get('output_data', {}).get('has_results') or
                job.get('results') or
                bool(job.get('output_data', {}).get('results'))
            )
            
            if job_type == 'INDIVIDUAL' and status == 'completed' and has_results:
                job['type'] = 'individual'
                job['storage_path'] = f"jobs/{job.get('id')}"
                individual_jobs.append(job)
        
        # Performance metrics
        elapsed = time.time() - start_time
        
        result = UnifiedJobResponse(
            jobs=individual_jobs,
            total=len(individual_jobs),
            performance={
                'response_time_seconds': round(elapsed, 3),
                'cache_hit': False,
                'strategy': 'individual_only',
                'individual_jobs': len(individual_jobs),
                'batch_jobs': 0,
                'firestore_queries': 1,
                'gcp_storage_calls': len(individual_jobs) if include_results else 0
            },
            cache_info={
                'cached_at': now,
                'cache_key': cache_key,
                'ttl_seconds': CACHE_TTL
            }
        )
        
        # Cache the result
        MEMORY_CACHE[cache_key] = result.dict()
        CACHE_TIMESTAMPS[cache_key] = now
        
        logger.info(f"✅ Individual jobs loaded for {user_id}: {len(individual_jobs)} jobs in {round(elapsed * 1000)}ms")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error loading individual jobs for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load individual jobs: {str(e)}")

@router.get("/batch-jobs", response_model=UnifiedJobResponse)
async def get_batch_jobs_only(
    user_id: str = Query("current_user", description="User ID"),
    lightweight: bool = Query(False, description="Return only essential fields for fast loading"),
    include_results: bool = Query(False, description="Include job results data"),
    limit: int = Query(500, description="Maximum number of batches to return", ge=1, le=2000)
) -> UnifiedJobResponse:
    """
    Get only batch jobs (BATCH_PARENT job_type) with results stored in hub-job-files/batches/
    Used by My Batches page - excludes individual jobs and failed batches without results.
    """
    
    start_time = time.time()
    USER_ACTIVITY[user_id] = start_time
    
    # Generate cache key for batch jobs only
    cache_key = f"{user_id}:batches:{'light' if lightweight else 'full'}:{limit}:results={include_results}"
    now = time.time()
    
    # Check memory cache first
    if cache_key in MEMORY_CACHE:
        cached_time = CACHE_TIMESTAMPS.get(cache_key, 0)
        if now - cached_time < CACHE_TTL:
            result = MEMORY_CACHE[cache_key].copy()
            result['performance'].update({
                'response_time_seconds': round(time.time() - start_time, 6),
                'cache_hit': True,
                'cache_age_seconds': round(now - cached_time, 2)
            })
            logger.info(f"⚡ CACHE HIT (batches): {user_id} - {round((time.time() - start_time) * 1000, 2)}ms")
            return result
    
    try:
        if lightweight:
            jobs = await get_jobs_lightweight(user_id, limit)
        else:
            jobs = await get_jobs_with_details(user_id, limit, include_results, True)
        
        # Filter to only batch jobs
        batch_jobs = []
        for job in jobs:
            task_type = job.get('task_type', '').lower()
            job_type = job.get('job_type', 'INDIVIDUAL')
            status = job.get('status', 'pending')
            
            # Include BATCH_PARENT jobs or running/pending batch tasks
            if ('batch' in task_type or job_type == 'BATCH_PARENT'):
                job['type'] = 'batch_parent'
                if status == 'completed' and job.get('files_stored_to_gcp'):
                    job['storage_path'] = f"batches/{job.get('id')}"
                batch_jobs.append(job)
        
        # Performance metrics
        elapsed = time.time() - start_time
        
        result = UnifiedJobResponse(
            jobs=batch_jobs,
            total=len(batch_jobs),
            performance={
                'response_time_seconds': round(elapsed, 3),
                'cache_hit': False,
                'strategy': 'batches_only',
                'individual_jobs': 0,
                'batch_jobs': len(batch_jobs),
                'firestore_queries': 1,
                'gcp_storage_calls': len(batch_jobs) if include_results else 0
            },
            cache_info={
                'cached_at': now,
                'cache_key': cache_key,
                'ttl_seconds': CACHE_TTL
            }
        )
        
        # Cache the result
        MEMORY_CACHE[cache_key] = result.dict()
        CACHE_TIMESTAMPS[cache_key] = now
        
        logger.info(f"✅ Batch jobs loaded for {user_id}: {len(batch_jobs)} jobs in {round(elapsed * 1000)}ms")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error loading batch jobs for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load batch jobs: {str(e)}")

@router.get("/unified-jobs", response_model=UnifiedJobResponse)
async def get_unified_jobs_ultra_fast(
    user_id: str = Query("current_user", description="User ID"),
    lightweight: bool = Query(False, description="Return only essential fields for fast loading"),
    include_results: bool = Query(False, description="Include job results data"),
    include_batches: bool = Query(True, description="Include batch information"),
    limit: int = Query(1000, description="Maximum number of jobs to return", ge=1, le=5000)
) -> UnifiedJobResponse:
    """
    Ultra-fast endpoint that returns ALL user jobs with unified format.
    
    Performance optimizations:
    - Aggressive memory caching (sub-millisecond for cache hits)
    - Lightweight mode for instant navigation
    - Batch operations for results fetching
    - Smart cache invalidation based on user activity
    """
    
    start_time = time.time()
    
    # Track user activity
    USER_ACTIVITY[user_id] = start_time
    
    # Generate cache key
    cache_key = f"{user_id}:unified:{'light' if lightweight else 'full'}:{limit}:results={include_results}:batches={include_batches}"
    now = time.time()
    
    # Check memory cache first (sub-millisecond response)
    if cache_key in MEMORY_CACHE:
        cached_time = CACHE_TIMESTAMPS.get(cache_key, 0)
        if now - cached_time < CACHE_TTL:
            result = MEMORY_CACHE[cache_key].copy()
            result['performance'].update({
                'response_time_seconds': round(time.time() - start_time, 6),
                'cache_hit': True,
                'cache_age_seconds': round(now - cached_time, 2)
            })
            logger.info(f"⚡ CACHE HIT: {user_id} - {round((time.time() - start_time) * 1000, 2)}ms")
            return result
    
    # Clean up cache periodically
    if len(MEMORY_CACHE) > 100:  # Prevent memory bloat
        await cleanup_cache()
    
    # Load fresh data
    logger.info(f"🔄 CACHE MISS: Loading fresh data for {user_id}")
    
    try:
        if lightweight:
            jobs = await get_jobs_lightweight(user_id, limit)
        else:
            jobs = await get_jobs_with_details(user_id, limit, include_results, include_batches)
        
        # Categorize jobs based on storage location and completion status
        individual_jobs = []
        batch_jobs = []
        
        for job in jobs:
            task_type = job.get('task_type', '').lower()
            job_type = job.get('job_type', 'INDIVIDUAL')
            status = job.get('status', 'pending')
            
            # Only include jobs that are completed with results stored in GCP
            if status == 'completed' and job.get('files_stored_to_gcp'):
                if 'batch' in task_type or job_type == 'BATCH_PARENT':
                    # Batch jobs should have files in hub-job-files/batches/
                    job['type'] = 'batch_parent'
                    job['storage_path'] = f"batches/{job.get('id')}"
                    batch_jobs.append(job)
                elif job_type == 'INDIVIDUAL':
                    # Individual jobs should have files in hub-job-files/jobs/
                    job['type'] = 'individual'
                    job['storage_path'] = f"jobs/{job.get('id')}"
                    individual_jobs.append(job)
            elif status in ['running', 'pending']:
                # Include running/pending jobs but mark them as in-progress
                if 'batch' in task_type or job_type == 'BATCH_PARENT':
                    job['type'] = 'batch_parent'
                    batch_jobs.append(job)
                else:
                    job['type'] = 'individual'
                    individual_jobs.append(job)
            # Skip failed/cancelled jobs without results
        
        # Performance metrics
        elapsed = time.time() - start_time
        
        result = UnifiedJobResponse(
            jobs=jobs,
            total=len(jobs),
            performance={
                'response_time_seconds': round(elapsed, 3),
                'cache_hit': False,
                'strategy': 'lightweight' if lightweight else 'full_load',
                'individual_jobs': len(individual_jobs),
                'batch_jobs': len(batch_jobs),
                'firestore_queries': 1 if lightweight else 2,
                'gcp_storage_calls': len(jobs) if include_results else 0
            },
            cache_info={
                'cached_at': now,
                'cache_key': cache_key,
                'ttl_seconds': CACHE_TTL
            }
        )
        
        # Cache the result
        MEMORY_CACHE[cache_key] = result.dict()
        CACHE_TIMESTAMPS[cache_key] = now
        
        logger.info(f"✅ Fresh load completed for {user_id}: {len(jobs)} jobs in {round(elapsed * 1000)}ms")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error loading unified jobs for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load jobs: {str(e)}")

async def get_jobs_lightweight(user_id: str, limit: int = 200) -> List[Dict]:
    """
    Get only essential job fields for ultra-fast loading.
    Optimized for instant navigation between pages.
    """
    
    try:
        # Single optimized Firestore query with minimal fields
        jobs_ref = (
            gcp_database.db.collection('jobs')
            .where('user_id', '==', user_id)
            .order_by('created_at', direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        
        jobs = []
        for doc in jobs_ref.stream():
            job_data = doc.to_dict()
            
            # Only include essential fields for fast loading
            essential_job = {
                'id': doc.id,
                'job_name': job_data.get('job_name') or job_data.get('name', 'Unnamed Job'),
                'task_type': job_data.get('task_type', 'unknown'),
                'status': job_data.get('status', 'pending'),
                'created_at': job_data.get('created_at'),
                'updated_at': job_data.get('updated_at'),
                'user_id': job_data.get('user_id'),
                'estimated_completion_time': job_data.get('estimated_completion_time'),
                'job_type': job_data.get('job_type', 'INDIVIDUAL')
            }
            
            # Add batch info if it's a batch job
            if job_data.get('job_type') == 'BATCH_PARENT':
                essential_job.update({
                    'batch_parent_id': job_data.get('batch_parent_id'),
                    'total_ligands_screened': job_data.get('total_ligands_screened', 0),
                    'successful_predictions': job_data.get('successful_predictions', 0)
                })
            
            jobs.append(essential_job)
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error in get_jobs_lightweight: {e}")
        raise

async def get_jobs_with_details(user_id: str, limit: int, include_results: bool, include_batches: bool) -> List[Dict]:
    """
    Get comprehensive job data including results and batch information.
    Uses parallel processing for optimal performance.
    """
    
    try:
        # Base query for all jobs
        jobs = await get_jobs_lightweight(user_id, limit)
        
        if not jobs:
            return []
        
        # Parallel processing for additional data
        tasks = []
        
        # Task 1: Get results if requested
        if include_results:
            job_ids = [job['id'] for job in jobs]
            tasks.append(get_batch_results(job_ids))
        else:
            async def empty_dict(): return {}
            tasks.append(empty_dict())
        
        # Task 2: Get batch summaries if requested
        if include_batches:
            batch_ids = [job['id'] for job in jobs if job.get('job_type') == 'BATCH_PARENT']
            if batch_ids:
                tasks.append(get_batch_summaries(batch_ids))
            else:
                async def empty_dict(): return {}
                tasks.append(empty_dict())
        else:
            async def empty_dict(): return {}
            tasks.append(empty_dict())
        
        # Execute all tasks in parallel
        results_map, batch_summaries = await asyncio.gather(*tasks)
        
        # Enhance jobs with additional data
        enhanced_jobs = []
        for job in jobs:
            job_id = job['id']
            
            # Add results if available
            if include_results and job_id in results_map:
                job['results'] = results_map[job_id]
            
            # Add batch summary if available
            if include_batches and job.get('job_type') == 'BATCH_PARENT' and job_id in batch_summaries:
                job['batch_info'] = batch_summaries[job_id]
            
            enhanced_jobs.append(job)
        
        return enhanced_jobs
        
    except Exception as e:
        logger.error(f"Error in get_jobs_with_details: {e}")
        raise

async def get_batch_results(job_ids: List[str]) -> Dict[str, Any]:
    """Batch fetch results for multiple jobs using GCP Storage batch API"""
    
    try:
        # Use the optimized batch storage service
        if hasattr(gcp_storage_service, 'batch_get_results'):
            return await gcp_storage_service.batch_get_results(job_ids)
        else:
            # Fallback to individual calls but with concurrency
            async def get_single_result(job_id):
                try:
                    return job_id, await gcp_storage_service.get_job_results(job_id)
                except Exception:
                    return job_id, None
            
            tasks = [get_single_result(job_id) for job_id in job_ids[:20]]  # Limit concurrent calls
            results = await asyncio.gather(*tasks)
            
            return {job_id: result for job_id, result in results if result is not None}
    
    except Exception as e:
        logger.error(f"Error fetching batch results: {e}")
        return {}

async def get_batch_summaries(batch_ids: List[str]) -> Dict[str, Any]:
    """Get batch summary information"""
    
    try:
        if hasattr(batch_relationship_manager, 'get_batch_summaries'):
            return await batch_relationship_manager.get_batch_summaries(batch_ids)
        else:
            # Fallback implementation
            summaries = {}
            for batch_id in batch_ids:
                try:
                    summary = await batch_relationship_manager.get_batch_results(batch_id)
                    summaries[batch_id] = {
                        'child_count': summary.get('total_ligands_screened', 0),
                        'completed_count': summary.get('successful_predictions', 0),
                        'summary': summary.get('batch_statistics', {})
                    }
                except Exception:
                    continue
            
            return summaries
    
    except Exception as e:
        logger.error(f"Error fetching batch summaries: {e}")
        return {}

@router.delete("/cache")
async def clear_cache(
    user_id: str = Query("current_user", description="User ID to clear cache for")
):
    """Clear cache for a specific user (useful for testing and debugging)"""
    
    cleared_count = 0
    keys_to_remove = []
    
    for key in MEMORY_CACHE.keys():
        if key.startswith(f"{user_id}:"):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        MEMORY_CACHE.pop(key, None)
        CACHE_TIMESTAMPS.pop(key, None)
        cleared_count += 1
    
    logger.info(f"🧹 Cleared {cleared_count} cache entries for user {user_id}")
    
    return {
        'message': f'Cleared {cleared_count} cache entries for user {user_id}',
        'cleared_keys': cleared_count
    }

@router.get("/cache-stats")
async def get_cache_stats():
    """Get cache statistics for monitoring"""
    
    now = time.time()
    active_entries = 0
    expired_entries = 0
    
    for key, timestamp in CACHE_TIMESTAMPS.items():
        if now - timestamp < CACHE_TTL:
            active_entries += 1
        else:
            expired_entries += 1
    
    return {
        'total_entries': len(MEMORY_CACHE),
        'active_entries': active_entries,
        'expired_entries': expired_entries,
        'cache_ttl_seconds': CACHE_TTL,
        'memory_usage_mb': round(len(str(MEMORY_CACHE)) / 1024 / 1024, 2),
        'active_users': len(USER_ACTIVITY),
        'last_cleanup': 'not_implemented'  # TODO: Track cleanup times
    }

# Background cache warming (optional)
async def warm_cache_for_active_users():
    """Warm cache for recently active users"""
    
    now = time.time()
    recent_threshold = 300  # 5 minutes
    
    for user_id, last_activity in USER_ACTIVITY.items():
        if now - last_activity < recent_threshold:
            try:
                # Warm lightweight cache
                await get_unified_jobs_ultra_fast(user_id=user_id, lightweight=True)
                logger.info(f"🔥 Warmed cache for active user: {user_id}")
            except Exception as e:
                logger.warning(f"Failed to warm cache for {user_id}: {e}")

# Startup event to initialize cache warming (if needed)
@router.on_event("startup")
async def startup_event():
    logger.info("🚀 Ultra-Fast Unified API initialized with aggressive memory caching")
    logger.info(f"   Cache TTL: {CACHE_TTL} seconds")
    logger.info(f"   Expected performance: <1ms for cache hits, <2s for fresh loads")