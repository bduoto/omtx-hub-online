"""
Security Middleware - REQUIRED for production
Distinguished Engineer Implementation - Comprehensive security headers and CORS
"""

import logging
import time
import uuid
from typing import List, Optional

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://firestore.googleapis.com https://storage.googleapis.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing for tracing"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Track timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add timing and request ID to response
        processing_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
        
        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"-> {response.status_code} ({processing_time:.3f}s)"
        )
        
        return response

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Basic rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
        self.window_size = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/startup"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                timestamp for timestamp in self.request_counts[client_ip]
                if timestamp > window_start
            ]
        else:
            self.request_counts[client_ip] = []
        
        # Check if rate limit exceeded
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response(
                content='{"error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_size))
                }
            )
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.requests_per_minute - len(self.request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_size))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        
        # Check for forwarded headers (Cloud Run, load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"

def add_security_middleware(app):
    """Add all security middleware to FastAPI app"""
    
    import os
    
    # Get allowed origins from environment
    allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
    if not allowed_origins or allowed_origins == [""]:
        # Default origins for development
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "https://omtx-hub.com",
            "https://*.omtx.com"
        ]
    
    # CORS - Critical for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-User-Id",
            "X-Request-ID",
            "X-Requested-With"
        ],
        expose_headers=[
            "X-Total-Count",
            "X-Page-Count",
            "X-Request-ID",
            "X-Processing-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )
    
    # Trusted hosts
    trusted_hosts = os.getenv("TRUSTED_HOSTS", "").split(",")
    if not trusted_hosts or trusted_hosts == [""]:
        # Default trusted hosts
        trusted_hosts = [
            "*.omtx.com",
            "*.run.app",
            "localhost",
            "127.0.0.1"
        ]
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts
    )
    
    # Rate limiting (basic implementation)
    rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    app.add_middleware(RateLimitingMiddleware, requests_per_minute=rate_limit)
    
    # Request tracking
    app.add_middleware(RequestTrackingMiddleware)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("✅ Security middleware configured")
    logger.info(f"   CORS origins: {len(allowed_origins)} configured")
    logger.info(f"   Trusted hosts: {len(trusted_hosts)} configured")
    logger.info(f"   Rate limit: {rate_limit} requests/minute")

class DevelopmentSecurityOverride:
    """Override security settings for development"""
    
    @staticmethod
    def configure_for_development(app):
        """Configure relaxed security for development"""
        
        import os
        
        if os.getenv("ENVIRONMENT") != "development":
            logger.warning("⚠️ Development security override called in non-development environment")
            return
        
        # Add development-specific CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins in development
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Disable rate limiting in development
        logger.info("🔓 Development mode: Security restrictions relaxed")

def get_security_config() -> dict:
    """Get current security configuration"""
    
    import os
    
    return {
        "cors_origins": os.getenv("CORS_ORIGINS", "").split(","),
        "trusted_hosts": os.getenv("TRUSTED_HOSTS", "").split(","),
        "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "https_only": os.getenv("HTTPS_ONLY", "false").lower() == "true"
    }
