"""
Job Monitoring Service
Monitors job status changes and triggers appropriate actions
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from google.cloud import firestore
from google.cloud.firestore_v1.watch import DocumentChange

from services.webhook_service import webhook_service

logger = logging.getLogger(__name__)

class JobMonitoringService:
    """Service for monitoring job status changes and triggering actions"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.monitoring_interval = 30  # seconds
        self.stale_job_threshold = 3600  # 1 hour in seconds
        self.watchers = {}
        self.running = False
        
        logger.info("👁️ Job Monitoring Service initialized")
    
    async def start_monitoring(self):
        """Start monitoring jobs for status changes"""
        
        if self.running:
            logger.warning("Monitoring service already running")
            return
        
        self.running = True
        logger.info("🚀 Starting job monitoring service")
        
        # Start background tasks
        asyncio.create_task(self._monitor_job_completions())
        asyncio.create_task(self._monitor_batch_completions())
        asyncio.create_task(self._monitor_stale_jobs())
        
        logger.info("✅ Job monitoring service started")
    
    async def stop_monitoring(self):
        """Stop monitoring jobs"""
        
        self.running = False
        
        # Cancel all watchers
        for watcher_id, cancel_func in self.watchers.items():
            cancel_func()
        
        self.watchers.clear()
        logger.info("🛑 Job monitoring service stopped")
    
    async def _monitor_job_completions(self):
        """Monitor individual job completions"""
        
        while self.running:
            try:
                # Query recently completed jobs that haven't been notified
                jobs_ref = self.db.collection('jobs')
                
                # Get jobs completed in the last 5 minutes that haven't been notified
                five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
                
                completed_jobs = jobs_ref.where('status', '==', 'completed')\
                    .where('webhook_notified', '==', False)\
                    .where('completed_at', '>=', five_minutes_ago)\
                    .limit(50).stream()
                
                for job_doc in completed_jobs:
                    job_data = job_doc.to_dict()
                    await self._process_completed_job(job_doc.id, job_data)
                
                # Check failed jobs
                failed_jobs = jobs_ref.where('status', '==', 'failed')\
                    .where('webhook_notified', '==', False)\
                    .where('failed_at', '>=', five_minutes_ago)\
                    .limit(50).stream()
                
                for job_doc in failed_jobs:
                    job_data = job_doc.to_dict()
                    await self._process_failed_job(job_doc.id, job_data)
                
            except Exception as e:
                logger.error(f"Error monitoring job completions: {e}")
            
            await asyncio.sleep(self.monitoring_interval)
    
    async def _monitor_batch_completions(self):
        """Monitor batch job completions"""
        
        while self.running:
            try:
                # Query batch parent jobs
                batches_ref = self.db.collection('jobs')
                
                # Get batch parent jobs that might be complete
                batch_parents = batches_ref.where('job_type', '==', 'BATCH_PARENT')\
                    .where('status', 'in', ['running', 'pending'])\
                    .limit(20).stream()
                
                for batch_doc in batch_parents:
                    batch_data = batch_doc.to_dict()
                    await self._check_batch_completion(batch_doc.id, batch_data)
                
            except Exception as e:
                logger.error(f"Error monitoring batch completions: {e}")
            
            await asyncio.sleep(self.monitoring_interval * 2)  # Check less frequently
    
    async def _monitor_stale_jobs(self):
        """Monitor and handle stale/stuck jobs"""
        
        while self.running:
            try:
                # Query jobs that have been running too long
                stale_threshold = datetime.utcnow() - timedelta(seconds=self.stale_job_threshold)
                
                jobs_ref = self.db.collection('jobs')
                stale_jobs = jobs_ref.where('status', '==', 'running')\
                    .where('started_at', '<=', stale_threshold)\
                    .limit(10).stream()
                
                for job_doc in stale_jobs:
                    job_data = job_doc.to_dict()
                    await self._handle_stale_job(job_doc.id, job_data)
                
            except Exception as e:
                logger.error(f"Error monitoring stale jobs: {e}")
            
            await asyncio.sleep(self.monitoring_interval * 4)  # Check every 2 minutes
    
    async def _process_completed_job(self, job_id: str, job_data: Dict[str, Any]):
        """Process a completed job"""
        
        try:
            user_id = job_data.get('user_id')
            if not user_id:
                logger.warning(f"No user_id for job {job_id}")
                return
            
            # Send webhook notification
            await webhook_service.send_job_completion_webhook(
                job_id=job_id,
                user_id=user_id,
                status='completed',
                results=job_data.get('output_data', {})
            )
            
            # Mark as notified
            self.db.collection('jobs').document(job_id).update({
                'webhook_notified': True,
                'webhook_notified_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"✅ Processed completed job: {job_id}")
            
            # If this is a batch child, check if batch is complete
            if job_data.get('job_type') == 'BATCH_CHILD' and job_data.get('batch_parent_id'):
                await self._check_batch_completion_by_child(job_data['batch_parent_id'])
            
        except Exception as e:
            logger.error(f"Error processing completed job {job_id}: {e}")
    
    async def _process_failed_job(self, job_id: str, job_data: Dict[str, Any]):
        """Process a failed job"""
        
        try:
            user_id = job_data.get('user_id')
            if not user_id:
                logger.warning(f"No user_id for job {job_id}")
                return
            
            # Send webhook notification
            await webhook_service.send_job_completion_webhook(
                job_id=job_id,
                user_id=user_id,
                status='failed',
                results={'error': job_data.get('error', 'Unknown error')}
            )
            
            # Mark as notified
            self.db.collection('jobs').document(job_id).update({
                'webhook_notified': True,
                'webhook_notified_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"❌ Processed failed job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing failed job {job_id}: {e}")
    
    async def _check_batch_completion(self, batch_id: str, batch_data: Dict[str, Any]):
        """Check if a batch is complete"""
        
        try:
            # Get all child jobs
            child_jobs_ref = self.db.collection('jobs')\
                .where('batch_parent_id', '==', batch_id)
            
            child_jobs = list(child_jobs_ref.stream())
            total_jobs = len(child_jobs)
            
            if total_jobs == 0:
                logger.warning(f"No child jobs found for batch {batch_id}")
                return
            
            completed_jobs = 0
            failed_jobs = 0
            running_jobs = 0
            
            for child_doc in child_jobs:
                child_data = child_doc.to_dict()
                status = child_data.get('status')
                
                if status == 'completed':
                    completed_jobs += 1
                elif status == 'failed':
                    failed_jobs += 1
                elif status == 'running':
                    running_jobs += 1
            
            # Check if batch is complete
            if completed_jobs + failed_jobs == total_jobs:
                await self._complete_batch(batch_id, batch_data, total_jobs, completed_jobs, failed_jobs)
            else:
                # Update batch progress
                self.db.collection('jobs').document(batch_id).update({
                    'progress': {
                        'total': total_jobs,
                        'completed': completed_jobs,
                        'failed': failed_jobs,
                        'running': running_jobs,
                        'percentage': (completed_jobs + failed_jobs) / total_jobs * 100
                    },
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
        except Exception as e:
            logger.error(f"Error checking batch completion for {batch_id}: {e}")
    
    async def _check_batch_completion_by_child(self, batch_parent_id: str):
        """Check batch completion triggered by child completion"""
        
        try:
            batch_doc = self.db.collection('jobs').document(batch_parent_id).get()
            
            if batch_doc.exists:
                batch_data = batch_doc.to_dict()
                if batch_data.get('status') != 'completed':
                    await self._check_batch_completion(batch_parent_id, batch_data)
            
        except Exception as e:
            logger.error(f"Error checking batch by child: {e}")
    
    async def _complete_batch(
        self, 
        batch_id: str, 
        batch_data: Dict[str, Any],
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int
    ):
        """Mark batch as complete and send notifications"""
        
        try:
            user_id = batch_data.get('user_id')
            
            # Calculate summary statistics
            success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            summary = {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': success_rate,
                'completion_time': datetime.utcnow().isoformat()
            }
            
            # Update batch status
            self.db.collection('jobs').document(batch_id).update({
                'status': 'completed',
                'completed_at': firestore.SERVER_TIMESTAMP,
                'summary': summary,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Send webhook notification
            if user_id:
                await webhook_service.send_batch_completion_webhook(
                    batch_id=batch_id,
                    user_id=user_id,
                    total_jobs=total_jobs,
                    completed_jobs=completed_jobs,
                    failed_jobs=failed_jobs,
                    summary=summary
                )
            
            logger.info(f"🎉 Batch {batch_id} completed: {completed_jobs}/{total_jobs} successful")
            
        except Exception as e:
            logger.error(f"Error completing batch {batch_id}: {e}")
    
    async def _handle_stale_job(self, job_id: str, job_data: Dict[str, Any]):
        """Handle a stale/stuck job"""
        
        try:
            started_at = job_data.get('started_at')
            if isinstance(started_at, datetime):
                runtime = (datetime.utcnow() - started_at).total_seconds()
            else:
                runtime = self.stale_job_threshold
            
            logger.warning(f"⚠️ Stale job detected: {job_id} (running for {runtime:.0f}s)")
            
            # Mark job as failed due to timeout
            self.db.collection('jobs').document(job_id).update({
                'status': 'failed',
                'error': f'Job timeout after {runtime:.0f} seconds',
                'failed_at': firestore.SERVER_TIMESTAMP,
                'timeout': True,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Send failure notification
            user_id = job_data.get('user_id')
            if user_id:
                await webhook_service.send_job_completion_webhook(
                    job_id=job_id,
                    user_id=user_id,
                    status='failed',
                    results={'error': f'Job timeout after {runtime:.0f} seconds'}
                )
            
        except Exception as e:
            logger.error(f"Error handling stale job {job_id}: {e}")
    
    def watch_job(self, job_id: str, callback):
        """Watch a specific job for changes (real-time)"""
        
        def on_snapshot(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                callback(doc.id, doc.to_dict())
        
        doc_ref = self.db.collection('jobs').document(job_id)
        doc_watch = doc_ref.on_snapshot(on_snapshot)
        
        self.watchers[job_id] = doc_watch
        logger.info(f"👁️ Watching job: {job_id}")
        
        return doc_watch

# Global monitoring service instance
job_monitoring_service = JobMonitoringService()