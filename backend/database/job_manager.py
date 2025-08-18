import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from schemas.job_schemas import JobCreate, JobResponse, JobStatus, JobUpdate

class JobManager:
    def __init__(self, storage_path: str = "jobs"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.jobs_file = self.storage_path / "jobs.json"
        self._load_jobs()
    
    def _load_jobs(self):
        """Load jobs from JSON file"""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    data = json.load(f)
                    self.jobs = {job_id: JobResponse(**job_data) for job_id, job_data in data.items()}
            except Exception as e:
                print(f"Error loading jobs: {e}")
                self.jobs = {}
        else:
            self.jobs = {}
    
    def _save_jobs(self):
        """Save jobs to JSON file"""
        try:
            with open(self.jobs_file, 'w') as f:
                json.dump(
                    {job_id: job.dict() for job_id, job in self.jobs.items()},
                    f,
                    default=str,
                    indent=2
                )
        except Exception as e:
            print(f"Error saving jobs: {e}")
    
    def create_job(self, job: JobCreate) -> str:
        """Create a new job"""
        job_response = JobResponse(**job.dict())
        self.jobs[job.id] = job_response
        self._save_jobs()
        return job.id
    
    def get_job(self, job_id: str) -> Optional[JobResponse]:
        """Get a job by ID"""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[JobResponse]:
        """Get all jobs"""
        return list(self.jobs.values())
    
    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update job status"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].status = status
        if status in ["completed", "failed"]:
            self.jobs[job_id].completed = datetime.utcnow()
        
        self._save_jobs()
        return True
    
    def update_job_results(self, job_id: str, results: Dict[str, Any], status: str) -> bool:
        """Update job results and status"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].results = results
        self.jobs[job_id].status = status
        self.jobs[job_id].completed = datetime.utcnow()
        
        self._save_jobs()
        return True
    
    def update_job_error(self, job_id: str, error_message: str) -> bool:
        """Update job with error message"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].error_message = error_message
        self.jobs[job_id].status = "failed"
        self.jobs[job_id].completed = datetime.utcnow()
        
        self._save_jobs()
        return True
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False
    
    def get_jobs_by_status(self, status: JobStatus) -> List[JobResponse]:
        """Get jobs by status"""
        return [job for job in self.jobs.values() if job.status == status]
    
    def get_jobs_by_type(self, job_type: str) -> List[JobResponse]:
        """Get jobs by type"""
        return [job for job in self.jobs.values() if job.type == job_type] 