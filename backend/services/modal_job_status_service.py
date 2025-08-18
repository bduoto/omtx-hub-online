"""
Modal Job Status Service - Production-Ready Architecture

Replaces the polling-based modal_monitor with efficient, on-demand status checking
using Modal's native FunctionCall.from_id() pattern.

Senior Principal Engineering Design Principles:
- Event-driven over polling
- Fail-fast with clear error messages  
- Idempotent operations
- Comprehensive logging and observability
- Self-healing error recovery
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum

import modal

from database.unified_job_manager import unified_job_manager
from services.batch_relationship_manager import batch_relationship_manager
from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

class JobStatusResult(Enum):
    """Enum for job status check results"""
    COMPLETED = "completed"
    RUNNING = "running" 
    FAILED = "failed"
    NOT_FOUND = "not_found"
    ERROR = "error"

class ModalJobStatusService:
    """
    Production-ready service for checking Modal job status without polling.
    
    Key Features:
    - Non-blocking status checks using Modal FunctionCall.from_id()
    - Immediate result processing when jobs complete
    - Comprehensive error handling and recovery
    - Batch-aware result processing
    - Idempotent operations (safe to call multiple times)
    """
    
    def __init__(self):
        self.processed_jobs = set()  # Prevent duplicate processing
        self.error_count = 0
        self.success_count = 0
        
    async def check_job_status(self, job_id: str, modal_call_id: str) -> Tuple[JobStatusResult, Optional[Dict[str, Any]]]:
        """
        Check the status of a specific Modal job non-blocking.
        
        Args:
            job_id: Our internal job ID
            modal_call_id: Modal's function call ID
            
        Returns:
            Tuple of (status, result_data)
            
        Senior Principal Engineering Notes:
        - Uses Modal's recommended FunctionCall.from_id() pattern
        - Non-blocking with timeout=0 for instant response
        - Comprehensive error handling for all failure modes
        - Returns structured data for easy downstream processing
        """
        try:
            logger.debug(f"🔍 Checking Modal status for job {job_id} (call: {modal_call_id})")
            
            # Use Modal's native status checking
            function_call = modal.FunctionCall.from_id(modal_call_id)
            
            try:
                # Non-blocking check - returns immediately if not done
                result = function_call.get(timeout=0)
                
                # Job completed successfully
                logger.info(f"✅ Modal job completed for {job_id}")
                self.success_count += 1
                
                return JobStatusResult.COMPLETED, result
                
            except TimeoutError:
                # Job still running - this is normal
                logger.debug(f"🔄 Modal job still running for {job_id}")
                return JobStatusResult.RUNNING, None
                
            except modal.exception.InvalidError as e:
                # Modal call ID doesn't exist
                logger.warning(f"🔍 Modal call {modal_call_id} not found for job {job_id}: {e}")
                return JobStatusResult.NOT_FOUND, None
                
            except Exception as modal_error:
                # Check for specific unhydrated FunctionCall error
                error_str = str(modal_error)
                if "unhydrated FunctionCall" in error_str:
                    logger.warning(f"🔍 Unhydrated FunctionCall for job {job_id} - Modal call {modal_call_id} no longer accessible")
                    return JobStatusResult.NOT_FOUND, {"error": "Modal call ID no longer accessible", "reason": "unhydrated_function_call"}
                else:
                    # Other Modal-specific errors (network, auth, etc.)
                    logger.error(f"❌ Modal error checking job {job_id}: {modal_error}")
                    self.error_count += 1
                    return JobStatusResult.ERROR, {"error": str(modal_error)}
                
        except Exception as e:
            # Unexpected errors in our code
            logger.error(f"❌ Unexpected error checking job {job_id}: {e}")
            self.error_count += 1
            return JobStatusResult.ERROR, {"error": str(e)}
    
    async def process_completed_job(self, job_id: str, modal_result: Dict[str, Any]) -> bool:
        """
        Process a completed Modal job immediately.
        
        This replaces the modal_monitor's delayed processing with immediate
        result handling when we detect completion.
        
        Args:
            job_id: Our internal job ID
            modal_result: The result from Modal
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            logger.info(f"🔍 DEBUG: Starting process_completed_job for {job_id}")
            logger.info(f"🔍 DEBUG: Modal result keys: {list(modal_result.keys())}")
            logger.info(f"🔍 DEBUG: Has structure_file_base64: {'structure_file_base64' in modal_result}")
            
            # Prevent duplicate processing
            if job_id in self.processed_jobs:
                logger.debug(f"Job {job_id} already processed, skipping")
                return True
                
            logger.info(f"🔄 Processing completed job {job_id}")
            
            # Get job details from database
            job_data = await unified_job_manager.get_job_async(job_id)  # Use async version
            if not job_data:
                logger.error(f"❌ Job {job_id} not found in database")
                return False
            
            logger.info(f"🔍 DEBUG: Job data found for {job_id}")
            
            # Check if this is a batch child job
            input_data = job_data.get('input_data', {})
            parent_batch_id = input_data.get('parent_batch_id')
            
            logger.info(f"🔍 DEBUG: parent_batch_id = {parent_batch_id}")
            
            if parent_batch_id:
                # Process as batch child job
                logger.info(f"🔍 DEBUG: Processing as batch child job")
                success = await self._process_batch_child_completion(
                    job_id, parent_batch_id, modal_result, job_data
                )
                logger.info(f"🔍 DEBUG: Batch child processing result: {success}")
            else:
                # Process as individual job
                logger.info(f"🔍 DEBUG: Processing as individual job")
                success = await self._process_individual_job_completion(
                    job_id, modal_result, job_data
                )
                logger.info(f"🔍 DEBUG: Individual processing result: {success}")
            
            if success:
                self.processed_jobs.add(job_id)
                logger.info(f"✅ Successfully processed completed job {job_id}")
            else:
                logger.error(f"❌ Failed to process completed job {job_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error processing completed job {job_id}: {e}")
            return False
    
    async def _process_batch_child_completion(
        self, 
        job_id: str, 
        parent_batch_id: str, 
        modal_result: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> bool:
        """Process completion of a batch child job"""
        try:
            logger.info(f"📦 Processing batch child completion: {job_id} in batch {parent_batch_id}")
            
            # Store child results using batch relationship manager
            # This triggers the complete storage hierarchy we built
            success = await batch_relationship_manager.store_child_results(
                parent_batch_id,
                job_id,
                modal_result,
                job_data.get('input_data', {}).get('task_type', 'protein_ligand_binding')
            )
            
            if success:
                # Update job status in database (using async version)
                # Don't spread job_data to avoid datetime serialization issues
                await unified_job_manager.update_job_status_async(
                    job_id, 
                    "completed",
                    {
                        'status': 'completed',
                        'completed_at': datetime.utcnow().isoformat(),
                        'results': modal_result,
                        'files_stored_to_gcp': True,
                        'has_results': True,
                        'output_data': {
                            'has_results': True,
                            'results_stored': True
                        }
                    }
                )
                
                logger.info(f"✅ Batch child {job_id} completed and stored")
                return True
            else:
                logger.error(f"❌ Failed to store batch child results for {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing batch child {job_id}: {e}")
            return False
    
    async def _process_individual_job_completion(
        self, 
        job_id: str, 
        modal_result: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> bool:
        """Process completion of an individual (non-batch) job"""
        try:
            logger.info(f"🔧 Processing individual job completion: {job_id}")
            
            # Store results to GCP using existing storage service
            storage_path = f"jobs/{job_id}"
            
            # Store main results file
            results_success = await gcp_storage_service.storage.upload_file(
                f"{storage_path}/results.json",
                modal_result
            )
            
            # Store structure file if present
            structure_success = True
            if 'structure_file_base64' in modal_result:
                structure_success = await gcp_storage_service.storage.upload_file(
                    f"{storage_path}/structure.cif",
                    modal_result['structure_file_base64'],
                    is_base64=True
                )
            
            if results_success and structure_success:
                # Update job status in database (using async version)
                # Don't spread job_data to avoid datetime serialization issues
                await unified_job_manager.update_job_status_async(
                    job_id,
                    "completed", 
                    {
                        'status': 'completed',
                        'completed_at': datetime.utcnow().isoformat(),
                        'results': modal_result,
                        'files_stored_to_gcp': True,
                        'has_results': True,
                        'output_data': {
                            'has_results': True,
                            'results_stored': True
                        }
                    }
                )
                
                logger.info(f"✅ Individual job {job_id} completed and stored")
                return True
            else:
                logger.error(f"❌ Failed to store results for individual job {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing individual job {job_id}: {e}")
            return False
    
    async def check_multiple_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, Tuple[JobStatusResult, Optional[Dict[str, Any]]]]:
        """
        Check status of multiple jobs efficiently.
        
        Uses asyncio.gather for concurrent status checks.
        """
        try:
            logger.debug(f"🔍 Checking status of {len(jobs)} jobs concurrently")
            
            # Create tasks for concurrent execution
            tasks = []
            job_ids = []
            
            for job in jobs:
                job_id = job.get('id')
                modal_call_id = job.get('modal_call_id')
                
                if job_id and modal_call_id:
                    tasks.append(self.check_job_status(job_id, modal_call_id))
                    job_ids.append(job_id)
            
            # Execute all status checks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build response dictionary
            status_map = {}
            for i, result in enumerate(results):
                job_id = job_ids[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ Exception checking job {job_id}: {result}")
                    status_map[job_id] = (JobStatusResult.ERROR, {"error": str(result)})
                else:
                    status_map[job_id] = result
            
            return status_map
            
        except Exception as e:
            logger.error(f"❌ Error in check_multiple_jobs: {e}")
            return {}
    
    async def process_any_completed_jobs(self, status_map: Dict[str, Tuple[JobStatusResult, Optional[Dict[str, Any]]]]) -> int:
        """
        Process any completed jobs from a status check batch.
        
        Returns:
            Number of jobs successfully processed
        """
        processed_count = 0
        
        for job_id, (status, result) in status_map.items():
            if status == JobStatusResult.COMPLETED and result:
                success = await self.process_completed_job(job_id, result)
                if success:
                    processed_count += 1
        
        return processed_count
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get service health metrics for monitoring"""
        return {
            "processed_jobs_count": len(self.processed_jobs),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.success_count + self.error_count),
            "service_status": "healthy" if self.error_count < 10 else "degraded"
        }

# Global singleton instance
modal_job_status_service = ModalJobStatusService()