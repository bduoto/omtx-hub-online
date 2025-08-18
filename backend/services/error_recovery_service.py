"""
Error Recovery Service for OMTX-Hub
Handles job failures, retries, and system recovery
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ErrorType(str, Enum):
    MODAL_TIMEOUT = "modal_timeout"
    MODAL_ERROR = "modal_error"
    STORAGE_ERROR = "storage_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"

class RecoveryAction(str, Enum):
    RETRY = "retry"
    FAIL_GRACEFULLY = "fail_gracefully"
    ESCALATE = "escalate"
    IGNORE = "ignore"

@dataclass
class ErrorContext:
    """Context information for error recovery"""
    job_id: str
    job_type: str
    error_type: ErrorType
    error_message: str
    attempt_count: int
    timestamp: float
    additional_context: Dict[str, Any]

class ErrorRecoveryService:
    """Service for handling job failures and recovery"""
    
    def __init__(self):
        self.max_retries = {
            ErrorType.MODAL_TIMEOUT: 2,
            ErrorType.MODAL_ERROR: 1,
            ErrorType.STORAGE_ERROR: 3,
            ErrorType.DATABASE_ERROR: 2,
            ErrorType.VALIDATION_ERROR: 0,  # Don't retry validation errors
            ErrorType.SYSTEM_ERROR: 1
        }
        
        self.retry_delays = {
            ErrorType.MODAL_TIMEOUT: 300,  # 5 minutes
            ErrorType.MODAL_ERROR: 60,     # 1 minute
            ErrorType.STORAGE_ERROR: 30,   # 30 seconds
            ErrorType.DATABASE_ERROR: 60,  # 1 minute
            ErrorType.SYSTEM_ERROR: 120    # 2 minutes
        }
        
        self.failed_jobs = {}  # job_id -> ErrorContext
        self.recovery_queue = asyncio.Queue()
        
    async def handle_job_error(self, job_id: str, job_type: str, error: Exception, 
                              attempt_count: int = 1, additional_context: Dict = None) -> RecoveryAction:
        """Handle a job error and determine recovery action"""
        
        # Classify the error
        error_type = self._classify_error(error)
        
        # Create error context
        context = ErrorContext(
            job_id=job_id,
            job_type=job_type,
            error_type=error_type,
            error_message=str(error),
            attempt_count=attempt_count,
            timestamp=time.time(),
            additional_context=additional_context or {}
        )
        
        # Store error context
        self.failed_jobs[job_id] = context
        
        # Determine recovery action
        action = self._determine_recovery_action(context)
        
        logger.error(f"Job {job_id} failed: {error_type.value} - Action: {action.value}")
        
        if action == RecoveryAction.RETRY:
            await self._schedule_retry(context)
        elif action == RecoveryAction.FAIL_GRACEFULLY:
            await self._fail_job_gracefully(context)
        elif action == RecoveryAction.ESCALATE:
            await self._escalate_error(context)
        
        return action
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type based on exception"""
        error_str = str(error).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.MODAL_TIMEOUT
        elif "modal" in error_str:
            return ErrorType.MODAL_ERROR
        elif "storage" in error_str or "bucket" in error_str or "gcs" in error_str:
            return ErrorType.STORAGE_ERROR
        elif "firestore" in error_str or "database" in error_str:
            return ErrorType.DATABASE_ERROR
        elif "validation" in error_str or "invalid" in error_str:
            return ErrorType.VALIDATION_ERROR
        else:
            return ErrorType.SYSTEM_ERROR
    
    def _determine_recovery_action(self, context: ErrorContext) -> RecoveryAction:
        """Determine what recovery action to take"""
        
        # Check if we've exceeded max retries
        max_retries = self.max_retries.get(context.error_type, 0)
        if context.attempt_count > max_retries:
            if context.error_type in [ErrorType.MODAL_TIMEOUT, ErrorType.MODAL_ERROR]:
                return RecoveryAction.ESCALATE
            else:
                return RecoveryAction.FAIL_GRACEFULLY
        
        # Validation errors should never be retried
        if context.error_type == ErrorType.VALIDATION_ERROR:
            return RecoveryAction.FAIL_GRACEFULLY
        
        # For batch children, be more aggressive with retries
        if context.job_type == "batch_child":
            return RecoveryAction.RETRY
        
        # For batch parents, escalate quickly
        if context.job_type == "batch_parent":
            return RecoveryAction.ESCALATE
        
        # Default to retry for most errors
        return RecoveryAction.RETRY
    
    async def _schedule_retry(self, context: ErrorContext):
        """Schedule a job for retry"""
        delay = self.retry_delays.get(context.error_type, 60)
        
        logger.info(f"Scheduling retry for job {context.job_id} in {delay} seconds")
        
        # Add to recovery queue with delay
        await asyncio.sleep(delay)
        await self.recovery_queue.put(context)
    
    async def _fail_job_gracefully(self, context: ErrorContext):
        """Fail a job gracefully with proper cleanup"""
        from database.unified_job_manager import unified_job_manager
        
        logger.info(f"Failing job {context.job_id} gracefully")
        
        # Update job status
        unified_job_manager.update_job_status(
            context.job_id, 
            "failed", 
            {
                "error_type": context.error_type.value,
                "error_message": context.error_message,
                "failed_at": context.timestamp,
                "attempt_count": context.attempt_count
            }
        )
        
        # If this is a batch child, update parent progress
        if context.job_type == "batch_child":
            await self._update_batch_parent_on_child_failure(context)
    
    async def _escalate_error(self, context: ErrorContext):
        """Escalate error to system administrators"""
        logger.critical(f"Escalating error for job {context.job_id}: {context.error_message}")
        
        # In production, this would send alerts to monitoring systems
        # For now, just log and fail gracefully
        await self._fail_job_gracefully(context)
    
    async def _update_batch_parent_on_child_failure(self, context: ErrorContext):
        """Update batch parent when a child fails"""
        from database.unified_job_manager import unified_job_manager
        
        # Get the job to find parent ID
        job = unified_job_manager.get_job(context.job_id)
        if not job or not job.get('batch_parent_id'):
            return
        
        parent_id = job['batch_parent_id']
        
        # Update batch progress
        unified_job_manager.update_batch_progress(parent_id)
        
        logger.info(f"Updated batch parent {parent_id} after child {context.job_id} failure")
    
    async def process_recovery_queue(self):
        """Process the recovery queue for retries"""
        while True:
            try:
                context = await self.recovery_queue.get()
                await self._retry_job(context)
            except Exception as e:
                logger.error(f"Error processing recovery queue: {e}")
                await asyncio.sleep(10)  # Brief pause before continuing
    
    async def _retry_job(self, context: ErrorContext):
        """Retry a failed job"""
        from api.unified_endpoints import process_prediction_task
        from database.unified_job_manager import unified_job_manager
        
        logger.info(f"Retrying job {context.job_id} (attempt {context.attempt_count + 1})")
        
        # Get job data
        job = unified_job_manager.get_job(context.job_id)
        if not job:
            logger.error(f"Cannot retry job {context.job_id}: job not found")
            return
        
        # Reset job status
        unified_job_manager.update_job_status(context.job_id, "pending")
        
        # Retry the job
        try:
            await process_prediction_task(
                job_id=context.job_id,
                task_type=job.get('type', 'protein_ligand_binding'),
                input_data=job.get('input_data', {}),
                job_name=job.get('name', 'Retry Job'),
                use_msa=job.get('input_data', {}).get('use_msa', True),
                use_potentials=job.get('input_data', {}).get('use_potentials', False)
            )
        except Exception as e:
            # Handle retry failure
            await self.handle_job_error(
                context.job_id, 
                context.job_type, 
                e, 
                context.attempt_count + 1,
                context.additional_context
            )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        error_counts = {}
        recovery_actions = {}
        
        for context in self.failed_jobs.values():
            error_type = context.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            'total_failed_jobs': len(self.failed_jobs),
            'error_type_distribution': error_counts,
            'recovery_queue_size': self.recovery_queue.qsize(),
            'recent_failures': [
                {
                    'job_id': ctx.job_id,
                    'error_type': ctx.error_type.value,
                    'attempt_count': ctx.attempt_count,
                    'timestamp': ctx.timestamp
                }
                for ctx in list(self.failed_jobs.values())[-10:]  # Last 10 failures
            ]
        }
    
    def clear_old_errors(self, hours_old: int = 24):
        """Clear old error records"""
        cutoff_time = time.time() - (hours_old * 3600)
        self.failed_jobs = {
            job_id: context for job_id, context in self.failed_jobs.items()
            if context.timestamp > cutoff_time
        }

# Global instance
error_recovery_service = ErrorRecoveryService()
