"""
Post-Processing Hooks for Boltz-2 Pipeline Integration
Automatically triggers scientific analysis when jobs complete.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.post_processing_integration import (
    trigger_job_post_processing,
    trigger_batch_post_processing,
    integration_service
)

logger = logging.getLogger(__name__)

class PostProcessingHooks:
    """
    Hooks into existing OMTX-Hub pipeline to trigger post-processing.
    
    Call these functions when jobs change status or batches complete.
    """
    
    @staticmethod
    async def on_job_completed(job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Hook called when a job transitions to 'completed' status.
        
        Args:
            job_id: The completed job ID
            job_data: Complete job data including results
            
        Returns:
            bool: True if post-processing was triggered successfully
        """
        try:
            logger.info(f"🧬 Triggering post-processing for completed job {job_id}")
            
            # Trigger individual job post-processing
            success = await trigger_job_post_processing(job_id)
            
            if success:
                logger.info(f"✅ Post-processing completed for job {job_id}")
            else:
                logger.warning(f"⚠️ Post-processing failed for job {job_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in post-processing hook for job {job_id}: {e}")
            return False
    
    @staticmethod
    async def on_batch_completed(batch_id: str, batch_data: Dict[str, Any]) -> bool:
        """
        Hook called when all jobs in a batch are completed.
        
        Args:
            batch_id: The completed batch ID
            batch_data: Batch metadata and job summary
            
        Returns:
            bool: True if batch post-processing was triggered successfully
        """
        try:
            logger.info(f"🧪 Triggering batch post-processing for {batch_id}")
            
            # Trigger batch-level clustering and analysis
            success = await trigger_batch_post_processing(batch_id)
            
            if success:
                logger.info(f"✅ Batch post-processing completed for {batch_id}")
            else:
                logger.warning(f"⚠️ Batch post-processing failed for {batch_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in batch post-processing hook for {batch_id}: {e}")
            return False
    
    @staticmethod
    async def on_job_status_change(job_id: str, old_status: str, new_status: str, job_data: Dict[str, Any]) -> None:
        """
        Hook called whenever a job status changes.
        Automatically triggers post-processing when status becomes 'completed'.
        
        Args:
            job_id: Job identifier
            old_status: Previous status
            new_status: New status
            job_data: Complete job data
        """
        try:
            # Only trigger post-processing on completion
            if new_status == 'completed' and old_status != 'completed':
                await PostProcessingHooks.on_job_completed(job_id, job_data)
                
                # Check if this completes a batch
                batch_id = job_data.get('batch_parent_id')
                if batch_id:
                    await PostProcessingHooks._check_batch_completion(batch_id)
            
        except Exception as e:
            logger.error(f"❌ Error in status change hook for job {job_id}: {e}")
    
    @staticmethod
    async def _check_batch_completion(batch_id: str) -> None:
        """
        Check if a batch is complete and trigger batch post-processing.
        """
        try:
            if not integration_service:
                return
            
            # Get batch jobs to check completion
            from ..database.unified_job_manager import unified_job_manager
            batch_jobs = await unified_job_manager.get_batch_jobs(batch_id)
            
            if not batch_jobs:
                return
            
            # Count completed vs total jobs
            completed_jobs = [job for job in batch_jobs if job.get("status") == "completed"]
            total_jobs = len(batch_jobs)
            
            # If all jobs are complete, trigger batch processing
            if len(completed_jobs) == total_jobs and total_jobs > 0:
                logger.info(f"🎯 Batch {batch_id} is complete ({completed_jobs}/{total_jobs}), triggering batch analysis")
                await PostProcessingHooks.on_batch_completed(batch_id, {"total_jobs": total_jobs})
            else:
                logger.debug(f"📊 Batch {batch_id} progress: {len(completed_jobs)}/{total_jobs} completed")
                
        except Exception as e:
            logger.error(f"❌ Error checking batch completion for {batch_id}: {e}")

# Integration functions to call from existing codebase
async def integrate_with_modal_monitor():
    """
    Integration point for modal_monitor.py
    Call this function when Modal jobs complete.
    """
    # This would be called from modal_monitor.py when updating job status
    pass

async def integrate_with_job_manager():
    """
    Integration point for unified_job_manager.py
    Call this when job status is updated.
    """
    # This would be called from unified_job_manager.py in update_job_status method
    pass

# Example integration in existing files:
INTEGRATION_EXAMPLES = """
# In modal_monitor.py - when job completes:
from hooks.post_processing_hooks import PostProcessingHooks

async def handle_completed_job(job_id: str, job_data: dict):
    # Update job status
    await unified_job_manager.update_job_status(job_id, "completed", job_data)
    
    # Trigger post-processing
    await PostProcessingHooks.on_job_completed(job_id, job_data)

# In unified_job_manager.py - when updating status:
from hooks.post_processing_hooks import PostProcessingHooks

async def update_job_status(self, job_id: str, status: str, **kwargs):
    old_status = await self.get_job_status(job_id)
    
    # Update status in database
    await self._update_job_status_impl(job_id, status, **kwargs)
    
    # Trigger hooks
    job_data = await self.get_job(job_id)
    await PostProcessingHooks.on_job_status_change(job_id, old_status, status, job_data)

# In unified_batch_processor.py - when batch completes:
from hooks.post_processing_hooks import PostProcessingHooks

async def finalize_batch(self, batch_id: str):
    # Complete batch processing
    await self._finalize_batch_impl(batch_id)
    
    # Trigger batch analysis
    batch_data = await self.get_batch_data(batch_id)
    await PostProcessingHooks.on_batch_completed(batch_id, batch_data)
"""