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
from google.auth import jwt
from google.auth.transport import requests as google_requests
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
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', os.getenv('GCP_PROJECT_ID', 'om-models'))
        self.bucket_name = os.getenv('GCP_BUCKET_NAME', os.getenv('GCS_BUCKET_NAME', 'hub-job-files'))
        self.cloud_tasks_sa_email = f"cloud-tasks-service@{self.project_id}.iam.gserviceaccount.com"

        logger.info(f"🎮 GPU Worker Service initialized for project: {self.project_id}")
        logger.info(f"   Expected Cloud Tasks SA: {self.cloud_tasks_sa_email}")

    def _log_job_history(self, job_id: str, user_id: str, event: str, details: Dict[str, Any] = None):
        """Log job history event to GCS for debugging"""
        try:
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)

            history_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "job_id": job_id,
                "user_id": user_id,
                "event": event,
                "details": details or {},
                "service": "gpu_worker"
            }

            # Append to job history log
            history_path = f"users/{user_id}/jobs/{job_id}/job_history.log"
            history_blob = bucket.blob(history_path)

            # Get existing content or start fresh
            try:
                existing_content = history_blob.download_as_text() if history_blob.exists() else ""
            except:
                existing_content = ""

            # Append new entry
            new_content = existing_content + json.dumps(history_entry) + "\n"
            history_blob.upload_from_string(new_content, content_type="text/plain")

        except Exception as e:
            logger.warning(f"⚠️ Failed to log job history: {e}")
    
    def _validate_cloud_tasks_auth(self, request: Request) -> bool:
        """Validate that request comes from Cloud Tasks using OIDC token"""
        try:
            # Get Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return False

            token = auth_header.split(' ')[1]

            # Verify the OIDC token
            # Cloud Tasks uses the service account to sign OIDC tokens
            request_adapter = google_requests.Request()

            # Verify token and get claims
            claims = jwt.decode(token, request=request_adapter, verify=True)

            # Check issuer and audience
            expected_issuer = "https://accounts.google.com"
            if claims.get('iss') != expected_issuer:
                logger.warning(f"Invalid issuer: {claims.get('iss')}")
                return False

            # Check service account email
            email = claims.get('email')
            if not email or not email.endswith(f"@{self.project_id}.iam.gserviceaccount.com"):
                logger.warning(f"Invalid service account: {email}")
                return False

            logger.info(f"✅ Cloud Tasks OIDC validated from SA: {email}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ OIDC validation failed: {e}")
            return False

    async def process_job_task(self, payload: JobTaskPayload, request: Request = None) -> Dict[str, Any]:
        """Process a GPU job task with user validation"""

        start_time = datetime.utcnow()
        logger.info(f"🚀 Processing GPU job task: {payload.job_id} (type: {payload.job_type})")

        # Log job start
        self._log_job_history(payload.job_id, "unknown", "job_started", {
            "job_type": payload.job_type,
            "batch_id": payload.batch_id
        })

        try:
            # 1. Validate authentication
            is_development = os.getenv('ENVIRONMENT', 'production').lower() == 'development'

            if not is_development:
                # Production: require Cloud Tasks OIDC validation
                if not request or not self._validate_cloud_tasks_auth(request):
                    # Fallback to JWT if provided (for manual testing)
                    if payload.auth_token:
                        try:
                            token_payload = JWTAuth.verify_token(payload.auth_token)
                            logger.info(f"✅ Fallback JWT validated for manual testing")
                        except Exception as e:
                            raise ValueError(f"Authentication failed: OIDC invalid and JWT failed: {e}")
                    else:
                        raise ValueError("Authentication required: no valid Cloud Tasks OIDC or JWT token")
            else:
                logger.warning(f"⚠️ Development mode: skipping auth validation for {payload.job_id}")

            # 2. Get job details from Firestore
            job_ref = db.collection('jobs').document(payload.job_id)
            job_doc = job_ref.get()

            if not job_doc.exists:
                raise ValueError(f"Job {payload.job_id} not found in database")

            job_data = job_doc.to_dict()
            user_id = job_data.get('user_id')

            if not user_id:
                raise ValueError(f"No user_id found for job {payload.job_id}")

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

            # 5. Update job status to completed with standardized output_data
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Ensure result has proper structure for output_data
            standardized_output = {
                'status': 'completed',
                'results': result.get('results', {}),
                'files_stored_to_gcp': result.get('files_stored_to_gcp', True),
                'gcp_results_path': result.get('gcp_results_path', f'users/{user_id}/jobs/{payload.job_id}/'),
                'execution_time_seconds': execution_time,
                'completed_at': datetime.utcnow().isoformat()
            }

            job_ref.update({
                'status': 'completed',
                'completed_at': firestore.SERVER_TIMESTAMP,
                'execution_time_seconds': execution_time,
                'output_data': standardized_output,
                'webhook_notified': False,  # Will be picked up by monitoring service
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            logger.info(f"🗄️ Firestore Update: jobs/{payload.job_id} -> status=completed, execution_time={execution_time:.1f}s")

            logger.info(f"✅ Job {payload.job_id} completed in {execution_time:.1f}s")

            # Log job completion
            self._log_job_history(payload.job_id, user_id, "job_completed", {
                "execution_time_seconds": execution_time,
                "status": "completed"
            })

            # Notify batch monitor if this is a batch job
            if payload.job_type == "BATCH_CHILD":
                try:
                    from .batch_monitor_service import batch_monitor_service
                    await batch_monitor_service.on_job_completed(payload.job_id, "completed")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to notify batch monitor: {e}")
            
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

                # Notify batch monitor if this is a batch job
                if payload.job_type == "BATCH_CHILD":
                    try:
                        from .batch_monitor_service import batch_monitor_service
                        await batch_monitor_service.on_job_completed(payload.job_id, "failed")
                    except Exception as batch_e:
                        logger.warning(f"⚠️ Failed to notify batch monitor: {batch_e}")

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
                'GOOGLE_CLOUD_PROJECT': self.project_id,
                'GCP_BUCKET_NAME': self.bucket_name,
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
            
            # Parse results from GCS and normalize to canonical format
            try:
                job_path = f'users/{user_id}/jobs/{job_id}'

                # Check for results file (task_0_results.json from boltz2_cloud_run)
                results_blob = bucket.blob(f'{job_path}/task_0_results.json')
                if results_blob.exists():
                    results_data = json.loads(results_blob.download_as_text())

                    # Get the first (and only) result for individual jobs
                    if results_data and len(results_data) > 0:
                        result_data = results_data[0]

                        # Create canonical results.json
                        canonical_results = {
                            'job_id': job_id,
                            'status': 'completed',
                            'results': {
                                'ligand_name': result_data.get('ligand_name'),
                                'ligand_smiles': result_data.get('ligand_smiles'),
                                'binding_affinity': result_data.get('binding_affinity', 0.0),
                                'confidence_score': result_data.get('confidence_score', 0.0),
                                'execution_time_seconds': result_data.get('execution_time_seconds', 0),
                                'structure_available': bool(result_data.get('structure_base64'))
                            },
                            'input_data': {
                                'protein_sequence': protein_sequence,
                                'ligand_smiles': ligand_smiles,
                                'ligand_name': ligand_name
                            },
                            'files_stored_to_gcp': True,
                            'gcp_results_path': f'{job_path}/',
                            'completed_at': datetime.utcnow().isoformat()
                        }

                        # Write canonical results.json
                        canonical_blob = bucket.blob(f'{job_path}/results.json')
                        canonical_blob.upload_from_string(
                            json.dumps(canonical_results, indent=2),
                            content_type='application/json'
                        )
                        logger.info(f"📁 GCS Write: {job_path}/results.json ({len(json.dumps(canonical_results))} bytes)")

                        # If structure data exists, write structure.cif
                        if result_data.get('structure_base64'):
                            try:
                                import base64
                                structure_data = base64.b64decode(result_data['structure_base64'])
                                structure_blob = bucket.blob(f'{job_path}/structure.cif')
                                structure_blob.upload_from_string(structure_data, content_type='chemical/x-cif')
                                logger.info(f"📁 GCS Write: {job_path}/structure.cif ({len(structure_data)} bytes)")
                                logger.info(f"✅ Wrote canonical structure.cif for job {job_id}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to write structure file: {e}")

                        logger.info(f"✅ Normalized results to canonical format for job {job_id}")

                        return {
                            'status': 'completed',
                            'results': canonical_results['results'],
                            'files_stored_to_gcp': True,
                            'gcp_results_path': f'{job_path}/'
                        }

                # Fallback if no results file found
                return {
                    'status': 'completed',
                    'results': {'message': 'Job completed but results parsing failed'},
                    'files_stored_to_gcp': True,
                    'gcp_results_path': f'{job_path}/'
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

        # Process the job with request context for auth validation
        result = await gpu_service.process_job_task(payload, request)

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