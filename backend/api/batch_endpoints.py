"""
Batch Processing Endpoints for OMTX-Hub
Handles batch protein-ligand screening with progress tracking and ZIP downloads
"""

import asyncio
import io
import json
import logging
import time
import uuid
import zipfile
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from pydantic import BaseModel, Field

from database.unified_job_manager import unified_job_manager
from tasks.task_handlers import task_handler_registry, TaskType
from schemas.task_schemas import task_schema_registry

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class LigandInput(BaseModel):
    id: str = Field(..., description="Unique identifier for the ligand")
    smiles: str = Field(..., description="SMILES string for the ligand")
    name: Optional[str] = Field(None, description="Optional compound name")

class BatchScreeningRequest(BaseModel):
    protein_sequence: str = Field(..., description="Protein sequence for screening")
    protein_name: str = Field(..., description="Name of the protein (e.g., TRIM25) - REQUIRED")
    ligands: List[LigandInput] = Field(..., description="List of ligands to screen", min_items=1, max_items=1501)
    job_name: str = Field("batch_screening", description="Name for the batch job")
    use_msa: bool = Field(True, description="Whether to use MSA server")
    use_potentials: bool = Field(False, description="Whether to use potentials")

class BatchStatus(BaseModel):
    batch_id: str
    total_jobs: int
    completed: int
    failed: int
    in_progress: int
    status: str  # pending, running, completed, failed, partially_completed
    created_at: str
    estimated_completion_time: Optional[int] = None
    individual_jobs: List[Dict[str, Any]] = []

class BatchResponse(BaseModel):
    batch_id: str
    status: str
    message: str
    total_jobs: int
    estimated_completion_time: Optional[int] = None

# In-memory batch storage (in production, use database)
active_batches: Dict[str, Dict[str, Any]] = {}
batch_job_results: Dict[str, List[Dict[str, Any]]] = {}

@router.post("/protein-ligand-screening", response_model=BatchResponse)
async def submit_batch_screening(request: BatchScreeningRequest, background_tasks: BackgroundTasks):
    """Submit batch protein-ligand screening job"""
    
    # Generate batch ID
    batch_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"🚀 Submitting batch screening: {batch_id}")
    logger.info(f"   Protein sequence length: {len(request.protein_sequence)}")
    logger.info(f"   Number of ligands: {len(request.ligands)}")
    logger.info(f"   Job name: {request.job_name}")
    
    # Validate protein sequence
    if len(request.protein_sequence.strip()) < 10:
        raise HTTPException(status_code=400, detail="Protein sequence must be at least 10 amino acids long")
    
    # Validate protein name
    if not request.protein_name or not request.protein_name.strip():
        raise HTTPException(status_code=400, detail="Protein name is required and cannot be empty")
    
    # Validate SMILES strings
    for ligand in request.ligands:
        if not is_valid_smiles(ligand.smiles):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid SMILES string for ligand {ligand.id}: {ligand.smiles}"
            )
    
    # Create batch record
    batch_data = {
        'batch_id': batch_id,
        'protein_sequence': request.protein_sequence,
        'ligands': [ligand.dict() for ligand in request.ligands],
        'job_name': request.job_name,
        'total_jobs': len(request.ligands),
        'completed': 0,
        'failed': 0,
        'in_progress': 0,
        'status': 'pending',
        'created_at': time.time(),
        'use_msa': request.use_msa,
        'use_potentials': request.use_potentials,
        'individual_job_ids': []
    }
    
    active_batches[batch_id] = batch_data
    batch_job_results[batch_id] = []
    
    # Start batch processing in background
    background_tasks.add_task(
        process_batch_screening,
        batch_id,
        request.protein_sequence,
        request.ligands,
        request.job_name,
        request.protein_name,
        request.use_msa,
        request.use_potentials
    )
    
    estimated_time = len(request.ligands) * 300  # ~5 minutes per ligand
    
    logger.info(f"✅ Batch submitted successfully: {batch_id}")
    
    return BatchResponse(
        batch_id=batch_id,
        status="submitted",
        message=f"Batch screening submitted with {len(request.ligands)} ligands",
        total_jobs=len(request.ligands),
        estimated_completion_time=estimated_time
    )

