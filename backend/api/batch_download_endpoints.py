"""
Batch Download Endpoints for OMTX-Hub
Handles bulk downloads of batch prediction results
"""

import io
import zipfile
import csv
import base64
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database.unified_job_manager import unified_job_manager
from services.batch_processor import batch_processor

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/batch/{batch_id}/download-all")
async def download_batch_results_zip(batch_id: str):
    """Download all batch results as a ZIP file containing structures and summary CSV"""
    
    try:
        logger.info(f"📦 Preparing batch download for: {batch_id}")
        
        # Get batch status and individual jobs
        batch_status = await batch_processor.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        individual_jobs = batch_status.get('individual_jobs', [])
        
        if not individual_jobs:
            raise HTTPException(status_code=404, detail="No individual jobs found in batch")
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add summary CSV
            csv_content = create_batch_summary_csv(individual_jobs)
            zip_file.writestr(f'batch_summary_{batch_id}.csv', csv_content)
            
            # Add individual structure files
            structure_count = 0
            for job in individual_jobs:
                if job.get('status') != 'completed':
                    continue
                    
                job_id = job.get('id')
                ligand_name = job.get('input_data', {}).get('ligand_name', f'ligand_{structure_count + 1}')
                
                # Get structure content
                results = job.get('results', {}) or job.get('output_data', {})
                structure_content = get_structure_content(results)
                
                if structure_content:
                    # Sanitize filename
                    safe_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in ligand_name)
                    filename = f'{safe_name}_{job_id[:8]}.cif'
                    zip_file.writestr(filename, structure_content)
                    structure_count += 1
            
            # Add batch metadata
            metadata = create_batch_metadata(batch_status, structure_count)
            zip_file.writestr('batch_metadata.txt', metadata)
        
        # Prepare ZIP for download
        zip_buffer.seek(0)
        
        logger.info(f"✅ Batch ZIP created with {structure_count} structures")
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=batch_results_{batch_id}.zip"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create batch download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create batch download: {str(e)}")


def create_batch_summary_csv(individual_jobs: List[Dict[str, Any]]) -> str:
    """Create CSV summary of batch results"""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Index',
        'Job ID',
        'Ligand Name',
        'SMILES',
        'Status',
        'Binding Score',
        'Confidence',
        'PTM Score',
        'Execution Time (s)'
    ])
    
    # Sort jobs by batch_index numerically to fix ordering
    sorted_jobs = sorted(individual_jobs, key=lambda j: int(j.get('input_data', {}).get('batch_index', 0)))
    
    # Write data rows
    for job in sorted_jobs:
        input_data = job.get('input_data', {})
        results = job.get('results', {}) or job.get('output_data', {})
        
        # Extract values with proper fallbacks
        batch_index = input_data.get('batch_index', 0)
        job_id = job.get('id', '')[:8]  # Short ID
        ligand_name = input_data.get('ligand_name', '')
        ligand_smiles = input_data.get('ligand_smiles', '')
        status = job.get('status', '')
        
        # Extract result values with multiple fallback paths
        affinity = results.get('affinity') or results.get('binding_score') or results.get('affinity_pred_value')
        confidence = results.get('confidence') or results.get('confidence_score')
        ptm_score = results.get('ptm_score') or results.get('ptm') or results.get('ptm_score')
        execution_time = results.get('execution_time')
        
        # Format values for CSV
        affinity_str = f"{affinity:.4f}" if affinity is not None else 'N/A'
        confidence_str = f"{confidence * 100:.1f}%" if confidence is not None else 'N/A'
        ptm_str = f"{ptm_score:.4f}" if ptm_score is not None else 'N/A'
        exec_time_str = f"{execution_time:.1f}" if execution_time is not None else 'N/A'
        
        writer.writerow([
            int(batch_index) + 1,  # 1-based index, ensure numeric
            job_id,
            ligand_name,
            ligand_smiles,
            status,
            affinity_str,
            confidence_str,
            ptm_str,
            exec_time_str
        ])
    
    return output.getvalue()


def get_structure_content(results: Dict[str, Any]) -> str:
    """Extract structure content from job results"""
    
    # Try direct content first
    structure_content = results.get('structure_file_content', '')
    
    if not structure_content:
        # Try base64 decoded content
        structure_base64 = results.get('structure_file_base64', '')
        if structure_base64:
            try:
                structure_content = base64.b64decode(structure_base64).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decode base64 structure: {e}")
    
    return structure_content


def create_batch_metadata(batch_status: Dict[str, Any], structure_count: int) -> str:
    """Create metadata file for the batch"""
    
    progress = batch_status.get('progress', {})
    
    metadata = f"""OMTX-Hub Batch Prediction Results
==================================

Batch ID: {batch_status.get('batch_id')}
Status: {batch_status.get('status')}

Summary Statistics:
- Total Jobs: {progress.get('total', 0)}
- Completed: {progress.get('completed', 0)}
- Failed: {progress.get('failed', 0)}
- Running: {progress.get('running', 0)}
- Success Rate: {progress.get('progress_percent', 0)}%

Files Included:
- Structure Files (.cif): {structure_count}
- Summary CSV: 1

Generated by OMTX-Hub
"""
    
    return metadata


@router.get("/batch/{batch_id}/download-csv")
async def download_batch_csv(batch_id: str):
    """Download batch results as CSV only"""
    
    try:
        # Get batch status and individual jobs
        batch_status = await batch_processor.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        individual_jobs = batch_status.get('individual_jobs', [])
        
        # Create CSV content
        csv_content = create_batch_summary_csv(individual_jobs)
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=batch_results_{batch_id}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create CSV download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create CSV download: {str(e)}")