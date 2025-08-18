#!/usr/bin/env python3
"""
Streamlined Batch Processing Service
Handles batch jobs efficiently with proper Modal integration
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from database.unified_job_manager import unified_job_manager
from tasks.task_handlers import task_handler_registry
from services.batch_relationship_manager import batch_relationship_manager

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Streamlined batch processor for protein-ligand screening"""
    
    def __init__(self):
        self.active_batches = {}
        
    async def submit_batch(self, batch_job_id: str, protein_sequence: str, 
                          ligands: List[Dict], job_name: str, 
                          protein_name: str, use_msa: bool = True, 
                          use_potentials: bool = False) -> Dict[str, Any]:
        """Submit batch job and return immediately"""
        
        logger.info(f"🚀 Starting batch submission: {batch_job_id}")
        logger.info(f"   Protein sequence length: {len(protein_sequence)}")
        logger.info(f"   Number of ligands: {len(ligands)}")
        logger.info(f"   Ligands data: {ligands}")
        
        # Validate inputs
        if not protein_sequence:
            raise ValueError("Protein sequence is required")
        if not protein_name or not protein_name.strip():
            raise ValueError("Protein name is required and cannot be empty")
        if not ligands or len(ligands) == 0:
            logger.error(f"❌ Ligands validation failed: ligands={ligands}, len={len(ligands) if ligands else 'None'}")
            raise ValueError("At least one ligand is required")
        if len(ligands) > 1500:  # Updated limit to match system capabilities
            raise ValueError(f"Too many ligands: {len(ligands)}. Maximum 1500 per batch.")
        
        # Create batch tracking record
        batch_data = {
            'batch_id': batch_job_id,
            'total_ligands': len(ligands),
            'submitted_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'individual_job_ids': [],
            'status': 'processing',
            'start_time': time.time()
        }
        
        # Check if main batch job already exists (it may have been created by the predict endpoint)
        existing_job = unified_job_manager.get_job(batch_job_id)
        
        if not existing_job:
            # Create main batch job record in database
            main_batch_job = {
                'id': batch_job_id,
                'name': job_name,
                'type': 'batch_protein_ligand_screening',
                'job_type': 'batch_parent',  # Ensure parent is marked correctly
                'status': 'processing',
                'model_name': 'boltz2',
                'input_data': {
                    'protein_sequence': protein_sequence,
                    'ligands': ligands,
                    'total_ligands': len(ligands)
                },
                'created_at': time.time()
            }
            
            unified_job_manager.create_job(main_batch_job)
            logger.info(f"📝 Created new batch job: {batch_job_id}")
        else:
            logger.info(f"📝 Using existing batch job: {batch_job_id}")
            # Update the existing job with batch processing status
            unified_job_manager.update_job_status(batch_job_id, "running", {
                'protein_sequence': protein_sequence,
                'ligands': ligands,
                'total_ligands': len(ligands),
                'job_type': 'batch_parent'  # Ensure parent is properly marked
            })
        
        # Store in memory for tracking
        self.active_batches[batch_job_id] = batch_data
        
        # Create batch structure in relationship manager
        batch_metadata = {
            'job_name': job_name,
            'protein_name': protein_name,
            'protein_sequence': protein_sequence,
            'total_ligands': len(ligands),
            'use_msa': use_msa,
            'use_potentials': use_potentials,
            'ligands_info': [{'name': l.get('name'), 'smiles': l.get('smiles')} for l in ligands]
        }
        asyncio.create_task(batch_relationship_manager.create_batch_structure(batch_job_id, batch_metadata))
        
        # Start async processing
        asyncio.create_task(self._process_batch_async(
            batch_job_id, protein_sequence, ligands, job_name, use_msa, use_potentials, protein_name
        ))
        
        return {
            'batch_id': batch_job_id,
            'status': 'processing',
            'message': f'Batch submitted. Processing {len(ligands)} ligands.',
            'total_ligands': len(ligands),
            'estimated_time': len(ligands) * 30
        }
    
    async def _process_batch_async(self, batch_job_id: str, protein_sequence: str,
                                  ligands: List[Dict], job_name: str, 
                                  use_msa: bool, use_potentials: bool,
                                  protein_name: str):
        """Process batch in true background"""
        
        logger.info(f"🔄 Processing batch async: {batch_job_id}")
        
        try:
            batch_data = self.active_batches[batch_job_id]
            
            # Submit individual jobs to Modal (efficiently)
            modal_jobs = []
            for idx, ligand in enumerate(ligands):
                try:
                    individual_job_id = str(uuid.uuid4())
                    ligand_name = ligand.get('name', f'Ligand_{idx+1}')
                    ligand_smiles = ligand.get('smiles', '')
                    
                    # Create streamlined job record BEFORE submitting to Modal
                    job_data = {
                        'name': f"{job_name} - {ligand_name}",
                        'type': 'protein_ligand_binding',
                        'job_type': 'batch_child',  # Mark as batch child
                        'batch_parent_id': batch_job_id,  # Top-level parent reference
                        'batch_index': idx,  # Top-level batch index
                        'status': 'pending',  # Start as pending
                        'model_name': 'boltz2',
                        'input_data': {
                            'task_type': 'protein_ligand_binding',  # Add task_type for Monitor processing
                            'job_name': job_name,  # Store original job name for file naming
                            'protein_name': protein_name,  # Store protein name for file naming
                            'protein_sequence': protein_sequence,
                            'ligand_smiles': ligand_smiles,
                            'ligand_name': ligand_name
                        },
                        'created_at': time.time()
                    }
                    
                    # Create job record FIRST and get the actual job ID
                    actual_job_id = unified_job_manager.create_job(job_data)
                    if not actual_job_id:
                        logger.error(f"❌ Failed to create job for ligand {ligand_name}")
                        batch_data['failed_jobs'] += 1
                        continue
                    
                    # Update job ID to use the actual database ID
                    individual_job_id = actual_job_id
                    
                    # Create streamlined job data for Modal with correct job ID
                    modal_job_data = {
                        'job_id': individual_job_id,  # Use actual DB ID
                        'protein_sequence': protein_sequence,
                        'ligand_smiles': ligand_smiles,
                        'ligand_name': ligand_name,
                        'protein_name': protein_name,  # Add protein_name
                        'use_msa_server': use_msa,
                        'use_potentials': use_potentials
                    }
                    
                    # Register child job with batch relationship manager
                    child_metadata = {
                        'task_type': 'protein_ligand_binding',
                        'ligand_name': ligand_name,
                        'ligand_smiles': ligand_smiles,
                        'batch_index': idx,
                        'protein_name': protein_name
                    }
                    await batch_relationship_manager.register_child_job(batch_job_id, individual_job_id, child_metadata)
                    
                    # Submit to Modal efficiently (single call per ligand)
                    modal_call = await self._submit_single_modal_job(modal_job_data)
                    
                    if modal_call and modal_call.get('modal_call_id'):
                        # Update job with Modal call ID
                        unified_job_manager.update_job_status(individual_job_id, "running", {
                            'modal_call_id': modal_call['modal_call_id']
                        })
                        
                        modal_jobs.append({
                            'job_id': individual_job_id,
                            'modal_call_id': modal_call['modal_call_id'],
                            'ligand_name': ligand_name,
                            'status': 'running'
                        })
                        
                        batch_data['individual_job_ids'].append(individual_job_id)
                        batch_data['submitted_jobs'] += 1
                        
                        logger.info(f"✅ Submitted Modal job: {individual_job_id} -> {modal_call['modal_call_id']}")
                        
                    else:
                        logger.error(f"❌ Failed to submit Modal job for {ligand_name}")
                        batch_data['failed_jobs'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing ligand {idx}: {str(e)}")
                    batch_data['failed_jobs'] += 1
            
            # Update batch job with submitted jobs info
            batch_result = {
                'status': 'running',
                'total_ligands': len(ligands),
                'submitted_jobs': batch_data['submitted_jobs'],
                'failed_jobs': batch_data['failed_jobs'],
                'individual_job_ids': batch_data['individual_job_ids'],
                'modal_jobs': modal_jobs
            }
            
            unified_job_manager.update_job_status(batch_job_id, "running", batch_result)
            
            logger.info(f"✅ Batch processing initiated: {batch_job_id}")
            logger.info(f"   Submitted: {batch_data['submitted_jobs']}/{len(ligands)}")
            logger.info(f"   Failed: {batch_data['failed_jobs']}")
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {batch_job_id} - {str(e)}")
            unified_job_manager.update_job_status(batch_job_id, "failed", {"error": str(e)})
            
            # Clean up tracking
            if batch_job_id in self.active_batches:
                del self.active_batches[batch_job_id]
    
    async def _submit_single_modal_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Submit single job to Modal efficiently"""
        
        try:
            # Use task handler to submit to Modal
            result = await task_handler_registry.process_task(
                task_type='protein_ligand_binding',
                input_data={
                    'protein_sequence': job_data['protein_sequence'],
                    'ligand_smiles': job_data['ligand_smiles'],
                    'protein_name': job_data.get('protein_name', 'Target Protein')  # Add protein_name
                },
                job_name=f"Batch Job - {job_data['ligand_name']}",
                job_id=job_data['job_id'],
                use_msa=job_data['use_msa_server'],
                use_potentials=job_data['use_potentials']
            )
            
            # Return Modal call ID if successful
            if result and result.get('modal_call_id'):
                return {
                    'modal_call_id': result['modal_call_id'],
                    'status': 'submitted'
                }
            else:
                logger.error(f"No Modal call ID returned for job: {job_data['job_id']}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to submit Modal job: {str(e)}")
            return None
    
    async def get_batch_status(self, batch_job_id: str) -> Dict[str, Any]:
        """Get comprehensive batch status"""
        
        try:
            # Get batch job from database
            batch_job = unified_job_manager.get_job(batch_job_id)
            if not batch_job:
                raise ValueError(f"Batch job not found: {batch_job_id}")
            
            # Get individual jobs by searching for parent_batch_id in input_data
            all_jobs = await unified_job_manager.get_all_jobs(limit=200)
            individual_jobs = [
                job for job in all_jobs 
                if job.get('input_data', {}).get('parent_batch_id') == batch_job_id
            ]
            
            # Sort by batch_index NUMERICALLY to preserve original order (fix sorting issue)
            individual_jobs.sort(key=lambda j: int(j.get('input_data', {}).get('batch_index', 999)))
            
            # Process individual jobs to ensure proper data structure
            processed_jobs = []
            for job in individual_jobs:
                input_data = job.get('input_data', {})
                results = job.get('results', {}) or job.get('output_data', {})
                
                # Ensure proper data structure for frontend consumption
                processed_job = {
                    'id': job.get('id', ''),
                    'name': job.get('name', ''),
                    'status': job.get('status', 'unknown'),
                    'input_data': {
                        'ligand_name': input_data.get('ligand_name', ''),
                        'ligand_smiles': input_data.get('ligand_smiles', ''),
                        'batch_index': int(input_data.get('batch_index', 0)),  # Ensure numeric
                        'protein_name': input_data.get('protein_name', ''),
                        'protein_sequence': input_data.get('protein_sequence', '')
                    },
                    'results': self._normalize_results(results),  # Normalize result structure
                    'output_data': self._normalize_results(results)  # Duplicate for compatibility
                }
                processed_jobs.append(processed_job)
            
            # Calculate progress
            total_jobs = len(processed_jobs)
            completed_jobs = len([j for j in processed_jobs if j.get('status') == 'completed'])
            failed_jobs = len([j for j in processed_jobs if j.get('status') == 'failed'])
            running_jobs = len([j for j in processed_jobs if j.get('status') == 'running'])
            
            # Determine overall status
            if completed_jobs + failed_jobs == total_jobs:
                overall_status = 'completed' if failed_jobs == 0 else 'partially_completed'
            elif total_jobs == 0:
                overall_status = 'pending'
            else:
                overall_status = 'running'
            
            return {
                'batch_id': batch_job_id,
                'status': overall_status,
                'progress': {
                    'total': total_jobs,
                    'completed': completed_jobs,
                    'failed': failed_jobs,
                    'running': running_jobs,
                    'progress_percent': int((completed_jobs / total_jobs) * 100) if total_jobs > 0 else 0
                },
                # Add batch_summary for frontend compatibility
                'batch_summary': {
                    'total_ligands': total_jobs,
                    'completed_jobs': completed_jobs,
                    'failed_jobs': failed_jobs,
                    'execution_time': self._calculate_total_execution_time(processed_jobs)
                },
                'individual_jobs': processed_jobs,  # Return processed jobs with correct structure
                'estimated_completion': self._estimate_completion_time(running_jobs)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch status: {str(e)}")
            return {
                'batch_id': batch_job_id,
                'status': 'error',
                'error': str(e),
                'individual_jobs': []
            }
    
    def _normalize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize result structure to ensure consistent field mapping"""
        if not results:
            return {}
        
        # Extract key metrics with proper field mapping and fallbacks
        affinity = results.get('affinity') or results.get('binding_score') or results.get('affinity_pred_value')
        confidence = results.get('confidence') or results.get('confidence_score')
        ptm_score = results.get('ptm_score') or results.get('ptm')
        
        normalized = {
            'affinity': affinity,  # Main affinity score with fallbacks
            'confidence': confidence,  # Main confidence score with fallbacks
            'ptm_score': ptm_score,  # PTM score with fallback
            'execution_time': results.get('execution_time'),
            
            # Additional confidence metrics
            'confidence_score': results.get('confidence_score') or results.get('confidence'),
            'iptm_score': results.get('iptm_score') or results.get('iptm'),
            'plddt_score': results.get('plddt_score') or results.get('plddt'),
            
            # Structure information
            'structure_file_content': results.get('structure_file_content'),
            'structure_file_base64': results.get('structure_file_base64'),
            
            # Raw results for debugging
            '_raw_results': results
        }
        
        # Remove None values to keep structure clean
        return {k: v for k, v in normalized.items() if v is not None}
    
    def _calculate_total_execution_time(self, jobs: List[Dict[str, Any]]) -> float:
        """Calculate total execution time from completed jobs"""
        total_time = 0.0
        for job in jobs:
            if job.get('status') == 'completed':
                results = job.get('results', {})
                exec_time = results.get('execution_time')
                if exec_time:
                    total_time += float(exec_time)
        return total_time
    
    def _estimate_completion_time(self, running_jobs: int) -> int:
        """Estimate remaining completion time"""
        avg_job_time = 300  # 5 minutes per job estimate
        return running_jobs * avg_job_time
    
    def cleanup_completed_batch(self, batch_job_id: str):
        """Clean up completed batch from memory"""
        if batch_job_id in self.active_batches:
            del self.active_batches[batch_job_id]
            logger.info(f"🧹 Cleaned up batch: {batch_job_id}")

# Global instance
batch_processor = BatchProcessor()