"""
Metrics Service for OMTX-Hub
Prometheus metrics collection and exposure
"""

import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Prometheus Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_requests = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

# Job Metrics
jobs_total = Counter(
    'omtx_hub_jobs_total',
    'Total jobs submitted',
    ['job_type', 'user_id']
)

job_completions_total = Counter(
    'omtx_hub_job_completions_total',
    'Total job completions',
    ['job_type', 'status']
)

job_failures_total = Counter(
    'omtx_hub_job_failures_total',
    'Total job failures',
    ['job_type', 'error_type']
)

job_duration_seconds = Histogram(
    'omtx_hub_job_duration_seconds',
    'Job execution duration in seconds',
    ['job_type']
)

active_jobs = Gauge(
    'omtx_hub_active_jobs',
    'Currently active jobs'
)

completed_jobs = Gauge(
    'omtx_hub_completed_jobs',
    'Jobs completed in last hour'
)

failed_jobs = Gauge(
    'omtx_hub_failed_jobs',
    'Jobs failed in last hour'
)

# System Metrics
gpu_utilization = Gauge(
    'omtx_hub_gpu_utilization',
    'GPU utilization percentage'
)

storage_usage = Gauge(
    'omtx_hub_storage_usage',
    'Storage usage in GB'
)

active_users = Gauge(
    'omtx_hub_active_users',
    'Active users in last hour'
)

error_rate = Gauge(
    'omtx_hub_error_rate',
    'Error rate percentage'
)

# Authentication Metrics
auth_attempts_total = Counter(
    'omtx_hub_auth_attempts_total',
    'Total authentication attempts',
    ['result']
)

webhook_deliveries_total = Counter(
    'omtx_hub_webhook_deliveries_total',
    'Total webhook deliveries',
    ['status']
)

# Application Info
app_info = Info(
    'omtx_hub_app',
    'Application information'
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        active_requests.inc()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            method = request.method
            endpoint = self._get_endpoint_pattern(request)
            status = str(response.status_code)
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint, 
                status=status
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record failed requests
            duration = time.time() - start_time
            method = request.method
            endpoint = self._get_endpoint_pattern(request)
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status="500"
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            raise
            
        finally:
            active_requests.dec()
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern from request"""
        
        path = request.url.path
        
        # Map common patterns
        if path.startswith("/api/v1/predict"):
            if "/batch" in path:
                return "/api/v1/predict/batch"
            else:
                return "/api/v1/predict"
        elif path.startswith("/api/v1/jobs/"):
            return "/api/v1/jobs/{id}"
        elif path.startswith("/api/v1/batches/"):
            return "/api/v1/batches/{id}"
        elif path.startswith("/api/v1/webhooks/"):
            return "/api/v1/webhooks/*"
        elif path.startswith("/api/auth/"):
            return "/api/auth/*"
        elif path == "/health":
            return "/health"
        elif path == "/docs" or path.startswith("/openapi"):
            return "/docs"
        else:
            return path

class MetricsService:
    """Service for managing application metrics"""
    
    def __init__(self):
        self._initialize_app_info()
        logger.info("📊 Metrics service initialized")
    
    def _initialize_app_info(self):
        """Initialize application info metrics"""
        
        import os
        
        app_info.info({
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'service_name': os.getenv('SERVICE_NAME', 'omtx-hub-api'),
            'project_id': os.getenv('GCP_PROJECT_ID', 'om-models')
        })
    
    def record_job_submission(self, job_type: str, user_id: str):
        """Record job submission"""
        jobs_total.labels(job_type=job_type, user_id=user_id).inc()
    
    def record_job_completion(self, job_type: str, status: str, duration_seconds: float):
        """Record job completion"""
        job_completions_total.labels(job_type=job_type, status=status).inc()
        job_duration_seconds.labels(job_type=job_type).observe(duration_seconds)
    
    def record_job_failure(self, job_type: str, error_type: str):
        """Record job failure"""
        job_failures_total.labels(job_type=job_type, error_type=error_type).inc()
    
    def update_system_metrics(self, metrics_data: Dict[str, Any]):
        """Update system-level metrics"""
        
        active_jobs.set(metrics_data.get('active_jobs', 0))
        completed_jobs.set(metrics_data.get('completed_jobs_last_hour', 0))
        failed_jobs.set(metrics_data.get('failed_jobs_last_hour', 0))
        gpu_utilization.set(metrics_data.get('gpu_utilization', 0))
        storage_usage.set(metrics_data.get('storage_usage_gb', 0))
        active_users.set(metrics_data.get('active_users', 0))
        error_rate.set(metrics_data.get('error_rate', 0))
    
    def record_auth_attempt(self, success: bool):
        """Record authentication attempt"""
        result = "success" if success else "failure"
        auth_attempts_total.labels(result=result).inc()
    
    def record_webhook_delivery(self, success: bool):
        """Record webhook delivery"""
        status = "success" if success else "failure"
        webhook_deliveries_total.labels(status=status).inc()
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest()

# Global metrics service instance
metrics_service = MetricsService()

def get_metrics_response() -> Response:
    """Get metrics as HTTP response"""
    
    metrics_data = metrics_service.get_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )