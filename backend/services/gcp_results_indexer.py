"""
GCP Results Indexer - Fast query optimization for dashboard performance
Enhanced with partitioned indexing, in-memory caching, and background updates
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib

from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

@dataclass
class JobIndex:
    """Optimized job index entry"""
    job_id: str
    batch_id: Optional[str]
    user_id: str
    status: str
    task_type: str
    model_type: str
    created_at: float
    completed_at: Optional[float]
    affinity: Optional[float]
    confidence: Optional[float]
    execution_time: Optional[float]
    storage_paths: Dict[str, str]
    indexed_at: float

@dataclass
class BatchIndex:
    """Optimized batch index entry"""
    batch_id: str
    user_id: str
    status: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    created_at: float
    completed_at: Optional[float]
    best_affinity: Optional[float]
    avg_confidence: Optional[float]
    total_execution_time: Optional[float]
    storage_paths: Dict[str, str]
    indexed_at: float

class GCPResultsIndexer:
    """
    High-performance indexer for fast dashboard queries
    
    Key features:
    - Partitioned by date for efficient queries
    - Separate indexes for jobs and batches
    - Compressed JSON storage
    - In-memory caching with TTL
    - Background indexing service
    - Backward compatibility with legacy methods
    """
    
    def __init__(self):
        self.storage = gcp_storage_service
        
        # Index organization
        self.index_structure = {
            'jobs': 'index/jobs/{date_partition}/',
            'batches': 'index/batches/{date_partition}/',
            'user_jobs': 'index/users/{user_id}/jobs/{date_partition}/',
            'user_batches': 'index/users/{user_id}/batches/{date_partition}/',
            'aggregates': 'index/aggregates/{date_partition}/',
            'search': 'index/search/'
        }
        
        # In-memory cache
        self.job_cache: Dict[str, JobIndex] = {}
        self.batch_cache: Dict[str, BatchIndex] = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps: Dict[str, float] = {}
        
        # Legacy cache for backward compatibility
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache
        
        # Background indexing
        self.indexing_queue: asyncio.Queue = asyncio.Queue()
        self.indexing_enabled = True
        self.index_batch_size = 50
        
        # Performance metrics
        self.metrics = {
            'jobs_indexed': 0,
            'batches_indexed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'indexing_errors': 0,
            'last_index_time': 0
        }
    
    async def index_job_result(
        self,
        job_id: str,
        job_data: Dict[str, Any],
        result_data: Dict[str, Any] = None
    ):
        """Index a completed job for fast queries"""
        
        try:
            # Create job index entry
            job_index = JobIndex(
                job_id=job_id,
                batch_id=job_data.get('batch_parent_id'),
                user_id=job_data.get('user_id', 'unknown'),
                status=job_data.get('status', 'unknown'),
                task_type=job_data.get('task_type', 'unknown'),
                model_type=job_data.get('metadata', {}).get('model_type', 'boltz2'),
                created_at=job_data.get('created_at', time.time()),
                completed_at=job_data.get('completed_at'),
                affinity=result_data.get('affinity') if result_data else None,
                confidence=result_data.get('confidence') if result_data else None,
                execution_time=result_data.get('execution_time') if result_data else None,
                storage_paths=self._extract_storage_paths(job_data, result_data),
                indexed_at=time.time()
            )
            
            # Add to indexing queue
            await self.indexing_queue.put(('job', job_index))
            
            # Update cache
            self.job_cache[job_id] = job_index
            self.cache_timestamps[f"job_{job_id}"] = time.time()
            
            logger.debug(f"📇 Queued job for indexing: {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Error indexing job {job_id}: {e}")
            self.metrics['indexing_errors'] += 1
    
    async def query_user_jobs(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
        date_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Fast query for user jobs with filtering"""
        
        try:
            # Check cache first
            cache_key = f"user_jobs_{user_id}_{limit}_{offset}_{status_filter}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self.metrics['cache_hits'] += 1
                return cached_result
            
            self.metrics['cache_misses'] += 1
            
            # Determine date partitions to query
            partitions = self._get_date_partitions(date_range)
            
            # Query indexed data
            jobs = []
            for partition in partitions:
                partition_jobs = await self._query_partition_jobs(
                    user_id, partition, status_filter
                )
                jobs.extend(partition_jobs)
            
            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            
            # Apply pagination
            total_count = len(jobs)
            paginated_jobs = jobs[offset:offset + limit]
            
            result = {
                'jobs': paginated_jobs,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            }
            
            # Cache result
            self._set_cache(cache_key, result, ttl=60)  # 1 minute TTL for queries
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error querying user jobs for {user_id}: {e}")
            return {'jobs': [], 'total_count': 0, 'limit': limit, 'offset': offset, 'has_more': False}
    
    async def get_dashboard_stats(self, user_id: str) -> Dict[str, Any]:
        """Get optimized dashboard statistics"""
        
        try:
            # Check cache first
            cache_key = f"dashboard_stats_{user_id}"
            cached_stats = self._get_from_cache(cache_key)
            if cached_stats:
                self.metrics['cache_hits'] += 1
                return cached_stats
            
            self.metrics['cache_misses'] += 1
            
            # Query recent data (last 30 days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            date_range = (start_date.timestamp(), end_date.timestamp())
            
            # Get partitions for date range
            partitions = self._get_date_partitions(date_range)
            
            # Aggregate statistics
            stats = {
                'total_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'running_jobs': 0,
                'total_batches': 0,
                'best_affinity': None,
                'avg_execution_time': 0,
                'total_execution_time': 0
            }
            
            execution_times = []
            affinities = []
            
            # Aggregate from partitions
            for partition in partitions:
                partition_stats = await self._get_partition_stats(user_id, partition)
                
                stats['total_jobs'] += partition_stats.get('job_count', 0)
                stats['completed_jobs'] += partition_stats.get('completed_jobs', 0)
                stats['failed_jobs'] += partition_stats.get('failed_jobs', 0)
                stats['running_jobs'] += partition_stats.get('running_jobs', 0)
                
                if partition_stats.get('execution_times'):
                    execution_times.extend(partition_stats['execution_times'])
                
                if partition_stats.get('affinities'):
                    affinities.extend(partition_stats['affinities'])
            
            # Calculate derived statistics
            if execution_times:
                stats['avg_execution_time'] = sum(execution_times) / len(execution_times)
                stats['total_execution_time'] = sum(execution_times)
            
            if affinities:
                stats['best_affinity'] = max(affinities)
            
            # Cache result
            self._set_cache(cache_key, stats, ttl=300)  # 5 minute TTL
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting dashboard stats for {user_id}: {e}")
            return {
                'total_jobs': 0, 'completed_jobs': 0, 'failed_jobs': 0, 'running_jobs': 0,
                'total_batches': 0, 'best_affinity': None, 'avg_execution_time': 0, 'total_execution_time': 0
            }

    async def get_user_results(self, user_id: str = "current_user", limit: int = 50) -> Dict[str, Any]:
        """Get all user results from GCP storage (legacy method for backward compatibility)"""
        
        # Try new optimized method first
        try:
            optimized_result = await self.query_user_jobs(user_id, limit=limit)
            if optimized_result.get('jobs'):
                # Convert to legacy format
                legacy_results = []
                for job in optimized_result['jobs']:
                    legacy_results.append({
                        'id': f"gcp_{job.get('job_id', '')}",
                        'job_id': job.get('job_id'),
                        'task_type': job.get('task_type'),
                        'job_name': f"Job {job.get('job_id', '')[:8]}",
                        'status': job.get('status'),
                        'created_at': datetime.fromtimestamp(job.get('created_at', 0)).isoformat(),
                        'user_id': user_id,
                        'storage_source': 'gcp_optimized',
                        'affinity': job.get('affinity'),
                        'confidence': job.get('confidence')
                    })
                
                return {
                    "results": legacy_results,
                    "total": optimized_result.get('total_count', 0),
                    "user_id": user_id,
                    "source": "gcp_optimized",
                    "cache_status": "optimized"
                }
        except Exception as e:
            logger.warning(f"⚠️ Optimized query failed, falling back to legacy: {e}")
        
        # Fallback to legacy implementation
        if not hasattr(self.storage, 'available') or not self.storage.available:
            logger.error("❌ GCP Storage not available!")
            return {"results": [], "total": 0, "source": "error", "error": "GCP storage not configured"}
        
        # Check cache first
        cache_key = f"user_results:{user_id}:{limit}"
        if self._is_cache_valid(cache_key):
            logger.info(f"📦 Returning cached results for {user_id}")
            return self._cache[cache_key]
        
        try:
            results = []
            
            # List all jobs from GCP jobs/ directory  
            jobs_prefix = "jobs/"
            job_ids = set()
            
            # Get all files in jobs/ directory and extract job IDs
            logger.debug(f"📂 Scanning GCP bucket for jobs with prefix: {jobs_prefix}")
            blobs = self.storage.bucket.list_blobs(prefix=jobs_prefix)
            
            for blob in blobs:
                # Extract job ID from blob path like "jobs/job_id/file.json"
                if blob.name.startswith(jobs_prefix) and '/' in blob.name[len(jobs_prefix):]:
                    relative_path = blob.name[len(jobs_prefix):]  # Remove "jobs/" prefix
                    job_id = relative_path.split('/')[0]  # Get first directory part
                    if job_id and job_id not in job_ids:
                        job_ids.add(job_id)
                        logger.debug(f"   Found job: {job_id}")
            
            logger.info(f"📊 Found {len(job_ids)} jobs in GCP bucket")
            
            # Process each job
            for job_id in sorted(job_ids, reverse=True)[:limit * 2]:  # Sort by ID (newer first)
                # Try to read metadata.json
                metadata_path = f"{jobs_prefix}{job_id}/metadata.json"
                metadata_content = self.storage.download_file(metadata_path)
                
                if not metadata_content:
                    continue
                
                try:
                    metadata = json.loads(metadata_content.decode('utf-8'))
                except:
                    continue
                
                # Get all files for this job
                job_files = self.storage.list_job_files(job_id)
                
                if job_files:
                    # Build result entry from metadata
                    result_entry = {
                        'id': f"gcp_{job_id}",
                        'job_id': job_id,
                        'task_type': metadata.get('task_type', 'unknown'),
                        'job_name': metadata.get('job_name', f'Job {job_id[:8]}'),
                        'status': 'completed',  # Only completed jobs are in GCP
                        'created_at': metadata.get('stored_at', datetime.utcnow().isoformat()),
                        'completed_at': metadata.get('stored_at', datetime.utcnow().isoformat()),
                        'user_id': user_id,
                        
                        # GCP specific fields
                        'file_count': len(job_files),
                        'file_types': list(set(f['name'].split('.')[-1] for f in job_files if '.' in f['name'])),
                        'has_structure': any(f['name'].endswith('.cif') for f in job_files),
                        'bucket_path': f"jobs/{job_id}/",
                        'storage_source': 'gcp',
                        
                        # Include results from GCP
                        'inputs': metadata.get('inputs', {}),
                        'results': {},  # Will be loaded from results.json
                        'output_data': {},  # Will be populated from results.json for frontend compatibility
                        'has_results': False,  # Will be set based on results.json availability

                        # Prediction-specific fields (will be populated from results if available)
                        'affinity': None,
                        'confidence': None,
                        'structure_file_base64': None,
                        'ptm_score': None,
                        'plddt_score': None,
                        'iptm_score': None
                    }
                    
                    # Try to load results.json
                    results_path = f"{jobs_prefix}{job_id}/results.json"
                    results_content = self.storage.download_file(results_path)
                    if results_content:
                        try:
                            results_data = json.loads(results_content.decode('utf-8'))
                            result_entry['results'] = results_data
                            # Also populate output_data for frontend compatibility
                            result_entry['output_data'] = results_data
                            result_entry['has_results'] = True

                            # Extract prediction-specific fields for frontend
                            if isinstance(results_data, dict):
                                result_entry['affinity'] = results_data.get('affinity')
                                result_entry['confidence'] = results_data.get('confidence')
                                result_entry['structure_file_base64'] = results_data.get('structure_file_base64')
                                result_entry['ptm_score'] = results_data.get('ptm_score')
                                result_entry['plddt_score'] = results_data.get('plddt_score')
                                result_entry['iptm_score'] = results_data.get('iptm_score')

                        except Exception as e:
                            logger.warning(f"Failed to parse results.json for job {job_id}: {e}")
                            result_entry['has_results'] = False
                    else:
                        result_entry['has_results'] = False
                    
                    # For batch jobs, get individual results
                    if metadata.get('task_type') == 'batch_protein_ligand_screening':
                        result_entry['results'] = await self._get_batch_results_from_gcp(job_id, job_files)
                    
                    results.append(result_entry)
                    
                    if len(results) >= limit:
                        break
            
            # Build response
            response = {
                "results": results[:limit],
                "total": len(results),
                "user_id": user_id,
                "source": "gcp",
                "cache_status": "miss"
            }
            
            # Cache the results
            self._cache[cache_key] = response
            self._cache_timestamp = datetime.now()
            
            logger.info(f"✅ Indexed {len(results)} results from GCP for {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to index GCP results: {str(e)}")
            return {
                "results": [],
                "total": 0,
                "source": "error",
                "error": str(e)
            }
    
    async def _get_batch_results_from_gcp(self, job_id: str, job_files: List[Dict]) -> Dict[str, Any]:
        """Extract batch results from GCP files"""
        
        batch_results = {
            'total_ligands': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'individual_results': []
        }
        
        # Look for results.json file
        results_file = next((f for f in job_files if f['name'] == 'results.json'), None)
        if results_file:
            try:
                content = self.storage.download_file(f"jobs/{job_id}/results.json")
                if content:
                    data = json.loads(content.decode('utf-8'))
                    batch_results.update(data)
            except Exception as e:
                logger.error(f"Failed to parse results.json for {job_id}: {e}")
        
        # Count structure files for completed jobs
        structure_files = [f for f in job_files if f['name'].endswith('.cif')]
        batch_results['completed_jobs'] = len(structure_files)
        batch_results['total_ligands'] = batch_results.get('total_ligands', len(structure_files))
        
        return batch_results
    
    async def get_job_download_info(self, job_id: str) -> Dict[str, Any]:
        """Get download URLs for job files from GCP"""
        
        if not self.storage.available:
            return {"error": "GCP storage not available"}
        
        try:
            job_files = self.storage.list_job_files(job_id)
            
            if not job_files:
                return {"error": "No files found for job"}
            
            download_info = {
                "job_id": job_id,
                "files": []
            }
            
            for file in job_files:
                # Generate signed URL for each file
                signed_url = self.storage.get_public_url(file['path'])
                if signed_url:
                    download_info["files"].append({
                        "name": file['name'],
                        "size": file['size'],
                        "type": file['content_type'],
                        "url": signed_url
                    })
            
            # Primary structure file
            structure_file = next((f for f in download_info["files"] if f['name'].endswith('.cif')), None)
            if structure_file:
                download_info["primary_structure_url"] = structure_file["url"]
            
            return download_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get download info: {str(e)}")
            return {"error": str(e)}
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache or not self._cache_timestamp:
            return False
        
        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl
    
    def invalidate_cache(self, user_id: Optional[str] = None):
        """Invalidate cache entries"""
        if user_id:
            keys_to_remove = [k for k in self._cache.keys() if f":{user_id}:" in k]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
        self._cache_timestamp = None
        logger.info(f"🗑️ Cache invalidated for {user_id or 'all users'}")
    
    # Enhanced indexing methods
    async def _query_partition_jobs(
        self,
        user_id: str,
        partition: str,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query jobs from a specific partition"""
        
        try:
            # Build index path
            index_path = f"index/users/{user_id}/jobs/{partition}/index.json.gz"
            
            # Check if partition exists
            if not await self._file_exists(index_path):
                return []
            
            # Load partition index
            index_data = await self._load_compressed_index(index_path)
            jobs = index_data.get('jobs', [])
            
            # Apply status filter
            if status_filter:
                jobs = [job for job in jobs if job.get('status') == status_filter]
            
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Error querying partition jobs {partition}: {e}")
            return []
    
    async def _get_partition_stats(self, user_id: str, partition: str) -> Dict[str, Any]:
        """Get aggregated statistics for a partition"""
        
        try:
            # Try to load pre-computed aggregates
            aggregate_path = f"index/aggregates/{partition}/{user_id}.json.gz"
            
            if await self._file_exists(aggregate_path):
                return await self._load_compressed_index(aggregate_path)
            
            # Fallback: compute from raw partition data
            jobs = await self._query_partition_jobs(user_id, partition)
            
            stats = {
                'job_count': len(jobs),
                'completed_jobs': len([j for j in jobs if j.get('status') == 'completed']),
                'failed_jobs': len([j for j in jobs if j.get('status') == 'failed']),
                'running_jobs': len([j for j in jobs if j.get('status') == 'running']),
                'execution_times': [j.get('execution_time') for j in jobs if j.get('execution_time')],
                'affinities': [j.get('affinity') for j in jobs if j.get('affinity')]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting partition stats {partition}: {e}")
            return {}
    
    async def start_background_indexing(self):
        """Start background indexing service"""
        
        logger.info("🚀 Starting background indexing service...")
        
        while self.indexing_enabled:
            try:
                # Process indexing queue
                await self._process_indexing_batch()
                
                # Periodic cleanup
                await self._cleanup_old_cache()
                
                # Small delay to prevent CPU overload
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                logger.info("🛑 Background indexing cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in background indexing: {e}")
                await asyncio.sleep(5)  # Back off on errors
    
    async def _process_indexing_batch(self):
        """Process a batch of indexing operations"""
        
        batch_items = []
        
        # Collect batch of items from queue
        try:
            # Get first item (blocking)
            item = await asyncio.wait_for(self.indexing_queue.get(), timeout=1.0)
            batch_items.append(item)
            
            # Get additional items (non-blocking)
            for _ in range(self.index_batch_size - 1):
                try:
                    item = self.indexing_queue.get_nowait()
                    batch_items.append(item)
                except asyncio.QueueEmpty:
                    break
                    
        except asyncio.TimeoutError:
            return  # No items to process
        
        if not batch_items:
            return
        
        # Group by type and partition
        job_partitions = defaultdict(list)
        
        for item_type, item_data in batch_items:
            partition = self._get_date_partition(item_data.created_at)
            
            if item_type == 'job':
                job_partitions[partition].append(item_data)
        
        # Process job partitions
        for partition, jobs in job_partitions.items():
            await self._update_job_partition(partition, jobs)
            self.metrics['jobs_indexed'] += len(jobs)
        
        self.metrics['last_index_time'] = time.time()
        
        logger.debug(f"📇 Processed indexing batch: {len(job_partitions)} job partitions")
    
    async def _update_job_partition(self, partition: str, new_jobs: List[JobIndex]):
        """Update job partition with new entries"""
        
        try:
            # Group jobs by user
            user_jobs = defaultdict(list)
            for job in new_jobs:
                user_jobs[job.user_id].append(asdict(job))
            
            # Update each user's partition
            for user_id, jobs in user_jobs.items():
                await self._update_user_job_partition(user_id, partition, jobs)
            
        except Exception as e:
            logger.error(f"❌ Error updating job partition {partition}: {e}")
    
    async def _update_user_job_partition(self, user_id: str, partition: str, new_jobs: List[Dict[str, Any]]):
        """Update user's job partition index"""
        
        try:
            index_path = f"index/users/{user_id}/jobs/{partition}/index.json.gz"
            
            # Load existing index
            existing_jobs = []
            if await self._file_exists(index_path):
                existing_index = await self._load_compressed_index(index_path)
                existing_jobs = existing_index.get('jobs', [])
            
            # Merge with new jobs (deduplicate by job_id)
            job_dict = {job['job_id']: job for job in existing_jobs}
            for job in new_jobs:
                job_dict[job['job_id']] = job
            
            # Create updated index
            updated_index = {
                'partition': partition,
                'user_id': user_id,
                'jobs': list(job_dict.values()),
                'count': len(job_dict),
                'updated_at': time.time()
            }
            
            # Save compressed index
            await self._save_compressed_index(index_path, updated_index)
            
        except Exception as e:
            logger.error(f"❌ Error updating user job partition {user_id}/{partition}: {e}")
    
    async def _save_compressed_index(self, path: str, data: Dict[str, Any]):
        """Save index data with compression"""
        
        try:
            import gzip
            
            # Serialize and compress
            json_data = json.dumps(data, separators=(',', ':')).encode('utf-8')
            compressed_data = gzip.compress(json_data)
            
            # Upload to storage
            await self.storage.upload_file(
                path,
                compressed_data,
                content_type='application/gzip'
            )
            
        except Exception as e:
            logger.error(f"❌ Error saving compressed index {path}: {e}")
            raise
    
    async def _load_compressed_index(self, path: str) -> Dict[str, Any]:
        """Load and decompress index data"""
        
        try:
            import gzip
            
            # Download compressed data
            compressed_data = await self.storage.download_file(path)
            
            # Decompress and parse
            json_data = gzip.decompress(compressed_data)
            return json.loads(json_data.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"❌ Error loading compressed index {path}: {e}")
            return {}
    
    def _extract_storage_paths(self, job_data: Dict[str, Any], result_data: Dict[str, Any] = None) -> Dict[str, str]:
        """Extract storage paths from job and result data"""
        
        job_id = job_data.get('id')
        batch_id = job_data.get('batch_parent_id')
        
        if batch_id:
            base_path = f"batches/{batch_id}/jobs/{job_id}"
        else:
            base_path = f"jobs/{job_id}"
        
        return {
            'results': f"{base_path}/results.json",
            'metadata': f"{base_path}/metadata.json",
            'structure': f"{base_path}/structure.cif"
        }
    
    def _get_date_partition(self, timestamp: float) -> str:
        """Get date partition for a timestamp"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d')
    
    def _get_date_partitions(self, date_range: Optional[tuple] = None) -> List[str]:
        """Get list of date partitions for a date range"""
        
        if not date_range:
            # Default to last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromtimestamp(date_range[0])
            end_date = datetime.fromtimestamp(date_range[1])
        
        partitions = []
        current_date = start_date
        
        while current_date <= end_date:
            partitions.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        return partitions
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache with TTL check"""
        
        if key not in self.cache_timestamps:
            return None
        
        if time.time() - self.cache_timestamps[key] > self.cache_ttl:
            # Expired
            self.cache_timestamps.pop(key, None)
            if key in self.job_cache:
                self.job_cache.pop(key, None)
            if key in self.batch_cache:
                self.batch_cache.pop(key, None)
            return None
        
        # Check different cache types
        if key.startswith('job_'):
            return self.job_cache.get(key)
        elif key.startswith('batch_'):
            return self.batch_cache.get(key)
        else:
            # Generic cache (stored in job_cache for simplicity)
            return self.job_cache.get(key)
    
    def _set_cache(self, key: str, value: Any, ttl: int = None):
        """Set item in cache with TTL"""
        
        if ttl is None:
            ttl = self.cache_ttl
        
        self.cache_timestamps[key] = time.time()
        
        # Store in appropriate cache
        if key.startswith('job_') or not key.startswith('batch_'):
            self.job_cache[key] = value
        else:
            self.batch_cache[key] = value
    
    async def _cleanup_old_cache(self):
        """Clean up expired cache entries"""
        
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, timestamp in self.cache_timestamps.items():
                if current_time - timestamp > self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.cache_timestamps.pop(key, None)
                self.job_cache.pop(key, None)
                self.batch_cache.pop(key, None)
            
            if expired_keys:
                logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up cache: {e}")
    
    async def _file_exists(self, path: str) -> bool:
        """Check if file exists in storage"""
        try:
            return await self.storage.file_exists(path)
        except:
            return False
    
    def get_indexer_metrics(self) -> Dict[str, Any]:
        """Get indexer performance metrics"""
        
        return {
            'jobs_indexed': self.metrics['jobs_indexed'],
            'batches_indexed': self.metrics['batches_indexed'],
            'cache_hits': self.metrics['cache_hits'],
            'cache_misses': self.metrics['cache_misses'],
            'cache_hit_rate': (
                self.metrics['cache_hits'] / 
                max(self.metrics['cache_hits'] + self.metrics['cache_misses'], 1) * 100
            ),
            'indexing_errors': self.metrics['indexing_errors'],
            'last_index_time': self.metrics['last_index_time'],
            'queue_size': self.indexing_queue.qsize(),
            'cache_size': len(self.job_cache) + len(self.batch_cache),
            'indexing_enabled': self.indexing_enabled
        }
    
    def stop_indexing(self):
        """Stop background indexing"""
        self.indexing_enabled = False
        logger.info("🛑 Background indexing stopped")

# Global instance
gcp_results_indexer = GCPResultsIndexer()

async def start_indexing_service():
    """Start the background indexing service"""
    
    logger.info("🚀 Starting GCP results indexing service...")
    
    # Start background indexing
    indexing_task = asyncio.create_task(gcp_results_indexer.start_background_indexing())
    
    logger.info("✅ GCP results indexing service started")
    
    return indexing_task