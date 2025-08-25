"""
Cloud Tasks Service for Queue-based GPU Processing
Manages job submission to Cloud Tasks for Cloud Run execution
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

from google.cloud import tasks_v2
from google.cloud import firestore
from google.protobuf import timestamp_pb2, duration_pb2
import google.auth

logger = logging.getLogger(__name__)

class CloudTasksService:
    """Service for managing Cloud Tasks queue for GPU processing"""
    
    def __init__(self):
        """Initialize Cloud Tasks client"""
        self.project_id = os.getenv("GCP_PROJECT_ID", "om-models")
        self.location = os.getenv("GCP_REGION", "us-central1")
        self.service_url = os.getenv("GPU_WORKER_URL", "https://boltz2-production-zhye5az7za-uc.a.run.app")
        
        # Queue names
        self.individual_queue = "boltz2-predictions"
        self.batch_queue = "boltz2-batch-predictions"
        
        # Initialize clients
        self.tasks_client = tasks_v2.CloudTasksClient()
        self.db = firestore.Client(project=self.project_id)
        
        # Get credentials for service account
        self.credentials, _ = google.auth.default()
        
        logger.info(f"✅ Cloud Tasks Service initialized")
        logger.info(f"   Project: {self.project_id}")
        logger.info(f"   Location: {self.location}")
        logger.info(f"   Service URL: {self.service_url}")
    
    def _get_queue_path(self, queue_name: str) -> str:
        """Get full queue path"""
        return self.tasks_client.queue_path(
            self.project_id,
            self.location,
            queue_name
        )
    
    def submit_prediction_task(
        self,
        job_id: str,
        protein_sequence: str,
        ligand_smiles: str,
        ligand_name: Optional[str] = None,
        user_id: Optional[str] = None,
        batch_parent_id: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Submit a prediction task to Cloud Tasks queue
        
        Args:
            job_id: Unique job identifier
            protein_sequence: Protein sequence for prediction
            ligand_smiles: Ligand SMILES string
            ligand_name: Optional ligand name
            user_id: Optional user identifier
            batch_parent_id: Optional parent batch ID
            priority: Task priority ('normal' or 'high')
            
        Returns:
            Task submission result
        """
        try:
            logger.info(f"📤 Submitting task to Cloud Tasks: {job_id}")
            
            # Choose queue based on priority
            queue_name = self.batch_queue if priority == "high" or batch_parent_id else self.individual_queue
            queue_path = self._get_queue_path(queue_name)
            
            # Create job record in Firestore first
            job_doc = {
                "job_id": job_id,
                "status": "queued",
                "job_type": "BATCH_CHILD" if batch_parent_id else "INDIVIDUAL",
                "batch_parent_id": batch_parent_id,
                "user_id": user_id or "anonymous",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "queue": queue_name,
                "input_data": {
                    "protein_sequence": protein_sequence,
                    "ligand_smiles": ligand_smiles,
                    "ligand_name": ligand_name or "unknown"
                }
            }
            
            # Store in Firestore
            self.db.collection("jobs").document(job_id).set(job_doc)
            logger.info(f"   ✅ Job record created in Firestore")
            
            # Create HTTP request body for Cloud Run
            payload = {
                "job_id": job_id,
                "protein_sequence": protein_sequence,
                "ligand_smiles": ligand_smiles,
                "ligand_name": ligand_name or "unknown",
                "user_id": user_id or "anonymous",
                "batch_parent_id": batch_parent_id or ""
            }
            
            # Create Cloud Tasks HTTP request
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{self.service_url}/predict",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Job-ID": job_id,
                        "X-User-ID": user_id or "anonymous"
                    },
                    "body": json.dumps(payload).encode()
                }
            }
            
            # Add OIDC token for authentication (uses default service account)
            if self.service_url.startswith("https://"):
                task["http_request"]["oidc_token"] = {
                    "service_account_email": f"boltz2-worker@{self.project_id}.iam.gserviceaccount.com"
                }
            
            # Set task dispatch deadline (5 minutes for processing)
            task["dispatch_deadline"] = duration_pb2.Duration(seconds=300)
            
            # Create the task
            request = tasks_v2.CreateTaskRequest(
                parent=queue_path,
                task=task
            )
            
            response = self.tasks_client.create_task(request=request)
            task_name = response.name
            
            logger.info(f"   ✅ Task created: {task_name}")
            
            # Update Firestore with task details
            self.db.collection("jobs").document(job_id).update({
                "task_name": task_name,
                "updated_at": datetime.utcnow()
            })
            
            return {
                "success": True,
                "job_id": job_id,
                "task_name": task_name,
                "queue": queue_name,
                "status": "queued",
                "message": "Task submitted to Cloud Tasks queue"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit task: {e}")
            
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
                "error": str(e)
            }
    
    def submit_batch_tasks(
        self,
        batch_id: str,
        protein_sequence: str,
        ligands: list,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit multiple prediction tasks as a batch
        
        Args:
            batch_id: Batch identifier
            protein_sequence: Protein sequence for all predictions
            ligands: List of ligand dictionaries
            user_id: Optional user identifier
            
        Returns:
            Batch submission results
        """
        try:
            logger.info(f"📦 Submitting batch of {len(ligands)} tasks to Cloud Tasks")
            
            # Create parent batch record
            batch_doc = {
                "batch_id": batch_id,
                "status": "processing",
                "total_jobs": len(ligands),
                "completed_jobs": 0,
                "failed_jobs": 0,
                "queued_jobs": 0,
                "user_id": user_id or "anonymous",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            self.db.collection("batches").document(batch_id).set(batch_doc)
            
            # Submit individual tasks
            task_names = []
            job_ids = []
            
            for i, ligand in enumerate(ligands):
                job_id = f"{batch_id}_{i+1}"
                
                result = self.submit_prediction_task(
                    job_id=job_id,
                    protein_sequence=protein_sequence,
                    ligand_smiles=ligand.get("smiles"),
                    ligand_name=ligand.get("name", f"ligand_{i+1}"),
                    user_id=user_id,
                    batch_parent_id=batch_id,
                    priority="high"  # Batch jobs get high priority
                )
                
                if result["success"]:
                    task_names.append(result["task_name"])
                    job_ids.append(job_id)
                else:
                    logger.error(f"Failed to submit task {job_id}: {result.get('error')}")
            
            # Update batch with task details
            self.db.collection("batches").document(batch_id).update({
                "job_ids": job_ids,
                "task_names": task_names,
                "queued_jobs": len(job_ids),
                "updated_at": datetime.utcnow()
            })
            
            return {
                "success": True,
                "batch_id": batch_id,
                "total_jobs": len(ligands),
                "submitted_jobs": len(job_ids),
                "task_names": task_names,
                "message": f"Batch submitted with {len(job_ids)} tasks to Cloud Tasks"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit batch: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_queue_stats(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a queue or all queues
        
        Args:
            queue_name: Optional specific queue name
            
        Returns:
            Queue statistics
        """
        try:
            stats = {}
            
            queues = [queue_name] if queue_name else [self.individual_queue, self.batch_queue]
            
            for q in queues:
                queue_path = self._get_queue_path(q)
                queue = self.tasks_client.get_queue(name=queue_path)
                
                stats[q] = {
                    "name": queue.name,
                    "state": queue.state.name,
                    "rate_limits": {
                        "max_dispatches_per_second": queue.rate_limits.max_dispatches_per_second,
                        "max_concurrent_dispatches": queue.rate_limits.max_concurrent_dispatches
                    },
                    "retry_config": {
                        "max_attempts": queue.retry_config.max_attempts,
                        "min_backoff": queue.retry_config.min_backoff.seconds,
                        "max_backoff": queue.retry_config.max_backoff.seconds
                    }
                }
            
            return {
                "success": True,
                "queues": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def pause_queue(self, queue_name: str) -> bool:
        """Pause a queue"""
        try:
            queue_path = self._get_queue_path(queue_name)
            queue = self.tasks_client.get_queue(name=queue_path)
            queue.state = tasks_v2.Queue.State.PAUSED
            
            update_mask = {"paths": ["state"]}
            self.tasks_client.update_queue(queue=queue, update_mask=update_mask)
            
            logger.info(f"✅ Queue {queue_name} paused")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause queue: {e}")
            return False
    
    def resume_queue(self, queue_name: str) -> bool:
        """Resume a paused queue"""
        try:
            queue_path = self._get_queue_path(queue_name)
            queue = self.tasks_client.get_queue(name=queue_path)
            queue.state = tasks_v2.Queue.State.RUNNING
            
            update_mask = {"paths": ["state"]}
            self.tasks_client.update_queue(queue=queue, update_mask=update_mask)
            
            logger.info(f"✅ Queue {queue_name} resumed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume queue: {e}")
            return False