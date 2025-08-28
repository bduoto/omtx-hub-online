"""
Cloud Run Job Service for Async GPU Processing
Triggers Cloud Run Jobs instead of calling HTTP endpoints
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from google.cloud import run_v2
from google.cloud import firestore
from google.api_core import retry
import google.auth

logger = logging.getLogger(__name__)

class CloudRunJobService:
    """Service for managing Cloud Run Jobs for GPU processing"""
    
    def __init__(self):
        """Initialize Cloud Run Job client"""
        self.project_id = os.getenv("GCP_PROJECT_ID", "om-models")
        self.region = os.getenv("GCP_REGION", "us-central1")
        self.job_name = os.getenv("CLOUD_RUN_JOB_NAME", "boltz2-job")
        
        # Initialize clients
        self.jobs_client = run_v2.JobsClient()
        self.executions_client = run_v2.ExecutionsClient()
        self.db = firestore.Client(project=self.project_id)
        
        # Get credentials
        self.credentials, _ = google.auth.default()
        
        # Job configuration
        self.job_parent = f"projects/{self.project_id}/locations/{self.region}"
        self.job_name_full = f"{self.job_parent}/jobs/{self.job_name}"
        
        logger.info(f"✅ Cloud Run Job Service initialized")
        logger.info(f"   Project: {self.project_id}")
        logger.info(f"   Region: {self.region}")
        logger.info(f"   Job: {self.job_name}")
    
    def submit_prediction_job(
        self,
        job_id: str,
        protein_sequence: str,
        ligand_smiles: str,
        ligand_name: Optional[str] = None,
        user_id: Optional[str] = None,
        batch_parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a prediction job to Cloud Run Jobs
        
        Args:
            job_id: Unique job identifier
            protein_sequence: Protein sequence for prediction
            ligand_smiles: Ligand SMILES string
            ligand_name: Optional ligand name
            user_id: Optional user identifier
            batch_parent_id: Optional parent batch ID
            
        Returns:
            Job submission result with execution details
        """
        try:
            logger.info(f"📤 Submitting Cloud Run Job: {job_id}")
            
            # Create job record in Firestore first
            job_doc = {
                "job_id": job_id,
                "status": "submitted",
                "job_type": "BATCH_CHILD" if batch_parent_id else "INDIVIDUAL",
                "batch_parent_id": batch_parent_id,
                "user_id": user_id or "anonymous",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "input_data": {
                    "protein_sequence": protein_sequence,
                    "ligand_smiles": ligand_smiles,
                    "ligand_name": ligand_name or "unknown"
                },
                "execution": {
                    "type": "cloud_run_job",
                    "job_name": self.job_name,
                    "region": self.region
                }
            }
            
            # Store in Firestore
            self.db.collection("jobs").document(job_id).set(job_doc)
            logger.info(f"   ✅ Job record created in Firestore")
            
            # Prepare environment variables for the job
            env_vars = [
                run_v2.EnvVar(name="JOB_ID", value=job_id),
                run_v2.EnvVar(name="PROTEIN_SEQUENCE", value=protein_sequence),
                run_v2.EnvVar(name="LIGAND_SMILES", value=ligand_smiles),
                run_v2.EnvVar(name="LIGAND_NAME", value=ligand_name or "unknown"),
                run_v2.EnvVar(name="FIRESTORE_PROJECT", value=self.project_id),
                run_v2.EnvVar(name="BATCH_PARENT_ID", value=batch_parent_id or ""),
            ]
            
            # Create execution request
            execution_template = run_v2.ExecutionTemplate(
                parallelism=1,
                task_count=1,
                template=run_v2.TaskTemplate(
                    containers=[
                        run_v2.Container(
                            env=env_vars
                        )
                    ]
                )
            )
            
            # Create the execution
            request = run_v2.RunJobRequest(
                name=self.job_name_full,
                overrides=execution_template
            )
            
            # Execute the job
            operation = self.jobs_client.run_job(request=request)
            logger.info(f"   ✅ Cloud Run Job execution started")
            
            # Get execution name from operation
            execution_name = operation.metadata.name if hasattr(operation, 'metadata') else None
            
            # Update Firestore with execution details
            self.db.collection("jobs").document(job_id).update({
                "status": "processing",
                "updated_at": datetime.utcnow(),
                "execution.execution_name": execution_name,
                "execution.started_at": datetime.utcnow()
            })
            
            return {
                "success": True,
                "job_id": job_id,
                "status": "processing",
                "execution_name": execution_name,
                "message": "Job submitted to Cloud Run Jobs for GPU processing",
                "estimated_time_seconds": 60
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit Cloud Run Job: {e}")
            
            # Update status to failed
            try:
                self.db.collection("jobs").document(job_id).update({
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.utcnow()
                })
            except:
                pass
            
            return {
                "success": False,
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a submitted job

        Args:
            job_id: Job identifier

        Returns:
            Job status and results if available
        """
        try:
            # Get job from Firestore
            job_doc = self.db.collection("jobs").document(job_id).get()

            if not job_doc.exists:
                return {
                    "success": False,
                    "error": "Job not found"
                }

            job_data = job_doc.to_dict()

            # Check if job has results - prioritize output_data.results over legacy results
            if job_data.get("status") == "completed":
                output_data = job_data.get("output_data", {})
                results = output_data.get("results", job_data.get("results", {}))

                return {
                    "success": True,
                    "job_id": job_id,
                    "status": "completed",
                    "results": results,
                    "completed_at": job_data.get("completed_at"),
                    "processing_time": job_data.get("processing_time_seconds") or job_data.get("execution_time_seconds"),
                    "files_stored_to_gcp": output_data.get("files_stored_to_gcp", False),
                    "gcp_results_path": output_data.get("gcp_results_path")
                }
            else:
                return {
                    "success": True,
                    "job_id": job_id,
                    "status": job_data.get("status"),
                    "message": "Job is still processing",
                    "created_at": job_data.get("created_at"),
                    "updated_at": job_data.get("updated_at")
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get job status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def submit_batch_jobs(
        self,
        batch_id: str,
        protein_sequence: str,
        ligands: list,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit multiple prediction jobs as a batch
        
        Args:
            batch_id: Batch identifier
            protein_sequence: Protein sequence for all predictions
            ligands: List of ligand dictionaries with 'smiles' and optional 'name'
            user_id: Optional user identifier
            
        Returns:
            Batch submission results
        """
        try:
            logger.info(f"📦 Submitting batch of {len(ligands)} jobs")
            
            # Create parent batch record
            batch_doc = {
                "batch_id": batch_id,
                "status": "processing",
                "total_jobs": len(ligands),
                "completed_jobs": 0,
                "failed_jobs": 0,
                "user_id": user_id or "anonymous",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            self.db.collection("batches").document(batch_id).set(batch_doc)
            
            # Submit individual jobs
            job_ids = []
            for i, ligand in enumerate(ligands):
                job_id = f"{batch_id}_{i+1}"
                
                result = self.submit_prediction_job(
                    job_id=job_id,
                    protein_sequence=protein_sequence,
                    ligand_smiles=ligand.get("smiles"),
                    ligand_name=ligand.get("name", f"ligand_{i+1}"),
                    user_id=user_id,
                    batch_parent_id=batch_id
                )
                
                if result["success"]:
                    job_ids.append(job_id)
                else:
                    logger.error(f"Failed to submit job {job_id}: {result.get('error')}")
            
            # Update batch with job IDs
            self.db.collection("batches").document(batch_id).update({
                "job_ids": job_ids,
                "updated_at": datetime.utcnow()
            })
            
            return {
                "success": True,
                "batch_id": batch_id,
                "total_jobs": len(ligands),
                "submitted_jobs": len(job_ids),
                "job_ids": job_ids,
                "message": f"Batch submitted with {len(job_ids)} jobs"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit batch: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_job_execution(self, execution_name: str) -> Dict[str, Any]:
        """
        Check the status of a Cloud Run Job execution
        
        Args:
            execution_name: Full execution resource name
            
        Returns:
            Execution status details
        """
        try:
            execution = self.executions_client.get_execution(name=execution_name)
            
            return {
                "name": execution.name,
                "status": execution.reconciling,
                "running_count": execution.running_count,
                "succeeded_count": execution.succeeded_count,
                "failed_count": execution.failed_count,
                "created_time": execution.create_time,
                "completion_time": execution.completion_time
            }
            
        except Exception as e:
            logger.error(f"Failed to check execution: {e}")
            return {"error": str(e)}