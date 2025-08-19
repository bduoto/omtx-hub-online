"""
Cloud Run Service - Enterprise-grade Modal replacement
Distinguished Engineer Implementation with L4 optimization and observability
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from google.cloud import run_v2
from google.cloud import storage
from google.cloud import firestore
from google.cloud import monitoring_v3
import aiohttp
import backoff

from services.l4_optimization_engine import l4_batch_processor, L4OptimizationConfig
from database.gcp_storage_service import gcp_storage_service

logger = logging.getLogger(__name__)

@dataclass
class CloudRunExecution:
    """Structured execution metadata"""
    execution_id: str
    job_name: str
    status: str
    created_at: float
    gpu_type: str
    estimated_cost_usd: float
    shards_count: int
    total_ligands: int
    
    # Performance metrics
    execution_time_seconds: Optional[float] = None
    memory_peak_gb: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0

class CloudRunService:
    """Enterprise Cloud Run service with L4 optimization and comprehensive observability"""
    
    def __init__(self):
        # GCP clients
        self.jobs_client = run_v2.JobsClient()
        self.services_client = run_v2.ServicesClient()
        self.storage_client = storage.Client()
        self.firestore_client = firestore.Client()
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        
        # Configuration
        self.project_id = self._get_project_id()
        self.region = self._get_region()
        self.bucket_name = self._get_bucket_name()
        
        # Service URLs
        self.sync_service_url = f"https://boltz2-service-{self.project_id}.{self.region}.run.app"
        self.batch_job_name = f"projects/{self.project_id}/locations/{self.region}/jobs/boltz2-batch"
        
        # Performance tracking
        self.execution_metrics: Dict[str, CloudRunExecution] = {}
        
        logger.info(f"🚀 CloudRunService initialized for project {self.project_id} in {self.region}")
    
    def _get_project_id(self) -> str:
        """Get GCP project ID with fallback"""
        import os
        return os.getenv("GCP_PROJECT_ID", "om-models")
    
    def _get_region(self) -> str:
        """Get GCP region with fallback"""
        import os
        return os.getenv("GCP_REGION", "us-central1")
    
    def _get_bucket_name(self) -> str:
        """Get GCS bucket name with fallback"""
        import os
        return os.getenv("GCS_BUCKET_NAME", "hub-job-files")
    
    async def execute_batch_job(
        self,
        user_id: str,
        job_id: str,
        protein_sequence: str,
        ligands: List[str],
        job_name: str
    ) -> CloudRunExecution:
        """Execute batch job on Cloud Run with L4 optimization and user isolation"""

        start_time = time.time()
        execution_id = str(uuid.uuid4())

        logger.info(f"🧬 Executing batch job: {job_name} for user {user_id} ({len(ligands)} ligands, {len(protein_sequence)}aa protein)")

        try:
            # 1. Upload input data to user-scoped GCS path
            input_path = await self._upload_user_batch_input(user_id, job_id, protein_sequence, ligands)

            # 2. Calculate optimal task configuration for L4
            task_count = min(len(ligands), 10)  # Max 10 parallel tasks for cost control
            ligands_per_task = max(1, len(ligands) // task_count)

            # 3. Create execution metadata
            execution = CloudRunExecution(
                execution_id=execution_id,
                job_name=job_name,
                status="submitting",
                created_at=start_time,
                gpu_type="L4",
                estimated_cost_usd=self._estimate_batch_cost(len(ligands), len(protein_sequence)),
                shards_count=task_count,
                total_ligands=len(ligands)
            )

            # 4. Execute Cloud Run Job with user context
            operation = await self._execute_cloud_run_job_with_user_context(
                user_id, job_id, input_path, task_count
            )

            # 5. Update job status in Firestore
            await self._update_job_status_firestore(user_id, job_id, "running", {
                "cloud_run_execution": operation.name,
                "task_count": task_count,
                "estimated_cost": execution.estimated_cost_usd
            })

            # 6. Track execution
            execution.status = "running"
            self.execution_metrics[execution_id] = execution

            logger.info(f"✅ Batch job executing: {execution_id} (tasks: {task_count})")

            return execution
            
        except Exception as e:
            logger.error(f"❌ Failed to submit batch job {job_name}: {str(e)}")
            execution = CloudRunExecution(
                execution_id=execution_id,
                job_name=job_name,
                status="failed",
                created_at=start_time,
                gpu_type="L4",
                estimated_cost_usd=0.0,
                shards_count=0,
                total_ligands=len(ligands),
                error_message=str(e)
            )
            self.execution_metrics[execution_id] = execution
            raise
    
    async def predict_single(
        self, 
        protein_sequence: str, 
        ligand: str,
        timeout_seconds: int = 3600
    ) -> Dict[str, Any]:
        """Synchronous prediction via Cloud Run Service with comprehensive error handling"""
        
        start_time = time.time()
        
        logger.info(f"🔬 Single prediction: {len(protein_sequence)}aa protein x 1 ligand")
        
        # Estimate memory requirements
        memory_estimate = l4_batch_processor.memory_manager.estimate_memory_usage(
            len(protein_sequence), 1
        )
        
        if not memory_estimate["fits_in_l4"]:
            logger.warning(f"⚠️ Protein may exceed L4 memory: {memory_estimate['total_gb']:.1f}GB")
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout_seconds)
            ) as session:
                
                payload = {
                    "protein_sequence": protein_sequence,
                    "ligand": ligand,
                    "optimization_config": {
                        "use_fp16": True,
                        "gradient_checkpointing": memory_estimate["total_gb"] > 20,
                        "flash_attention": True
                    },
                    "memory_estimate": memory_estimate
                }
                
                async with session.post(
                    f"{self.sync_service_url}/predict",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        execution_time = time.time() - start_time
                        
                        # Add performance metadata
                        result["performance_metadata"] = {
                            "execution_time_seconds": execution_time,
                            "gpu_type": "L4",
                            "memory_estimate_gb": memory_estimate["total_gb"],
                            "optimization_applied": payload["optimization_config"]
                        }
                        
                        logger.info(f"✅ Single prediction completed in {execution_time:.1f}s")
                        return result
                    
                    else:
                        error_text = await response.text()
                        raise Exception(f"Cloud Run service error {response.status}: {error_text}")
                        
        except asyncio.TimeoutError:
            raise Exception(f"Prediction timeout after {timeout_seconds}s")
        except Exception as e:
            logger.error(f"❌ Single prediction failed: {str(e)}")
            raise
    
    async def _upload_user_batch_input(
        self,
        user_id: str,
        job_id: str,
        protein_sequence: str,
        ligands: List[str]
    ) -> str:
        """Upload batch input data to user-scoped GCS path"""

        # Prepare ligands with proper structure
        formatted_ligands = []
        for i, ligand in enumerate(ligands):
            if isinstance(ligand, str):
                formatted_ligands.append({
                    "name": f"ligand_{i}",
                    "smiles": ligand
                })
            else:
                formatted_ligands.append(ligand)

        input_data = {
            "user_id": user_id,
            "job_id": job_id,
            "protein_sequence": protein_sequence,
            "ligands": formatted_ligands,
            "created_at": time.time(),
            "gpu_type": "L4"
        }

        # Upload to user-scoped path
        input_path = f"users/{user_id}/jobs/{job_id}/input.json"
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(input_path)

        blob.upload_from_string(
            json.dumps(input_data, indent=2),
            content_type="application/json"
        )

        # Set user-specific metadata
        blob.metadata = {
            "user_id": user_id,
            "job_id": job_id,
            "uploaded_at": str(int(time.time()))
        }
        blob.patch()

        logger.info(f"📤 Uploaded batch input to gs://{self.bucket_name}/{input_path}")
        return f"gs://{self.bucket_name}/{input_path}"
    
    async def _execute_cloud_run_job_with_user_context(
        self,
        user_id: str,
        job_id: str,
        input_path: str,
        task_count: int
    ) -> Any:
        """Execute Cloud Run Job with user context and L4 optimization"""

        try:
            from google.cloud import run_v2

            # Create job execution request
            job_name = f"projects/{self.project_id}/locations/{self.region}/jobs/boltz2-l4"

            request = run_v2.RunJobRequest(
                name=job_name,
                overrides=run_v2.RunJobRequest.Overrides(
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=[
                                run_v2.EnvVar(name="USER_ID", value=user_id),
                                run_v2.EnvVar(name="JOB_ID", value=job_id),
                                run_v2.EnvVar(name="INPUT_PATH", value=input_path),
                                run_v2.EnvVar(name="OUTPUT_PATH", value=f"gs://{self.bucket_name}/users/{user_id}/jobs/{job_id}/"),
                                run_v2.EnvVar(name="GPU_TYPE", value="L4"),
                                run_v2.EnvVar(name="OPTIMIZATION_LEVEL", value="aggressive"),
                                run_v2.EnvVar(name="GCP_PROJECT_ID", value=self.project_id),
                                run_v2.EnvVar(name="GCS_BUCKET_NAME", value=self.bucket_name)
                            ]
                        )
                    ],
                    task_count=task_count,
                    parallelism=min(task_count, 5),  # Conservative parallelism for L4
                    task_timeout="3600s"  # 1 hour timeout
                )
            )

            # Execute job
            operation = self.jobs_client.run_job(request=request)

            logger.info(f"🚀 Cloud Run Job executing: {operation.name} (tasks: {task_count})")
            return operation

    async def _update_job_status_firestore(self, user_id: str, job_id: str, status: str, metadata: Dict[str, Any]):
        """Update job status in Firestore"""

        try:
            job_ref = self.db.collection('users').document(user_id)\
                .collection('jobs').document(job_id)

            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP,
                **metadata
            }

            job_ref.update(update_data)
            logger.debug(f"📝 Updated job {job_id} status to {status}")

        except Exception as e:
            logger.error(f"❌ Failed to update job status: {str(e)}")

    def _estimate_batch_cost(self, ligand_count: int, protein_length: int) -> float:
        """Estimate batch processing cost for L4 GPU"""

        # L4 cost: $0.65/hour
        # Estimate: ~30 seconds per ligand + protein length factor
        base_time_per_ligand = 30  # seconds
        protein_factor = max(1.0, protein_length / 500)  # Scale with protein size

        total_seconds = ligand_count * base_time_per_ligand * protein_factor
        total_hours = total_seconds / 3600

        l4_cost_per_hour = 0.65
        return total_hours * l4_cost_per_hour

        except Exception as e:
            logger.error(f"❌ Cloud Run Job execution failed: {str(e)}")
            raise
    
    async def _create_firestore_job_document(
        self, 
        execution: CloudRunExecution, 
        operation_name: str,
        shards: List[Dict[str, Any]]
    ):
        """Create comprehensive Firestore job document"""
        
        job_doc = {
            "execution_id": execution.execution_id,
            "job_name": execution.job_name,
            "status": execution.status,
            "created_at": firestore.SERVER_TIMESTAMP,
            
            # Cloud Run metadata
            "cloud_run_operation": operation_name,
            "cloud_run_region": self.region,
            "gpu_type": execution.gpu_type,
            
            # Performance estimates
            "estimated_cost_usd": execution.estimated_cost_usd,
            "shards_count": execution.shards_count,
            "total_ligands": execution.total_ligands,
            
            # Optimization metadata
            "optimization_config": asdict(L4OptimizationConfig()),
            "shards_metadata": [
                {
                    "expected_memory_gb": shard["expected_memory_gb"],
                    "strategy": shard["strategy"],
                    "ligands_count": len(shard["ligands"])
                }
                for shard in shards
            ]
        }
        
        self.firestore_client.collection('jobs').document(execution.execution_id).set(job_doc)
        logger.debug(f"📝 Created Firestore job document: {execution.execution_id}")
    
    def _estimate_shard_cost(self, shard: Dict[str, Any]) -> float:
        """Estimate cost for a single shard"""
        
        protein_length = len(shard["protein_sequence"])
        num_ligands = len(shard["ligands"])
        
        # L4 cost calculation
        l4_cost_per_hour = 0.65
        estimated_time_hours = l4_batch_processor._calculate_l4_processing_time(
            protein_length, num_ligands
        ) / 3600
        
        return estimated_time_hours * l4_cost_per_hour
    
    async def _emit_batch_submission_metrics(self, execution: CloudRunExecution):
        """Emit custom metrics for monitoring"""
        
        try:
            # Create custom metric for batch submissions
            series = monitoring_v3.TimeSeries()
            series.metric.type = "custom.googleapis.com/omtx_hub/batch_submissions"
            series.resource.type = "global"
            
            point = monitoring_v3.Point()
            point.value.int64_value = 1
            point.interval.end_time.seconds = int(time.time())
            series.points = [point]
            
            # Add labels
            series.metric.labels["gpu_type"] = execution.gpu_type
            series.metric.labels["shards_count"] = str(execution.shards_count)
            series.metric.labels["estimated_cost"] = f"{execution.estimated_cost_usd:.3f}"
            
            project_name = f"projects/{self.project_id}"
            self.monitoring_client.create_time_series(
                name=project_name, 
                time_series=[series]
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to emit metrics: {str(e)}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[CloudRunExecution]:
        """Get execution status with real-time updates"""
        
        if execution_id in self.execution_metrics:
            execution = self.execution_metrics[execution_id]
            
            # Update status from Firestore
            try:
                doc = self.firestore_client.collection('jobs').document(execution_id).get()
                if doc.exists:
                    doc_data = doc.to_dict()
                    execution.status = doc_data.get("status", execution.status)
                    
                    # Update performance metrics if available
                    if "execution_time_seconds" in doc_data:
                        execution.execution_time_seconds = doc_data["execution_time_seconds"]
                    if "memory_peak_gb" in doc_data:
                        execution.memory_peak_gb = doc_data["memory_peak_gb"]
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to update execution status: {str(e)}")
            
            return execution
        
        return None

# Global Cloud Run service instance
cloud_run_service = CloudRunService()
