"""
OMTX-Hub Clean API Backend
Consolidated 11-endpoint API for Boltz-2, RFAntibody, and Chai-1 predictions

BEFORE: 101 scattered endpoints across multiple versions
AFTER: 11 clean, unified endpoints with consistent patterns
"""

import os
import logging
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("✅ Environment variables loaded from .env file")
except ImportError:
    logging.warning("⚠️ python-dotenv not installed, using system environment")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
import uvicorn

# Import our clean consolidated API
from api.consolidated_api import router as api_v1_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React dev
        "http://localhost:5173",   # Vite dev  
        "http://localhost:8080",   # Alt dev
        "http://localhost:8081",   # Alt dev
        "https://*.vercel.app",    # Vercel deployments
        "https://*.netlify.app",   # Netlify deployments
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include the consolidated API v1 (prefix already set in router)
app.include_router(api_v1_router)

# Root endpoint - redirect to docs
@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Simple health check (non-versioned for load balancers)
@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for load balancers and monitoring
    """
    return {
        "status": "healthy",
        "timestamp": "2025-01-20T18:00:00Z",
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
        from database.unified_job_manager import UnifiedJobManager
        job_manager = UnifiedJobManager()
        db_healthy = await job_manager.health_check()
        
        if db_healthy:
            logger.info("✅ Database connection healthy")
        else:
            logger.warning("⚠️ Database connection issues detected")
            
    except Exception as e:
        logger.error(f"❌ Startup health check failed: {e}")

# Shutdown event
@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("🛑 OMTX-Hub Consolidated API shutting down")
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