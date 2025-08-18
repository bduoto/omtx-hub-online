"""
GCP Storage Configuration - PRIMARY STORAGE
Complete replacement for Supabase storage
Handles all job file operations
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from google.cloud import storage
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class GCPStorageManager:
    """Manages GCP bucket operations for job files"""
    
    def __init__(self):
        self.client = None
        self.bucket = None
        self.bucket_name = os.getenv('GCP_BUCKET_NAME', 'hub-job-files')
        self.available = False
        
        # Initialize if credentials are available
        self._initialize()
    
    def _initialize(self):
        """Initialize GCP client and bucket"""
        try:
            # Option 1: Service account JSON from environment variable
            gcp_creds_json = os.getenv('GCP_CREDENTIALS_JSON')
            if gcp_creds_json:
                creds_dict = json.loads(gcp_creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                self.client = storage.Client(credentials=credentials)
            else:
                # Option 2: Default credentials (for local development or GCP environment)
                self.client = storage.Client()
            
            # Get or create bucket
            try:
                self.bucket = self.client.bucket(self.bucket_name)
                if not self.bucket.exists():
                    self.bucket = self.client.create_bucket(self.bucket_name, location="us-central1")
                    logger.info(f"✅ Created GCP bucket: {self.bucket_name}")
                else:
                    logger.info(f"✅ Connected to GCP bucket: {self.bucket_name}")
                    
                self.available = True
                
            except Exception as e:
                logger.error(f"❌ Failed to access/create bucket: {e}")
                self.available = False
                
        except Exception as e:
            logger.warning(f"⚠️ GCP Storage not configured: {e}")
            logger.info("GCP Storage unavailable - storage operations will fail")
            self.available = False
    
    def upload_file(self, file_path: str, content: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload file to GCP bucket"""
        if not self.available:
            return False
            
        try:
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(content, content_type=content_type)
            logger.info(f"✅ Uploaded to GCP: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ GCP upload failed: {e}")
            return False
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """Download file from GCP bucket"""
        if not self.available:
            return None
            
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                content = blob.download_as_bytes()
                logger.info(f"✅ Downloaded from GCP: {file_path}")
                return content
            else:
                logger.warning(f"⚠️ File not found in GCP: {file_path}")
                return None
        except Exception as e:
            logger.error(f"❌ GCP download failed: {e}")
            return None
    
    def list_job_files(self, job_id: str) -> List[Dict[str, Any]]:
        """List all files for a job"""
        if not self.available:
            return []
            
        try:
            prefix = f"jobs/{job_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            files = []
            for blob in blobs:
                files.append({
                    'name': blob.name.replace(prefix, ''),
                    'size': blob.size,
                    'created': blob.time_created.isoformat() if blob.time_created else None,
                    'content_type': blob.content_type,
                    'path': blob.name
                })
            
            logger.info(f"✅ Listed {len(files)} files for job {job_id}")
            return files
            
        except Exception as e:
            logger.error(f"❌ Failed to list GCP files: {e}")
            return []
    
    def get_public_url(self, file_path: str, expiry_hours: int = 24) -> Optional[str]:
        """Generate signed URL for direct download"""
        if not self.available:
            return None
            
        try:
            blob = self.bucket.blob(file_path)
            if blob.exists():
                from datetime import timedelta
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(hours=expiry_hours),
                    method="GET"
                )
                return url
            return None
        except Exception as e:
            logger.error(f"❌ Failed to generate signed URL: {e}")
            return None

# Global instance
gcp_storage = GCPStorageManager()