"""
Safe Background Job Processor
Processes existing jobs with safety controls to prevent unwanted submissions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)

class SafeBackgroundProcessor:
    """Background processor with safety controls"""
    
    def __init__(self):
        self.processing = False
        self.max_concurrent_submissions = 10  # Limit SUBMISSION rate, not Modal execution
        self.active_modal_jobs = set()
        self.safety_enabled = True
        
        # Safety controls
        self.allowed_job_types = {
            'protein_ligand_binding',
            'batch_protein_ligand_screening', 
            'protein_structure',
            'antibody_design',
            'BATCH_CHILD',
            'BATCH_PARENT'
        }
        
        # Only process jobs created in last 24 hours (safety measure)
        self.max_job_age_hours = 24
    
    async def start_processing(self):
        """Start safe background processing"""
        
        if self.processing:
            logger.warning("⚠️ Background processor already running")
            return
            
        self.processing = True
        logger.info("🚀 Starting SAFE background job processor")
        logger.info(f"   Max concurrent submissions: {self.max_concurrent_submissions} (Modal handles unlimited scaling)")
        logger.info(f"   Max job age: {self.max_job_age_hours} hours")
        logger.info(f"   Allowed job types: {list(self.allowed_job_types)}")
        logger.info("   🚀 NO LIMITS on Modal execution - 1500+ job batches fully supported!")
        
        while self.processing:
            try:
                await self._process_pending_jobs()
                await self._cleanup_completed_jobs()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Background processor error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_pending_jobs(self):
        """Process pending jobs with safety checks"""
        
        # Only limit submission rate, not Modal execution
        # Modal auto-scales to handle any number of jobs
        
        # Get pending jobs with safety filters
        pending_jobs = await self._get_safe_pending_jobs()
        
        if not pending_jobs:
            return
            
        logger.info(f"🔍 Found {len(pending_jobs)} safe pending jobs to process")
        
        # Process jobs in batches to avoid overwhelming the system during submission
        # But Modal will handle unlimited concurrent execution
        batch_size = min(self.max_concurrent_submissions, len(pending_jobs))
        jobs_to_process = pending_jobs[:batch_size]
        
        logger.info(f"🚀 Submitting {len(jobs_to_process)} jobs to Modal (no execution limits)")
        
        for job in jobs_to_process:
            try:
                await self._process_single_job(job)
                # Small delay between submissions to avoid overwhelming the submission system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Failed to process job {job.get('id', 'unknown')}: {e}")
    
    async def _get_safe_pending_jobs(self) -> List[Dict[str, Any]]:
        """Get pending jobs with safety filters"""
        
        try:
            # Get all pending jobs
            all_pending = unified_job_manager.get_jobs_by_status('pending', limit=50)
            
            safe_jobs = []
            cutoff_time = datetime.utcnow() - timedelta(hours=self.max_job_age_hours)
            
            for job in all_pending:
                # Safety check 1: Job type allowed
                job_type = job.get('job_type', '')
                task_type = job.get('task_type', '')
                
                if not any(allowed in str(job_type) or allowed in str(task_type) 
                          for allowed in self.allowed_job_types):
                    logger.debug(f"⏭️ Skipping job {job.get('id')} - type not allowed: {job_type}/{task_type}")
                    continue
                
                # Safety check 2: Job age (be more flexible with date parsing)
                created_at = job.get('created_at')
                if created_at:
                    try:
                        # Handle different timestamp formats
                        if hasattr(created_at, 'timestamp'):
                            # Firestore timestamp
                            job_datetime = datetime.fromtimestamp(created_at.timestamp())
                        elif isinstance(created_at, (int, float)):
                            # Unix timestamp
                            job_datetime = datetime.fromtimestamp(created_at)
                        else:
                            # String timestamp
                            created_str = str(created_at).replace('Z', '+00:00')
                            job_datetime = datetime.fromisoformat(created_str).replace(tzinfo=None)
                            
                        if job_datetime < cutoff_time:
                            logger.debug(f"⏭️ Skipping old job {job.get('id')} - created {job_datetime}")
                            continue
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Could not parse date for job {job.get('id')}: {e} - allowing job to process")
                        # Allow processing if we can't parse the date (be permissive)
                
                # Safety check 3: Has required data
                input_data = job.get('input_data', {})
                if not input_data and not job.get('parameters'):
                    logger.debug(f"⏭️ Skipping job {job.get('id')} - no input data or parameters")
                    continue
                
                safe_jobs.append(job)
            
            logger.info(f"✅ {len(safe_jobs)} jobs passed safety checks (out of {len(all_pending)} pending)")
            return safe_jobs  # No limit - Modal handles all jobs
            
        except Exception as e:
            logger.error(f"❌ Error getting safe pending jobs: {e}")
            return []
    
    async def _process_single_job(self, job: Dict[str, Any]):
        """Process a single job safely"""
        
        job_id = job.get('id', job.get('job_id'))
        job_type = job.get('job_type', job.get('task_type', ''))
        
        logger.info(f"🚀 Processing job {job_id} ({job_type})")
        
        try:
            # Update status to running first
            unified_job_manager.update_job_status(job_id, 'running')
            
            # Use the existing task handler system
            from tasks.task_handlers import task_handler_registry
            
            # Extract input data
            input_data = job.get('input_data', {})
            job_name = job.get('job_name', job.get('name', f'Job {job_id[:8]}'))
            
            # Determine task type
            task_type = job.get('task_type', 'protein_ligand_binding')
            if 'batch' in str(job_type).lower() or 'BATCH_CHILD' in str(job_type):
                task_type = 'protein_ligand_binding'
            
            # Process task using existing handler
            result = await task_handler_registry.process_task(
                task_type=task_type,
                input_data=input_data,
                job_name=job_name,
                job_id=job_id,
                use_msa=input_data.get('use_msa', True),
                use_potentials=input_data.get('use_potentials', False)
            )
            
            # Track Modal job if async
            modal_call_id = result.get('modal_call_id')
            if modal_call_id:
                self.active_modal_jobs.add(modal_call_id)
                logger.info(f"✅ Job {job_id} submitted to Modal: {modal_call_id}")
                # Update job with Modal call ID
                unified_job_manager.update_job_status(job_id, 'running', result)
            else:
                # Sync job completed immediately
                if result.get('status') == 'completed':
                    unified_job_manager.update_job_status(job_id, 'completed', result)
                    logger.info(f"✅ Job {job_id} completed synchronously")
                else:
                    logger.warning(f"⚠️ Job {job_id} result: {result}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing job {job_id}: {e}")
            unified_job_manager.update_job_status(job_id, 'failed', {'error': str(e)})
    
    async def _cleanup_completed_jobs(self):
        """Clean up completed Modal jobs from tracking"""
        
        if not self.active_modal_jobs:
            return
            
        completed_jobs = set()
        
        # Use the Modal completion checker to see which jobs are done
        try:
            from services.modal_completion_checker import modal_completion_checker
            
            for modal_call_id in self.active_modal_jobs.copy():
                try:
                    # Check if job is still being tracked by completion checker
                    # If not, it's probably completed
                    if modal_call_id not in getattr(modal_completion_checker, 'pending_calls', {}):
                        completed_jobs.add(modal_call_id)
                        
                except Exception as e:
                    logger.debug(f"Assuming job {modal_call_id} completed due to error: {e}")
                    completed_jobs.add(modal_call_id)
        
        except Exception as e:
            logger.warning(f"⚠️ Error during cleanup: {e}")
        
        # Remove completed jobs from tracking
        self.active_modal_jobs -= completed_jobs
        
        if completed_jobs:
            logger.info(f"🧹 Cleaned up {len(completed_jobs)} completed Modal jobs")
    
    def stop_processing(self):
        """Stop background processing"""
        self.processing = False
        logger.info("🛑 Safe background job processor stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get processor status"""
        return {
            'processing': self.processing,
            'active_modal_jobs': len(self.active_modal_jobs),
            'max_concurrent_submissions': self.max_concurrent_submissions,
            'modal_execution_limit': 'UNLIMITED - Modal auto-scales',
            'safety_enabled': self.safety_enabled,
            'allowed_job_types': list(self.allowed_job_types),
            'max_job_age_hours': self.max_job_age_hours,
            'batch_support': '1500+ jobs fully supported'
        }

# Global instance
safe_background_processor = SafeBackgroundProcessor()

async def safe_background_job_processor():
    """Entry point for safe background processing"""
    await safe_background_processor.start_processing()