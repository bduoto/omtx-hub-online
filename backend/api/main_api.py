"""
Clean OMTX-Hub Main API
Uses only the consolidated v1 API + health check

11 endpoints total (vs 101 scattered endpoints)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import logging

from .consolidated_api import router as api_v1_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OMTX-Hub Protein Prediction API",
    description="Clean, unified API for Boltz-2, RFAntibody, and Chai-1 predictions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8080",
        "http://localhost:8081"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only the consolidated API
app.include_router(api_v1_router)

# Root redirect to docs
@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Simple health check (non-versioned)
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "available_models": ["boltz2", "rfantibody", "chai1"]
    }

# Health check alias
@app.get("/api/health")
async def api_health_check():
    """Health check with API prefix"""
    return await health_check()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)