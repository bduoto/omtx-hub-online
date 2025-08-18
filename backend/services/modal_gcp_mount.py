#!/usr/bin/env python3
"""
Modal GCP CloudBucketMount Integration
Provides direct GCP bucket access from Modal functions for optimized batch storage
"""

import modal
import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ModalGCPMount:
    """
    Integration service for Modal CloudBucketMount with GCP Storage
    Enables direct file writing from Modal functions to GCP bucket
    """
    
    def __init__(self):
        self.bucket_name = os.getenv('GCP_BUCKET_NAME', 'hub-job-files')
        self.gcp_secret = None
        self._initialize_gcp_secret()
    
    def _initialize_gcp_secret(self):
        """Initialize GCP secret for Modal CloudBucketMount"""
        try:
            # GCP credentials for CloudBucketMount
            # These should be HMAC keys, not service account keys
            gcp_access_key = os.getenv('GOOGLE_ACCESS_KEY_ID')
            gcp_secret_key = os.getenv('GOOGLE_ACCESS_KEY_SECRET')
            
            if gcp_access_key and gcp_secret_key:
                self.gcp_secret = modal.Secret.from_dict({
                    "GOOGLE_ACCESS_KEY_ID": gcp_access_key,
                    "GOOGLE_ACCESS_KEY_SECRET": gcp_secret_key
                })
                logger.info("✅ GCP CloudBucketMount secret initialized")
            else:
                logger.warning("⚠️ GCP HMAC credentials not found - CloudBucketMount disabled")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize GCP secret: {e}")
    
    def get_cloud_bucket_mount(self, read_only: bool = False) -> Optional[modal.CloudBucketMount]:
        """
        Get configured CloudBucketMount for GCP bucket
        
        Args:
            read_only: Whether to mount bucket in read-only mode
            
        Returns:
            Configured CloudBucketMount or None if not available
        """
        if not self.gcp_secret:
            logger.warning("⚠️ No GCP secret available for CloudBucketMount")
            return None
        
        try:
            mount = modal.CloudBucketMount(
                bucket_name=self.bucket_name,
                bucket_endpoint_url="https://storage.googleapis.com",
                secret=self.gcp_secret,
                read_only=read_only
            )
            
            logger.info(f"✅ Created CloudBucketMount for {self.bucket_name} (read_only={read_only})")
            return mount
            
        except Exception as e:
            logger.error(f"❌ Failed to create CloudBucketMount: {e}")
            return None
    
    def get_batch_mount_config(self, batch_id: str) -> Dict[str, Any]:
        """
        Get mount configuration for batch processing
        Mounts bucket with specific prefix for the batch
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            Mount configuration for Modal function
        """
        if not self.gcp_secret:
            return {}
        
        try:
            # Mount the entire bucket but optimize for batch path
            mount = modal.CloudBucketMount(
                bucket_name=self.bucket_name,
                bucket_endpoint_url="https://storage.googleapis.com", 
                secret=self.gcp_secret,
                read_only=False  # Allow writing results
            )
            
            return {
                "/gcp-bucket": mount
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create batch mount config: {e}")
            return {}
    
    @staticmethod
    def write_batch_results_to_mount(
        mount_path: str,
        batch_id: str, 
        job_id: str,
        results: Dict[str, Any]
    ) -> bool:
        """
        Write batch results directly to mounted GCP bucket
        This function runs INSIDE Modal functions
        
        Args:
            mount_path: Path where bucket is mounted (e.g., "/gcp-bucket")
            batch_id: Batch identifier
            job_id: Job identifier  
            results: Results to store
            
        Returns:
            Success status
        """
        try:
            import tempfile
            import shutil
            
            # Create standardized batch paths
            batch_job_dir = f"{mount_path}/batches/{batch_id}/jobs/{job_id}"
            
            # Create directories if they don't exist
            # Note: CloudBucketMount requires parent directories to exist
            os.makedirs(batch_job_dir, exist_ok=True)
            
            # Write results.json
            results_path = f"{batch_job_dir}/results.json"
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                json.dump(results, temp_file, indent=2)
                temp_path = temp_file.name
            
            # Move to final location (CloudBucketMount compatible)
            shutil.move(temp_path, results_path)
            
            # Write structure file if present
            if results.get('structure_file_base64'):
                structure_path = f"{batch_job_dir}/structure.cif"
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                    temp_file.write(results['structure_file_base64'])
                    temp_path = temp_file.name
                
                shutil.move(temp_path, structure_path)
            
            # Write metadata
            metadata = {
                'job_id': job_id,
                'batch_id': batch_id,
                'stored_at': datetime.utcnow().isoformat(),
                'has_structure': bool(results.get('structure_file_base64')),
                'affinity': results.get('affinity'),
                'confidence': results.get('confidence')
            }
            
            metadata_path = f"{batch_job_dir}/metadata.json"
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                json.dump(metadata, temp_file, indent=2)
                temp_path = temp_file.name
            
            shutil.move(temp_path, metadata_path)
            
            logger.info(f"✅ Stored batch results to {batch_job_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write batch results to mount: {e}")
            return False
    
    @staticmethod 
    def write_archive_results_to_mount(
        mount_path: str,
        batch_id: str,
        job_id: str, 
        results: Dict[str, Any],
        ligand_name: str = "Unknown"
    ) -> bool:
        """
        Write results to archive location for backup
        This function runs INSIDE Modal functions
        
        Args:
            mount_path: Path where bucket is mounted
            batch_id: Batch identifier
            job_id: Job identifier
            results: Results to store
            ligand_name: Name of ligand for archive path
            
        Returns:
            Success status
        """
        try:
            import tempfile
            import shutil
            
            # Clean ligand name for filename
            clean_ligand = ''.join(c for c in ligand_name if c.isalnum() or c in '-_')
            archive_dir = f"{mount_path}/archive/Batches/{batch_id}/{clean_ligand}_{job_id}"
            
            # Create directories
            os.makedirs(archive_dir, exist_ok=True)
            
            # Write files using temp file approach for CloudBucketMount compatibility
            for filename, content in [
                ("results.json", json.dumps(results, indent=2)),
                ("structure.cif", results.get('structure_file_base64', ''))
            ]:
                if content:  # Only write if content exists
                    file_path = f"{archive_dir}/{filename}"
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                        temp_file.write(content)
                        temp_path = temp_file.name
                    
                    shutil.move(temp_path, file_path)
            
            logger.info(f"✅ Archived results to {archive_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write archive results: {e}")
            return False

# Global instance
modal_gcp_mount = ModalGCPMount()