"""
Modal Job Monitoring Service

This service runs in the background to check Modal job completion
and automatically update job statuses in the database.
"""
import asyncio
import logging
import os
import json
import time
from typing import List, Dict, Any
from datetime import datetime

import modal

from database.unified_job_manager import unified_job_manager  # For job status/metadata using GCP
from services.gcp_storage_service import gcp_storage_service  # For file storage
from services.batch_relationship_manager import batch_relationship_manager  # For batch relationships

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModalJobMonitor:
    """Monitor Modal jobs and update database when they complete"""
    
    def __init__(self):
        # Set Modal auth
        os.environ['MODAL_TOKEN_ID'] = 'ak-4gwOEVs4hEAwy27Lf7b1Tz'
        os.environ['MODAL_TOKEN_SECRET'] = 'as-cauu6z3bil26giQmKgXdyQ'
        self.running = False
        
    async def start_monitoring(self, check_interval: int = 30):
        """Start the monitoring loop"""
        self.running = True
        logger.info(f"🚀 Starting Modal job monitor with {check_interval}s interval")
        
        while self.running:
            try:
                await self.check_running_jobs()
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(check_interval)
                
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("🛑 Stopping Modal job monitor")
        
    async def check_running_jobs(self):
        """Check all running jobs for completion and process pending batch jobs"""
        try:
            # Use targeted queries instead of getting all jobs to avoid timeout
            logger.info("🔍 Fetching running jobs for completion check...")
            running_jobs = unified_job_manager.get_jobs_by_status('running')
            
            logger.info("🔍 Fetching pending jobs for batch processing...")
            pending_jobs = unified_job_manager.get_jobs_by_status('pending')
            
            # Filter pending jobs for protein_ligand_binding tasks
            pending_batch_jobs = []
            for job in pending_jobs:
                if job.get('input_data', {}).get('task_type') == 'protein_ligand_binding':
                    pending_batch_jobs.append(job)
            
            # Check running jobs for completion
            if running_jobs:
                logger.info(f"🔍 Checking {len(running_jobs)} running jobs for completion")
                for job in running_jobs:
                    await self.check_job_completion(job)
            
            # Process pending batch jobs (limit to 5 concurrent to avoid overload)
            if pending_batch_jobs:
                logger.info(f"🚀 Found {len(pending_batch_jobs)} pending protein_ligand_binding jobs")
                logger.info(f"🚀 Processing {min(len(pending_batch_jobs), 5)} pending batch jobs")
                batch_jobs_to_process = pending_batch_jobs[:5]  # Limit concurrent processing
                
                for job in batch_jobs_to_process:
                    logger.info(f"🔄 Starting to process pending job: {job.get('id')}")
                    await self.process_pending_batch_job(job)
            else:
                logger.debug("ℹ️ No pending batch jobs found")
                
        except Exception as e:
            logger.error(f"❌ Error checking running jobs: {e}")
            
    async def check_job_completion(self, job: Dict[str, Any]):
        """Check if a specific job has completed on Modal"""
        try:
            if not job:
                logger.error("❌ Received None job in check_job_completion")
                return
                
            job_id = job.get('id')
            if not job_id:
                logger.error("❌ Job missing ID in check_job_completion")
                return
            
            # Look for modal_call_id in multiple possible locations
            modal_call_id = None
            
            # Check in results first
            results = job.get('results', {})
            if results:
                modal_call_id = results.get('modal_call_id')
            
            # Fallback to output_data
            if not modal_call_id:
                output_data = job.get('output_data', {})
                if output_data:
                    modal_call_id = output_data.get('modal_call_id')
            
            # Also check result_data (where unified_job_manager might store it)
            if not modal_call_id:
                result_data = job.get('result_data', {})
                if result_data:
                    modal_call_id = result_data.get('modal_call_id')
            
            # Check top-level modal_call_id
            if not modal_call_id:
                modal_call_id = job.get('modal_call_id')
                
            if not modal_call_id:
                # No Modal call ID found, skip this job
                logger.debug(f"🔍 No Modal call ID found for job {job_id}, skipping")
                return
                
            logger.debug(f"🔍 Checking Modal call {modal_call_id} for job {job_id}")
            
            # Check Modal job status
            modal_result = await self.get_modal_result(modal_call_id)
            
            if modal_result['status'] == 'completed':
                # Check if we already processed this job to avoid duplicates
                existing_results = job.get('results', {})
                if existing_results.get('files_stored_to_gcp'):
                    logger.debug(f"Job {job_id} already processed, skipping")
                    return
                logger.info(f"✅ Modal job completed for {job_id}, updating database and storing files")
                
                # Check if this is a batch child job
                input_data = job.get('input_data', {})
                parent_batch_id = input_data.get('parent_batch_id')
                
                if parent_batch_id:
                    # Store via batch relationship manager in standardized structure
                    success = await batch_relationship_manager.store_child_results(
                        parent_batch_id, job_id, modal_result['result'], job.get('type', 'unknown')
                    )
                    
                    # Also update batch progress in real-time (proactive tracking)
                    if success:
                        await batch_relationship_manager.update_batch_progress_realtime(
                            parent_batch_id, job_id, 'completed'
                        )
                else:
                    # Individual job (not part of batch) - store in flat structure
                    await gcp_storage_service.store_job_results(job_id, modal_result['result'], job.get('type', 'unknown'))
                
                # Store only lightweight metadata in Firestore (not full results)
                lightweight_result = {
                    'status': 'completed',
                    'completion_time': modal_result['result'].get('execution_time', 0),
                    'structure_available': bool(modal_result['result'].get('structure_file_base64')),
                    'affinity': modal_result['result'].get('affinity', 0),
                    'confidence': modal_result['result'].get('confidence', 0),
                    'files_stored_to_gcp': True,
                    'gcp_storage_path': f"jobs/{job_id}/",
                    'modal_call_id': modal_result['result'].get('modal_call_id')
                }
                
                unified_job_manager.update_job_status(
                    job_id, 
                    'completed',
                    lightweight_result
                )
                
                # CRITICAL FIX: Update batch parent progress if this is a batch child
                await self._update_batch_parent_progress_if_needed(job_id)
                
            elif modal_result['status'] == 'failed':
                logger.info(f"❌ Modal job failed for {job_id}, updating database")
                error_result = {
                    "error": modal_result.get('error', 'Modal job failed'),
                    "modal_error": True
                }
                unified_job_manager.update_job_status(
                    job_id,
                    'failed',
                    error_result
                )
                
                # CRITICAL FIX: Update batch parent progress if this is a batch child
                await self._update_batch_parent_progress_if_needed(job_id)
                
        except Exception as e:
            logger.error(f"❌ Error checking job {job.get('id')}: {e}")
    
    async def process_pending_batch_job(self, job: Dict[str, Any]):
        """Process a pending batch job by directly calling the task handler"""
        try:
            job_id = job.get('id')
            if not job_id:
                logger.error("❌ Job missing ID in process_pending_batch_job")
                return
            
            logger.info(f"🔄 Processing pending batch job: {job_id}")
            
            # Update job status to running
            unified_job_manager.update_job_status(job_id, "running")
            
            # Import task handler directly to avoid circular imports
            from tasks.task_handlers import task_handler_registry
            
            # Extract input data
            input_data = job.get('input_data', {})
            
            # For batch jobs, the data is directly in input_data, not nested
            if 'protein_sequence' in input_data and 'ligand_smiles' in input_data:
                # Batch job format: data directly in input_data
                task_input = {
                    'protein_sequence': input_data.get('protein_sequence'),
                    'ligand_smiles': input_data.get('ligand_smiles'),
                    'protein_name': input_data.get('protein_name', 'BatchProtein'),  # Add protein_name
                    'ligand_name': input_data.get('ligand_name', 'Unknown')  # Also add ligand_name
                }
            else:
                # Standard format: nested input_data
                task_input = input_data.get('input_data', {})
            
            logger.info(f"🔍 Task input for {job_id}: {task_input}")
            
            # Process task using task handler registry directly
            result = await task_handler_registry.process_task(
                task_type='protein_ligand_binding',
                input_data=task_input,
                job_name=input_data.get('job_name', f"Batch Job {job_id[:8]}"),
                job_id=job_id,
                use_msa=input_data.get('use_msa', True),
                use_potentials=input_data.get('use_potentials', False)
            )
            
            # Check if this is an async task (Modal prediction started)
            if result.get('status') == 'running' and result.get('modal_call_id'):
                # Update job with running status and Modal call ID for monitoring
                unified_job_manager.update_job_status(job_id, "running", result)
                logger.info(f"✅ Async batch job started, monitoring in background: {job_id}")
            else:
                # Synchronous task completed
                unified_job_manager.update_job_status(job_id, "completed", result)
                logger.info(f"✅ Batch job completed successfully: {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing pending batch job {job.get('id')}: {e}")
            # Mark job as failed
            try:
                error_result = {
                    'job_id': job.get('id'),
                    'status': 'failed',
                    'error': str(e),
                    'error_message': str(e)
                }
                unified_job_manager.update_job_status(
                    job.get('id'), 
                    'failed', 
                    error_result
                )
            except Exception as update_error:
                logger.error(f"❌ Failed to update job status: {update_error}")
    
    # DEPRECATED: Replaced by GCP storage service
    async def process_modal_result_files_DEPRECATED(self, job_id: str, modal_result: Dict[str, Any]):
        """Process and store files from Modal prediction results with user-friendly names"""
        try:
            logger.info(f"📁 Processing files for job {job_id}")
            
            # Get job data to generate user-friendly file names
            job_data = await unified_job_manager.get_job(job_id)
            if not job_data:
                logger.error(f"❌ Could not get job data for {job_id}")
                return
            
            # Generate user-friendly file names
            from services.file_naming import file_naming
            file_names = file_naming.generate_job_file_names(job_data)
            
            logger.info(f"📝 Generated file names for {job_id}: {list(file_names.values())}")
            
            files_stored = 0
            
            # Store structure files (CIF and PDB) with user-friendly names
            if modal_result.get('structure_file_content'):
                content = modal_result['structure_file_content']
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                success = unified_job_manager.upload_job_file(
                    job_id=job_id,
                    file_name=file_names['structure_cif'],
                    file_content=content,
                    file_type="cif",
                    content_type="chemical/x-cif"
                )
                if success:
                    files_stored += 1
                    logger.info(f"✅ Stored {file_names['structure_cif']} for job {job_id}")
            
            # Store PDB if available
            if modal_result.get('structure_pdb_content'):
                content = modal_result['structure_pdb_content']
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                success = unified_job_manager.upload_job_file(
                    job_id=job_id,
                    file_name=file_names['structure_pdb'],
                    file_content=content,
                    file_type="pdb",
                    content_type="chemical/x-pdb"
                )
                if success:
                    files_stored += 1
                    logger.info(f"✅ Stored {file_names['structure_pdb']} for job {job_id}")
            
            # Store log files if available
            if modal_result.get('log_content'):
                content = modal_result['log_content']
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                success = unified_job_manager.upload_job_file(
                    job_id=job_id,
                    file_name=file_names['prediction_log'],
                    file_content=content,
                    file_type="log",
                    content_type="text/plain"
                )
                if success:
                    files_stored += 1
                    logger.info(f"✅ Stored {file_names['prediction_log']} for job {job_id}")
            
            # Store input.txt file with job parameters
            input_content = self._generate_input_file_content(job_data, modal_result)
            if input_content:
                success = unified_job_manager.upload_job_file(
                    job_id=job_id,
                    file_name=file_names['input_txt'],
                    file_content=input_content.encode('utf-8'),
                    file_type="txt",
                    content_type="text/plain"
                )
                if success:
                    files_stored += 1
                    logger.info(f"✅ Stored {file_names['input_txt']} for job {job_id}")
            
            # Store structure.txt file with structure metadata
            if modal_result.get('structure_file_content'):
                structure_txt_content = self._generate_structure_txt_content(modal_result)
                if structure_txt_content:
                    success = unified_job_manager.upload_job_file(
                        job_id=job_id,
                        file_name=file_names['structure_txt'],
                        file_content=structure_txt_content.encode('utf-8'),
                        file_type="txt",
                        content_type="text/plain"
                    )
                    if success:
                        files_stored += 1
                        logger.info(f"✅ Stored {file_names['structure_txt']} for job {job_id}")
            
            # Store any other files from the result
            for key, value in modal_result.items():
                if key.endswith('_file') and key not in ['structure_file_content', 'structure_pdb_content', 'log_content']:
                    if isinstance(value, (str, bytes)):
                        content = value.encode('utf-8') if isinstance(value, str) else value
                        file_name = key.replace('_file', '') + '.txt'
                        
                        success = unified_job_manager.upload_job_file(
                            job_id=job_id,
                            file_name=file_name,
                            file_content=content,
                            file_type="txt",
                            content_type="text/plain"
                        )
                        if success:
                            files_stored += 1
                            logger.info(f"✅ Stored {file_name} for job {job_id}")
            
            logger.info(f"📊 Stored {files_stored} files for job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing files for job {job_id}: {e}")
    
    def _generate_input_file_content(self, job_data: Dict[str, Any], modal_result: Dict[str, Any]) -> str:
        """Generate content for input.txt file with job parameters"""
        
        input_data = job_data.get('input_data', {})
        
        content = f"""OMTX-Hub Prediction Job Input Parameters
==========================================

Job Information:
- Job ID: {job_data.get('id', 'unknown')}
- Job Name: {job_data.get('name', 'unknown')}
- Task Type: {input_data.get('task_type', 'unknown')}
- Model: {job_data.get('model_name', 'unknown')}
- Status: {job_data.get('status', 'unknown')}
- Created: {job_data.get('submitted', 'unknown')}

"""
        
        # Add batch information if applicable
        if input_data.get('parent_batch_id'):
            content += f"""Batch Information:
- Batch ID: {input_data.get('parent_batch_id')}
- Batch Index: {input_data.get('batch_index', 'unknown')}
- Ligand Name: {input_data.get('ligand_name', 'unknown')}

"""
        
        # Add protein information
        protein_sequence = input_data.get('protein_sequence', '')
        if protein_sequence:
            seq_length = len(protein_sequence.replace('\n', '').replace(' ', ''))
            content += f"""Protein Information:
- Sequence Length: {seq_length} amino acids
- Sequence:
{protein_sequence}

"""
        
        # Add ligand information
        ligand_smiles = input_data.get('ligand_smiles', '')
        if ligand_smiles:
            content += f"""Ligand Information:
- SMILES: {ligand_smiles}
- Name: {input_data.get('ligand_name', 'unknown')}

"""
        
        # Add prediction results summary
        if modal_result:
            content += f"""Prediction Results Summary:
- Affinity Score: {modal_result.get('affinity', 'N/A')}
- Confidence: {modal_result.get('confidence', 'N/A')}
- PTM Score: {modal_result.get('ptm_score', 'N/A')}
- Execution Time: {modal_result.get('execution_time', 'N/A')} seconds
- Modal Call ID: {modal_result.get('modal_call_id', 'N/A')}

"""
        
        content += f"""Generated by OMTX-Hub
https://github.com/om-therapeutics/omtx-hub
"""
        
        return content
    
    def _generate_structure_txt_content(self, modal_result: Dict[str, Any]) -> str:
        """Generate content for structure.txt file with structure metadata"""
        
        content = f"""OMTX-Hub Structure File Information
===================================

Structure Details:
- Format: CIF (Crystallographic Information File)
- Generated by: Boltz-2 Model
- Prediction Type: Protein-Ligand Complex

Confidence Metrics:
- Overall Confidence: {modal_result.get('confidence', 'N/A')}
- PTM Score: {modal_result.get('ptm_score', 'N/A')}
- PlDDT Score: {modal_result.get('plddt_score', 'N/A')}
- iPTM Score: {modal_result.get('iptm_score', 'N/A')}

Binding Analysis:
- Predicted Affinity: {modal_result.get('affinity', 'N/A')}
- Binding Probability: {modal_result.get('affinity_probability', 'N/A')}

"""
        
        # Add structure file information
        structure_content = modal_result.get('structure_file_content', '')
        if structure_content:
            # Count atoms in structure
            atom_count = structure_content.count('ATOM') + structure_content.count('HETATM')
            content += f"""Structure Statistics:
- Total Atoms: {atom_count}
- File Size: {len(structure_content)} characters

"""
        
        content += f"""Visualization:
- Compatible with: PyMOL, ChimeraX, VMD, and other molecular viewers
- Recommended viewer: OMTX-Hub built-in Molstar viewer

Generated by OMTX-Hub Boltz-2 Pipeline
"""
        
        return content
            
    async def get_modal_result(self, modal_call_id: str) -> Dict[str, Any]:
        """Get result from Modal call ID"""
        try:
            call = modal.FunctionCall.from_id(modal_call_id)
            result = call.get()
            return {
                'status': 'completed',
                'result': result
            }
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['still running', 'not finished', 'pending']):
                return {
                    'status': 'running',
                    'error': str(e)
                }
            else:
                return {
                    'status': 'failed', 
                    'error': str(e)
                }
    
    async def _update_batch_parent_progress_if_needed(self, job_id: str) -> None:
        """
        CRITICAL FIX: Update batch parent progress when child job status changes
        Senior Principal Engineer implementation for batch parent-child synchronization
        """
        try:
            # Get the child job to check if it's part of a batch
            child_job_data = unified_job_manager.get_job(job_id)
            if not child_job_data:
                return
            
            # Check if this job is a batch child (has batch_parent_id)
            batch_parent_id = child_job_data.get('batch_parent_id')
            if not batch_parent_id:
                # Also check legacy format in input_data
                input_data = child_job_data.get('input_data', {})
                batch_parent_id = input_data.get('parent_batch_id')
            
            if not batch_parent_id:
                # Not a batch child, nothing to update
                return
            
            logger.info(f"🔄 Updating batch parent {batch_parent_id} progress after child {job_id} completion")
            
            # Get the batch parent job
            parent_job_data = unified_job_manager.get_job(batch_parent_id)
            if not parent_job_data:
                logger.warning(f"⚠️ Batch parent {batch_parent_id} not found")
                return
            
            # Convert parent to enhanced job data for intelligent progress tracking
            from models.enhanced_job_model import EnhancedJobData
            
            parent_job = EnhancedJobData.from_job_data(parent_job_data)
            if not parent_job:
                logger.warning(f"⚠️ Batch parent {batch_parent_id} not in new format")
                return
            
            # Get all children of this batch parent
            from services.unified_job_storage import unified_job_storage
            children = await unified_job_storage.get_batch_children(
                batch_parent_id, 
                include_results=False
            )
            
            if not children:
                logger.warning(f"⚠️ No children found for batch parent {batch_parent_id}")
                return
            
            # Update parent with intelligent batch progress
            child_statuses = [child.status for child in children]
            parent_job.update_batch_progress(child_statuses, children)
            
            # Determine if batch is complete
            completed_count = len([child for child in children if child.status.value in ['completed', 'failed', 'cancelled']])
            is_batch_complete = completed_count >= len(children)
            
            # Update parent job status if batch is complete
            if is_batch_complete:
                success_count = len([child for child in children if child.status.value == 'completed'])
                if success_count > 0:
                    new_status = 'completed'
                    logger.info(f"✅ Batch {batch_parent_id} completed: {success_count}/{len(children)} successful")
                else:
                    new_status = 'failed'
                    logger.info(f"❌ Batch {batch_parent_id} failed: 0/{len(children)} successful")
                
                # Update parent job with completion status and intelligence
                parent_update = {
                    'status': new_status,
                    'batch_progress': parent_job.batch_progress,
                    'batch_metadata': parent_job.batch_metadata,
                    'batch_estimated_completion': parent_job.batch_estimated_completion,
                    'batch_completion_rate': parent_job.batch_completion_rate,
                    'completed_at': time.time() if new_status == 'completed' else None,
                    'updated_at': time.time()
                }
                
                unified_job_manager.update_job_status(batch_parent_id, new_status, parent_update)
                
            else:
                # Update parent with current progress (still running)
                parent_update = {
                    'batch_progress': parent_job.batch_progress,
                    'batch_metadata': parent_job.batch_metadata,
                    'batch_estimated_completion': parent_job.batch_estimated_completion,
                    'batch_completion_rate': parent_job.batch_completion_rate,
                    'updated_at': time.time()
                }
                
                unified_job_manager.update_job_status(batch_parent_id, 'running', parent_update)
                
                remaining = len(children) - completed_count
                logger.info(f"🔄 Batch {batch_parent_id} progress: {completed_count}/{len(children)} complete, {remaining} remaining")
            
        except Exception as e:
            logger.error(f"❌ Failed to update batch parent progress: {e}")
            # Don't let batch update failures crash individual job completion
            import traceback
            traceback.print_exc()

# Global monitor instance
modal_monitor = ModalJobMonitor()

async def start_modal_monitor():
    """Start the Modal monitoring service"""
    await modal_monitor.start_monitoring()
    
def stop_modal_monitor():
    """Stop the Modal monitoring service"""
    modal_monitor.stop_monitoring()