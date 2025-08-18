"""
Batch File Scanner Service
Efficiently scans GCP storage for individual job result files to determine actual completion status
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

class BatchFileScanner:
    """Efficiently scans batch job files in GCP storage for real completion status"""
    
    def __init__(self):
        self.max_workers = 10  # Concurrent file checks
        
    async def scan_batch_files(self, batch_id: str, job_ids: List[str]) -> Dict[str, Any]:
        """
        Scan GCP storage files for a batch to determine actual completion status
        
        Returns:
        {
            'completed_jobs': [job_data_with_results],
            'failed_jobs': [job_id],
            'scan_summary': {
                'total_scanned': int,
                'files_found': int,
                'files_missing': int,
                'scan_time_ms': float
            }
        }
        """
        import time
        start_time = time.time()
        
        logger.info(f"🔍 Scanning {len(job_ids)} jobs for batch {batch_id}")
        
        # Check both possible storage locations
        storage_paths = [
            f"batches/{batch_id}/jobs/",  # New batch hierarchy
            f"jobs/"                      # Legacy individual jobs
        ]
        
        completed_jobs = []
        failed_jobs = []
        
        # Use ThreadPoolExecutor for concurrent file checks
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all file check tasks
            future_to_job = {}
            
            for job_id in job_ids:
                future = executor.submit(self._check_job_files, batch_id, job_id, storage_paths)
                future_to_job[future] = job_id
            
            # Process results as they complete
            for future in as_completed(future_to_job):
                job_id = future_to_job[future]
                try:
                    job_result = future.result()
                    if job_result:
                        completed_jobs.append(job_result)
                        logger.debug(f"✅ Found results for job {job_id[:8]}")
                    else:
                        failed_jobs.append(job_id)
                        logger.debug(f"❌ No results for job {job_id[:8]}")
                except Exception as e:
                    logger.error(f"❌ Error checking job {job_id[:8]}: {e}")
                    failed_jobs.append(job_id)
        
        scan_time = (time.time() - start_time) * 1000
        
        scan_summary = {
            'total_scanned': len(job_ids),
            'files_found': len(completed_jobs),
            'files_missing': len(failed_jobs),
            'scan_time_ms': round(scan_time, 2)
        }
        
        logger.info(f"📊 Scan complete: {len(completed_jobs)} completed, {len(failed_jobs)} failed in {scan_time:.0f}ms")
        
        return {
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'scan_summary': scan_summary
        }
    
    def _check_job_files(self, batch_id: str, job_id: str, storage_paths: List[str]) -> Optional[Dict[str, Any]]:
        """Check if job files exist and load results if found"""
        
        # Try each storage location
        for base_path in storage_paths:
            if base_path.startswith("batches/"):
                results_path = f"{base_path}{job_id}/results.json"
                metadata_path = f"{base_path}{job_id}/metadata.json"
            else:
                # Legacy path
                results_path = f"{base_path}{job_id}/results.json"
                metadata_path = f"{base_path}{job_id}/metadata.json"
            
            try:
                # Check for results.json
                results_data = gcp_storage_service.storage.download_file(results_path)
                if results_data:
                    # File exists - parse and return the data
                    if isinstance(results_data, bytes):
                        results_data = results_data.decode('utf-8')
                    
                    results = json.loads(results_data)
                    
                    # Also try to get metadata if available
                    metadata = {}
                    try:
                        metadata_data = gcp_storage_service.storage.download_file(metadata_path)
                        if metadata_data:
                            if isinstance(metadata_data, bytes):
                                metadata_data = metadata_data.decode('utf-8')
                            metadata = json.loads(metadata_data)
                    except:
                        pass  # Metadata is optional
                    
                    # Return combined job data
                    return {
                        'job_id': job_id,
                        'results': results,
                        'metadata': metadata,
                        'storage_path': results_path,
                        'has_results': True,
                        'status': 'completed'
                    }
                    
            except Exception as e:
                logger.debug(f"Path {results_path} not found: {e}")
                continue
        
        # No files found in any location
        return None
    
    async def reconstruct_batch_results_simple(self, batch_id: str, job_ids: List[str], input_data_map: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """
        Simple batch reconstruction: binary file check + data structure creation
        
        For each job:
        - If results.json exists in storage → load real data
        - If no file exists → create placeholder with zeros
        
        This ensures we always have a complete array/dataframe structure for frontend rendering
        """
        logger.info(f"🔧 Simple reconstruction for batch {batch_id} with {len(job_ids)} jobs")
        
        # Scan for files
        scan_results = await self.scan_batch_files(batch_id, job_ids)
        
        # Create file lookup for quick access
        results_by_job_id = {}
        for job_result in scan_results['completed_jobs']:
            results_by_job_id[job_result['job_id']] = job_result
        
        # Build complete results array
        complete_results = []
        
        for i, job_id in enumerate(job_ids):
            input_data = input_data_map.get(job_id, {})
            ligand_name = input_data.get('ligand_name', f"Ligand {i+1}")
            ligand_smiles = input_data.get('ligand_smiles', '')
            
            if job_id in results_by_job_id:
                # Real data exists - use comprehensive extraction
                job_file_data = results_by_job_id[job_id]
                
                # Create fake DB data for extraction function
                fake_db_data = {
                    'input_data': {
                        'ligand_name': ligand_name,
                        'ligand_smiles': ligand_smiles,
                        'batch_index': i + 1
                    }
                }
                
                # Use the comprehensive extraction function
                result_entry = self.extract_job_data_from_results(job_file_data, fake_db_data)
            else:
                # No file found - create placeholder with zeros
                result_entry = {
                    'job_id': job_id,
                    'ligand_name': ligand_name,
                    'ligand_smiles': ligand_smiles,
                    'affinity': 0.0,
                    'confidence': 0.0,
                    'ptm_score': 0.0,
                    'iptm_score': 0.0,
                    'plddt_score': 0.0,
                    'status': 'failed',
                    'has_structure': False,
                    'has_results': False,
                    'data_source': 'placeholder',
                    'storage_path': '',
                    'raw_modal_result': {},
                    'affinity_ensemble': {},
                    'confidence_metrics': {},
                }
            
            complete_results.append(result_entry)
        
        logger.info(f"✅ Reconstructed {len(complete_results)} total entries: {len(scan_results['completed_jobs'])} with data, {len(scan_results['failed_jobs'])} placeholders")
        
        return complete_results
    
    def _extract_affinity(self, results: Dict[str, Any]) -> float:
        """Extract affinity value from various possible locations"""
        # FIRST: Check raw_modal_result for the actual Modal execution results
        if 'raw_modal_result' in results and isinstance(results['raw_modal_result'], dict):
            raw_modal = results['raw_modal_result']
            if 'affinity' in raw_modal and isinstance(raw_modal['affinity'], (int, float)):
                return float(raw_modal['affinity'])
            if 'binding_affinity' in raw_modal and isinstance(raw_modal['binding_affinity'], (int, float)):
                return float(raw_modal['binding_affinity'])
        
        # FALLBACK: Try top-level fields
        for field in ['affinity', 'binding_affinity', 'affinity_ensemble']:
            if field in results:
                value = results[field]
                if isinstance(value, dict):
                    # Handle nested structures like affinity_ensemble.affinity
                    return value.get('affinity', 0.0)
                elif isinstance(value, (int, float)):
                    return float(value)
        return 0.0
    
    def _extract_confidence(self, results: Dict[str, Any]) -> float:
        """Extract confidence value from various possible locations"""
        # FIRST: Check raw_modal_result for the actual Modal execution results
        if 'raw_modal_result' in results and isinstance(results['raw_modal_result'], dict):
            raw_modal = results['raw_modal_result']
            if 'confidence' in raw_modal and isinstance(raw_modal['confidence'], (int, float)):
                return float(raw_modal['confidence'])
            if 'prediction_confidence' in raw_modal and isinstance(raw_modal['prediction_confidence'], (int, float)):
                return float(raw_modal['prediction_confidence'])
        
        # FALLBACK: Try top-level fields
        for field in ['confidence', 'prediction_confidence', 'confidence_score']:
            if field in results:
                value = results[field]
                if isinstance(value, dict):
                    # Handle nested structures
                    return value.get('overall_confidence', value.get('confidence', 0.0))
                elif isinstance(value, (int, float)):
                    return float(value)
        return 0.0

    def extract_job_data_from_results(self, job_result: Dict[str, Any], job_db_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format job data from file results and database info with comprehensive field extraction"""
        
        results = job_result.get('results', {})
        metadata = job_result.get('metadata', {})
        
        # Get input data from database
        input_data = job_db_data.get('input_data', {})
        ligand_name = input_data.get('ligand_name', 'Unknown')
        ligand_smiles = input_data.get('ligand_smiles', '')
        batch_index = input_data.get('batch_index', 0)
        
        # COMPREHENSIVE FIELD EXTRACTION from raw_modal_result
        raw_modal = results.get('raw_modal_result', results)
        
        # Primary affinity and confidence 
        affinity = self._extract_affinity(results)
        confidence = self._extract_confidence(results)
        
        # Extract comprehensive Modal result fields for table display
        # Core Boltz-2 metrics (use direct field names from examination)
        ptm_score = self._safe_float(raw_modal.get('ptm_score') or raw_modal.get('ptm') or raw_modal.get('PTM'))
        iptm_score = self._safe_float(raw_modal.get('iptm_score') or raw_modal.get('iptm') or raw_modal.get('iPTM'))
        plddt_score = self._safe_float(raw_modal.get('plddt_score') or raw_modal.get('plddt') or raw_modal.get('plDDT'))
        
        # Complex metrics from confidence_metrics dict  
        confidence_metrics = raw_modal.get('confidence_metrics', {})
        if isinstance(confidence_metrics, dict):
            # Dict format: {'confidence_score': 0.377, 'ptm': 0.266, 'iptm': 0.335, 'ligand_iptm': 0.335, 'protein_iptm': 0.0, 'complex_plddt': 0.387, 'complex_iplddt': 0.284, 'complex_pde': 4.19, 'complex_ipde': 12.06}
            ligand_iptm = self._safe_float(confidence_metrics.get('ligand_iptm'))       # Ligand iPTM
            complex_iplddt = self._safe_float(confidence_metrics.get('complex_iplddt')) # Complex ipLDDT  
            complex_ipde = self._safe_float(confidence_metrics.get('complex_ipde'))     # Complex iPDE
            complex_plddt = self._safe_float(confidence_metrics.get('complex_plddt'))   # Complex pLDDT
        else:
            # Fallback to direct field access
            ligand_iptm = self._safe_float(raw_modal.get('ligand_iptm_score') or raw_modal.get('ligand_iptm') or raw_modal.get('ligand_iPTM'))
            complex_iplddt = self._safe_float(raw_modal.get('complex_iplddt') or raw_modal.get('complex_plDDT'))
            complex_ipde = self._safe_float(raw_modal.get('complex_ipde') or raw_modal.get('complex_iPDE'))
            complex_plddt = plddt_score  # Use main plddt as fallback
        
        # Ensemble affinity data (multiple predictions)
        # Based on examination, affinity_ensemble is a dict with specific field names
        affinity_ensemble = raw_modal.get('affinity_ensemble', {})
        if isinstance(affinity_ensemble, dict):
            # Dict format: {'affinity_pred_value': 0.96, 'affinity_probability_binary': 0.36, 'affinity_pred_value1': 1.16, 'affinity_probability_binary1': 0.33, 'affinity_pred_value2': 0.76, 'affinity_probability_binary2': 0.39}
            ens_affinity = self._safe_float(affinity_ensemble.get('affinity_pred_value'))      # Primary ensemble affinity
            ens_prob = self._safe_float(affinity_ensemble.get('affinity_probability_binary'))  # Primary ensemble probability
            ens_aff_1 = self._safe_float(affinity_ensemble.get('affinity_pred_value1'))        # Ensemble affinity 1
            ens_prob_1 = self._safe_float(affinity_ensemble.get('affinity_probability_binary1'))  # Ensemble probability 1  
            ens_aff_2 = self._safe_float(affinity_ensemble.get('affinity_pred_value2'))        # Ensemble affinity 2
            ens_prob_2 = self._safe_float(affinity_ensemble.get('affinity_probability_binary2'))  # Ensemble probability 2
        else:
            # Fallback if format changes
            ens_affinity = None
            ens_prob = None
            ens_aff_1 = None
            ens_prob_1 = None
            ens_aff_2 = None
            ens_prob_2 = None
        
        # Affinity probability (key metric) - use the same field as in raw_modal_result
        affinity_prob = self._safe_float(raw_modal.get('affinity_probability') or 
                                       raw_modal.get('affinity_prob') or
                                       (affinity_ensemble.get('affinity_probability_binary') if isinstance(affinity_ensemble, dict) else None))
        
        # Check for structure file
        has_structure = bool(results.get('structure_file_base64') or 
                           results.get('structure_file_content') or
                           results.get('structure_data'))
        
        return {
            'job_id': job_result['job_id'],
            'ligand_name': ligand_name,
            'ligand_smiles': ligand_smiles,
            'affinity': affinity,
            'confidence': confidence,
            'status': 'completed',
            'has_structure': has_structure,
            'has_results': True,
            'batch_index': batch_index,
            
            # COMPREHENSIVE TABLE FIELDS
            'affinity_prob': affinity_prob,  # Affinity Prob
            'ens_affinity': ens_affinity,    # Ens. Affinity  
            'ens_prob': ens_prob,            # Ens. Prob
            'ens_aff_2': ens_aff_2,          # Ens. Aff 2
            'ens_prob_2': ens_prob_2,        # Ens. Prob 2
            'ens_aff_1': ens_aff_1,          # Ens. Aff 1
            'ens_prob_1': ens_prob_1,        # Ens. Prob 1
            'iptm_score': iptm_score,        # iPTM
            'ligand_iptm': ligand_iptm,      # Ligand iPTM
            'complex_iplddt': complex_iplddt, # Complex ipLDDT
            'complex_ipde': complex_ipde,    # Complex iPDE
            'complex_plddt': complex_plddt,  # Complex pLDDT (from confidence metrics)
            'ptm_score': ptm_score,          # PTM
            'plddt_score': plddt_score,      # For backward compatibility
            
            # Legacy field names for compatibility
            'ptm': ptm_score,
            'iptm': iptm_score,
            'plddt': plddt_score,
            
            # Timestamps from database
            'created_at': job_db_data.get('created_at'),
            'started_at': job_db_data.get('started_at'),
            'completed_at': job_db_data.get('completed_at'),
            'updated_at': job_db_data.get('updated_at'),
            
            # Include raw Modal data for compatibility
            'raw_modal_result': raw_modal,
            'affinity_ensemble': affinity_ensemble,
            'confidence_metrics': raw_modal.get('confidence_metrics', {}),
            'prediction_confidence': raw_modal.get('prediction_confidence', {}),
            'binding_affinity': raw_modal.get('binding_affinity', {}),
            'structure_file_base64': results.get('structure_file_base64'),
            
            # Result structure for backward compatibility
            'result': {
                'affinity': affinity,
                'confidence': confidence,
                'binding_score': affinity,
                'execution_time': results.get('execution_time', 0)
            },
            
            # Input data structure
            'input_data': {
                'ligand_name': ligand_name,
                'ligand_smiles': ligand_smiles,
                'batch_index': batch_index,
                'protein_sequence_name': input_data.get('protein_sequence_name', 'Unknown'),
                'task_type': 'protein_ligand_binding'
            }
        }
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float, return None if not convertible"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

# Global instance
batch_file_scanner = BatchFileScanner()