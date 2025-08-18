"""
CDN Cache Headers Middleware for Global Performance
Optimizes caching headers for CDN and browser caching
"""

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)

class CDNCacheHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add optimal cache headers for CDN and browser caching"""
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or self._default_config()
        logger.info("🌐 CDN Cache Headers Middleware initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default caching configuration"""
        return {
            # API endpoints caching rules
            'api_cache_rules': [
                {
                    'pattern': r'/api/v3/batches/\?.*',
                    'max_age': 60,  # 1 minute for batch listings
                    'stale_while_revalidate': 300,  # 5 minutes stale
                    'cache_control': 'public, max-age=60, stale-while-revalidate=300'
                },
                {
                    'pattern': r'/api/v2/results/(ultra-)?fast.*',
                    'max_age': 30,  # 30 seconds for fast results
                    'stale_while_revalidate': 120,  # 2 minutes stale
                    'cache_control': 'public, max-age=30, stale-while-revalidate=120'
                },
                {
                    'pattern': r'/api/v3/batches/[^/]+/results',
                    'max_age': 300,  # 5 minutes for batch results
                    'stale_while_revalidate': 900,  # 15 minutes stale
                    'cache_control': 'public, max-age=300, stale-while-revalidate=900'
                },
                {
                    'pattern': r'/api/v3/batches/[^/]+/status',
                    'max_age': 10,  # 10 seconds for status
                    'stale_while_revalidate': 60,  # 1 minute stale
                    'cache_control': 'public, max-age=10, stale-while-revalidate=60'
                }
            ],
            
            # Static content caching
            'static_cache_rules': [
                {
                    'pattern': r'\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$',
                    'max_age': 31536000,  # 1 year
                    'cache_control': 'public, max-age=31536000, immutable'
                }
            ],
            
            # No-cache rules
            'no_cache_rules': [
                {
                    'pattern': r'/api/v3/batches/submit',
                    'cache_control': 'no-cache, no-store, must-revalidate'
                },
                {
                    'pattern': r'/api/.*/delete',
                    'cache_control': 'no-cache, no-store, must-revalidate'
                },
                {
                    'pattern': r'/health',
                    'cache_control': 'no-cache, max-age=0'
                }
            ],
            
            # CDN-specific headers
            'cdn_headers': {
                'Cloudflare': {
                    'CF-Cache-Status': 'HIT',
                    'CF-Ray': 'auto'
                },
                'CloudFront': {
                    'CloudFront-Viewer-Country': 'auto'
                }
            }
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add cache headers to response"""
        
        # Get response from application
        response = await call_next(request)
        
        # Add cache headers based on request path
        self._add_cache_headers(request, response)
        
        # Add CDN optimization headers
        self._add_cdn_headers(request, response)
        
        # Add performance headers
        self._add_performance_headers(request, response)
        
        return response
    
    def _add_cache_headers(self, request: Request, response: Response):
        """Add appropriate cache headers based on request path"""
        
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        full_path = f"{path}?{query}" if query else path
        
        # Check no-cache rules first
        for rule in self.config['no_cache_rules']:
            if re.search(rule['pattern'], full_path):
                response.headers['Cache-Control'] = rule['cache_control']
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return
        
        # Check API cache rules
        for rule in self.config['api_cache_rules']:
            if re.search(rule['pattern'], full_path):
                response.headers['Cache-Control'] = rule['cache_control']
                response.headers['ETag'] = self._generate_etag(request, response)
                response.headers['Vary'] = 'Accept, Accept-Encoding, Authorization'
                return
        
        # Check static content rules
        for rule in self.config['static_cache_rules']:
            if re.search(rule['pattern'], path):
                response.headers['Cache-Control'] = rule['cache_control']
                return
        
        # Default cache headers for other endpoints
        if path.startswith('/api/'):
            response.headers['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=300'
            response.headers['ETag'] = self._generate_etag(request, response)
        else:
            response.headers['Cache-Control'] = 'public, max-age=300'
    
    def _add_cdn_headers(self, request: Request, response: Response):
        """Add CDN-specific optimization headers"""
        
        # Add Cloudflare optimization headers
        response.headers['CF-Cache-Status'] = 'DYNAMIC'
        response.headers['CF-Ray'] = 'auto'
        
        # Add general CDN headers
        response.headers['X-Cache-Status'] = 'MISS'  # Will be overridden by CDN
        response.headers['X-Served-By'] = 'omtx-hub-api'
        
        # Add geographic optimization hints
        response.headers['Vary'] = response.headers.get('Vary', '') + ', CloudFront-Viewer-Country'
    
    def _add_performance_headers(self, request: Request, response: Response):
        """Add performance optimization headers"""
        
        # Security headers that also help performance
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Compression hints
        response.headers['Vary'] = response.headers.get('Vary', '') + ', Accept-Encoding'
        
        # Connection optimization
        response.headers['Connection'] = 'keep-alive'
        
        # CORS optimization for API endpoints
        if request.url.path.startswith('/api/'):
            response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
    
    def _generate_etag(self, request: Request, response: Response) -> str:
        """Generate ETag for response caching"""
        
        # Simple ETag based on path and query parameters
        import hashlib
        
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        content_length = response.headers.get('content-length', '0')
        
        etag_source = f"{path}:{query}:{content_length}"
        etag_hash = hashlib.md5(etag_source.encode()).hexdigest()[:16]
        
        return f'"{etag_hash}"'

def create_cdn_cache_middleware(config: Optional[Dict[str, Any]] = None):
    """Factory function to create CDN cache middleware"""
    
    def middleware_factory(app):
        return CDNCacheHeadersMiddleware(app, config)
    
    return middleware_factory

# Configuration for different environments
PRODUCTION_CACHE_CONFIG = {
    'api_cache_rules': [
        {
            'pattern': r'/api/v3/batches/\?.*',
            'max_age': 300,  # 5 minutes for production
            'stale_while_revalidate': 900,
            'cache_control': 'public, max-age=300, stale-while-revalidate=900'
        },
        {
            'pattern': r'/api/v2/results/(ultra-)?fast.*',
            'max_age': 120,  # 2 minutes for production
            'stale_while_revalidate': 600,
            'cache_control': 'public, max-age=120, stale-while-revalidate=600'
        }
    ]
}

DEVELOPMENT_CACHE_CONFIG = {
    'api_cache_rules': [
        {
            'pattern': r'/api/.*',
            'max_age': 0,  # No caching in development
            'cache_control': 'no-cache, no-store, must-revalidate'
        }
    ]
}
