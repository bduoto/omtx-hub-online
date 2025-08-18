"""
Enhanced Job Model for OMTX-Hub Unified Architecture
Provides consistent data structures for individual, batch parent, and batch child jobs
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional
from enum import Enum
import time
import uuid
import logging

logger = logging.getLogger(__name__)

class JobType(str, Enum):
    """Job type classification for unified handling"""
    INDIVIDUAL = "individual"
    BATCH_PARENT = "batch_parent"
    BATCH_CHILD = "batch_child"

class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    """Prediction task types supported"""
    PROTEIN_LIGAND_BINDING = "protein_ligand_binding"
    BATCH_PROTEIN_LIGAND_SCREENING = "batch_protein_ligand_screening"
    PROTEIN_STRUCTURE = "protein_structure"
    PROTEIN_COMPLEX = "protein_complex"
    BINDING_SITE_PREDICTION = "binding_site_prediction"
    VARIANT_COMPARISON = "variant_comparison"
    DRUG_DISCOVERY = "drug_discovery"
    NANOBODY_DESIGN = "nanobody_design"
    CDR_OPTIMIZATION = "cdr_optimization"
    EPITOPE_TARGETED_DESIGN = "epitope_targeted_design"
    ANTIBODY_DE_NOVO_DESIGN = "antibody_de_novo_design"

@dataclass
class EnhancedJobData:
    """Enhanced job data structure for unified handling"""
    
    # Core identification
    id: str
    name: str
    job_type: JobType
    task_type: str  # Can be TaskType enum value or string
    status: JobStatus
    
    # Timestamps
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    updated_at: Optional[float] = None
    
    # Job data
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Metadata
    model_name: str = "boltz2"
    user_id: str = "current_user"
    organization_id: Optional[str] = None
    
    # Batch relationship fields
    batch_parent_id: Optional[str] = None
    batch_child_ids: Optional[List[str]] = None
    batch_index: Optional[int] = None
    
    # Enhanced batch intelligence (Senior Principal Engineer extension)
    batch_metadata: Optional[Dict[str, Any]] = None  # Shared batch context
    batch_progress: Optional[Dict[str, int]] = None  # Real-time progress tracking
    batch_estimated_completion: Optional[float] = None  # Dynamic completion estimates
    batch_total_ligands: Optional[int] = None  # For batch parent tracking
    batch_completion_rate: Optional[float] = None  # Success rate tracking
    
    # Execution tracking
    modal_call_id: Optional[str] = None
    gcp_storage_path: Optional[str] = None
    estimated_completion_time: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization validation and defaults"""
        # Set updated_at to current time if not provided
        if self.updated_at is None:
            self.updated_at = time.time()
        
        # Ensure job_type matches task_type for batch jobs
        if self.task_type == TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value:
            if self.job_type != JobType.BATCH_PARENT:
                self.job_type = JobType.BATCH_PARENT
        
        # Ensure batch children have proper parent reference
        if self.job_type == JobType.BATCH_CHILD and self.batch_parent_id is None:
            # Try to extract from legacy input_data format
            if isinstance(self.input_data, dict):
                legacy_parent = self.input_data.get('parent_batch_id')
                if legacy_parent:
                    self.batch_parent_id = legacy_parent
    
    def to_firestore_dict(self) -> Dict[str, Any]:
        """
        Convert to Firestore-compatible dictionary with size optimization.
        
        Senior Principal Engineering Note: Firestore has 1MB document limit.
        We store only lightweight metadata in Firestore and keep large data in GCP Storage.
        """
        data = asdict(self)
        
        # Convert enums to strings
        data['job_type'] = self.job_type.value
        data['status'] = self.status.value
        
        # ✅ CRITICAL FIX: Exclude large fields that can exceed 1MB Firestore limit
        large_fields_to_exclude = [
            'output_data',  # Can be >1MB with structure files and detailed prediction data
        ]
        
        # Keep only lightweight metadata for Firestore
        cleaned_data = {}
        for key, value in data.items():
            if value is not None and key not in large_fields_to_exclude:
                cleaned_data[key] = value
        
        # Add lightweight indicators for API compatibility
        cleaned_data['has_results'] = self.output_data is not None
        cleaned_data['results_in_gcp'] = bool(self.gcp_storage_path)
        
        return cleaned_data
    
    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        base_dict = self.to_firestore_dict()
        
        # Add computed fields for API
        base_dict['duration'] = self._calculate_duration()
        base_dict['is_batch'] = self.job_type in [JobType.BATCH_PARENT, JobType.BATCH_CHILD]
        base_dict['has_results'] = self.output_data is not None
        base_dict['can_view'] = self.status in [JobStatus.COMPLETED, JobStatus.FAILED]
        
        return base_dict
    
    def _calculate_duration(self) -> Optional[float]:
        """Calculate job execution duration in seconds"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return None
    
    @classmethod
    def from_firestore_dict(cls, data: Dict[str, Any]) -> 'EnhancedJobData':
        """Create EnhancedJobData from Firestore document"""
        
        # Convert string enums back to enum objects
        if 'job_type' in data:
            data['job_type'] = JobType(data['job_type'])
        if 'status' in data:
            data['status'] = JobStatus(data['status'])
        
        # Handle missing fields with defaults
        data.setdefault('created_at', time.time())
        data.setdefault('input_data', {})
        data.setdefault('job_type', JobType.INDIVIDUAL)
        data.setdefault('status', JobStatus.PENDING)
        
        return cls(**data)
    
    @classmethod
    def from_job_data(cls, job_data: Dict[str, Any]) -> Optional['EnhancedJobData']:
        """
        Create EnhancedJobData ONLY from properly formatted jobs.
        Returns None if job doesn't meet our new format requirements.
        
        Required fields for new format:
        - job_type (must be one of: individual, batch_parent, batch_child)
        - task_type (must be a valid TaskType)
        - status (must be a valid JobStatus)
        """
        
        # STRICT VALIDATION: Only accept jobs with proper job_type field
        job_type_str = job_data.get('job_type')
        if not job_type_str:
            # No job_type field = legacy job, ignore it
            return None
        
        # Validate job_type is valid
        try:
            job_type = JobType(job_type_str)
        except ValueError:
            # Invalid job_type value = corrupted or legacy, ignore it
            return None
        
        # Validate required fields are present
        if not job_data.get('id'):
            return None
        if not job_data.get('name'):
            return None
        if not job_data.get('task_type'):
            return None
        
        # Validate status is valid
        try:
            status = JobStatus(job_data.get('status', 'pending'))
        except ValueError:
            return None
        
        # Convert timestamp fields properly
        def convert_timestamp(value):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return value
            if hasattr(value, 'timestamp'):
                return value.timestamp()
            if isinstance(value, str):
                from datetime import datetime
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
                except:
                    return None
            return None
        
        # Build the enhanced job with validated data
        try:
            return cls(
                id=job_data['id'],
                name=job_data['name'],
                job_type=job_type,
                task_type=job_data['task_type'],
                status=status,
                created_at=convert_timestamp(job_data.get('created_at')) or time.time(),
                started_at=convert_timestamp(job_data.get('started_at')),
                completed_at=convert_timestamp(job_data.get('completed_at')),
                updated_at=convert_timestamp(job_data.get('updated_at')),
                input_data=job_data.get('input_data', {}),
                output_data=job_data.get('output_data'),
                error_message=job_data.get('error_message'),
                model_name=job_data.get('model_name', 'boltz2'),
                user_id=job_data.get('user_id', 'current_user'),
                batch_parent_id=job_data.get('batch_parent_id'),
                batch_child_ids=job_data.get('batch_child_ids'),
                batch_index=job_data.get('batch_index'),
                modal_call_id=job_data.get('modal_call_id'),
                gcp_storage_path=job_data.get('gcp_storage_path'),
                estimated_completion_time=job_data.get('estimated_completion_time')
            )
        except Exception as e:
            # Any error in creating the job = invalid format, ignore it
            logger.debug(f"Skipping invalid job {job_data.get('id', 'unknown')}: {e}")
            return None
    
    def update_status(self, new_status: JobStatus, output_data: Dict[str, Any] = None, error_message: str = None):
        """Update job status with proper timestamps"""
        old_status = self.status
        self.status = new_status
        self.updated_at = time.time()
        
        # Set appropriate timestamps
        if new_status == JobStatus.RUNNING and old_status == JobStatus.PENDING:
            self.started_at = time.time()
        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            self.completed_at = time.time()
        
        # Update data
        if output_data:
            self.output_data = output_data
        if error_message:
            self.error_message = error_message
    
    def add_child_job(self, child_id: str):
        """Add a child job ID to a batch parent"""
        if self.job_type != JobType.BATCH_PARENT:
            raise ValueError("Only batch parent jobs can have children")

        if self.batch_child_ids is None:
            self.batch_child_ids = []

        if child_id not in self.batch_child_ids:
            self.batch_child_ids.append(child_id)
            self.updated_at = time.time()

    def update_status(self, new_status: JobStatus, output_data: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None):
        """Update job status with optional output data and error message"""
        self.status = new_status
        self.updated_at = time.time()

        if new_status == JobStatus.RUNNING and self.started_at is None:
            self.started_at = time.time()
        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            if self.completed_at is None:
                self.completed_at = time.time()

        if output_data:
            self.output_data = output_data

        if error_message:
            self.error_message = error_message
    
    def is_batch_complete(self, child_statuses: List[JobStatus]) -> bool:
        """Check if a batch parent job is complete based on children"""
        if self.job_type != JobType.BATCH_PARENT:
            return False
        
        if not child_statuses:
            return False
        
        # All children must be in a final state
        final_states = [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
        return all(status in final_states for status in child_statuses)
    
    def calculate_batch_progress(self, child_statuses: List[JobStatus]) -> Dict[str, Any]:
        """Calculate batch progress statistics"""
        if self.job_type != JobType.BATCH_PARENT:
            return {}
        
        if not child_statuses:
            return {'total': 0, 'completed': 0, 'failed': 0, 'running': 0, 'pending': 0, 'progress_percentage': 0}
        
        total = len(child_statuses)
        completed = child_statuses.count(JobStatus.COMPLETED)
        failed = child_statuses.count(JobStatus.FAILED)
        running = child_statuses.count(JobStatus.RUNNING)
        pending = child_statuses.count(JobStatus.PENDING)
        cancelled = child_statuses.count(JobStatus.CANCELLED)
        
        progress_percentage = ((completed + failed + cancelled) / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': pending,
            'cancelled': cancelled,
            'progress_percentage': progress_percentage,
            'success_rate': (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
        }
    
    # === Enhanced Batch Intelligence Methods (Senior Principal Engineer) ===
    
    def update_batch_progress(self, child_statuses: List[JobStatus], 
                            children_data: Optional[List['EnhancedJobData']] = None) -> None:
        """Update real-time batch progress with intelligent completion estimation"""
        if self.job_type != JobType.BATCH_PARENT:
            return
        
        # Calculate current progress
        progress = self.calculate_batch_progress(child_statuses)
        self.batch_progress = progress
        
        # Update batch metadata with intelligent insights
        if children_data:
            self._update_batch_intelligence(children_data, progress)
        
        # Dynamic completion estimation
        self.batch_estimated_completion = self._calculate_dynamic_completion_time(progress, children_data)
        
        # Track completion rate for batch quality metrics
        if progress['total'] > 0:
            self.batch_completion_rate = progress['completed'] / progress['total']
    
    def _update_batch_intelligence(self, children_data: List['EnhancedJobData'], 
                                 progress: Dict[str, Any]) -> None:
        """Update batch metadata with intelligent insights"""
        if not self.batch_metadata:
            self.batch_metadata = {}
        
        # Performance insights
        completed_children = [child for child in children_data if child.status == JobStatus.COMPLETED]
        if completed_children:
            durations = [child._calculate_duration() for child in completed_children 
                        if child._calculate_duration() is not None]
            if durations:
                self.batch_metadata.update({
                    'avg_execution_time': sum(durations) / len(durations),
                    'fastest_execution': min(durations),
                    'slowest_execution': max(durations),
                    'performance_variance': max(durations) - min(durations) if len(durations) > 1 else 0
                })
        
        # Quality insights
        if progress['total'] > 0:
            self.batch_metadata.update({
                'current_success_rate': progress['completed'] / progress['total'],
                'failure_rate': progress['failed'] / progress['total'],
                'completion_trend': self._analyze_completion_trend(children_data)
            })
        
        # Resource utilization insights
        running_children = [child for child in children_data if child.status == JobStatus.RUNNING]
        self.batch_metadata.update({
            'concurrent_executions': len(running_children),
            'resource_efficiency': self._calculate_resource_efficiency(progress, children_data)
        })
    
    def _calculate_dynamic_completion_time(self, progress: Dict[str, Any], 
                                        children_data: Optional[List['EnhancedJobData']]) -> Optional[float]:
        """Calculate intelligent completion time estimation"""
        if not children_data or progress['total'] == 0:
            return None
        
        # If batch is complete, return 0
        if progress['completed'] + progress['failed'] + progress['cancelled'] >= progress['total']:
            return 0.0
        
        # Calculate average execution time from completed children
        completed_children = [child for child in children_data if child.status == JobStatus.COMPLETED]
        if not completed_children:
            # Use default estimation if no completed children
            remaining_jobs = progress['running'] + progress['pending']
            return remaining_jobs * 300.0  # 5 minutes per job default
        
        # Calculate based on actual performance
        durations = [child._calculate_duration() for child in completed_children 
                    if child._calculate_duration() is not None]
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            # Add 20% buffer for variance and apply to remaining jobs
            remaining_jobs = progress['running'] + progress['pending']
            estimated_time = remaining_jobs * avg_duration * 1.2
            return estimated_time
        
        return None
    
    def _analyze_completion_trend(self, children_data: List['EnhancedJobData']) -> str:
        """Analyze batch completion trend for intelligent insights"""
        completed_children = [child for child in children_data 
                            if child.status == JobStatus.COMPLETED and child.completed_at]
        
        if len(completed_children) < 2:
            return "insufficient_data"
        
        # Sort by completion time
        completed_children.sort(key=lambda x: x.completed_at)
        
        # Calculate completion rate trend (jobs per minute)
        recent_completions = completed_children[-5:] if len(completed_children) >= 5 else completed_children
        if len(recent_completions) >= 2:
            time_span = recent_completions[-1].completed_at - recent_completions[0].completed_at
            if time_span > 0:
                completion_rate = (len(recent_completions) - 1) / (time_span / 60)  # jobs per minute
                
                # Classify trend
                if completion_rate >= 0.5:
                    return "accelerating"
                elif completion_rate >= 0.2:
                    return "steady"
                else:
                    return "decelerating"
        
        return "stable"
    
    def _calculate_resource_efficiency(self, progress: Dict[str, Any], 
                                     children_data: List['EnhancedJobData']) -> float:
        """Calculate batch resource utilization efficiency"""
        if progress['total'] == 0:
            return 0.0
        
        # Consider factors: concurrent execution, failure rate, completion speed
        concurrency_factor = min(progress['running'] / max(progress['total'] * 0.1, 1), 1.0)  # Optimal ~10% concurrent
        success_factor = progress['completed'] / max(progress['completed'] + progress['failed'], 1)
        
        # Weighted efficiency score
        efficiency = (concurrency_factor * 0.3) + (success_factor * 0.7)
        return min(efficiency, 1.0)
    
    def get_batch_insights(self) -> Dict[str, Any]:
        """Get comprehensive batch performance and quality insights"""
        if self.job_type != JobType.BATCH_PARENT:
            return {}
        
        insights = {
            'batch_id': self.id,
            'batch_name': self.name,
            'current_progress': self.batch_progress or {},
            'estimated_completion_time': self.batch_estimated_completion,
            'completion_rate': self.batch_completion_rate,
            'batch_metadata': self.batch_metadata or {},
            'total_ligands': self.batch_total_ligands,
            'intelligence_timestamp': time.time()
        }
        
        # Add status-based insights
        if self.batch_progress:
            progress = self.batch_progress
            insights.update({
                'batch_health': self._assess_batch_health(progress),
                'performance_rating': self._rate_batch_performance(),
                'recommendations': self._generate_batch_recommendations(progress)
            })
        
        return insights
    
    def _assess_batch_health(self, progress: Dict[str, Any]) -> str:
        """Assess overall batch health status"""
        if progress['total'] == 0:
            return "unknown"
        
        failure_rate = progress['failed'] / progress['total']
        completion_rate = progress['completed'] / progress['total']
        finished_rate = (progress['completed'] + progress['failed'] + progress['cancelled']) / progress['total']
        
        # For completed batches, use final success rate
        if finished_rate >= 0.95:  # Batch is essentially complete
            if completion_rate >= 0.9 and failure_rate <= 0.1:
                return "excellent"
            elif failure_rate > 0.3:
                return "unhealthy"
            elif failure_rate > 0.1:
                return "concerning"
            else:
                return "healthy"
        
        # For in-progress batches, consider current trends
        if failure_rate > 0.3:
            return "unhealthy"
        elif failure_rate > 0.15 and completion_rate < 0.3:
            return "concerning"
        elif completion_rate > 0.6 and failure_rate < 0.1:
            return "excellent"
        else:
            return "healthy"
    
    def _rate_batch_performance(self) -> str:
        """Rate batch performance based on efficiency metrics"""
        if not self.batch_metadata:
            return "unknown"
        
        efficiency = self.batch_metadata.get('resource_efficiency', 0)
        success_rate = self.batch_metadata.get('current_success_rate', 0)
        
        combined_score = (efficiency * 0.4) + (success_rate * 0.6)
        
        if combined_score >= 0.9:
            return "outstanding"
        elif combined_score >= 0.8:
            return "excellent"
        elif combined_score >= 0.7:
            return "good"
        elif combined_score >= 0.6:
            return "fair"
        else:
            return "poor"
    
    def _generate_batch_recommendations(self, progress: Dict[str, Any]) -> List[str]:
        """Generate intelligent recommendations for batch optimization"""
        recommendations = []
        
        if not progress or progress['total'] == 0:
            return recommendations
        
        failure_rate = progress['failed'] / progress['total']
        running_rate = progress['running'] / progress['total']
        
        # Performance recommendations
        if failure_rate > 0.2:
            recommendations.append("High failure rate detected - review input validation")
        
        if running_rate > 0.5 and progress['completed'] > 0:
            recommendations.append("High concurrent load - consider reducing batch size for better stability")
        
        if self.batch_metadata:
            variance = self.batch_metadata.get('performance_variance', 0)
            if variance > 300:  # 5 minutes variance
                recommendations.append("High execution time variance - review job complexity distribution")
            
            trend = self.batch_metadata.get('completion_trend', '')
            if trend == 'decelerating':
                recommendations.append("Completion rate declining - monitor system resources")
        
        return recommendations


def create_individual_job(name: str, task_type: str, input_data: Dict[str, Any], 
                         model_name: str = "boltz2", user_id: str = "current_user") -> EnhancedJobData:
    """Factory function for creating individual jobs"""
    return EnhancedJobData(
        id=str(uuid.uuid4()),
        name=name,
        job_type=JobType.INDIVIDUAL,
        task_type=task_type,
        status=JobStatus.PENDING,
        created_at=time.time(),
        input_data=input_data,
        model_name=model_name,
        user_id=user_id
    )

def create_batch_parent_job(name: str, task_type: str, input_data: Dict[str, Any],
                           model_name: str = "boltz2", user_id: str = "current_user") -> EnhancedJobData:
    """Factory function for creating batch parent jobs"""
    return EnhancedJobData(
        id=str(uuid.uuid4()),
        name=name,
        job_type=JobType.BATCH_PARENT,
        task_type=task_type,
        status=JobStatus.PENDING,
        created_at=time.time(),
        input_data=input_data,
        model_name=model_name,
        user_id=user_id,
        batch_child_ids=[]
    )

def create_batch_child_job(name: str, parent_id: str, batch_index: int, input_data: Dict[str, Any],
                          model_name: str = "boltz2", user_id: str = "current_user") -> EnhancedJobData:
    """Factory function for creating batch child jobs"""
    return EnhancedJobData(
        id=str(uuid.uuid4()),
        name=name,
        job_type=JobType.BATCH_CHILD,
        task_type=TaskType.PROTEIN_LIGAND_BINDING.value,  # Children are always individual predictions
        status=JobStatus.PENDING,
        created_at=time.time(),
        input_data=input_data,
        model_name=model_name,
        user_id=user_id,
        batch_parent_id=parent_id,
        batch_index=batch_index
    )