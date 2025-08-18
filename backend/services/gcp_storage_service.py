"""
GCP Storage Service for Modal Results
Stores all Modal prediction outputs directly to GCP bucket
"""

import json
import logging
import base64
from typing import Dict, Any, Optional
from datetime import datetime
from config.gcp_storage import gcp_storage

logger = logging.getLogger(__name__)

class GCPStorageService:
    """Service to store Modal results directly to GCP"""
    
    def __init__(self):
        self.storage = gcp_storage
    
    def _get_model_from_task_type(self, task_type: str) -> str:
        """Map task type to model name"""
        task_to_model = {
            'protein_ligand_binding': 'Boltz-2',
            'protein_structure': 'Boltz-2',
            'protein_complex': 'Boltz-2',
            'batch_protein_ligand_screening': 'Boltz-2',
            'binding_site_prediction': 'Boltz-2',
            'variant_comparison': 'Boltz-2',
            'drug_discovery': 'Boltz-2',
            'nanobody_design': 'RFAntibody',
            'cdr_optimization': 'RFAntibody',
            'epitope_targeted_design': 'RFAntibody',
            'antibody_de_novo_design': 'RFAntibody',
            'protein_protein_complex': 'Chai-1',
            'multimer_prediction': 'Chai-1'
        }
        
        # If unknown task type, try to infer from task name
        if task_type not in task_to_model:
            if 'antibody' in task_type.lower() or 'nanobody' in task_type.lower():
                return 'RFAntibody'
            elif 'complex' in task_type.lower() or 'multimer' in task_type.lower():
                return 'Chai-1'
            else:
                return 'Other'  # New models go here
        
        return task_to_model[task_type]
    
    def _get_task_folder_name(self, task_type: str) -> str:
        """Map task type to folder name"""
        task_to_folder = {
            'protein_ligand_binding': 'Protein-Ligand',
            'protein_structure': 'Protein-Structure',
            'protein_complex': 'Protein-Complex',
            'batch_protein_ligand_screening': 'Batch-Screen',
            'binding_site_prediction': 'Binding-Site',
            'variant_comparison': 'Variant-Comparison',
            'drug_discovery': 'Drug-Discovery',
            'nanobody_design': 'Nanobody-Design',
            'cdr_optimization': 'CDR-Optimization',
            'epitope_targeted_design': 'Epitope-Targeted',
            'antibody_de_novo_design': 'Antibody-DeNovo',
            'protein_protein_complex': 'Protein-Complex',
            'multimer_prediction': 'Multimer'
        }
        
        # If unknown, create folder name from task type
        if task_type not in task_to_folder:
            # Convert snake_case to Title-Case
            folder_name = '-'.join(word.capitalize() for word in task_type.split('_'))
            logger.info(f"📝 New task type '{task_type}' will be stored as '{folder_name}'")
            return folder_name
            
        return task_to_folder[task_type]
    
    async def store_job_results(self, job_id: str, results: Dict[str, Any], task_type: str) -> bool:
        """Store job results to GCP bucket in both locations"""
        
        if not self.storage.available:
            logger.error("❌ GCP Storage not available!")
            return False
        
        try:
            # Store in flat jobs directory for quick access
            jobs_path = f"jobs/{job_id}"
            
            # Also determine archive path
            model_name = self._get_model_from_task_type(task_type)
            task_folder = self._get_task_folder_name(task_type)
            archive_path = f"archive/{model_name}/{task_folder}/{job_id}"
            
            # Note: GCS doesn't require explicit directory creation
            # Directories are created automatically when files are uploaded
            logger.info(f"📁 Storing to: {jobs_path} and {archive_path}")
            
            # Store main results JSON in both locations
            results_json = json.dumps(results, indent=2)
            
            # Store in jobs directory
            success = self.storage.upload_file(
                f"{jobs_path}/results.json",
                results_json.encode('utf-8'),
                "application/json"
            )
            
            # Also store in archive
            self.storage.upload_file(
                f"{archive_path}/results.json",
                results_json.encode('utf-8'),
                "application/json"
            )
            
            # Store structure files if present
            if results.get('structure_file_base64'):
                try:
                    structure_content = base64.b64decode(results['structure_file_base64'])

                    # Store in jobs directory
                    self.storage.upload_file(
                        f"{jobs_path}/structure.cif",
                        structure_content,
                        "chemical/x-cif"
                    )

                    # Store in archive
                    self.storage.upload_file(
                        f"{archive_path}/structure.cif",
                        structure_content,
                        "chemical/x-cif"
                    )

                except Exception as e:
                    logger.error(f"❌ Failed to decode/store structure file for job {job_id}: {e}")
                    # Continue without structure file rather than failing entire operation
            
            # Store confidence data in both locations
            if results.get('confidence'):
                confidence_json = json.dumps(results['confidence'], indent=2)
                self.storage.upload_file(f"{jobs_path}/confidence.json", confidence_json.encode('utf-8'), "application/json")
                self.storage.upload_file(f"{archive_path}/confidence.json", confidence_json.encode('utf-8'), "application/json")
            
            # Store affinity data in both locations
            if results.get('affinity'):
                affinity_data = {
                    'affinity_pred_value': results.get('affinity'),
                    'affinity_probability_binary': results.get('affinity_probability', 0.0)
                }
                affinity_json = json.dumps(affinity_data, indent=2)
                self.storage.upload_file(f"{jobs_path}/affinity.json", affinity_json.encode('utf-8'), "application/json")
                self.storage.upload_file(f"{archive_path}/affinity.json", affinity_json.encode('utf-8'), "application/json")
            
            # For batch jobs, store individual results
            if task_type == 'batch_protein_ligand_screening':
                individual_results = results.get('individual_results', [])
                for idx, ind_result in enumerate(individual_results):
                    ind_job_id = ind_result.get('job_id', f"{job_id}_ligand_{idx}")
                    await self.store_job_results(ind_job_id, ind_result, 'protein_ligand_binding')
            
            # Store metadata with location info
            metadata = {
                'job_id': job_id,
                'task_type': task_type,
                'model': model_name,
                'task_folder': task_folder,
                'stored_at': datetime.utcnow().isoformat(),
                'file_count': len(results.get('all_structures', [])) + 3,
                'locations': {
                    'jobs': jobs_path,
                    'archive': archive_path
                },
                # Store basic job info for indexer
                'job_name': results.get('job_name', f'Job {job_id[:8]}'),
                'inputs': results.get('input_data', {}),
                'status': 'completed'
            }
            metadata_json = json.dumps(metadata, indent=2)
            self.storage.upload_file(f"{jobs_path}/metadata.json", metadata_json.encode('utf-8'), "application/json")
            self.storage.upload_file(f"{archive_path}/metadata.json", metadata_json.encode('utf-8'), "application/json")
            
            logger.info(f"✅ Stored job {job_id} to GCP: jobs/{job_id} and {archive_path}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to store results to GCP: {str(e)}")
            return False
    
    async def store_modal_output(self, job_id: str, modal_output: Dict[str, Any]) -> bool:
        """Store raw Modal output to GCP"""
        
        if not self.storage.available:
            return False
        
        try:
            # Store raw Modal output
            modal_json = json.dumps(modal_output, indent=2)
            success = self.storage.upload_file(
                f"jobs/{job_id}/modal_output.json",
                modal_json.encode('utf-8'),
                "application/json"
            )
            
            logger.info(f"✅ Stored Modal output for job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to store Modal output: {str(e)}")
            return False

# Global instance
gcp_storage_service = GCPStorageService()