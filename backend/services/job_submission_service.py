"""
Job Submission Service for GKE → Cloud Tasks → Cloud Run Jobs Pipeline
Handles both individual and batch Boltz-2 predictions with proper hierarchy
"""

import os
import json
import uuid
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import tasks_v2, firestore
from google.protobuf import timestamp_pb2, duration_pb2

logger = logging.getLogger(__name__)

class JobSubmissionService:
    """Orchestrates job submission from GKE API to Cloud Tasks for GPU processing"""
    
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'om-models')
        self.location = os.getenv('CLOUD_TASKS_LOCATION', 'us-central1')
        self.gpu_worker_url = os.getenv('GPU_WORKER_URL', 'https://gpu-worker-service-338254269321.us-central1.run.app')
        
        # Initialize clients
        self.tasks_client = tasks_v2.CloudTasksClient()
        self.db = firestore.Client(project=self.project_id)
        
        # Queue paths
        self.standard_queue = self.tasks_client.queue_path(
            self.project_id, self.location, 'gpu-job-queue'
        )
        self.priority_queue = self.tasks_client.queue_path(
            self.project_id, self.location, 'gpu-job-queue-high'
        )
        
        logger.info(f"✅ Job Submission Service initialized for project: {self.project_id}")
    
    async def submit_individual_job(
        self, 
        protein_sequence: str,
        ligand_smiles: str,
        ligand_name: Optional[str] = None,
        user_id: str = "anonymous",
        parameters: Optional[Dict[str, Any]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Submit an individual Boltz-2 prediction job
        
        Returns:
            Dict containing job_id and initial status
        """
        
        # Generate unique job ID
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        timestamp = firestore.SERVER_TIMESTAMP
        
        # Create job document structure
        job_data = {
            "job_id": job_id,
            "job_type": "INDIVIDUAL",
            "model": "boltz2",
            "status": "pending",
            "user_id": user_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            
            # Input data
            "input_data": {
                "protein_sequence": protein_sequence,
                "ligand_smiles": ligand_smiles,
                "ligand_name": ligand_name or f"Ligand_{job_id[:8]}",
                "parameters": parameters or {
                    "use_msa": True,
                    "num_samples": 5,
                    "confidence_threshold": 0.7
                }
            },
            
            # Tracking fields (will be updated by worker)
            "cloud_run_job": None,
            "results": None,
            "error": None,
            "started_at": None,
            "completed_at": None
        }
        
        try:
            # 1. Save job to Firestore
            job_ref = self.db.collection('jobs').document(job_id)
            job_ref.set(job_data)
            logger.info(f"📝 Created job record: {job_id}")
            
            # 2. Create Cloud Task
            task = self._create_task(
                job_id=job_id,
                job_type="INDIVIDUAL",
                priority=priority
            )
            
            # 3. Submit to appropriate queue
            queue = self.priority_queue if priority == "high" else self.standard_queue
            response = self.tasks_client.create_task(
                request={
                    "parent": queue,
                    "task": task
                }
            )
            
            logger.info(f"✅ Job {job_id} queued for GPU processing")
            
            # 4. Update job with task info
            job_ref.update({
                "cloud_task": {
                    "name": response.name,
                    "queue": queue,
                    "created_at": timestamp
                },
                "status": "queued"
            })
            
            return {
                "job_id": job_id,
                "status": "queued",
                "estimated_completion_time": self._estimate_completion_time(priority),
                "queue_position": self._get_queue_position(queue)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit job {job_id}: {e}")
            
            # Update job as failed
            if job_id:
                job_ref.update({
                    "status": "failed",
                    "error": str(e),
                    "updated_at": timestamp
                })
            
            raise Exception(f"Job submission failed: {e}")
    
    async def submit_batch_job(
        self,
        batch_name: str,
        protein_sequence: str,
        ligands: List[Dict[str, str]],
        user_id: str = "anonymous",
        parameters: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 10,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Submit a batch of Boltz-2 predictions
        
        Args:
            batch_name: Human-readable batch name
            protein_sequence: Target protein sequence
            ligands: List of dicts with 'name' and 'smiles' keys
            user_id: User identifier
            parameters: Model parameters
            max_concurrent: Max parallel GPU jobs
            priority: Job priority (normal/high)
        
        Returns:
            Dict containing batch_id and initial status
        """
        
        # Generate batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        timestamp = firestore.SERVER_TIMESTAMP
        
        # Create batch parent document
        batch_data = {
            "job_id": batch_id,
            "job_type": "BATCH_PARENT",
            "batch_name": batch_name,
            "model": "boltz2",
            "status": "pending",
            "user_id": user_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            
            # Batch configuration
            "batch_config": {
                "total_ligands": len(ligands),
                "max_concurrent": max_concurrent,
                "priority": priority,
                "protein_sequence": protein_sequence,
                "parameters": parameters or {}
            },
            
            # Progress tracking
            "progress": {
                "total": len(ligands),
                "completed": 0,
                "failed": 0,
                "running": 0,
                "pending": len(ligands),
                "queued": 0
            },
            
            # Results placeholder
            "batch_results": None,
            "child_job_ids": []
        }
        
        try:
            # 1. Create batch parent in Firestore
            batch_ref = self.db.collection('jobs').document(batch_id)
            batch_ref.set(batch_data)
            logger.info(f"📦 Created batch parent: {batch_id} with {len(ligands)} ligands")
            
            # 2. Create child jobs
            child_job_ids = []
            batch_write = self.db.batch()
            
            for idx, ligand in enumerate(ligands):
                child_id = f"{batch_id}_{idx:04d}"
                
                child_data = {
                    "job_id": child_id,
                    "job_type": "BATCH_CHILD",
                    "batch_parent_id": batch_id,
                    "batch_index": idx,
                    "model": "boltz2",
                    "status": "pending",
                    "user_id": user_id,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    
                    "input_data": {
                        "protein_sequence": protein_sequence,
                        "ligand_smiles": ligand["smiles"],
                        "ligand_name": ligand.get("name", f"Ligand_{idx+1}"),
                        "parameters": parameters or {}
                    },
                    
                    "cloud_run_job": None,
                    "results": None,
                    "error": None
                }
                
                batch_write.set(
                    self.db.collection('jobs').document(child_id),
                    child_data
                )
                child_job_ids.append(child_id)
            
            # Commit all child jobs
            batch_write.commit()
            logger.info(f"✅ Created {len(child_job_ids)} child jobs for batch {batch_id}")
            
            # 3. Update parent with child IDs
            batch_ref.update({"child_job_ids": child_job_ids})
            
            # 4. Queue initial jobs (respecting max_concurrent)
            queued_count = 0
            queue = self.priority_queue if priority == "high" else self.standard_queue
            
            for i, child_id in enumerate(child_job_ids[:max_concurrent]):
                # Stagger job submission by 2 seconds to avoid overwhelming GPU
                task = self._create_task(
                    job_id=child_id,
                    job_type="BATCH_CHILD",
                    batch_id=batch_id,
                    priority=priority,
                    delay_seconds=i * 2
                )
                
                response = self.tasks_client.create_task(
                    request={
                        "parent": queue,
                        "task": task
                    }
                )
                
                # Update child job status
                self.db.collection('jobs').document(child_id).update({
                    "status": "queued",
                    "cloud_task": {
                        "name": response.name,
                        "queue": queue
                    }
                })
                
                queued_count += 1
            
            # Update batch progress
            batch_ref.update({
                "progress.queued": queued_count,
                "progress.pending": len(ligands) - queued_count,
                "status": "running"
            })
            
            logger.info(f"🚀 Queued {queued_count} initial jobs for batch {batch_id}")
            
            return {
                "batch_id": batch_id,
                "status": "running",
                "total_ligands": len(ligands),
                "queued_jobs": queued_count,
                "estimated_completion_time": self._estimate_batch_completion(
                    len(ligands), max_concurrent, priority
                )
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to submit batch {batch_id}: {e}")
            
            # Update batch as failed
            if batch_id:
                batch_ref.update({
                    "status": "failed",
                    "error": str(e),
                    "updated_at": timestamp
                })
            
            raise Exception(f"Batch submission failed: {e}")
    
    def _create_task(
        self,
        job_id: str,
        job_type: str,
        batch_id: Optional[str] = None,
        priority: str = "normal",
        delay_seconds: int = 0
    ) -> Dict[str, Any]:
        """Create a Cloud Task for GPU processing"""
        
        # Task payload
        payload = {
            "job_id": job_id,
            "job_type": job_type,
            "batch_id": batch_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Create HTTP request
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{self.gpu_worker_url}/process",
                "headers": {
                    "Content-Type": "application/json",
                    "X-CloudTasks-QueueName": "gpu-job-queue",
                    "X-CloudTasks-TaskRetryCount": "0"
                },
                "body": json.dumps(payload).encode()
            }
        }
        
        # Add delay if specified
        if delay_seconds > 0:
            scheduled_time = timestamp_pb2.Timestamp()
            scheduled_time.FromDatetime(
                datetime.utcnow() + timedelta(seconds=delay_seconds)
            )
            task["schedule_time"] = scheduled_time
        
        # Set task deadline (30 minutes for GPU jobs)
        task["dispatch_deadline"] = duration_pb2.Duration(seconds=1800)
        
        return task
    
    def _estimate_completion_time(self, priority: str) -> str:
        """Estimate completion time for individual job"""
        
        # Base estimation: 3-5 minutes per job
        if priority == "high":
            minutes = 3
        else:
            minutes = 5
        
        completion_time = datetime.utcnow() + timedelta(minutes=minutes)
        return completion_time.isoformat()
    
    def _estimate_batch_completion(
        self, 
        total_ligands: int, 
        max_concurrent: int,
        priority: str
    ) -> str:
        """Estimate completion time for batch job"""
        
        # Calculate batches needed
        batches = (total_ligands + max_concurrent - 1) // max_concurrent
        
        # Estimate time per batch (5 minutes)
        minutes_per_batch = 3 if priority == "high" else 5
        total_minutes = batches * minutes_per_batch
        
        completion_time = datetime.utcnow() + timedelta(minutes=total_minutes)
        return completion_time.isoformat()
    
    def _get_queue_position(self, queue_path: str) -> int:
        """Get approximate position in queue"""
        
        try:
            # Get queue stats
            queue = self.tasks_client.get_queue(request={"name": queue_path})
            
            # This is approximate - Cloud Tasks doesn't provide exact position
            stats = queue.stats
            if stats:
                return stats.tasks_count
            return 0
            
        except Exception:
            return 0
    
    async def queue_next_batch_jobs(self, batch_id: str, count: int = 5):
        """Queue next set of jobs for a batch"""
        
        # Get pending child jobs
        pending_jobs = self.db.collection('jobs').where(
            'batch_parent_id', '==', batch_id
        ).where(
            'status', '==', 'pending'
        ).limit(count).stream()
        
        queued = 0
        for job_doc in pending_jobs:
            job_data = job_doc.to_dict()
            job_id = job_data['job_id']
            
            # Create and submit task
            task = self._create_task(
                job_id=job_id,
                job_type="BATCH_CHILD",
                batch_id=batch_id,
                delay_seconds=queued * 2  # Stagger by 2 seconds
            )
            
            queue = self.standard_queue  # Use standard queue for batch continuation
            response = self.tasks_client.create_task(
                request={
                    "parent": queue,
                    "task": task
                }
            )
            
            # Update job status
            self.db.collection('jobs').document(job_id).update({
                "status": "queued",
                "cloud_task": {
                    "name": response.name,
                    "queue": queue
                }
            })
            
            queued += 1
        
        if queued > 0:
            logger.info(f"✅ Queued {queued} additional jobs for batch {batch_id}")
            
            # Update batch progress
            batch_ref = self.db.collection('jobs').document(batch_id)
            batch_ref.update({
                "progress.queued": firestore.Increment(queued),
                "progress.pending": firestore.Increment(-queued),
                "updated_at": firestore.SERVER_TIMESTAMP
            })

# Create singleton instance
job_submission_service = JobSubmissionService()