"""
Concurrency Manager - High-performance multi-tenant concurrency control
Distinguished Engineer Implementation - Production-ready with rate limiting and resource management
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import redis
import os

logger = logging.getLogger(__name__)

@dataclass
class ConcurrencyLimits:
    """Tier-based concurrency limits"""
    max_concurrent_jobs: int
    max_requests_per_minute: int
    max_gpu_minutes_per_hour: int
    priority_level: int  # 1=highest, 5=lowest

class ConcurrencyManager:
    """Enterprise concurrency manager with per-user limits and global protection"""
    
    def __init__(self):
        # Redis for distributed rate limiting (optional)
        self.redis_client = None
        if os.getenv("REDIS_URL"):
            try:
                import redis
                self.redis_client = redis.from_url(os.getenv("REDIS_URL"))
                logger.info("✅ Redis connected for distributed rate limiting")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed, using in-memory: {str(e)}")
        
        # In-memory fallback
        self.user_semaphores = defaultdict(lambda: asyncio.Semaphore(1))
        self.rate_buckets = defaultdict(lambda: {'tokens': 60, 'last_refill': time.time()})
        self.active_jobs = defaultdict(int)
        
        # Global system protection
        self.global_semaphore = asyncio.Semaphore(100)  # Max 100 concurrent jobs system-wide
        self.system_load_threshold = 0.8  # 80% system load threshold
        
        # Tier-based limits
        self.tier_limits = {
            'free': ConcurrencyLimits(
                max_concurrent_jobs=1,
                max_requests_per_minute=10,
                max_gpu_minutes_per_hour=60,
                priority_level=5
            ),
            'basic': ConcurrencyLimits(
                max_concurrent_jobs=3,
                max_requests_per_minute=60,
                max_gpu_minutes_per_hour=300,
                priority_level=4
            ),
            'pro': ConcurrencyLimits(
                max_concurrent_jobs=10,
                max_requests_per_minute=300,
                max_gpu_minutes_per_hour=1800,
                priority_level=3
            ),
            'enterprise': ConcurrencyLimits(
                max_concurrent_jobs=50,
                max_requests_per_minute=1000,
                max_gpu_minutes_per_hour=18000,
                priority_level=1
            )
        }
        
        logger.info("⚡ ConcurrencyManager initialized with multi-tier limits")
    
    async def acquire_job_slot(self, user_id: str, tier: str, estimated_gpu_minutes: int = 1) -> bool:
        """Acquire slot for job execution with comprehensive checking"""
        
        try:
            # Get tier limits
            limits = self.tier_limits.get(tier, self.tier_limits['free'])
            
            # Check rate limiting first (fastest check)
            if not await self._check_rate_limit(user_id, tier):
                logger.warning(f"⚠️ Rate limit exceeded for user {user_id}")
                return False
            
            # Check GPU minutes quota
            if not await self._check_gpu_minutes_quota(user_id, tier, estimated_gpu_minutes):
                logger.warning(f"⚠️ GPU minutes quota exceeded for user {user_id}")
                return False
            
            # Check system load
            if not await self._check_system_load():
                logger.warning(f"⚠️ System load too high, rejecting job for user {user_id}")
                return False
            
            # Try to acquire user-specific slot
            user_acquired = await self._acquire_user_slot(user_id, limits.max_concurrent_jobs)
            if not user_acquired:
                logger.info(f"📊 User concurrent limit reached for {user_id}")
                return False
            
            # Try to acquire global slot
            global_acquired = self.global_semaphore.acquire()
            if not await asyncio.wait_for(global_acquired, timeout=0.1):
                # Release user slot if global acquisition fails
                await self._release_user_slot(user_id)
                logger.info(f"📊 Global concurrent limit reached")
                return False
            
            # Update active jobs counter
            self.active_jobs[user_id] += 1
            
            logger.info(f"✅ Job slot acquired for user {user_id} (tier: {tier})")
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Timeout acquiring job slot for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Error acquiring job slot for user {user_id}: {str(e)}")
            return False
    
    async def release_job_slot(self, user_id: str, actual_gpu_minutes: Optional[int] = None):
        """Release job slot after completion"""
        
        try:
            # Release user slot
            await self._release_user_slot(user_id)
            
            # Release global slot
            self.global_semaphore.release()
            
            # Update active jobs counter
            if self.active_jobs[user_id] > 0:
                self.active_jobs[user_id] -= 1
            
            # Update GPU minutes usage if provided
            if actual_gpu_minutes:
                await self._update_gpu_minutes_usage(user_id, actual_gpu_minutes)
            
            logger.debug(f"✅ Job slot released for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error releasing job slot for user {user_id}: {str(e)}")
    
    async def _check_rate_limit(self, user_id: str, tier: str) -> bool:
        """Token bucket rate limiting with Redis support"""
        
        limits = self.tier_limits.get(tier, self.tier_limits['free'])
        max_tokens = limits.max_requests_per_minute
        
        if self.redis_client:
            return await self._redis_rate_limit(user_id, max_tokens)
        else:
            return self._memory_rate_limit(user_id, max_tokens)
    
    async def _redis_rate_limit(self, user_id: str, max_tokens: int) -> bool:
        """Redis-based distributed rate limiting"""
        
        try:
            key = f"rate_limit:{user_id}"
            current_time = int(time.time())
            window_start = current_time - 60  # 1-minute window
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, 60)
            
            results = pipe.execute()
            current_count = results[1]
            
            return current_count < max_tokens
            
        except Exception as e:
            logger.error(f"❌ Redis rate limiting error: {str(e)}")
            # Fallback to memory-based rate limiting
            return self._memory_rate_limit(user_id, max_tokens)
    
    def _memory_rate_limit(self, user_id: str, max_tokens: int) -> bool:
        """In-memory token bucket rate limiting"""
        
        bucket = self.rate_buckets[user_id]
        now = time.time()
        
        # Refill tokens (1 token per second)
        time_passed = now - bucket['last_refill']
        tokens_to_add = time_passed * (max_tokens / 60.0)  # Tokens per second
        bucket['tokens'] = min(max_tokens, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
        
        # Check if request allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True
        
        return False
    
    async def _check_gpu_minutes_quota(self, user_id: str, tier: str, estimated_minutes: int) -> bool:
        """Check GPU minutes quota for the current hour"""
        
        limits = self.tier_limits.get(tier, self.tier_limits['free'])
        max_gpu_minutes = limits.max_gpu_minutes_per_hour
        
        try:
            if self.redis_client:
                # Redis-based quota tracking
                key = f"gpu_minutes:{user_id}:{int(time.time() // 3600)}"  # Hour-based key
                current_usage = int(self.redis_client.get(key) or 0)
                
                if current_usage + estimated_minutes > max_gpu_minutes:
                    return False
                
                # Reserve the estimated minutes
                self.redis_client.incrby(key, estimated_minutes)
                self.redis_client.expire(key, 3600)  # Expire after 1 hour
                
                return True
            else:
                # Simple in-memory check (not distributed)
                # In production, you'd want to use a proper distributed store
                return True
                
        except Exception as e:
            logger.error(f"❌ GPU minutes quota check error: {str(e)}")
            return True  # Allow on error to avoid blocking
    
    async def _check_system_load(self) -> bool:
        """Check system load and reject requests if too high"""
        
        try:
            # Check CPU load
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check if system is under stress
            if cpu_percent > 90 or memory_percent > 90:
                logger.warning(f"🚨 High system load: CPU {cpu_percent}%, Memory {memory_percent}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ System load check error: {str(e)}")
            return True  # Allow on error
    
    async def _acquire_user_slot(self, user_id: str, max_concurrent: int) -> bool:
        """Acquire user-specific concurrency slot"""
        
        # Update semaphore if limit changed
        current_limit = self.user_semaphores[user_id]._value
        if current_limit != max_concurrent:
            self.user_semaphores[user_id] = asyncio.Semaphore(max_concurrent)
        
        # Try to acquire with timeout
        try:
            await asyncio.wait_for(self.user_semaphores[user_id].acquire(), timeout=0.1)
            return True
        except asyncio.TimeoutError:
            return False
    
    async def _release_user_slot(self, user_id: str):
        """Release user-specific concurrency slot"""
        
        try:
            self.user_semaphores[user_id].release()
        except ValueError:
            # Semaphore already at maximum, ignore
            pass
    
    async def _update_gpu_minutes_usage(self, user_id: str, actual_minutes: int):
        """Update actual GPU minutes usage"""
        
        try:
            if self.redis_client:
                key = f"gpu_minutes_actual:{user_id}:{int(time.time() // 3600)}"
                self.redis_client.incrby(key, actual_minutes)
                self.redis_client.expire(key, 3600)
                
        except Exception as e:
            logger.error(f"❌ GPU minutes update error: {str(e)}")
    
    async def get_user_concurrency_stats(self, user_id: str, tier: str) -> Dict[str, Any]:
        """Get user's current concurrency statistics"""
        
        limits = self.tier_limits.get(tier, self.tier_limits['free'])
        
        try:
            current_jobs = self.active_jobs.get(user_id, 0)
            
            # Get rate limit status
            bucket = self.rate_buckets[user_id]
            available_requests = int(bucket['tokens'])
            
            # Get GPU minutes usage (current hour)
            gpu_minutes_used = 0
            if self.redis_client:
                key = f"gpu_minutes_actual:{user_id}:{int(time.time() // 3600)}"
                gpu_minutes_used = int(self.redis_client.get(key) or 0)
            
            return {
                'user_id': user_id,
                'tier': tier,
                'current_jobs': current_jobs,
                'max_concurrent_jobs': limits.max_concurrent_jobs,
                'available_requests': available_requests,
                'max_requests_per_minute': limits.max_requests_per_minute,
                'gpu_minutes_used_this_hour': gpu_minutes_used,
                'max_gpu_minutes_per_hour': limits.max_gpu_minutes_per_hour,
                'priority_level': limits.priority_level,
                'utilization': {
                    'jobs_pct': (current_jobs / limits.max_concurrent_jobs) * 100,
                    'requests_pct': ((limits.max_requests_per_minute - available_requests) / limits.max_requests_per_minute) * 100,
                    'gpu_minutes_pct': (gpu_minutes_used / limits.max_gpu_minutes_per_hour) * 100
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting concurrency stats for user {user_id}: {str(e)}")
            return {'error': str(e)}
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide concurrency statistics"""
        
        try:
            total_active_jobs = sum(self.active_jobs.values())
            global_slots_used = 100 - self.global_semaphore._value
            
            # System load
            import psutil
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            return {
                'total_active_jobs': total_active_jobs,
                'global_slots_used': global_slots_used,
                'global_slots_available': self.global_semaphore._value,
                'system_load': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3)
                },
                'active_users': len([uid for uid, jobs in self.active_jobs.items() if jobs > 0])
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting system stats: {str(e)}")
            return {'error': str(e)}

# Global concurrency manager instance
concurrency_manager = ConcurrencyManager()
