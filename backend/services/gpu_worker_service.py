"""
GPU Worker Service for Cloud Run
Receives Cloud Tasks and executes GPU jobs with user validation
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import subprocess
import tempfile

from google.cloud import firestore
from auth.jwt_auth import JWTAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firestore
db = firestore.Client()

class JobTaskPayload(BaseModel):
    """Cloud Task payload for GPU job execution"""
    job_id: str
    job_type: str
    batch_id: Optional[str] = None
    timestamp: str
    auth_token: Optional[str] = None

class GPUWorkerService:
    """GPU Worker Service that processes Cloud Tasks for GPU jobs"""
    
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID', 'om-models')
        self.bucket_name = os.getenv('GCS_BUCKET_NAME', 'hub-job-files')
        
        logger.info(f"🎮 GPU Worker Service initialized for project: {self.project_id}")
    
    async def process_job_task(self, payload: JobTaskPayload) -> Dict[str, Any]:
        """Process a GPU job task with user validation"""
        
        start_time = datetime.utcnow()
        logger.info(f"🚀 Processing GPU job task: {payload.job_id} (type: {payload.job_type})")
        
        try:
            # 1. Get job details from Firestore
            job_ref = db.collection('jobs').document(payload.job_id)
            job_doc = job_ref.get()
            
            if not job_doc.exists:
                raise ValueError(f"Job {payload.job_id} not found in database")
            
            job_data = job_doc.to_dict()
            user_id = job_data.get('user_id')
            
            if not user_id:
                raise ValueError(f"No user_id found for job {payload.job_id}")
            
            # 2. Validate auth token if provided
            if payload.auth_token:
                try:
                    token_payload = JWTAuth.verify_token(payload.auth_token)
                    token_user_id = token_payload.get('user_id')
                    
                    if token_user_id != user_id:
                        raise ValueError(f"Token user_id ({token_user_id}) doesn't match job user_id ({user_id})")
                    
                    logger.info(f"✅ JWT token validated for user: {user_id}")
                    
                except Exception as e:
                    raise ValueError(f"Auth token validation failed: {e}")
            else:
                # Development mode warning
                if os.getenv('ENVIRONMENT') == 'development':
                    logger.warning(f"⚠️ No auth token provided for job {payload.job_id} (development mode)")
                else:
                    raise ValueError("Auth token required for GPU job processing")
            
            # 3. Update job status to running
            job_ref.update({
                'status': 'running',
                'started_at': firestore.SERVER_TIMESTAMP,
                'gpu_worker_started': start_time,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # 4. Execute GPU job based on type
            if payload.job_type in ['INDIVIDUAL', 'BATCH_CHILD']:
                result = await self._execute_boltz2_job(
                    job_id=payload.job_id,
                    user_id=user_id,
                    job_data=job_data,
                    auth_token=payload.auth_token
                )
            else:
                raise ValueError(f"Unsupported job type: {payload.job_type}")
            
            # 5. Update job status to completed
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            job_ref.update({
                'status': 'completed',
                'completed_at': firestore.SERVER_TIMESTAMP,
                'execution_time_seconds': execution_time,
                'output_data': result,
                'webhook_notified': False,  # Will be picked up by monitoring service
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"✅ Job {payload.job_id} completed in {execution_time:.1f}s")
            
            return {
                "status": "completed",
                "job_id": payload.job_id,
                "execution_time_seconds": execution_time,
                "message": "GPU job completed successfully"
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)
            
            logger.error(f"❌ Job {payload.job_id} failed after {execution_time:.1f}s: {error_msg}")
            
            # Update job status to failed
            try:
                job_ref.update({
                    'status': 'failed',
                    'error': error_msg,
                    'failed_at': firestore.SERVER_TIMESTAMP,
                    'execution_time_seconds': execution_time,
                    'webhook_notified': False,  # Will be picked up by monitoring service
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            except:
                pass  # Don't fail if we can't update status
            
            return {
                "status": "failed",
                "job_id": payload.job_id,
                "error": error_msg,
                "execution_time_seconds": execution_time
            }
    
    async def _execute_boltz2_job(
        self, 
        job_id: str, 
        user_id: str, 
        job_data: Dict[str, Any],
        auth_token: Optional[str]
    ) -> Dict[str, Any]:
        """Execute Boltz-2 job using the Cloud Run script"""
        
        try:
            # Extract input data
            input_data = job_data.get('input_data', {})
            protein_sequence = input_data.get('protein_sequence')
            ligand_smiles = input_data.get('ligand_smiles')
            ligand_name = input_data.get('ligand_name', f'ligand_{job_id[:8]}')
            
            if not protein_sequence or not ligand_smiles:
                raise ValueError("Missing required input data: protein_sequence or ligand_smiles")
            
            # Prepare environment for Boltz2CloudRunner
            env_vars = {
                'USER_ID': user_id,
                'JOB_ID': job_id,
                'INPUT_PATH': f'gs://{self.bucket_name}/users/{user_id}/jobs/{job_id}/input.json',
                'OUTPUT_PATH': f'gs://{self.bucket_name}/users/{user_id}/jobs/{job_id}/',
                'GPU_TYPE': 'L4',
                'GCP_PROJECT_ID': self.project_id,
                'GCS_BUCKET_NAME': self.bucket_name,
                'CLOUD_RUN_TASK_INDEX': '0',
                'CLOUD_RUN_TASK_COUNT': '1',
                'AUTH_TOKEN': auth_token or '',
                'ENVIRONMENT': os.getenv('ENVIRONMENT', 'production'),
                'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', 'omtx-hub-default-secret-key-change-in-production')
            }
            
            # Create input file in GCS
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            input_file_data = {
                'user_id': user_id,
                'job_id': job_id,
                'protein_sequence': protein_sequence,
                'ligands': [{
                    'name': ligand_name,
                    'smiles': ligand_smiles
                }],
                'created_at': datetime.utcnow().isoformat(),
                'gpu_type': 'L4'
            }
            
            input_blob = bucket.blob(f'users/{user_id}/jobs/{job_id}/input.json')
            input_blob.upload_from_string(
                json.dumps(input_file_data, indent=2),
                content_type='application/json'
            )
            
            logger.info(f"📤 Created input file for job {job_id}")
            
            # Execute Boltz2CloudRunner as subprocess
            python_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'boltz2_cloud_run.py')
            
            # Update environment with our variables
            subprocess_env = os.environ.copy()
            subprocess_env.update(env_vars)
            
            logger.info(f"🔧 Executing Boltz2CloudRunner for job {job_id}")
            
            result = subprocess.run(
                ['python', python_path],
                env=subprocess_env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Boltz2CloudRunner failed: {result.stderr}")
            
            logger.info(f"✅ Boltz2CloudRunner completed for job {job_id}")
            
            # Parse results from GCS
            try:
                # Check for results file
                results_blob = bucket.blob(f'users/{user_id}/jobs/{job_id}/task_0_results.json')
                if results_blob.exists():
                    results_data = json.loads(results_blob.download_as_text())
                    
                    # Get the first (and only) result for individual jobs
                    if results_data and len(results_data) > 0:
                        result_data = results_data[0]
                        return {
                            'status': 'completed',
                            'results': {
                                'ligand_name': result_data.get('ligand_name'),
                                'ligand_smiles': result_data.get('ligand_smiles'),
                                'binding_affinity': result_data.get('binding_affinity', 0.0),
                                'confidence_score': result_data.get('confidence_score', 0.0),
                                'execution_time_seconds': result_data.get('execution_time_seconds', 0),
                                'structure_available': bool(result_data.get('structure_base64'))
                            },
                            'files_stored_to_gcp': True,
                            'gcp_results_path': f'users/{user_id}/jobs/{job_id}/'
                        }
                
                # Fallback if no results file found
                return {
                    'status': 'completed',
                    'results': {'message': 'Job completed but results parsing failed'},
                    'files_stored_to_gcp': True,
                    'gcp_results_path': f'users/{user_id}/jobs/{job_id}/'
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse results for job {job_id}: {e}")
                return {
                    'status': 'completed',
                    'results': {'message': 'Job completed but results parsing failed'},
                    'files_stored_to_gcp': True,
                    'error': str(e)
                }
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Boltz-2 execution timeout (1 hour)")
        except Exception as e:
            logger.error(f"❌ Boltz-2 execution failed: {e}")
            raise

# FastAPI app for the GPU worker service
app = FastAPI(
    title="OMTX-Hub GPU Worker Service",
    description="Processes Cloud Tasks for GPU-accelerated protein predictions",
    version="1.0.0"
)

# Initialize service
gpu_service = GPUWorkerService()

@app.post("/process")
async def process_job(request: Request):
    """
    Process a GPU job from Cloud Tasks
    
    This endpoint receives job tasks from Cloud Tasks queue and executes them
    on GPU-enabled Cloud Run instances with user validation.
    """
    try:
        # Parse request body
        body = await request.body()
        task_data = json.loads(body.decode('utf-8'))
        
        # Validate payload
        payload = JobTaskPayload(**task_data)
        
        # Process the job
        result = await gpu_service.process_job_task(payload)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to process job task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "service": "gpu-worker",
        "timestamp": datetime.utcnow().isoformat(),
        "gpu_available": "L4",
        "message": "GPU Worker Service operational"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OMTX-Hub GPU Worker Service",
        "version": "1.0.0",
        "description": "Processes Cloud Tasks for GPU-accelerated protein predictions",
        "endpoints": ["/process", "/health"]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)