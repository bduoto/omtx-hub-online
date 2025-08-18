"""
RFAntibody API endpoints for nanobody design
"""
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from database.unified_job_manager import unified_job_manager

# Create router
router = APIRouter()

# Request/Response Models
class RFAntibodyPredictRequest(BaseModel):
    target_name: str = Field(..., description="Name of the target protein/antigen (e.g., EGFR, HER2, etc.) - REQUIRED")
    pdb_content: str = Field(..., description="PDB structure content for the target")
    hotspot_residues: list[str] = Field(..., description="List of hotspot residue positions")
    num_designs: int = Field(10, ge=1, le=50, description="Number of nanobody designs to generate")
    run_relax: bool = Field(False, description="Run relaxation on generated designs")
    job_name: str = Field(..., description="Name for this nanobody design job")
    
    @validator('target_name')
    def validate_target_name(cls, v):
        """Validate target name is not empty."""
        if not v or not v.strip():
            raise ValueError("Target name is required and cannot be empty")
        if len(v.strip()) > 100:
            raise ValueError("Target name cannot exceed 100 characters")
        return v.strip()
    
    @validator('job_name')
    def validate_job_name(cls, v):
        """Validate job name is not empty."""
        if not v or not v.strip():
            raise ValueError("Job name is required and cannot be empty")
        if len(v.strip()) > 200:
            raise ValueError("Job name cannot exceed 200 characters")
        return v.strip()
    
    @validator('pdb_content')
    def validate_pdb_content(cls, v):
        """Validate PDB content is not empty."""
        if not v or not v.strip():
            raise ValueError("PDB content is required and cannot be empty")
        if len(v.strip()) < 50:
            raise ValueError("PDB content appears too short to be valid")
        return v.strip()
    
    @validator('hotspot_residues')
    def validate_hotspot_residues(cls, v):
        """Validate hotspot residues list."""
        if not v or len(v) == 0:
            raise ValueError("At least one hotspot residue is required")
        return v

class RFAntibodyPredictResponse(BaseModel):
    job_id: str
    status: str
    message: str
    num_designs_generated: Optional[int] = None
    backbone_designs: Optional[list] = None
    sequence_designs: Optional[list] = None
    final_structures: Optional[list] = None
    design_scores: Optional[list] = None
    pipeline_status: Optional[dict] = None
    execution_time: Optional[float] = None

