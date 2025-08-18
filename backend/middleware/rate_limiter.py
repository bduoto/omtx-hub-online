#!/usr/bin/env python3
"""
Production Rate Limiting Middleware - Redis-Enhanced
Enhanced with Redis backend, user tiers, and comprehensive monitoring

Implements enterprise-grade rate limiting for the OMTX-Hub platform
with Redis persistence, user tier management, and production monitoring.
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import os
from collections import defaultdict, deque

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Redis integration (optional dependency)
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Redis not available, using in-memory rate limiting")
    REDIS_AVAILABLE = False

class UserTier(Enum):
    """User tier definitions for rate limiting"""
    DEFAULT = "default"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"

class RateLimitType(Enum):
    """Different types of rate limits"""
    API_REQUESTS = "api_requests"
    JOB_SUBMISSIONS = "job_submissions"
    BATCH_SUBMISSIONS = "batch_submissions"
    FILE_DOWNLOADS = "file_downloads"
    WEBHOOK_CALLS = "webhook_calls"

class RateLimitConfig:
    """Rate limit configurations by user tier and limit type"""
    
    LIMITS = {
        # API Requests (per minute)
        RateLimitType.API_REQUESTS: {
            UserTier.DEFAULT: 60,
            UserTier.PREMIUM: 300,
            UserTier.ENTERPRISE: 1000,
            UserTier.ADMIN: 10000
        },
        
        # Job Submissions (per hour)
        RateLimitType.JOB_SUBMISSIONS: {
            UserTier.DEFAULT: 10,
            UserTier.PREMIUM: 50,
            UserTier.ENTERPRISE: 200,
            UserTier.ADMIN: 1000
        },
        
        # Batch Submissions (per day)
        RateLimitType.BATCH_SUBMISSIONS: {
            UserTier.DEFAULT: 2,
            UserTier.PREMIUM: 10,
            UserTier.ENTERPRISE: 50,
            UserTier.ADMIN: 200
        },
        
        # File Downloads (per minute)
        RateLimitType.FILE_DOWNLOADS: {
            UserTier.DEFAULT: 20,
            UserTier.PREMIUM: 100,
            UserTier.ENTERPRISE: 500,
            UserTier.ADMIN: 1000
        },
        
        # Webhook Calls (per minute) 
        RateLimitType.WEBHOOK_CALLS: {
            UserTier.DEFAULT: 100,
            UserTier.PREMIUM: 500,
            UserTier.ENTERPRISE: 2000,
            UserTier.ADMIN: 10000
        }
    }
    
    # Time windows for different limit types (in seconds)
    TIME_WINDOWS = {
        RateLimitType.API_REQUESTS: 60,        # 1 minute
        RateLimitType.JOB_SUBMISSIONS: 3600,   # 1 hour
        RateLimitType.BATCH_SUBMISSIONS: 86400, # 1 day
        RateLimitType.FILE_DOWNLOADS: 60,      # 1 minute
        RateLimitType.WEBHOOK_CALLS: 60        # 1 minute
    }

class TokenBucket:
    """Token bucket algorithm for smooth rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float, window_seconds: int):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.window_seconds = window_seconds
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_reset_time(self) -> int:
        """Get time until bucket is fully refilled"""
        if self.tokens >= self.capacity:
            return 0
        
        tokens_needed = self.capacity - self.tokens
        seconds_to_refill = tokens_needed / self.refill_rate
        return int(seconds_to_refill)

