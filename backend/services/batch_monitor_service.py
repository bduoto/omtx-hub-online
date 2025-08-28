"""
Batch Monitor Service
Monitors batch job progress and manages batch orchestration
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from google.cloud import firestore
from google.cloud import storage

from .cloud_tasks_service import CloudTasksService

logger = logging.getLogger(__name__)

class BatchMonitorService:
    """Service to monitor and orchestrate batch job execution"""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT_ID", "om-models"))
        self.bucket_name = os.getenv("GCP_BUCKET_NAME", "hub-job-files")
        
        # Initialize clients
        self.db = firestore.Client(project=self.project_id)
        self.storage_client = storage.Client(project=self.project_id)
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.tasks_service = CloudTasksService()
        
        logger.info(f"✅ Batch Monitor Service initialized for project: {self.project_id}")
    
    async def on_job_completed(self, job_id: str, status: str) -> None:
        """Handle job completion and update batch progress"""
        try:
            # Get job document
            job_doc = self.db.collection("jobs").document(job_id).get()
            if not job_doc.exists:
                return
            
            job_data = job_doc.to_dict()
            batch_parent_id = job_data.get("batch_parent_id")
            
            if not batch_parent_id:
                return  # Not a batch job
            
            logger.info(f"📊 Updating batch progress for {batch_parent_id} (job {job_id} -> {status})")
            
            # Update batch counters
            batch_ref = self.db.collection("batches").document(batch_parent_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                logger.warning(f"⚠️ Batch {batch_parent_id} not found")
                return
            
            batch_data = batch_doc.to_dict()
            
            # Update counters atomically
            if status == "completed":
                batch_ref.update({
                    "completed_jobs": firestore.Increment(1),
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                logger.info(f"🗄️ Firestore Update: batches/{batch_parent_id} -> completed_jobs += 1")
            elif status == "failed":
                batch_ref.update({
                    "failed_jobs": firestore.Increment(1),
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                logger.info(f"🗄️ Firestore Update: batches/{batch_parent_id} -> failed_jobs += 1")
            
            # Check if we need to queue more jobs
            await self._manage_batch_concurrency(batch_parent_id, batch_data)
            
            # Check if batch is complete
            await self._check_batch_completion(batch_parent_id)
            
        except Exception as e:
            logger.error(f"❌ Failed to handle job completion for {job_id}: {e}")
    
    async def _manage_batch_concurrency(self, batch_id: str, batch_data: Dict[str, Any]) -> None:
        """Maintain max_concurrent by queuing pending jobs"""
        try:
            max_concurrent = batch_data.get("max_concurrent", 10)
            
            # Count currently running jobs
            running_jobs = self.db.collection("jobs").where(
                "batch_parent_id", "==", batch_id
            ).where(
                "status", "in", ["queued", "running"]
            ).stream()
            
            running_count = len(list(running_jobs))
            
            if running_count < max_concurrent:
                # Queue more pending jobs
                slots_available = max_concurrent - running_count
                
                pending_jobs = self.db.collection("jobs").where(
                    "batch_parent_id", "==", batch_id
                ).where(
                    "status", "==", "pending"
                ).limit(slots_available).stream()
                
                queued_count = 0
                for job_doc in pending_jobs:
                    job_data = job_doc.to_dict()
                    job_id = job_data["job_id"]
                    
                    # Submit to Cloud Tasks
                    result = self.tasks_service.submit_prediction_task(
                        job_id=job_id,
                        protein_sequence=job_data["input_data"]["protein_sequence"],
                        ligand_smiles=job_data["input_data"]["ligand_smiles"],
                        ligand_name=job_data["input_data"]["ligand_name"],
                        user_id=job_data["user_id"],
                        batch_parent_id=batch_id
                    )
                    
                    if result["success"]:
                        queued_count += 1
                        logger.info(f"✅ Queued continuation job {job_id} for batch {batch_id}")
                
                if queued_count > 0:
                    # Update batch counters
                    self.db.collection("batches").document(batch_id).update({
                        "queued_jobs": firestore.Increment(queued_count),
                        "updated_at": firestore.SERVER_TIMESTAMP
                    })
                    logger.info(f"🗄️ Firestore Update: batches/{batch_id} -> queued_jobs += {queued_count}")
                    logger.info(f"📈 Queued {queued_count} additional jobs for batch {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to manage batch concurrency for {batch_id}: {e}")
    
    async def _check_batch_completion(self, batch_id: str) -> None:
        """Check if batch is complete and finalize artifacts"""
        try:
            batch_ref = self.db.collection("batches").document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return
            
            batch_data = batch_doc.to_dict()
            total_jobs = batch_data.get("total_jobs", 0)
            completed_jobs = batch_data.get("completed_jobs", 0)
            failed_jobs = batch_data.get("failed_jobs", 0)
            
            if (completed_jobs + failed_jobs) >= total_jobs:
                # Batch is complete
                logger.info(f"🎉 Batch {batch_id} completed: {completed_jobs} success, {failed_jobs} failed")
                
                # Update batch status
                batch_ref.update({
                    "status": "completed",
                    "completed_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                })
                
                # Generate batch artifacts
                await self._generate_batch_artifacts(batch_id, batch_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to check batch completion for {batch_id}: {e}")
    
    async def _generate_batch_artifacts(self, batch_id: str, batch_data: Dict[str, Any]) -> None:
        """Generate aggregated batch results and export files"""
        try:
            user_id = batch_data.get("user_id", "anonymous")
            batch_path = f"users/{user_id}/batches/{batch_id}"
            
            # Get all child job results
            child_jobs = self.db.collection("jobs").where(
                "batch_parent_id", "==", batch_id
            ).stream()
            
            results = []
            for job_doc in child_jobs:
                job_data = job_doc.to_dict()
                output_data = job_data.get("output_data", {})
                job_results = output_data.get("results", {})
                
                if job_results:
                    results.append({
                        "job_id": job_data["job_id"],
                        "status": job_data["status"],
                        "ligand_name": job_results.get("ligand_name"),
                        "ligand_smiles": job_results.get("ligand_smiles"),
                        "binding_affinity": job_results.get("binding_affinity"),
                        "confidence_score": job_results.get("confidence_score"),
                        "execution_time_seconds": job_results.get("execution_time_seconds")
                    })
            
            # Create aggregated.json
            aggregated_data = {
                "batch_id": batch_id,
                "batch_name": batch_data.get("batch_name", f"Batch {batch_id[:8]}"),
                "user_id": user_id,
                "total_jobs": len(results),
                "completed_at": datetime.utcnow().isoformat(),
                "results": results,
                "summary": {
                    "avg_binding_affinity": sum(r.get("binding_affinity", 0) for r in results) / max(len(results), 1),
                    "avg_confidence": sum(r.get("confidence_score", 0) for r in results) / max(len(results), 1),
                    "total_execution_time": sum(r.get("execution_time_seconds", 0) for r in results)
                }
            }
            
            # Upload aggregated.json
            aggregated_blob = self.bucket.blob(f"{batch_path}/aggregated.json")
            aggregated_blob.upload_from_string(
                json.dumps(aggregated_data, indent=2),
                content_type="application/json"
            )
            logger.info(f"📁 GCS Write: {batch_path}/aggregated.json ({len(json.dumps(aggregated_data))} bytes)")

            # Create CSV export
            csv_lines = ["job_id,ligand_name,ligand_smiles,binding_affinity,confidence_score,execution_time"]
            for result in results:
                csv_lines.append(
                    f"{result['job_id']},{result.get('ligand_name', '')},"
                    f"{result.get('ligand_smiles', '')},{result.get('binding_affinity', 0)},"
                    f"{result.get('confidence_score', 0)},{result.get('execution_time_seconds', 0)}"
                )

            csv_content = "\n".join(csv_lines)
            csv_blob = self.bucket.blob(f"{batch_path}/batch_results.csv")
            csv_blob.upload_from_string(csv_content, content_type="text/csv")
            logger.info(f"📁 GCS Write: {batch_path}/batch_results.csv ({len(csv_content)} bytes)")
            
            logger.info(f"✅ Generated batch artifacts for {batch_id} at {batch_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate batch artifacts for {batch_id}: {e}")

# Global instance
batch_monitor_service = BatchMonitorService()
