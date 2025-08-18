"""
Smart Job Router for OMTX-Hub Unified Architecture
Intelligently routes predictions to appropriate handlers based on content analysis
"""

import asyncio
import logging
import uuid
import time
from typing import Dict, Any, List
from models.enhanced_job_model import (
    EnhancedJobData, JobType, JobStatus, TaskType,
    create_individual_job, create_batch_parent_job, create_batch_child_job
)
from database.unified_job_manager import unified_job_manager
from services.modal_execution_service import modal_execution_service

logger = logging.getLogger(__name__)

class SmartJobRouter:
    """Smart router that handles both individual and batch predictions intelligently"""
    
    def __init__(self):
        self.job_manager = unified_job_manager
        self.modal_service = modal_execution_service
        
        # Import task handler registry dynamically to avoid circular imports
        try:
            from tasks.task_handlers import task_handler_registry
            self.task_registry = task_handler_registry
        except ImportError:
            logger.warning("Task handler registry not available - some features may not work")
            self.task_registry = None
    
    async def route_prediction(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Smart routing entry point for all predictions"""
        
        logger.info(f"🎯 Smart routing prediction request...")
        
        # Extract request components
        task_type = request_data.get('task_type')
        input_data = request_data.get('input_data', {})
        job_name = request_data.get('job_name', 'Unnamed Job')
        model_id = request_data.get('model_id', 'boltz2')
        use_msa = request_data.get('use_msa', True)
        use_potentials = request_data.get('use_potentials', False)
        
        # Determine job type intelligently
        job_type = self._determine_job_type(task_type, input_data)
        
        logger.info(f"   Determined job type: {job_type.value}")
        logger.info(f"   Task type: {task_type}")
        logger.info(f"   Job name: {job_name}")
        
        if job_type == JobType.BATCH_PARENT:
            return await self._handle_batch_prediction(
                task_type, input_data, job_name, model_id, use_msa, use_potentials
            )
        else:
            return await self._handle_individual_prediction(
                task_type, input_data, job_name, model_id, use_msa, use_potentials
            )
    
    def _determine_job_type(self, task_type: str, input_data: Dict[str, Any]) -> JobType:
        """Intelligent job type determination based on content analysis"""
        
        # Explicit batch task type
        if task_type == TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value:
            return JobType.BATCH_PARENT
        
        # Check for multiple ligands in individual task (auto-convert to batch)
        ligands = input_data.get('ligands', [])
        if isinstance(ligands, list) and len(ligands) > 1:
            logger.info(f"🔄 Auto-converting individual task to batch: {len(ligands)} ligands detected")
            return JobType.BATCH_PARENT
        
        # Check for batch indicators in input data
        if any(key.startswith('batch_') for key in input_data.keys()):
            return JobType.BATCH_PARENT
        
        # Check for array of compounds/sequences that indicate batch processing
        arrays_to_check = ['compounds', 'sequences', 'smiles_list', 'ligand_list']
        for array_key in arrays_to_check:
            array_data = input_data.get(array_key, [])
            if isinstance(array_data, list) and len(array_data) > 1:
                logger.info(f"🔄 Auto-converting to batch based on {array_key}: {len(array_data)} items")
                return JobType.BATCH_PARENT
        
        return JobType.INDIVIDUAL
    
    async def _handle_individual_prediction(
        self, task_type: str, input_data: Dict[str, Any], job_name: str,
        model_id: str, use_msa: bool, use_potentials: bool
    ) -> Dict[str, Any]:
        """Handle individual prediction with enhanced job model"""
        
        logger.info(f"🎯 Processing individual prediction: {job_name}")
        
        # Create enhanced job record
        job = create_individual_job(
            name=job_name,
            task_type=task_type,
            input_data=input_data,
            model_name=model_id
        )
        
        # Store job in database
        success = await self._store_enhanced_job(job)
        if not success:
            raise Exception("Failed to create job record")
        
        logger.info(f"✅ Created individual job: {job.id}")
        
        # Execute prediction asynchronously
        asyncio.create_task(self._execute_individual_job(job.id, task_type, input_data, use_msa, use_potentials))
        
        return {
            'job_id': job.id,
            'job_type': 'individual',
            'status': 'submitted',
            'message': f'Individual prediction submitted: {job_name}',
            'estimated_completion_time': self._estimate_completion_time(task_type)
        }
    
    async def _handle_batch_prediction(
        self, task_type: str, input_data: Dict[str, Any], job_name: str,
        model_id: str, use_msa: bool, use_potentials: bool
    ) -> Dict[str, Any]:
        """Handle batch prediction with proper parent-child hierarchy"""
        
        logger.info(f"🎯 Processing batch prediction: {job_name}")
        
        # Extract ligands from input data
        ligands = input_data.get('ligands', [])
        if not ligands:
            raise ValueError("Batch prediction requires ligands array")
        
        logger.info(f"   Processing {len(ligands)} ligands")
        
        # Create batch parent job
        parent_job = create_batch_parent_job(
            name=job_name,
            task_type=task_type,
            input_data=input_data,
            model_name=model_id
        )
        
        # Store parent job
        success = await self._store_enhanced_job(parent_job)
        if not success:
            raise Exception("Failed to create parent job record")
        
        logger.info(f"✅ Created batch parent: {parent_job.id}")
        
        # Create child jobs
        child_ids = []
        protein_sequence = input_data.get('protein_sequence', '')
        protein_name = input_data.get('protein_name', 'Unknown Protein')
        
        for idx, ligand in enumerate(ligands):
            child_id = f"{parent_job.id}-{idx:04d}"
            ligand_name = ligand.get('name', f'Ligand_{idx+1}')
            ligand_smiles = ligand.get('smiles', '')
            
            # Create child job with enhanced model
            child_job = EnhancedJobData(
                id=child_id,
                name=f"{job_name} - {ligand_name}",
                job_type=JobType.BATCH_CHILD,
                task_type=TaskType.PROTEIN_LIGAND_BINDING.value,
                status=JobStatus.PENDING,
                created_at=time.time(),
                input_data={
                    'protein_sequence': protein_sequence,
                    'ligand_smiles': ligand_smiles,
                    'ligand_name': ligand_name,
                    'protein_name': protein_name
                },
                model_name=model_id,
                batch_parent_id=parent_job.id,
                batch_index=idx
            )
            
            # Store child job
            await self._store_enhanced_job(child_job)
            child_ids.append(child_id)
        
        # Update parent with child IDs
        parent_job.batch_child_ids = child_ids
        await self._update_enhanced_job(parent_job)
        
        logger.info(f"✅ Created {len(child_ids)} child jobs")
        
        # Execute batch asynchronously
        asyncio.create_task(self._execute_batch_job(parent_job.id))
        
        return {
            'job_id': parent_job.id,
            'job_type': 'batch',
            'status': 'submitted',
            'total_ligands': len(ligands),
            'child_job_ids': child_ids,
            'message': f'Batch prediction submitted: {len(ligands)} ligands',
            'estimated_completion_time': len(ligands) * 30  # 30 seconds per ligand
        }
    
    async def _store_enhanced_job(self, job: EnhancedJobData) -> bool:
        """Store enhanced job in database"""
        try:
            firestore_data = job.to_firestore_dict()
            created_id = self.job_manager.create_job(firestore_data)
            return created_id is not None
        except Exception as e:
            logger.error(f"❌ Failed to store job {job.id}: {e}")
            return False
    
    async def _update_enhanced_job(self, job: EnhancedJobData) -> bool:
        """Update enhanced job in database"""
        try:
            firestore_data = job.to_firestore_dict()
            # Remove fields that shouldn't be updated
            update_data = {k: v for k, v in firestore_data.items() 
                          if k not in ['id', 'created_at']}
            
            return self.job_manager.update_job_status(
                job.id, 
                job.status.value, 
                update_data
            )
        except Exception as e:
            logger.error(f"❌ Failed to update job {job.id}: {e}")
            return False
    
    async def _execute_individual_job(
        self, job_id: str, task_type: str, input_data: Dict[str, Any],
        use_msa: bool, use_potentials: bool
    ):
        """Execute individual job using existing task handlers"""
        
        logger.info(f"🚀 Executing individual job: {job_id}")
        
        try:
            # Update job status to running
            self.job_manager.update_job_status(job_id, JobStatus.RUNNING.value)
            
            if self.task_registry:
                # Use existing task handler
                result = await self.task_registry.process_task(
                    task_type, input_data, f"Job_{job_id}", job_id,
                    use_msa=use_msa, use_potentials=use_potentials
                )
                
                # Update job with results
                self.job_manager.update_job_status(
                    job_id, JobStatus.COMPLETED.value, result
                )
                
                logger.info(f"✅ Individual job completed: {job_id}")
            else:
                logger.error(f"❌ Task registry not available for job {job_id}")
                self.job_manager.update_job_status(
                    job_id, JobStatus.FAILED.value, 
                    {'error': 'Task registry not available'}
                )
                
        except Exception as e:
            logger.error(f"❌ Individual job failed {job_id}: {e}")
            self.job_manager.update_job_status(
                job_id, JobStatus.FAILED.value,
                {'error': str(e)}
            )
    
    async def _execute_batch_job(self, batch_id: str):
        """Execute batch job with parallel child processing"""
        
        logger.info(f"🚀 Executing batch job: {batch_id}")
        
        try:
            # Update parent status to running
            self.job_manager.update_job_status(batch_id, JobStatus.RUNNING.value)
            
            # Get parent job to find children
            parent_job = self.job_manager.get_job(batch_id)
            if not parent_job:
                logger.error(f"❌ Parent job not found: {batch_id}")
                return
            
            # Get child IDs
            child_ids = parent_job.get('batch_child_ids', [])
            if not child_ids:
                logger.error(f"❌ No child jobs found for batch: {batch_id}")
                return
            
            logger.info(f"🔄 Processing {len(child_ids)} child jobs")
            
            # Process children with controlled parallelism
            semaphore = asyncio.Semaphore(5)  # Max 5 concurrent executions
            
            async def process_child(child_id: str):
                async with semaphore:
                    await self._execute_batch_child(child_id, batch_id)
            
            # Execute all children
            child_tasks = [process_child(child_id) for child_id in child_ids]
            await asyncio.gather(*child_tasks, return_exceptions=True)
            
            # Update parent status based on children
            await self._finalize_batch_job(batch_id)
            
            logger.info(f"✅ Batch job completed: {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Batch job failed {batch_id}: {e}")
            self.job_manager.update_job_status(
                batch_id, JobStatus.FAILED.value,
                {'error': str(e)}
            )
    
    async def _execute_batch_child(self, child_id: str, parent_id: str):
        """Execute a single batch child job"""
        
        try:
            # Get child job data
            child_job = self.job_manager.get_job(child_id)
            if not child_job:
                logger.error(f"❌ Child job not found: {child_id}")
                return
            
            # Extract execution parameters
            input_data = child_job.get('input_data', {})
            
            # Execute using existing task handler
            await self._execute_individual_job(
                child_id, 
                TaskType.PROTEIN_LIGAND_BINDING.value,
                input_data,
                use_msa=True,
                use_potentials=False
            )
            
            # Update parent progress
            await self._update_batch_progress(parent_id)
            
        except Exception as e:
            logger.error(f"❌ Batch child failed {child_id}: {e}")
            self.job_manager.update_job_status(
                child_id, JobStatus.FAILED.value,
                {'error': str(e)}
            )
            await self._update_batch_progress(parent_id)
    
    async def _update_batch_progress(self, batch_id: str):
        """Update batch parent progress based on children status"""
        
        try:
            # Get all children
            parent_job = self.job_manager.get_job(batch_id)
            child_ids = parent_job.get('batch_child_ids', [])
            
            if not child_ids:
                return
            
            # Get children status
            child_statuses = []
            for child_id in child_ids:
                child = self.job_manager.get_job(child_id)
                if child:
                    status_str = child.get('status', 'pending')
                    try:
                        child_statuses.append(JobStatus(status_str))
                    except ValueError:
                        child_statuses.append(JobStatus.PENDING)
            
            # Calculate progress using enhanced model
            dummy_parent = EnhancedJobData(
                id=batch_id, name="", job_type=JobType.BATCH_PARENT,
                task_type="", status=JobStatus.RUNNING, created_at=time.time()
            )
            
            progress = dummy_parent.calculate_batch_progress(child_statuses)
            
            # Update parent with progress
            self.job_manager.update_job_status(
                batch_id, JobStatus.RUNNING.value, 
                {'batch_progress': progress}
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to update batch progress {batch_id}: {e}")
    
    async def _finalize_batch_job(self, batch_id: str):
        """Finalize batch job based on children completion"""
        
        try:
            parent_job = self.job_manager.get_job(batch_id)
            child_ids = parent_job.get('batch_child_ids', [])
            
            # Get final children status
            child_statuses = []
            results = []
            
            for child_id in child_ids:
                child = self.job_manager.get_job(child_id)
                if child:
                    status_str = child.get('status', 'pending')
                    try:
                        child_statuses.append(JobStatus(status_str))
                    except ValueError:
                        child_statuses.append(JobStatus.FAILED)
                    
                    # Collect results
                    if child.get('output_data'):
                        results.append({
                            'child_id': child_id,
                            'result': child['output_data']
                        })
            
            # Determine final status
            if not child_statuses:
                final_status = JobStatus.FAILED
            else:
                dummy_parent = EnhancedJobData(
                    id=batch_id, name="", job_type=JobType.BATCH_PARENT,
                    task_type="", status=JobStatus.RUNNING, created_at=time.time()
                )
                
                if dummy_parent.is_batch_complete(child_statuses):
                    # Check if any succeeded
                    has_success = JobStatus.COMPLETED in child_statuses
                    final_status = JobStatus.COMPLETED if has_success else JobStatus.FAILED
                else:
                    final_status = JobStatus.RUNNING  # Still in progress
            
            # Update parent with final status
            final_data = {
                'child_results': results,
                'final_progress': dummy_parent.calculate_batch_progress(child_statuses)
            }
            
            self.job_manager.update_job_status(
                batch_id, final_status.value, final_data
            )
            
            logger.info(f"✅ Batch job finalized: {batch_id} -> {final_status.value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to finalize batch job {batch_id}: {e}")
    
    def _estimate_completion_time(self, task_type: str) -> int:
        """Estimate completion time in seconds based on task type"""
        
        estimates = {
            TaskType.PROTEIN_LIGAND_BINDING.value: 60,
            TaskType.PROTEIN_STRUCTURE.value: 120,
            TaskType.PROTEIN_COMPLEX.value: 180,
            TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value: 300,  # Will be overridden for actual batch size
            TaskType.NANOBODY_DESIGN.value: 240,
            TaskType.CDR_OPTIMIZATION.value: 180,
        }
        
        return estimates.get(task_type, 60)

# Global instance
smart_job_router = SmartJobRouter()