class RedisRateLimiter:
    """
    Redis-based rate limiter with token bucket algorithm
    
    Features:
    - Per-user rate limiting with tier support
    - Multiple limit types (API, jobs, batches, downloads)
    - Token bucket algorithm for smooth rate limiting
    - Graceful degradation when Redis is unavailable
    - Distributed rate limiting across multiple instances
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        self.fallback_buckets: Dict[str, TokenBucket] = {}
        self.redis_available = False
        
        # Legacy compatibility
        self.user_buckets: Dict[str, TokenBucket] = {}
        self.endpoint_buckets: Dict[str, TokenBucket] = {}
        self.blocked_ips = set()
        self.suspicious_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Performance metrics
        self.metrics = {
            'requests_checked': 0,
            'requests_allowed': 0,
            'requests_denied': 0,
            'redis_errors': 0,
            'fallback_used': 0,
            'last_reset': time.time()
        }
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis not available, using fallback rate limiting")
            return
        
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
            logger.info(f"✅ Redis rate limiter connected to {self.redis_url}")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, using fallback rate limiting: {e}")
            self.redis_available = False
    
    def get_user_tier(self, user_id: str, request: Request = None) -> UserTier:
        """Determine user tier based on user ID and request context"""
        
        # Check for admin users
        if user_id in ["admin", "system", "webhook"]:
            return UserTier.ADMIN
        
        # Check for tier information in headers
        if request:
            tier_header = request.headers.get("x-user-tier", "").lower()
            if tier_header:
                try:
                    return UserTier(tier_header)
                except ValueError:
                    pass
        
        # Check user ID patterns
        if user_id.startswith("enterprise_"):
            return UserTier.ENTERPRISE
        elif user_id.startswith("premium_"):
            return UserTier.PREMIUM
        
        # Default tier
        return UserTier.DEFAULT
    
    def get_limit_type(self, request: Request) -> RateLimitType:
        """Determine rate limit type based on request path"""
        
        path = request.url.path.lower()
        
        if "/webhook" in path:
            return RateLimitType.WEBHOOK_CALLS
        elif "/download" in path or "/structure" in path:
            return RateLimitType.FILE_DOWNLOADS
        elif "/batch" in path and request.method == "POST":
            return RateLimitType.BATCH_SUBMISSIONS
        elif "/predict" in path or "/submit" in path:
            return RateLimitType.JOB_SUBMISSIONS
        else:
            return RateLimitType.API_REQUESTS
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit_type: RateLimitType,
        user_tier: UserTier = UserTier.DEFAULT,
        tokens: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits
        
        Returns:
            (allowed: bool, info: dict with limit details)
        """
        
        self.metrics['requests_checked'] += 1
        
        try:
            # Get limit configuration
            limit = RateLimitConfig.LIMITS[limit_type][user_tier]
            window = RateLimitConfig.TIME_WINDOWS[limit_type]
            
            # Try Redis-based limiting first
            if self.redis_available and self.redis_client:
                try:
                    allowed, info = await self._check_redis_limit(
                        user_id, limit_type, limit, window, tokens
                    )
                    
                    if allowed:
                        self.metrics['requests_allowed'] += 1
                    else:
                        self.metrics['requests_denied'] += 1
                    
                    return allowed, info
                    
                except Exception as e:
                    logger.warning(f"⚠️ Redis rate limit check failed: {e}")
                    self.metrics['redis_errors'] += 1
                    self.redis_available = False
            
            # Fallback to in-memory limiting
            self.metrics['fallback_used'] += 1
            allowed, info = await self._check_fallback_limit(
                user_id, limit_type, limit, window, tokens
            )
            
            if allowed:
                self.metrics['requests_allowed'] += 1
            else:
                self.metrics['requests_denied'] += 1
            
            return allowed, info
            
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {e}")
            # Allow request on error (fail open)
            self.metrics['requests_allowed'] += 1
            return True, {"error": "rate_limit_check_failed", "allowed": True}
    
    async def _check_redis_limit(
        self,
        user_id: str,
        limit_type: RateLimitType,
        limit: int,
        window: int,
        tokens: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using Redis"""
        
        key = f"rate_limit:{user_id}:{limit_type.value}"
        now = time.time()
        
        # Use Redis Lua script for atomic operations
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local tokens = tonumber(ARGV[4])
        
        -- Get current bucket state
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket[1]) or limit
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate refill
        local elapsed = now - last_refill
        local refill_rate = limit / window
        local tokens_to_add = elapsed * refill_rate
        current_tokens = math.min(limit, current_tokens + tokens_to_add)
        
        -- Check if we can consume tokens
        local allowed = current_tokens >= tokens
        if allowed then
            current_tokens = current_tokens - tokens
        end
        
        -- Update bucket state
        redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
        redis.call('EXPIRE', key, window * 2)  -- Keep data for 2x window
        
        -- Calculate reset time
        local reset_time = 0
        if current_tokens < limit then
            reset_time = math.ceil((limit - current_tokens) / refill_rate)
        end
        
        return {allowed and 1 or 0, current_tokens, limit, reset_time}
        """
        
        result = await self.redis_client.eval(
            lua_script,
            1,  # Number of keys
            key, now, window, limit, tokens
        )
        
        allowed = bool(result[0])
        remaining = int(result[1])
        total_limit = int(result[2])
        reset_time = int(result[3])
        
        return allowed, {
            "allowed": allowed,
            "limit": total_limit,
            "remaining": remaining,
            "reset_time": reset_time,
            "retry_after": reset_time if not allowed else 0,
            "window_seconds": window,
            "source": "redis"
        }
    
    async def _check_fallback_limit(
        self,
        user_id: str,
        limit_type: RateLimitType,
        limit: int,
        window: int,
        tokens: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit using in-memory fallback"""
        
        key = f"{user_id}:{limit_type.value}"
        
        # Get or create token bucket
        if key not in self.fallback_buckets:
            refill_rate = limit / window
            self.fallback_buckets[key] = TokenBucket(limit, refill_rate, window)
        
        bucket = self.fallback_buckets[key]
        allowed = bucket.consume(tokens)
        
        return allowed, {
            "allowed": allowed,
            "limit": limit,
            "remaining": int(bucket.tokens),
            "reset_time": bucket.get_reset_time(),
            "retry_after": bucket.get_reset_time() if not allowed else 0,
            "window_seconds": window,
            "source": "fallback"
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter performance metrics"""
        
        uptime = time.time() - self.metrics['last_reset']
        
        return {
            "requests_checked": self.metrics['requests_checked'],
            "requests_allowed": self.metrics['requests_allowed'],
            "requests_denied": self.metrics['requests_denied'],
            "allow_rate": (
                self.metrics['requests_allowed'] / 
                max(self.metrics['requests_checked'], 1) * 100
            ),
            "redis_errors": self.metrics['redis_errors'],
            "fallback_used": self.metrics['fallback_used'],
            "redis_available": self.redis_available,
            "fallback_buckets_count": len(self.fallback_buckets),
            "uptime_seconds": uptime
        }
    
    # Legacy compatibility methods
    def _sanitize_user_id(self, user_id: str) -> str:
        """Sanitize user ID to prevent injection attacks"""
        if not user_id or not isinstance(user_id, str):
            return 'anonymous'

        # Remove potentially dangerous characters
        import re
        sanitized = re.sub(r'[^\w\-@.]', '', user_id)

        # Limit length to prevent abuse
        sanitized = sanitized[:100]

        return sanitized if sanitized else 'anonymous'
    
    def detect_suspicious_activity(self, client_ip: str, user_id: str) -> bool:
        """Detect potential abuse patterns"""
        now = datetime.now()
        activity_window = now - timedelta(minutes=5)
        
        # Record this request
        self.suspicious_activity[client_ip].append(now)
        
        # Count recent requests from this IP
        recent_requests = [
            req_time for req_time in self.suspicious_activity[client_ip]
            if req_time > activity_window
        ]
        
        # Flag as suspicious if more than 500 requests in 5 minutes from single IP
        if len(recent_requests) > 500:
            logger.warning(f"🚨 Suspicious activity detected from IP {client_ip}: {len(recent_requests)} requests in 5 minutes")
            return True
        
        return False
    
    def get_endpoint_key(self, request: Request) -> str:
        """Extract rate limiting key from endpoint (legacy compatibility)"""
        path = request.url.path.lower()
        method = request.method.lower()
        
        if '/api/v3/batches/submit' in path:
            return 'batch_submit'
        elif '/status' in path and '/batches/' in path:
            return 'batch_status'
        elif path.endswith('/api/v3/batches/') or path.endswith('/api/v3/batches'):
            return 'batch_list'
        elif '/results' in path and '/batches/' in path:
            return 'batch_results'
        elif method == 'delete' and '/batches/' in path:
            return 'batch_delete'
        
        return 'default'
    
    async def check_rate_limit_legacy(self, request: Request) -> Optional[JSONResponse]:
        """
        Legacy rate limiting logic for backward compatibility
        Returns None if request is allowed, JSONResponse if blocked
        """
        
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        raw_user_id = request.query_params.get('user_id', 'anonymous')

        # Validate and sanitize user_id to prevent injection attacks
        user_id = self._sanitize_user_id(raw_user_id)
        
        # Check for suspicious activity
        if self.detect_suspicious_activity(client_ip, user_id):
            self.blocked_ips.add(client_ip)
            logger.error(f"🚫 IP {client_ip} blocked for suspicious activity")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Suspicious activity detected. IP temporarily blocked.",
                    "retry_after": 3600  # 1 hour
                }
            )
        
        # Use new rate limiting system
        try:
            limit_type = self.get_limit_type(request)
            user_tier = self.get_user_tier(user_id, request)
            
            allowed, info = await self.check_rate_limit(user_id, limit_type, user_tier)
            
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded for {limit_type.value}",
                        "limit_info": info
                    },
                    headers={
                        "X-RateLimit-Limit": str(info.get("limit", 0)),
                        "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                        "X-RateLimit-Reset": str(info.get("reset_time", 0)),
                        "Retry-After": str(info.get("retry_after", 60))
                    }
                )
        
        except Exception as e:
            logger.error(f"❌ Rate limiting error: {e}")
            # Fail open for errors
        
        # Request is allowed
        logger.debug(f"✅ Rate limit check passed for {user_id}")
        return None
    
    def get_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get current rate limit status for monitoring (legacy compatibility)"""
        try:
            user_tier = self.get_user_tier(user_id)
            
            # Get API request limits
            limit = RateLimitConfig.LIMITS[RateLimitType.API_REQUESTS][user_tier]
            
            return {
                'user_id': user_id,
                'user_tier': user_tier.value,
                'tokens_remaining': limit,  # Simplified for compatibility
                'tokens_capacity': limit,
                'refill_rate': limit / 60,  # Per second
                'blocked_ips_count': len(self.blocked_ips),
                'redis_available': self.redis_available
            }
        except Exception as e:
            logger.error(f"❌ Error getting rate limit status: {e}")
            return {
                'user_id': user_id,
                'user_tier': 'default',
                'tokens_remaining': 60,
                'tokens_capacity': 60,
                'refill_rate': 1.0,
                'blocked_ips_count': 0,
                'redis_available': False
            }

# Global rate limiter instance (Redis-enhanced)
rate_limiter = RedisRateLimiter()

# Middleware class for FastAPI integration
class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting for certain paths
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            await self.app(scope, receive, send)
            return
        
        # Determine user ID
        user_id = self._get_user_id(request)
        
        # Determine rate limit type based on path
        limit_type = rate_limiter.get_limit_type(request)
        
        # Get user tier
        user_tier = rate_limiter.get_user_tier(user_id, request)
        
        # Check rate limit
        try:
            allowed, limit_info = await rate_limiter.check_rate_limit(
                user_id, limit_type, user_tier
            )
            
            if not allowed:
                # Rate limit exceeded
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded for {limit_type.value}",
                        "limit_info": limit_info
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                        "X-RateLimit-Remaining": str(limit_info.get("remaining", 0)),
                        "X-RateLimit-Reset": str(limit_info.get("reset_time", 0)),
                        "Retry-After": str(limit_info.get("retry_after", 60))
                    }
                )
                
                await response(scope, receive, send)
                return
            
            # Add rate limit headers to response
            def add_rate_limit_headers(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers.update({
                        b"x-ratelimit-limit": str(limit_info.get("limit", 0)).encode(),
                        b"x-ratelimit-remaining": str(limit_info.get("remaining", 0)).encode(),
                        b"x-ratelimit-reset": str(limit_info.get("reset_time", 0)).encode()
                    })
                    message["headers"] = list(headers.items())
                return message
            
            # Continue with request
            await self.app(scope, receive, lambda message: send(add_rate_limit_headers(message)))
            
        except Exception as e:
            logger.error(f"❌ Rate limiting middleware error: {e}")
            # Continue with request on error (fail open)
            await self.app(scope, receive, send)
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from request"""
        
        # Try various sources for user ID
        user_id = (
            request.headers.get("x-user-id") or
            request.query_params.get('user_id') or
            request.headers.get("authorization", "").replace("Bearer ", "")[:16] or
            request.client.host if request.client else "unknown"
        )
        
        # Create a hash for IP-based identification
        if user_id == request.client.host:
            user_id = f"ip_{hashlib.md5(user_id.encode()).hexdigest()[:8]}"
        
        return user_id

