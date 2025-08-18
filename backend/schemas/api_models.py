"""
Standardized API Models for OMTX-Hub
All models use snake_case naming for consistency with corporate ecosystem
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

class TaskType(str, Enum):
    """Supported prediction task types"""
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"
    NANOBODY_DESIGN = "nanobody_design"
    CDR_OPTIMIZATION = "cdr_optimization"
    EPITOPE_TARGETED_DESIGN = "epitope_targeted_design"
    ANTIBODY_DE_NOVO_DESIGN = "antibody_de_novo_design"

class JobStatus(str, Enum):
    """Job status values"""
    PENDING = "pending"
    SUBMITTED = "submitted" 
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Base Models
class BaseApiModel(BaseModel):
    """Base model with standard configuration"""
    model_config = ConfigDict(
        # Generate camelCase aliases for frontend compatibility
        alias_generator=to_camel,
        # Allow field population by alias
        populate_by_name=True,
        # Use enum values in serialization
        use_enum_values=True,
        # Validate assignment
        validate_assignment=True
    )

class BaseRequest(BaseApiModel):
    """Base request model"""
    pass

class BaseResponse(BaseApiModel):
    """Base response model"""
    success: bool = Field(default=True, description="Whether the request was successful")
    message: Optional[str] = Field(default=None, description="Human-readable message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class ErrorResponse(BaseResponse):
    """Standard error response"""
    success: bool = Field(default=False)
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error information")

# Pagination Models
class PaginationRequest(BaseRequest):
    """Standard pagination request"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

class PaginationResponse(BaseApiModel):
    """Standard pagination response"""
    total_items: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")
    current_page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")

# Job Models
class JobCreate(BaseRequest):
    """Request to create a new job"""
    job_name: str = Field(..., min_length=1, max_length=255, description="Human-readable job name")
    task_type: TaskType = Field(..., description="Type of prediction task")
    model_id: str = Field(default="boltz2", description="Model to use for prediction")
    input_data: Dict[str, Any] = Field(..., description="Task-specific input data")
    use_msa: bool = Field(default=True, description="Whether to use MSA server")
    use_potentials: bool = Field(default=False, description="Whether to use potentials")
    batch_name: Optional[str] = Field(default=None, description="Batch name for grouped jobs")

class JobResponse(BaseResponse):
    """Job information response"""
    job_id: str = Field(..., description="Unique job identifier")
    job_name: str = Field(..., description="Human-readable job name")
    task_type: TaskType = Field(..., description="Type of prediction task")
    model_id: str = Field(..., description="Model used for prediction")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    estimated_completion_time: Optional[int] = Field(default=None, description="Estimated completion time in seconds")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Job progress (0-1)")
    batch_id: Optional[str] = Field(default=None, description="Batch identifier if part of batch")
    batch_index: Optional[int] = Field(default=None, description="Index within batch")

class JobDetailResponse(JobResponse):
    """Detailed job information with results"""
    input_data: Dict[str, Any] = Field(..., description="Task-specific input data")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Job parameters")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Job results")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: Optional[float] = Field(default=None, description="Actual execution time in seconds")
    resource_usage: Optional[Dict[str, Any]] = Field(default=None, description="Resource usage statistics")

class JobListRequest(PaginationRequest):
    """Request to list jobs with filtering"""
    status: Optional[JobStatus] = Field(default=None, description="Filter by job status")
    task_type: Optional[TaskType] = Field(default=None, description="Filter by task type")
    model_id: Optional[str] = Field(default=None, description="Filter by model")
    search_query: Optional[str] = Field(default=None, description="Search in job names")
    created_after: Optional[datetime] = Field(default=None, description="Filter jobs created after date")
    created_before: Optional[datetime] = Field(default=None, description="Filter jobs created before date")

class JobListResponse(BaseResponse):
    """Paginated list of jobs"""
    jobs: List[JobResponse] = Field(..., description="List of jobs")
    pagination: PaginationResponse = Field(..., description="Pagination information")

# Task Models
class TaskInfo(BaseApiModel):
    """Information about a supported task"""
    task_type: TaskType = Field(..., description="Task type identifier")
    task_name: str = Field(..., description="Human-readable task name")
    description: str = Field(..., description="Task description")
    estimated_time: int = Field(..., description="Estimated completion time in seconds")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for inputs")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema for outputs")

class TaskListResponse(BaseResponse):
    """List of supported tasks"""
    tasks: List[TaskInfo] = Field(..., description="Available tasks")
    total_tasks: int = Field(..., description="Total number of tasks")

# Batch Models  
class BatchCreate(BaseRequest):
    """Request to create a batch of jobs"""
    batch_name: str = Field(..., min_length=1, max_length=255, description="Batch name")
    jobs: List[JobCreate] = Field(..., min_items=1, description="Jobs in the batch")

