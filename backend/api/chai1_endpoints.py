"""
Chai-1 Model API Endpoints
=========================

FastAPI endpoints for Chai-1 biomolecular structure prediction.
Handles FASTA input validation, async Modal execution, and result storage.

Routes:
- POST /predict: Submit Chai-1 prediction job
- GET /health: Health check for Chai-1 service
"""

import json
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
import uuid

# Internal imports
from database.unified_job_manager import unified_job_manager
# Removed: Direct Supabase imports - now using unified GCP manager
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Request/Response Models
class Chai1PredictRequest(BaseModel):
    """Request model for Chai-1 predictions."""
    fasta_content: str = Field(..., description="FASTA formatted sequences with entity|name=identifier headers")
    protein_name: str = Field(..., description="Name of the protein/complex (e.g., IL6, EGFR-complex, etc.) - REQUIRED")
    num_samples: int = Field(5, ge=1, le=10, description="Number of structure predictions (num_diffn_samples)")
    use_msa_server: bool = Field(False, description="Use MSA server for improved accuracy")
    use_templates_server: bool = Field(False, description="Use template server for improved accuracy")
    num_trunk_recycles: int = Field(3, ge=1, le=10, description="Number of trunk recycling iterations")
    num_diffn_timesteps: int = Field(200, ge=50, le=500, description="Number of diffusion timesteps")
    use_esm_embeddings: bool = Field(True, description="Use ESM embeddings")
    seed: int = Field(42, description="Random seed for reproducibility")
    job_name: str = Field(..., description="Name for this prediction job")
    
    @validator('protein_name')
    def validate_protein_name(cls, v):
        """Validate protein name is not empty."""
        if not v or not v.strip():
            raise ValueError("Protein name is required and cannot be empty")
        if len(v.strip()) > 100:
            raise ValueError("Protein name cannot exceed 100 characters")
        return v.strip()
    
    @validator('job_name')
    def validate_job_name(cls, v):
        """Validate job name is not empty."""
        if not v or not v.strip():
            raise ValueError("Job name is required and cannot be empty")
        if len(v.strip()) > 200:
            raise ValueError("Job name cannot exceed 200 characters")
        return v.strip()
    
    @validator('fasta_content')
    def validate_fasta(cls, v):
        """Validate Chai-1 FASTA format with entity type headers."""
        if not v.strip():
            raise ValueError("FASTA content cannot be empty")
        
        lines = v.strip().split('\n')
        if not lines[0].startswith('>'):
            raise ValueError("FASTA must start with '>' header line")
        
        # Validate entity type headers
        headers = [l for l in lines if l.startswith('>')]
        if len(headers) == 0:
            raise ValueError("No FASTA headers found")
        
        valid_entity_types = {'protein', 'ligand', 'dna', 'rna'}
        for header in headers:
            if '|name=' not in header:
                raise ValueError(f"Header must include '|name=identifier': {header}")
            
            entity_part = header.split('|')[0].replace('>', '').lower()
            if entity_part not in valid_entity_types:
                raise ValueError(f"Invalid entity type '{entity_part}'. Must be one of: {valid_entity_types}")
        
        return v

class Chai1PredictResponse(BaseModel):
    """Response model for Chai-1 prediction submission."""
    job_id: str
    status: str
    message: str
    estimated_time: int = Field(600, description="Estimated time in seconds")

class Chai1Structure(BaseModel):
    """Model for a single Chai-1 structure result."""
    pdb_content: str = Field(..., description="Base64 encoded PDB content")
    confidence_score: float = Field(..., description="Average confidence score")
    sample_index: int = Field(..., description="Sample index (0-based)")

class Chai1ResultResponse(BaseModel):
    """Response model for completed Chai-1 predictions."""
    job_id: str
    status: str
    structures: List[Chai1Structure]
    num_structures: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float
    parameters: Dict[str, Any]

