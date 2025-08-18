#!/usr/bin/env python3
"""
Simple Batch Storage Fix

This script will directly fix the batch storage structure by:
1. Finding completed batch jobs with results.json but missing metadata.json/structure.cif
2. Creating the missing files from the results.json data
3. Creating aggregated results if all jobs are complete

Usage: python fix_batch_storage.py
"""

import asyncio
import json
import base64
import logging
from datetime import datetime
from typing import Dict, Any, List

from services.gcp_storage_service import gcp_storage_service
from database.unified_job_manager import unified_job_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_batch_storage_structure():
    """Fix batch storage structure for existing batches"""
    
    try:
        # Get all batch jobs from database
        batch_parents = unified_job_manager.get_jobs_by_type("BATCH_PARENT")
        
        for batch_parent in batch_parents:
            batch_id = batch_parent.get('id')
            if not batch_id:
                continue
                
            logger.info(f"🔧 Processing batch {batch_id}")
            
            # Get child jobs for this batch
            child_jobs = []
            all_jobs = unified_job_manager.get_all_jobs(limit=1000)
            
            for job in all_jobs:
                input_data = job.get('input_data', {})
                if input_data.get('parent_batch_id') == batch_id:
                    child_jobs.append(job)
            
            if not child_jobs:
                logger.info(f"No child jobs found for batch {batch_id}")
                continue
                
            logger.info(f"Found {len(child_jobs)} child jobs for batch {batch_id}")
            
            # Process each child job
            completed_jobs = []
            for child_job in child_jobs:
                job_id = child_job.get('id')
                if child_job.get('status') == 'completed':
                    success = await fix_child_job_storage(batch_id, job_id)
                    if success:
                        completed_jobs.append(job_id)
            
            # Create aggregated results if all jobs complete
            if len(completed_jobs) == len(child_jobs):
                await create_aggregated_results(batch_id, completed_jobs)
                
    except Exception as e:
        logger.error(f"Error fixing batch storage: {e}")

async def fix_child_job_storage(batch_id: str, job_id: str) -> bool:
    """Fix storage for a single child job"""
    
    try:
        # Check if results.json exists
        results_path = f"batches/{batch_id}/jobs/{job_id}/results.json"
        
        try:
            results_data = await gcp_storage_service.storage.download_file(results_path)
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
            await gcp_storage_service.storage.download_file(metadata_path)
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
            await gcp_storage_service.storage.upload_file(
                metadata_path, metadata_content, 'application/json'
            )
            logger.info(f"✅ Created metadata.json for {job_id}")
        
        # Create structure.cif if missing
        structure_path = f"batches/{batch_id}/jobs/{job_id}/structure.cif"
        try:
            await gcp_storage_service.storage.download_file(structure_path)
            logger.info(f"structure.cif already exists for {job_id}")
        except:
            # Create structure.cif from base64
            if results.get('structure_file_base64'):
                try:
                    structure_content = base64.b64decode(results['structure_file_base64'])
                    await gcp_storage_service.storage.upload_file(
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

async def create_aggregated_results(batch_id: str, job_ids: List[str]):
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
                results_data = await gcp_storage_service.storage.download_file(results_path)
                if isinstance(results_data, bytes):
                    results_data = results_data.decode('utf-8')
                results = json.loads(results_data)
                
                # Get metadata
                metadata_path = f"batches/{batch_id}/jobs/{job_id}/metadata.json"
                metadata_data = await gcp_storage_service.storage.download_file(metadata_path)
                if isinstance(metadata_data, bytes):
                    metadata_data = metadata_data.decode('utf-8')
                metadata = json.loads(metadata_data)
                
                job_summary = {
                    'job_id': job_id,
                    'ligand_name': metadata.get('ligand_name', 'Unknown'),
                    'affinity': metadata.get('affinity', 0),
                    'confidence': metadata.get('confidence', 0),
                    'has_structure': metadata.get('has_structure', False)
                }
                
                aggregated_results['results'].append(job_summary)
                
                total_affinity += metadata.get('affinity', 0)
                total_confidence += metadata.get('confidence', 0)
                
            except Exception as e:
                logger.error(f"Error processing job {job_id} for aggregation: {e}")
        
        # Add summary statistics
        aggregated_results['summary'] = {
            'average_affinity': total_affinity / len(job_ids) if job_ids else 0,
            'average_confidence': total_confidence / len(job_ids) if job_ids else 0,
            'best_affinity': max([r['affinity'] for r in aggregated_results['results']], default=0),
            'best_ligand': next((r['ligand_name'] for r in aggregated_results['results'] 
                               if r['affinity'] == max([r['affinity'] for r in aggregated_results['results']], default=0)), 'None')
        }
        
        # Store aggregated results
        aggregated_path = f"batches/{batch_id}/results/aggregated.json"
        aggregated_content = json.dumps(aggregated_results, indent=2).encode('utf-8')
        await gcp_storage_service.storage.upload_file(
            aggregated_path, aggregated_content, 'application/json'
        )
        logger.info(f"✅ Created aggregated results for batch {batch_id}")
        
        # Create summary.json
        summary_path = f"batches/{batch_id}/results/summary.json"
        summary_content = json.dumps(aggregated_results['summary'], indent=2).encode('utf-8')
        await gcp_storage_service.storage.upload_file(
            summary_path, summary_content, 'application/json'
        )
        logger.info(f"✅ Created summary.json for batch {batch_id}")
        
    except Exception as e:
        logger.error(f"Error creating aggregated results for batch {batch_id}: {e}")

if __name__ == "__main__":
    asyncio.run(fix_batch_storage_structure())