"""
Resource Quota Manager - Intelligent resource allocation and quota tracking
Manages GPU time, storage, and concurrent job quotas per user tier
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import os

from middleware.rate_limiter import UserTier

logger = logging.getLogger(__name__)

# Redis integration (optional dependency)
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Redis not available for quota persistence")
    REDIS_AVAILABLE = False

class ResourceType(Enum):
    """Types of resources managed by quota system"""
    GPU_MINUTES = "gpu_minutes"
    STORAGE_GB = "storage_gb"
    CONCURRENT_JOBS = "concurrent_jobs"
    CONCURRENT_BATCHES = "concurrent_batches"
    TOTAL_JOBS_MONTHLY = "total_jobs_monthly"
    PRIORITY_QUEUE_ACCESS = "priority_queue_access"

@dataclass
class ResourceQuota:
    """Resource quota configuration"""
    resource_type: ResourceType
    total_limit: float
    used_amount: float
    reset_period_days: int
    last_reset: float
    soft_limit_percentage: float = 80.0  # Warning threshold
    
    @property
    def remaining(self) -> float:
        """Get remaining quota"""
        return max(0, self.total_limit - self.used_amount)
    
    @property
    def usage_percentage(self) -> float:
        """Get usage as percentage"""
        if self.total_limit == 0:
            return 100.0
        return min(100.0, (self.used_amount / self.total_limit) * 100)
    
    @property
    def is_over_soft_limit(self) -> bool:
        """Check if over soft limit (warning threshold)"""
        return self.usage_percentage >= self.soft_limit_percentage
    
    @property
    def is_exhausted(self) -> bool:
        """Check if quota is exhausted"""
        return self.remaining <= 0
    
    def should_reset(self) -> bool:
        """Check if quota should be reset based on time"""
        if self.reset_period_days <= 0:
            return False
        
        reset_interval = self.reset_period_days * 24 * 3600  # Convert to seconds
        return time.time() - self.last_reset >= reset_interval

class QuotaConfig:
    """Resource quota configurations by user tier"""
    
    QUOTAS = {
        UserTier.DEFAULT: {
            ResourceType.GPU_MINUTES: {
                'total_limit': 60,      # 1 hour GPU time per month
                'reset_period_days': 30,
                'soft_limit_percentage': 80.0
            },
            ResourceType.STORAGE_GB: {
                'total_limit': 1.0,     # 1 GB storage
                'reset_period_days': 0,  # No reset - persistent
                'soft_limit_percentage': 85.0
            },
            ResourceType.CONCURRENT_JOBS: {
                'total_limit': 2,       # 2 concurrent jobs
                'reset_period_days': 0,  # No reset - real-time limit
                'soft_limit_percentage': 100.0
            },
            ResourceType.CONCURRENT_BATCHES: {
                'total_limit': 1,       # 1 concurrent batch
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.TOTAL_JOBS_MONTHLY: {
                'total_limit': 50,      # 50 jobs per month
                'reset_period_days': 30,
                'soft_limit_percentage': 80.0
            },
            ResourceType.PRIORITY_QUEUE_ACCESS: {
                'total_limit': 0,       # No priority access
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            }
        },
        
        UserTier.PREMIUM: {
            ResourceType.GPU_MINUTES: {
                'total_limit': 300,     # 5 hours GPU time per month
                'reset_period_days': 30,
                'soft_limit_percentage': 80.0
            },
            ResourceType.STORAGE_GB: {
                'total_limit': 10.0,    # 10 GB storage
                'reset_period_days': 0,
                'soft_limit_percentage': 85.0
            },
            ResourceType.CONCURRENT_JOBS: {
                'total_limit': 5,       # 5 concurrent jobs
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.CONCURRENT_BATCHES: {
                'total_limit': 3,       # 3 concurrent batches
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.TOTAL_JOBS_MONTHLY: {
                'total_limit': 500,     # 500 jobs per month
                'reset_period_days': 30,
                'soft_limit_percentage': 80.0
            },
            ResourceType.PRIORITY_QUEUE_ACCESS: {
                'total_limit': 1,       # Priority access available
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            }
        },
        
        UserTier.ENTERPRISE: {
            ResourceType.GPU_MINUTES: {
                'total_limit': 1800,    # 30 hours GPU time per month
                'reset_period_days': 30,
                'soft_limit_percentage': 85.0
            },
            ResourceType.STORAGE_GB: {
                'total_limit': 100.0,   # 100 GB storage
                'reset_period_days': 0,
                'soft_limit_percentage': 90.0
            },
            ResourceType.CONCURRENT_JOBS: {
                'total_limit': 20,      # 20 concurrent jobs
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.CONCURRENT_BATCHES: {
                'total_limit': 10,      # 10 concurrent batches
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.TOTAL_JOBS_MONTHLY: {
                'total_limit': 5000,    # 5000 jobs per month
                'reset_period_days': 30,
                'soft_limit_percentage': 85.0
            },
            ResourceType.PRIORITY_QUEUE_ACCESS: {
                'total_limit': 1,       # Priority access available
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            }
        },
        
        UserTier.ADMIN: {
            ResourceType.GPU_MINUTES: {
                'total_limit': 10000,   # Virtually unlimited
                'reset_period_days': 30,
                'soft_limit_percentage': 95.0
            },
            ResourceType.STORAGE_GB: {
                'total_limit': 1000.0,  # 1 TB storage
                'reset_period_days': 0,
                'soft_limit_percentage': 95.0
            },
            ResourceType.CONCURRENT_JOBS: {
                'total_limit': 100,     # 100 concurrent jobs
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.CONCURRENT_BATCHES: {
                'total_limit': 50,      # 50 concurrent batches
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            },
            ResourceType.TOTAL_JOBS_MONTHLY: {
                'total_limit': 100000,  # Virtually unlimited
                'reset_period_days': 30,
                'soft_limit_percentage': 95.0
            },
            ResourceType.PRIORITY_QUEUE_ACCESS: {
                'total_limit': 1,       # Priority access available
                'reset_period_days': 0,
                'soft_limit_percentage': 100.0
            }
        }
    }

@dataclass
class ResourceEstimate:
    """Estimated resource requirements for a job/batch"""
    gpu_minutes: float
    storage_gb: float
    concurrent_jobs: int
    is_priority: bool = False
    estimated_completion_time: Optional[float] = None
    
    def __post_init__(self):
        # Ensure reasonable estimates
        self.gpu_minutes = max(0.1, self.gpu_minutes)  # Minimum 0.1 minute
        self.storage_gb = max(0.001, self.storage_gb)   # Minimum 1 MB
        self.concurrent_jobs = max(1, self.concurrent_jobs)  # At least 1 job

class ResourceQuotaManager:
    """
    Intelligent resource quota management system
    
    Features:
    - Per-user tier resource quotas
    - Real-time usage tracking
    - Automatic quota resets
    - Resource estimation and pre-allocation
    - Redis persistence with fallback
    - Soft limit warnings
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        self.redis_available = False
        
        # In-memory fallback storage
        self.user_quotas: Dict[str, Dict[ResourceType, ResourceQuota]] = {}
        
        # Active resource tracking
        self.active_jobs: Dict[str, Dict[str, ResourceEstimate]] = {}  # user_id -> {job_id: estimate}
        self.active_batches: Dict[str, Dict[str, ResourceEstimate]] = {}  # user_id -> {batch_id: estimate}
        
        # Performance metrics
        self.metrics = {
            'quota_checks': 0,
            'quota_violations': 0,
            'quotas_reset': 0,
            'redis_errors': 0,
            'fallback_used': 0
        }
    
    async def initialize(self):
        """Initialize Redis connection and load quotas"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test connection
                await self.redis_client.ping()
                self.redis_available = True
                logger.info(f"✅ Resource quota manager connected to Redis: {self.redis_url}")
                
            except Exception as e:
                logger.warning(f"⚠️ Redis not available, using in-memory quota tracking: {e}")
                self.redis_available = False
        else:
            logger.warning("⚠️ Redis not available, using in-memory quota tracking")
            self.redis_available = False
    
    async def get_user_quotas(self, user_id: str, user_tier: UserTier) -> Dict[ResourceType, ResourceQuota]:
        """Get or initialize user quotas"""
        
        # Try Redis first
        if self.redis_available and self.redis_client:
            try:
                quotas = await self._load_quotas_from_redis(user_id, user_tier)
                if quotas:
                    return quotas
            except Exception as e:
                logger.warning(f"⚠️ Failed to load quotas from Redis: {e}")
                self.metrics['redis_errors'] += 1
        
        # Fallback to in-memory
        self.metrics['fallback_used'] += 1
        return await self._get_quotas_from_memory(user_id, user_tier)
    
    async def _load_quotas_from_redis(self, user_id: str, user_tier: UserTier) -> Optional[Dict[ResourceType, ResourceQuota]]:
        """Load user quotas from Redis"""
        
        try:
            key = f"quota:{user_id}"
            quota_data = await self.redis_client.hgetall(key)
            
            if not quota_data:
                # Initialize new quotas
                return await self._initialize_user_quotas(user_id, user_tier)
            
            # Parse stored quotas
            quotas = {}
            for resource_type in ResourceType:
                resource_key = resource_type.value
                if resource_key in quota_data:
                    quota_json = quota_data[resource_key]
                    quota_dict = json.loads(quota_json)
                    quotas[resource_type] = ResourceQuota(**quota_dict)
                else:
                    # Initialize missing quota
                    quotas[resource_type] = await self._create_quota(resource_type, user_tier)
            
            # Check for auto-resets
            await self._check_and_reset_quotas(user_id, quotas)
            
            return quotas
            
        except Exception as e:
            logger.error(f"❌ Error loading quotas from Redis: {e}")
            return None
    
    async def _get_quotas_from_memory(self, user_id: str, user_tier: UserTier) -> Dict[ResourceType, ResourceQuota]:
        """Get quotas from in-memory storage"""
        
        if user_id not in self.user_quotas:
            self.user_quotas[user_id] = await self._initialize_user_quotas(user_id, user_tier)
        
        quotas = self.user_quotas[user_id]
        
        # Check for auto-resets
        await self._check_and_reset_quotas(user_id, quotas)
        
        return quotas
    
    async def _initialize_user_quotas(self, user_id: str, user_tier: UserTier) -> Dict[ResourceType, ResourceQuota]:
        """Initialize quotas for a new user"""
        
        quotas = {}
        for resource_type in ResourceType:
            quotas[resource_type] = await self._create_quota(resource_type, user_tier)
        
        # Save to Redis if available
        if self.redis_available and self.redis_client:
            try:
                await self._save_quotas_to_redis(user_id, quotas)
            except Exception as e:
                logger.warning(f"⚠️ Failed to save quotas to Redis: {e}")
        
        return quotas
    
    async def _create_quota(self, resource_type: ResourceType, user_tier: UserTier) -> ResourceQuota:
        """Create a new resource quota based on tier"""
        
        config = QuotaConfig.QUOTAS[user_tier][resource_type]
        
        return ResourceQuota(
            resource_type=resource_type,
            total_limit=config['total_limit'],
            used_amount=0.0,
            reset_period_days=config['reset_period_days'],
            last_reset=time.time(),
            soft_limit_percentage=config['soft_limit_percentage']
        )
    
    async def _check_and_reset_quotas(self, user_id: str, quotas: Dict[ResourceType, ResourceQuota]):
        """Check and reset quotas if needed"""
        
        reset_needed = False
        
        for resource_type, quota in quotas.items():
            if quota.should_reset():
                logger.info(f"🔄 Resetting {resource_type.value} quota for user {user_id}")
                quota.used_amount = 0.0
                quota.last_reset = time.time()
                reset_needed = True
                self.metrics['quotas_reset'] += 1
        
        if reset_needed:
            # Save updated quotas
            if self.redis_available and self.redis_client:
                try:
                    await self._save_quotas_to_redis(user_id, quotas)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to save reset quotas: {e}")
    
    async def _save_quotas_to_redis(self, user_id: str, quotas: Dict[ResourceType, ResourceQuota]):
        """Save quotas to Redis"""
        
        key = f"quota:{user_id}"
        quota_data = {}
        
        for resource_type, quota in quotas.items():
            quota_data[resource_type.value] = json.dumps(asdict(quota))
        
        await self.redis_client.hset(key, mapping=quota_data)
        await self.redis_client.expire(key, 86400 * 32)  # 32 days TTL
    
    async def check_resource_availability(
        self,
        user_id: str,
        user_tier: UserTier,
        resource_estimate: ResourceEstimate
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user has sufficient resources for a job
        
        Returns:
            (allowed: bool, details: dict with quota information)
        """
        
        self.metrics['quota_checks'] += 1
        
        try:
            quotas = await self.get_user_quotas(user_id, user_tier)
            
            # Check each resource requirement
            violations = []
            warnings = []
            
            # GPU Minutes
            gpu_quota = quotas[ResourceType.GPU_MINUTES]
            if gpu_quota.remaining < resource_estimate.gpu_minutes:
                violations.append({
                    'resource': 'gpu_minutes',
                    'required': resource_estimate.gpu_minutes,
                    'available': gpu_quota.remaining,
                    'reset_in_days': gpu_quota.reset_period_days
                })
            elif gpu_quota.usage_percentage + (resource_estimate.gpu_minutes / gpu_quota.total_limit * 100) >= gpu_quota.soft_limit_percentage:
                warnings.append({
                    'resource': 'gpu_minutes',
                    'usage_after': gpu_quota.usage_percentage + (resource_estimate.gpu_minutes / gpu_quota.total_limit * 100)
                })
            
            # Storage
            storage_quota = quotas[ResourceType.STORAGE_GB]
            if storage_quota.remaining < resource_estimate.storage_gb:
                violations.append({
                    'resource': 'storage_gb',
                    'required': resource_estimate.storage_gb,
                    'available': storage_quota.remaining
                })
            elif storage_quota.usage_percentage + (resource_estimate.storage_gb / storage_quota.total_limit * 100) >= storage_quota.soft_limit_percentage:
                warnings.append({
                    'resource': 'storage_gb',
                    'usage_after': storage_quota.usage_percentage + (resource_estimate.storage_gb / storage_quota.total_limit * 100)
                })
            
            # Concurrent Jobs
            concurrent_quota = quotas[ResourceType.CONCURRENT_JOBS]
            current_jobs = len(self.active_jobs.get(user_id, {}))
            if current_jobs + resource_estimate.concurrent_jobs > concurrent_quota.total_limit:
                violations.append({
                    'resource': 'concurrent_jobs',
                    'required': resource_estimate.concurrent_jobs,
                    'current': current_jobs,
                    'limit': concurrent_quota.total_limit
                })
            
            # Monthly Job Limit
            monthly_quota = quotas[ResourceType.TOTAL_JOBS_MONTHLY]
            if monthly_quota.remaining < resource_estimate.concurrent_jobs:
                violations.append({
                    'resource': 'total_jobs_monthly',
                    'required': resource_estimate.concurrent_jobs,
                    'available': monthly_quota.remaining,
                    'reset_in_days': monthly_quota.reset_period_days
                })
            
            # Priority Queue Access (if requested)
            if resource_estimate.is_priority:
                priority_quota = quotas[ResourceType.PRIORITY_QUEUE_ACCESS]
                if priority_quota.total_limit == 0:
                    violations.append({
                        'resource': 'priority_queue_access',
                        'message': 'Priority queue access not available for your tier'
                    })
            
            allowed = len(violations) == 0
            
            if not allowed:
                self.metrics['quota_violations'] += 1
            
            return allowed, {
                'allowed': allowed,
                'violations': violations,
                'warnings': warnings,
                'quotas': {
                    resource_type.value: {
                        'used': quota.used_amount,
                        'limit': quota.total_limit,
                        'remaining': quota.remaining,
                        'usage_percentage': quota.usage_percentage,
                        'is_over_soft_limit': quota.is_over_soft_limit
                    }
                    for resource_type, quota in quotas.items()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking resource availability: {e}")
            # Fail open for errors
            return True, {'error': 'quota_check_failed', 'allowed': True}
    
    async def reserve_resources(
        self,
        user_id: str,
        user_tier: UserTier,
        job_id: str,
        resource_estimate: ResourceEstimate,
        is_batch: bool = False
    ) -> bool:
        """Reserve resources for a job"""
        
        try:
            quotas = await self.get_user_quotas(user_id, user_tier)
            
            # Reserve GPU time and storage
            quotas[ResourceType.GPU_MINUTES].used_amount += resource_estimate.gpu_minutes
            quotas[ResourceType.STORAGE_GB].used_amount += resource_estimate.storage_gb
            quotas[ResourceType.TOTAL_JOBS_MONTHLY].used_amount += resource_estimate.concurrent_jobs
            
            # Track active resources
            if is_batch:
                if user_id not in self.active_batches:
                    self.active_batches[user_id] = {}
                self.active_batches[user_id][job_id] = resource_estimate
            else:
                if user_id not in self.active_jobs:
                    self.active_jobs[user_id] = {}
                self.active_jobs[user_id][job_id] = resource_estimate
            
            # Save updated quotas
            if self.redis_available and self.redis_client:
                try:
                    await self._save_quotas_to_redis(user_id, quotas)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to save quota updates: {e}")
            else:
                self.user_quotas[user_id] = quotas
            
            logger.info(f"✅ Reserved resources for {job_id}: GPU={resource_estimate.gpu_minutes}min, Storage={resource_estimate.storage_gb}GB")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error reserving resources: {e}")
            return False
    
    async def release_resources(
        self,
        user_id: str,
        job_id: str,
        actual_usage: Optional[ResourceEstimate] = None,
        is_batch: bool = False
    ) -> bool:
        """Release resources when job completes"""
        
        try:
            # Find and remove from active tracking
            original_estimate = None
            if is_batch and user_id in self.active_batches:
                original_estimate = self.active_batches[user_id].pop(job_id, None)
            elif not is_batch and user_id in self.active_jobs:
                original_estimate = self.active_jobs[user_id].pop(job_id, None)
            
            if not original_estimate:
                logger.warning(f"⚠️ No active resource tracking found for job {job_id}")
                return False
            
            # Adjust quotas based on actual vs estimated usage
            if actual_usage:
                quotas = await self.get_user_quotas(user_id, UserTier.DEFAULT)  # Get current quotas
                
                # Adjust GPU time usage (only if actual is different from estimate)
                gpu_difference = actual_usage.gpu_minutes - original_estimate.gpu_minutes
                if abs(gpu_difference) > 0.1:  # Only adjust if difference > 0.1 minute
                    quotas[ResourceType.GPU_MINUTES].used_amount += gpu_difference
                    
                # Adjust storage usage
                storage_difference = actual_usage.storage_gb - original_estimate.storage_gb
                if abs(storage_difference) > 0.001:  # Only adjust if difference > 1MB
                    quotas[ResourceType.STORAGE_GB].used_amount += storage_difference
                
                # Save updated quotas
                if self.redis_available and self.redis_client:
                    try:
                        await self._save_quotas_to_redis(user_id, quotas)
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to save quota adjustments: {e}")
                else:
                    self.user_quotas[user_id] = quotas
            
            logger.info(f"✅ Released resources for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error releasing resources: {e}")
            return False
    
    def estimate_job_resources(
        self,
        task_type: str,
        model_type: str,
        job_params: Dict[str, Any]
    ) -> ResourceEstimate:
        """Estimate resource requirements for a job"""
        
        # Base estimates by model type
        base_estimates = {
            'boltz2': {
                'gpu_minutes_per_complex': 3.5,  # ~205 seconds
                'storage_mb_per_complex': 2.0    # ~2MB per result
            },
            'chai1': {
                'gpu_minutes_per_complex': 8.0,  # Larger model
                'storage_mb_per_complex': 5.0    # Larger outputs
            },
            'rfantibody': {
                'gpu_minutes_per_complex': 5.0,
                'storage_mb_per_complex': 3.0
            }
        }
        
        model_base = base_estimates.get(model_type.lower(), base_estimates['boltz2'])
        
        # Estimate based on task type
        if task_type == 'batch_protein_ligand_screening':
            # Batch job
            ligand_count = len(job_params.get('ligands', []))
            protein_count = 1  # Single protein
            
            complexes = ligand_count * protein_count
            gpu_minutes = complexes * model_base['gpu_minutes_per_complex']
            storage_gb = complexes * model_base['storage_mb_per_complex'] / 1024  # Convert MB to GB
            concurrent_jobs = ligand_count  # Each ligand is a separate job
            
        elif task_type == 'protein_ligand_binding':
            # Single job
            gpu_minutes = model_base['gpu_minutes_per_complex']
            storage_gb = model_base['storage_mb_per_complex'] / 1024
            concurrent_jobs = 1
            
        else:
            # Default estimates
            gpu_minutes = 5.0
            storage_gb = 0.005  # 5 MB
            concurrent_jobs = 1
        
        # Add safety margin
        gpu_minutes *= 1.2  # 20% margin for variability
        storage_gb *= 1.5   # 50% margin for additional files
        
        return ResourceEstimate(
            gpu_minutes=gpu_minutes,
            storage_gb=storage_gb,
            concurrent_jobs=concurrent_jobs,
            estimated_completion_time=gpu_minutes * 60  # Convert to seconds
        )
    
    async def get_user_resource_summary(self, user_id: str, user_tier: UserTier) -> Dict[str, Any]:
        """Get comprehensive resource usage summary for a user"""
        
        try:
            quotas = await self.get_user_quotas(user_id, user_tier)
            
            active_jobs_count = len(self.active_jobs.get(user_id, {}))
            active_batches_count = len(self.active_batches.get(user_id, {}))
            
            return {
                'user_id': user_id,
                'user_tier': user_tier.value,
                'quotas': {
                    resource_type.value: {
                        'used': quota.used_amount,
                        'limit': quota.total_limit,
                        'remaining': quota.remaining,
                        'usage_percentage': quota.usage_percentage,
                        'is_over_soft_limit': quota.is_over_soft_limit,
                        'is_exhausted': quota.is_exhausted,
                        'reset_period_days': quota.reset_period_days,
                        'last_reset': quota.last_reset
                    }
                    for resource_type, quota in quotas.items()
                },
                'active_resources': {
                    'jobs': active_jobs_count,
                    'batches': active_batches_count,
                    'total_active': active_jobs_count + active_batches_count
                },
                'recommendations': self._generate_recommendations(quotas, user_tier)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting resource summary: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, quotas: Dict[ResourceType, ResourceQuota], user_tier: UserTier) -> List[str]:
        """Generate recommendations based on current usage"""
        
        recommendations = []
        
        for resource_type, quota in quotas.items():
            if quota.is_exhausted:
                if resource_type == ResourceType.GPU_MINUTES:
                    if user_tier == UserTier.DEFAULT:
                        recommendations.append("Consider upgrading to Premium for 5x more GPU time")
                    elif user_tier == UserTier.PREMIUM:
                        recommendations.append("Consider upgrading to Enterprise for 6x more GPU time")
                elif resource_type == ResourceType.STORAGE_GB:
                    if user_tier == UserTier.DEFAULT:
                        recommendations.append("Consider upgrading to Premium for 10x more storage")
                elif resource_type == ResourceType.CONCURRENT_JOBS:
                    recommendations.append("Wait for current jobs to complete before submitting new ones")
                    
            elif quota.is_over_soft_limit:
                if resource_type == ResourceType.GPU_MINUTES:
                    recommendations.append(f"You've used {quota.usage_percentage:.1f}% of your GPU time quota")
                elif resource_type == ResourceType.STORAGE_GB:
                    recommendations.append(f"You've used {quota.usage_percentage:.1f}% of your storage quota")
        
        return recommendations
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get resource quota manager metrics"""
        
        return {
            'quota_checks': self.metrics['quota_checks'],
            'quota_violations': self.metrics['quota_violations'],
            'quotas_reset': self.metrics['quotas_reset'],
            'redis_errors': self.metrics['redis_errors'],
            'fallback_used': self.metrics['fallback_used'],
            'redis_available': self.redis_available,
            'active_users': len(self.user_quotas),
            'total_active_jobs': sum(len(jobs) for jobs in self.active_jobs.values()),
            'total_active_batches': sum(len(batches) for batches in self.active_batches.values())
        }

# Global instance
resource_quota_manager = ResourceQuotaManager()

async def initialize_quota_manager(redis_url: str = None):
    """Initialize the global resource quota manager"""
    
    if redis_url:
        resource_quota_manager.redis_url = redis_url
    
    await resource_quota_manager.initialize()
    
    # Start cleanup task
    asyncio.create_task(_periodic_quota_cleanup())
    
    logger.info("✅ Resource quota manager initialized")
    return resource_quota_manager

async def _periodic_quota_cleanup():
    """Periodic cleanup of stale data"""
    
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            # Clean up completed jobs that weren't properly released
            current_time = time.time()
            stale_threshold = 3600 * 6  # 6 hours
            
            for user_id in list(resource_quota_manager.active_jobs.keys()):
                user_jobs = resource_quota_manager.active_jobs[user_id]
                stale_jobs = []
                
                for job_id, estimate in user_jobs.items():
                    if estimate.estimated_completion_time and (
                        current_time - estimate.estimated_completion_time > stale_threshold
                    ):
                        stale_jobs.append(job_id)
                
                for job_id in stale_jobs:
                    logger.warning(f"🧹 Cleaning up stale job {job_id} for user {user_id}")
                    user_jobs.pop(job_id, None)
                
                if not user_jobs:
                    resource_quota_manager.active_jobs.pop(user_id, None)
            
            # Similar cleanup for batches
            for user_id in list(resource_quota_manager.active_batches.keys()):
                user_batches = resource_quota_manager.active_batches[user_id]
                stale_batches = []
                
                for batch_id, estimate in user_batches.items():
                    if estimate.estimated_completion_time and (
                        current_time - estimate.estimated_completion_time > stale_threshold
                    ):
                        stale_batches.append(batch_id)
                
                for batch_id in stale_batches:
                    logger.warning(f"🧹 Cleaning up stale batch {batch_id} for user {user_id}")
                    user_batches.pop(batch_id, None)
                
                if not user_batches:
                    resource_quota_manager.active_batches.pop(user_id, None)
                    
        except asyncio.CancelledError:
            logger.info("🛑 Quota cleanup cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Error in quota cleanup: {e}")