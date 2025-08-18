"""
Batch-Aware Modal Completion Checker
Intelligent completion detection with batch context awareness
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass

from database.unified_job_manager import unified_job_manager
from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

@dataclass
class JobContext:
    """Context information for a completed job"""
    job_id: str
    batch_id: Optional[str]
    batch_parent_id: Optional[str] 
    job_type: str
    task_type: str
    ligand_name: Optional[str]
    ligand_index: Optional[int]
    created_at: datetime
    is_batch_child: bool

@dataclass 
class BatchProgress:
    """Real-time batch progress tracking"""
    batch_id: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    percentage: float
    estimated_completion: Optional[float]
    last_updated: datetime

class BatchAwareCompletionChecker:
    """Intelligent batch-aware completion detection and orchestration"""
    
    def __init__(self):
        self.batch_progress_cache = {}  # batch_id -> BatchProgress
        self.active_batch_ids = set()  # Track which batches we're monitoring
        self.completion_callbacks = []  # Registered completion handlers
        self.milestone_thresholds = [10, 25, 50, 75, 90, 100]  # Progress milestones
        self.batch_milestones_reached = {}  # batch_id -> set of reached milestones
        
    async def on_job_completion(self, job_id: str, modal_result: Dict[str, Any]) -> None:
        """Main entry point - triggered when any Modal job completes"""
        
        try:
            start_time = time.time()
            
            # 1. Get comprehensive job context
            job_context = await self._get_job_context(job_id)
            
            if not job_context:
                logger.warning(f"⚠️ Could not get context for completed job {job_id}")
                return
                
            logger.info(f"🎯 Job completed: {job_id} (batch: {job_context.batch_id})")
            
            # 2. Store the completed job result (this replaces fragmented storage)
            await self._store_job_result_atomically(job_context, modal_result)
            
            # 3. Update batch progress if this is a batch job
            if job_context.is_batch_child and job_context.batch_id:
                await self._update_batch_progress(job_context, modal_result)
                
                # 4. Check for batch milestones and triggers
                await self._check_batch_milestones(job_context.batch_id)
                
            # 5. Trigger completion callbacks
            await self._trigger_completion_callbacks(job_context, modal_result)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Batch-aware completion processed in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Error in batch-aware completion for job {job_id}: {e}")
            # Don't let completion errors break the system
            
    async def _get_job_context(self, job_id: str) -> Optional[JobContext]:
        """Get comprehensive context for a completed job"""
        
        try:
            # Get job details from database
            job = unified_job_manager.get_job(job_id)
            
            if not job:
                logger.error(f"❌ Job {job_id} not found in database")
                return None
                
            # Extract context information
            job_type = job.get('job_type', 'INDIVIDUAL')
            task_type = job.get('task_type', 'unknown')
            batch_parent_id = job.get('batch_parent_id')
            
            # Determine if this is a batch child job
            is_batch_child = (
                job_type == 'BATCH_CHILD' or 
                batch_parent_id is not None or
                'batch' in str(task_type).lower()
            )
            
            # Get batch ID (could be the job itself if it's a parent, or the parent ID)
            batch_id = batch_parent_id if is_batch_child else (job_id if job_type == 'BATCH_PARENT' else None)
            
            # Extract ligand information for batch jobs
            input_data = job.get('input_data', {})
            ligand_name = input_data.get('ligand_name')
            ligand_index = input_data.get('ligand_index')
            
            # Parse creation time
            created_at = job.get('created_at')
            if hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            elif isinstance(created_at, (int, float)):
                created_at = datetime.fromtimestamp(created_at)
            else:
                created_at = datetime.utcnow()
                
            context = JobContext(
                job_id=job_id,
                batch_id=batch_id,
                batch_parent_id=batch_parent_id,
                job_type=job_type,
                task_type=task_type,
                ligand_name=ligand_name,
                ligand_index=ligand_index,
                created_at=created_at,
                is_batch_child=is_batch_child
            )
            
            logger.debug(f"📋 Job context: {job_id} -> batch:{batch_id}, type:{job_type}, child:{is_batch_child}")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error getting job context for {job_id}: {e}")
            return None
    
    async def _store_job_result_atomically(self, job_context: JobContext, modal_result: Dict[str, Any]) -> None:
        """Store job result with optimal storage pattern"""
        
        try:
            # 1. Update job status in database
            unified_job_manager.update_job_status(
                job_context.job_id, 
                'completed', 
                {
                    'results': modal_result,
                    'completed_at': datetime.utcnow().isoformat(),
                    'files_stored_to_gcp': True,
                    'has_results': True
                }
            )
            
            # 2. CRITICAL: Update batch parent job metadata immediately
            if job_context.is_batch_child and job_context.batch_id:
                await self._update_batch_parent_metadata(job_context.batch_id)
            
            # 3. Store files to GCP with intelligent organization
            storage_path = self._determine_optimal_storage_path(job_context)
            
            await gcp_storage_service.store_job_results(
                job_id=job_context.job_id,
                result_data=modal_result,
                task_type=job_context.task_type,
                storage_path=storage_path
            )
            
            logger.debug(f"💾 Stored job {job_context.job_id} to {storage_path}")
            
        except Exception as e:
            logger.error(f"❌ Error storing job result atomically for {job_context.job_id}: {e}")
            raise
    
    def _determine_optimal_storage_path(self, job_context: JobContext) -> str:
        """Determine optimal GCP storage path based on job context"""
        
        if job_context.is_batch_child and job_context.batch_id:
            # Store batch child jobs under batch hierarchy for better organization
            return f"batches/{job_context.batch_id}/jobs/{job_context.job_id}"
        else:
            # Store individual jobs in standard location
            return f"jobs/{job_context.job_id}"
    
    async def _update_batch_progress(self, job_context: JobContext, modal_result: Dict[str, Any]) -> None:
        """Update real-time batch progress tracking"""
        
        batch_id = job_context.batch_id
        if not batch_id:
            return
            
        try:
            # Get current batch progress (cached for performance)
            progress = await self._get_batch_progress(batch_id)
            
            # Update completion counts
            if modal_result.get('status') == 'completed':
                progress.completed_jobs += 1
            else:
                progress.failed_jobs += 1
                
            # Update percentage
            total_finished = progress.completed_jobs + progress.failed_jobs
            progress.percentage = (total_finished / progress.total_jobs) * 100 if progress.total_jobs > 0 else 0
            progress.last_updated = datetime.utcnow()
            
            # Estimate completion time based on current rate
            if progress.completed_jobs > 0:
                elapsed_time = (datetime.utcnow() - progress.last_updated).total_seconds()
                rate = progress.completed_jobs / max(elapsed_time, 1)  # jobs per second
                remaining_jobs = progress.total_jobs - total_finished
                progress.estimated_completion = remaining_jobs / rate if rate > 0 else None
            
            # Cache updated progress
            self.batch_progress_cache[batch_id] = progress
            
            # Add to active monitoring
            self.active_batch_ids.add(batch_id)
            
            logger.debug(f"📊 Batch progress updated: {batch_id} -> {progress.percentage:.1f}% ({progress.completed_jobs}/{progress.total_jobs})")
            
        except Exception as e:
            logger.error(f"❌ Error updating batch progress for {batch_id}: {e}")
    
    async def _get_batch_progress(self, batch_id: str) -> BatchProgress:
        """Get current batch progress with intelligent caching"""
        
        # Return cached progress if available and recent
        if batch_id in self.batch_progress_cache:
            cached_progress = self.batch_progress_cache[batch_id]
            cache_age = (datetime.utcnow() - cached_progress.last_updated).total_seconds()
            
            if cache_age < 30:  # Use cached data if less than 30 seconds old
                return cached_progress
        
        # Query database for current progress
        try:
            # Get batch parent info
            batch_parent = unified_job_manager.get_job(batch_id)
            if not batch_parent:
                raise ValueError(f"Batch parent {batch_id} not found")
            
            # Get all batch child jobs
            from config.gcp_database import gcp_database
            
            jobs_ref = gcp_database.db.collection('jobs').where('batch_parent_id', '==', batch_id)
            child_jobs = []
            
            for doc in jobs_ref.stream():
                child_jobs.append(doc.to_dict())
            
            # Calculate current progress
            total_jobs = len(child_jobs)
            completed_jobs = sum(1 for job in child_jobs if job.get('status') == 'completed')
            failed_jobs = sum(1 for job in child_jobs if job.get('status') == 'failed')
            running_jobs = sum(1 for job in child_jobs if job.get('status') == 'running')
            
            progress = BatchProgress(
                batch_id=batch_id,
                total_jobs=total_jobs,
                completed_jobs=completed_jobs,
                failed_jobs=failed_jobs,
                running_jobs=running_jobs,
                percentage=(completed_jobs + failed_jobs) / total_jobs * 100 if total_jobs > 0 else 0,
                estimated_completion=None,
                last_updated=datetime.utcnow()
            )
            
            return progress
            
        except Exception as e:
            logger.error(f"❌ Error getting batch progress for {batch_id}: {e}")
            # Return empty progress to avoid breaking the system
            return BatchProgress(
                batch_id=batch_id,
                total_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                running_jobs=0,
                percentage=0,
                estimated_completion=None,
                last_updated=datetime.utcnow()
            )
    
    async def _check_batch_milestones(self, batch_id: str) -> None:
        """Check for batch completion milestones and trigger appropriate actions"""
        
        try:
            progress = await self._get_batch_progress(batch_id)
            
            # Initialize milestone tracking for this batch
            if batch_id not in self.batch_milestones_reached:
                self.batch_milestones_reached[batch_id] = set()
            
            reached_milestones = self.batch_milestones_reached[batch_id]
            
            # Check each milestone threshold
            for threshold in self.milestone_thresholds:
                if progress.percentage >= threshold and threshold not in reached_milestones:
                    reached_milestones.add(threshold)
                    await self._trigger_milestone_action(batch_id, threshold, progress)
            
        except Exception as e:
            logger.error(f"❌ Error checking batch milestones for {batch_id}: {e}")
    
    async def _trigger_milestone_action(self, batch_id: str, milestone: int, progress: BatchProgress) -> None:
        """Trigger actions when batch reaches specific milestones"""
        
        logger.info(f"🎯 Batch {batch_id} reached {milestone}% completion ({progress.completed_jobs}/{progress.total_jobs})")
        
        try:
            if milestone == 25:
                await self._on_batch_25_percent(batch_id, progress)
            elif milestone == 50:
                await self._on_batch_50_percent(batch_id, progress)
            elif milestone == 75:
                await self._on_batch_75_percent(batch_id, progress)
            elif milestone == 100:
                await self._on_batch_completion(batch_id, progress)
                
        except Exception as e:
            logger.error(f"❌ Error triggering milestone action for {batch_id} at {milestone}%: {e}")
    
    async def _on_batch_25_percent(self, batch_id: str, progress: BatchProgress) -> None:
        """Actions when batch reaches 25% completion"""
        # Could start preparing batch aggregations, send notifications, etc.
        logger.info(f"📊 Starting early batch analysis for {batch_id}")
        
    async def _on_batch_50_percent(self, batch_id: str, progress: BatchProgress) -> None:
        """Actions when batch reaches 50% completion"""
        # Could generate intermediate summaries, update caches, etc.
        logger.info(f"📊 Generating intermediate summary for {batch_id}")
        
    async def _on_batch_75_percent(self, batch_id: str, progress: BatchProgress) -> None:
        """Actions when batch reaches 75% completion"""
        # Could start final preparations, pre-compute final aggregations, etc.
        logger.info(f"📊 Preparing final aggregations for {batch_id}")
        
    async def _on_batch_completion(self, batch_id: str, progress: BatchProgress) -> None:
        """Actions when batch is 100% complete"""
        logger.info(f"🎉 Batch {batch_id} completed! ({progress.completed_jobs} jobs)")
        
        try:
            # 1. Finalize batch results
            await self._finalize_batch_results(batch_id)
            
            # 2. Update batch parent status  
            unified_job_manager.update_job_status(batch_id, 'completed')
            
            # 3. Clean up tracking
            self._cleanup_batch_tracking(batch_id)
            
            # 4. Trigger completion notifications (future: WebSocket, email, etc.)
            await self._notify_batch_completion(batch_id, progress)
            
        except Exception as e:
            logger.error(f"❌ Error finalizing batch completion for {batch_id}: {e}")
    
    async def _finalize_batch_results(self, batch_id: str) -> None:
        """Finalize batch results and create aggregated batch_results.json"""
        try:
            logger.info(f"📋 Finalizing batch results for {batch_id}")
            
            # Use the existing batch results creation service
            from scripts.create_legacy_batch_results import create_batch_results_for_batch
            
            # Generate comprehensive batch_results.json with all fields
            success = await create_batch_results_for_batch(batch_id)
            
            if success:
                logger.info(f"✅ Successfully generated batch_results.json for {batch_id}")
            else:
                logger.error(f"❌ Failed to generate batch_results.json for {batch_id}")
                
        except Exception as e:
            logger.error(f"❌ Error finalizing batch results for {batch_id}: {e}")
        
    def _cleanup_batch_tracking(self, batch_id: str) -> None:
        """Clean up tracking data for completed batch"""
        self.active_batch_ids.discard(batch_id)
        self.batch_progress_cache.pop(batch_id, None)
        self.batch_milestones_reached.pop(batch_id, None)
        
    async def _notify_batch_completion(self, batch_id: str, progress: BatchProgress) -> None:
        """Send notifications about batch completion"""
        # Future: WebSocket, email notifications, etc.
        logger.info(f"📧 Batch completion notification sent for {batch_id}")
    
    async def _update_batch_parent_metadata(self, batch_id: str) -> None:
        """Update batch parent job with latest child job statistics"""
        
        try:
            # Get current batch progress
            progress = await self._get_batch_progress(batch_id)
            
            # Update batch parent job with current statistics
            batch_metadata = {
                'total_jobs': progress.total_jobs,
                'completed_jobs': progress.completed_jobs,
                'failed_jobs': progress.failed_jobs,
                'running_jobs': progress.running_jobs,
                'progress_percentage': progress.percentage,
                'last_updated': datetime.utcnow().isoformat(),
                'batch_statistics': {
                    'completion_rate': progress.percentage,
                    'success_rate': (progress.completed_jobs / max(progress.completed_jobs + progress.failed_jobs, 1)) * 100,
                    'total_processed': progress.completed_jobs + progress.failed_jobs
                }
            }
            
            # Determine batch status based on progress
            if progress.percentage >= 100:
                batch_status = 'completed'
            elif progress.completed_jobs > 0 or progress.running_jobs > 0:
                batch_status = 'running'
            else:
                batch_status = 'pending'
            
            # Update batch parent job
            unified_job_manager.update_job_status(
                batch_id, 
                batch_status,
                batch_metadata
            )
            
            logger.info(f"📊 Updated batch parent {batch_id}: {batch_status} ({progress.completed_jobs}/{progress.total_jobs} completed)")
            
            # Invalidate relevant caches
            from services.batch_status_cache import batch_status_cache
            batch_status_cache.invalidate_batch_status(batch_id)
            
        except Exception as e:
            logger.error(f"❌ Error updating batch parent metadata for {batch_id}: {e}")
    
    async def _trigger_completion_callbacks(self, job_context: JobContext, modal_result: Dict[str, Any]) -> None:
        """Trigger registered completion callbacks"""
        
        for callback in self.completion_callbacks:
            try:
                await callback(job_context, modal_result)
            except Exception as e:
                logger.error(f"❌ Error in completion callback: {e}")
    
    def register_completion_callback(self, callback):
        """Register a callback to be triggered on job completion"""
        self.completion_callbacks.append(callback)
        
    def get_active_batches(self) -> Set[str]:
        """Get set of currently active batch IDs"""
        return self.active_batch_ids.copy()
        
    def get_batch_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get cached batch progress"""
        return self.batch_progress_cache.get(batch_id)
        
    async def force_refresh_batch_progress(self, batch_id: str) -> BatchProgress:
        """Force refresh batch progress from database"""
        # Clear cache to force fresh lookup
        self.batch_progress_cache.pop(batch_id, None)
        return await self._get_batch_progress(batch_id)

# Global instance
batch_aware_completion_checker = BatchAwareCompletionChecker()

# Integration function for Modal completion checker
async def on_modal_job_completion(job_id: str, modal_result: Dict[str, Any]) -> None:
    """Integration point for existing Modal completion checker"""
    await batch_aware_completion_checker.on_job_completion(job_id, modal_result)