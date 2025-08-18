"""
Post-Processing Integration Service
Integrates Boltz-2 post-processing into existing OMTX-Hub pipeline.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.boltz_post_processor import post_processor
from services.gcp_storage_service import gcp_storage_service
from database.unified_job_manager import unified_job_manager
try:
    from services.redis_cache_service import get_redis_client
except ImportError:
    def get_redis_client():
        return None

logger = logging.getLogger(__name__)

class PostProcessingIntegration:
    """
    Integrates post-processing into the existing OMTX-Hub pipeline.
    
    Features:
    - Automatic trigger when jobs complete
    - Batch-level processing when all jobs finish
    - Performance monitoring and caching
    - Graceful fallback when dependencies unavailable
    """
    
    def __init__(self, job_manager=None, storage_service=None):
        self.job_manager = job_manager or unified_job_manager
        self.storage_service = storage_service or gcp_storage_service
        self.redis_client = get_redis_client()
        self._processing_cache = {}
    
    async def process_completed_job(self, job_id: str) -> bool:
        """
        Process a single completed job.
        Called automatically when a job transitions to 'completed' status.
        """
        try:
            # Check if already processed
            if await self._is_job_processed(job_id):
                logger.debug(f"Job {job_id} already post-processed")
                return True
            
            # Get job data
            job_data = await self.job_manager.get_job(job_id)
            if not job_data:
                logger.error(f"Job {job_id} not found for post-processing")
                return False
            
            # Ensure structure file is available
            structure_path = await self._ensure_structure_file(job_data)
            if not structure_path:
                logger.warning(f"No structure file available for job {job_id}")
                return False
            
            # Update job data with structure path
            job_data["structure_file"] = structure_path
            
            # Process the job
            results = await post_processor.process_job_async(job_data)
            
            # Store results in database
            success = await self._store_job_results(job_id, results)
            
            # Cache processing status
            await self._cache_processing_status(job_id, success)
            
            # Check if batch is complete and trigger batch processing
            if success:
                await self._check_and_process_batch(job_data.get("batch_parent_id"))
            
            logger.info(f"Post-processed job {job_id}: success={success}")
            return success
            
        except Exception as e:
            logger.error(f"Error post-processing job {job_id}: {e}")
            return False
    
    async def process_batch(self, batch_id: str, force: bool = False) -> bool:
        """
        Process entire batch for clustering and aggregation.
        Called automatically when all jobs in batch complete.
        """
        try:
            # Check if already processed
            if not force and await self._is_batch_processed(batch_id):
                logger.debug(f"Batch {batch_id} already post-processed")
                return True
            
            # Get all completed jobs in batch
            batch_jobs = await self.job_manager.get_batch_jobs(batch_id)
            completed_jobs = [job for job in batch_jobs if job.get("status") == "completed"]
            
            if not completed_jobs:
                logger.warning(f"No completed jobs found for batch {batch_id}")
                return False
            
            # Ensure all jobs have structure files
            jobs_with_structures = []
            for job in completed_jobs:
                structure_path = await self._ensure_structure_file(job)
                if structure_path:
                    job["structure_file"] = structure_path
                    jobs_with_structures.append(job)
            
            if not jobs_with_structures:
                logger.warning(f"No jobs with structure files for batch {batch_id}")
                return False
            
            # Process batch
            batch_analysis = await post_processor.process_batch_async(jobs_with_structures, batch_id)
            
            # Store batch results
            success = await self._store_batch_results(batch_id, batch_analysis)
            
            # Update individual job cluster assignments
            if success and batch_analysis.cluster_summary.get("cluster_assignments"):
                await self._update_job_clusters(jobs_with_structures, batch_analysis)
            
            # Cache batch processing status
            await self._cache_batch_status(batch_id, success)
            
            # Invalidate related caches
            await self._invalidate_batch_caches(batch_id)
            
            logger.info(f"Post-processed batch {batch_id}: {batch_analysis.processed_jobs}/{batch_analysis.total_jobs} jobs")
            return success
            
        except Exception as e:
            logger.error(f"Error post-processing batch {batch_id}: {e}")
            return False
    
    async def get_batch_analysis(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve batch analysis results with caching.
        """
        try:
            # Check cache first
            cache_key = f"batch_analysis:{batch_id}"
            if self.redis_client:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return cached
            
            # Get from database
            from database.post_processing_schema import FirestorePostProcessingService
            firestore_service = FirestorePostProcessingService(self.job_manager.db)
            batch_analysis = await firestore_service.get_batch_analysis(batch_id)
            
            if batch_analysis:
                result = {
                    "hotspot_residues": batch_analysis.hotspot_residues,
                    "binding_modes": batch_analysis.binding_mode_counts,
                    "scaffold_diversity": batch_analysis.scaffold_diversity,
                    "cluster_summary": batch_analysis.cluster_summary,
                    "processing_stats": {
                        "total_jobs": batch_analysis.total_jobs,
                        "processed_jobs": batch_analysis.processed_jobs,
                        "success_rate": batch_analysis.processed_jobs / max(batch_analysis.total_jobs, 1)
                    }
                }
                
                # Cache for 1 hour
                if self.redis_client:
                    await self.redis_client.setex(cache_key, 3600, result)
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving batch analysis for {batch_id}: {e}")
            return None
    
    async def _ensure_structure_file(self, job_data: Dict) -> Optional[str]:
        """
        Ensure structure file is available locally.
        Downloads from GCP if needed.
        """
        try:
            # Check if structure file path exists locally
            existing_path = job_data.get("structure_file")
            if existing_path and self._file_exists(existing_path):
                return existing_path
            
            # Try to get from output_data
            output_data = job_data.get("output_data", {})
            structure_content = output_data.get("structure_file_content")
            
            if structure_content:
                # Save structure content to local file
                job_id = job_data.get("job_id", job_data.get("id"))
                local_path = f"/tmp/structures/{job_id}.cif"
                
                # Ensure directory exists
                import os
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Decode and save
                import base64
                if isinstance(structure_content, str):
                    try:
                        decoded = base64.b64decode(structure_content)
                        with open(local_path, 'wb') as f:
                            f.write(decoded)
                        return local_path
                    except Exception:
                        # Maybe it's already text
                        with open(local_path, 'w') as f:
                            f.write(structure_content)
                        return local_path
            
            # Try to download from GCP storage
            job_id = job_data.get("job_id", job_data.get("id"))
            if job_id:
                gcp_path = f"jobs/{job_id}/structure.cif"
                local_path = f"/tmp/structures/{job_id}.cif"
                
                try:
                    success = await self.storage_service.download_file(gcp_path, local_path)
                    if success:
                        return local_path
                except Exception as e:
                    logger.debug(f"Could not download structure from GCP for job {job_id}: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error ensuring structure file for job: {e}")
            return None
    
    def _file_exists(self, path: str) -> bool:
        """Check if file exists"""
        try:
            from pathlib import Path
            return Path(path).exists()
        except Exception:
            return False
    
    async def _is_job_processed(self, job_id: str) -> bool:
        """Check if job has been post-processed"""
        try:
            job_data = await self.job_manager.get_job(job_id)
            return job_data and job_data.get("post_processing_success", False)
        except Exception:
            return False
    
    async def _is_batch_processed(self, batch_id: str) -> bool:
        """Check if batch has been post-processed"""
        try:
            analysis = await self.get_batch_analysis(batch_id)
            return analysis is not None
        except Exception:
            return False
    
    async def _store_job_results(self, job_id: str, results: Dict[str, Any]) -> bool:
        """Store job post-processing results"""
        try:
            from database.post_processing_schema import FirestorePostProcessingService
            firestore_service = FirestorePostProcessingService(self.job_manager.db)
            return await firestore_service.store_job_post_processing(job_id, results)
        except Exception as e:
            logger.error(f"Error storing job results for {job_id}: {e}")
            return False
    
    async def _store_batch_results(self, batch_id: str, analysis) -> bool:
        """Store batch analysis results"""
        try:
            from database.post_processing_schema import FirestorePostProcessingService
            firestore_service = FirestorePostProcessingService(self.job_manager.db)
            
            results_dict = {
                "hotspot_residues": analysis.hotspot_residues,
                "binding_modes": analysis.binding_modes,
                "scaffold_diversity": analysis.scaffold_diversity,
                "cluster_summary": analysis.cluster_summary,
                "total_jobs": analysis.total_jobs,
                "processed_jobs": analysis.processed_jobs
            }
            
            return await firestore_service.store_batch_analysis(batch_id, results_dict)
        except Exception as e:
            logger.error(f"Error storing batch results for {batch_id}: {e}")
            return False
    
    async def _update_job_clusters(self, jobs: List[Dict], batch_analysis) -> bool:
        """Update individual jobs with cluster assignments"""
        try:
            # This would update cluster_id and cluster_label for each job
            # Implementation depends on how cluster assignments are stored
            # For now, we'll skip this as it requires cluster assignment tracking
            return True
        except Exception as e:
            logger.error(f"Error updating job clusters: {e}")
            return False
    
    async def _check_and_process_batch(self, batch_id: Optional[str]) -> None:
        """Check if batch is complete and trigger batch processing"""
        if not batch_id:
            return
        
        try:
            # Get batch status
            batch_jobs = await self.job_manager.get_batch_jobs(batch_id)
            completed_jobs = [job for job in batch_jobs if job.get("status") == "completed"]
            
            # If all jobs are complete, process batch
            if len(completed_jobs) == len(batch_jobs):
                await self.process_batch(batch_id)
                
        except Exception as e:
            logger.error(f"Error checking batch completion for {batch_id}: {e}")
    
    async def _cache_processing_status(self, job_id: str, success: bool) -> None:
        """Cache job processing status"""
        try:
            if self.redis_client:
                cache_key = f"job_processed:{job_id}"
                await self.redis_client.setex(cache_key, 3600, success)
        except Exception:
            pass
    
    async def _cache_batch_status(self, batch_id: str, success: bool) -> None:
        """Cache batch processing status"""
        try:
            if self.redis_client:
                cache_key = f"batch_processed:{batch_id}"
                await self.redis_client.setex(cache_key, 3600, success)
        except Exception:
            pass
    
    async def _invalidate_batch_caches(self, batch_id: str) -> None:
        """Invalidate caches related to batch results"""
        try:
            if self.redis_client:
                patterns = [
                    f"batch_results:{batch_id}:*",
                    f"enhanced_results:{batch_id}:*",
                    f"batch_analysis:{batch_id}"
                ]
                for pattern in patterns:
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
        except Exception:
            pass

# Global integration instance (initialized in main app)
integration_service: Optional[PostProcessingIntegration] = None

def initialize_integration(job_manager=None, storage_service=None):
    """Initialize global integration service"""
    global integration_service
    integration_service = PostProcessingIntegration(job_manager, storage_service)
    return integration_service

async def trigger_job_post_processing(job_id: str) -> bool:
    """
    Public API for triggering job post-processing.
    Call this when a job transitions to 'completed' status.
    """
    if integration_service:
        return await integration_service.process_completed_job(job_id)
    return False

async def trigger_batch_post_processing(batch_id: str) -> bool:
    """
    Public API for triggering batch post-processing.
    Call this manually or when all batch jobs complete.
    """
    if integration_service:
        return await integration_service.process_batch(batch_id)
    return False

async def get_enhanced_batch_analysis(batch_id: str) -> Optional[Dict[str, Any]]:
    """
    Public API for retrieving enhanced batch analysis.
    Returns post-processed scientific metrics.
    """
    if integration_service:
        return await integration_service.get_batch_analysis(batch_id)
    return None