class BatchResponse(BaseResponse):
    """Batch information"""
    batch_id: str = Field(..., description="Unique batch identifier")
    batch_name: str = Field(..., description="Human-readable batch name")
    total_jobs: int = Field(..., description="Total number of jobs in batch")
    completed_jobs: int = Field(default=0, description="Number of completed jobs")
    failed_jobs: int = Field(default=0, description="Number of failed jobs")
    status: str = Field(..., description="Overall batch status")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    estimated_completion_time: Optional[int] = Field(default=None, description="Estimated completion time for batch")

class BatchDetailResponse(BatchResponse):
    """Detailed batch information with jobs"""
    jobs: List[JobResponse] = Field(..., description="Jobs in the batch")
    common_parameters: Dict[str, Any] = Field(default_factory=dict, description="Common parameters across jobs")

class BatchListResponse(BaseResponse):
    """Paginated list of batches"""
    batches: List[BatchResponse] = Field(..., description="List of batches")
    pagination: PaginationResponse = Field(..., description="Pagination information")

# Log Models
class LogEntry(BaseApiModel):
    """Single log entry"""
    timestamp: str = Field(..., description="Log timestamp")
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    source: str = Field(..., description="Log source")
    function_name: Optional[str] = Field(default=None, description="Function that generated the log")
    app_id: Optional[str] = Field(default=None, description="Application identifier")
    execution_id: Optional[str] = Field(default=None, description="Execution identifier")
    raw_line: Optional[str] = Field(default=None, description="Raw log line")

class LogListRequest(PaginationRequest):
    """Request to list logs"""
    app_id: Optional[str] = Field(default=None, description="Filter by application ID")
    level: Optional[LogLevel] = Field(default=None, description="Filter by log level")
    search_query: Optional[str] = Field(default=None, description="Search in log messages")
    start_time: Optional[datetime] = Field(default=None, description="Start time for log range")
    end_time: Optional[datetime] = Field(default=None, description="End time for log range")

class LogListResponse(BaseResponse):
    """Paginated list of log entries"""
    logs: List[LogEntry] = Field(..., description="Log entries")
    pagination: PaginationResponse = Field(..., description="Pagination information")

# System Models
class SystemHealth(BaseApiModel):
    """System health status"""
    status: str = Field(..., description="Overall system status")
    database_status: str = Field(..., description="Database connectivity status")
    storage_status: str = Field(..., description="File storage status")
    modal_status: str = Field(..., description="Modal service status")
    active_jobs: int = Field(..., description="Number of currently active jobs")
    total_jobs_today: int = Field(..., description="Total jobs processed today")
    average_response_time: Optional[float] = Field(default=None, description="Average API response time")
    uptime: Optional[float] = Field(default=None, description="System uptime in seconds")

class SystemStatusResponse(BaseResponse):
    """System status response"""
    health: SystemHealth = Field(..., description="Health information")
    supported_tasks: List[str] = Field(..., description="List of supported task types")
    recent_jobs_count: int = Field(..., description="Number of recent jobs")

# File Models
class FileDownloadResponse(BaseApiModel):
    """File download information"""
    file_name: str = Field(..., description="Name of the file")
    content_type: str = Field(..., description="MIME type of the file")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    download_url: Optional[str] = Field(default=None, description="Direct download URL")

# Update/Delete Models
class JobUpdate(BaseRequest):
    """Request to update job information"""
    status: Optional[JobStatus] = Field(default=None, description="New job status")
    results: Optional[Dict[str, Any]] = Field(default=None, description="Job results")
    error_message: Optional[str] = Field(default=None, description="Error message")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Job progress")

class JobDeleteResponse(BaseResponse):
    """Response after deleting a job"""
    job_id: str = Field(..., description="ID of deleted job")
    
class BatchDeleteResponse(BaseResponse):
    """Response after deleting a batch"""
    batch_id: str = Field(..., description="ID of deleted batch")
    deleted_jobs: int = Field(..., description="Number of jobs deleted")

# Export Models
class JobExportRequest(BaseRequest):
    """Request to export job data"""
    format: str = Field(default="json", description="Export format (json, csv, xlsx)")
    include_results: bool = Field(default=True, description="Include job results in export")
    include_logs: bool = Field(default=False, description="Include execution logs in export")

class JobExportResponse(BaseResponse):
    """Job export response"""
    export_url: str = Field(..., description="URL to download the exported file")
    file_name: str = Field(..., description="Name of the exported file")
    expires_at: datetime = Field(..., description="When the export URL expires")

# Search Models
class SearchRequest(PaginationRequest):
    """General search request"""
    query: str = Field(..., min_length=1, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional search filters")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")

class SearchResponse(BaseResponse):
    """Search results response"""
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    pagination: PaginationResponse = Field(..., description="Pagination information")
    search_query: str = Field(..., description="Original search query")
    total_matches: int = Field(..., description="Total number of matches")