async def process_batch_screening(
    batch_id: str,
    protein_sequence: str,
    ligands: List[LigandInput],
    job_name: str,
    protein_name: str,
    use_msa: bool,
    use_potentials: bool
):
    """Process batch screening with controlled concurrency"""
    
    logger.info(f"🔄 Starting batch processing: {batch_id}")
    
    try:
        # Update batch status
        active_batches[batch_id]['status'] = 'running'
        
        # Create individual prediction tasks
        tasks = []
        job_ids = []
        
        for i, ligand in enumerate(ligands):
            # Generate individual job ID
            individual_job_id = f"{batch_id}_ligand_{i+1:03d}_{ligand.id}"
            job_ids.append(individual_job_id)
            
            # Create task
            task = process_single_ligand_prediction(
                batch_id=batch_id,
                job_id=individual_job_id,
                protein_sequence=protein_sequence,
                ligand=ligand,
                job_name=f"{job_name}_ligand_{i+1}",
                protein_name=protein_name,
                use_msa=use_msa,
                use_potentials=use_potentials
            )
            tasks.append(task)
        
        # Update batch with job IDs
        active_batches[batch_id]['individual_job_ids'] = job_ids
        
        # Process with controlled concurrency (max 5 concurrent jobs)
        semaphore = asyncio.Semaphore(5)
        
        async def controlled_task(task):
            async with semaphore:
                return await task
        
        # Execute all tasks with concurrency control
        results = await asyncio.gather(*[controlled_task(task) for task in tasks], return_exceptions=True)
        
        # Process results
        completed_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i+1} failed: {result}")
                failed_count += 1
            elif result and result.get('status') == 'completed':
                completed_count += 1
            else:
                failed_count += 1
        
        # Update final batch status
        if completed_count == len(ligands):
            active_batches[batch_id]['status'] = 'completed'
        elif completed_count > 0:
            active_batches[batch_id]['status'] = 'partially_completed'
        else:
            active_batches[batch_id]['status'] = 'failed'
        
        active_batches[batch_id]['completed'] = completed_count
        active_batches[batch_id]['failed'] = failed_count
        active_batches[batch_id]['in_progress'] = 0
        active_batches[batch_id]['completed_at'] = time.time()
        
        logger.info(f"✅ Batch processing completed: {batch_id} - {completed_count}/{len(ligands)} successful")
        
    except Exception as e:
        logger.error(f"❌ Batch processing failed: {batch_id} - {str(e)}")
        active_batches[batch_id]['status'] = 'failed'
        active_batches[batch_id]['error_message'] = str(e)

