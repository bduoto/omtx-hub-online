"""
GCP Database Configuration - Complete Supabase Replacement
Uses Google Cloud Firestore for all database operations
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from google.cloud import firestore
from google.oauth2 import service_account
from functools import lru_cache

logger = logging.getLogger(__name__)

class GCPDatabaseManager:
    """Manages GCP Firestore operations - Complete Supabase replacement"""
    
    def __init__(self):
        self.db = None
        self.available = False
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'om-models')
        
        # Simple in-memory cache for performance
        self._cache = {}
        self._cache_ttl = 120  # 2 minutes default TTL
        
        # Initialize if credentials are available
        self._initialize()
    
    def _initialize(self):
        """Initialize Firestore client"""
        try:
            # Option 1: Default credentials (for GCP environment) - PRIORITIZED
            # This uses the service account attached to the GKE node pool
            if os.getenv('KUBERNETES_SERVICE_HOST'):  # Running in Kubernetes
                logger.info("🔧 Using GKE default credentials for Firestore")
                self.db = firestore.Client(project=self.project_id)
            else:
                # Option 2: Service account JSON for local development
                gcp_creds_json = os.getenv('GCP_CREDENTIALS_JSON')
                if gcp_creds_json:
                    logger.info("🔧 Using service account JSON for Firestore")
                    creds_dict = json.loads(gcp_creds_json)
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                    self.db = firestore.Client(project=self.project_id, credentials=credentials)
                else:
                    # Option 3: Default credentials (for local development)
                    logger.info("🔧 Using local default credentials for Firestore")
                    self.db = firestore.Client(project=self.project_id)
            
            # Test connection
            collections_ref = self.db.collections()
            list(collections_ref)  # Try to list collections to test connection
            
            self.available = True
            logger.info(f"✅ Connected to GCP Firestore: {self.project_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to GCP Firestore: {e}")
            self.available = False
    
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters"""
        params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{prefix}:{params}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"📋 Cache hit: {cache_key}")
                return cached_data
            else:
                del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL"""
        ttl = ttl or self._cache_ttl
        self._cache[cache_key] = (data, time.time())
        
        # Simple cache cleanup - remove oldest entries if cache too large
        if len(self._cache) > 100:
            sorted_entries = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_entries[:20]:
                del self._cache[key]
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern or all"""
        if pattern:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
            logger.info(f"🧹 Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")
        else:
            self._cache.clear()
            logger.info("🧹 Cleared all cache entries")
    
    def create_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Create a new job in Firestore with proper field initialization"""
        if not self.available:
            return None
            
        try:
            # Add timestamps and ensure required fields for indexing
            now = datetime.now(timezone.utc)
            job_data.update({
                'created_at': now,
                'updated_at': now,
                'user_id': job_data.get('user_id', 'anonymous'),
                'job_type': job_data.get('job_type', 'single'),
                'status': job_data.get('status', 'pending')
            })
            
            # Create document with provided ID or auto-generated ID
            provided_id = job_data.get('id')
            if provided_id:
                # Use provided ID
                doc_ref = self.db.collection('jobs').document(provided_id)
                job_id = provided_id
            else:
                # Auto-generate ID
                doc_ref = self.db.collection('jobs').document()
                job_id = doc_ref.id

            doc_ref.set(job_data)
            
            # Invalidate relevant caches
            self.invalidate_cache('get_jobs')
            self.invalidate_cache('user_jobs')
            
            logger.info(f"✅ Created job: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create job: {e}")
            return None
    
    def get_job(self, job_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get job by ID with caching"""
        if not self.available:
            return None
        
        # Check cache first
        cache_key = f"job:{job_id}"
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
        
        try:
            doc_ref = self.db.collection('jobs').document(job_id)
            doc = doc_ref.get()
            
            if doc.exists:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                
                # Check if results are stored in GCS due to size
                output_data = job_data.get('output_data', {})
                if output_data.get('results_in_gcp') and output_data.get('gcp_results_path'):
                    logger.info(f"📁 Loading large results from GCS for job {job_id}")
                    try:
                        from services.gcp_storage_service import gcp_storage_service
                        large_results = gcp_storage_service.storage.download_file(
                            output_data['gcp_results_path']
                        )
                        if large_results:
                            import json
                            if isinstance(large_results, bytes):
                                large_results = large_results.decode('utf-8')
                            full_output = json.loads(large_results)
                            # Merge the full results back
                            job_data['output_data'] = full_output
                            logger.info(f"✅ Loaded large results ({output_data.get('data_size_bytes', 0)} bytes) from GCS")
                    except Exception as e:
                        logger.error(f"❌ Failed to load large results from GCS: {e}")
                        # Keep the minimal data if we can't load the full results
                
                # Cache the result
                self._set_cache(cache_key, job_data)
                
                logger.info(f"✅ Retrieved job: {job_id}")
                return job_data
            else:
                logger.warning(f"⚠️ Job not found: {job_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: str, output_data: Dict[str, Any] = None) -> bool:
        """Update job status with cache invalidation and large data handling"""
        if not self.available:
            return False
            
        try:
            doc_ref = self.db.collection('jobs').document(job_id)
            
            update_data = {
                'status': status,
                'updated_at': datetime.now(timezone.utc)
            }
            
            if status == 'running':
                update_data['started_at'] = datetime.now(timezone.utc)
            elif status == 'completed':
                update_data['completed_at'] = datetime.now(timezone.utc)
            
            if output_data:
                # Check size of output_data to avoid Firestore 1MB limit
                import json
                data_size = len(json.dumps(output_data).encode('utf-8'))
                
                if data_size > 900000:  # Leave some buffer below 1MB limit
                    logger.warning(f"⚠️ Output data too large ({data_size} bytes) for job {job_id}, storing in GCS only")
                    # Store large results in GCS, keep only metadata in Firestore
                    from services.gcp_storage_service import gcp_storage_service
                    
                    # Store the full results in GCS
                    storage_path = f"jobs/{job_id}/large_results.json"
                    storage_success = gcp_storage_service.storage.upload_file(
                        storage_path,
                        output_data
                    )
                    
                    if storage_success:
                        # Store only essential metadata in Firestore
                        minimal_output = {
                            'status': output_data.get('status', 'completed'),
                            'results_in_gcp': True,
                            'gcp_results_path': storage_path,
                            'completed_at': output_data.get('completed_at'),
                            'affinity': output_data.get('results', {}).get('affinity') if 'results' in output_data else None,
                            'confidence': output_data.get('results', {}).get('confidence') if 'results' in output_data else None,
                            'has_results': True,
                            'files_stored_to_gcp': output_data.get('files_stored_to_gcp', True),
                            'modal_call_id': output_data.get('modal_call_id'),
                            'data_size_bytes': data_size
                        }
                        update_data['output_data'] = minimal_output
                    else:
                        logger.error(f"❌ Failed to store large results in GCS for job {job_id}")
                        return False
                else:
                    # Data is small enough for Firestore
                    update_data['output_data'] = output_data
            
            doc_ref.update(update_data)
            
            # Invalidate relevant caches
            self.invalidate_cache(f"job:{job_id}")
            self.invalidate_cache('get_jobs')
            self.invalidate_cache('user_jobs')
            
            logger.info(f"✅ Updated job {job_id} status to: {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update job {job_id}: {e}")
            return False
    
    def get_jobs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get jobs by status - backward compatible method"""
        jobs, _ = self.get_jobs_by_status_optimized(status, limit)
        return jobs
    
    def get_jobs_by_status_optimized(self, 
                                   status: str, 
                                   limit: int = 50,
                                   cursor: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Get jobs by status with cursor-based pagination"""
        if not self.available:
            return [], None
        
        # Check cache for first page
        cache_key = self._get_cache_key('jobs_status', status=status, limit=limit)
        if not cursor:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
        
        try:
            # Build optimized query using composite index
            query = (self.db.collection('jobs')
                    .where('status', '==', status)
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            # Apply cursor if provided
            if cursor:
                query = query.start_after(cursor)
            
            docs = list(query.stream())
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            # Get next cursor
            next_cursor = None
            if len(docs) == limit:
                last_doc = docs[-1]
                next_cursor = {
                    'created_at': last_doc.to_dict().get('created_at'),
                    'id': last_doc.id
                }
            
            result = (jobs, next_cursor)
            
            # Cache first page
            if not cursor:
                self._set_cache(cache_key, result)
            
            logger.info(f"✅ Retrieved {len(jobs)} jobs with status '{status}' (optimized)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get jobs by status {status}: {e}")
            return [], None
    
    def get_recent_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent jobs"""
        if not self.available:
            return []
            
        try:
            query = (self.db.collection('jobs')
                    .order_by('updated_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            logger.info(f"✅ Retrieved {len(jobs)} recent jobs")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent jobs: {e}")
            return []
    
    def save_job_result(self, job_id: str, result_data: Dict[str, Any]) -> bool:
        """Save job result to my_results collection"""
        if not self.available:
            return False
            
        try:
            result_data.update({
                'job_id': job_id,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            
            # Use job_id as document ID for easy retrieval
            doc_ref = self.db.collection('my_results').document(job_id)
            doc_ref.set(result_data)
            
            logger.info(f"✅ Saved result for job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save result for job {job_id}: {e}")
            return False
    
    def get_user_job_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user job results"""
        if not self.available:
            return []
            
        try:
            query = (self.db.collection('my_results')
                    .order_by('updated_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            results = []
            
            for doc in docs:
                result_data = doc.to_dict()
                result_data['id'] = doc.id
                results.append(result_data)
            
            logger.info(f"✅ Retrieved {len(results)} user job results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to get user job results: {e}")
            return []
    
    def add_gallery_item(self, gallery_data: Dict[str, Any]) -> Optional[str]:
        """Add item to gallery"""
        if not self.available:
            return None
            
        try:
            gallery_data.update({
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            
            doc_ref = self.db.collection('gallery').document()
            doc_ref.set(gallery_data)
            
            gallery_id = doc_ref.id
            logger.info(f"✅ Added gallery item: {gallery_id}")
            return gallery_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add gallery item: {e}")
            return None
    
    def get_gallery_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get gallery items"""
        if not self.available:
            return []
            
        try:
            query = (self.db.collection('gallery')
                    .order_by('updated_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            items = []
            
            for doc in docs:
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                items.append(item_data)
            
            logger.info(f"✅ Retrieved {len(items)} gallery items")
            return items
            
        except Exception as e:
            logger.error(f"❌ Failed to get gallery items: {e}")
            return []
    
    def upload_job_file(self, job_id: str, file_name: str, file_content: bytes) -> bool:
        """Upload job file metadata to Firestore (actual file goes to GCS)"""
        if not self.available:
            return False
            
        try:
            file_data = {
                'job_id': job_id,
                'file_name': file_name,
                'file_size': len(file_content),
                'uploaded_at': datetime.now(timezone.utc),
                'storage_path': f"jobs/{job_id}/{file_name}"
            }
            
            doc_ref = self.db.collection('job_files').document()
            doc_ref.set(file_data)
            
            logger.info(f"✅ Uploaded file metadata: {file_name} for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file metadata: {e}")
            return False
    
    def get_job_files(self, job_id: str) -> List[Dict[str, Any]]:
        """Get files for a job"""
        if not self.available:
            return []
            
        try:
            query = (self.db.collection('job_files')
                    .where('job_id', '==', job_id)
                    .order_by('uploaded_at', direction=firestore.Query.DESCENDING))
            
            docs = query.stream()
            files = []
            
            for doc in docs:
                file_data = doc.to_dict()
                file_data['id'] = doc.id
                files.append(file_data)
            
            logger.info(f"✅ Retrieved {len(files)} files for job: {job_id}")
            return files
            
        except Exception as e:
            logger.error(f"❌ Failed to get files for job {job_id}: {e}")
            return []

    def get_user_jobs_optimized(self,
                               user_id: str,
                               status: Optional[str] = None,
                               model_name: Optional[str] = None,
                               limit: int = 50,
                               cursor: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Get user jobs with optional filters and pagination"""
        if not self.available:
            return [], None
        
        # Check cache for first page
        cache_key = self._get_cache_key('user_jobs', user_id=user_id, status=status, model=model_name, limit=limit)
        if not cursor:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
        
        try:
            # Build query with composite index
            query = self.db.collection('jobs').where('user_id', '==', user_id)
            
            if status:
                query = query.where('status', '==', status)
            elif model_name:
                query = query.where('model_name', '==', model_name)
            
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
            
            if cursor:
                query = query.start_after(cursor)
            
            docs = list(query.stream())
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            # Get next cursor
            next_cursor = None
            if len(docs) == limit:
                last_doc = docs[-1]
                next_cursor = {
                    'created_at': last_doc.to_dict().get('created_at'),
                    'id': last_doc.id
                }
            
            result = (jobs, next_cursor)
            
            # Cache first page results
            if not cursor:
                self._set_cache(cache_key, result)
            
            logger.info(f"✅ Retrieved {len(jobs)} jobs for user '{user_id}'")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get user jobs: {e}")
            return [], None
    
    def get_batch_jobs_optimized(self,
                                batch_parent_id: str,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Get batch child jobs efficiently using composite index"""
        if not self.available:
            return []
        
        cache_key = f"batch_children:{batch_parent_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            # Use composite index on batch_parent_id and batch_index
            query = (self.db.collection('jobs')
                    .where('batch_parent_id', '==', batch_parent_id)
                    .order_by('batch_index')
                    .limit(limit))
            
            docs = query.stream()
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            # Cache the results
            self._set_cache(cache_key, jobs)
            
            logger.info(f"✅ Retrieved {len(jobs)} batch children for parent '{batch_parent_id}'")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch children: {e}")
            return []
    
    def get_jobs_by_type_optimized(self,
                                  job_type: str,
                                  user_id: Optional[str] = None,
                                  limit: int = 50,
                                  cursor: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Get jobs by type with optional user filter"""
        if not self.available:
            return [], None
        
        try:
            # Build query using composite index
            if user_id:
                query = (self.db.collection('jobs')
                        .where('user_id', '==', user_id)
                        .where('job_type', '==', job_type))
            else:
                query = self.db.collection('jobs').where('job_type', '==', job_type)
            
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
            
            if cursor:
                query = query.start_after(cursor)
            
            docs = list(query.stream())
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            # Get next cursor
            next_cursor = None
            if len(docs) == limit:
                last_doc = docs[-1]
                next_cursor = {
                    'created_at': last_doc.to_dict().get('created_at'),
                    'id': last_doc.id
                }
            
            logger.info(f"✅ Retrieved {len(jobs)} jobs of type '{job_type}'")
            return jobs, next_cursor
            
        except Exception as e:
            logger.error(f"❌ Failed to get jobs by type: {e}")
            return [], None
    
    def batch_get_jobs(self, job_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Efficiently get multiple jobs by ID"""
        if not self.available or not job_ids:
            return {}
        
        try:
            # Check cache first
            results = {}
            uncached_ids = []
            
            for job_id in job_ids:
                cache_key = f"job:{job_id}"
                cached = self._get_from_cache(cache_key)
                if cached:
                    results[job_id] = cached
                else:
                    uncached_ids.append(job_id)
            
            # Batch fetch uncached jobs
            if uncached_ids:
                # Firestore batch get (max 500 at a time)
                for i in range(0, len(uncached_ids), 500):
                    batch_ids = uncached_ids[i:i+500]
                    docs = self.db.get_all([
                        self.db.collection('jobs').document(job_id)
                        for job_id in batch_ids
                    ])
                    
                    for doc in docs:
                        if doc.exists:
                            job_data = doc.to_dict()
                            job_data['id'] = doc.id
                            results[doc.id] = job_data
                            
                            # Cache the result
                            self._set_cache(f"job:{doc.id}", job_data)
            
            logger.info(f"✅ Batch retrieved {len(results)} jobs")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to batch get jobs: {e}")
            return {}
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get statistics about query performance and cache usage"""
        cache_entries = len(self._cache)
        cache_size_bytes = sum(len(str(v)) for v in self._cache.values())
        
        return {
            'cache_entries': cache_entries,
            'cache_size_bytes': cache_size_bytes,
            'cache_hit_rate': 'Not tracked in simple implementation',
            'available': self.available,
            'project_id': self.project_id
        }

# Global instance
gcp_database = GCPDatabaseManager()