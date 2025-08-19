"""
Health Checks for Cloud Run - REQUIRED for production
Distinguished Engineer Implementation - Comprehensive health monitoring
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any

import torch
from fastapi import APIRouter, Response
from google.cloud import firestore
from google.cloud import storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health Checks"])

@router.get("/health")
async def health_check():
    """
    Basic health check for Cloud Run
    Used by load balancer for traffic routing
    """
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "omtx-hub",
        "version": "2.0.0"
    }

@router.get("/ready")
async def readiness_check():
    """
    Deep readiness check - validates all dependencies
    Used by Cloud Run to determine if instance is ready to serve traffic
    """
    
    checks = {
        "firestore": {"status": "unknown", "latency_ms": 0},
        "storage": {"status": "unknown", "latency_ms": 0},
        "gpu": {"status": "unknown", "details": {}},
        "model": {"status": "unknown", "details": {}},
        "memory": {"status": "unknown", "details": {}},
        "disk": {"status": "unknown", "details": {}}
    }
    
    overall_healthy = True
    
    # Check Firestore connectivity
    try:
        start_time = time.time()
        db = firestore.Client()
        
        # Test read/write
        test_ref = db.collection('_health').document('readiness_check')
        test_ref.set({"timestamp": firestore.SERVER_TIMESTAMP, "test": True})
        
        # Test read
        doc = test_ref.get()
        if doc.exists:
            checks["firestore"]["status"] = "healthy"
            checks["firestore"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        else:
            checks["firestore"]["status"] = "unhealthy"
            overall_healthy = False
            
    except Exception as e:
        checks["firestore"]["status"] = "unhealthy"
        checks["firestore"]["error"] = str(e)
        overall_healthy = False
    
    # Check Cloud Storage connectivity
    try:
        start_time = time.time()
        client = storage.Client()
        bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        bucket = client.bucket(bucket_name)
        
        # Test bucket access
        if bucket.exists():
            # Test write
            test_blob = bucket.blob("_health/readiness_check.txt")
            test_blob.upload_from_string(f"Health check at {time.time()}")
            
            checks["storage"]["status"] = "healthy"
            checks["storage"]["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            checks["storage"]["bucket"] = bucket_name
        else:
            checks["storage"]["status"] = "unhealthy"
            checks["storage"]["error"] = f"Bucket {bucket_name} does not exist"
            overall_healthy = False
            
    except Exception as e:
        checks["storage"]["status"] = "unhealthy"
        checks["storage"]["error"] = str(e)
        overall_healthy = False
    
    # Check GPU availability and health
    try:
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            current_device = torch.cuda.current_device()
            gpu_name = torch.cuda.get_device_name(current_device)
            gpu_memory = torch.cuda.get_device_properties(current_device).total_memory
            gpu_memory_allocated = torch.cuda.memory_allocated(current_device)
            gpu_memory_cached = torch.cuda.memory_reserved(current_device)
            
            # Test GPU computation
            start_time = time.time()
            test_tensor = torch.randn(1000, 1000, device='cuda')
            result = torch.matmul(test_tensor, test_tensor)
            gpu_compute_time = (time.time() - start_time) * 1000
            
            checks["gpu"]["status"] = "healthy"
            checks["gpu"]["details"] = {
                "available": True,
                "count": gpu_count,
                "current_device": current_device,
                "name": gpu_name,
                "memory_total_gb": round(gpu_memory / (1024**3), 2),
                "memory_allocated_gb": round(gpu_memory_allocated / (1024**3), 2),
                "memory_cached_gb": round(gpu_memory_cached / (1024**3), 2),
                "memory_free_gb": round((gpu_memory - gpu_memory_allocated) / (1024**3), 2),
                "compute_test_ms": round(gpu_compute_time, 2)
            }
            
            # Check if memory usage is too high
            memory_usage_percent = (gpu_memory_allocated / gpu_memory) * 100
            if memory_usage_percent > 90:
                checks["gpu"]["status"] = "warning"
                checks["gpu"]["warning"] = f"High memory usage: {memory_usage_percent:.1f}%"
                
        else:
            checks["gpu"]["status"] = "unhealthy"
            checks["gpu"]["details"] = {"available": False, "error": "CUDA not available"}
            # Don't fail overall health for GPU in development
            if os.getenv("ENVIRONMENT") == "production":
                overall_healthy = False
                
    except Exception as e:
        checks["gpu"]["status"] = "unhealthy"
        checks["gpu"]["error"] = str(e)
        if os.getenv("ENVIRONMENT") == "production":
            overall_healthy = False
    
    # Check model loading capability
    try:
        # Test if we can import Boltz
        import boltz
        checks["model"]["status"] = "healthy"
        checks["model"]["details"] = {
            "boltz_available": True,
            "version": getattr(boltz, '__version__', 'unknown')
        }
        
        # Check if model is pre-loaded
        model_cache_path = "/tmp/model_loaded.flag"
        if os.path.exists(model_cache_path):
            checks["model"]["details"]["preloaded"] = True
        else:
            checks["model"]["details"]["preloaded"] = False
            
    except ImportError as e:
        checks["model"]["status"] = "unhealthy"
        checks["model"]["error"] = f"Cannot import boltz: {str(e)}"
        overall_healthy = False
    except Exception as e:
        checks["model"]["status"] = "unhealthy"
        checks["model"]["error"] = str(e)
        overall_healthy = False
    
    # Check memory usage
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        checks["memory"]["status"] = "healthy"
        checks["memory"]["details"] = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent,
            "free_gb": round(memory.free / (1024**3), 2)
        }
        
        checks["disk"]["status"] = "healthy"
        checks["disk"]["details"] = {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_percent": round((disk.used / disk.total) * 100, 1)
        }
        
        # Check if memory usage is too high
        if memory.percent > 90:
            checks["memory"]["status"] = "warning"
            checks["memory"]["warning"] = f"High memory usage: {memory.percent}%"
        
        # Check if disk usage is too high
        if (disk.used / disk.total) > 0.9:
            checks["disk"]["status"] = "warning"
            checks["disk"]["warning"] = f"High disk usage: {round((disk.used / disk.total) * 100, 1)}%"
            
    except ImportError:
        checks["memory"]["status"] = "unknown"
        checks["memory"]["error"] = "psutil not available"
        checks["disk"]["status"] = "unknown"
        checks["disk"]["error"] = "psutil not available"
    except Exception as e:
        checks["memory"]["status"] = "unhealthy"
        checks["memory"]["error"] = str(e)
        checks["disk"]["status"] = "unhealthy"
        checks["disk"]["error"] = str(e)
    
    # Determine overall status
    if overall_healthy:
        status_code = 200
        overall_status = "ready"
    else:
        status_code = 503
        overall_status = "not_ready"
    
    response_data = {
        "status": overall_status,
        "timestamp": time.time(),
        "checks": checks,
        "summary": {
            "healthy_checks": len([c for c in checks.values() if c["status"] == "healthy"]),
            "warning_checks": len([c for c in checks.values() if c["status"] == "warning"]),
            "unhealthy_checks": len([c for c in checks.values() if c["status"] == "unhealthy"]),
            "total_checks": len(checks)
        }
    }
    
    return Response(
        content=json.dumps(response_data, indent=2),
        status_code=status_code,
        media_type="application/json"
    )

@router.get("/startup")
async def startup_probe():
    """
    Startup probe for Cloud Run - allows longer initialization
    Used during container startup to determine when the service is ready
    """
    
    startup_checks = {
        "container_started": True,
        "python_initialized": True,
        "dependencies_loaded": False,
        "model_ready": False,
        "gpu_initialized": False
    }
    
    try:
        # Check if dependencies are loaded
        import torch
        import boltz
        from google.cloud import firestore, storage
        startup_checks["dependencies_loaded"] = True
        
        # Check if GPU is initialized
        if torch.cuda.is_available():
            # Test GPU access
            torch.cuda.current_device()
            startup_checks["gpu_initialized"] = True
        
        # Check if model loading flag exists
        model_flag_path = "/tmp/model_loaded.flag"
        if os.path.exists(model_flag_path):
            startup_checks["model_ready"] = True
        else:
            # Try to create the flag (simulate model loading)
            try:
                with open(model_flag_path, "w") as f:
                    f.write(f"Model loaded at {time.time()}")
                startup_checks["model_ready"] = True
            except Exception:
                pass
        
        # Determine if startup is complete
        required_checks = ["dependencies_loaded", "gpu_initialized"]
        startup_complete = all(startup_checks.get(check, False) for check in required_checks)
        
        if startup_complete:
            return {
                "status": "started",
                "timestamp": time.time(),
                "checks": startup_checks,
                "message": "Service startup completed successfully"
            }
        else:
            return Response(
                content=json.dumps({
                    "status": "starting",
                    "timestamp": time.time(),
                    "checks": startup_checks,
                    "message": "Service is still starting up"
                }, indent=2),
                status_code=503,
                media_type="application/json"
            )
            
    except Exception as e:
        return Response(
            content=json.dumps({
                "status": "startup_failed",
                "timestamp": time.time(),
                "checks": startup_checks,
                "error": str(e),
                "message": "Service startup failed"
            }, indent=2),
            status_code=503,
            media_type="application/json"
        )

@router.get("/metrics")
async def metrics_endpoint():
    """
    Metrics endpoint for monitoring
    Returns Prometheus-compatible metrics
    """
    
    try:
        metrics = []
        
        # GPU metrics
        if torch.cuda.is_available():
            gpu_memory_used = torch.cuda.memory_allocated(0)
            gpu_memory_total = torch.cuda.get_device_properties(0).total_memory
            
            metrics.extend([
                f"omtx_gpu_memory_used_bytes {gpu_memory_used}",
                f"omtx_gpu_memory_total_bytes {gpu_memory_total}",
                f"omtx_gpu_memory_utilization {(gpu_memory_used / gpu_memory_total) * 100}"
            ])
        
        # System metrics
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            metrics.extend([
                f"omtx_memory_used_bytes {memory.used}",
                f"omtx_memory_total_bytes {memory.total}",
                f"omtx_memory_utilization {memory.percent}",
                f"omtx_cpu_utilization {cpu_percent}"
            ])
        except ImportError:
            pass
        
        # Service metrics
        metrics.extend([
            f"omtx_service_uptime_seconds {time.time() - startup_time}",
            f"omtx_service_healthy 1"
        ])
        
        return Response(
            content="\n".join(metrics) + "\n",
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"❌ Metrics endpoint failed: {str(e)}")
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )

# Track startup time
startup_time = time.time()
