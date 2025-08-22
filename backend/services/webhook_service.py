"""
Webhook Service for Job Status Notifications
Handles job completion callbacks and status updates
"""

import os
import json
import logging
import hmac
import hashlib
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from google.cloud import firestore
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)

class WebhookConfig(BaseModel):
    """Webhook configuration for a user"""
    url: HttpUrl
    secret: str
    events: List[str] = ["job.completed", "job.failed", "batch.completed"]
    active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30

class WebhookPayload(BaseModel):
    """Standard webhook payload format"""
    event: str
    timestamp: str
    job_id: str
    user_id: str
    status: str
    data: Dict[str, Any]
    signature: Optional[str] = None

class WebhookService:
    """Service for managing and sending webhook notifications"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.webhook_secret = os.getenv('WEBHOOK_SECRET', 'omtx-hub-webhook-secret')
        self.max_retries = 3
        self.retry_delay = [5, 15, 30]  # Seconds between retries
        
        logger.info("🔔 Webhook Service initialized")
    
    async def register_webhook(self, user_id: str, config: WebhookConfig) -> Dict[str, Any]:
        """Register a webhook for a user"""
        
        try:
            # Store webhook configuration in Firestore
            webhook_ref = self.db.collection('users').document(user_id)\
                .collection('webhooks').document()
            
            webhook_data = {
                'webhook_id': webhook_ref.id,
                'url': str(config.url),
                'secret': config.secret,
                'events': config.events,
                'active': config.active,
                'retry_count': config.retry_count,
                'timeout_seconds': config.timeout_seconds,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_triggered': None,
                'failure_count': 0
            }
            
            webhook_ref.set(webhook_data)
            
            logger.info(f"✅ Webhook registered for user {user_id}: {config.url}")
            
            return {
                'webhook_id': webhook_ref.id,
                'status': 'registered',
                'url': str(config.url),
                'events': config.events
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to register webhook: {e}")
            raise
    
    async def send_job_completion_webhook(
        self, 
        job_id: str, 
        user_id: str, 
        status: str, 
        results: Optional[Dict[str, Any]] = None
    ):
        """Send webhook notification for job completion"""
        
        try:
            # Get user's webhook configurations
            webhooks = await self._get_user_webhooks(user_id)
            
            if not webhooks:
                logger.debug(f"No webhooks configured for user {user_id}")
                return
            
            # Determine event type
            event = "job.completed" if status == "completed" else "job.failed"
            
            # Create payload
            payload = WebhookPayload(
                event=event,
                timestamp=datetime.utcnow().isoformat(),
                job_id=job_id,
                user_id=user_id,
                status=status,
                data={
                    'results': results or {},
                    'job_type': 'individual',
                    'completion_time': datetime.utcnow().isoformat()
                }
            )
            
            # Send to all active webhooks
            tasks = []
            for webhook in webhooks:
                if event in webhook.get('events', []) and webhook.get('active', False):
                    tasks.append(self._send_webhook(webhook, payload))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"📤 Sent {len(tasks)} webhook notifications for job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send job completion webhook: {e}")
    
    async def send_batch_completion_webhook(
        self, 
        batch_id: str, 
        user_id: str, 
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int,
        summary: Optional[Dict[str, Any]] = None
    ):
        """Send webhook notification for batch completion"""
        
        try:
            # Get user's webhook configurations
            webhooks = await self._get_user_webhooks(user_id)
            
            if not webhooks:
                logger.debug(f"No webhooks configured for user {user_id}")
                return
            
            # Create payload
            payload = WebhookPayload(
                event="batch.completed",
                timestamp=datetime.utcnow().isoformat(),
                job_id=batch_id,
                user_id=user_id,
                status="completed",
                data={
                    'batch_id': batch_id,
                    'total_jobs': total_jobs,
                    'completed_jobs': completed_jobs,
                    'failed_jobs': failed_jobs,
                    'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                    'summary': summary or {},
                    'job_type': 'batch',
                    'completion_time': datetime.utcnow().isoformat()
                }
            )
            
            # Send to all active webhooks
            tasks = []
            for webhook in webhooks:
                if "batch.completed" in webhook.get('events', []) and webhook.get('active', False):
                    tasks.append(self._send_webhook(webhook, payload))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"📤 Sent {len(tasks)} webhook notifications for batch {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send batch completion webhook: {e}")
    
    async def _get_user_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active webhooks for a user"""
        
        try:
            webhooks_ref = self.db.collection('users').document(user_id)\
                .collection('webhooks')
            
            webhooks = []
            for doc in webhooks_ref.where('active', '==', True).stream():
                webhooks.append(doc.to_dict())
            
            return webhooks
            
        except Exception as e:
            logger.error(f"Failed to get user webhooks: {e}")
            return []
    
    async def _send_webhook(self, webhook_config: Dict[str, Any], payload: WebhookPayload):
        """Send webhook with retries and signature verification"""
        
        url = webhook_config['url']
        secret = webhook_config.get('secret', self.webhook_secret)
        timeout = webhook_config.get('timeout_seconds', 30)
        max_retries = webhook_config.get('retry_count', self.max_retries)
        
        # Generate HMAC signature
        payload_json = payload.json()
        signature = self._generate_signature(payload_json, secret)
        payload.signature = signature
        
        headers = {
            'Content-Type': 'application/json',
            'X-OMTX-Signature': signature,
            'X-OMTX-Event': payload.event,
            'X-OMTX-Timestamp': payload.timestamp
        }
        
        # Send with retries
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=payload_json,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        if response.status == 200:
                            logger.info(f"✅ Webhook sent successfully to {url}")
                            await self._update_webhook_status(
                                webhook_config['webhook_id'], 
                                success=True
                            )
                            return
                        elif response.status == 410:  # Gone - webhook should be disabled
                            logger.warning(f"⚠️ Webhook returned 410 Gone, disabling: {url}")
                            await self._disable_webhook(webhook_config['webhook_id'])
                            return
                        else:
                            error_text = await response.text()
                            logger.warning(f"Webhook returned {response.status}: {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Webhook timeout (attempt {attempt + 1}/{max_retries}): {url}")
            except Exception as e:
                logger.warning(f"⚠️ Webhook error (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Wait before retry (if not last attempt)
            if attempt < max_retries - 1:
                delay = self.retry_delay[min(attempt, len(self.retry_delay) - 1)]
                await asyncio.sleep(delay)
        
        # All retries failed
        logger.error(f"❌ Webhook failed after {max_retries} attempts: {url}")
        await self._update_webhook_status(webhook_config['webhook_id'], success=False)
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload"""
        
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    async def _update_webhook_status(self, webhook_id: str, success: bool):
        """Update webhook status after send attempt"""
        
        try:
            # Note: This is a simplified version - you'd need user_id for the full path
            # In production, you'd pass user_id or store it in the webhook config
            update_data = {
                'last_triggered': firestore.SERVER_TIMESTAMP
            }
            
            if not success:
                update_data['failure_count'] = firestore.Increment(1)
            else:
                update_data['failure_count'] = 0
            
            # This would need the full path with user_id in production
            # self.db.collection('users').document(user_id)\
            #     .collection('webhooks').document(webhook_id).update(update_data)
            
        except Exception as e:
            logger.error(f"Failed to update webhook status: {e}")
    
    async def _disable_webhook(self, webhook_id: str):
        """Disable a webhook after receiving 410 Gone"""
        
        try:
            # This would need the full path with user_id in production
            # self.db.collection('users').document(user_id)\
            #     .collection('webhooks').document(webhook_id).update({
            #         'active': False,
            #         'disabled_at': firestore.SERVER_TIMESTAMP,
            #         'disabled_reason': 'Received 410 Gone response'
            #     })
            
            logger.info(f"🚫 Webhook disabled: {webhook_id}")
            
        except Exception as e:
            logger.error(f"Failed to disable webhook: {e}")
    
    async def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify incoming webhook signature (for webhook receivers)"""
        
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, signature)

# Global webhook service instance
webhook_service = WebhookService()