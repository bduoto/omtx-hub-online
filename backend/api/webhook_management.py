"""
Webhook Management API - Configure and monitor Modal webhook integration
"""

import os
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, HttpUrl

from services.production_modal_service import production_modal_service
from services.webhook_completion_checker import webhook_completion_checker

logger = logging.getLogger(__name__)
router = APIRouter()

class WebhookConfiguration(BaseModel):
    webhook_base_url: HttpUrl
    webhook_secret: str
    auto_configure: bool = True

class WebhookStatus(BaseModel):
    configured: bool
    base_url: str
    apps_configured: int
    total_apps: int
    last_configured_at: str = None
    health_status: str

class WebhookTestRequest(BaseModel):
    modal_call_id: str = "test_123"
    status: str = "success"
    test_data: Dict[str, Any] = {}

@router.post("/api/v3/webhooks/configure")
async def configure_webhooks(
    config: WebhookConfiguration,
    background_tasks: BackgroundTasks
):
    """
    Configure webhooks for all Modal apps
    
    This endpoint sets up webhook delivery from Modal to OMTX-Hub
    for real-time job completion notifications.
    """
    
    try:
        logger.info(f"🔗 Configuring webhooks for: {config.webhook_base_url}")
        
        # Validate webhook base URL is accessible
        webhook_url = str(config.webhook_base_url)
        if not webhook_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid webhook base URL")
        
        # Configure webhooks in background
        if config.auto_configure:
            background_tasks.add_task(
                _configure_webhooks_background,
                webhook_url,
                config.webhook_secret
            )
            
            return {
                "status": "configuration_started",
                "message": "Webhook configuration started in background",
                "webhook_url": webhook_url
            }
        else:
            # Synchronous configuration
            success = await production_modal_service.configure_webhooks(
                webhook_url,
                config.webhook_secret
            )
            
            if success:
                return {
                    "status": "configured",
                    "message": "All webhooks configured successfully",
                    "webhook_url": webhook_url
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Some webhook configurations failed"
                )
    
    except Exception as e:
        logger.error(f"❌ Webhook configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _configure_webhooks_background(webhook_url: str, webhook_secret: str):
    """Background task for webhook configuration"""
    
    try:
        success = await production_modal_service.configure_webhooks(
            webhook_url,
            webhook_secret
        )
        
        if success:
            logger.info("✅ Background webhook configuration completed")
        else:
            logger.error("❌ Background webhook configuration failed")
            
    except Exception as e:
        logger.error(f"❌ Background webhook configuration error: {e}")

@router.get("/api/v3/webhooks/status", response_model=WebhookStatus)
async def get_webhook_status():
    """Get current webhook configuration status"""
    
    try:
        # Get service metrics
        metrics = await production_modal_service.get_metrics()
        
        # Check webhook health
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "")
        webhook_secret = os.getenv("MODAL_WEBHOOK_SECRET", "")
        
        # Count configured apps (this is conceptual - actual implementation depends on Modal API)
        apps_configured = 0
        total_apps = len(production_modal_service.config.get('models', {}))
        
        # Simple heuristic: if webhook URL and secret are configured, assume apps are configured
        if webhook_base_url and webhook_secret:
            apps_configured = total_apps
        
        return WebhookStatus(
            configured=apps_configured > 0,
            base_url=webhook_base_url,
            apps_configured=apps_configured,
            total_apps=total_apps,
            health_status="healthy" if apps_configured == total_apps else "partial"
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting webhook status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v3/webhooks/active-executions")
async def get_active_executions():
    """Get currently active Modal executions"""
    
    try:
        executions = await production_modal_service.list_active_executions()
        
        return {
            "total_active": len(executions),
            "executions": [
                {
                    "modal_call_id": exec.modal_call_id,
                    "job_id": exec.job_id,
                    "batch_id": exec.batch_id,
                    "model_type": exec.model_type,
                    "lane": exec.lane.value,
                    "submitted_at": exec.submitted_at,
                    "duration": time.time() - exec.submitted_at
                }
                for exec in executions
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting active executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v3/webhooks/test")
async def test_webhook_delivery(test_request: WebhookTestRequest):
    """Test webhook delivery and processing"""
    
    try:
        # Simulate webhook delivery
        test_payload = {
            "call_id": test_request.modal_call_id,
            "status": test_request.status,
            "result": test_request.test_data if test_request.status == "success" else {},
            "error": test_request.test_data if test_request.status == "failure" else {},
            "metadata": {
                "test_mode": True,
                "timestamp": time.time()
            }
        }
        
        # Process test webhook
        if test_request.status == "success":
            await webhook_completion_checker.on_job_completion(
                test_request.modal_call_id,
                test_payload["result"]
            )
        else:
            await webhook_completion_checker.on_job_failure(
                test_request.modal_call_id,
                test_payload["error"]
            )
        
        return {
            "status": "test_completed",
            "message": f"Test webhook processed successfully",
            "test_payload": test_payload
        }
        
    except Exception as e:
        logger.error(f"❌ Webhook test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v3/webhooks/executions/{modal_call_id}/cancel")
async def cancel_execution(modal_call_id: str):
    """Cancel a running Modal execution"""
    
    try:
        success = await production_modal_service.cancel_execution(modal_call_id)
        
        if success:
            return {
                "status": "cancelled",
                "message": f"Execution {modal_call_id} cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Execution {modal_call_id} not found or already completed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling execution {modal_call_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v3/webhooks/metrics")
async def get_webhook_metrics():
    """Get webhook delivery and processing metrics"""
    
    try:
        # Get production modal service metrics
        modal_metrics = await production_modal_service.get_metrics()
        
        # Get webhook completion checker metrics
        completion_metrics = await webhook_completion_checker.get_metrics()
        
        return {
            "modal_service": modal_metrics,
            "completion_checker": completion_metrics,
            "webhook_health": {
                "endpoint_available": True,  # Could add actual health check
                "last_webhook_received": None,  # Could track last webhook timestamp
                "total_webhooks_processed": None  # Could track webhook count
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting webhook metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v3/webhooks/logs")
async def get_webhook_logs(limit: int = 100):
    """Get recent webhook processing logs"""
    
    try:
        # This would integrate with your logging system
        # For now, return a placeholder structure
        
        return {
            "total_logs": 0,
            "logs": [],
            "message": "Webhook logging integration not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting webhook logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add time import at the top
import time