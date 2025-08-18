"""
GCP Bucket Browser
Utilities for browsing and managing the organized bucket structure
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from config.gcp_storage import gcp_storage

logger = logging.getLogger(__name__)

class GCPBucketBrowser:
    """Browse and manage organized bucket structure"""
    
    def __init__(self):
        self.storage = gcp_storage
    
    async def list_models(self) -> List[str]:
        """List all model directories in archive"""
        if not self.storage.available:
            return []
        
        try:
            prefix = "archive/"
            blobs = self.storage.bucket.list_blobs(prefix=prefix, delimiter='/')
            
            models = []
            for prefix in blobs.prefixes:
                model_name = prefix.replace('archive/', '').rstrip('/')
                if model_name:
                    models.append(model_name)
            
            return sorted(models)
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def list_tasks_for_model(self, model: str) -> List[str]:
        """List all task directories for a model"""
        if not self.storage.available:
            return []
        
        try:
            prefix = f"archive/{model}/"
            blobs = self.storage.bucket.list_blobs(prefix=prefix, delimiter='/')
            
            tasks = []
            for prefix in blobs.prefixes:
                task_name = prefix.replace(f'archive/{model}/', '').rstrip('/')
                if task_name:
                    tasks.append(task_name)
            
            return sorted(tasks)
            
        except Exception as e:
            logger.error(f"Failed to list tasks for {model}: {e}")
            return []
    
    async def list_jobs_by_task(self, model: str, task: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List jobs for a specific model/task combination"""
        if not self.storage.available:
            return []
        
        try:
            prefix = f"archive/{model}/{task}/"
            blobs = self.storage.bucket.list_blobs(prefix=prefix)
            
            jobs = {}
            for blob in blobs:
                # Parse job ID from path
                path_parts = blob.name.split('/')
                if len(path_parts) >= 4:
                    job_id = path_parts[3]
                    
                    if job_id not in jobs:
                        jobs[job_id] = {
                            'job_id': job_id,
                            'model': model,
                            'task': task,
                            'files': [],
                            'created': None,
                            'size': 0
                        }
                    
                    jobs[job_id]['files'].append(blob.name.split('/')[-1])
                    jobs[job_id]['size'] += blob.size
                    
                    if blob.time_created and (not jobs[job_id]['created'] or blob.time_created < jobs[job_id]['created']):
                        jobs[job_id]['created'] = blob.time_created
            
            # Convert to list and sort by creation time
            job_list = list(jobs.values())
            job_list.sort(key=lambda x: x['created'] or datetime.min, reverse=True)
            
            return job_list[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list jobs for {model}/{task}: {e}")
            return []
    
    async def get_bucket_stats(self) -> Dict[str, Any]:
        """Get statistics about bucket usage"""
        if not self.storage.available:
            return {}
        
        try:
            stats = {
                'models': {},
                'total_jobs': 0,
                'total_size': 0,
                'recent_jobs': []
            }
            
            # Count jobs in flat directory
            jobs_blobs = self.storage.bucket.list_blobs(prefix="jobs/")
            job_count = 0
            recent_jobs = []
            
            for blob in jobs_blobs:
                stats['total_size'] += blob.size
                path_parts = blob.name.split('/')
                if len(path_parts) >= 2 and path_parts[1] and '/' in blob.name[5:]:
                    job_id = path_parts[1]
                    if job_id not in [j['job_id'] for j in recent_jobs]:
                        recent_jobs.append({
                            'job_id': job_id,
                            'created': blob.time_created.isoformat() if blob.time_created else None,
                            'file': blob.name
                        })
                        job_count += 1
            
            stats['total_jobs'] = job_count
            stats['recent_jobs'] = sorted(recent_jobs, key=lambda x: x['created'] or '', reverse=True)[:10]
            
            # Count by model/task in archive
            archive_blobs = self.storage.bucket.list_blobs(prefix="archive/")
            for blob in archive_blobs:
                path_parts = blob.name.split('/')
                if len(path_parts) >= 3:
                    model = path_parts[1]
                    task = path_parts[2] if len(path_parts) > 2 else 'Unknown'
                    
                    if model not in stats['models']:
                        stats['models'][model] = {'tasks': {}, 'total_size': 0, 'job_count': 0}
                    
                    if task not in stats['models'][model]['tasks']:
                        stats['models'][model]['tasks'][task] = {'size': 0, 'count': 0}
                    
                    stats['models'][model]['tasks'][task]['size'] += blob.size
                    stats['models'][model]['total_size'] += blob.size
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get bucket stats: {e}")
            return {}
    
    async def cleanup_old_jobs(self, days: int = 30) -> Dict[str, int]:
        """Clean up jobs older than specified days from flat directory"""
        if not self.storage.available:
            return {'deleted': 0, 'errors': 0}
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = 0
            errors = 0
            
            # Only clean from jobs/ directory, keep archive intact
            blobs = self.storage.bucket.list_blobs(prefix="jobs/")
            
            for blob in blobs:
                if blob.time_created and blob.time_created < cutoff_date:
                    try:
                        blob.delete()
                        deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {blob.name}: {e}")
                        errors += 1
            
            logger.info(f"🗑️ Cleaned up {deleted} old files from jobs directory")
            return {'deleted': deleted, 'errors': errors}
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return {'deleted': 0, 'errors': 0}

# Global instance
gcp_bucket_browser = GCPBucketBrowser()