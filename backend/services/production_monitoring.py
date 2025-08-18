"""
Production Monitoring Service for OMTX-Hub
Provides comprehensive monitoring for the unified prediction pipeline
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class JobMetrics:
    """Metrics for job performance tracking"""
    job_type: str
    task_type: str
    status: str
    execution_time: Optional[float] = None
    queue_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: float = 0

class ProductionMonitor:
    """Production monitoring for unified job pipeline"""
    
    def __init__(self, max_metrics_history: int = 1000):
        self.metrics_history = deque(maxlen=max_metrics_history)
        self.active_jobs = {}  # job_id -> start_time
        self.job_counters = defaultdict(int)
        self.error_counters = defaultdict(int)
        self.performance_stats = defaultdict(list)
        self._lock = Lock()
        
    def track_job_start(self, job_id: str, job_type: str, task_type: str):
        """Track when a job starts"""
        with self._lock:
            self.active_jobs[job_id] = {
                'start_time': time.time(),
                'job_type': job_type,
                'task_type': task_type
            }
            self.job_counters[f"{job_type}_{task_type}_started"] += 1
            
    def track_job_completion(self, job_id: str, status: str, error_message: Optional[str] = None):
        """Track when a job completes"""
        with self._lock:
            if job_id not in self.active_jobs:
                logger.warning(f"Job {job_id} completed but not tracked")
                return
                
            job_info = self.active_jobs.pop(job_id)
            execution_time = time.time() - job_info['start_time']
            
            # Create metrics record
            metrics = JobMetrics(
                job_type=job_info['job_type'],
                task_type=job_info['task_type'],
                status=status,
                execution_time=execution_time,
                error_message=error_message,
                timestamp=time.time()
            )
            
            self.metrics_history.append(metrics)
            
            # Update counters
            counter_key = f"{job_info['job_type']}_{job_info['task_type']}_{status}"
            self.job_counters[counter_key] += 1
            
            if status == 'failed' and error_message:
                self.error_counters[error_message] += 1
                
            # Track performance
            perf_key = f"{job_info['job_type']}_{job_info['task_type']}"
            self.performance_stats[perf_key].append(execution_time)
            
            # Keep only recent performance data
            if len(self.performance_stats[perf_key]) > 100:
                self.performance_stats[perf_key] = self.performance_stats[perf_key][-100:]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        with self._lock:
            current_time = time.time()
            recent_metrics = [m for m in self.metrics_history if current_time - m.timestamp < 3600]  # Last hour
            
            total_jobs = len(recent_metrics)
            completed_jobs = len([m for m in recent_metrics if m.status == 'completed'])
            failed_jobs = len([m for m in recent_metrics if m.status == 'failed'])
            
            # Calculate average execution times
            avg_times = {}
            for key, times in self.performance_stats.items():
                if times:
                    avg_times[key] = {
                        'avg': sum(times) / len(times),
                        'min': min(times),
                        'max': max(times),
                        'count': len(times)
                    }
            
            return {
                'timestamp': current_time,
                'active_jobs': len(self.active_jobs),
                'recent_jobs_1h': total_jobs,
                'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                'failure_rate': (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                'average_execution_times': avg_times,
                'top_errors': dict(list(self.error_counters.items())[:5]),
                'job_type_distribution': self._get_job_type_distribution(recent_metrics),
                'system_status': self._determine_system_status(completed_jobs, failed_jobs, total_jobs)
            }
    
    def get_batch_job_health(self) -> Dict[str, Any]:
        """Get specific health metrics for batch jobs"""
        with self._lock:
            current_time = time.time()
            recent_batch_metrics = [
                m for m in self.metrics_history 
                if current_time - m.timestamp < 3600 and 'batch' in m.job_type
            ]
            
            batch_parents = [m for m in recent_batch_metrics if m.job_type == 'batch_parent']
            batch_children = [m for m in recent_batch_metrics if m.job_type == 'batch_child']
            
            return {
                'batch_parents_completed': len([m for m in batch_parents if m.status == 'completed']),
                'batch_children_completed': len([m for m in batch_children if m.status == 'completed']),
                'batch_children_failed': len([m for m in batch_children if m.status == 'failed']),
                'average_batch_child_time': self._calculate_average_time(batch_children),
                'batch_completion_rate': self._calculate_batch_completion_rate(),
                'active_batch_jobs': len([j for j in self.active_jobs.values() if 'batch' in j['job_type']])
            }
    
    def _get_job_type_distribution(self, metrics: List[JobMetrics]) -> Dict[str, int]:
        """Get distribution of job types"""
        distribution = defaultdict(int)
        for metric in metrics:
            distribution[f"{metric.job_type}_{metric.task_type}"] += 1
        return dict(distribution)
    
    def _determine_system_status(self, completed: int, failed: int, total: int) -> str:
        """Determine overall system status"""
        if total == 0:
            return "idle"
        
        failure_rate = failed / total * 100
        if failure_rate > 20:
            return "degraded"
        elif failure_rate > 10:
            return "warning"
        else:
            return "healthy"
    
    def _calculate_average_time(self, metrics: List[JobMetrics]) -> float:
        """Calculate average execution time for metrics"""
        times = [m.execution_time for m in metrics if m.execution_time is not None]
        return sum(times) / len(times) if times else 0
    
    def _calculate_batch_completion_rate(self) -> float:
        """Calculate batch job completion rate"""
        # This would need more sophisticated logic to track batch parent-child relationships
        # For now, return a simple metric
        batch_metrics = [m for m in self.metrics_history if 'batch' in m.job_type]
        if not batch_metrics:
            return 0
        
        completed = len([m for m in batch_metrics if m.status == 'completed'])
        return completed / len(batch_metrics) * 100
    
    def export_metrics(self) -> List[Dict[str, Any]]:
        """Export all metrics for external monitoring systems"""
        with self._lock:
            return [asdict(metric) for metric in self.metrics_history]
    
    def clear_old_metrics(self, hours_old: int = 24):
        """Clear metrics older than specified hours"""
        with self._lock:
            cutoff_time = time.time() - (hours_old * 3600)
            self.metrics_history = deque([
                m for m in self.metrics_history if m.timestamp > cutoff_time
            ], maxlen=self.metrics_history.maxlen)

# Global instance
production_monitor = ProductionMonitor()
