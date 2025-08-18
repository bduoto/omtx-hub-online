"""
Batch Storage Fix API

Simple API endpoint to fix batch storage structure issues
"""

import json
import base64
import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

from services.gcp_storage_service import gcp_storage_service
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/fix-batch-storage/{batch_id}")
async def fix_batch_storage(batch_id: str):
    """Fix batch storage structure for a specific batch"""
    
    try:
        logger.info(f"🔧 Fixing batch storage for {batch_id}")
        
        # Get all jobs to find children
        all_jobs = await unified_job_manager.get_all_jobs(limit=1000)
        child_jobs = []
        
        for job in all_jobs:
            input_data = job.get('input_data', {})
            if input_data.get('parent_batch_id') == batch_id:
                child_jobs.append(job)
        
        if not child_jobs:
            raise HTTPException(status_code=404, detail=f"No child jobs found for batch {batch_id}")
        
        logger.info(f"Found {len(child_jobs)} child jobs for batch {batch_id}")
        
        # Fix each child job
        fixed_jobs = []
        for child_job in child_jobs:
            job_id = child_job.get('id')
            if child_job.get('status') == 'completed':
                success = await fix_child_job_storage(batch_id, job_id)
                if success:
                    fixed_jobs.append(job_id)
        
        # Create aggregated results if all jobs complete
        aggregated_created = False
        if len(fixed_jobs) == len([j for j in child_jobs if j.get('status') == 'completed']):
            aggregated_created = await create_aggregated_results(batch_id, fixed_jobs)
        
        return {
            "batch_id": batch_id,
            "total_child_jobs": len(child_jobs),
            "fixed_jobs": len(fixed_jobs),
            "fixed_job_ids": fixed_jobs,
            "aggregated_results_created": aggregated_created,
            "message": f"Fixed {len(fixed_jobs)} jobs for batch {batch_id}"
        }
        
    except Exception as e:
        logger.error(f"Error fixing batch storage for {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def fix_child_job_storage(batch_id: str, job_id: str) -> bool:
    """Fix storage for a single child job"""
    
    try:
        # Check if results.json exists
        results_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
        
        try:
            results_data = gcp_storage_service.storage.download_file(results_path)
            if isinstance(results_data, bytes):
                results_data = results_data.decode('utf-8')
            results = json.loads(results_data)
        except Exception as e:
            logger.warning(f"No results.json found for {job_id}: {e}")
            return False
        
        logger.info(f"Found results.json for {job_id}")
        
        # Create metadata.json if missing
        metadata_path = f"batches/{batch_id}/jobs/{job_id}/metadata.json"
        try:
            gcp_storage_service.storage.download_file(metadata_path)
            logger.info(f"metadata.json already exists for {job_id}")
        except:
            # Create metadata.json
            metadata = {
                'job_id': job_id,
                'batch_id': batch_id,
                'task_type': 'protein_ligand_binding',
                'model': 'boltz2',
                'stored_at': datetime.utcnow().isoformat(),
                'has_structure': bool(results.get('structure_file_base64')),
                'affinity': results.get('binding_affinity', {}).get('affinity', 0),
                'confidence': results.get('prediction_confidence', {}).get('confidence', 0),
                'ptm_score': results.get('structure_data', {}).get('ptm_score', 0),
                'plddt_score': results.get('structure_data', {}).get('plddt_score', 0),
                'iptm_score': results.get('structure_data', {}).get('iptm_score', 0),
                'execution_time': results.get('execution_time', 0),
                'modal_call_id': results.get('modal_call_id'),
                'ligand_name': results.get('ligand_name', 'Unknown'),
                'protein_name': results.get('protein_name', 'Unknown')
            }
            
            metadata_content = json.dumps(metadata, indent=2).encode('utf-8')
            gcp_storage_service.storage.upload_file(
                metadata_path, metadata_content, 'application/json'
            )
            logger.info(f"✅ Created metadata.json for {job_id}")
        
        # Create structure.cif if missing
        structure_path = f"batches/{batch_id}/jobs/{job_id}/structure.cif"
        try:
            gcp_storage_service.storage.download_file(structure_path)
            logger.info(f"structure.cif already exists for {job_id}")
        except:
            # Create structure.cif from base64
            if results.get('structure_file_base64'):
                try:
                    structure_content = base64.b64decode(results['structure_file_base64'])
                    gcp_storage_service.storage.upload_file(
                        structure_path, structure_content, 'chemical/x-cif'
                    )
                    logger.info(f"✅ Created structure.cif for {job_id}")
                except Exception as e:
                    logger.error(f"Failed to decode structure for {job_id}: {e}")
            else:
                logger.warning(f"No structure data found for {job_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing child job {job_id}: {e}")
        return False

async def create_aggregated_results(batch_id: str, job_ids: List[str]) -> bool:
    """Create aggregated results for completed batch"""
    
    try:
        aggregated_results = {
            'batch_id': batch_id,
            'created_at': datetime.utcnow().isoformat(),
            'total_jobs': len(job_ids),
            'completed_jobs': len(job_ids),
            'results': []
        }
        
        total_affinity = 0
        total_confidence = 0
        
        for job_id in job_ids:
            try:
                # Get job results
                results_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
                results_data = gcp_storage_service.storage.download_file(results_path)
                if isinstance(results_data, bytes):
                    results_data = results_data.decode('utf-8')
                results = json.loads(results_data)
                
                # Get metadata
                metadata_path = f"batches/{batch_id}/jobs/{job_id}/metadata.json"
                metadata_data = gcp_storage_service.storage.download_file(metadata_path)
                if isinstance(metadata_data, bytes):
                    metadata_data = metadata_data.decode('utf-8')
                metadata = json.loads(metadata_data)
                
                # Create comprehensive job summary with full Modal results
                job_summary = {
                    'job_id': job_id,
                    'ligand_name': metadata.get('ligand_name', 'Unknown'),
                    'protein_name': metadata.get('protein_name', 'Unknown'),
                    'task_type': metadata.get('task_type', 'protein_ligand_binding'),
                    'model': metadata.get('model', 'boltz2'),
                    'stored_at': metadata.get('stored_at'),
                    'has_structure': metadata.get('has_structure', False),
                    'execution_time': metadata.get('execution_time', 0),
                    'modal_call_id': metadata.get('modal_call_id'),
                    
                    # Core prediction metrics
                    'affinity': metadata.get('affinity', 0),
                    'confidence': metadata.get('confidence', 0),
                    'ptm_score': metadata.get('ptm_score', 0),
                    'plddt_score': metadata.get('plddt_score', 0),
                    'iptm_score': metadata.get('iptm_score', 0),
                    
                    # Include full Modal result data for comprehensive analysis
                    'raw_modal_result': results.get('raw_modal_result', {}),
                    
                    # Detailed prediction data
                    'structure_data': results.get('structure_data', {}),
                    'prediction_confidence': results.get('prediction_confidence', {}),
                    'binding_affinity': results.get('binding_affinity', {}),
                    
                    # Ensemble data if available
                    'affinity_ensemble': results.get('raw_modal_result', {}).get('affinity_ensemble', {}),
                    'confidence_metrics': results.get('raw_modal_result', {}).get('confidence_metrics', {}),
                }
                
                aggregated_results['results'].append(job_summary)
                
                total_affinity += metadata.get('affinity', 0)
                total_confidence += metadata.get('confidence', 0)
                
            except Exception as e:
                logger.error(f"Error processing job {job_id} for aggregation: {e}")
        
        # Calculate comprehensive summary statistics
        affinities = [r['affinity'] for r in aggregated_results['results'] if r['affinity']]
        confidences = [r['confidence'] for r in aggregated_results['results'] if r['confidence']]
        ptm_scores = [r['ptm_score'] for r in aggregated_results['results'] if r['ptm_score']]
        plddt_scores = [r['plddt_score'] for r in aggregated_results['results'] if r['plddt_score']]
        iptm_scores = [r['iptm_score'] for r in aggregated_results['results'] if r['iptm_score']]
        execution_times = [r['execution_time'] for r in aggregated_results['results'] if r['execution_time']]
        
        # Find best and worst performers
        best_result = max(aggregated_results['results'], key=lambda x: x['affinity'], default={})
        worst_result = min(aggregated_results['results'], key=lambda x: x['affinity'], default={})
        
        aggregated_results['summary'] = {
            # Basic statistics
            'total_jobs': len(job_ids),
            'completed_jobs': len(aggregated_results['results']),
            'success_rate': len(aggregated_results['results']) / len(job_ids) * 100 if job_ids else 0,
            
            # Affinity analysis
            'affinity_stats': {
                'average': sum(affinities) / len(affinities) if affinities else 0,
                'min': min(affinities) if affinities else 0,
                'max': max(affinities) if affinities else 0,
                'median': sorted(affinities)[len(affinities)//2] if affinities else 0,
                'std_dev': (sum([(x - sum(affinities)/len(affinities))**2 for x in affinities]) / len(affinities))**0.5 if len(affinities) > 1 else 0
            },
            
            # Confidence analysis  
            'confidence_stats': {
                'average': sum(confidences) / len(confidences) if confidences else 0,
                'min': min(confidences) if confidences else 0,
                'max': max(confidences) if confidences else 0,
                'median': sorted(confidences)[len(confidences)//2] if confidences else 0
            },
            
            # Structure quality metrics
            'structure_quality': {
                'avg_ptm': sum(ptm_scores) / len(ptm_scores) if ptm_scores else 0,
                'avg_plddt': sum(plddt_scores) / len(plddt_scores) if plddt_scores else 0,
                'avg_iptm': sum(iptm_scores) / len(iptm_scores) if iptm_scores else 0
            },
            
            # Performance metrics
            'performance': {
                'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
                'total_execution_time': sum(execution_times) if execution_times else 0,
                'structures_generated': len([r for r in aggregated_results['results'] if r['has_structure']])
            },
            
            # Best and worst performers
            'top_performer': {
                'job_id': best_result.get('job_id', 'N/A'),
                'ligand_name': best_result.get('ligand_name', 'N/A'),
                'affinity': best_result.get('affinity', 0),
                'confidence': best_result.get('confidence', 0)
            },
            'worst_performer': {
                'job_id': worst_result.get('job_id', 'N/A'),
                'ligand_name': worst_result.get('ligand_name', 'N/A'),
                'affinity': worst_result.get('affinity', 0),
                'confidence': worst_result.get('confidence', 0)
            },
            
            # Analysis insights
            'insights': {
                'high_affinity_count': len([a for a in affinities if a > 0.8]),
                'medium_affinity_count': len([a for a in affinities if 0.4 <= a <= 0.8]),
                'low_affinity_count': len([a for a in affinities if a < 0.4]),
                'high_confidence_count': len([c for c in confidences if c > 0.7]),
                'recommended_ligands': [r['ligand_name'] for r in aggregated_results['results'] 
                                      if r['affinity'] > 0.6 and r['confidence'] > 0.5][:5]  # Top 5
            }
        }
        
        # Store aggregated results
        aggregated_path = f"batches/{batch_id}/results/aggregated.json"
        aggregated_content = json.dumps(aggregated_results, indent=2).encode('utf-8')
        gcp_storage_service.storage.upload_file(
            aggregated_path, aggregated_content, 'application/json'
        )
        logger.info(f"✅ Created aggregated results for batch {batch_id}")
        
        # Create summary.json
        summary_path = f"batches/{batch_id}/results/summary.json"
        summary_content = json.dumps(aggregated_results['summary'], indent=2).encode('utf-8')
        gcp_storage_service.storage.upload_file(
            summary_path, summary_content, 'application/json'
        )
        logger.info(f"✅ Created summary.json for batch {batch_id}")
        
        # Create comprehensive batch results (parent-level results)
        batch_results_path = f"batches/{batch_id}/batch_results.json"
        batch_results = {
            'batch_id': batch_id,
            'batch_type': 'protein_ligand_binding_screen',
            'model': 'boltz2',
            'created_at': datetime.utcnow().isoformat(),
            'total_ligands_screened': len(job_ids),
            'successful_predictions': len(aggregated_results['results']),
            
            # Overall batch statistics
            'batch_statistics': aggregated_results['summary'],
            
            # Individual job results with full Modal data
            'individual_results': aggregated_results['results'],
            
            # Ranking and recommendations
            'ligand_ranking': sorted(aggregated_results['results'], 
                                   key=lambda x: x['affinity'], reverse=True),
            
            # Export metadata for further analysis
            'export_info': {
                'generated_at': datetime.utcnow().isoformat(),
                'format_version': '2.0',
                'data_source': 'modal_boltz2_predictions',
                'includes_raw_modal_results': True,
                'includes_structure_files': True
            }
        }
        
        batch_results_content = json.dumps(batch_results, indent=2).encode('utf-8')
        gcp_storage_service.storage.upload_file(
            batch_results_path, batch_results_content, 'application/json'
        )
        logger.info(f"✅ Created comprehensive batch_results.json for batch {batch_id}")
        
        # Create CSV export for easy analysis
        create_batch_csv_export(batch_id, aggregated_results['results'])
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating aggregated results for batch {batch_id}: {e}")
        return False

def create_batch_csv_export(batch_id: str, results: List[Dict[str, Any]]):
    """Create CSV export for batch results"""
    try:
        import csv
        import io
        
        # Prepare CSV data
        csv_data = []
        for result in results:
            row = {
                'job_id': result.get('job_id', ''),
                'ligand_name': result.get('ligand_name', ''),
                'protein_name': result.get('protein_name', ''),
                'affinity': result.get('affinity', 0),
                'confidence': result.get('confidence', 0),
                'ptm_score': result.get('ptm_score', 0),
                'plddt_score': result.get('plddt_score', 0),
                'iptm_score': result.get('iptm_score', 0),
                'execution_time': result.get('execution_time', 0),
                'has_structure': result.get('has_structure', False),
                'stored_at': result.get('stored_at', ''),
                
                # Ensemble metrics if available
                'affinity_probability': result.get('raw_modal_result', {}).get('affinity_probability', ''),
                'complex_plddt': result.get('raw_modal_result', {}).get('confidence_metrics', {}).get('complex_plddt', ''),
                'ligand_iptm': result.get('raw_modal_result', {}).get('ligand_iptm_score', ''),
                'protein_iptm': result.get('raw_modal_result', {}).get('protein_iptm_score', ''),
            }
            csv_data.append(row)
        
        # Create CSV content
        output = io.StringIO()
        if csv_data:
            fieldnames = csv_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        csv_content = output.getvalue().encode('utf-8')
        
        # Store CSV export
        csv_path = f"batches/{batch_id}/results/batch_export.csv"
        gcp_storage_service.storage.upload_file(
            csv_path, csv_content, 'text/csv'
        )
        logger.info(f"✅ Created CSV export for batch {batch_id}")
        
    except Exception as e:
        logger.error(f"Error creating CSV export for batch {batch_id}: {e}")

@router.get("/list-batches")
async def list_batches():
    """List all batch jobs for debugging"""
    
    try:
        all_jobs = await unified_job_manager.get_all_jobs(limit=1000)
        
        batches = {}
        for job in all_jobs:
            input_data = job.get('input_data', {})
            parent_batch_id = input_data.get('parent_batch_id')
            
            if parent_batch_id:
                # This is a child job
                if parent_batch_id not in batches:
                    batches[parent_batch_id] = {'children': [], 'parent': None}
                batches[parent_batch_id]['children'].append({
                    'job_id': job.get('id'),
                    'status': job.get('status'),
                    'ligand_name': input_data.get('ligand_name', 'Unknown')
                })
            
            # Check if this is a batch parent
            job_type = job.get('input_data', {}).get('job_type')
            if job_type == 'BATCH_PARENT' or job.get('type') == 'BATCH_PARENT':
                batch_id = job.get('id')
                if batch_id not in batches:
                    batches[batch_id] = {'children': [], 'parent': None}
                batches[batch_id]['parent'] = {
                    'job_id': batch_id,
                    'status': job.get('status'),
                    'created_at': job.get('created_at')
                }
        
        return {
            'total_batches': len(batches),
            'batches': batches
        }
        
    except Exception as e:
        logger.error(f"Error listing batches: {e}")
        raise HTTPException(status_code=500, detail=str(e))