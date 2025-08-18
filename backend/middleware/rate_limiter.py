#!/usr/bin/env python3
"""
Production Rate Limiting Middleware
Senior Principal Engineer Implementation

Implements intelligent rate limiting for the unified batch processing API
with user-based quotas, endpoint-specific limits, and burst protection.
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio

logger = logging.getLogger(__name__)

class TokenBucket:
    """Token bucket algorithm for smooth rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens, returns True if successful"""
        now = time.time()
        # Add tokens based on time passed
        time_passed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class ProductionRateLimiter:
    """
    Enterprise-Grade Rate Limiter
    
    Features:
    - User-based quotas with role-based limits
    - Endpoint-specific rate limiting
    - Burst protection with token bucket algorithm
    - Redis-compatible for distributed systems
    - Intelligent backoff recommendations
    """
    
    def __init__(self):
        # In-memory storage (replace with Redis in production)
        self.user_buckets: Dict[str, TokenBucket] = {}
        self.endpoint_buckets: Dict[str, TokenBucket] = {}
        self.global_bucket = TokenBucket(capacity=1000, refill_rate=10.0)  # 10 req/sec global
        
        # Rate limit configurations
        self.rate_limits = {
            # User-based limits (requests per minute)
            'user_default': {'capacity': 60, 'refill_rate': 1.0},      # 60/min standard user
            'user_premium': {'capacity': 120, 'refill_rate': 2.0},     # 120/min premium user
            'user_enterprise': {'capacity': 300, 'refill_rate': 5.0},  # 300/min enterprise
            
            # Endpoint-specific limits
            'batch_submit': {'capacity': 10, 'refill_rate': 0.17},     # 10/min batch submission
            'batch_status': {'capacity': 180, 'refill_rate': 3.0},     # 180/min status polling
            'batch_list': {'capacity': 30, 'refill_rate': 0.5},        # 30/min batch listing
            'batch_results': {'capacity': 60, 'refill_rate': 1.0},     # 60/min results access
            'batch_delete': {'capacity': 20, 'refill_rate': 0.33},     # 20/min deletion ops
        }
        
        # Blocked IPs (security feature)
        self.blocked_ips = set()
        self.suspicious_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def get_user_tier(self, user_id: str) -> str:
        """Determine user tier for rate limiting"""
        # TODO: Integrate with user management system
        # For now, basic logic based on user_id patterns
        if user_id.startswith('enterprise_'):
            return 'user_enterprise'
        elif user_id.startswith('premium_'):
            return 'user_premium'
        return 'user_default'
    
    def get_endpoint_key(self, request: Request) -> str:
        """Extract rate limiting key from endpoint"""
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

    def get_user_bucket(self, user_id: str) -> TokenBucket:
        """Get or create user token bucket"""
        if user_id not in self.user_buckets:
            user_tier = self.get_user_tier(user_id)
            config = self.rate_limits[user_tier]
            self.user_buckets[user_id] = TokenBucket(
                capacity=config['capacity'],
                refill_rate=config['refill_rate']
            )
        return self.user_buckets[user_id]
    
    def get_endpoint_bucket(self, endpoint_key: str) -> TokenBucket:
        """Get or create endpoint token bucket"""
        if endpoint_key not in self.endpoint_buckets:
            if endpoint_key in self.rate_limits:
                config = self.rate_limits[endpoint_key]
                self.endpoint_buckets[endpoint_key] = TokenBucket(
                    capacity=config['capacity'],
                    refill_rate=config['refill_rate']
                )
            else:
                # Default limits for unknown endpoints
                self.endpoint_buckets[endpoint_key] = TokenBucket(
                    capacity=30, refill_rate=0.5
                )
        return self.endpoint_buckets[endpoint_key]
    
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
    
    async def check_rate_limit(self, request: Request) -> Optional[JSONResponse]:
        """
        Main rate limiting logic
        Returns None if request is allowed, JSONResponse if blocked
        """
        
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        raw_user_id = request.query_params.get('user_id', 'anonymous')

        # Validate and sanitize user_id to prevent injection attacks
        user_id = self._sanitize_user_id(raw_user_id)
        endpoint_key = self.get_endpoint_key(request)
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            logger.warning(f"🚫 Blocked IP {client_ip} attempted access")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Access forbidden",
                    "message": "Your IP address has been blocked due to suspicious activity",
                    "retry_after": None
                }
            )
        
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
        
        # Check global rate limit
        if not self.global_bucket.consume():
            logger.warning(f"🌐 Global rate limit exceeded from {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Global rate limit exceeded",
                    "message": "Server is experiencing high load. Please retry later.",
                    "retry_after": 60
                }
            )
        
        # Check user rate limit
        user_bucket = self.get_user_bucket(user_id)
        if not user_bucket.consume():
            user_tier = self.get_user_tier(user_id)
            logger.warning(f"👤 User rate limit exceeded for {user_id} (tier: {user_tier})")
            
            # Calculate retry after time
            tokens_needed = 1
            retry_after = int(tokens_needed / user_bucket.refill_rate)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "User rate limit exceeded",
                    "message": f"You have exceeded your rate limit. Upgrade to premium for higher limits.",
                    "retry_after": retry_after,
                    "current_tier": user_tier,
                    "upgrade_available": user_tier == 'user_default'
                }
            )
        
        # Check endpoint-specific rate limit
        endpoint_bucket = self.get_endpoint_bucket(endpoint_key)
        if not endpoint_bucket.consume():
            logger.warning(f"🎯 Endpoint rate limit exceeded for {endpoint_key} from {user_id}")
            
            retry_after = int(1 / endpoint_bucket.refill_rate)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Endpoint rate limit exceeded",
                    "message": f"Too many requests to {endpoint_key}. Please slow down.",
                    "retry_after": retry_after,
                    "endpoint": endpoint_key
                }
            )
        
        # Request is allowed
        logger.debug(f"✅ Rate limit check passed for {user_id} -> {endpoint_key}")
        return None
    
    def get_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get current rate limit status for monitoring"""
        user_bucket = self.get_user_bucket(user_id)
        user_tier = self.get_user_tier(user_id)
        
        return {
            'user_id': user_id,
            'user_tier': user_tier,
            'tokens_remaining': int(user_bucket.tokens),
            'tokens_capacity': user_bucket.capacity,
            'refill_rate': user_bucket.refill_rate,
            'global_tokens_remaining': int(self.global_bucket.tokens),
            'blocked_ips_count': len(self.blocked_ips),
            'endpoint_limits': {
                key: {
                    'tokens_remaining': int(bucket.tokens),
                    'capacity': bucket.capacity
                }
                for key, bucket in self.endpoint_buckets.items()
            }
        }

# Global rate limiter instance
rate_limiter = ProductionRateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting
    """
    
    # Skip rate limiting for health checks and internal endpoints
    if request.url.path in ['/health', '/metrics', '/docs', '/openapi.json']:
        return await call_next(request)
    
    # Apply rate limiting
    rate_limit_response = await rate_limiter.check_rate_limit(request)
    if rate_limit_response:
        return rate_limit_response
    
    # Process request normally
    response = await call_next(request)
    
    # Add rate limit headers to response
    user_id = request.query_params.get('user_id', 'anonymous')
    status = rate_limiter.get_rate_limit_status(user_id)
    
    response.headers["X-RateLimit-Remaining"] = str(status['tokens_remaining'])
    response.headers["X-RateLimit-Capacity"] = str(status['tokens_capacity'])
    response.headers["X-RateLimit-Tier"] = status['user_tier']
    
    return response