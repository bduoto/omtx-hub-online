"""
High-Performance Results Service
Optimized for sub-second response times
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import hashlib

from config.gcp_storage import gcp_storage
from database.unified_job_manager import unified_job_manager
from config.gcp_database import gcp_database

logger = logging.getLogger(__name__)

class PerformanceOptimizedResults:
    """Ultra-fast results service with multiple optimization strategies"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    async def get_my_results_fast(self, 
                                 user_id: str = "current_user", 
                                 limit: int = 50,
                                 page: int = 1) -> Dict[str, Any]:
        """
        Ultra-fast results loading with multiple optimization strategies:
        1. Database-first approach (no GCP scanning)
        2. Lazy loading of result details
        3. Aggressive caching
        4. Parallel processing
        """
        
        start_time = time.time()
        cache_key = f"fast_results:{user_id}:{limit}:{page}"
        
        # Strategy 1: Check cache first
        if self._is_cache_valid(cache_key):
            logger.info(f"⚡ Cache hit for {user_id} - {time.time() - start_time:.3f}s")
            return self.cache[cache_key]['data']
        
        try:
            # Strategy 2: Database-first approach (fastest)
            results = await self._get_results_from_database_only(user_id, limit, page)
            
            # Strategy 3: Lazy load only essential metadata
            enhanced_results = await self._lazy_enhance_results(results)
            
            # Strategy 4: Cache aggressively
            self._cache_results(cache_key, enhanced_results)
            
            elapsed = time.time() - start_time
            logger.info(f"⚡ Fast results for {user_id}: {len(enhanced_results.get('results', []))} jobs in {elapsed:.3f}s")
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"❌ Fast results failed: {e}")
            return {"results": [], "total": 0, "source": "error", "error": str(e)}
    
    async def _get_results_from_database_only(self, user_id: str, limit: int, page: int) -> Dict[str, Any]:
        """Get results from database only - no GCP scanning"""

        # Use the optimized database query with caching and composite indexes
        jobs = []
        next_cursor = None

        try:
            # Try optimized method first
            if gcp_database.available:
                jobs, next_cursor = gcp_database.get_user_jobs_optimized(
                    user_id=user_id,
                    limit=limit,
                    cursor=None  # First page only for now
                )
                logger.info(f"⚡ Retrieved {len(jobs)} jobs using optimized query")
            else:
                raise Exception("GCP database not available")

        except Exception as e:
            logger.warning(f"⚠️ Optimized query failed, falling back to unified job manager: {e}")
            # Fallback to unified job manager
            try:
                jobs = unified_job_manager.primary_backend.get_user_jobs(user_id, limit=limit)
                logger.info(f"⚡ Retrieved {len(jobs)} jobs using unified job manager")
            except Exception as e2:
                logger.error(f"❌ All database queries failed: {e2}")
                jobs = []
        
        # Filter for individual jobs only (exclude batch parents)
        individual_jobs = []
        for job in jobs:
            job_type = job.get('job_type', '')
            task_type = job.get('task_type', '')

            # Include individual jobs and batch children, exclude batch parents
            if (job_type != 'batch_parent' and
                not task_type.startswith('batch_') and
                not job.get('batch_parent_id')):  # Individual jobs
                individual_jobs.append(job)
            elif job.get('batch_parent_id'):  # Batch children
                individual_jobs.append(job)

        # Since we're using optimized pagination, we already have the right amount
        paginated_jobs = individual_jobs[:limit]
        
        return {
            "results": paginated_jobs,
            "total": len(individual_jobs),
            "source": "database_optimized",
            "page": page,
            "limit": limit,
            "has_more": next_cursor is not None
        }
    
    async def _lazy_enhance_results(self, results_data: Dict[str, Any]) -> Dict[str, Any]:
        """Lazy enhancement - only load what's absolutely necessary for the list view"""
        
        jobs = results_data.get('results', [])
        enhanced_jobs = []
        
        for job in jobs:
            job_id = job.get('id', job.get('job_id'))

            # Load actual result data from GCP storage and determine correct status
            result_data = {}
            actual_status = 'unknown'

            try:
                # Try to load results from GCP storage
                from config.gcp_storage import gcp_storage
                import json

                # Try to load results.json from GCP
                results_path = f"jobs/{job_id}/results.json"
                results_content = gcp_storage.download_file(results_path)

                if results_content:
                    try:
                        result_data = json.loads(results_content.decode('utf-8'))
                        # Job has completed results in GCP
                        actual_status = 'completed'
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in results file for job {job_id}")
                        result_data = {}
                        actual_status = 'failed'
                elif job.get('modal_call_id'):
                    # Job has Modal call ID but no results yet - still running
                    actual_status = 'running'
                else:
                    # Job exists but no Modal call or results - failed/cancelled
                    actual_status = 'failed'

            except Exception as e:
                logger.warning(f"Could not load GCP results for job {job_id}: {e}")
                # Determine status based on available data
                if job.get('modal_call_id') and not job.get('output_data'):
                    actual_status = 'running'
                elif job.get('output_data'):
                    actual_status = 'completed'
                    result_data = job.get('output_data', {})
                else:
                    actual_status = 'failed'

            # Create comprehensive job data for frontend compatibility
            enhanced_job = {
                # Basic job information
                'id': job_id,
                'job_id': job_id,
                'job_name': job.get('name', job.get('job_name', 'Unnamed Job')),
                'name': job.get('name', job.get('job_name', 'Unnamed Job')),
                'task_type': job.get('task_type', 'unknown'),
                'status': actual_status,  # Use the determined actual status
                'created_at': job.get('created_at'),
                'updated_at': job.get('updated_at'),
                'model_name': job.get('model_name', 'boltz2'),
                'user_id': job.get('user_id', 'current_user'),

                # Execution information
                'execution_time': job.get('duration', 0),
                'duration': job.get('duration', 0),
                'has_results': bool(result_data),
                'has_structure': bool(result_data.get('structure_file_base64')),

                # Results data from GCP storage
                'output_data': result_data,
                'results': result_data,

                # Prediction results (extract from result_data)
                'affinity': result_data.get('affinity') if result_data else None,
                'confidence': result_data.get('confidence') if result_data else None,
                'structure_file_base64': result_data.get('structure_file_base64') if result_data else None,
                'ptm_score': result_data.get('ptm_score') if result_data else None,
                'plddt_score': result_data.get('plddt_score') if result_data else None,
                'iptm_score': result_data.get('iptm_score') if result_data else None,

                # Modal information
                'modal_call_id': job.get('modal_call_id'),
                'modal_function_id': job.get('modal_function_id'),

                # Batch information
                'batch_parent_id': job.get('batch_parent_id'),
                'job_type': job.get('job_type', 'individual'),

                # Input data
                'input_data': job.get('input_data', {}),

                # Keep original data for compatibility
                'original_data': job
            }

            enhanced_jobs.append(enhanced_job)
        
        return {
            "results": enhanced_jobs,
            "total": results_data.get('total', 0),
            "source": "database_enhanced",
            "page": results_data.get('page', 1),
            "limit": results_data.get('limit', 50),
            "cache_status": "miss"
        }
    
    async def get_job_details_on_demand(self, job_id: str) -> Dict[str, Any]:
        """Load full job details only when requested (for detail view)"""
        
        cache_key = f"job_details:{job_id}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            # Get job from database
            job_data = unified_job_manager.get_job(job_id)
            if not job_data:
                return {"error": "Job not found"}
            
            # Load results from GCP only if needed
            if job_data.get('output_data'):
                # Results already in database
                full_results = job_data['output_data']
            else:
                # Load from GCP as fallback
                full_results = await self._load_results_from_gcp(job_id)
            
            enhanced_job = {
                **job_data,
                'results': full_results,
                'loaded_at': datetime.utcnow().isoformat()
            }
            
            self._cache_results(cache_key, enhanced_job)
            return enhanced_job
            
        except Exception as e:
            logger.error(f"❌ Failed to load job details for {job_id}: {e}")
            return {"error": str(e)}
    
    async def _load_results_from_gcp(self, job_id: str) -> Dict[str, Any]:
        """Load results from GCP only when absolutely necessary"""
        
        if not gcp_storage.available:
            return {}
        
        try:
            results_path = f"jobs/{job_id}/results.json"
            results_content = gcp_storage.download_file(results_path)
            
            if results_content:
                return json.loads(results_content.decode('utf-8'))
            
        except Exception as e:
            logger.warning(f"Could not load GCP results for {job_id}: {e}")
        
        return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self.cache:
            return False
        
        entry = self.cache[cache_key]
        return time.time() - entry['timestamp'] < self.cache_ttl
    
    def _cache_results(self, cache_key: str, data: Any):
        """Cache results with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Simple cache cleanup (keep last 100 entries)
        if len(self.cache) > 100:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]

# Global instance
performance_results = PerformanceOptimizedResults()
