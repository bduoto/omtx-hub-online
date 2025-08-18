"""
Separated Results API Endpoints
Clean separation of individual and batch job results
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends, BackgroundTasks
from datetime import datetime
import asyncio

# Import services
from services.job_classifier import JobClassifier, JobType
from services.gcp_results_indexer import gcp_results_indexer
from services.batch_results_service import batch_results_service
from services.results_enrichment_service import results_enrichment_service
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3/results", tags=["results_v3"])

# ============================================
# Individual Results Endpoints
# ============================================

@router.get("/individual")
async def get_individual_results(
    user_id: str = Query("current_user", description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    search: Optional[str] = Query(None, description="Search in job names"),
    model: Optional[str] = Query(None, description="Filter by model"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    enrich: bool = Query(True, description="Enrich results with full data")
):
    """
    Get ONLY individual job results - no batch jobs or batch children
    """
    
    try:
        logger.info(f"📊 Fetching individual results for user: {user_id}")
        
        # Step 1: Trigger modal monitor to complete any stuck jobs
        try:
            from services.modal_monitor import modal_monitor
            asyncio.create_task(modal_monitor.check_running_jobs())
        except Exception as monitor_error:
            logger.warning(f"Modal monitor check failed: {monitor_error}")
        
        # Step 2: Get all user results from GCP indexer - PERFORMANCE OPTIMIZED
        all_results = await gcp_results_indexer.get_user_results(user_id, limit=min(500, per_page*3))
        
        if not all_results or not all_results.get('results'):
            logger.warning(f"No results found for user {user_id}")
            return {
                'results': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'job_type': 'individual',
                'filters_applied': True
            }
        
        # Step 3: Filter for individual jobs only using classifier
        individual_results = []
        for job in all_results['results']:
            classification = JobClassifier.classify_job(job)
            if classification == JobType.INDIVIDUAL:
                # Enhance job with classification metadata
                job = JobClassifier.enhance_job_with_type(job)
                individual_results.append(job)
        
        logger.info(f"🔍 Found {len(individual_results)} individual jobs out of {len(all_results['results'])} total")
        
        # Step 4: Apply additional filters
        filtered_results = individual_results
        
        if search:
            search_lower = search.lower()
            filtered_results = [
                j for j in filtered_results 
                if search_lower in j.get('job_name', '').lower() or
                   search_lower in j.get('inputs', {}).get('protein_name', '').lower()
            ]
        
        if model:
            filtered_results = [
                j for j in filtered_results 
                if j.get('model_name', '').lower() == model.lower()
            ]
        
        if status:
            filtered_results = [
                j for j in filtered_results 
                if j.get('status', '').lower() == status.lower()
            ]
        
        if date_from:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            filtered_results = [
                j for j in filtered_results 
                if datetime.fromisoformat(j.get('created_at', '2024-01-01').replace('Z', '+00:00')) >= from_date
            ]
        
        if date_to:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            filtered_results = [
                j for j in filtered_results 
                if datetime.fromisoformat(j.get('created_at', '2024-01-01').replace('Z', '+00:00')) <= to_date
            ]
        
        # Step 5: Sort results (newest first)
        filtered_results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Step 6: Apply pagination
        total_filtered = len(filtered_results)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated = filtered_results[start_idx:end_idx]
        
        # Step 7: Optionally enrich with full data
        if enrich and paginated:
            try:
                paginated = await results_enrichment_service.enrich_multiple_jobs(paginated)
            except Exception as e:
                logger.warning(f"Failed to enrich results: {e}")
        
        # Step 8: Calculate pagination metadata
        total_pages = (total_filtered + per_page - 1) // per_page if total_filtered > 0 else 0
        
        response = {
            'results': paginated,
            'total': total_filtered,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'job_type': 'individual',
            'filters_applied': bool(search or model or status or date_from or date_to),
            'statistics': {
                'total_individual_jobs': len(individual_results),
                'filtered_count': total_filtered,
                'models': list(set(j.get('model_name', 'Unknown') for j in individual_results))
            }
        }
        
        logger.info(f"✅ Returning {len(paginated)} individual results (page {page}/{total_pages})")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to get individual results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get individual results: {str(e)}")

# ============================================
# Batch Results Endpoints
# ============================================

@router.get("/batch")
async def get_batch_results(
    user_id: str = Query("current_user", description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    include_children: bool = Query(False, description="Include full child results"),
    status_filter: Optional[str] = Query(None, description="Filter by batch status"),
    search: Optional[str] = Query(None, description="Search in batch names")
):
    """
    Get ONLY batch parent jobs - no individual jobs or batch children
    """
    
    try:
        logger.info(f"📊 Fetching batch results for user: {user_id}")
        
        # Step 1: Get all user results
        all_results = await gcp_results_indexer.get_user_results(user_id, limit=500)
        
        if not all_results or not all_results.get('results'):
            return {
                'results': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'job_type': 'batch'
            }
        
        # Step 2: Filter for batch parents only using classifier
        batch_results = []
        for job in all_results['results']:
            classification = JobClassifier.classify_job(job)
            if classification == JobType.BATCH_PARENT:
                # Enhance with batch metadata
                job = JobClassifier.enhance_job_with_type(job)
                batch_results.append(job)
        
        logger.info(f"🔍 Found {len(batch_results)} batch jobs out of {len(all_results['results'])} total")
        
        # Step 3: Apply filters
        filtered_batches = batch_results
        
        if search:
            search_lower = search.lower()
            filtered_batches = [
                b for b in filtered_batches 
                if search_lower in b.get('job_name', '').lower()
            ]
        
        if status_filter:
            filtered_batches = [
                b for b in filtered_batches 
                if b.get('status', '').lower() == status_filter.lower()
            ]
        
        # Step 4: Sort by creation date (newest first)
        filtered_batches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Step 5: Apply pagination
        total_filtered = len(filtered_batches)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated = filtered_batches[start_idx:end_idx]
        
        # Step 6: Add batch summaries or full children based on flag
        for batch in paginated:
            batch_id = batch.get('job_id') or batch.get('id')
            
            if not include_children:
                # Lightweight response - just add summary
                batch_meta = batch.get('_batch_metadata', {})
                batch['children_summary'] = {
                    'total': batch_meta.get('total_children', 0),
                    'completed': batch_meta.get('completed_children', 0),
                    'failed': batch_meta.get('failed_children', 0),
                    'pending': batch_meta.get('total_children', 0) - 
                              batch_meta.get('completed_children', 0) - 
                              batch_meta.get('failed_children', 0)
                }
                
                # Calculate progress percentage
                total = batch['children_summary']['total']
                completed = batch['children_summary']['completed']
                batch['progress_percentage'] = (completed / total * 100) if total > 0 else 0
                
            else:
                # Full enrichment with all children
                try:
                    full_batch_data = await batch_results_service.get_batch_with_children(batch_id)
                    batch['full_results'] = full_batch_data
                    batch['child_results'] = full_batch_data.get('child_results', [])[:10]  # Limit for response size
                except Exception as e:
                    logger.warning(f"Failed to load children for batch {batch_id}: {e}")
                    batch['children_error'] = str(e)
        
        # Step 7: Calculate pagination metadata
        total_pages = (total_filtered + per_page - 1) // per_page if total_filtered > 0 else 0
        
        response = {
            'results': paginated,
            'total': total_filtered,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'job_type': 'batch',
            'include_children': include_children,
            'statistics': {
                'total_batch_jobs': len(batch_results),
                'filtered_count': total_filtered,
                'total_child_jobs': sum(b.get('_batch_metadata', {}).get('total_children', 0) for b in batch_results)
            }
        }
        
        logger.info(f"✅ Returning {len(paginated)} batch results (page {page}/{total_pages})")
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to get batch results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch results: {str(e)}")

@router.get("/batch/{batch_id}")
async def get_batch_details(
    batch_id: str,
    include_children: bool = Query(True, description="Include child results")
):
    """
    Get detailed information about a specific batch
    """
    
    try:
        logger.info(f"📊 Fetching batch details for: {batch_id}")
        
        # Get full batch data with children
        batch_data = await batch_results_service.get_batch_with_children(batch_id)
        
        if not batch_data:
            raise HTTPException(404, f"Batch {batch_id} not found")
        
        # Enhance with classification
        batch_data = JobClassifier.enhance_job_with_type(batch_data)
        
        if not include_children:
            # Remove child results for lightweight response
            batch_data.pop('child_results', None)
            batch_data['children_included'] = False
        else:
            batch_data['children_included'] = True
        
        return batch_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch details: {str(e)}")

@router.get("/batch/{batch_id}/children")
async def get_batch_children(
    batch_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Children per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    sort_by: str = Query("index", description="Sort by: index, affinity, confidence")
):
    """
    Get paginated children for a specific batch
    """
    
    try:
        logger.info(f"📊 Fetching children for batch: {batch_id}")
        
        # Get full batch data
        batch_data = await batch_results_service.get_batch_with_children(batch_id)
        
        if not batch_data:
            raise HTTPException(404, f"Batch {batch_id} not found")
        
        children = batch_data.get('child_results', [])
        
        # Apply status filter
        if status_filter:
            children = [c for c in children if c.get('status', '').lower() == status_filter.lower()]
        
        # Apply sorting
        if sort_by == "affinity":
            children.sort(key=lambda x: float(x.get('affinity', 0)), reverse=True)
        elif sort_by == "confidence":
            children.sort(key=lambda x: float(x.get('confidence', 0)), reverse=True)
        else:  # Default to index
            children.sort(key=lambda x: x.get('batch_index', 0))
        
        # Pagination
        total = len(children)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated = children[start_idx:end_idx]
        
        return {
            'batch_id': batch_id,
            'children': paginated,
            'total_children': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 0,
            'aggregated_metrics': batch_data.get('aggregated_metrics', {}),
            'sort_by': sort_by,
            'status_filter': status_filter
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch children: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch children: {str(e)}")

# ============================================
# Statistics Endpoints
# ============================================

@router.get("/statistics")
async def get_results_statistics(
    user_id: str = Query("current_user", description="User ID")
):
    """
    Get statistics about user's jobs (separated by type)
    """
    
    try:
        # Get all results
        all_results = await gcp_results_indexer.get_user_results(user_id, limit=1000)
        
        if not all_results or not all_results.get('results'):
            return {
                'total_jobs': 0,
                'individual_jobs': 0,
                'batch_jobs': 0,
                'batch_children': 0
            }
        
        # Separate jobs by type
        separated = JobClassifier.separate_jobs(all_results['results'])
        
        # Calculate statistics
        stats = {
            'total_jobs': len(all_results['results']),
            'individual_jobs': len(separated[JobType.INDIVIDUAL]),
            'batch_jobs': len(separated[JobType.BATCH_PARENT]),
            'batch_children': len(separated[JobType.BATCH_CHILD]),
            
            # Model distribution
            'models': {},
            
            # Status distribution
            'status_distribution': {
                'completed': 0,
                'failed': 0,
                'running': 0,
                'pending': 0
            },
            
            # Batch statistics
            'batch_statistics': {
                'total_batch_jobs': len(separated[JobType.BATCH_PARENT]),
                'total_child_jobs': sum(
                    JobClassifier.extract_batch_metadata(b).get('total_children', 0) 
                    for b in separated[JobType.BATCH_PARENT]
                ),
                'average_batch_size': 0
            }
        }
        
        # Calculate model distribution for individual jobs
        for job in separated[JobType.INDIVIDUAL]:
            model = job.get('model_name', 'Unknown')
            stats['models'][model] = stats['models'].get(model, 0) + 1
        
        # Calculate status distribution
        for job in all_results['results']:
            status = job.get('status', 'unknown').lower()
            if status in stats['status_distribution']:
                stats['status_distribution'][status] += 1
        
        # Calculate average batch size
        if stats['batch_statistics']['total_batch_jobs'] > 0:
            stats['batch_statistics']['average_batch_size'] = (
                stats['batch_statistics']['total_child_jobs'] / 
                stats['batch_statistics']['total_batch_jobs']
            )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

# ============================================
# Delete Endpoints
# ============================================

@router.delete("/individual/{job_id}")
async def delete_individual_result(
    job_id: str,
    user_id: str = Query("current_user", description="User ID")
):
    """
    Delete an individual job result
    """
    
    try:
        # Verify it's an individual job
        job = unified_job_manager.get_job(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        
        classification = JobClassifier.classify_job(job)
        if classification != JobType.INDIVIDUAL:
            raise HTTPException(400, f"Job {job_id} is not an individual job (type: {classification.value})")
        
        # Delete the job
        success = unified_job_manager.delete_job_result(job_id, user_id)
        
        if not success:
            raise HTTPException(500, "Failed to delete job")
        
        # Invalidate cache
        gcp_results_indexer.invalidate_cache(user_id)
        
        return {"message": f"Individual job {job_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete individual job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")

@router.delete("/batch/{batch_id}")
async def delete_batch_result(
    batch_id: str,
    user_id: str = Query("current_user", description="User ID"),
    delete_children: bool = Query(True, description="Also delete all child jobs")
):
    """
    Delete a batch job and optionally its children
    """
    
    try:
        # Verify it's a batch job
        job = unified_job_manager.get_job(batch_id)
        if not job:
            raise HTTPException(404, "Batch not found")
        
        classification = JobClassifier.classify_job(job)
        if classification != JobType.BATCH_PARENT:
            raise HTTPException(400, f"Job {batch_id} is not a batch job (type: {classification.value})")
        
        if delete_children:
            # Get all child IDs
            batch_meta = JobClassifier.extract_batch_metadata(job)
            child_ids = batch_meta.get('child_job_ids', [])
            
            # Delete all children
            for child_id in child_ids:
                try:
                    unified_job_manager.delete_job_result(child_id, user_id)
                except Exception as e:
                    logger.warning(f"Failed to delete child {child_id}: {e}")
        
        # Delete the batch parent
        success = unified_job_manager.delete_job_result(batch_id, user_id)
        
        if not success:
            raise HTTPException(500, "Failed to delete batch")
        
        # Invalidate cache
        gcp_results_indexer.invalidate_cache(user_id)
        
        return {
            "message": f"Batch {batch_id} deleted successfully",
            "children_deleted": delete_children
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete batch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete batch: {str(e)}")

@router.get("/batch/{batch_id}/download-info")
async def get_batch_download_info(batch_id: str):
    """
    Get download information for a batch - compatible with MyBatches.tsx expectations
    """
    try:
        logger.info(f"📁 Getting download info for batch: {batch_id}")
        
        # Get batch data to find GCP paths
        batch_data = await batch_results_service.get_batch_with_children(batch_id)
        
        if not batch_data:
            raise HTTPException(404, f"Batch {batch_id} not found")
        
        # Build download endpoints based on GCP bucket structure
        # GCP structure: bucket/jobs/{batch_id}/ and bucket/archive/batch/{model}/
        download_endpoints = []
        user_friendly_names = {}
        
        # Check for batch ZIP download
        batch_zip_endpoint = f"/api/v2/batches/{batch_id}/download-all"
        download_endpoints.append(batch_zip_endpoint)
        user_friendly_names["zip"] = f"{batch_data.get('batch_name', 'batch')}_{batch_id}_results.zip"
        
        # Check for individual child downloads if available
        if batch_data.get('child_results'):
            child_count = len(batch_data['child_results'])
            user_friendly_names["archive"] = f"{batch_data.get('batch_name', 'batch')}_{child_count}_predictions.zip"
        
        return {
            "batch_id": batch_id,
            "download_endpoints": download_endpoints,
            "user_friendly_names": user_friendly_names,
            "batch_name": batch_data.get('batch_name', 'Batch'),
            "total_children": batch_data.get('total_children', 0),
            "bucket_path": f"jobs/{batch_id}/",
            "archive_path": f"archive/batch/{batch_data.get('model_name', 'unknown')}/"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get batch download info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch download info: {str(e)}")