# Legacy middleware function for backward compatibility
async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting (legacy compatibility)
    """
    
    # Skip rate limiting for health checks and internal endpoints
    if request.url.path in ['/health', '/metrics', '/docs', '/openapi.json']:
        return await call_next(request)
    
    # Apply rate limiting
    rate_limit_response = await rate_limiter.check_rate_limit_legacy(request)
    if rate_limit_response:
        return rate_limit_response
    
    # Process request normally
    response = await call_next(request)
    
    # Add rate limit headers to response
    try:
        user_id = request.query_params.get('user_id', 'anonymous')
        status_info = rate_limiter.get_rate_limit_status(user_id)
        
        response.headers["X-RateLimit-Remaining"] = str(status_info.get('tokens_remaining', 0))
        response.headers["X-RateLimit-Capacity"] = str(status_info.get('tokens_capacity', 0))
        response.headers["X-RateLimit-Tier"] = str(status_info.get('user_tier', 'default'))
    except Exception as e:
        logger.error(f"❌ Error adding rate limit headers: {e}")
    
    return response

async def initialize_rate_limiter(redis_url: str = None):
    """Initialize the global rate limiter"""
    
    if redis_url:
        rate_limiter.redis_url = redis_url
    
    await rate_limiter.initialize()
    
    # Start cleanup task
    asyncio.create_task(_periodic_cleanup())
    
    return rate_limiter

async def _periodic_cleanup():
    """Periodic cleanup of old data"""
    
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            # Clean up old fallback buckets
            current_time = time.time()
            expired_keys = []
            
            for key, bucket in rate_limiter.fallback_buckets.items():
                if current_time - bucket.last_refill > 3600:  # 1 hour
                    expired_keys.append(key)
            
            for key in expired_keys:
                rate_limiter.fallback_buckets.pop(key, None)
            
            if expired_keys:
                logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired rate limit buckets")
                
        except asyncio.CancelledError:
            logger.info("🛑 Rate limiter cleanup cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Error in rate limiter cleanup: {e}")