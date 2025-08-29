"""
OMTX-Hub Clean API Backend
Consolidated 11-endpoint API for Boltz-2, RFAntibody, and Chai-1 predictions

BEFORE: 101 scattered endpoints across multiple versions
AFTER: 11 clean, unified endpoints with consistent patterns
"""

import os
import logging
from pathlib import Path

# Initialize logging service first
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("✅ Environment variables loaded from .env file")
except ImportError:
    logging.warning("⚠️ python-dotenv not installed, using system environment")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
import uvicorn

# Import monitoring and metrics (optional)
try:
    from services.metrics_service import MetricsMiddleware, get_metrics_response
    METRICS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Metrics service not available: {e}")
    METRICS_AVAILABLE = False
    
    # Create dummy middleware for compatibility
    class MetricsMiddleware:
        def __init__(self, app): 
            self.app = app
        
        async def __call__(self, scope, receive, send):
            # Pass through without any metrics collection
            return await self.app(scope, receive, send)
    
    def get_metrics_response():
        return {"error": "metrics not available"}

# Import our APIs
from api.consolidated_api import router as api_v1_router
from api.job_orchestration_api import router as jobs_router
from api.auth_api import router as auth_router
from api.webhook_api import router as webhook_router
from api.async_prediction_api import router as async_api_router

# Initialize logging service first (optional)
try:
    from services.logging_service import logging_service
    logger.info("✅ Logging service imported")
except ImportError as e:
    logger.warning(f"⚠️ Logging service not available: {e}")
    logging_service = None

# Create FastAPI app
app = FastAPI(
    title="OMTX-Hub Protein Prediction API",
    description="""
    Clean, unified API for protein predictions across multiple models.
    
    **Supported Models:**
    - **Boltz-2**: Protein-ligand binding predictions
    - **RFAntibody**: Antibody design and optimization
    - **Chai-1**: Multi-modal structure predictions
    
    **Key Features:**
    - 🧬 Single API for all prediction models
    - 📊 Unified job and batch management
    - 📥 Consistent file download patterns
    - 🏥 Real-time health monitoring
    - 🎯 Type-safe TypeScript client available
    
    **Endpoints:** 11 total (vs 101 legacy endpoints)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(MetricsMiddleware)  # Add metrics collection first
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React dev
        "http://localhost:5173",   # Vite dev
        "http://localhost:5174",   # Vite dev alt port
        "http://localhost:8080",   # Alt dev
        "http://localhost:8081",   # Alt dev
        "https://omtx-hub-native-338254269321.us-central1.run.app",  # Cloud Run production
    ],
    allow_origin_regex=r"https://.*\.(vercel|netlify)\.app",  # Allow Vercel/Netlify subdomains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers (order matters for route precedence)
app.include_router(auth_router)      # Authentication API
app.include_router(webhook_router)   # Webhook management API
app.include_router(async_api_router) # Async prediction API (Cloud Run Jobs)
app.include_router(jobs_router)      # Job orchestration API  
app.include_router(api_v1_router)    # General consolidated API

# Add migration API for consolidating all jobs under deployment user
try:
    from api.migration_api import router as migration_router
    app.include_router(migration_router)
    logger.info("✅ Migration API endpoints added at /api/migration")
except ImportError:
    logger.warning("⚠️ Migration API not available")

# Root endpoint - redirect to docs
@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# API v2 compatibility routes (temporary)
@app.post("/api/v2/predict")
async def v2_predict_compat(request: Request):
    """Compatibility route for v2 predict - redirects to v1"""
    return RedirectResponse(url="/api/v1/predict", status_code=307)

@app.post("/api/v2/predict/batch")
async def v2_predict_batch_compat(request: Request):
    """Compatibility route for v2 batch predict - redirects to v1"""
    return RedirectResponse(url="/api/v1/predict/batch", status_code=307)

# Simple health check (non-versioned for load balancers)
@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for load balancers and monitoring
    """
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "api_version": "v1",
        "available_models": ["boltz2", "rfantibody", "chai1"],
        "endpoints": 11,
        "message": "OMTX-Hub Consolidated API operational"
    }

# Health check with API prefix (for compatibility)
@app.get("/api/health")
async def api_health_check():
    """Health check with API prefix for compatibility"""
    return await health_check()

# V2 compatibility routes (for frontend backward compatibility)
from fastapi.responses import RedirectResponse

@app.post("/api/v2/predict")
async def v2_predict_compat():
    """V2 predict endpoint - redirects to V1"""
    return RedirectResponse(url="/api/v1/predict", status_code=307)

@app.post("/api/v2/predict/batch")
async def v2_predict_batch_compat():
    """V2 batch predict endpoint - redirects to V1"""
    return RedirectResponse(url="/api/v1/predict/batch", status_code=307)

# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint for monitoring"""
    return get_metrics_response()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 OMTX-Hub Consolidated API starting up")
    logger.info("📊 Available endpoints: 11 (consolidated from 101 legacy)")
    logger.info("🧬 Supported models: Boltz-2, RFAntibody, Chai-1")
    logger.info("🎯 API version: v1")
    logger.info("📚 Documentation: /docs")
    
    # Validate critical services on startup
    try:
        # Test database connection
        from database.unified_job_manager import unified_job_manager
        status = unified_job_manager.get_status()
        logger.info(f"🗄️ DB status: {status}")
        db_healthy = status.get("available", False)
        
        if db_healthy:
            logger.info("✅ Database connection healthy")
        else:
            logger.warning("⚠️ Database connection issues detected")
            
    except Exception as e:
        logger.error(f"❌ Startup health check failed: {e}")
    
    # Start job monitoring service (optional for Cloud Run)
    ENABLE_JOB_MONITORING = os.getenv("ENABLE_JOB_MONITORING", "false").lower() == "true"
    if ENABLE_JOB_MONITORING:
        try:
            from services.job_monitoring_service import job_monitoring_service
            await job_monitoring_service.start_monitoring()
            logger.info("✅ Job monitoring service started")
        except Exception as e:
            logger.error(f"❌ Failed to start job monitoring service: {e}")
    else:
        logger.info("ℹ️ Job monitoring service disabled (ENABLE_JOB_MONITORING=false)")
    
    # Start system monitoring service (optional for Cloud Run)
    ENABLE_SYSTEM_MONITORING = os.getenv("ENABLE_SYSTEM_MONITORING", "false").lower() == "true"
    if ENABLE_SYSTEM_MONITORING:
        try:
            from services.monitoring_service import monitoring_service
            await monitoring_service.start_monitoring()
            logger.info("✅ Monitoring service started")
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring service: {e}")
    else:
        logger.info("ℹ️ System monitoring service disabled (ENABLE_SYSTEM_MONITORING=false)")

# Shutdown event
@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("🛑 OMTX-Hub Consolidated API shutting down")
    
    # Stop job monitoring service (if enabled)
    ENABLE_JOB_MONITORING = os.getenv("ENABLE_JOB_MONITORING", "false").lower() == "true"
    if ENABLE_JOB_MONITORING:
        try:
            from services.job_monitoring_service import job_monitoring_service
            await job_monitoring_service.stop_monitoring()
            logger.info("✅ Job monitoring service stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop job monitoring service: {e}")
    
    logger.info("✅ Clean shutdown completed")

# Development server
if __name__ == "__main__":
    # Development settings
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🔧 Starting development server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
        access_log=True
    )