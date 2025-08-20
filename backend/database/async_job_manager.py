"""
Async wrapper for UnifiedJobManager to work with consolidated API
"""
import asyncio
from typing import Dict, Any, List, Tuple, Optional
import uuid
from datetime import datetime
from database.unified_job_manager import UnifiedJobManager

class AsyncJobManager:
    """Async wrapper for UnifiedJobManager with missing methods"""
    
    def __init__(self):
        self.sync_manager = UnifiedJobManager()
    
    async def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job"""
        loop = asyncio.get_event_loop()
        job_id = await loop.run_in_executor(None, self.sync_manager.create_job, job_data)
        if job_id:
            return {"id": job_id, **job_data}
        raise Exception("Failed to create job")
    
    async def create_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new batch"""
        # For now, create a batch as a special type of job
        batch_id = str(uuid.uuid4())
        batch_data["id"] = batch_id
        batch_data["type"] = "batch"
        batch_data["created_at"] = datetime.utcnow().isoformat()
        batch_data["status"] = "pending"
        
        # Store batch in database
        loop = asyncio.get_event_loop()
        job_id = await loop.run_in_executor(
            None, 
            self.sync_manager.create_job, 
            {
                "job_id": batch_id,
                "job_type": "BATCH_PARENT",
                **batch_data
            }
        )
        
        return batch_data
    
    async def update_batch(self, batch_id: str, updates: Dict[str, Any]) -> None:
        """Update batch data"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.sync_manager.update_job,
            batch_id,
            updates
        )
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.sync_manager.get_job, job_id)
    
    async def list_jobs(
        self, 
        user_id: str = "default",
        offset: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List jobs with pagination"""
        loop = asyncio.get_event_loop()
        
        # Get user jobs (get more than needed for filtering)
        jobs = await loop.run_in_executor(
            None,
            self.sync_manager.get_user_jobs,
            user_id,
            limit + offset  # Get extra for offset
        )
        
        if not jobs:
            return [], 0
        
        # Filter by status if provided
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        
        # Filter by model if provided
        if model_id:
            jobs = [j for j in jobs if j.get("model_id") == model_id]
        
        # Apply pagination
        total = len(jobs)
        jobs = jobs[offset:offset + limit]
        
        return jobs, total
    
    async def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch by ID"""
        return await self.get_job(batch_id)
    
    async def list_batches(
        self,
        user_id: str = "default",
        offset: int = 0,
        limit: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List batches with pagination"""
        # Get all batch jobs
        jobs, total = await self.list_jobs(user_id, offset, limit * 2, status)
        
        # Filter for batch parents only
        batches = [j for j in jobs if j.get("job_type") == "BATCH_PARENT"]
        
        return batches[:limit], len(batches)
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.sync_manager.delete_job,
            job_id
        )
        return result is not None
    
    async def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch and its children"""
        # First delete child jobs
        children, _ = await self.list_jobs(
            user_id="default",
            limit=1000,
            status=None
        )
        
        # Filter for children of this batch
        batch_children = [
            j for j in children 
            if j.get("batch_parent_id") == batch_id or j.get("batch_id") == batch_id
        ]
        
        # Delete all children
        for child in batch_children:
            await self.delete_job(child.get("id", child.get("job_id")))
        
        # Delete the batch itself
        return await self.delete_job(batch_id)
    
    async def health_check(self) -> bool:
        """Check if the database is healthy"""
        try:
            # Try to list a few jobs as a health check
            await self.list_jobs(limit=1)
            return True
        except Exception:
            return False