async def process_single_ligand_prediction(
    batch_id: str,
    job_id: str,
    protein_sequence: str,
    ligand: LigandInput,
    job_name: str,
    protein_name: str,
    use_msa: bool,
    use_potentials: bool
) -> Dict[str, Any]:
    """Process a single protein-ligand prediction"""
    
    logger.info(f"Processing individual prediction: {job_id}")
    
    try:
        # Update batch progress
        active_batches[batch_id]['in_progress'] += 1
        
        # Prepare input data for protein-ligand binding prediction
        input_data = {
            'protein_sequence': protein_sequence,
            'ligand_smiles': ligand.smiles
        }
        
        # Create job data
        job_data = {
            'id': job_id,
            'name': job_name,
            'type': TaskType.PROTEIN_LIGAND_BINDING,
            'status': 'pending',
            'model_name': 'boltz2',
            'input_data': {
                'task_type': TaskType.PROTEIN_LIGAND_BINDING,
                'input_data': input_data,
                'job_name': job_name,
                'protein_name': protein_name,
                'use_msa': use_msa,
                'use_potentials': use_potentials
            },
            'parameters': {
                'use_msa': use_msa,
                'use_potentials': use_potentials
            },
            'created_at': time.time(),
            'batch_id': batch_id,
            'ligand_info': {
                'id': ligand.id,
                'smiles': ligand.smiles,
                'name': ligand.name
            }
        }
        
        # Create job in unified manager
        created_job_id = await unified_job_manager.create_job(job_data)
        
        # Update job status to running
        await unified_job_manager.update_job_status(created_job_id, "running")
        
        # Process task using task handler registry
        result = await task_handler_registry.process_task(
            task_type=TaskType.PROTEIN_LIGAND_BINDING,
            input_data=input_data,
            job_name=job_name,
            job_id=created_job_id,
            use_msa=use_msa,
            use_potentials=use_potentials
        )
        
        # Add ligand metadata to result
        result['ligand_info'] = {
            'id': ligand.id,
            'smiles': ligand.smiles,
            'name': ligand.name or f"Ligand_{ligand.id}"
        }
        result['batch_id'] = batch_id
        result['individual_job_id'] = created_job_id
        
        # Check if this is an async job (using spawn) or a completed job
        if result.get('status') == 'running' and result.get('modal_call_id'):
            # This is an async job - it will be completed by background monitoring
            logger.info(f"🚀 Async Modal job started: {job_id} -> {result.get('modal_call_id')}")
            
            # Update job status to running (should already be done by task handler)
            await unified_job_manager.update_job_status(created_job_id, "running", {
                'modal_call_id': result.get('modal_call_id'),
                'ligand_info': result['ligand_info'],
                'batch_id': batch_id
            })
            
            # Store running job info in batch results for tracking
            batch_job_results[batch_id].append(result)
            
            # Keep job in 'in_progress' - background monitor will update when complete
            logger.info(f"⏳ Job {job_id} started in background, will be monitored for completion")
            
            return result
            
        else:
            # This is a completed job (synchronous execution)
            await unified_job_manager.update_job_results(created_job_id, result, "completed")
            
            # Store result in batch results
            batch_job_results[batch_id].append(result)
            
            # Update batch progress
            active_batches[batch_id]['in_progress'] -= 1
            active_batches[batch_id]['completed'] += 1
            
            logger.info(f"✅ Individual prediction completed: {job_id}")
            
            return result
        
    except Exception as e:
        logger.error(f"❌ Individual prediction failed: {job_id} - {str(e)}")
        
        # Update batch progress
        if batch_id in active_batches:
            active_batches[batch_id]['in_progress'] -= 1
            active_batches[batch_id]['failed'] += 1
        
        # Store error result
        error_result = {
            'job_id': job_id,
            'batch_id': batch_id,
            'ligand_info': {
                'id': ligand.id,
                'smiles': ligand.smiles,
                'name': ligand.name or f"Ligand_{ligand.id}"
            },
            'status': 'failed',
            'error': str(e),
            'error_message': str(e)
        }
        batch_job_results[batch_id].append(error_result)
        
        # Update job with error
        try:
            await unified_job_manager.update_job_results(job_id, error_result, "failed")
        except:
            pass  # Job might not exist yet
        
        return error_result

@router.get("/batch/{batch_id}/status", response_model=BatchStatus)
async def get_batch_status(batch_id: str):
    """Get batch status and progress"""
    
    if batch_id not in active_batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_data = active_batches[batch_id]
    results = batch_job_results.get(batch_id, [])
    
    # Get individual job statuses
    individual_jobs = []
    for result in results:
        individual_jobs.append({
            'job_id': result.get('individual_job_id', result.get('job_id')),
            'ligand_id': result.get('ligand_info', {}).get('id'),
            'ligand_name': result.get('ligand_info', {}).get('name'),
            'smiles': result.get('ligand_info', {}).get('smiles'),
            'status': result.get('status', 'unknown'),
            'affinity': result.get('affinity'),
            'confidence': result.get('confidence'),
            'error_message': result.get('error_message')
        })
    
    return BatchStatus(
        batch_id=batch_id,
        total_jobs=batch_data['total_jobs'],
        completed=batch_data['completed'],
        failed=batch_data['failed'],
        in_progress=batch_data['in_progress'],
        status=batch_data['status'],
        created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(batch_data['created_at'])),
        estimated_completion_time=batch_data.get('estimated_completion_time'),
        individual_jobs=individual_jobs
    )

