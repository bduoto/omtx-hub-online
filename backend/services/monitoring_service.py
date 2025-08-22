"""
Monitoring Service for OMTX-Hub
Comprehensive monitoring and alerting for GKE and Cloud Run components
"""

import os
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from google.cloud import monitoring_v3
from google.cloud import logging as gcp_logging
from google.cloud import storage
from google.cloud import firestore

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    api_requests_per_minute: int
    active_jobs: int
    completed_jobs_last_hour: int
    failed_jobs_last_hour: int
    average_job_duration: float
    gpu_utilization: float
    storage_usage_gb: float
    active_users: int
    error_rate: float

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # 'greater', 'less', 'equal'
    duration_minutes: int
    severity: str  # 'critical', 'warning', 'info'
    enabled: bool = True

class MonitoringService:
    """Comprehensive monitoring service for OMTX-Hub infrastructure"""
    
    def __init__(self):
        self.project_id = os.getenv('GCP_PROJECT_ID', 'om-models')
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.logging_client = gcp_logging.Client()
        self.storage_client = storage.Client()
        self.db = firestore.Client()
        
        # Monitoring configuration
        self.metrics_interval = 60  # seconds
        self.log_retention_days = 30
        self.alert_cooldown = 300  # 5 minutes
        
        # Alert state tracking
        self.alert_states = {}
        self.last_alerts = {}
        
        # Custom metrics
        self.custom_metrics = [
            'omtx_hub/api_requests',
            'omtx_hub/job_completions',
            'omtx_hub/job_failures', 
            'omtx_hub/gpu_utilization',
            'omtx_hub/storage_usage',
            'omtx_hub/user_activity',
            'omtx_hub/error_rate'
        ]
        
        # Default alert rules
        self.alert_rules = [
            AlertRule("High Error Rate", "error_rate", 5.0, "greater", 5, "critical"),
            AlertRule("GPU High Utilization", "gpu_utilization", 90.0, "greater", 10, "warning"),
            AlertRule("Job Failure Rate", "job_failure_rate", 20.0, "greater", 15, "warning"),
            AlertRule("Storage Usage", "storage_usage_gb", 1000.0, "greater", 5, "warning"),
            AlertRule("API Response Time", "api_response_time", 2000, "greater", 5, "critical"),
            AlertRule("Active Jobs Stuck", "stuck_jobs", 5, "greater", 30, "critical")
        ]
        
        logger.info(f"📊 Monitoring Service initialized for project: {self.project_id}")
    
    async def start_monitoring(self):
        """Start monitoring tasks"""
        
        logger.info("🚀 Starting comprehensive monitoring service")
        
        # Create custom metrics if they don't exist
        await self._create_custom_metrics()
        
        # Start monitoring tasks
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._monitor_alerts())
        asyncio.create_task(self._monitor_job_health())
        asyncio.create_task(self._monitor_api_health())
        asyncio.create_task(self._cleanup_old_logs())
        
        logger.info("✅ Monitoring service started")
    
    async def _collect_system_metrics(self):
        """Collect and emit system metrics"""
        
        while True:
            try:
                start_time = time.time()
                
                # Collect metrics
                metrics = await self._gather_system_metrics()
                
                # Emit to Google Cloud Monitoring
                await self._emit_metrics(metrics)
                
                # Store historical data
                await self._store_metrics_history(metrics)
                
                collection_time = time.time() - start_time
                logger.debug(f"📈 Metrics collected in {collection_time:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Error collecting metrics: {e}")
            
            await asyncio.sleep(self.metrics_interval)
    
    async def _gather_system_metrics(self) -> SystemMetrics:
        """Gather comprehensive system metrics"""
        
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        try:
            # Query Firestore for job metrics
            jobs_ref = self.db.collection('jobs')
            
            # Active jobs
            active_jobs = len(list(jobs_ref.where('status', 'in', ['running', 'pending']).stream()))
            
            # Completed jobs in last hour
            completed_jobs = len(list(
                jobs_ref.where('status', '==', 'completed')
                .where('completed_at', '>=', hour_ago).stream()
            ))
            
            # Failed jobs in last hour
            failed_jobs = len(list(
                jobs_ref.where('status', '==', 'failed')
                .where('failed_at', '>=', hour_ago).stream()
            ))
            
            # Average job duration (last 10 completed jobs)
            recent_completed = list(
                jobs_ref.where('status', '==', 'completed')
                .order_by('completed_at', direction=firestore.Query.DESCENDING)
                .limit(10).stream()
            )
            
            avg_duration = 0.0
            if recent_completed:
                durations = [
                    job.to_dict().get('execution_time_seconds', 0) 
                    for job in recent_completed
                ]
                avg_duration = sum(durations) / len(durations)
            
            # Active users (last hour)
            users_ref = self.db.collection('users')
            active_users = len(list(
                users_ref.where('last_activity', '>=', hour_ago).stream()
            ))
            
            # Storage usage (approximate)
            storage_usage = await self._calculate_storage_usage()
            
            # GPU utilization (placeholder - would come from Cloud Run metrics)
            gpu_utilization = await self._get_gpu_utilization()
            
            # Error rate
            error_rate = (failed_jobs / max(completed_jobs + failed_jobs, 1)) * 100
            
            # API requests per minute (placeholder)
            api_requests = await self._get_api_request_rate()
            
            return SystemMetrics(
                timestamp=now,
                api_requests_per_minute=api_requests,
                active_jobs=active_jobs,
                completed_jobs_last_hour=completed_jobs,
                failed_jobs_last_hour=failed_jobs,
                average_job_duration=avg_duration,
                gpu_utilization=gpu_utilization,
                storage_usage_gb=storage_usage,
                active_users=active_users,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Error gathering metrics: {e}")
            # Return default metrics on error
            return SystemMetrics(
                timestamp=now,
                api_requests_per_minute=0,
                active_jobs=0,
                completed_jobs_last_hour=0,
                failed_jobs_last_hour=0,
                average_job_duration=0.0,
                gpu_utilization=0.0,
                storage_usage_gb=0.0,
                active_users=0,
                error_rate=0.0
            )
    
    async def _emit_metrics(self, metrics: SystemMetrics):
        """Emit metrics to Google Cloud Monitoring"""
        
        try:
            project_name = f"projects/{self.project_id}"
            
            # Create time series for each metric
            time_series = []
            
            metric_data = [
                ('omtx_hub/api_requests', metrics.api_requests_per_minute),
                ('omtx_hub/active_jobs', metrics.active_jobs),
                ('omtx_hub/completed_jobs', metrics.completed_jobs_last_hour),
                ('omtx_hub/failed_jobs', metrics.failed_jobs_last_hour),
                ('omtx_hub/job_duration', metrics.average_job_duration),
                ('omtx_hub/gpu_utilization', metrics.gpu_utilization),
                ('omtx_hub/storage_usage', metrics.storage_usage_gb),
                ('omtx_hub/active_users', metrics.active_users),
                ('omtx_hub/error_rate', metrics.error_rate)
            ]
            
            for metric_type, value in metric_data:
                series = monitoring_v3.TimeSeries()
                series.metric.type = f"custom.googleapis.com/{metric_type}"
                series.resource.type = "global"
                
                point = monitoring_v3.Point()
                point.value.double_value = float(value)
                point.interval.end_time.seconds = int(metrics.timestamp.timestamp())
                series.points = [point]
                
                time_series.append(series)
            
            # Send to monitoring
            if time_series:
                self.monitoring_client.create_time_series(
                    name=project_name,
                    time_series=time_series
                )
                
                logger.debug(f"📊 Emitted {len(time_series)} metrics to Cloud Monitoring")
            
        except Exception as e:
            logger.error(f"Failed to emit metrics: {e}")
    
    async def _monitor_alerts(self):
        """Monitor alert conditions and trigger notifications"""
        
        while True:
            try:
                for rule in self.alert_rules:
                    if not rule.enabled:
                        continue
                    
                    # Get current metric value
                    current_value = await self._get_metric_value(rule.metric_name)
                    
                    # Check alert condition
                    triggered = self._evaluate_alert_condition(rule, current_value)
                    
                    # Handle alert state
                    await self._handle_alert(rule, triggered, current_value)
                
            except Exception as e:
                logger.error(f"Error monitoring alerts: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _monitor_job_health(self):
        """Monitor job health and detect issues"""
        
        while True:
            try:
                # Check for stuck jobs
                stuck_threshold = datetime.utcnow() - timedelta(hours=2)
                
                stuck_jobs = list(
                    self.db.collection('jobs')
                    .where('status', '==', 'running')
                    .where('started_at', '<=', stuck_threshold)
                    .stream()
                )
                
                if stuck_jobs:
                    logger.warning(f"⚠️ Found {len(stuck_jobs)} stuck jobs")
                    await self._handle_stuck_jobs(stuck_jobs)
                
                # Check Cloud Run service health
                await self._check_cloud_run_health()
                
                # Check storage health
                await self._check_storage_health()
                
            except Exception as e:
                logger.error(f"Error monitoring job health: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def _monitor_api_health(self):
        """Monitor API endpoint health"""
        
        while True:
            try:
                import aiohttp
                
                # Health check our own API
                async with aiohttp.ClientSession() as session:
                    start_time = time.time()
                    
                    async with session.get(f"http://localhost:8000/health") as response:
                        response_time = (time.time() - start_time) * 1000  # ms
                        
                        if response.status == 200:
                            # Emit response time metric
                            await self._emit_single_metric('omtx_hub/api_response_time', response_time)
                            logger.debug(f"✅ API health check: {response_time:.1f}ms")
                        else:
                            logger.warning(f"⚠️ API health check failed: {response.status}")
                            await self._emit_single_metric('omtx_hub/api_errors', 1)
                
            except Exception as e:
                logger.error(f"API health check failed: {e}")
                await self._emit_single_metric('omtx_hub/api_errors', 1)
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _get_metric_value(self, metric_name: str) -> float:
        """Get current value for a metric"""
        
        # This would query Cloud Monitoring for the latest value
        # For now, return placeholder values
        metric_mapping = {
            'error_rate': 2.0,
            'gpu_utilization': 75.0,
            'storage_usage_gb': 500.0,
            'api_response_time': 150.0,
            'stuck_jobs': 0.0
        }
        
        return metric_mapping.get(metric_name, 0.0)
    
    def _evaluate_alert_condition(self, rule: AlertRule, current_value: float) -> bool:
        """Evaluate if alert condition is met"""
        
        if rule.comparison == 'greater':
            return current_value > rule.threshold
        elif rule.comparison == 'less':
            return current_value < rule.threshold
        elif rule.comparison == 'equal':
            return abs(current_value - rule.threshold) < 0.01
        
        return False
    
    async def _handle_alert(self, rule: AlertRule, triggered: bool, current_value: float):
        """Handle alert state changes"""
        
        alert_key = rule.name
        was_triggered = self.alert_states.get(alert_key, False)
        
        if triggered and not was_triggered:
            # New alert
            self.alert_states[alert_key] = True
            self.last_alerts[alert_key] = datetime.utcnow()
            
            await self._send_alert(rule, current_value, "FIRED")
            
        elif not triggered and was_triggered:
            # Alert resolved
            self.alert_states[alert_key] = False
            
            await self._send_alert(rule, current_value, "RESOLVED")
    
    async def _send_alert(self, rule: AlertRule, value: float, status: str):
        """Send alert notification"""
        
        logger.warning(f"🚨 ALERT {status}: {rule.name} - {value} {rule.comparison} {rule.threshold}")
        
        # Here you would integrate with your alerting system:
        # - Send email/SMS
        # - Post to Slack/Discord
        # - Create PagerDuty incident
        # - etc.
        
        # For now, just log structured alert data
        alert_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_name': rule.name,
            'status': status,
            'severity': rule.severity,
            'metric_name': rule.metric_name,
            'current_value': value,
            'threshold': rule.threshold,
            'comparison': rule.comparison
        }
        
        # Log to Cloud Logging with special severity
        severity = 'ERROR' if rule.severity == 'critical' else 'WARNING'
        logger.log(
            getattr(logging, severity),
            f"ALERT_{status}",
            extra={'alert_data': alert_data}
        )
    
    async def _calculate_storage_usage(self) -> float:
        """Calculate total storage usage in GB"""
        
        try:
            bucket = self.storage_client.bucket('hub-job-files')
            total_size = 0
            
            # Sample some blobs to estimate total size
            blobs = bucket.list_blobs(max_results=100)
            sample_size = 0
            sample_count = 0
            
            for blob in blobs:
                if blob.size:
                    sample_size += blob.size
                    sample_count += 1
            
            if sample_count > 0:
                # Rough estimate based on sample
                estimated_total = (sample_size / sample_count) * 1000  # Estimate
                return estimated_total / (1024 ** 3)  # Convert to GB
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating storage usage: {e}")
            return 0.0
    
    async def _get_gpu_utilization(self) -> float:
        """Get GPU utilization from Cloud Run metrics"""
        
        # Placeholder - would query Cloud Run metrics API
        return 75.0
    
    async def _get_api_request_rate(self) -> int:
        """Get API request rate from logs"""
        
        # Placeholder - would query Cloud Logging for request counts
        return 120
    
    async def _emit_single_metric(self, metric_type: str, value: float):
        """Emit a single metric to Cloud Monitoring"""
        
        try:
            project_name = f"projects/{self.project_id}"
            
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/{metric_type}"
            series.resource.type = "global"
            
            point = monitoring_v3.Point()
            point.value.double_value = float(value)
            point.interval.end_time.seconds = int(time.time())
            series.points = [point]
            
            self.monitoring_client.create_time_series(
                name=project_name,
                time_series=[series]
            )
            
        except Exception as e:
            logger.error(f"Failed to emit single metric {metric_type}: {e}")
    
    async def _create_custom_metrics(self):
        """Create custom metric descriptors if they don't exist"""
        
        try:
            project_name = f"projects/{self.project_id}"
            
            for metric_name in self.custom_metrics:
                descriptor = monitoring_v3.MetricDescriptor()
                descriptor.type = f"custom.googleapis.com/{metric_name}"
                descriptor.metric_kind = monitoring_v3.MetricDescriptor.MetricKind.GAUGE
                descriptor.value_type = monitoring_v3.MetricDescriptor.ValueType.DOUBLE
                descriptor.description = f"OMTX-Hub custom metric: {metric_name}"
                
                try:
                    self.monitoring_client.create_metric_descriptor(
                        name=project_name,
                        metric_descriptor=descriptor
                    )
                    logger.debug(f"Created metric descriptor: {metric_name}")
                except Exception as e:
                    # Metric might already exist
                    if "already exists" not in str(e):
                        logger.debug(f"Metric descriptor creation failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create metric descriptors: {e}")
    
    async def _store_metrics_history(self, metrics: SystemMetrics):
        """Store metrics history in Firestore for dashboards"""
        
        try:
            metrics_ref = self.db.collection('monitoring').document('metrics')\
                .collection('history').document()
            
            metrics_data = {
                'timestamp': metrics.timestamp,
                'api_requests_per_minute': metrics.api_requests_per_minute,
                'active_jobs': metrics.active_jobs,
                'completed_jobs_last_hour': metrics.completed_jobs_last_hour,
                'failed_jobs_last_hour': metrics.failed_jobs_last_hour,
                'average_job_duration': metrics.average_job_duration,
                'gpu_utilization': metrics.gpu_utilization,
                'storage_usage_gb': metrics.storage_usage_gb,
                'active_users': metrics.active_users,
                'error_rate': metrics.error_rate
            }
            
            metrics_ref.set(metrics_data)
            
        except Exception as e:
            logger.error(f"Failed to store metrics history: {e}")
    
    async def _cleanup_old_logs(self):
        """Clean up old monitoring data"""
        
        while True:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=self.log_retention_days)
                
                # Clean up old metrics history
                old_metrics = self.db.collection('monitoring').document('metrics')\
                    .collection('history').where('timestamp', '<=', cutoff_date).stream()
                
                deleted_count = 0
                for doc in old_metrics:
                    doc.reference.delete()
                    deleted_count += 1
                
                if deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {deleted_count} old metric records")
                
            except Exception as e:
                logger.error(f"Error cleaning up old logs: {e}")
            
            # Run daily
            await asyncio.sleep(24 * 3600)
    
    async def _handle_stuck_jobs(self, stuck_jobs: List[Any]):
        """Handle stuck jobs"""
        
        for job_doc in stuck_jobs:
            job_data = job_doc.to_dict()
            job_id = job_doc.id
            
            logger.warning(f"⚠️ Handling stuck job: {job_id}")
            
            # Mark as failed
            job_doc.reference.update({
                'status': 'failed',
                'error': 'Job stuck - marked as failed by monitoring service',
                'failed_at': firestore.SERVER_TIMESTAMP,
                'stuck_job_recovery': True
            })
    
    async def _check_cloud_run_health(self):
        """Check Cloud Run service health"""
        
        try:
            # This would check Cloud Run service status
            # For now, just log that we're checking
            logger.debug("🔍 Checking Cloud Run service health")
            
        except Exception as e:
            logger.error(f"Cloud Run health check failed: {e}")
    
    async def _check_storage_health(self):
        """Check Cloud Storage health"""
        
        try:
            # Test bucket accessibility
            bucket = self.storage_client.bucket('hub-job-files')
            bucket.reload()
            
            logger.debug("✅ Storage health check passed")
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            await self._emit_single_metric('omtx_hub/storage_errors', 1)

# Global monitoring service instance
monitoring_service = MonitoringService()