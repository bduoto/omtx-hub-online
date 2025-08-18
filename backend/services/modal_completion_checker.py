"""
Modal Completion Checker Service

Background service that periodically checks for completed Modal jobs
and processes them through the batch storage pipeline.

This solves the issue where jobs complete asynchronously but aren't being
processed through the batch storage hierarchy.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from database.unified_job_manager import unified_job_manager
from services.modal_job_status_service import modal_job_status_service
from services.batch_relationship_manager import batch_relationship_manager

logger = logging.getLogger(__name__)

class ModalCompletionChecker:
    """
    Checks for completed Modal jobs and processes them through storage pipeline.
    
    Unlike the modal_monitor which processes pending jobs, this service
    specifically checks running jobs with Modal call IDs for completion.
    """
    
    def __init__(self):
        self.running = False
        self.check_interval = 15  # Check every 15 seconds
        self.last_check = None
        self.processed_count = 0
        self.error_count = 0
        
    async def start(self):
        """Start the completion checking loop"""
        self.running = True
        logger.info("🚀 Starting Modal completion checker service")
        
        while self.running:
            try:
                await self._check_for_completions()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"❌ Error in completion checker loop: {e}")
                self.error_count += 1
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the completion checking loop"""
        self.running = False
        logger.info("🛑 Stopping Modal completion checker service")
    
    async def _check_for_completions(self):
        """Check all running jobs with Modal call IDs for completion"""
        try:
            self.last_check = datetime.utcnow()
            
            # Get all running jobs
            running_jobs = unified_job_manager.get_jobs_by_status('running')
            
            if not running_jobs:
                logger.debug("No running jobs to check")
                return
            
            # Filter jobs with Modal call IDs
            modal_jobs = []
            for job in running_jobs:
                modal_call_id = self._extract_modal_call_id(job)
                if modal_call_id:
                    modal_jobs.append({
                        'id': job.get('id'),
                        'modal_call_id': modal_call_id,
                        'data': job
                    })
            
            if not modal_jobs:
                logger.debug("No running jobs with Modal call IDs")
                return
            
            logger.info(f"🔍 Checking {len(modal_jobs)} running Modal jobs for completion")
            
            # Check each job's status
            for modal_job in modal_jobs:
                await self._check_single_job(modal_job)
                
        except Exception as e:
            logger.error(f"❌ Error checking for completions: {e}")
    
    def _extract_modal_call_id(self, job: Dict[str, Any]) -> str:
        """Extract Modal call ID from various possible locations in job data"""
        # Check multiple possible locations
        locations = [
            job.get('modal_call_id'),
            job.get('results', {}).get('modal_call_id'),
            job.get('output_data', {}).get('modal_call_id'),
            job.get('result_data', {}).get('modal_call_id'),
        ]
        
        for location in locations:
            if location:
                return location
        
        return None
    
    async def _check_single_job(self, modal_job: Dict[str, Any]):
        """Check a single job for completion and process if complete"""
        try:
            job_id = modal_job['id']
            modal_call_id = modal_job['modal_call_id']
            
            logger.debug(f"Checking job {job_id} with Modal call {modal_call_id}")
            
            # Use modal_job_status_service to check status
            status, result = await modal_job_status_service.check_job_status(
                job_id, modal_call_id
            )
            
            if status.value == 'completed' and result:
                logger.info(f"✅ Job {job_id} completed, processing results")
                
                # Process the completed job through the storage pipeline
                success = await self._process_completed_job(job_id, result, modal_job['data'])
                
                if success:
                    self.processed_count += 1
                    logger.info(f"✅ Successfully processed completed job {job_id}")
                else:
                    logger.error(f"❌ Failed to process completed job {job_id}")
                    
            elif status.value == 'failed':
                logger.info(f"❌ Job {job_id} failed on Modal")
                # Update job status to failed
                unified_job_manager.update_job_status(
                    job_id, 
                    'failed',
                    {'error': result.get('error') if result else 'Modal job failed'}
                )
                
            elif status.value == 'not_found':
                # Handle unhydrated FunctionCall and other Modal call ID issues
                if result and result.get('reason') == 'unhydrated_function_call':
                    logger.warning(f"🔍 Job {job_id} has unhydrated FunctionCall - marking as failed")
                    unified_job_manager.update_job_status(
                        job_id,
                        'failed', 
                        {
                            'error': 'Modal call ID no longer accessible',
                            'cleanup_reason': 'unhydrated_function_call',
                            'original_modal_call_id': modal_call_id
                        }
                    )
                else:
                    logger.warning(f"🔍 Job {job_id} Modal call not found")
                    unified_job_manager.update_job_status(
                        job_id,
                        'failed',
                        {'error': 'Modal call ID not found'}
                    )
                
        except Exception as e:
            logger.error(f"❌ Error checking job {modal_job.get('id')}: {e}")
    
    async def _process_completed_job(
        self, 
        job_id: str, 
        modal_result: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> bool:
        """Process a completed job through the batch-aware completion system"""
        try:
            # ENHANCED: Use batch-aware completion checker for all job completions
            from services.batch_aware_completion_checker import batch_aware_completion_checker
            
            logger.info(f"🎯 Processing completed job {job_id} through batch-aware system")
            
            # Trigger batch-aware completion processing
            # This handles both individual jobs and batch children intelligently
            await batch_aware_completion_checker.on_job_completion(job_id, modal_result)
            
            logger.info(f"✅ Successfully processed completed job {job_id} via batch-aware system")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error processing completed job {job_id}: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status and metrics"""
        return {
            'running': self.running,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'check_interval': self.check_interval,
            'health': 'healthy' if self.error_count < 10 else 'degraded'
        }

# Global instance
modal_completion_checker = ModalCompletionChecker()

async def start_completion_checker():
    """Start the completion checking service"""
    await modal_completion_checker.start()

def stop_completion_checker():
    """Stop the completion checking service"""
    modal_completion_checker.stop()