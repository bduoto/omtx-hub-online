"""
Integration Service - External system integration with webhooks and events
Distinguished Engineer Implementation - Production-ready with retry logic and security
"""

import asyncio
import aiohttp
import hmac
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from google.cloud import firestore
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

@dataclass
class WebhookEvent:
    """Structured webhook event"""
    event_type: str
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class IntegrationConfig:
    """Integration configuration for external services"""
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    auth_service_url: Optional[str] = None
    billing_service_url: Optional[str] = None
    analytics_service_url: Optional[str] = None
    pubsub_topic: Optional[str] = None

class IntegrationService:
    """Enterprise integration service with comprehensive external system support"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.webhook_client = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        
        # Pub/Sub for event streaming (optional)
        self.pubsub_publisher = None
        try:
            self.pubsub_publisher = pubsub_v1.PublisherClient()
            logger.info("✅ Pub/Sub publisher initialized")
        except Exception as e:
            logger.warning(f"⚠️ Pub/Sub not available: {str(e)}")
        
        # Event queue for failed webhooks
        self.failed_webhooks = asyncio.Queue()
        
        # Start background retry processor
        asyncio.create_task(self._process_failed_webhooks())
        
        logger.info("🔌 IntegrationService initialized with external system support")
    
    async def emit_user_event(
        self, 
        user_id: str, 
        event_type: str, 
        data: Dict[str, Any],
        immediate: bool = False
    ):
        """Emit event to all configured external systems"""
        
        try:
            # Get user's integration configuration
            config = await self._get_user_integration_config(user_id)
            
            # Create event
            event = WebhookEvent(
                event_type=event_type,
                user_id=user_id,
                data=data,
                timestamp=datetime.utcnow()
            )
            
            # Store event in user's event stream
            await self._store_event(event)
            
            # Send to configured integrations
            tasks = []
            
            if config.webhook_url:
                tasks.append(self._send_webhook(event, config))
            
            if config.billing_service_url and event_type in ['job_completed', 'job_failed']:
                tasks.append(self._send_billing_event(event, config))
            
            if self.pubsub_publisher and config.pubsub_topic:
                tasks.append(self._publish_to_pubsub(event, config))
            
            # Execute all integrations concurrently
            if tasks:
                if immediate:
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # Fire and forget for non-critical events
                    asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
            
            logger.debug(f"📡 Event emitted: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to emit event for user {user_id}: {str(e)}")
    
    async def _send_webhook(self, event: WebhookEvent, config: IntegrationConfig):
        """Send webhook with signature and retry logic"""
        
        try:
            # Prepare payload
            payload = {
                "event": event.event_type,
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
                "retry_count": event.retry_count
            }
            
            payload_json = json.dumps(payload, sort_keys=True)
            
            # Generate signature for security
            signature = ""
            if config.webhook_secret:
                signature = hmac.new(
                    config.webhook_secret.encode(),
                    payload_json.encode(),
                    hashlib.sha256
                ).hexdigest()
            
            # Send webhook
            headers = {
                "Content-Type": "application/json",
                "X-OMTX-Event": event.event_type,
                "X-OMTX-Timestamp": str(int(event.timestamp.timestamp())),
                "X-OMTX-Signature": f"sha256={signature}" if signature else "",
                "User-Agent": "OMTX-Hub/1.0"
            }
            
            async with self.webhook_client.post(
                config.webhook_url,
                data=payload_json,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    logger.info(f"✅ Webhook sent successfully for user {event.user_id}")
                    
                    # Log successful webhook
                    await self._log_webhook_result(event, "success", response.status)
                    
                elif response.status in [429, 502, 503, 504]:
                    # Retryable errors
                    logger.warning(f"⚠️ Webhook retryable error {response.status} for user {event.user_id}")
                    await self._queue_webhook_retry(event, config, f"HTTP {response.status}")
                    
                else:
                    # Non-retryable errors
                    error_text = await response.text()
                    logger.error(f"❌ Webhook failed {response.status} for user {event.user_id}: {error_text}")
                    await self._log_webhook_result(event, "failed", response.status, error_text)
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Webhook timeout for user {event.user_id}")
            await self._queue_webhook_retry(event, config, "timeout")
            
        except Exception as e:
            logger.error(f"❌ Webhook error for user {event.user_id}: {str(e)}")
            await self._queue_webhook_retry(event, config, str(e))
    
    async def _send_billing_event(self, event: WebhookEvent, config: IntegrationConfig):
        """Send usage data to billing service"""
        
        try:
            # Extract billing-relevant data
            billing_data = {
                "user_id": event.user_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "usage": {
                    "gpu_minutes": event.data.get("gpu_minutes_used", 0),
                    "storage_gb": event.data.get("storage_used_gb", 0),
                    "api_calls": 1,
                    "job_type": event.data.get("job_type", "unknown")
                },
                "cost_estimate": event.data.get("cost_actual", 0.0)
            }
            
            async with self.webhook_client.post(
                f"{config.billing_service_url}/usage",
                json=billing_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    logger.info(f"💰 Billing event sent for user {event.user_id}")
                else:
                    logger.warning(f"⚠️ Billing service error {response.status} for user {event.user_id}")
                    
        except Exception as e:
            logger.error(f"❌ Billing event error for user {event.user_id}: {str(e)}")
    
    async def _publish_to_pubsub(self, event: WebhookEvent, config: IntegrationConfig):
        """Publish event to Pub/Sub topic"""
        
        try:
            if not self.pubsub_publisher:
                return
            
            # Prepare message
            message_data = {
                "event_type": event.event_type,
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
            
            # Publish message
            topic_path = self.pubsub_publisher.topic_path(
                project=config.pubsub_topic.split('/')[1],
                topic=config.pubsub_topic.split('/')[-1]
            )
            
            future = self.pubsub_publisher.publish(
                topic_path,
                json.dumps(message_data).encode(),
                event_type=event.event_type,
                user_id=event.user_id
            )
            
            # Wait for publish to complete
            message_id = future.result(timeout=10)
            logger.info(f"📢 Event published to Pub/Sub: {message_id}")
            
        except Exception as e:
            logger.error(f"❌ Pub/Sub publish error: {str(e)}")
    
    async def _get_user_integration_config(self, user_id: str) -> IntegrationConfig:
        """Get user's integration configuration"""
        
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                settings = user_data.get('settings', {})
                
                return IntegrationConfig(
                    webhook_url=settings.get('webhook_url'),
                    webhook_secret=settings.get('webhook_secret'),
                    auth_service_url=settings.get('auth_service_url'),
                    billing_service_url=settings.get('billing_service_url'),
                    analytics_service_url=settings.get('analytics_service_url'),
                    pubsub_topic=settings.get('pubsub_topic')
                )
            else:
                return IntegrationConfig()
                
        except Exception as e:
            logger.error(f"❌ Failed to get integration config for user {user_id}: {str(e)}")
            return IntegrationConfig()
    
    async def _store_event(self, event: WebhookEvent):
        """Store event in user's event stream"""
        
        try:
            event_ref = self.db.collection('users').document(event.user_id)\
                .collection('events').document()
            
            event_data = {
                'event_type': event.event_type,
                'data': event.data,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'retry_count': event.retry_count
            }
            
            event_ref.set(event_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to store event for user {event.user_id}: {str(e)}")
    
    async def _queue_webhook_retry(self, event: WebhookEvent, config: IntegrationConfig, error: str):
        """Queue webhook for retry"""
        
        if event.retry_count < event.max_retries:
            event.retry_count += 1
            await self.failed_webhooks.put((event, config, error))
            logger.info(f"🔄 Webhook queued for retry {event.retry_count}/{event.max_retries}")
        else:
            logger.error(f"❌ Webhook max retries exceeded for user {event.user_id}")
            await self._log_webhook_result(event, "max_retries_exceeded", 0, error)
    
    async def _process_failed_webhooks(self):
        """Background processor for failed webhook retries"""
        
        while True:
            try:
                # Wait for failed webhook
                event, config, error = await self.failed_webhooks.get()
                
                # Exponential backoff delay
                delay = min(300, 2 ** event.retry_count)  # Max 5 minutes
                await asyncio.sleep(delay)
                
                # Retry webhook
                await self._send_webhook(event, config)
                
            except Exception as e:
                logger.error(f"❌ Webhook retry processor error: {str(e)}")
                await asyncio.sleep(60)  # Wait before continuing
    
    async def _log_webhook_result(
        self, 
        event: WebhookEvent, 
        status: str, 
        http_status: int, 
        error: Optional[str] = None
    ):
        """Log webhook delivery result"""
        
        try:
            log_ref = self.db.collection('users').document(event.user_id)\
                .collection('webhook_logs').document()
            
            log_data = {
                'event_type': event.event_type,
                'status': status,
                'http_status': http_status,
                'retry_count': event.retry_count,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'error': error
            }
            
            log_ref.set(log_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to log webhook result: {str(e)}")
    
    async def validate_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        secret: str
    ) -> bool:
        """Validate incoming webhook signature"""
        
        try:
            expected_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"❌ Webhook signature validation error: {str(e)}")
            return False
    
    async def get_user_events(
        self, 
        user_id: str, 
        limit: int = 50, 
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's event history"""
        
        try:
            query = self.db.collection('users').document(user_id)\
                .collection('events')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)
            
            if event_type:
                query = query.where('event_type', '==', event_type)
            
            events = []
            for doc in query.stream():
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Failed to get events for user {user_id}: {str(e)}")
            return []
    
    async def get_webhook_logs(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's webhook delivery logs"""
        
        try:
            query = self.db.collection('users').document(user_id)\
                .collection('webhook_logs')\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)
            
            logs = []
            for doc in query.stream():
                log_data = doc.to_dict()
                log_data['id'] = doc.id
                logs.append(log_data)
            
            return logs
            
        except Exception as e:
            logger.error(f"❌ Failed to get webhook logs for user {user_id}: {str(e)}")
            return []
    
    async def update_user_integration_config(
        self, 
        user_id: str, 
        config: Dict[str, Any]
    ) -> bool:
        """Update user's integration configuration"""
        
        try:
            user_ref = self.db.collection('users').document(user_id)
            
            # Validate webhook URL if provided
            if 'webhook_url' in config and config['webhook_url']:
                if not config['webhook_url'].startswith(('http://', 'https://')):
                    raise ValueError("Webhook URL must start with http:// or https://")
            
            # Update settings
            user_ref.update({
                'settings': config,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"✅ Integration config updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update integration config for user {user_id}: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        
        try:
            await self.webhook_client.close()
            logger.info("✅ IntegrationService cleanup complete")
        except Exception as e:
            logger.error(f"❌ IntegrationService cleanup error: {str(e)}")

# Global integration service instance
integration_service = IntegrationService()