@router.get("/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Get detailed batch results"""
    
    if batch_id not in active_batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_data = active_batches[batch_id]
    results = batch_job_results.get(batch_id, [])
    
    # Organize results by categories
    affinity_results = []
    confidence_results = []
    interaction_results = []
    
    for result in results:
        if result.get('status') == 'completed':
            ligand_info = result.get('ligand_info', {})
            
            # Affinity data
            if result.get('affinity') is not None:
                affinity_results.append({
                    'ligand_id': ligand_info.get('id'),
                    'ligand_name': ligand_info.get('name'),
                    'smiles': ligand_info.get('smiles'),
                    'affinity_kcal_mol': result.get('affinity'),
                    'confidence_score': result.get('confidence', {}).get('ptm', 0)
                })
            
            # Confidence data
            confidence_data = result.get('confidence', {})
            if confidence_data:
                confidence_results.append({
                    'ligand_id': ligand_info.get('id'),
                    'ligand_name': ligand_info.get('name'),
                    'smiles': ligand_info.get('smiles'),
                    'ptm': confidence_data.get('ptm'),
                    'iplddt': confidence_data.get('iplddt'),
                    'iptm': confidence_data.get('iptm')
                })
            
            # Interaction data (if available)
            if result.get('interactions'):
                interaction_results.append({
                    'ligand_id': ligand_info.get('id'),
                    'ligand_name': ligand_info.get('name'),
                    'smiles': ligand_info.get('smiles'),
                    'interactions': result.get('interactions')
                })
    
    return {
        'batch_id': batch_id,
        'batch_info': batch_data,
        'results': {
            'affinity': affinity_results,
            'confidence': confidence_results,
            'interactions': interaction_results
        },
        'summary': {
            'total_predictions': len(results),
            'successful_predictions': len([r for r in results if r.get('status') == 'completed']),
            'failed_predictions': len([r for r in results if r.get('status') == 'failed']),
            'best_affinity': min([r.get('affinity', float('inf')) for r in results if r.get('affinity') is not None], default=None),
            'worst_affinity': max([r.get('affinity', float('-inf')) for r in results if r.get('affinity') is not None], default=None)
        }
    }

@router.get("/batch/{batch_id}/download")
async def download_batch_results(batch_id: str, include_partial: bool = True):
    """Download batch results as ZIP file"""
    
    if batch_id not in active_batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_data = active_batches[batch_id]
    results = batch_job_results.get(batch_id, [])
    
    # Filter results if not including partial
    if not include_partial and batch_data['status'] not in ['completed', 'partially_completed']:
        raise HTTPException(status_code=400, detail="Batch not completed. Use include_partial=true to download partial results")
    
    completed_results = [r for r in results if r.get('status') == 'completed']
    
    if not completed_results:
        raise HTTPException(status_code=404, detail="No completed results to download")
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add structure files
            structures_added = 0
            for i, result in enumerate(completed_results):
                ligand_info = result.get('ligand_info', {})
                ligand_id = ligand_info.get('id', f'ligand_{i+1}')
                
                # Add CIF structure file
                structure_content = result.get('structure_file_content')
                if not structure_content and result.get('structure_file_base64'):
                    import base64
                    try:
                        structure_content = base64.b64decode(result['structure_file_base64']).decode('utf-8')
                    except Exception as e:
                        logger.error(f"Failed to decode structure for ligand {ligand_id}: {e}")
                        continue
                
                if structure_content:
                    filename = f"structures/{ligand_id}_{ligand_info.get('name', 'compound')}.cif"
                    zf.writestr(filename, structure_content)
                    structures_added += 1
            
            # Create summary CSV
            summary_data = []
            for result in completed_results:
                ligand_info = result.get('ligand_info', {})
                confidence = result.get('confidence', {})
                
                summary_data.append({
                    'Ligand_ID': ligand_info.get('id', ''),
                    'Ligand_Name': ligand_info.get('name', ''),
                    'SMILES': ligand_info.get('smiles', ''),
                    'Affinity_kcal_mol': result.get('affinity', ''),
                    'PTM_Score': confidence.get('ptm', ''),
                    'ipLDDT_Score': confidence.get('iplddt', ''),
                    'ipTM_Score': confidence.get('iptm', ''),
                    'Status': result.get('status', '')
                })
            
            # Convert to CSV
            if summary_data:
                import csv
                csv_buffer = io.StringIO()
                fieldnames = summary_data[0].keys()
                writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(summary_data)
                zf.writestr(f"{batch_id}_results_summary.csv", csv_buffer.getvalue())
            
            # Add detailed JSON report
            detailed_report = {
                'batch_id': batch_id,
                'batch_info': batch_data,
                'results': completed_results,
                'summary': {
                    'total_requested': batch_data['total_jobs'],
                    'completed': len(completed_results),
                    'failed': batch_data['failed'],
                    'structures_included': structures_added,
                    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }
            }
            zf.writestr(f"{batch_id}_detailed_report.json", json.dumps(detailed_report, indent=2))
            
            # Add README
            readme_content = f"""# Batch Screening Results: {batch_id}

## Contents:
- structures/ - CIF structure files for each successful prediction
- {batch_id}_results_summary.csv - Summary of all results in CSV format
- {batch_id}_detailed_report.json - Complete results in JSON format

## Summary:
- Total ligands requested: {batch_data['total_jobs']}
- Successful predictions: {len(completed_results)}
- Failed predictions: {batch_data['failed']}
- Structure files included: {structures_added}

## Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
"""
            zf.writestr("README.txt", readme_content)
    
    except Exception as e:
        logger.error(f"Failed to create ZIP file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create download: {str(e)}")
    
    zip_data = zip_buffer.getvalue()
    
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={batch_id}_results.zip"
        }
    )

