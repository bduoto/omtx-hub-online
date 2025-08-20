"""
User-Aware Job Manager - Multi-tenant job management with complete user isolation
Distinguished Engineer Implementation - Production-ready with quotas and security
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from google.cloud import firestore
from google.cloud.firestore import FieldFilter, Query
import uuid

logger = logging.getLogger(__name__)

@dataclass
class UserQuota:
    """User quota configuration"""
    tier: str
    max_concurrent_jobs: int
    max_monthly_jobs: int
    max_storage_gb: float
    max_gpu_minutes_monthly: int
    priority_level: int  # 1=highest, 5=lowest

@dataclass
class UserUsage:
    """Current user usage tracking"""
    user_id: str
    current_jobs: int
    monthly_jobs: int
    storage_used_gb: float
    gpu_minutes_used: int
    last_reset: datetime

class UserAwareJobManager:
    """Enterprise job manager with complete user isolation and quota enforcement"""
    
    def __init__(self):
        # Initialize Firestore client with error handling
        try:
            self.db = firestore.Client()
            print("✅ UserAwareJobManager: Firestore client initialized")
        except Exception as e:
            print(f"⚠️ UserAwareJobManager: Firestore initialization failed: {e}")
            self.db = None
        
        # Tier configurations
        self.tier_quotas = {
            'free': UserQuota(
                tier='free',
                max_concurrent_jobs=1,
                max_monthly_jobs=10,
                max_storage_gb=1.0,
                max_gpu_minutes_monthly=60,
                priority_level=5
            ),
            'basic': UserQuota(
                tier='basic',
                max_concurrent_jobs=3,
                max_monthly_jobs=100,
                max_storage_gb=10.0,
                max_gpu_minutes_monthly=600,
                priority_level=4
            ),
            'pro': UserQuota(
                tier='pro',
                max_concurrent_jobs=10,
                max_monthly_jobs=1000,
                max_storage_gb=100.0,
                max_gpu_minutes_monthly=6000,
                priority_level=3
            ),
            'enterprise': UserQuota(
                tier='enterprise',
                max_concurrent_jobs=50,
                max_monthly_jobs=10000,
                max_storage_gb=1000.0,
                max_gpu_minutes_monthly=60000,
                priority_level=1
            )
        }
        
        logger.info("🔐 UserAwareJobManager initialized with multi-tenant isolation")
    
    async def create_job(self, user_id: str, job_data: Dict[str, Any]) -> str:
        """Create job with user isolation and quota enforcement"""
        
        # Validate user and check quotas
        await self._validate_user_quota(user_id, 'job_creation')
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Prepare user-scoped job document
        user_job_data = {
            'id': job_id,
            'user_id': user_id,
            'status': 'pending',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            **job_data,
            
            # Security metadata
            'tenant_isolation': True,
            'data_classification': 'user_private',
            'access_control': {
                'owner': user_id,
                'readers': [user_id],
                'writers': [user_id]
            }
        }
        
        # Atomic transaction to create job and update usage
        @firestore.transactional
        def create_job_transaction(transaction):
            # Create job in user's collection
            user_job_ref = self.db.collection('users').document(user_id)\
                .collection('jobs').document(job_id)
            transaction.set(user_job_ref, user_job_data)
            
            # Create admin view (for monitoring, no user data)
            admin_job_ref = self.db.collection('admin_jobs').document(job_id)
            admin_job_data = {
                'job_id': job_id,
                'user_id': user_id,  # For admin queries only
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP,
                'tier': self._get_user_tier(user_id),
                'resource_estimate': job_data.get('resource_estimate', {}),
                'cost_estimate': job_data.get('cost_estimate', 0.0)
            }
            transaction.set(admin_job_ref, admin_job_data)
            
            # Update user usage
            usage_ref = self.db.collection('users').document(user_id)\
                .collection('usage').document(self._get_current_month())
            transaction.update(usage_ref, {
                'current_jobs': firestore.Increment(1),
                'monthly_jobs': firestore.Increment(1),
                'last_job_created': firestore.SERVER_TIMESTAMP
            })
        
        # Execute transaction
        transaction = self.db.transaction()
        create_job_transaction(transaction)
        
        logger.info(f"✅ Job created: {job_id} for user {user_id}")
        
        # Emit event for external systems
        await self._emit_user_event(user_id, 'job_created', {
            'job_id': job_id,
            'job_type': job_data.get('type', 'unknown')
        })
        
        return job_id
    
    async def get_job(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job with user validation"""
        
        # Only allow users to access their own jobs
        job_ref = self.db.collection('users').document(user_id)\
            .collection('jobs').document(job_id)
        
        job_doc = job_ref.get()
        
        if not job_doc.exists:
            logger.warning(f"⚠️ Job access denied: {job_id} for user {user_id}")
            return None
        
        job_data = job_doc.to_dict()
        
        # Verify ownership (defense in depth)
        if job_data.get('user_id') != user_id:
            logger.error(f"🚨 Security violation: User {user_id} attempted to access job {job_id}")
            return None
        
        return job_data
    
    async def list_user_jobs(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List jobs for specific user only"""
        
        # Build query for user's jobs only
        query = self.db.collection('users').document(user_id)\
            .collection('jobs')\
            .order_by('created_at', direction=Query.DESCENDING)\
            .limit(limit)\
            .offset(offset)
        
        # Add status filter if provided
        if status_filter:
            query = query.where('status', '==', status_filter)
        
        jobs = []
        for doc in query.stream():
            job_data = doc.to_dict()
            
            # Sanitize sensitive data for API response
            sanitized_job = self._sanitize_job_data(job_data)
            jobs.append(sanitized_job)
        
        logger.debug(f"📋 Listed {len(jobs)} jobs for user {user_id}")
        return jobs
    
    async def update_job_status(
        self, 
        user_id: str, 
        job_id: str, 
        status: str, 
        update_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update job status with user validation"""
        
        update_data = update_data or {}
        
        # Prepare update data
        job_update = {
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP,
            **update_data
        }
        
        @firestore.transactional
        def update_job_transaction(transaction):
            # Update user's job
            user_job_ref = self.db.collection('users').document(user_id)\
                .collection('jobs').document(job_id)
            
            # Verify job exists and belongs to user
            job_doc = user_job_ref.get(transaction=transaction)
            if not job_doc.exists or job_doc.to_dict().get('user_id') != user_id:
                raise ValueError(f"Job {job_id} not found or access denied for user {user_id}")
            
            transaction.update(user_job_ref, job_update)
            
            # Update admin view
            admin_job_ref = self.db.collection('admin_jobs').document(job_id)
            admin_update = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'execution_time': update_data.get('execution_time_seconds'),
                'cost_actual': update_data.get('cost_actual'),
                'gpu_minutes': update_data.get('gpu_minutes_used')
            }
            transaction.update(admin_job_ref, {k: v for k, v in admin_update.items() if v is not None})
            
            # Update usage counters
            if status in ['completed', 'failed']:
                usage_ref = self.db.collection('users').document(user_id)\
                    .collection('usage').document(self._get_current_month())
                
                usage_updates = {
                    'current_jobs': firestore.Increment(-1),
                    'last_job_completed': firestore.SERVER_TIMESTAMP
                }
                
                # Add GPU minutes if provided
                if update_data.get('gpu_minutes_used'):
                    usage_updates['gpu_minutes_used'] = firestore.Increment(
                        update_data['gpu_minutes_used']
                    )
                
                transaction.update(usage_ref, usage_updates)
        
        # Execute transaction
        try:
            transaction = self.db.transaction()
            update_job_transaction(transaction)
            
            logger.info(f"✅ Job {job_id} updated to {status} for user {user_id}")
            
            # Emit event for external systems
            await self._emit_user_event(user_id, 'job_status_changed', {
                'job_id': job_id,
                'status': status,
                'update_data': update_data
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update job {job_id} for user {user_id}: {str(e)}")
            return False
    
    async def get_user_usage(self, user_id: str) -> UserUsage:
        """Get current user usage statistics"""
        
        current_month = self._get_current_month()
        usage_ref = self.db.collection('users').document(user_id)\
            .collection('usage').document(current_month)
        
        usage_doc = usage_ref.get()
        
        if usage_doc.exists:
            usage_data = usage_doc.to_dict()
            return UserUsage(
                user_id=user_id,
                current_jobs=usage_data.get('current_jobs', 0),
                monthly_jobs=usage_data.get('monthly_jobs', 0),
                storage_used_gb=usage_data.get('storage_used_gb', 0.0),
                gpu_minutes_used=usage_data.get('gpu_minutes_used', 0),
                last_reset=usage_data.get('last_reset', datetime.utcnow())
            )
        else:
            # Initialize usage document
            initial_usage = {
                'current_jobs': 0,
                'monthly_jobs': 0,
                'storage_used_gb': 0.0,
                'gpu_minutes_used': 0,
                'last_reset': firestore.SERVER_TIMESTAMP
            }
            usage_ref.set(initial_usage)
            
            return UserUsage(
                user_id=user_id,
                current_jobs=0,
                monthly_jobs=0,
                storage_used_gb=0.0,
                gpu_minutes_used=0,
                last_reset=datetime.utcnow()
            )
    
    async def _validate_user_quota(self, user_id: str, operation: str):
        """Validate user quota before operation"""
        
        user_tier = await self._get_user_tier(user_id)
        quota = self.tier_quotas.get(user_tier, self.tier_quotas['free'])
        usage = await self.get_user_usage(user_id)
        
        # Check concurrent jobs limit
        if operation == 'job_creation':
            if usage.current_jobs >= quota.max_concurrent_jobs:
                raise ValueError(f"Concurrent jobs limit exceeded: {usage.current_jobs}/{quota.max_concurrent_jobs}")
            
            if usage.monthly_jobs >= quota.max_monthly_jobs:
                raise ValueError(f"Monthly jobs limit exceeded: {usage.monthly_jobs}/{quota.max_monthly_jobs}")
            
            if usage.gpu_minutes_used >= quota.max_gpu_minutes_monthly:
                raise ValueError(f"Monthly GPU minutes limit exceeded: {usage.gpu_minutes_used}/{quota.max_gpu_minutes_monthly}")
        
        logger.debug(f"✅ Quota validation passed for user {user_id} operation {operation}")
    
    async def _get_user_tier(self, user_id: str) -> str:
        """Get user tier from user document"""
        
        user_ref = self.db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            return user_doc.to_dict().get('tier', 'free')
        else:
            # Create user document with default tier
            user_ref.set({
                'user_id': user_id,
                'tier': 'free',
                'created_at': firestore.SERVER_TIMESTAMP,
                'settings': {
                    'notifications_enabled': True,
                    'webhook_url': None
                }
            })
            return 'free'
    
    def _get_current_month(self) -> str:
        """Get current month string for usage tracking"""
        return datetime.utcnow().strftime('%Y-%m')
    
    def _sanitize_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from job for API response"""
        
        # Remove internal fields
        sanitized = {k: v for k, v in job_data.items() if not k.startswith('_')}
        
        # Remove sensitive fields
        sensitive_fields = ['access_control', 'tenant_isolation', 'data_classification']
        for field in sensitive_fields:
            sanitized.pop(field, None)
        
        return sanitized
    
    async def _emit_user_event(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Emit event for external systems (webhooks, analytics, etc.)"""
        
        try:
            # Store event in user's event stream
            event_ref = self.db.collection('users').document(user_id)\
                .collection('events').document()
            
            event_data = {
                'event_type': event_type,
                'data': data,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': user_id
            }
            
            event_ref.set(event_data)
            
            # TODO: Integrate with external webhook service
            # await webhook_service.send_webhook(user_id, event_type, data)
            
        except Exception as e:
            logger.error(f"⚠️ Failed to emit event for user {user_id}: {str(e)}")

# Global instance with error handling
try:
    user_aware_job_manager = UserAwareJobManager()
    print("✅ Global UserAwareJobManager initialized")
except Exception as e:
    print(f"⚠️ UserAwareJobManager initialization failed: {e}")
    user_aware_job_manager = None
