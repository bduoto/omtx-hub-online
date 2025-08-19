"""
Eventarc Handler - Real-time event processing for Cloud Run
Distinguished Engineer Implementation - Event-driven architecture replacing Modal webhooks
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from google.cloud import firestore
from google.cloud import storage
from google.cloud import run_v2
from google.cloud import eventarc_v1
import cloudevents.http

from services.cloud_run_service import cloud_run_service
from database.unified_job_manager import unified_job_manager

logger = logging.getLogger(__name__)

@dataclass
class EventarcEvent:
    """Structured Eventarc event"""
    event_type: str
    source: str
    subject: str
    data: Dict[str, Any]
    timestamp: datetime
    
    # Firestore-specific fields
    document_name: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    value: Optional[Dict[str, Any]] = None

class EventarcHandler:
    """Enterprise-grade Eventarc event handler with comprehensive processing"""
    
    def __init__(self):
        self.firestore_client = firestore.Client()
        self.storage_client = storage.Client()
        self.run_client = run_v2.JobsClient()
        
        # Event processing metrics
        self.events_processed = 0
        self.events_failed = 0
        self.last_event_time = None
        
        logger.info("🎯 EventarcHandler initialized for real-time processing")
    
    async def handle_firestore_event(self, cloud_event: cloudevents.http.CloudEvent) -> Dict[str, Any]:
        """Handle Firestore document events (create, update, delete)"""
        
        try:
            # Parse cloud event
            event = self._parse_firestore_event(cloud_event)
            
            logger.info(f"📨 Firestore event: {event.event_type} on {event.document_name}")
            
            # Route based on document collection
            if "/batches/" in event.document_name:
                return await self._handle_batch_event(event)
            elif "/jobs/" in event.document_name:
                return await self._handle_job_event(event)
            else:
                logger.debug(f"🔄 Ignoring event for document: {event.document_name}")
                return {"status": "ignored", "reason": "not_relevant"}
                
        except Exception as e:
            self.events_failed += 1
            logger.error(f"❌ Failed to handle Firestore event: {str(e)}")
            raise
    
    async def handle_cloud_run_event(self, cloud_event: cloudevents.http.CloudEvent) -> Dict[str, Any]:
        """Handle Cloud Run job completion events"""
        
        try:
            event_data = cloud_event.data
            
            logger.info(f"🏃 Cloud Run event: {event_data.get('eventType')} for {event_data.get('jobName')}")
            
            # Handle job completion
            if event_data.get("eventType") == "google.cloud.run.job.v1.execution.succeeded":
                return await self._handle_job_completion(event_data)
            elif event_data.get("eventType") == "google.cloud.run.job.v1.execution.failed":
                return await self._handle_job_failure(event_data)
            else:
                return {"status": "ignored", "reason": "not_completion_event"}
                
        except Exception as e:
            self.events_failed += 1
            logger.error(f"❌ Failed to handle Cloud Run event: {str(e)}")
            raise
    
    def _parse_firestore_event(self, cloud_event: cloudevents.http.CloudEvent) -> EventarcEvent:
        """Parse Firestore cloud event into structured format"""
        
        event_data = cloud_event.data
        
        return EventarcEvent(
            event_type=cloud_event.get_type(),
            source=cloud_event.get_source(),
            subject=cloud_event.get_subject(),
            data=event_data,
            timestamp=datetime.fromisoformat(cloud_event.get_time().replace('Z', '+00:00')),
            document_name=event_data.get("documentName", ""),
            old_value=event_data.get("oldValue", {}),
            value=event_data.get("value", {})
        )
    
    async def _handle_batch_event(self, event: EventarcEvent) -> Dict[str, Any]:
        """Handle batch document events - trigger Cloud Run Jobs"""
        
        # Extract batch ID from document name
        # Format: projects/{project}/databases/{database}/documents/batches/{batch_id}
        batch_id = event.document_name.split("/")[-1]
        
        if event.event_type == "google.cloud.firestore.document.v1.created":
            # New batch created - trigger Cloud Run Job
            return await self._trigger_batch_processing(batch_id, event.value)
        
        elif event.event_type == "google.cloud.firestore.document.v1.updated":
            # Batch updated - check if status changed
            old_status = event.old_value.get("fields", {}).get("status", {}).get("stringValue", "")
            new_status = event.value.get("fields", {}).get("status", {}).get("stringValue", "")
            
            if old_status != new_status:
                logger.info(f"📊 Batch {batch_id} status changed: {old_status} → {new_status}")
                
                if new_status == "cancelled":
                    return await self._cancel_batch_processing(batch_id)
        
        return {"status": "processed", "batch_id": batch_id}
    
    async def _handle_job_event(self, event: EventarcEvent) -> Dict[str, Any]:
        """Handle individual job document events"""
        
        job_id = event.document_name.split("/")[-1]
        
        if event.event_type == "google.cloud.firestore.document.v1.updated":
            # Check for status changes that require action
            old_status = event.old_value.get("fields", {}).get("status", {}).get("stringValue", "")
            new_status = event.value.get("fields", {}).get("status", {}).get("stringValue", "")
            
            if new_status == "completed":
                # Job completed - trigger any post-processing
                return await self._handle_job_post_processing(job_id, event.value)
        
        return {"status": "processed", "job_id": job_id}
    
    async def _trigger_batch_processing(self, batch_id: str, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger Cloud Run Job for batch processing"""
        
        try:
            # Extract batch parameters from Firestore document
            fields = batch_data.get("fields", {})
            
            protein_sequence = fields.get("protein_sequence", {}).get("stringValue", "")
            ligands_array = fields.get("ligands", {}).get("arrayValue", {}).get("values", [])
            ligands = [item.get("stringValue", "") for item in ligands_array]
            job_name = fields.get("job_name", {}).get("stringValue", f"batch-{batch_id}")
            
            if not protein_sequence or not ligands:
                logger.warning(f"⚠️ Incomplete batch data for {batch_id}")
                return {"status": "error", "reason": "incomplete_data"}
            
            logger.info(f"🚀 Triggering batch processing: {batch_id} ({len(ligands)} ligands)")
            
            # Submit to Cloud Run
            execution = await cloud_run_service.submit_batch_job(
                protein_sequence=protein_sequence,
                ligands=ligands,
                job_name=job_name,
                user_id="eventarc"
            )
            
            # Update batch document with execution metadata
            self.firestore_client.collection('batches').document(batch_id).update({
                "cloud_run_execution_id": execution.execution_id,
                "status": "running",
                "started_at": firestore.SERVER_TIMESTAMP,
                "gpu_type": execution.gpu_type,
                "estimated_cost_usd": execution.estimated_cost_usd
            })
            
            logger.info(f"✅ Batch processing triggered: {batch_id} → {execution.execution_id}")
            
            return {
                "status": "triggered",
                "batch_id": batch_id,
                "execution_id": execution.execution_id,
                "shards_count": execution.shards_count
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to trigger batch processing for {batch_id}: {str(e)}")
            
            # Update batch status to failed
            self.firestore_client.collection('batches').document(batch_id).update({
                "status": "failed",
                "error": str(e),
                "failed_at": firestore.SERVER_TIMESTAMP
            })
            
            raise
    
    async def _handle_job_completion(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Cloud Run job completion"""
        
        job_name = event_data.get("jobName", "")
        execution_name = event_data.get("executionName", "")
        
        logger.info(f"🎉 Cloud Run job completed: {job_name}")
        
        try:
            # Find corresponding batch/job in Firestore
            batches_query = self.firestore_client.collection('batches').where(
                "cloud_run_operation", "==", execution_name
            ).limit(1)
            
            batch_docs = list(batches_query.stream())
            
            if batch_docs:
                batch_doc = batch_docs[0]
                batch_id = batch_doc.id
                
                # Process completion
                await self._process_batch_completion(batch_id, event_data)
                
                return {
                    "status": "completed",
                    "batch_id": batch_id,
                    "execution_name": execution_name
                }
            else:
                logger.warning(f"⚠️ No batch found for execution: {execution_name}")
                return {"status": "orphaned", "execution_name": execution_name}
                
        except Exception as e:
            logger.error(f"❌ Failed to handle job completion: {str(e)}")
            raise
    
    async def _handle_job_failure(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Cloud Run job failure"""
        
        job_name = event_data.get("jobName", "")
        execution_name = event_data.get("executionName", "")
        error_message = event_data.get("errorMessage", "Unknown error")
        
        logger.error(f"💥 Cloud Run job failed: {job_name} - {error_message}")
        
        try:
            # Find and update corresponding batch
            batches_query = self.firestore_client.collection('batches').where(
                "cloud_run_operation", "==", execution_name
            ).limit(1)
            
            batch_docs = list(batches_query.stream())
            
            if batch_docs:
                batch_doc = batch_docs[0]
                batch_id = batch_doc.id
                
                # Update batch status to failed
                self.firestore_client.collection('batches').document(batch_id).update({
                    "status": "failed",
                    "error": error_message,
                    "failed_at": firestore.SERVER_TIMESTAMP
                })
                
                logger.info(f"📝 Updated batch {batch_id} status to failed")
                
                return {
                    "status": "failed",
                    "batch_id": batch_id,
                    "error": error_message
                }
            
            return {"status": "orphaned_failure", "execution_name": execution_name}
            
        except Exception as e:
            logger.error(f"❌ Failed to handle job failure: {str(e)}")
            raise
    
    async def _process_batch_completion(self, batch_id: str, event_data: Dict[str, Any]):
        """Process batch completion - aggregate results and update status"""
        
        try:
            logger.info(f"🔄 Processing batch completion: {batch_id}")
            
            # TODO: Implement result aggregation from GCS
            # This would read individual shard results and combine them
            
            # For now, mark as completed
            self.firestore_client.collection('batches').document(batch_id).update({
                "status": "completed",
                "completed_at": firestore.SERVER_TIMESTAMP,
                "processing_time_seconds": event_data.get("duration", 0)
            })
            
            logger.info(f"✅ Batch completion processed: {batch_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process batch completion for {batch_id}: {str(e)}")
            raise
    
    async def _cancel_batch_processing(self, batch_id: str) -> Dict[str, Any]:
        """Cancel running batch processing"""
        
        try:
            # Get batch document to find Cloud Run execution
            batch_doc = self.firestore_client.collection('batches').document(batch_id).get()
            
            if not batch_doc.exists:
                return {"status": "not_found", "batch_id": batch_id}
            
            batch_data = batch_doc.to_dict()
            execution_name = batch_data.get("cloud_run_operation")
            
            if execution_name:
                # TODO: Cancel Cloud Run job execution
                # This would require calling the Cloud Run API to cancel the job
                logger.info(f"🛑 Cancelling Cloud Run execution: {execution_name}")
            
            return {"status": "cancelled", "batch_id": batch_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel batch processing for {batch_id}: {str(e)}")
            raise
    
    async def _handle_job_post_processing(self, job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle post-processing for completed jobs"""
        
        try:
            # Extract job metadata
            fields = job_data.get("fields", {})
            job_type = fields.get("job_type", {}).get("stringValue", "")
            
            if job_type == "batch_parent":
                # Check if all child jobs are complete
                # TODO: Implement batch completion checking
                pass
            
            return {"status": "post_processed", "job_id": job_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to post-process job {job_id}: {str(e)}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event processing metrics"""
        
        return {
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "success_rate": (self.events_processed - self.events_failed) / max(self.events_processed, 1) * 100,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None
        }

# Global Eventarc handler instance
eventarc_handler = EventarcHandler()
