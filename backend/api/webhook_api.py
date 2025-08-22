"""
Webhook API endpoints for managing user webhook subscriptions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from services.webhook_service import webhook_service, WebhookConfig
from auth import get_current_user, get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

# Request/Response models
class WebhookRegistrationRequest(BaseModel):
    """Request to register a webhook"""
    url: HttpUrl
    secret: str
    events: List[str] = ["job.completed", "job.failed", "batch.completed"]
    retry_count: int = 3
    timeout_seconds: int = 30

class WebhookResponse(BaseModel):
    """Webhook configuration response"""
    webhook_id: str
    url: str
    events: List[str]
    active: bool
    created_at: datetime
    last_triggered: Optional[datetime] = None
    failure_count: int = 0

class WebhookListResponse(BaseModel):
    """List of webhooks for a user"""
    webhooks: List[WebhookResponse]
    total: int

@router.post("/register", response_model=Dict[str, Any])
async def register_webhook(
    request: WebhookRegistrationRequest,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Register a webhook for job notifications
    
    The webhook will receive HTTP POST requests when jobs complete, fail, or batches finish.
    All webhooks are signed with HMAC-SHA256 for security verification.
    """
    try:
        config = WebhookConfig(
            url=request.url,
            secret=request.secret,
            events=request.events,
            retry_count=request.retry_count,
            timeout_seconds=request.timeout_seconds
        )
        
        result = await webhook_service.register_webhook(current_user_id, config)
        
        logger.info(f"✅ Webhook registered for user {current_user_id}: {request.url}")
        
        return {
            "success": True,
            "webhook_id": result["webhook_id"],
            "message": "Webhook registered successfully",
            "url": str(request.url),
            "events": request.events,
            "signature_header": "X-OMTX-Signature",
            "signature_format": "sha256=<hex_digest>"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to register webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=WebhookListResponse)
async def list_webhooks(
    current_user_id: str = Depends(get_current_user_id)
) -> WebhookListResponse:
    """
    List all webhooks for the current user
    """
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        webhooks_ref = db.collection('users').document(current_user_id)\
            .collection('webhooks')
        
        webhooks = []
        for doc in webhooks_ref.stream():
            webhook_data = doc.to_dict()
            webhooks.append(WebhookResponse(
                webhook_id=doc.id,
                url=webhook_data.get('url', ''),
                events=webhook_data.get('events', []),
                active=webhook_data.get('active', False),
                created_at=webhook_data.get('created_at', datetime.utcnow()),
                last_triggered=webhook_data.get('last_triggered'),
                failure_count=webhook_data.get('failure_count', 0)
            ))
        
        return WebhookListResponse(
            webhooks=webhooks,
            total=len(webhooks)
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to list webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Delete a webhook subscription
    """
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        webhook_ref = db.collection('users').document(current_user_id)\
            .collection('webhooks').document(webhook_id)
        
        webhook_doc = webhook_ref.get()
        if not webhook_doc.exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        webhook_ref.delete()
        
        logger.info(f"🗑️ Webhook deleted: {webhook_id} for user {current_user_id}")
        
        return {
            "success": True,
            "message": "Webhook deleted successfully",
            "webhook_id": webhook_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{webhook_id}/toggle")
async def toggle_webhook(
    webhook_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Enable or disable a webhook
    """
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        webhook_ref = db.collection('users').document(current_user_id)\
            .collection('webhooks').document(webhook_id)
        
        webhook_doc = webhook_ref.get()
        if not webhook_doc.exists:
            raise HTTPException(status_code=404, detail="Webhook not found")
        
        webhook_data = webhook_doc.to_dict()
        current_status = webhook_data.get('active', False)
        new_status = not current_status
        
        webhook_ref.update({
            'active': new_status,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"🔄 Webhook {webhook_id} {'enabled' if new_status else 'disabled'}")
        
        return {
            "success": True,
            "message": f"Webhook {'enabled' if new_status else 'disabled'}",
            "webhook_id": webhook_id,
            "active": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to toggle webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/{webhook_id}")
async def test_webhook(
    webhook_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Send a test webhook notification
    """
    try:
        from services.webhook_service import WebhookPayload
        
        # Send test webhook
        await webhook_service.send_job_completion_webhook(
            job_id="test-job-12345",
            user_id=current_user_id,
            status="completed",
            results={
                "test": True,
                "message": "This is a test webhook notification",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"🧪 Test webhook sent for user {current_user_id}")
        
        return {
            "success": True,
            "message": "Test webhook sent successfully",
            "webhook_id": webhook_id,
            "test_payload": {
                "event": "job.completed",
                "job_id": "test-job-12345",
                "status": "completed"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to send test webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events")
async def list_webhook_events() -> Dict[str, Any]:
    """
    List available webhook events
    """
    return {
        "events": [
            {
                "name": "job.completed",
                "description": "Triggered when an individual job completes successfully"
            },
            {
                "name": "job.failed", 
                "description": "Triggered when an individual job fails"
            },
            {
                "name": "batch.completed",
                "description": "Triggered when a batch of jobs completes (all jobs finished)"
            }
        ],
        "signature_info": {
            "header": "X-OMTX-Signature",
            "format": "sha256=<hex_digest>",
            "algorithm": "HMAC-SHA256",
            "description": "Verify webhook authenticity using your secret key"
        },
        "example_payload": {
            "event": "job.completed",
            "timestamp": "2025-01-20T18:00:00Z",
            "job_id": "job-12345",
            "user_id": "user-67890", 
            "status": "completed",
            "data": {
                "results": {"binding_affinity": 0.85},
                "job_type": "individual"
            },
            "signature": "sha256=abc123..."
        }
    }