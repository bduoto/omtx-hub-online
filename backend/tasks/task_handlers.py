"""
Task Handler Registry for OMTX-Hub
Handles all 6 prediction task types with proper routing and formatting
"""

import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from enum import Enum

from models.model_registry import PredictionTask, model_registry
from database.unified_job_manager import unified_job_manager  # For job status/metadata using GCP

logger = logging.getLogger(__name__)

def validate_smiles(smiles: str) -> bool:
    """Validate a SMILES string"""
    if not smiles or not smiles.strip():
        return False
    
    trimmed = smiles.strip()
    
    # Reject common invalid patterns
    if trimmed.count(' ') > 2:  # Likely descriptive text
        return False
    
    # Reject if it contains common English words that indicate it's not a SMILES
    invalid_words = ['and', 'or', 'the', 'of', 'in', 'with', 'to', 'from', 'test', 'frontend', 'backend', 'example', 'carbonic', 'anhydrase', 'acetazolamide']
    lower_case = trimmed.lower()
    for word in invalid_words:
        if word in lower_case:
            return False
    
    # Basic character validation
    import re
    valid_chars = re.compile(r'^[A-Za-z0-9\[\]()=#@+\-\\.\\/:]*$')
    if not valid_chars.match(trimmed):
        return False
    
    # Must contain at least one letter (element symbol)
    if not re.search(r'[A-Za-z]', trimmed):
        return False
    
    # Should not be too long (most SMILES are under 200 characters)
    if len(trimmed) > 300:
        return False
    
    return True

class TaskType(str, Enum):
    """Supported task types"""
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"
    BATCH_PROTEIN_LIGAND_SCREENING = "batch_protein_ligand_screening"
    # RFAntibody tasks
    NANOBODY_DESIGN = "nanobody_design"
    CDR_OPTIMIZATION = "cdr_optimization"
    EPITOPE_TARGETED_DESIGN = "epitope_targeted_design"
    ANTIBODY_DE_NOVO_DESIGN = "antibody_de_novo_design"

