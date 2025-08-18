"""
Unified Job Storage Layer for OMTX-Hub
Provides consistent storage interface for all job types with enhanced querying capabilities
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from models.enhanced_job_model import (
    EnhancedJobData, JobType, JobStatus, TaskType
)
from database.unified_job_manager import unified_job_manager
from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

class UnifiedJobStorage:
    """Unified storage interface for all job types with enhanced querying"""
    
    def __init__(self):
        self.job_manager = unified_job_manager
        self.storage_service = gcp_storage_service
        
        # Cache for frequently accessed data
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    # === Core CRUD Operations ===
    
    async def store_job(self, job: EnhancedJobData) -> bool:
        """Store enhanced job in database"""
        try:
            firestore_data = job.to_firestore_dict()
            created_id = self.job_manager.create_job(firestore_data)
            
            if created_id:
                # Clear relevant caches
                self._invalidate_user_cache(job.user_id)
                logger.debug(f"Stored job: {job.id} ({job.job_type.value})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to store job {job.id}: {e}")
            return False
    
    async def get_job(self, job_id: str, enrich_with_results: bool = False) -> Optional[EnhancedJobData]:
        """Get job by ID with optional result enrichment"""
        try:
            # Check cache first
            cache_key = f"job:{job_id}:{enrich_with_results}"
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            
            # Get from database
            job_data = self.job_manager.get_job(job_id)
            if not job_data:
                return None
            
            # Convert to enhanced job ONLY if it's in the new format
            enhanced_job = EnhancedJobData.from_job_data(job_data)
            if enhanced_job is None:
                # Job is in legacy format, don't show it
                logger.debug(f"Job {job_id} is in legacy format, skipping")
                return None
            
            # Enrich with results if requested and completed
            if enrich_with_results and enhanced_job.status == JobStatus.COMPLETED:
                enhanced_job = await self._enrich_job_with_results(enhanced_job)
            
            # Cache the result
            self._set_cached(cache_key, enhanced_job)
            
            return enhanced_job
            
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None
    
    async def update_job(self, job: EnhancedJobData) -> bool:
        """Update enhanced job in database"""
        try:
            # Update timestamp
            job.updated_at = time.time()
            
            # Convert to firestore format
            firestore_data = job.to_firestore_dict()
            update_data = {k: v for k, v in firestore_data.items() 
                          if k not in ['id', 'created_at']}
            
            success = self.job_manager.update_job_status(
                job.id, job.status.value, update_data
            )
            
            if success:
                # Invalidate caches
                self._invalidate_job_cache(job.id)
                self._invalidate_user_cache(job.user_id)
                logger.debug(f"Updated job: {job.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to update job {job.id}: {e}")
            return False
    
    # === Query Operations ===
    
    async def get_user_jobs(
        self, 
        user_id: str = "current_user",
        limit: int = 50,
        job_types: Optional[List[JobType]] = None,
        status: Optional[JobStatus] = None,
        task_types: Optional[List[str]] = None,
        page: int = 1
    ) -> Tuple[List[EnhancedJobData], Dict[str, Any]]:
        """Get user jobs with filtering and pagination"""
        
        try:
            logger.debug(f"Querying jobs for user {user_id}: types={job_types}, status={status}")
            
            # Build cache key
            cache_key = f"user_jobs:{user_id}:{limit}:{job_types}:{status}:{task_types}:{page}"
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            
            # Get jobs from the jobs collection (new format only)
            all_jobs = self.job_manager.get_recent_jobs(limit * 2)
            
            # Filter jobs
            filtered_jobs = []
            for job_data in all_jobs:
                # Filter by user
                if user_id != "all" and job_data.get('user_id', 'current_user') != user_id:
                    continue
                
                # Convert to enhanced job ONLY if it's in the new format
                # This will return None for legacy jobs
                enhanced_job = EnhancedJobData.from_job_data(job_data)
                if enhanced_job is None:
                    # Skip legacy jobs completely
                    continue
                
                # Filter by job types
                if job_types and enhanced_job.job_type not in job_types:
                    continue
                
                # Filter by status
                if status and enhanced_job.status != status:
                    continue
                
                # Filter by task types
                if task_types and enhanced_job.task_type not in task_types:
                    continue
                
                filtered_jobs.append(enhanced_job)
            
            # Sort by created_at descending
            filtered_jobs.sort(key=lambda x: x.created_at, reverse=True)
            
            # Implement pagination
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_jobs = filtered_jobs[start_idx:end_idx]
            
            # Build pagination info
            pagination = {
                'page': page,
                'per_page': limit,
                'total': len(filtered_jobs),
                'total_pages': (len(filtered_jobs) + limit - 1) // limit,
                'has_more': end_idx < len(filtered_jobs)
            }
            
            result = (paginated_jobs, pagination)
            
            # Cache result
            self._set_cached(cache_key, result, ttl=60)  # Shorter TTL for user lists
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get user jobs: {e}")
            return [], {'page': page, 'per_page': limit, 'total': 0, 'total_pages': 0, 'has_more': False}
    
    async def get_batch_children(
        self, 
        batch_parent_id: str,
        include_results: bool = False,
        status_filter: Optional[JobStatus] = None
    ) -> List[EnhancedJobData]:
        """Get all children of a batch job with optional filtering"""
        
        try:
            cache_key = f"batch_children:{batch_parent_id}:{include_results}:{status_filter}"
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            
            # Use database-level filtering for better performance
            # Get all recent jobs and filter for children
            all_jobs = self.job_manager.get_recent_jobs(limit=500)  # Increased limit for batch children
            children = []
            
            for job_data in all_jobs:
                # Check if this is a child of our batch
                is_child = (
                    job_data.get('batch_parent_id') == batch_parent_id or
                    job_data.get('input_data', {}).get('parent_batch_id') == batch_parent_id
                )
                
                if not is_child:
                    continue
                
                # Convert to enhanced job ONLY if it's in the new format
                enhanced_job = EnhancedJobData.from_job_data(job_data)
                if enhanced_job is None:
                    # Skip legacy format children
                    continue
                
                # Filter by status if specified
                if status_filter and enhanced_job.status != status_filter:
                    continue
                
                # Enrich with results if requested
                if include_results and enhanced_job.status == JobStatus.COMPLETED:
                    enhanced_job = await self._enrich_job_with_results(enhanced_job)
                
                children.append(enhanced_job)
            
            # Sort by batch_index if available
            children.sort(key=lambda x: x.batch_index or 0)
            
            # Cache result
            self._set_cached(cache_key, children, ttl=30)  # Short TTL for dynamic data
            
            return children
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch children for {batch_parent_id}: {e}")
            return []
    
    async def get_batch_with_children(
        self, 
        batch_id: str,
        include_results: bool = False
    ) -> Optional[Tuple[EnhancedJobData, List[EnhancedJobData], Dict[str, Any]]]:
        """Get batch parent with children and statistics"""
        
        try:
            # Get parent job
            parent = await self.get_job(batch_id, enrich_with_results=include_results)
            if not parent or parent.job_type != JobType.BATCH_PARENT:
                return None
            
            # Get children
            children = await self.get_batch_children(batch_id, include_results)
            
            # Calculate statistics
            child_statuses = [child.status for child in children]
            statistics = parent.calculate_batch_progress(child_statuses)
            
            return parent, children, statistics
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch with children {batch_id}: {e}")
            return None
    
    # === Search and Query Helpers ===
    
    async def search_jobs(
        self,
        query: str,
        user_id: str = "current_user",
        job_types: Optional[List[JobType]] = None,
        limit: int = 20
    ) -> List[EnhancedJobData]:
        """Search jobs by name, task type, or other attributes"""
        
        try:
            # Get user jobs
            all_jobs, _ = await self.get_user_jobs(
                user_id=user_id, 
                limit=100,  # Search in larger set
                job_types=job_types
            )
            
            # Filter by search query
            query_lower = query.lower()
            matching_jobs = []
            
            for job in all_jobs:
                # Search in name
                if query_lower in job.name.lower():
                    matching_jobs.append(job)
                # Search in task type
                elif query_lower in job.task_type.lower():
                    matching_jobs.append(job)
                # Search in input data (protein name, etc.)
                elif isinstance(job.input_data, dict):
                    for value in job.input_data.values():
                        if isinstance(value, str) and query_lower in value.lower():
                            matching_jobs.append(job)
                            break
            
            return matching_jobs[:limit]
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    async def get_jobs_by_status(
        self,
        status: JobStatus,
        job_types: Optional[List[JobType]] = None,
        limit: int = 50
    ) -> List[EnhancedJobData]:
        """Get jobs by status with optional job type filtering"""
        
        try:
            # Use database query for efficiency
            status_jobs = self.job_manager.get_jobs_by_status(status.value, limit * 2)
            
            enhanced_jobs = []
            for job_data in status_jobs:
                # Convert to enhanced job ONLY if it's in the new format
                enhanced_job = EnhancedJobData.from_job_data(job_data)
                if enhanced_job is None:
                    # Skip legacy format jobs
                    continue
                
                # Filter by job types if specified
                if job_types and enhanced_job.job_type not in job_types:
                    continue
                
                enhanced_jobs.append(enhanced_job)
            
            return enhanced_jobs[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get jobs by status {status}: {e}")
            return []
    
    # === Statistics and Analytics ===
    
    async def get_user_statistics(self, user_id: str = "current_user") -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        
        try:
            cache_key = f"user_stats:{user_id}"
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            
            # Get all user jobs
            all_jobs, _ = await self.get_user_jobs(user_id, limit=500)
            
            # Calculate statistics
            stats = {
                'total_jobs': len(all_jobs),
                'by_status': {},
                'by_job_type': {},
                'by_task_type': {},
                'recent_activity': 0,
                'success_rate': 0,
                'avg_completion_time': 0
            }
            
            completion_times = []
            successful_jobs = 0
            recent_threshold = time.time() - (7 * 24 * 3600)  # 7 days ago
            
            for job in all_jobs:
                # Count by status
                status_key = job.status.value
                stats['by_status'][status_key] = stats['by_status'].get(status_key, 0) + 1
                
                # Count by job type
                type_key = job.job_type.value
                stats['by_job_type'][type_key] = stats['by_job_type'].get(type_key, 0) + 1
                
                # Count by task type
                task_key = job.task_type
                stats['by_task_type'][task_key] = stats['by_task_type'].get(task_key, 0) + 1
                
                # Recent activity
                if job.created_at > recent_threshold:
                    stats['recent_activity'] += 1
                
                # Success rate calculation
                if job.status == JobStatus.COMPLETED:
                    successful_jobs += 1
                
                # Completion time calculation
                duration = job._calculate_duration()
                if duration:
                    completion_times.append(duration)
            
            # Calculate derived statistics
            if len(all_jobs) > 0:
                stats['success_rate'] = (successful_jobs / len(all_jobs)) * 100
            
            if completion_times:
                stats['avg_completion_time'] = sum(completion_times) / len(completion_times)
            
            # Cache result
            self._set_cached(cache_key, stats, ttl=300)  # 5 minute cache
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get user statistics: {e}")
            return {}
    
    # === Result Enrichment ===
    
    async def _enrich_job_with_results(self, job: EnhancedJobData) -> EnhancedJobData:
        """Enrich job with results from GCP storage if not already present"""
        
        try:
            # Skip if already has output data
            if job.output_data:
                return job
            
            # Try to load from GCP storage
            if job.gcp_storage_path:
                storage_path = job.gcp_storage_path
            else:
                # Try standard path
                storage_path = f"jobs/{job.id}/results.json"
            
            # Attempt to load results
            results = await self._load_results_from_storage(storage_path)
            if results:
                job.output_data = results
                logger.debug(f"Enriched job {job.id} with GCP results")
            
            return job
            
        except Exception as e:
            logger.debug(f"Could not enrich job {job.id}: {e}")
            return job
    
    async def _load_results_from_storage(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """Load results from GCP storage"""
        try:
            # This would use the actual storage service
            # For now, return None since we don't have the exact implementation
            return None
        except Exception:
            return None
    
    # === Cache Management ===
    
    def _get_cached(self, key: str) -> Any:
        """Get item from cache if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry['timestamp'] < entry['ttl']:
                return entry['data']
            else:
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, data: Any, ttl: int = None) -> None:
        """Set item in cache with TTL"""
        if ttl is None:
            ttl = self._cache_ttl
        
        self._cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl
        }
        
        # Simple cache cleanup
        if len(self._cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]['timestamp']
            )[:20]
            
            for key in oldest_keys:
                del self._cache[key]
    
    def _invalidate_job_cache(self, job_id: str) -> None:
        """Invalidate cache entries for a specific job"""
        keys_to_remove = [key for key in self._cache.keys() if f":{job_id}:" in key or key.endswith(f":{job_id}")]
        for key in keys_to_remove:
            del self._cache[key]
    
    def _invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate cache entries for a specific user"""
        keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"user_jobs:{user_id}:") or key.startswith(f"user_stats:{user_id}")]
        for key in keys_to_remove:
            del self._cache[key]
    
    def clear_cache(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        logger.debug("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'entries': len(self._cache),
            'keys': list(self._cache.keys()),
            'memory_usage_estimate': len(str(self._cache))
        }

# Global instance
unified_job_storage = UnifiedJobStorage()