"""
GCP Job Manager - Complete Supabase Replacement
Handles all job operations using GCP Firestore + Cloud Storage
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
from google.cloud import firestore
from config.gcp_database import gcp_database
from config.gcp_storage import gcp_storage

logger = logging.getLogger(__name__)

class GCPJobManager:
    """Complete job management using GCP services - replaces Supabase entirely"""
    
    def __init__(self):
        self.db = gcp_database
        self.storage = gcp_storage
        
    @property
    def available(self) -> bool:
        """Check if both database and storage are available"""
        return self.db.available and self.storage.available
    
    def create_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Create a new job"""
        if not self.available:
            logger.error("❌ GCP services not available")
            return None
        
        # Ensure required fields
        job_data.setdefault('status', 'pending')
        job_data.setdefault('model_name', 'Unknown')
        
        return self.db.create_job(job_data)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        return self.db.get_job(job_id)
    
    def update_job_status(self, job_id: str, status: str, output_data: Dict[str, Any] = None) -> bool:
        """Update job status and optionally output data"""
        return self.db.update_job_status(job_id, status, output_data)
    
    def get_jobs_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get jobs by status"""
        return self.db.get_jobs_by_status(status, limit)
    
    def get_recent_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent jobs"""
        return self.db.get_recent_jobs(limit)
    
    def upload_job_file(self, job_id: str, file_name: str, file_content: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload job file to GCS and store metadata in Firestore"""
        if not self.available:
            return False
        
        try:
            # Upload to GCS
            file_path = f"jobs/{job_id}/{file_name}"
            storage_success = self.storage.upload_file(file_path, file_content, content_type)
            
            if storage_success:
                # Store metadata in Firestore
                return self.db.upload_job_file(job_id, file_name, file_content)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to upload job file: {e}")
            return False
    
    def get_job_files(self, job_id: str) -> List[Dict[str, Any]]:
        """Get files for a job"""
        return self.db.get_job_files(job_id)
    
    def download_job_file(self, job_id: str, file_name: str) -> Optional[bytes]:
        """Download job file from GCS"""
        if not self.storage.available:
            return None
        
        file_path = f"jobs/{job_id}/{file_name}"
        return self.storage.download_file(file_path)
    
    def get_file_download_url(self, job_id: str, file_name: str, expiry_hours: int = 24) -> Optional[str]:
        """Get signed URL for file download"""
        if not self.storage.available:
            return None
        
        file_path = f"jobs/{job_id}/{file_name}"
        return self.storage.get_public_url(file_path, expiry_hours)
    
    def save_job_result(self, job_id: str, result_data: Dict[str, Any]) -> bool:
        """Save job result to my_results collection"""
        return self.db.save_job_result(job_id, result_data)
    
    def get_user_job_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user job results"""
        return self.db.get_user_job_results(limit)
    
    def get_user_jobs(self, user_id: str = "current_user", limit: int = 50) -> List[Dict[str, Any]]:
        """Get jobs for a specific user"""
        if not self.available:
            return []
        
        try:
            query = (self.db.db.collection('jobs')
                    .where('user_id', '==', user_id)
                    .order_by('created_at', direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            logger.info(f"✅ Retrieved {len(jobs)} jobs for user {user_id}")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Failed to get jobs for user {user_id}: {e}")
            return []
    
    def add_gallery_item(self, gallery_data: Dict[str, Any]) -> Optional[str]:
        """Add item to gallery"""
        return self.db.add_gallery_item(gallery_data)
    
    def get_gallery_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get gallery items"""
        return self.db.get_gallery_items(limit)
    
    def create_batch_job(self, batch_data: Dict[str, Any], individual_jobs: List[Dict[str, Any]]) -> Optional[str]:
        """Create a batch job with individual sub-jobs"""
        if not self.available:
            return None
        
        try:
            # Create main batch job
            batch_data.update({
                'status': 'pending',
                'job_type': 'batch',
                'total_jobs': len(individual_jobs),
                'completed_jobs': 0
            })
            
            batch_id = self.db.create_job(batch_data)
            if not batch_id:
                return None
            
            # Create individual jobs
            created_jobs = []
            for i, job_data in enumerate(individual_jobs):
                job_data.update({
                    'batch_id': batch_id,
                    'batch_index': i,
                    'status': 'pending'
                })
                
                job_id = self.db.create_job(job_data)
                if job_id:
                    created_jobs.append(job_id)
            
            # Update batch with created job IDs
            self.db.update_job_status(batch_id, 'pending', {
                'individual_job_ids': created_jobs,
                'created_jobs': len(created_jobs)
            })
            
            logger.info(f"✅ Created batch job {batch_id} with {len(created_jobs)} individual jobs")
            return batch_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create batch job: {e}")
            return None
    
    def get_batch_jobs(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all jobs in a batch"""
        if not self.available:
            return []
        
        try:
            query = (self.db.db.collection('jobs')
                    .where('batch_id', '==', batch_id)
                    .order_by('batch_index'))
            
            docs = query.stream()
            jobs = []
            
            for doc in docs:
                job_data = doc.to_dict()
                job_data['id'] = doc.id
                jobs.append(job_data)
            
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch jobs for {batch_id}: {e}")
            return []
    
    def update_batch_progress(self, batch_id: str) -> bool:
        """Update batch job progress based on individual job completions"""
        if not self.available:
            return False
        
        try:
            batch_jobs = self.get_batch_jobs(batch_id)
            if not batch_jobs:
                return False
            
            completed_count = sum(1 for job in batch_jobs if job.get('status') == 'completed')
            total_count = len(batch_jobs)
            
            # Update batch job
            output_data = {
                'completed_jobs': completed_count,
                'total_jobs': total_count,
                'progress_percentage': (completed_count / total_count) * 100 if total_count > 0 else 0
            }
            
            # If all jobs completed, mark batch as completed
            status = 'completed' if completed_count == total_count else 'running'
            
            return self.db.update_job_status(batch_id, status, output_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to update batch progress for {batch_id}: {e}")
            return False
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        if not self.available:
            return {}
        
        try:
            stats = {}
            statuses = ['pending', 'running', 'completed', 'failed']
            
            for status in statuses:
                jobs = self.get_jobs_by_status(status, limit=1000)  # Get more for accurate count
                stats[status] = len(jobs)
            
            stats['total'] = sum(stats.values())
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get job stats: {e}")
            return {}
    
    def cleanup_old_jobs(self, days_old: int = 30) -> int:
        """Clean up jobs older than specified days"""
        if not self.available:
            return 0
        
        try:
            cutoff_date = datetime.now(timezone.utc).replace(day=datetime.now().day - days_old)
            
            # Query old jobs
            query = (self.db.db.collection('jobs')
                    .where('created_at', '<', cutoff_date)
                    .limit(100))  # Process in batches
            
            docs = query.stream()
            deleted_count = 0
            
            for doc in docs:
                # Delete associated files from GCS
                job_data = doc.to_dict()
                job_id = doc.id
                
                # Delete job files
                files = self.get_job_files(job_id)
                for file_info in files:
                    file_path = file_info.get('storage_path')
                    if file_path:
                        # Delete from GCS (you may want to implement this in gcp_storage.py)
                        pass
                
                # Delete job document
                doc.reference.delete()
                deleted_count += 1
            
            logger.info(f"✅ Cleaned up {deleted_count} old jobs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old jobs: {e}")
            return 0

# Global instance
gcp_job_manager = GCPJobManager()