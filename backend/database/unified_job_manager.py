"""
Unified Job Manager - Pure GCP Implementation
Provides a consistent interface for job operations using GCP Firestore + Cloud Storage
"""

import logging
from typing import Optional, Dict, Any, List, Union
from database.gcp_job_manager import gcp_job_manager

logger = logging.getLogger(__name__)

class UnifiedJobManager:
    """Unified interface for job management using pure GCP backend"""
    
    def __init__(self):
        # Use GCP as primary (and only) backend
        self.primary_backend = gcp_job_manager
        logger.info("🚀 Using GCP (Firestore + Cloud Storage) for job management")
    
    @property
    def available(self) -> bool:
        """Check if the job manager is available"""
        return self.primary_backend.available
    
    def create_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Create a new job"""
        return self.primary_backend.create_job(job_data)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        return self.primary_backend.get_job(job_id)
    
    def update_job_status(self, job_id: str, status: str, output_data: Dict[str, Any] = None) -> bool:
        """Update job status"""
        return self.primary_backend.update_job_status(job_id, status, output_data)
    
    def get_jobs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get jobs by status"""
        return self.primary_backend.get_jobs_by_status(status, limit)
    
    def get_recent_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent jobs"""
        return self.primary_backend.get_recent_jobs(limit)
    
    def upload_job_file(self, job_id: str, file_name: str, file_content: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload job file"""
        return self.primary_backend.upload_job_file(job_id, file_name, file_content, content_type)
    
    def get_job_files(self, job_id: str) -> List[Dict[str, Any]]:
        """Get files for a job"""
        return self.primary_backend.get_job_files(job_id)
    
    def download_job_file(self, job_id: str, file_name: str) -> Optional[bytes]:
        """Download job file"""
        return self.primary_backend.download_job_file(job_id, file_name)
    
    def get_file_download_url(self, job_id: str, file_name: str, expiry_hours: int = 24) -> Optional[str]:
        """Get file download URL"""
        return self.primary_backend.get_file_download_url(job_id, file_name, expiry_hours)
    
    def save_job_result(self, job_id: str, result_data: Dict[str, Any]) -> bool:
        """Save job result"""
        return self.primary_backend.save_job_result(job_id, result_data)
    
    def get_user_job_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user job results"""
        return self.primary_backend.get_user_job_results(limit)
    
    def add_gallery_item(self, gallery_data: Dict[str, Any]) -> Optional[str]:
        """Add gallery item"""
        return self.primary_backend.add_gallery_item(gallery_data)
    
    def get_gallery_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get gallery items"""
        return self.primary_backend.get_gallery_items(limit)
    
    def create_batch_job(self, batch_data: Dict[str, Any], individual_jobs: List[Dict[str, Any]]) -> Optional[str]:
        """Create a batch job with individual sub-jobs"""
        return self.primary_backend.create_batch_job(batch_data, individual_jobs)
    
    def get_batch_jobs(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all jobs in a batch"""
        return self.primary_backend.get_batch_jobs(batch_id)
    
    def update_batch_progress(self, batch_id: str) -> bool:
        """Update batch job progress"""
        return self.primary_backend.update_batch_progress(batch_id)
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        return self.primary_backend.get_job_stats()
    
    def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Clean up old jobs"""
        return self.primary_backend.cleanup_old_jobs(days_old)
    
    def get_user_batch_parents(self, user_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Get batch parent jobs for a user - CRITICAL for My Batches visibility"""
        try:
            from config.gcp_database import gcp_database
            from models.enhanced_job_model import JobType
            
            logger.info(f"🔍 Searching for batch parents for user {user_id}")
            
            # Query for all BATCH_PARENT jobs for this user
            batch_parent_query = (
                gcp_database.db.collection('jobs')
                .where('job_type', '==', JobType.BATCH_PARENT.value)
                .where('user_id', '==', user_id)
                .order_by('created_at', direction='DESCENDING')
                .limit(limit)
            )
            
            batch_parents = []
            for doc in batch_parent_query.stream():
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                batch_parents.append(job_data)
                
            logger.info(f"✅ Found {len(batch_parents)} batch parent jobs for user {user_id}")
            return batch_parents
            
        except Exception as e:
            logger.error(f"❌ Error getting batch parents: {e}")
            return []
    
    def get_user_jobs(self, user_id: str, limit: int = 5000) -> List[Dict[str, Any]]:
        """Get jobs for a specific user"""
        return self.primary_backend.get_user_jobs(user_id, limit)
    
    # Legacy async methods for backward compatibility
    async def create_job_async(self, job_data: Dict[str, Any]) -> str:
        """Async wrapper for create_job"""
        return self.create_job(job_data)
    
    async def get_job_async(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Async wrapper for get_job"""
        return self.get_job(job_id)
    
    async def get_all_jobs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all jobs with pagination"""
        jobs = self.get_recent_jobs(limit)
        # Apply offset if needed
        return jobs[offset:] if offset > 0 else jobs
    
    async def update_job_status_async(self, job_id: str, status: str, 
                                     result_data: Optional[Dict[str, Any]] = None) -> bool:
        """Async wrapper for update_job_status"""
        return self.update_job_status(job_id, status, result_data)
    
    async def update_job_results(self, job_id: str, results: Dict[str, Any], 
                                status: str) -> bool:
        """Update job results and status"""
        return self.update_job_status(job_id, status, results)
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job - not implemented for safety"""
        logger.warning(f"⚠️ Job deletion not implemented for safety: {job_id}")
        return False
    
    async def get_jobs_by_status_async(self, status: str) -> List[Dict[str, Any]]:
        """Async wrapper for get_jobs_by_status"""
        return self.get_jobs_by_status(status)
    
    async def get_job_count(self) -> int:
        """Get total job count"""
        try:
            stats = self.get_job_stats()
            return stats.get('total', 0)
        except Exception as e:
            logger.error(f"❌ Error getting job count: {e}")
            return 0
    
    async def get_recent_jobs_async(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Async wrapper for get_recent_jobs"""
        return self.get_recent_jobs(limit)
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        return {
            "gcp_database_available": self.primary_backend.db.available,
            "gcp_storage_available": self.primary_backend.storage.available,
            "available": self.available,
            "manager_type": "gcp_firestore_storage"
        }

# Global instance
unified_job_manager = UnifiedJobManager()