@router.post("/predict", response_model=RFAntibodyPredictResponse)
async def predict_nanobody_design(request: RFAntibodyPredictRequest):
    """
    Generate nanobody designs using RFAntibody pipeline
    """
    
    # Load Modal function dynamically to avoid auth conflicts
    try:
        import modal
        import os
        from services.modal_auth_service import modal_auth_service

        # Use secure credential management
        if not modal_auth_service.validate_credentials():
            raise HTTPException(
                status_code=503,
                detail="Modal authentication not configured. Please configure Modal credentials."
            )

        # Set credentials from secure service
        env = modal_auth_service.create_auth_env()
        os.environ.update(env)

        rfantibody_predict_modal = modal.Function.from_name("rfantibody-real-phase2", "rfantibody_predict_real_phase2")
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"RFAntibody service is currently unavailable: {str(e)}"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Create job entry using unified job manager
        job_data = {
            "id": job_id,
            "model_name": "rfantibody",
            "status": "pending",
            "type": "nanobody_design",
            "name": request.job_name,
            "input_data": {
                "target_name": request.target_name,
                "pdb_content": request.pdb_content[:1000] + "..." if len(request.pdb_content) > 1000 else request.pdb_content,
                "hotspot_residues": request.hotspot_residues,
                "num_designs": request.num_designs,
                "run_relax": request.run_relax
            }
        }
        created_job_id = await unified_job_manager.create_job(job_data)
        actual_job_id = created_job_id
        
        print(f"🚀 Starting RFAntibody prediction for job {actual_job_id}")
        print(f"   - Hotspot residues: {request.hotspot_residues}")
        print(f"   - Num designs: {request.num_designs}")
        print(f"   - PDB length: {len(request.pdb_content)} chars")
        
        # Extract target chain from hotspot residues (assume first hotspot chain)
        target_chain = "A"  # Default
        if request.hotspot_residues:
            first_hotspot = request.hotspot_residues[0]
            if ":" in first_hotspot:
                target_chain = first_hotspot.split(":")[0]
        
        # Call RFAntibody Modal function asynchronously
        print("🚀 Starting RFAntibody Modal function asynchronously")
        call = rfantibody_predict_modal.spawn(
            target_pdb_content=request.pdb_content,
            target_chain=target_chain,
            hotspot_residues=request.hotspot_residues,
            num_designs=request.num_designs,
            framework="vhh",
            job_id=actual_job_id
        )
        
        # Update job status to "running"
        await unified_job_manager.update_job_status(actual_job_id, "running")
        
        print(f"🚀 RFAntibody prediction started asynchronously for job {actual_job_id}")
        print(f"   - Modal call ID: {call.object_id}")
        
        # Store the Modal call ID for later result retrieval
        await unified_job_manager.update_job_status(actual_job_id, "running", {
            "modal_call_id": call.object_id,
            "modal_function": "rfantibody_predict_real_phase2"
        })
        
        # Return immediately - frontend will poll for results
        return RFAntibodyPredictResponse(
            job_id=actual_job_id,
            status="running",
            message="Nanobody design prediction started successfully. Check job status for completion.",
            num_designs_generated=None,
            backbone_designs=None,
            sequence_designs=None,
            final_structures=None,
            design_scores=None,
            pipeline_status={"status": "running", "message": "RFAntibody pipeline started"},
            execution_time=None
        )
        
    except Exception as e:
        error_msg = f"RFAntibody prediction failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Update job with error
        try:
            await unified_job_manager.update_job_status(actual_job_id, "failed")
        except:
            pass
        
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/status/{job_id}")
async def get_rfantibody_job_status(job_id: str):
    """
    Get the status of an RFAntibody prediction job
    """
    try:
        # Get job from database
        job = await unified_job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # If job is already completed or failed, return stored results
        if job.get("status") in ["completed", "failed"]:
            return {
                "job_id": job_id,
                "status": job["status"],
                "results": job.get("results", {}),
                "created_at": job.get("created_at"),
                "completed_at": job.get("completed_at")
            }
        
        # For running jobs, return status immediately without blocking Modal check
        # The background monitoring service will handle status updates
        
        # Still running or no Modal call ID
        return {
            "job_id": job_id,
            "status": job.get("status", "pending"),
            "message": "RFAntibody pipeline is running. Results will be updated when complete.",
            "created_at": job.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking job status: {str(e)}"
        )

async def check_modal_status_async(modal_call_id: str) -> Dict[str, Any]:
    """
    Check Modal status asynchronously with timeout to avoid blocking
    """
    import asyncio
    import subprocess
    import json
    
    # Create a subprocess script to check Modal status
    check_script = f'''
import modal
import os
import json

os.environ["MODAL_TOKEN_ID"] = "ak-4gwOEVs4hEAwy27Lf7b1Tz"
os.environ["MODAL_TOKEN_SECRET"] = "as-cauu6z3bil26giQmKgXdyQ"

try:
    call = modal.FunctionCall.from_id("{modal_call_id}")
    result = call.get(timeout=8)  # 8 second timeout for Modal call
    print(json.dumps({{"status": "completed", "result": result}}))
except Exception as e:
    error_str = str(e).lower()
    if any(keyword in error_str for keyword in ["still running", "not finished", "pending", "timeout", "timed out"]):
        print(json.dumps({{"status": "running", "error": str(e)}}))
    else:
        print(json.dumps({{"status": "failed", "error": str(e)}}))
'''
    
    try:
        # Run subprocess with timeout
        process = await asyncio.create_subprocess_exec(
            "python3", "-c", check_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=10.0  # 10 second timeout for better reliability
        )
        
        if process.returncode == 0 and stdout:
            return json.loads(stdout.decode().strip())
        else:
            return {"status": "running", "error": "Could not check Modal status"}
            
    except asyncio.TimeoutError:
        # Timeout means probably still running
        return {"status": "running", "error": "Modal status check timed out"}
    except Exception as e:
        return {"status": "running", "error": f"Error checking Modal: {str(e)}"}