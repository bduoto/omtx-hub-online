"""
Batch Relationship API Endpoints
Enhanced batch job management with proper parent-child relationships
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import logging

from services.batch_relationship_manager import batch_relationship_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/v2/batches/{batch_id}/results")
async def get_batch_results(batch_id: str) -> Dict[str, Any]:
    """Get complete batch results with all child job data"""
    try:
        batch_results = await batch_relationship_manager.get_batch_results(batch_id)
        
        if not batch_results:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "data": batch_results
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting batch results {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v2/batches/{batch_id}/children")
async def get_batch_children(batch_id: str) -> Dict[str, Any]:
    """Get all child jobs for a batch"""
    try:
        child_jobs = await batch_relationship_manager.get_child_jobs(batch_id)
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "child_count": len(child_jobs),
            "children": child_jobs
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting batch children {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v2/batches/{batch_id}/summary")
async def get_batch_summary(batch_id: str) -> Dict[str, Any]:
    """Get batch summary statistics"""
    try:
        batch_results = await batch_relationship_manager.get_batch_results(batch_id)
        
        if not batch_results:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        summary = batch_results.get('summary', {})
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "summary": summary,
            "batch_status": batch_results.get('status'),
            "total_jobs": summary.get('total_ligands', 0),
            "completed_jobs": summary.get('completed_jobs', 0),
            "failed_jobs": summary.get('failed_jobs', 0),
            "success_rate": summary.get('success_rate', 0),
            "top_affinity": summary.get('top_affinity', 0),
            "avg_affinity": summary.get('avg_affinity', 0)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting batch summary {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v2/batches/{batch_id}/download/csv")
async def download_batch_csv(batch_id: str):
    """Download batch results as CSV"""
    try:
        from fastapi.responses import Response
        from services.gcp_storage_service import gcp_storage_service
        
        # Try to get pre-generated CSV
        csv_path = f"batches/{batch_id}/aggregated/batch_results.csv"
        csv_content = None
        
        if gcp_storage_service.storage.available:
            csv_content = gcp_storage_service.storage.download_file(csv_path)
        
        if not csv_content:
            # Generate CSV on-the-fly
            batch_results = await batch_relationship_manager.get_batch_results(batch_id)
            if not batch_results:
                raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
            
            # Create CSV content
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Ligand_Name', 'SMILES', 'Status', 'Affinity', 'Confidence', 'Job_ID'])
            
            # Data rows
            for result in batch_results.get('individual_results', []):
                job_id = result.get('job_id', '')
                metadata = result.get('metadata', {})
                results = result.get('results', {})
                
                writer.writerow([
                    metadata.get('ligand_name', 'Unknown'),
                    metadata.get('ligand_smiles', ''),
                    'Completed' if results else 'Failed',
                    results.get('affinity', 'N/A'),
                    results.get('confidence', 'N/A'),
                    job_id
                ])
            
            csv_content = output.getvalue().encode('utf-8')
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=batch_{batch_id}_results.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error downloading batch CSV {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v2/batches/{batch_id}/child/{child_job_id}/results")
async def get_child_job_results(batch_id: str, child_job_id: str) -> Dict[str, Any]:
    """Get specific child job results within batch context"""
    try:
        # Load child results through relationship manager
        batch_results = await batch_relationship_manager.get_batch_results(batch_id)
        
        if not batch_results:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        # Find the specific child job
        child_result = None
        for result in batch_results.get('individual_results', []):
            if result.get('job_id') == child_job_id:
                child_result = result
                break
        
        if not child_result:
            raise HTTPException(status_code=404, detail=f"Child job {child_job_id} not found in batch {batch_id}")
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "job_id": child_job_id,
            "data": child_result
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting child job results {batch_id}/{child_job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v2/batches")
async def list_recent_batches(limit: int = 20) -> Dict[str, Any]:
    """List recent batch jobs"""
    try:
        # This would need to be implemented in the relationship manager
        # For now, return empty list as placeholder
        return {
            "status": "success",
            "batches": [],
            "message": "Batch listing not yet implemented - use individual job queries"
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing batches: {e}")
        raise HTTPException(status_code=500, detail=str(e))