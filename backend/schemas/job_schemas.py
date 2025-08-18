from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobCreate(BaseModel):
    id: str
    name: str
    type: str
    status: JobStatus
    submitted: datetime
    parameters: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    completed: Optional[datetime] = None
    error_message: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    name: str
    type: str
    status: JobStatus
    submitted: datetime
    parameters: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    completed: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    results: Optional[Dict[str, Any]] = None
    completed: Optional[datetime] = None
    error_message: Optional[str] = None 