# API Endpoints
@router.post("/predict", response_model=Chai1PredictResponse)
async def predict_chai1(
    request: Chai1PredictRequest,
    background_tasks: BackgroundTasks
) -> Chai1PredictResponse:
    """
    Submit a Chai-1 structure prediction job.
    
    This endpoint:
    1. Validates FASTA input
    2. Creates a job entry in the database
    3. Submits to Modal for GPU processing
    4. Returns job ID for status polling
    """
    job_id = str(uuid.uuid4())
    
    try:
        logger.info(f"🚀 Starting Chai-1 prediction for job {job_id}")
        
        # Create job in database
        job_data = {
            "job_id": job_id,
            "job_name": request.job_name,
            "model_name": "chai1",
            "task_type": "structure_prediction",
            "status": "pending",
            "input_data": {
                "protein_name": request.protein_name,
                "fasta_content": request.fasta_content,
                "num_samples": request.num_samples,
                "use_msa_server": request.use_msa_server,
                "use_templates_server": request.use_templates_server,
                "num_trunk_recycles": request.num_trunk_recycles,
                "num_diffn_timesteps": request.num_diffn_timesteps,
                "use_esm_embeddings": request.use_esm_embeddings,
                "seed": request.seed
            },
            "result_data": {},
            "error_message": None
        }
        
        created_job = await unified_job_manager.create_job(job_data)
        logger.info(f"✅ Created job {job_id} in database")
        
        # Run prediction in background
        background_tasks.add_task(
            run_chai1_prediction,
            job_id,
            request.dict()
        )
        
        return Chai1PredictResponse(
            job_id=job_id,
            status="pending",
            message="Chai-1 prediction job created successfully. Use job_id to check status.",
            estimated_time=600  # 10 minutes estimate
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating Chai-1 job: {str(e)}")
        
        # Update job as failed
        try:
            await unified_job_manager.update_job_status(
                job_id,
                status="failed",
                result_data={"error_message": str(e)}
            )
        except:
            pass
            
        raise HTTPException(
            status_code=500,
            detail="Internal server error during prediction submission"
        )

async def run_chai1_prediction(job_id: str, request_data: Dict[str, Any]):
    """
    Run Chai-1 prediction via Modal (background task).
    
    This function:
    1. Updates job status to 'running'
    2. Calls Modal function via subprocess (for auth isolation)
    3. Processes results and stores in database
    4. Updates job status to 'completed' or 'failed'
    """
    try:
        # Update job status to running
        await unified_job_manager.update_job_status(
            job_id,
            status="running"
        )
        logger.info(f"🔄 Running Chai-1 prediction for job {job_id}")
        
        # Prepare Modal input with proper Chai-1 parameters
        modal_input = {
            "fasta_content": request_data["fasta_content"],
            "num_samples": request_data["num_samples"],
            "use_msa_server": request_data["use_msa_server"],
            "use_templates_server": request_data["use_templates_server"],
            "num_trunk_recycles": request_data["num_trunk_recycles"],
            "num_diffn_timesteps": request_data["num_diffn_timesteps"],
            "use_esm_embeddings": request_data["use_esm_embeddings"],
            "seed": request_data["seed"],
            "job_id": job_id
        }
        
        # Write input to temp file for subprocess
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(modal_input, tmp_file)
            tmp_file_path = tmp_file.name
        
        # Run Modal function via subprocess
        cmd = [
            "python3", "-c",
            f"""
import json
import modal

# Load input
with open('{tmp_file_path}', 'r') as f:
    data = json.load(f)

# Load Modal function
chai1_predict_modal = modal.Function.from_name("omtx-hub-chai1", "chai1_predict_modal")

# Call function
result = chai1_predict_modal.remote(**data)
print(json.dumps(result))
"""
        ]
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if process.returncode != 0:
            raise Exception(f"Modal subprocess failed: {process.stderr}")
        
        # Parse result
        result = json.loads(process.stdout)
        
        if not result.get("success", False):
            raise Exception(result.get("error", "Unknown error"))
        
        logger.info(f"✅ Chai-1 prediction completed for job {job_id}")
        
        # Store results in GCP Storage
        stored_structures = []
        for structure in result.get("structures", []):
            # Upload PDB to storage bucket
            file_name = f"sample_{structure['sample_index']}.pdb"
            pdb_bytes = base64.b64decode(structure['pdb_content'])
            
            try:
                # Upload to GCP Cloud Storage via unified job manager
                upload_success = unified_job_manager.upload_job_file(
                    job_id=job_id,
                    file_name=file_name,
                    file_content=pdb_bytes,
                    content_type="chemical/x-pdb"
                )
                
                storage_path = f"jobs/{job_id}/{file_name}" if upload_success else None
                
                stored_structures.append({
                    "sample_index": structure['sample_index'],
                    "confidence_score": structure['confidence_score'],
                    "file_path": storage_path,
                    "file_name": file_name
                })
            except Exception as e:
                logger.warning(f"Failed to upload structure file for sample {structure['sample_index']}: {e}")
                # Fallback: store structure content directly in results
                stored_structures.append({
                    "sample_index": structure['sample_index'],
                    "confidence_score": structure['confidence_score'],
                    "pdb_content": structure['pdb_content']  # Base64 encoded
                })
        
        # Update job with results
        await unified_job_manager.update_job_status(
            job_id,
            status="completed",
            result_data={
                "structures": stored_structures,
                "num_structures": result.get("num_structures", 0),
                "metadata": result.get("metadata", {}),
                "execution_time": result.get("execution_time", 0),
                "parameters": result.get("parameters", {})
            }
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Chai-1 prediction timed out for job {job_id}")
        await unified_job_manager.update_job_status(
            job_id,
            status="failed",
            result_data={"error_message": "Prediction timed out after 1 hour"}
        )
    except Exception as e:
        logger.error(f"❌ Chai-1 prediction failed for job {job_id}: {str(e)}")
        await unified_job_manager.update_job_status(
            job_id,
            status="failed",
            result_data={"error_message": str(e)}
        )
    finally:
        # Clean up temp file
        try:
            import os
            os.unlink(tmp_file_path)
        except:
            pass

@router.get("/health")
async def health_check():
    """Check health of Chai-1 service."""
    try:
        # Check if Modal function is accessible
        import modal
        chai1_function = modal.Function.from_name("omtx-hub-chai1", "chai1_predict_modal")
        
        return {
            "status": "healthy",
            "model": "chai1",
            "modal_app": "omtx-hub-chai1",
            "modal_function": "available"
        }
    except Exception as e:
        logger.warning(f"Chai-1 health check warning: {str(e)}")
        return {
            "status": "degraded",
            "model": "chai1",
            "error": str(e)
        }