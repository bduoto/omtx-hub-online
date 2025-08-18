"""
GCP Results Indexer Service
Direct replacement for my_results_indexer using GCP storage only
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config.gcp_storage import gcp_storage
# Note: We'll get job metadata from GCP metadata.json files

logger = logging.getLogger(__name__)

class GCPResultsIndexer:
    """Service to index and serve results directly from GCP bucket"""
    
    def __init__(self):
        self.storage = gcp_storage
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache
    
    async def get_user_results(self, user_id: str = "current_user", limit: int = 50) -> Dict[str, Any]:
        """Get all user results from GCP storage"""
        
        if not self.storage.available:
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

# Global instance
gcp_results_indexer = GCPResultsIndexer()