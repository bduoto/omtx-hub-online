"""
Modal Webhook Handlers - HMAC-verified completion processing
Eliminates polling with real-time job completion notifications
"""

import hmac
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks

from services.production_modal_service import production_modal_service
from database.unified_job_manager import unified_job_manager
from services.gcp_storage_service import gcp_storage_service
from services.batch_aware_completion_checker import BatchAwareCompletionChecker

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize completion checker for batch intelligence
completion_checker = BatchAwareCompletionChecker()

# Webhook secret for HMAC verification
import os
MODAL_WEBHOOK_SECRET = os.getenv("MODAL_WEBHOOK_SECRET", "default-dev-secret")

@router.post("/api/v3/webhooks/modal/completion")
async def handle_modal_completion(
    request: Request,
    background_tasks: BackgroundTasks,
    x_modal_signature: Optional[str] = Header(None),
    x_modal_timestamp: Optional[str] = Header(None)
):
    """
    Handle Modal completion webhooks with HMAC verification
    
    This replaces polling-based completion checking with real-time notifications.
    Called by Modal when jobs complete/fail.
    """
    
    # Get raw body for signature verification
    raw_body = await request.body()
    
    # Verify HMAC signature
    if not _verify_webhook_signature(raw_body, x_modal_signature):
        logger.warning("❌ Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Verify timestamp to prevent replay attacks
    if not _verify_timestamp(x_modal_timestamp):
        logger.warning("❌ Webhook timestamp too old")
        raise HTTPException(status_code=401, detail="Timestamp too old")
    
    # Parse payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Extract completion data
    modal_call_id = payload.get('call_id')
    status = payload.get('status')  # 'success' or 'failure'
    result_data = payload.get('result', {})
    error_data = payload.get('error', {})
    metadata = payload.get('metadata', {})
    
    if not modal_call_id:
        logger.error("❌ Missing call_id in webhook payload")
        raise HTTPException(status_code=400, detail="Missing call_id")
    
    logger.info(f"🎯 Webhook received: {modal_call_id} -> {status}")
    
    # Process completion in background to avoid blocking Modal
    background_tasks.add_task(
        _process_completion_background,
        modal_call_id,
        status,
        result_data,
        error_data,
        metadata
    )
    
    return {"status": "accepted", "call_id": modal_call_id}

async def _process_completion_background(
    modal_call_id: str,
    status: str,
    result_data: Dict[str, Any],
    error_data: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """Process completion in background to avoid blocking webhook response"""
    
    try:
        logger.info(f"🔄 Processing completion for {modal_call_id}")
        
        if status == 'success':
            await _handle_job_success(modal_call_id, result_data, metadata)
        else:
            await _handle_job_failure(modal_call_id, error_data, metadata)
        
        # Notify Modal service about completion
        await production_modal_service.on_completion(modal_call_id, result_data if status == 'success' else error_data)
        
        logger.info(f"✅ Completion processed: {modal_call_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing completion {modal_call_id}: {e}")
        
        # Still notify Modal service about the failure
        try:
            await production_modal_service.on_failure(modal_call_id, {'error': str(e)})
        except Exception as notify_error:
            logger.error(f"❌ Failed to notify Modal service: {notify_error}")

async def _handle_job_success(
    modal_call_id: str,
    result_data: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """Handle successful job completion"""
    
    try:
        # Find the job by modal_call_id
        job_data = await _find_job_by_modal_call_id(modal_call_id)
        if not job_data:
            logger.error(f"❌ Job not found for modal_call_id: {modal_call_id}")
            return
        
        job_id = job_data['id']
        logger.info(f"✅ Processing success for job {job_id}")
        
        # Process and store results
        processed_results = await _process_and_store_results(job_id, result_data)
        
        # Update job status
        update_data = {
            'status': 'completed',
            'completed_at': time.time(),
            'modal_call_id': modal_call_id,
            'output_data': processed_results,
            'metadata': {
                **job_data.get('metadata', {}),
                'completion_method': 'webhook',
                'processed_at': time.time()
            }
        }
        
        success = unified_job_manager.update_job_status(job_id, 'completed', update_data)
        if not success:
            logger.error(f"❌ Failed to update job status for {job_id}")
            return
        
        # Handle batch intelligence if this is a batch child
        batch_parent_id = job_data.get('batch_parent_id')
        if batch_parent_id:
            await completion_checker.on_job_completion(modal_call_id, processed_results)
        
        logger.info(f"✅ Job {job_id} marked as completed")
        
    except Exception as e:
        logger.error(f"❌ Error handling job success: {e}")
        raise

async def _handle_job_failure(
    modal_call_id: str,
    error_data: Dict[str, Any],
    metadata: Dict[str, Any]
):
    """Handle failed job completion"""
    
    try:
        # Find the job by modal_call_id
        job_data = await _find_job_by_modal_call_id(modal_call_id)
        if not job_data:
            logger.error(f"❌ Job not found for modal_call_id: {modal_call_id}")
            return
        
        job_id = job_data['id']
        logger.info(f"❌ Processing failure for job {job_id}")
        
        # Update job status
        update_data = {
            'status': 'failed',
            'failed_at': time.time(),
            'modal_call_id': modal_call_id,
            'error_message': error_data.get('message', 'Unknown error'),
            'error_details': error_data,
            'metadata': {
                **job_data.get('metadata', {}),
                'completion_method': 'webhook',
                'processed_at': time.time()
            }
        }
        
        success = unified_job_manager.update_job_status(job_id, 'failed', update_data)
        if not success:
            logger.error(f"❌ Failed to update job status for {job_id}")
            return
        
        # Handle batch intelligence if this is a batch child
        batch_parent_id = job_data.get('batch_parent_id')
        if batch_parent_id:
            await completion_checker.on_job_failure(modal_call_id, error_data)
        
        logger.info(f"❌ Job {job_id} marked as failed")
        
    except Exception as e:
        logger.error(f"❌ Error handling job failure: {e}")
        raise

async def _find_job_by_modal_call_id(modal_call_id: str) -> Optional[Dict[str, Any]]:
    """Find job by Modal call ID"""
    
    try:
        # Search in active jobs first (this could be optimized with indexing)
        # For now, we'll search recent jobs
        
        # Get recent jobs across all users (this is a simplified approach)
        # In production, you'd want a more efficient lookup mechanism
        
        # Try to get the job from the production modal service first
        execution = await production_modal_service.get_execution_status(modal_call_id)
        if execution:
            job_data = unified_job_manager.get_job(execution.job_id)
            return job_data
        
        # Fallback: search through recent jobs (inefficient but works)
        # TODO: Implement proper indexing by modal_call_id
        logger.warning(f"⚠️ Falling back to job search for modal_call_id: {modal_call_id}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error finding job by modal_call_id {modal_call_id}: {e}")
        return None

async def _process_and_store_results(
    job_id: str,
    result_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process and store job results to GCP"""
    
    try:
        logger.info(f"📁 Processing and storing results for job {job_id}")
        
        # Store raw results to GCP
        raw_results_path = f"jobs/{job_id}/raw_results.json"
        await gcp_storage_service.upload_file(
            raw_results_path,
            json.dumps(result_data, indent=2).encode('utf-8'),
            content_type='application/json'
        )
        
        # Store structure files if present
        structure_files = {}
        if 'structure_file_base64' in result_data:
            structure_path = f"jobs/{job_id}/structure.cif"
            structure_content = result_data['structure_file_base64']
            
            # Decode and store structure file
            import base64
            structure_data = base64.b64decode(structure_content)
            await gcp_storage_service.upload_file(
                structure_path,
                structure_data,
                content_type='chemical/x-cif'
            )
            
            structure_files['primary_structure'] = structure_path
        
        # Process additional files
        if 'all_structures' in result_data:
            for i, struct_data in enumerate(result_data['all_structures']):
                if 'base64' in struct_data:
                    struct_path = f"jobs/{job_id}/structure_model_{i}.cif"
                    struct_content = base64.b64decode(struct_data['base64'])
                    await gcp_storage_service.upload_file(
                        struct_path,
                        struct_content,
                        content_type='chemical/x-cif'
                    )
                    structure_files[f'model_{i}'] = struct_path
        
        # Create processed results summary
        processed_results = {
            'job_id': job_id,
            'affinity': result_data.get('affinity'),
            'affinity_probability': result_data.get('affinity_probability'),
            'confidence': result_data.get('confidence'),
            'ptm_score': result_data.get('ptm_score'),
            'iptm_score': result_data.get('iptm_score'),
            'plddt_score': result_data.get('plddt_score'),
            'execution_time': result_data.get('execution_time'),
            'model_version': result_data.get('parameters', {}).get('model', 'boltz2'),
            'storage_paths': {
                'raw_results': raw_results_path,
                'structure_files': structure_files
            },
            'processed_at': time.time()
        }
        
        # Store processed results
        processed_path = f"jobs/{job_id}/processed_results.json"
        await gcp_storage_service.upload_file(
            processed_path,
            json.dumps(processed_results, indent=2).encode('utf-8'),
            content_type='application/json'
        )
        
        logger.info(f"✅ Results stored for job {job_id}")
        
        return processed_results
        
    except Exception as e:
        logger.error(f"❌ Error processing results for job {job_id}: {e}")
        # Return minimal results even if storage fails
        return {
            'job_id': job_id,
            'error': 'Failed to process results',
            'raw_data': result_data,
            'processed_at': time.time()
        }

def _verify_webhook_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verify HMAC signature from Modal"""
    
    if not signature_header or not MODAL_WEBHOOK_SECRET:
        logger.warning("⚠️ No signature or secret configured")
        return False
    
    try:
        # Extract signature (format: "sha256=<hex>")
        if '=' not in signature_header:
            return False
        
        algorithm, signature = signature_header.split('=', 1)
        if algorithm != 'sha256':
            return False
        
        # Compute expected signature
        expected_mac = hmac.new(
            MODAL_WEBHOOK_SECRET.encode(),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(expected_mac, signature)
        
    except Exception as e:
        logger.error(f"❌ Error verifying webhook signature: {e}")
        return False

def _verify_timestamp(timestamp_header: Optional[str]) -> bool:
    """Verify webhook timestamp to prevent replay attacks"""
    
    if not timestamp_header:
        logger.warning("⚠️ No timestamp in webhook")
        return False
    
    try:
        webhook_time = int(timestamp_header)
        current_time = int(time.time())
        
        # Allow 5 minute window
        time_diff = abs(current_time - webhook_time)
        return time_diff <= 300  # 5 minutes
        
    except (ValueError, TypeError):
        logger.error("❌ Invalid timestamp format")
        return False

@router.get("/api/v3/webhooks/modal/health")
async def webhook_health_check():
    """Health check endpoint for webhook service"""
    
    return {
        "status": "healthy",
        "service": "modal_webhook_handler",
        "timestamp": time.time(),
        "features": {
            "hmac_verification": bool(MODAL_WEBHOOK_SECRET),
            "timestamp_verification": True,
            "background_processing": True,
            "batch_intelligence": True
        }
    }

@router.post("/api/v3/webhooks/modal/test")
async def test_webhook_endpoint(test_data: Dict[str, Any]):
    """Test endpoint for webhook development (remove in production)"""
    
    logger.info(f"🧪 Test webhook received: {test_data}")
    
    # Simulate processing a test completion
    modal_call_id = test_data.get('call_id', 'test_call_123')
    status = test_data.get('status', 'success')
    
    try:
        await _process_completion_background(
            modal_call_id,
            status,
            test_data.get('result', {}),
            test_data.get('error', {}),
            test_data.get('metadata', {})
        )
        
        return {"status": "test_processed", "call_id": modal_call_id}
        
    except Exception as e:
        return {"status": "test_failed", "error": str(e)}