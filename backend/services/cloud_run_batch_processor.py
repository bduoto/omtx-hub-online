"""
Cloud Run Batch Processor - REPLACES ALL MODAL BATCH PROCESSING
Distinguished Engineer Implementation - This is CRITICAL for batch functionality
"""

import os
import json
import uuid
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.cloud import run_v2
from google.cloud import firestore
from google.cloud import storage

logger = logging.getLogger(__name__)

class CloudRunBatchProcessor:
    """Complete replacement for Modal batch processing - CRITICAL SERVICE"""
    
    def __init__(self):
        self.jobs_client = run_v2.JobsClient()
        self.db = firestore.Client()
        self.storage_client = storage.Client()
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.region = os.getenv("GCP_REGION", "us-central1")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "omtx-production")
        
        logger.info("🔄 CloudRunBatchProcessor initialized - Modal replacement active")
    
    async def submit_batch(
        self,
        user_id: str,
        batch_id: str,
        protein_sequence: str,
        ligands: List[Dict[str, Any]],
        job_name: str,
        use_msa: bool = True,
        use_potentials: bool = False
    ) -> Dict[str, Any]:
        """Submit batch to Cloud Run Jobs - REPLACES Modal spawn_map"""
        
        logger.info(f"🧬 Submitting batch {batch_id} for user {user_id}: {len(ligands)} ligands")
        
        try:
            # 1. Create batch parent in Firestore
            batch_ref = self.db.collection('users').document(user_id)\
                .collection('batches').document(batch_id)
            
            batch_doc = {
                'batch_id': batch_id,
                'job_name': job_name,
                'status': 'preparing',
                'total_ligands': len(ligands),
                'completed_ligands': 0,
                'failed_ligands': 0,
                'protein_sequence': protein_sequence,
                'created_at': firestore.SERVER_TIMESTAMP,
                'user_id': user_id,
                'processing_engine': 'cloud_run',
                'gpu_type': 'L4'
            }
            batch_ref.set(batch_doc)
            
            # 2. Upload batch input to GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            input_path = f"users/{user_id}/batches/{batch_id}/input.json"
            
            input_data = {
                'batch_id': batch_id,
                'user_id': user_id,
                'protein_sequence': protein_sequence,
                'ligands': ligands,
                'use_msa': use_msa,
                'use_potentials': use_potentials,
                'job_name': job_name,
                'created_at': datetime.utcnow().isoformat()
            }
            
            blob = bucket.blob(input_path)
            blob.upload_from_string(json.dumps(input_data, indent=2))
            blob.metadata = {
                'user_id': user_id,
                'batch_id': batch_id,
                'content_type': 'batch_input'
            }
            blob.patch()
            
            logger.info(f"📤 Uploaded batch input to gs://{self.bucket_name}/{input_path}")
            
            # 3. Calculate optimal task configuration for L4 GPU
            # L4 has 24GB VRAM, each ligand needs ~2GB for Boltz-2
            ligands_per_task = min(10, len(ligands))  # Max 10 ligands per task
            task_count = max(1, (len(ligands) + ligands_per_task - 1) // ligands_per_task)
            
            # 4. Submit to Cloud Run Job
            job_name_resource = f"projects/{self.project_id}/locations/{self.region}/jobs/boltz2-l4"
            
            request = run_v2.RunJobRequest(
                name=job_name_resource,
                overrides=run_v2.RunJobRequest.Overrides(
                    container_overrides=[
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=[
                                run_v2.EnvVar(name="USER_ID", value=user_id),
                                run_v2.EnvVar(name="BATCH_ID", value=batch_id),
                                run_v2.EnvVar(name="INPUT_PATH", value=f"gs://{self.bucket_name}/{input_path}"),
                                run_v2.EnvVar(name="OUTPUT_PATH", value=f"gs://{self.bucket_name}/users/{user_id}/batches/{batch_id}/"),
                                run_v2.EnvVar(name="LIGANDS_PER_TASK", value=str(ligands_per_task)),
                                run_v2.EnvVar(name="PROCESSING_MODE", value="batch"),
                                run_v2.EnvVar(name="GPU_TYPE", value="L4"),
                                run_v2.EnvVar(name="GCP_PROJECT_ID", value=self.project_id),
                                run_v2.EnvVar(name="GCS_BUCKET_NAME", value=self.bucket_name)
                            ]
                        )
                    ],
                    task_count=task_count,
                    parallelism=min(task_count, 5),  # Conservative parallelism for cost control
                    task_timeout="1800s"  # 30 minutes per task
                )
            )
            
            operation = self.jobs_client.run_job(request=request)
            
            logger.info(f"🚀 Cloud Run Job submitted: {operation.name} ({task_count} tasks)")
            
            # 5. Update batch status
            batch_ref.update({
                'status': 'running',
                'cloud_run_execution': operation.name,
                'task_count': task_count,
                'ligands_per_task': ligands_per_task,
                'started_at': firestore.SERVER_TIMESTAMP
            })
            
            # 6. Create child jobs for tracking individual ligands
            child_job_ids = []
            for i, ligand in enumerate(ligands):
                child_job_id = str(uuid.uuid4())
                child_ref = self.db.collection('users').document(user_id)\
                    .collection('jobs').document(child_job_id)
                
                child_ref.set({
                    'id': child_job_id,
                    'batch_id': batch_id,
                    'batch_parent_id': batch_id,
                    'job_type': 'BATCH_CHILD',
                    'ligand_index': i,
                    'ligand_name': ligand.get('name', f'Ligand_{i+1}'),
                    'ligand_smiles': ligand.get('smiles', ''),
                    'status': 'pending',
                    'protein_sequence': protein_sequence,
                    'task_assignment': i // ligands_per_task,  # Which Cloud Run task will process this
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'processing_engine': 'cloud_run',
                    'gpu_type': 'L4'
                })
                
                child_job_ids.append(child_job_id)
            
            batch_ref.update({'child_job_ids': child_job_ids})
            
            # 7. Create admin tracking record
            admin_batch_ref = self.db.collection('admin_batches').document(batch_id)
            admin_batch_ref.set({
                'batch_id': batch_id,
                'user_id': user_id,
                'job_name': job_name,
                'total_ligands': len(ligands),
                'task_count': task_count,
                'status': 'running',
                'cloud_run_execution': operation.name,
                'estimated_cost_usd': self._estimate_batch_cost(len(ligands), task_count),
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            result = {
                'batch_id': batch_id,
                'status': 'running',
                'task_count': task_count,
                'total_ligands': len(ligands),
                'ligands_per_task': ligands_per_task,
                'execution_name': operation.name,
                'estimated_cost_usd': self._estimate_batch_cost(len(ligands), task_count),
                'estimated_completion_minutes': task_count * 3  # 3 minutes per task average
            }
            
            logger.info(f"✅ Batch {batch_id} submitted successfully: {task_count} tasks processing {len(ligands)} ligands")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Batch submission failed for {batch_id}: {str(e)}")
            
            # Update batch status to failed
            try:
                batch_ref.update({
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': firestore.SERVER_TIMESTAMP
                })
            except:
                pass
            
            raise Exception(f"Batch submission failed: {str(e)}")
    
    def _estimate_batch_cost(self, ligand_count: int, task_count: int) -> float:
        """Estimate batch processing cost for L4 GPU"""
        
        # L4 GPU cost: $0.65/hour
        # Average processing time: 3 minutes per task
        # Each task processes multiple ligands in parallel
        
        l4_cost_per_hour = 0.65
        average_minutes_per_task = 3
        
        total_gpu_hours = (task_count * average_minutes_per_task) / 60
        estimated_cost = total_gpu_hours * l4_cost_per_hour
        
        return round(estimated_cost, 4)
    
    async def get_batch_status(self, user_id: str, batch_id: str) -> Dict[str, Any]:
        """Get comprehensive batch status"""
        
        try:
            # Get batch document
            batch_ref = self.db.collection('users').document(user_id)\
                .collection('batches').document(batch_id)
            batch_doc = batch_ref.get()
            
            if not batch_doc.exists:
                return {"error": "Batch not found"}
            
            batch_data = batch_doc.to_dict()
            
            # Get child jobs
            child_jobs = []
            jobs_ref = self.db.collection('users').document(user_id)\
                .collection('jobs')\
                .where('batch_id', '==', batch_id)
            
            for job_doc in jobs_ref.stream():
                child_jobs.append(job_doc.to_dict())
            
            # Calculate progress
            completed_jobs = [job for job in child_jobs if job.get('status') == 'completed']
            failed_jobs = [job for job in child_jobs if job.get('status') == 'failed']
            
            progress_percent = 0
            if batch_data.get('total_ligands', 0) > 0:
                progress_percent = (len(completed_jobs) / batch_data['total_ligands']) * 100
            
            return {
                'batch_id': batch_id,
                'status': batch_data.get('status', 'unknown'),
                'total_ligands': batch_data.get('total_ligands', 0),
                'completed_ligands': len(completed_jobs),
                'failed_ligands': len(failed_jobs),
                'progress_percent': round(progress_percent, 1),
                'task_count': batch_data.get('task_count', 0),
                'cloud_run_execution': batch_data.get('cloud_run_execution'),
                'created_at': batch_data.get('created_at'),
                'started_at': batch_data.get('started_at'),
                'estimated_cost_usd': batch_data.get('estimated_cost_usd', 0),
                'child_jobs': child_jobs[:10]  # Return first 10 for preview
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch status for {batch_id}: {str(e)}")
            return {"error": str(e)}
    
    async def cancel_batch(self, user_id: str, batch_id: str) -> bool:
        """Cancel running batch"""
        
        try:
            # Update batch status
            batch_ref = self.db.collection('users').document(user_id)\
                .collection('batches').document(batch_id)
            
            batch_doc = batch_ref.get()
            if not batch_doc.exists:
                return False
            
            batch_data = batch_doc.to_dict()
            
            # Cancel Cloud Run execution if possible
            execution_name = batch_data.get('cloud_run_execution')
            if execution_name:
                try:
                    # Note: Cloud Run Jobs don't have a direct cancel API
                    # The jobs will complete but we mark them as cancelled in Firestore
                    logger.info(f"⚠️ Cloud Run Job {execution_name} cannot be cancelled directly")
                except Exception as e:
                    logger.warning(f"⚠️ Could not cancel Cloud Run execution: {str(e)}")
            
            # Update batch and child jobs status
            batch_ref.update({
                'status': 'cancelled',
                'cancelled_at': firestore.SERVER_TIMESTAMP
            })
            
            # Update child jobs
            jobs_ref = self.db.collection('users').document(user_id)\
                .collection('jobs')\
                .where('batch_id', '==', batch_id)
            
            for job_doc in jobs_ref.stream():
                if job_doc.to_dict().get('status') in ['pending', 'running']:
                    job_doc.reference.update({
                        'status': 'cancelled',
                        'cancelled_at': firestore.SERVER_TIMESTAMP
                    })
            
            logger.info(f"✅ Batch {batch_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel batch {batch_id}: {str(e)}")
            return False
    
    async def get_batch_results(self, user_id: str, batch_id: str) -> Dict[str, Any]:
        """Get batch results from GCS"""
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            results_prefix = f"users/{user_id}/batches/{batch_id}/results/"
            
            results = []
            blobs = bucket.list_blobs(prefix=results_prefix)
            
            for blob in blobs:
                if blob.name.endswith('.json'):
                    try:
                        content = blob.download_as_text()
                        result_data = json.loads(content)
                        results.append(result_data)
                    except Exception as e:
                        logger.warning(f"⚠️ Could not parse result file {blob.name}: {str(e)}")
            
            return {
                'batch_id': batch_id,
                'results_count': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get batch results for {batch_id}: {str(e)}")
            return {"error": str(e)}

# Global instance to replace modal_batch_executor
cloud_run_batch_processor = CloudRunBatchProcessor()
