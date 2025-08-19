"""
Cloud Run Results Download Endpoints - CRITICAL FOR DEMO
Distinguished Engineer Implementation - Complete results retrieval from GCS
"""

import os
import io
import json
import zipfile
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse, JSONResponse
from google.cloud import storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v4/download", tags=["Results Download"])

@router.get("/batches/{batch_id}/results")
async def download_batch_results(
    batch_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    format: str = Query("zip", description="Download format: zip, json, or individual")
):
    """Download batch results from GCS"""
    
    if not user_id:
        user_id = "demo-user"
    
    logger.info(f"📥 Downloading batch results: {batch_id} for user {user_id}")
    
    try:
        client = storage.Client()
        bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        bucket = client.bucket(bucket_name)
        
        # Check if batch exists
        batch_prefix = f"users/{user_id}/batches/{batch_id}/"
        batch_blobs = list(bucket.list_blobs(prefix=batch_prefix, max_results=1))
        
        if not batch_blobs:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        if format == "zip":
            return await _download_batch_as_zip(bucket, user_id, batch_id)
        elif format == "json":
            return await _download_batch_as_json(bucket, user_id, batch_id)
        else:
            return await _list_batch_files(bucket, user_id, batch_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download batch results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/jobs/{job_id}/results")
async def download_job_results(
    job_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id"),
    format: str = Query("json", description="Download format: json, pdb, or cif")
):
    """Download individual job results from GCS"""
    
    if not user_id:
        user_id = "demo-user"
    
    logger.info(f"📥 Downloading job results: {job_id} for user {user_id}")
    
    try:
        client = storage.Client()
        bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        bucket = client.bucket(bucket_name)
        
        # Look for job results
        job_prefix = f"users/{user_id}/jobs/{job_id}/"
        job_blobs = list(bucket.list_blobs(prefix=job_prefix))
        
        if not job_blobs:
            raise HTTPException(status_code=404, detail=f"Job {job_id} results not found")
        
        if format == "json":
            return await _download_job_as_json(bucket, user_id, job_id)
        elif format in ["pdb", "cif"]:
            return await _download_structure_file(bucket, user_id, job_id, format)
        else:
            return await _list_job_files(bucket, user_id, job_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download job results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/batches/{batch_id}/status")
async def get_batch_download_status(
    batch_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Get batch download status and available files"""
    
    if not user_id:
        user_id = "demo-user"
    
    try:
        client = storage.Client()
        bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        bucket = client.bucket(bucket_name)
        
        # Get batch metadata
        results_prefix = f"users/{user_id}/batches/{batch_id}/results/"
        result_blobs = list(bucket.list_blobs(prefix=results_prefix))
        
        # Categorize files
        structure_files = []
        result_files = []
        log_files = []
        
        for blob in result_blobs:
            file_name = blob.name.split('/')[-1]
            file_size = blob.size
            
            if file_name.endswith(('.pdb', '.cif')):
                structure_files.append({
                    "name": file_name,
                    "size": file_size,
                    "url": f"/api/v4/download/files/{blob.name}"
                })
            elif file_name.endswith('.json'):
                result_files.append({
                    "name": file_name,
                    "size": file_size,
                    "url": f"/api/v4/download/files/{blob.name}"
                })
            elif file_name.endswith('.log'):
                log_files.append({
                    "name": file_name,
                    "size": file_size,
                    "url": f"/api/v4/download/files/{blob.name}"
                })
        
        total_size = sum(blob.size for blob in result_blobs)
        
        return {
            "batch_id": batch_id,
            "user_id": user_id,
            "total_files": len(result_blobs),
            "total_size_bytes": total_size,
            "structure_files": structure_files,
            "result_files": result_files,
            "log_files": log_files,
            "download_urls": {
                "zip": f"/api/v4/download/batches/{batch_id}/results?format=zip",
                "json": f"/api/v4/download/batches/{batch_id}/results?format=json"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get batch status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/files/{file_path:path}")
async def download_individual_file(
    file_path: str,
    user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """Download individual file from GCS"""
    
    if not user_id:
        user_id = "demo-user"
    
    # Security check - ensure user can only access their own files
    if not file_path.startswith(f"users/{user_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        client = storage.Client()
        bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        bucket = client.bucket(bucket_name)
        
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Stream the file
        file_data = blob.download_as_bytes()
        file_name = file_path.split('/')[-1]
        
        # Determine content type
        content_type = "application/octet-stream"
        if file_name.endswith('.json'):
            content_type = "application/json"
        elif file_name.endswith('.pdb'):
            content_type = "chemical/x-pdb"
        elif file_name.endswith('.cif'):
            content_type = "chemical/x-cif"
        elif file_name.endswith('.log'):
            content_type = "text/plain"
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_name}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")

# Helper functions

async def _download_batch_as_zip(bucket, user_id: str, batch_id: str) -> StreamingResponse:
    """Create ZIP archive of all batch results"""
    
    results_prefix = f"users/{user_id}/batches/{batch_id}/results/"
    result_blobs = list(bucket.list_blobs(prefix=results_prefix))
    
    if not result_blobs:
        raise HTTPException(status_code=404, detail="No results found for batch")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for blob in result_blobs:
            try:
                file_data = blob.download_as_bytes()
                file_name = blob.name.split('/')[-1]
                zip_file.writestr(file_name, file_data)
            except Exception as e:
                logger.warning(f"⚠️ Could not add file {blob.name} to ZIP: {str(e)}")
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=batch_{batch_id}_results.zip"
        }
    )

async def _download_batch_as_json(bucket, user_id: str, batch_id: str) -> JSONResponse:
    """Return batch results as JSON"""
    
    results_prefix = f"users/{user_id}/batches/{batch_id}/results/"
    result_blobs = list(bucket.list_blobs(prefix=results_prefix))
    
    results = []
    
    for blob in result_blobs:
        if blob.name.endswith('.json'):
            try:
                content = blob.download_as_text()
                result_data = json.loads(content)
                results.append(result_data)
            except Exception as e:
                logger.warning(f"⚠️ Could not parse result file {blob.name}: {str(e)}")
    
    return JSONResponse({
        "batch_id": batch_id,
        "user_id": user_id,
        "results_count": len(results),
        "results": results
    })

async def _download_job_as_json(bucket, user_id: str, job_id: str) -> JSONResponse:
    """Return job results as JSON"""
    
    job_prefix = f"users/{user_id}/jobs/{job_id}/"
    job_blobs = list(bucket.list_blobs(prefix=job_prefix))
    
    result_data = {}
    
    for blob in job_blobs:
        if blob.name.endswith('.json'):
            try:
                content = blob.download_as_text()
                data = json.loads(content)
                result_data.update(data)
            except Exception as e:
                logger.warning(f"⚠️ Could not parse result file {blob.name}: {str(e)}")
    
    return JSONResponse({
        "job_id": job_id,
        "user_id": user_id,
        "result": result_data
    })

async def _download_structure_file(bucket, user_id: str, job_id: str, format: str) -> StreamingResponse:
    """Download structure file (PDB or CIF)"""
    
    job_prefix = f"users/{user_id}/jobs/{job_id}/"
    job_blobs = list(bucket.list_blobs(prefix=job_prefix))
    
    # Find structure file
    structure_blob = None
    for blob in job_blobs:
        if blob.name.endswith(f'.{format}'):
            structure_blob = blob
            break
    
    if not structure_blob:
        raise HTTPException(status_code=404, detail=f"No {format.upper()} file found for job")
    
    file_data = structure_blob.download_as_bytes()
    
    content_type = "chemical/x-pdb" if format == "pdb" else "chemical/x-cif"
    
    return StreamingResponse(
        io.BytesIO(file_data),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={job_id}.{format}"
        }
    )

async def _list_batch_files(bucket, user_id: str, batch_id: str) -> JSONResponse:
    """List all files in batch"""
    
    results_prefix = f"users/{user_id}/batches/{batch_id}/"
    result_blobs = list(bucket.list_blobs(prefix=results_prefix))
    
    files = []
    for blob in result_blobs:
        files.append({
            "name": blob.name.split('/')[-1],
            "path": blob.name,
            "size": blob.size,
            "created": blob.time_created.isoformat() if blob.time_created else None,
            "download_url": f"/api/v4/download/files/{blob.name}"
        })
    
    return JSONResponse({
        "batch_id": batch_id,
        "user_id": user_id,
        "files": files
    })

async def _list_job_files(bucket, user_id: str, job_id: str) -> JSONResponse:
    """List all files for job"""
    
    job_prefix = f"users/{user_id}/jobs/{job_id}/"
    job_blobs = list(bucket.list_blobs(prefix=job_prefix))
    
    files = []
    for blob in job_blobs:
        files.append({
            "name": blob.name.split('/')[-1],
            "path": blob.name,
            "size": blob.size,
            "created": blob.time_created.isoformat() if blob.time_created else None,
            "download_url": f"/api/v4/download/files/{blob.name}"
        })
    
    return JSONResponse({
        "job_id": job_id,
        "user_id": user_id,
        "files": files
    })