class TaskHandlerRegistry:
    """Registry for handling different prediction tasks"""
    
    def __init__(self):
        self.handlers = {
            TaskType.PROTEIN_LIGAND_BINDING: self.handle_protein_ligand_binding,
            TaskType.PROTEIN_STRUCTURE: self.handle_protein_structure,
            TaskType.PROTEIN_COMPLEX: self.handle_protein_complex,
            TaskType.BINDING_SITE_PREDICTION: self.handle_binding_site_prediction,
            TaskType.VARIANT_COMPARISON: self.handle_variant_comparison,
            TaskType.DRUG_DISCOVERY: self.handle_drug_discovery,
            TaskType.BATCH_PROTEIN_LIGAND_SCREENING: self.handle_batch_protein_ligand_screening,
            # RFAntibody handlers
            TaskType.NANOBODY_DESIGN: self.handle_nanobody_design,
            TaskType.CDR_OPTIMIZATION: self.handle_cdr_optimization,
            TaskType.EPITOPE_TARGETED_DESIGN: self.handle_epitope_targeted_design,
            TaskType.ANTIBODY_DE_NOVO_DESIGN: self.handle_antibody_de_novo_design,
        }
    
    async def process_task(self, task_type: str, input_data: Dict[str, Any], 
                          job_name: str, job_id: str, **kwargs) -> Dict[str, Any]:
        """Process task with appropriate handler"""
        
        if task_type not in self.handlers:
            raise ValueError(f"Unsupported task type: {task_type}")
        
        logger.info(f"🚀 Processing {task_type} task: {job_id}")
        
        try:
            # Validate inputs
            task_enum = TaskType(task_type)
            validation = self.validate_task_inputs(task_enum, input_data)
            
            if not validation['valid']:
                raise ValueError(f"Invalid inputs: {validation['errors']}")
            
            # Execute task
            handler = self.handlers[task_enum]
            result = await handler(input_data, job_name, job_id, **kwargs)
            
            logger.info(f"✅ Task completed: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Task failed: {job_id} - {str(e)}")
            raise
    
    def validate_task_inputs(self, task: TaskType, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate inputs for a specific task"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Task-specific validation
        if task == TaskType.PROTEIN_LIGAND_BINDING:
            if not inputs.get('protein_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("protein_sequence is required")
            
            ligand_smiles = inputs.get('ligand_smiles')
            if not ligand_smiles:
                validation_results["valid"] = False
                validation_results["errors"].append("ligand_smiles is required")
            elif not validate_smiles(ligand_smiles):
                validation_results["valid"] = False
                validation_results["errors"].append(f"Invalid SMILES string: '{ligand_smiles}'. Please provide a valid molecular SMILES notation.")
        
        elif task == TaskType.PROTEIN_STRUCTURE:
            if not inputs.get('protein_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("protein_sequence is required")
        
        elif task == TaskType.PROTEIN_COMPLEX:
            if not inputs.get('chain_a_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("chain_a_sequence is required")
            
            if not inputs.get('chain_b_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("chain_b_sequence is required")
        
        elif task == TaskType.BINDING_SITE_PREDICTION:
            if not inputs.get('protein_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("protein_sequence is required")
        
        elif task == TaskType.VARIANT_COMPARISON:
            if not inputs.get('wildtype_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("wildtype_sequence is required")
            
            if not inputs.get('variants') or len(inputs.get('variants', [])) == 0:
                validation_results["valid"] = False
                validation_results["errors"].append("At least one variant is required")
        
        elif task == TaskType.DRUG_DISCOVERY:
            if not inputs.get('protein_sequence'):
                validation_results["valid"] = False
                validation_results["errors"].append("protein_sequence is required")
            
            compound_library = inputs.get('compound_library', [])
            if not compound_library or len(compound_library) == 0:
                validation_results["valid"] = False
                validation_results["errors"].append("At least one compound is required")
            else:
                # Validate each compound SMILES in the library
                for i, compound in enumerate(compound_library):
                    if isinstance(compound, dict) and 'smiles' in compound:
                        smiles = compound['smiles']
                        if not validate_smiles(smiles):
                            validation_results["valid"] = False
                            validation_results["errors"].append(f"Invalid SMILES string in compound {i+1}: '{smiles}'. Please provide a valid molecular SMILES notation.")
                    elif isinstance(compound, str):
                        if not validate_smiles(compound):
                            validation_results["valid"] = False
                            validation_results["errors"].append(f"Invalid SMILES string in compound {i+1}: '{compound}'. Please provide a valid molecular SMILES notation.")
        
        return validation_results
    
    async def handle_protein_ligand_binding(self, input_data: Dict[str, Any], 
                                           job_name: str, job_id: str, 
                                           use_msa: bool = True, 
                                           use_potentials: bool = False) -> Dict[str, Any]:
        """Handle protein-ligand binding prediction"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        protein_name = input_data.get('protein_name', '')
        ligand_smiles = input_data.get('ligand_smiles', '')
        
        # Validate protein_name is provided
        if not protein_name or not protein_name.strip():
            raise ValueError("protein_name is required for protein-ligand binding tasks")
        
        logger.info(f"🧬 Protein-ligand binding: {job_id}")
        logger.info(f"   Protein length: {len(protein_sequence)}")
        logger.info(f"   Ligand: {ligand_smiles}")
        
        # Call Modal prediction
        result = await self.call_modal_prediction(
            protein_sequences=[protein_sequence],
            ligands=[ligand_smiles],
            use_msa_server=use_msa,
            use_potentials=use_potentials,
            job_id=job_id
        )
        
        # Check if this is a Modal spawn response (async prediction started)
        if result.get('status') == 'running' and result.get('modal_call_id'):
            logger.info(f"✅ Modal prediction started for {job_id}, will be monitored in background")
            # Return a running status - the background monitor will update when complete
            return {
                'job_id': job_id,
                'task_type': 'protein_ligand_binding',
                'status': 'running',
                'modal_call_id': result.get('modal_call_id'),
                'message': 'Modal prediction running in background',
                'execution_time': 0
            }
        
        # If we get here, it's a completed result (sync execution)
        # Format result for UI
        return self.format_binding_result(result, job_id)
    
    async def handle_protein_structure(self, input_data: Dict[str, Any], 
                                     job_name: str, job_id: str, 
                                     use_msa: bool = True, 
                                     use_potentials: bool = False) -> Dict[str, Any]:
        """Handle protein structure prediction"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        protein_name = input_data.get('protein_name', '')
        
        # Validate protein_name is provided
        if not protein_name or not protein_name.strip():
            raise ValueError("protein_name is required for protein structure prediction tasks")
        
        logger.info(f"🏗️ Protein structure: {job_id}")
        logger.info(f"   Protein length: {len(protein_sequence)}")
        
        # Use Boltz-2 for structure prediction (without ligand)
        result = await self.call_modal_prediction(
            protein_sequences=[protein_sequence],
            ligands=[],  # No ligands for structure prediction
            use_msa_server=use_msa,
            use_potentials=use_potentials,
            job_id=job_id
        )
        
        # Check if this is a Modal spawn response (async prediction started)
        if result.get('status') == 'running' and result.get('modal_call_id'):
            logger.info(f"✅ Modal prediction started for {job_id}, will be monitored in background")
            # Return a running status - the background monitor will update when complete
            return {
                'job_id': job_id,
                'task_type': 'protein_structure',
                'status': 'running',
                'modal_call_id': result.get('modal_call_id'),
                'message': 'Modal prediction running in background',
                'execution_time': 0
            }
        
        # If we get here, it's a completed result (sync execution)
        # Format result for UI
        return self.format_structure_result(result, job_id)
    
    async def handle_protein_complex(self, input_data: Dict[str, Any], 
                                   job_name: str, job_id: str, 
                                   use_msa: bool = True) -> Dict[str, Any]:
        """Handle protein complex prediction"""
        
        # Extract inputs
        chain_a_sequence = input_data.get('chain_a_sequence', '')
        chain_b_sequence = input_data.get('chain_b_sequence', '')
        
        logger.info(f"🔗 Protein complex: {job_id}")
        logger.info(f"   Chain A length: {len(chain_a_sequence)}")
        logger.info(f"   Chain B length: {len(chain_b_sequence)}")
        
        # Combine sequences for complex prediction
        combined_sequence = f"{chain_a_sequence}:{chain_b_sequence}"
        
        # Use Boltz-2 for complex prediction
        result = await self.call_modal_prediction(
            protein_sequences=[combined_sequence],
            ligands=[],  # No ligands for complex prediction
            use_msa_server=use_msa,
            use_potentials=False,
            job_id=job_id
        )
        
        # Format result for UI
        return self.format_complex_result(result, job_id)
    
    async def handle_binding_site_prediction(self, input_data: Dict[str, Any], 
                                           job_name: str, job_id: str) -> Dict[str, Any]:
        """Handle binding site prediction"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        
        logger.info(f"🎯 Binding site prediction: {job_id}")
        logger.info(f"   Protein length: {len(protein_sequence)}")
        
        # Use Boltz-2 to predict structure first, then analyze binding sites
        result = await self.call_modal_prediction(
            protein_sequences=[protein_sequence],
            ligands=[],  # No ligands for binding site prediction
            use_msa_server=True,
            use_potentials=False,
            job_id=job_id
        )
        
        # Format result for UI
        return self.format_binding_site_result(result, job_id)
    
    async def handle_variant_comparison(self, input_data: Dict[str, Any], 
                                      job_name: str, job_id: str) -> Dict[str, Any]:
        """Handle variant comparison"""
        
        # Extract inputs
        wildtype_sequence = input_data.get('wildtype_sequence', '')
        variants = input_data.get('variants', [])
        
        logger.info(f"🔬 Variant comparison: {job_id}")
        logger.info(f"   Wildtype length: {len(wildtype_sequence)}")
        logger.info(f"   Variants count: {len(variants)}")
        
        # Predict structures for wildtype and variants
        results = []
        
        # Wildtype structure
        logger.info(f"   Processing wildtype...")
        wt_result = await self.call_modal_prediction(
            protein_sequences=[wildtype_sequence],
            ligands=[],
            use_msa_server=True,
            use_potentials=False,
            job_id=f"{job_id}_wildtype"
        )
        
        results.append({'type': 'wildtype', 'result': wt_result})
        
        # Variant structures
        for i, variant in enumerate(variants):
            variant_sequence = variant.get('sequence', '')
            variant_name = variant.get('name', f'Variant_{i+1}')
            
            logger.info(f"   Processing variant: {variant_name}")
            variant_result = await self.call_modal_prediction(
                protein_sequences=[variant_sequence],
                ligands=[],
                use_msa_server=True,
                use_potentials=False,
                job_id=f"{job_id}_variant_{i}"
            )
            
            results.append({
                'type': 'variant', 
                'name': variant_name,
                'result': variant_result
            })
        
        # Format result for UI
        return self.format_variant_comparison_result(results, job_id)
    
    async def handle_drug_discovery(self, input_data: Dict[str, Any], 
                                  job_name: str, job_id: str) -> Dict[str, Any]:
        """Handle drug discovery workflow"""
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        compound_library = input_data.get('compound_library', [])
        
        logger.info(f"💊 Drug discovery: {job_id}")
        logger.info(f"   Protein length: {len(protein_sequence)}")
        logger.info(f"   Compound library size: {len(compound_library)}")
        
        # Screen compounds against protein
        results = []
        
        for i, compound in enumerate(compound_library):
            compound_smiles = compound.get('smiles', '')
            compound_name = compound.get('name', f'Compound_{i+1}')
            
            logger.info(f"   Screening compound: {compound_name}")
            result = await self.call_modal_prediction(
                protein_sequences=[protein_sequence],
                ligands=[compound_smiles],
                use_msa_server=True,
                use_potentials=False,
                job_id=f"{job_id}_compound_{i}"
            )
            
            results.append({
                'compound_name': compound_name,
                'smiles': compound_smiles,
                'result': result
            })
        
        # Format result for UI
        return self.format_drug_discovery_result(results, job_id)
    
    async def handle_batch_protein_ligand_screening(self, input_data: Dict[str, Any], 
                                                   job_name: str, job_id: str, **kwargs) -> Dict[str, Any]:
        """Handle batch protein-ligand screening using streamlined batch processor"""
        
        logger.info(f"🗂️ Starting streamlined batch screening: {job_id}")
        
        # Extract inputs
        protein_sequence = input_data.get('protein_sequence', '')
        protein_name = input_data.get('protein_name', '')
        ligands_data = input_data.get('ligands', [])
        use_msa = kwargs.get('use_msa', input_data.get('use_msa', True))
        use_potentials = kwargs.get('use_potentials', input_data.get('use_potentials', False))
        
        # Validate protein_name is provided
        if not protein_name or not protein_name.strip():
            raise ValueError("protein_name is required for batch screening")
        
        # Use Cloud Run batch processor
        from services.cloud_run_batch_processor import cloud_run_batch_processor as batch_processor
        
        try:
            result = await batch_processor.submit_batch(
                batch_job_id=job_id,
                protein_sequence=protein_sequence,
                ligands=ligands_data,
                job_name=job_name,
                protein_name=protein_name,
                use_msa=use_msa,
                use_potentials=use_potentials
            )
            
            return {
                'status': 'running',
                'batch_id': job_id,
                'message': result['message'],
                'progress': {
                    'total': result['total_ligands'],
                    'total_jobs': result['total_ligands'],
                    'completed': 0,
                    'failed': 0,
                    'running': result['total_ligands']
                },
                'estimated_completion_time': result['estimated_time']
            }
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'message': f'Batch processing failed: {str(e)}'
            }
    
    async def call_modal_prediction(self, protein_sequences: List[str], ligands: List[str], 
                                   use_msa_server: bool = True, use_potentials: bool = False,
                                   job_id: str = "") -> Dict[str, Any]:
        """Call Modal prediction with proper error handling"""
        
        try:
            # Use the new Modal execution service
            from services.modal_execution_service import modal_execution_service
            
            # Prepare parameters for Boltz-2 prediction
            parameters = {
                'protein_sequences': protein_sequences,
                'ligands': ligands,
                'use_msa_server': use_msa_server,
                'use_potentials': use_potentials
            }
            
            # Execute Boltz-2 prediction via Modal service
            result_data = await modal_execution_service.execute_prediction(
                model_type='boltz2',
                parameters=parameters,
                job_id=job_id
            )
            
            # Only store results to GCP if we have actual results (not async)
            if job_id and isinstance(result_data, dict) and result_data.get('structure_file_base64'):
                # This is a synchronous result with actual data - need to check if it's a batch job
                job_data = await unified_job_manager.get_job_async(job_id)  # Use async version
                logger.info(f"🔍 Checking if job {job_id} is a batch child...")
                
                # Check if this is a batch child job
                parent_batch_id = None
                if job_data:
                    parent_batch_id = job_data.get('input_data', {}).get('parent_batch_id')
                    logger.info(f"🔍 Job {job_id} data: parent_batch_id = {parent_batch_id}")
                
                if parent_batch_id:
                    # This is a batch child - use ModalJobStatusService for proper batch handling
                    logger.info(f"📦 Completed batch child job {job_id} (batch: {parent_batch_id}), processing via batch pipeline")
                    from services.modal_job_status_service import modal_job_status_service
                    success = await modal_job_status_service.process_completed_job(job_id, result_data)
                    if success:
                        logger.info(f"✅ Successfully processed batch child {job_id} via batch pipeline")
                    else:
                        logger.error(f"❌ Failed to process batch child {job_id} via batch pipeline")
                else:
                    # Regular individual job
                    logger.info(f"🔧 Processing individual job {job_id}")
                    from services.gcp_storage_service import gcp_storage_service
                    await gcp_storage_service.store_job_results(job_id, result_data, 'protein_ligand_binding')
            elif job_id and isinstance(result_data, dict) and result_data.get('status') == 'running':
                # This is an async job - results will be stored when Modal completes
                logger.info(f"🔄 Async job {job_id} started, results will be stored when complete")
            
            # Store Modal call ID in job for background monitoring (metadata only)
            if job_id and isinstance(result_data, dict):
                modal_call_id = result_data.get('modal_call_id')
                if modal_call_id:
                    # Update job with Modal call ID for monitoring (database metadata)
                    unified_job_manager.update_job_status(job_id, "running", {
                        "modal_call_id": modal_call_id,
                        "modal_function": "boltz2_predict_modal"
                    })
                    logger.info(f"📝 Stored Modal call ID {modal_call_id} for job {job_id}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"❌ Modal prediction failed for {job_id}: {str(e)}")
            raise
    
    def format_binding_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format binding prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'protein_ligand_binding',
            'status': 'completed',
            'affinity': result.get('affinity', 0.0),
            'affinity_probability': result.get('affinity_probability', 0.0),
            'affinity_ensemble': result.get('affinity_ensemble', {}),
            'confidence': result.get('confidence', 0.0),
            'confidence_metrics': result.get('confidence_metrics', {}),
            'ptm_score': result.get('ptm_score', 0.0),
            'iptm_score': result.get('iptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'ligand_iptm_score': result.get('ligand_iptm_score', 0.0),
            'protein_iptm_score': result.get('protein_iptm_score', 0.0),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'structure_files': result.get('structure_files', {}),
            'all_structures': result.get('all_structures', []),
            'structure_count': result.get('structure_count', 0),
            'execution_time': result.get('execution_time', 0),
            'prediction_id': result.get('prediction_id', job_id),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', []),
            'boltz_output': result.get('boltz_output', ''),
            'boltz_error': result.get('boltz_error', ''),
            'error': result.get('error', None)
        }
    
    def format_structure_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format structure prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'protein_structure',
            'status': 'completed',
            'confidence': result.get('confidence', 0.0),
            'confidence_metrics': result.get('confidence_metrics', {}),
            'ptm_score': result.get('ptm_score', 0.0),
            'iptm_score': result.get('iptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'structure_files': result.get('structure_files', {}),
            'all_structures': result.get('all_structures', []),
            'structure_count': result.get('structure_count', 0),
            'execution_time': result.get('execution_time', 0),
            'prediction_id': result.get('prediction_id', job_id),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', []),
            'boltz_output': result.get('boltz_output', ''),
            'boltz_error': result.get('boltz_error', ''),
            'error': result.get('error', None)
        }
    
    def format_complex_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format complex prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'protein_complex',
            'status': 'completed',
            'confidence': result.get('confidence', 0.0),
            'confidence_metrics': result.get('confidence_metrics', {}),
            'ptm_score': result.get('ptm_score', 0.0),
            'iptm_score': result.get('iptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'structure_files': result.get('structure_files', {}),
            'all_structures': result.get('all_structures', []),
            'structure_count': result.get('structure_count', 0),
            'execution_time': result.get('execution_time', 0),
            'prediction_id': result.get('prediction_id', job_id),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', []),
            'boltz_output': result.get('boltz_output', ''),
            'boltz_error': result.get('boltz_error', ''),
            'error': result.get('error', None)
        }
    
    def format_binding_site_result(self, result: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Format binding site prediction result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'binding_site_prediction',
            'status': 'completed',
            'confidence': result.get('confidence', 0.0),
            'confidence_metrics': result.get('confidence_metrics', {}),
            'ptm_score': result.get('ptm_score', 0.0),
            'iptm_score': result.get('iptm_score', 0.0),
            'plddt_score': result.get('plddt_score', 0.0),
            'binding_sites': result.get('binding_sites', []),
            'structure_file_base64': result.get('structure_file_base64', ''),
            'structure_file_content': result.get('structure_file_content', ''),
            'structure_files': result.get('structure_files', {}),
            'all_structures': result.get('all_structures', []),
            'structure_count': result.get('structure_count', 0),
            'execution_time': result.get('execution_time', 0),
            'prediction_id': result.get('prediction_id', job_id),
            'parameters': result.get('parameters', {}),
            'modal_logs': result.get('modal_logs', []),
            'boltz_output': result.get('boltz_output', ''),
            'boltz_error': result.get('boltz_error', ''),
            'error': result.get('error', None)
        }
    
    def format_variant_comparison_result(self, results: List[Dict[str, Any]], job_id: str) -> Dict[str, Any]:
        """Format variant comparison result for UI"""
        return {
            'job_id': job_id,
            'task_type': 'variant_comparison',
            'status': 'completed',
            'wildtype_result': next((r['result'] for r in results if r['type'] == 'wildtype'), {}),
            'variant_results': [r for r in results if r['type'] == 'variant'],
            'comparison_metrics': self.calculate_variant_metrics(results),
            'execution_time': sum(r.get('result', {}).get('execution_time', 0) for r in results),
            'prediction_id': job_id,
            'parameters': results[0].get('result', {}).get('parameters', {}) if results else {},
            'modal_logs': [],
            'boltz_output': '',
            'boltz_error': '',
            'error': None
        }
    
    def format_drug_discovery_result(self, results: List[Dict[str, Any]], job_id: str) -> Dict[str, Any]:
        """Format drug discovery result for UI"""
        # Sort by affinity
        sorted_results = sorted(results, key=lambda x: x.get('result', {}).get('affinity', 0), reverse=True)
        
        return {
            'job_id': job_id,
            'task_type': 'drug_discovery',
            'status': 'completed',
            'compound_results': sorted_results,
            'top_compounds': sorted_results[:10],  # Top 10 compounds
            'screening_summary': self.calculate_screening_metrics(results),
            'execution_time': sum(r.get('result', {}).get('execution_time', 0) for r in results),
            'prediction_id': job_id,
            'parameters': results[0].get('result', {}).get('parameters', {}) if results else {},
            'modal_logs': [],
            'boltz_output': '',
            'boltz_error': '',
            'error': None
        }
    
    def calculate_variant_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparison metrics for variants"""
        wildtype_result = next((r['result'] for r in results if r['type'] == 'wildtype'), {})
        variant_results = [r for r in results if r['type'] == 'variant']
        
        wt_confidence = wildtype_result.get('confidence', 0.0)
        
        stability_changes = []
        for variant in variant_results:
            variant_confidence = variant.get('result', {}).get('confidence', 0.0)
            stability_change = variant_confidence - wt_confidence
            stability_changes.append({
                'variant_name': variant.get('name', 'Unknown'),
                'stability_change': stability_change,
                'predicted_effect': 'stabilizing' if stability_change > 0 else 'destabilizing'
            })
        
        return {
            'stability_changes': stability_changes,
            'structural_differences': [],
            'functional_predictions': []
        }
    
    def calculate_screening_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate screening metrics for drug discovery"""
        affinities = [r.get('result', {}).get('affinity', 0) for r in results]
        
        return {
            'total_compounds': len(results),
            'hit_rate': len([a for a in affinities if a > 0.5]) / len(affinities) if affinities else 0,
            'best_affinity': max(affinities) if affinities else 0,
            'average_affinity': sum(affinities) / len(affinities) if affinities else 0,
            'compounds_above_threshold': len([a for a in affinities if a > 0.5]),
            'screening_efficiency': f"{len([a for a in affinities if a > 0.5])}/{len(affinities)}"
        }
    
    # RFAntibody handlers
    async def handle_nanobody_design(self, input_data: Dict[str, Any], 
                                   job_name: str, job_id: str, 
                                   use_msa: bool = True, 
                                   use_potentials: bool = False) -> Dict[str, Any]:
        """Handle nanobody design prediction using RFAntibody Modal"""
        
        # Validate target_name is provided
        target_name = input_data.get('target_name', '')
        if not target_name or not target_name.strip():
            raise ValueError("target_name is required for nanobody design tasks")
        
        logger.info(f"🧬 Processing nanobody design: {job_id}")
        logger.info(f"   Target name: {target_name}")
        logger.info(f"   Target PDB: {len(input_data.get('target_pdb_content', ''))} characters")
        logger.info(f"   Target chain: {input_data.get('target_chain')}")
        logger.info(f"   Hotspot residues: {input_data.get('hotspot_residues')}")
        logger.info(f"   Number of designs: {input_data.get('num_designs')}")
        logger.info(f"   Framework: {input_data.get('framework')}")
        
        try:
            # Use the new Modal execution service
            from services.modal_execution_service import modal_execution_service
            
            # Prepare parameters for RFAntibody prediction
            parameters = {
                'target_pdb_content': input_data.get('target_pdb_content', ''),
                'target_chain': input_data.get('target_chain', 'A'),
                'hotspot_residues': input_data.get('hotspot_residues', []),
                'num_designs': input_data.get('num_designs', 10),
                'framework': input_data.get('framework', 'vhh'),
                'job_id': job_id
            }
            
            # Execute RFAntibody prediction via Modal service
            result = await modal_execution_service.execute_prediction(
                model_type='rfantibody',
                parameters=parameters,
                job_id=job_id
            )
            
            logger.info(f"✅ RFAntibody nanobody design completed for {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ RFAntibody nanobody design failed for {job_id}: {str(e)}")
            raise
    
    async def handle_cdr_optimization(self, input_data: Dict[str, Any], 
                                    job_name: str, job_id: str, 
                                    use_msa: bool = True, 
                                    use_potentials: bool = False) -> Dict[str, Any]:
        """Handle CDR optimization - currently not implemented"""
        raise NotImplementedError("CDR optimization task is not yet implemented")
    
    async def handle_epitope_targeted_design(self, input_data: Dict[str, Any], 
                                           job_name: str, job_id: str, 
                                           use_msa: bool = True, 
                                           use_potentials: bool = False) -> Dict[str, Any]:
        """Handle epitope targeted design - currently not implemented"""
        raise NotImplementedError("Epitope targeted design task is not yet implemented")
    
    async def handle_antibody_de_novo_design(self, input_data: Dict[str, Any], 
                                           job_name: str, job_id: str, 
                                           use_msa: bool = True, 
                                           use_potentials: bool = False) -> Dict[str, Any]:
        """Handle antibody de novo design - currently not implemented"""
        raise NotImplementedError("Antibody de novo design task is not yet implemented")
    
    def get_supported_tasks(self) -> List[str]:
        """Get list of supported task types"""
        return list(self.handlers.keys())
    
    def get_task_description(self, task_type: str) -> str:
        """Get description for a task type"""
        descriptions = {
            TaskType.PROTEIN_LIGAND_BINDING: "Predict protein-ligand binding affinity and structure",
            TaskType.PROTEIN_STRUCTURE: "Predict protein structure from sequence",
            TaskType.PROTEIN_COMPLEX: "Predict protein complex structure",
            TaskType.BINDING_SITE_PREDICTION: "Predict binding sites on protein structure",
            TaskType.VARIANT_COMPARISON: "Compare wildtype and variant protein structures",
            TaskType.DRUG_DISCOVERY: "Screen compound library against protein target",
            # RFAntibody descriptions
            TaskType.NANOBODY_DESIGN: "Design nanobodies targeting specific epitopes",
            TaskType.CDR_OPTIMIZATION: "Optimize antibody CDR regions for better binding",
            TaskType.EPITOPE_TARGETED_DESIGN: "Design antibodies targeting specific epitopes",
            TaskType.ANTIBODY_DE_NOVO_DESIGN: "Design antibodies from scratch"
        }
        try:
            task_enum = TaskType(task_type)
            return descriptions.get(task_enum, "Unknown task type")
        except ValueError:
            return "Unknown task type"

# Global instance
task_handler_registry = TaskHandlerRegistry() 