@router.get("/batch/{batch_id}/progress")
async def get_batch_progress(batch_id: str):
    """Get real-time batch progress for UI updates"""
    
    if batch_id not in active_batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_data = active_batches[batch_id]
    
    progress_percentage = 0
    if batch_data['total_jobs'] > 0:
        progress_percentage = (batch_data['completed'] + batch_data['failed']) / batch_data['total_jobs'] * 100
    
    return {
        'batch_id': batch_id,
        'progress_percentage': round(progress_percentage, 1),
        'completed': batch_data['completed'],
        'failed': batch_data['failed'],
        'in_progress': batch_data['in_progress'],
        'total': batch_data['total_jobs'],
        'status': batch_data['status'],
        'current_message': f"Processing {batch_data['in_progress']} predictions, {batch_data['completed']} completed, {batch_data['failed']} failed"
    }

def is_valid_smiles(smiles: str) -> bool:
    """Validate SMILES string (basic validation)"""
    if not smiles or not smiles.strip():
        return False
    
    smiles = smiles.strip()
    
    # Basic character validation
    valid_chars = set('ABCDEFGHIKLMNOPRSTUVWXYZabcdefghiklmnoprstuvwxyz0123456789()[]=#@+-./\\:')
    if not all(c in valid_chars for c in smiles):
        return False
    
    # Check for balanced parentheses and brackets
    if smiles.count('(') != smiles.count(')'):
        return False
    if smiles.count('[') != smiles.count(']'):
        return False
    
    # Must contain at least one letter (element symbol)
    if not any(c.isalpha() for c in smiles):
        return False
    
    # Reasonable length check
    if len(smiles) > 300:
        return False
    
    return True