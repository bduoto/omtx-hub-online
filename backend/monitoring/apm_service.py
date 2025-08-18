#!/usr/bin/env python3
"""
Production APM (Application Performance Monitoring) Service
Senior Principal Engineer Implementation

Comprehensive observability suite for the unified batch processing system
with metrics, distributed tracing, alerting, and performance analytics.
"""

import time
import logging
import asyncio
import platform
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from enum import Enum

import json

# Integration with our new architecture components
try:
    from middleware.rate_limiter import rate_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Rate limiter not available for APM integration")
    RATE_LIMITER_AVAILABLE = False

try:
    from services.resource_quota_manager import resource_quota_manager
    QUOTA_MANAGER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Resource quota manager not available for APM integration")
    QUOTA_MANAGER_AVAILABLE = False

try:
    from services.gcp_results_indexer import gcp_results_indexer
    GCP_INDEXER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ GCP results indexer not available for APM integration")
    GCP_INDEXER_AVAILABLE = False

try:
    from monitoring.health_check_service import health_check_service
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Health check service not available for APM integration")
    HEALTH_CHECK_AVAILABLE = False

# OpenTelemetry integration (optional)
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    OTEL_AVAILABLE = True
except ImportError:
    logger.info("ℹ️ OpenTelemetry not available, using built-in monitoring")
    OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Types of metrics we track"""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: MetricType

@dataclass
class TraceSpan:
    """Distributed tracing span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    tags: Dict[str, str]
    logs: List[Dict[str, Any]]
    error: Optional[str]

@dataclass  
class Alert:
    """System alert"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    tags: Dict[str, str]
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class PerformanceProfiler:
    """Performance profiling and bottleneck detection"""
    
    def __init__(self):
        self.call_stats: Dict[str, List[float]] = defaultdict(list)
        self.slow_queries: deque = deque(maxlen=100)
        self.memory_snapshots: deque = deque(maxlen=50)
        
    def record_call(self, function_name: str, duration_ms: float, context: Dict[str, Any] = None):
        """Record function call performance"""
        self.call_stats[function_name].append(duration_ms)
        
        # Track slow operations (>1 second)
        if duration_ms > 1000:
            self.slow_queries.append({
                'function': function_name,
                'duration_ms': duration_ms,
                'timestamp': datetime.utcnow(),
                'context': context or {}
            })
    
    def get_function_stats(self, function_name: str) -> Dict[str, Any]:
        """Get performance statistics for a function"""
        if function_name not in self.call_stats:
            return {}
        
        durations = self.call_stats[function_name]
        return {
            'call_count': len(durations),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'p95_duration_ms': self._percentile(durations, 95),
            'p99_duration_ms': self._percentile(durations, 99),
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of duration data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

class SystemHealthMonitor:
    """System resource and health monitoring"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.health_history: deque = deque(maxlen=100)
        
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system health metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics (basic)
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
                
                # CPU
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'load_avg_1m': load_avg[0],
                'load_avg_5m': load_avg[1],
                'load_avg_15m': load_avg[2],
                
                # Memory
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_percent': memory.percent,
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_gb': round(swap.used / (1024**3), 2),
                'swap_percent': swap.percent,
                
                # Disk
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_percent': round((disk.used / disk.total) * 100, 2),
                
                # Network
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'network_packets_sent': network.packets_sent,
                'network_packets_recv': network.packets_recv,
                
                # Process
                'process_memory_rss_mb': round(process_memory.rss / (1024**2), 2),
                'process_memory_vms_mb': round(process_memory.vms / (1024**2), 2),
                'process_cpu_percent': process.cpu_percent(),
                'process_threads': process.num_threads(),
                
                # System info
                'platform': platform.platform(),
                'python_version': platform.python_version(),
            }
            
            self.health_history.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}

class BatchJobMonitor:
    """Monitoring specifically for batch job performance"""
    
    def __init__(self):
        self.job_metrics: Dict[str, Any] = defaultdict(list)
        self.batch_health: Dict[str, Dict] = {}
        self.performance_trends: deque = deque(maxlen=200)
        
    def record_batch_submission(self, batch_id: str, metadata: Dict[str, Any]):
        """Record batch submission metrics"""
        self.batch_health[batch_id] = {
            'status': 'submitted',
            'submitted_at': datetime.utcnow(),
            'total_jobs': metadata.get('total_jobs', 0),
            'model_name': metadata.get('model_name', 'unknown'),
            'user_id': metadata.get('user_id', 'unknown'),
            'estimated_duration': metadata.get('estimated_duration'),
            'resource_requirements': metadata.get('resource_requirements', {}),
            'metrics': {
                'jobs_completed': 0,
                'jobs_failed': 0,
                'jobs_running': 0,
                'average_job_duration': 0,
                'resource_utilization': 0,
                'error_rate': 0
            }
        }
    
    def update_batch_progress(self, batch_id: str, progress_data: Dict[str, Any]):
        """Update batch progress metrics"""
        if batch_id not in self.batch_health:
            return
        
        batch = self.batch_health[batch_id]
        batch['last_updated'] = datetime.utcnow()
        batch['status'] = progress_data.get('status', batch['status'])
        
        metrics = batch['metrics']
        metrics.update({
            'jobs_completed': progress_data.get('completed', 0),
            'jobs_failed': progress_data.get('failed', 0),
            'jobs_running': progress_data.get('running', 0),
            'progress_percentage': progress_data.get('progress_percentage', 0),
        })
        
        # Calculate error rate
        total_processed = metrics['jobs_completed'] + metrics['jobs_failed']
        if total_processed > 0:
            metrics['error_rate'] = (metrics['jobs_failed'] / total_processed) * 100
        
        # Record performance trend
        if batch.get('submitted_at'):
            elapsed = (datetime.utcnow() - batch['submitted_at']).total_seconds()
            throughput = metrics['jobs_completed'] / (elapsed / 60) if elapsed > 0 else 0  # jobs per minute
            
            self.performance_trends.append({
                'batch_id': batch_id,
                'timestamp': datetime.utcnow(),
                'throughput_jobs_per_minute': throughput,
                'error_rate': metrics['error_rate'],
                'model_name': batch['model_name']
            })
    
    def get_batch_health_summary(self) -> Dict[str, Any]:
        """Get overall batch system health"""
        if not self.batch_health:
            return {'total_batches': 0, 'healthy': True}
        
        statuses = defaultdict(int)
        total_error_rate = 0
        total_throughput = 0
        problematic_batches = []
        
        for batch_id, batch in self.batch_health.items():
            statuses[batch['status']] += 1
            
            error_rate = batch['metrics']['error_rate']
            total_error_rate += error_rate
            
            # Flag problematic batches
            if error_rate > 20:  # >20% error rate
                problematic_batches.append({
                    'batch_id': batch_id,
                    'error_rate': error_rate,
                    'model_name': batch['model_name']
                })
        
        avg_error_rate = total_error_rate / len(self.batch_health) if self.batch_health else 0
        
        # Calculate recent throughput
        recent_trends = [t for t in self.performance_trends 
                        if (datetime.utcnow() - t['timestamp']).total_seconds() < 3600]  # Last hour
        avg_throughput = sum(t['throughput_jobs_per_minute'] for t in recent_trends) / len(recent_trends) if recent_trends else 0
        
        return {
            'total_batches': len(self.batch_health),
            'status_breakdown': dict(statuses),
            'average_error_rate': round(avg_error_rate, 2),
            'average_throughput_jobs_per_minute': round(avg_throughput, 2),
            'problematic_batches': problematic_batches,
            'healthy': avg_error_rate < 10 and len(problematic_batches) == 0
        }

class ProductionAPMService:
    """
    Enterprise APM Service - Complete Observability Stack
    
    Features:
    - Real-time metrics collection and aggregation
    - Distributed tracing for request flows
    - Intelligent alerting with escalation
    - Performance profiling and bottleneck detection
    - System health monitoring
    - Batch job specific monitoring
    - Integration with rate limiter and quota manager
    - OpenTelemetry support
    - Custom dashboard data export
    """
    
    def __init__(self):
        self.metrics: List[MetricPoint] = []
        self.traces: Dict[str, List[TraceSpan]] = defaultdict(list)
        self.alerts: List[Alert] = []
        self.active_spans: Dict[str, TraceSpan] = {}
        
        # Monitoring components
        self.profiler = PerformanceProfiler()
        self.system_monitor = SystemHealthMonitor()
        self.batch_monitor = BatchJobMonitor()
        
        # OpenTelemetry integration
        self.otel_tracer = None
        self.otel_meter = None
        self._initialize_otel()
        
        # Performance thresholds for alerting
        self.alert_thresholds = {
            'cpu_percent': 85,
            'memory_percent': 85,
            'disk_percent': 90,
            'error_rate': 10,
            'response_time_p95': 5000,  # 5 seconds
            'batch_failure_rate': 15,
            'rate_limit_violations': 50,  # per hour
            'quota_violations': 20,       # per hour
            'cache_hit_rate': 80,         # minimum percentage
            'redis_errors': 10            # per hour
        }
        
        # Background monitoring task
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Performance counters
        self.counters = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'rate_limit_violations': 0,
            'quota_violations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'redis_errors': 0,
            'modal_calls': 0,
            'modal_successes': 0,
            'modal_failures': 0
        }
    
    def _initialize_otel(self):
        """Initialize OpenTelemetry if available"""
        if not OTEL_AVAILABLE:
            return
        
        try:
            # Configure tracing
            trace.set_tracer_provider(TracerProvider())
            
            # OTLP endpoint from environment
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                span_processor = BatchSpanProcessor(otlp_exporter)
                trace.get_tracer_provider().add_span_processor(span_processor)
                logger.info(f"✅ OpenTelemetry tracing configured with endpoint: {otlp_endpoint}")
            
            self.otel_tracer = trace.get_tracer(__name__)
            
            # Configure metrics
            if os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"):
                metric_exporter = OTLPMetricExporter(
                    endpoint=os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
                )
                metric_reader = PeriodicExportingMetricReader(
                    exporter=metric_exporter,
                    export_interval_millis=30000  # 30 seconds
                )
                metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
                self.otel_meter = metrics.get_meter(__name__)
                logger.info("✅ OpenTelemetry metrics configured")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize OpenTelemetry: {e}")
    
    def increment_counter(self, counter_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a performance counter"""
        if counter_name in self.counters:
            self.counters[counter_name] += value
        
        # Also record as metric
        self.record_metric(f"counter.{counter_name}", value, tags, MetricType.COUNTER)
        
        # OpenTelemetry counter
        if self.otel_meter:
            try:
                counter = self.otel_meter.create_counter(f"omtx_{counter_name}")
                attributes = tags or {}
                counter.add(value, attributes)
            except Exception as e:
                logger.debug(f"Failed to record OTel counter: {e}")
    
    async def collect_architecture_metrics(self) -> Dict[str, Any]:
        """Collect metrics from our new architecture components"""
        
        architecture_metrics = {}
        
        # Rate Limiter Metrics
        if RATE_LIMITER_AVAILABLE:
            try:
                rate_metrics = rate_limiter.get_metrics()
                architecture_metrics['rate_limiter'] = rate_metrics
                
                # Record key metrics
                self.record_metric("rate_limiter.requests_checked", rate_metrics.get('requests_checked', 0))
                self.record_metric("rate_limiter.requests_allowed", rate_metrics.get('requests_allowed', 0))
                self.record_metric("rate_limiter.requests_denied", rate_metrics.get('requests_denied', 0))
                self.record_metric("rate_limiter.allow_rate", rate_metrics.get('allow_rate', 0))
                
            except Exception as e:
                logger.error(f"❌ Error collecting rate limiter metrics: {e}")
                architecture_metrics['rate_limiter'] = {'error': str(e)}
        
        # Resource Quota Manager Metrics
        if QUOTA_MANAGER_AVAILABLE:
            try:
                quota_metrics = resource_quota_manager.get_metrics()
                architecture_metrics['quota_manager'] = quota_metrics
                
                # Record key metrics
                self.record_metric("quota.checks", quota_metrics.get('quota_checks', 0))
                self.record_metric("quota.violations", quota_metrics.get('quota_violations', 0))
                self.record_metric("quota.active_users", quota_metrics.get('active_users', 0))
                
            except Exception as e:
                logger.error(f"❌ Error collecting quota manager metrics: {e}")
                architecture_metrics['quota_manager'] = {'error': str(e)}
        
        # GCP Results Indexer Metrics
        if GCP_INDEXER_AVAILABLE:
            try:
                indexer_metrics = gcp_results_indexer.get_indexer_metrics()
                architecture_metrics['gcp_indexer'] = indexer_metrics
                
                # Record key metrics
                self.record_metric("indexer.jobs_indexed", indexer_metrics.get('jobs_indexed', 0))
                self.record_metric("indexer.cache_hit_rate", indexer_metrics.get('cache_hit_rate', 0))
                self.record_metric("indexer.queue_size", indexer_metrics.get('queue_size', 0))
                
            except Exception as e:
                logger.error(f"❌ Error collecting indexer metrics: {e}")
                architecture_metrics['gcp_indexer'] = {'error': str(e)}
        
        # Health Check Service Metrics
        if HEALTH_CHECK_AVAILABLE:
            try:
                health_metrics = health_check_service.get_health_metrics()
                architecture_metrics['health_check'] = health_metrics
                
                # Record key metrics
                self.record_metric("health.total_checks", health_metrics.get('total_checks', 0))
                self.record_metric("health.success_rate", health_metrics.get('success_rate', 0))
                self.record_metric("health.slo_breaches", health_metrics.get('slo_breaches', 0))
                self.record_metric("health.services_monitored", health_metrics.get('services_monitored', 0))
                
                # Get system health status
                system_health = await health_check_service.get_system_health()
                architecture_metrics['system_health'] = {
                    'overall_status': system_health.get('overall_status', 'unknown'),
                    'services_count': len(system_health.get('services', {})),
                    'slo_compliance_rate': system_health.get('slo_summary', {}).get('slo_compliance_rate', 0),
                    'slo_breaches': system_health.get('slo_summary', {}).get('slo_breaches', 0)
                }
                
            except Exception as e:
                logger.error(f"❌ Error collecting health check metrics: {e}")
                architecture_metrics['health_check'] = {'error': str(e)}
        
        return architecture_metrics
    
    async def check_enhanced_alert_conditions(self):
        """Enhanced alert checking including new architecture components"""
        
        # Get architecture metrics
        arch_metrics = await self.collect_architecture_metrics()
        
        # Rate Limiter Alerts
        if 'rate_limiter' in arch_metrics and 'error' not in arch_metrics['rate_limiter']:
            rate_metrics = arch_metrics['rate_limiter']
            
            # High denial rate
            allow_rate = rate_metrics.get('allow_rate', 100)
            if allow_rate < 90:  # Less than 90% requests allowed
                self.create_alert(
                    AlertSeverity.WARNING,
                    "High Rate Limiting Activity",
                    f"Only {allow_rate:.1f}% of requests are being allowed through rate limiting"
                )
            
            # Redis unavailable
            if not rate_metrics.get('redis_available', True):
                self.create_alert(
                    AlertSeverity.WARNING,
                    "Rate Limiter Redis Unavailable",
                    "Rate limiter is using fallback mode due to Redis unavailability"
                )
        
        # Quota Manager Alerts
        if 'quota_manager' in arch_metrics and 'error' not in arch_metrics['quota_manager']:
            quota_metrics = arch_metrics['quota_manager']
            
            # High quota violations
            quota_violations = quota_metrics.get('quota_violations', 0)
            if quota_violations > self.alert_thresholds['quota_violations']:
                self.create_alert(
                    AlertSeverity.ERROR,
                    "High Quota Violations",
                    f"{quota_violations} quota violations detected"
                )
        
        # GCP Indexer Alerts
        if 'gcp_indexer' in arch_metrics and 'error' not in arch_metrics['gcp_indexer']:
            indexer_metrics = arch_metrics['gcp_indexer']
            
            # Low cache hit rate
            cache_hit_rate = indexer_metrics.get('cache_hit_rate', 0)
            if cache_hit_rate < self.alert_thresholds['cache_hit_rate']:
                self.create_alert(
                    AlertSeverity.WARNING,
                    "Low Indexer Cache Hit Rate",
                    f"GCP indexer cache hit rate is {cache_hit_rate:.1f}% (threshold: {self.alert_thresholds['cache_hit_rate']}%)"
                )
            
            # Large queue size
            queue_size = indexer_metrics.get('queue_size', 0)
            if queue_size > 1000:
                self.create_alert(
                    AlertSeverity.WARNING,
                    "Large Indexer Queue",
                    f"GCP indexer queue has {queue_size} pending items"
                )
        
        # Health Check Service Alerts
        if 'health_check' in arch_metrics and 'error' not in arch_metrics['health_check']:
            health_metrics = arch_metrics['health_check']
            
            # Low health check success rate
            success_rate = health_metrics.get('success_rate', 100)
            if success_rate < 95:
                self.create_alert(
                    AlertSeverity.ERROR,
                    "Health Check Failures",
                    f"Health check success rate is {success_rate:.1f}% (target: 95%+)"
                )
            
            # SLO breaches detected
            slo_breaches = health_metrics.get('slo_breaches', 0)
            if slo_breaches > 0:
                self.create_alert(
                    AlertSeverity.WARNING,
                    "SLO Breaches Detected",
                    f"Health check service detected {slo_breaches} SLO breaches"
                )
        
        # System Health Alerts
        if 'system_health' in arch_metrics:
            system_health = arch_metrics['system_health']
            
            # Overall system status degraded
            overall_status = system_health.get('overall_status', 'unknown')
            if overall_status in ['critical', 'unhealthy']:
                self.create_alert(
                    AlertSeverity.CRITICAL,
                    "System Health Critical",
                    f"Overall system health status is {overall_status}"
                )
            elif overall_status == 'degraded':
                self.create_alert(
                    AlertSeverity.WARNING,
                    "System Health Degraded",
                    f"Overall system health status is {overall_status}"
                )
            
            # Low SLO compliance
            slo_compliance = system_health.get('slo_compliance_rate', 100)
            if slo_compliance < 90:
                self.create_alert(
                    AlertSeverity.ERROR,
                    "Low SLO Compliance",
                    f"System SLO compliance rate is {slo_compliance:.1f}% (target: 90%+)"
                )
                
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🚀 APM monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 APM monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect system metrics
                system_metrics = self.system_monitor.collect_system_metrics()
                await self._process_system_metrics(system_metrics)
                
                # Collect architecture metrics
                architecture_metrics = await self.collect_architecture_metrics()
                
                # Check for alerts (enhanced version)
                await self._check_alert_conditions()
                await self.check_enhanced_alert_conditions()
                
                # Clean old data
                await self._cleanup_old_data()
                
                # Wait before next collection
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Back off on errors
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None, metric_type: MetricType = MetricType.GAUGE):
        """Record a metric data point"""
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            metric_type=metric_type
        )
        self.metrics.append(metric)
        
        # Limit metrics history
        if len(self.metrics) > 10000:
            self.metrics = self.metrics[-5000:]  # Keep recent half
    
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, tags: Dict[str, str] = None):
        """Context manager for distributed tracing"""
        import uuid
        
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name=operation_name,
            start_time=datetime.utcnow(),
            end_time=None,
            duration_ms=None,
            tags=tags or {},
            logs=[],
            error=None
        )
        
        self.active_spans[span_id] = span
        start_time = time.time()
        
        try:
            yield span
        except Exception as e:
            span.error = str(e)
            span.logs.append({
                'timestamp': datetime.utcnow(),
                'level': 'error',
                'message': str(e)
            })
            raise
        finally:
            end_time = time.time()
            span.end_time = datetime.utcnow()
            span.duration_ms = (end_time - start_time) * 1000
            
            # Record performance
            self.profiler.record_call(operation_name, span.duration_ms, span.tags)
            
            # Store trace
            self.traces[trace_id].append(span)
            del self.active_spans[span_id]
            
            # Record metric
            self.record_metric(
                f"operation.{operation_name}.duration_ms",
                span.duration_ms,
                tags=span.tags,
                metric_type=MetricType.TIMER
            )
    
    def create_alert(self, severity: AlertSeverity, title: str, message: str, tags: Dict[str, str] = None):
        """Create a system alert"""
        import uuid
        
        alert = Alert(
            id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.alerts.append(alert)
        
        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(log_level, f"🚨 ALERT [{severity.value.upper()}] {title}: {message}")
        
        return alert
    
    async def _process_system_metrics(self, metrics: Dict[str, Any]):
        """Process and record system metrics"""
        if 'error' in metrics:
            return
        
        # Record key system metrics
        self.record_metric("system.cpu_percent", metrics['cpu_percent'])
        self.record_metric("system.memory_percent", metrics['memory_percent'])
        self.record_metric("system.disk_percent", metrics['disk_percent'])
        self.record_metric("system.load_avg_1m", metrics['load_avg_1m'])
        self.record_metric("system.process_memory_mb", metrics['process_memory_rss_mb'])
    
    async def _check_alert_conditions(self):
        """Check conditions that should trigger alerts"""
        # Get latest system metrics
        recent_metrics = {}
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=5)
        
        for metric in reversed(self.metrics):
            if metric.timestamp < cutoff:
                break
            if metric.name not in recent_metrics:
                recent_metrics[metric.name] = metric.value
        
        # Check CPU alert
        cpu_percent = recent_metrics.get("system.cpu_percent", 0)
        if cpu_percent > self.alert_thresholds['cpu_percent']:
            self.create_alert(
                AlertSeverity.WARNING,
                "High CPU Usage",
                f"CPU usage is {cpu_percent:.1f}% (threshold: {self.alert_thresholds['cpu_percent']}%)"
            )
        
        # Check memory alert
        memory_percent = recent_metrics.get("system.memory_percent", 0)
        if memory_percent > self.alert_thresholds['memory_percent']:
            self.create_alert(
                AlertSeverity.WARNING,
                "High Memory Usage", 
                f"Memory usage is {memory_percent:.1f}% (threshold: {self.alert_thresholds['memory_percent']}%)"
            )
        
        # Check batch system health
        batch_health = self.batch_monitor.get_batch_health_summary()
        if not batch_health['healthy']:
            self.create_alert(
                AlertSeverity.ERROR,
                "Batch System Issues",
                f"Batch system unhealthy: {batch_health['average_error_rate']:.1f}% error rate"
            )
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data to prevent memory leaks"""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Clean old metrics
        self.metrics = [m for m in self.metrics if m.timestamp > cutoff]
        
        # Clean old traces
        for trace_id in list(self.traces.keys()):
            spans = self.traces[trace_id]
            recent_spans = [s for s in spans if s.start_time > cutoff]
            if recent_spans:
                self.traces[trace_id] = recent_spans
            else:
                del self.traces[trace_id]
        
        # Clean old alerts (keep for 7 days)
        alert_cutoff = datetime.utcnow() - timedelta(days=7)
        self.alerts = [a for a in self.alerts if a.timestamp > alert_cutoff]
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        now = datetime.utcnow()
        
        # System health
        system_health = self.system_monitor.collect_system_metrics()
        
        # Batch health
        batch_health = self.batch_monitor.get_batch_health_summary()
        
        # Architecture metrics
        architecture_metrics = await self.collect_architecture_metrics()
        
        # Performance stats
        recent_traces = []
        for spans in self.traces.values():
            recent_traces.extend([s for s in spans if s.start_time > now - timedelta(hours=1)])
        
        # Active alerts
        active_alerts = [a for a in self.alerts if not a.resolved]
        
        # Top slow operations
        slow_operations = sorted(
            [(name, stats) for name, stats in self.profiler.call_stats.items()],
            key=lambda x: x[1][-1] if x[1] else 0,  # Sort by most recent duration
            reverse=True
        )[:10]
        
        # Performance counters summary
        total_requests = self.counters.get('requests_total', 0)
        success_rate = (
            (self.counters.get('requests_successful', 0) / total_requests * 100) 
            if total_requests > 0 else 100
        )
        
        return {
            'timestamp': now.isoformat(),
            'system_health': system_health,
            'batch_health': batch_health,
            'architecture': architecture_metrics,
            'performance': {
                'recent_traces_count': len(recent_traces),
                'active_spans_count': len(self.active_spans),
                'slow_operations': [
                    {
                        'name': name,
                        'stats': self.profiler.get_function_stats(name)
                    } for name, _ in slow_operations
                ],
                'counters': self.counters,
                'success_rate': success_rate
            },
            'alerts': {
                'active_count': len(active_alerts),
                'recent_alerts': [asdict(a) for a in active_alerts[-5:]],
                'severity_breakdown': {
                    severity.value: len([a for a in active_alerts if a.severity == severity])
                    for severity in AlertSeverity
                }
            },
            'integrations': {
                'rate_limiter_available': RATE_LIMITER_AVAILABLE,
                'quota_manager_available': QUOTA_MANAGER_AVAILABLE,
                'gcp_indexer_available': GCP_INDEXER_AVAILABLE,
                'opentelemetry_enabled': OTEL_AVAILABLE and self.otel_tracer is not None
            },
            'uptime_seconds': (now - self.system_monitor.start_time).total_seconds()
        }

# Global APM service instance
apm_service = ProductionAPMService()

# Enhanced middleware integration functions
async def record_request_start(request_id: str, endpoint: str, user_id: str = None):
    """Record the start of a request for tracking"""
    apm_service.increment_counter('requests_total')
    
    # Record rate limiter metrics if available
    if RATE_LIMITER_AVAILABLE:
        try:
            rate_metrics = rate_limiter.get_metrics()
            if rate_metrics.get('requests_denied', 0) > 0:
                apm_service.increment_counter('rate_limit_violations')
        except:
            pass

async def record_request_success(request_id: str, response_time_ms: float):
    """Record successful request completion"""
    apm_service.increment_counter('requests_successful')
    apm_service.record_metric('request.response_time_ms', response_time_ms, 
                             tags={'status': 'success'}, metric_type=MetricType.TIMER)

async def record_request_failure(request_id: str, error_type: str, response_time_ms: float):
    """Record failed request"""
    apm_service.increment_counter('requests_failed')
    apm_service.record_metric('request.response_time_ms', response_time_ms, 
                             tags={'status': 'error', 'error_type': error_type}, 
                             metric_type=MetricType.TIMER)

async def record_modal_call(call_id: str, model_type: str, success: bool = True):
    """Record Modal function call"""
    apm_service.increment_counter('modal_calls')
    
    if success:
        apm_service.increment_counter('modal_successes')
    else:
        apm_service.increment_counter('modal_failures')
    
    apm_service.record_metric('modal.call', 1, 
                             tags={'model_type': model_type, 'success': str(success)}, 
                             metric_type=MetricType.COUNTER)

async def record_quota_violation(user_id: str, resource_type: str):
    """Record quota violation"""
    apm_service.increment_counter('quota_violations')
    apm_service.record_metric('quota.violation', 1, 
                             tags={'user_id': user_id, 'resource_type': resource_type}, 
                             metric_type=MetricType.COUNTER)

async def record_cache_operation(operation: str, hit: bool = True):
    """Record cache operation"""
    if hit:
        apm_service.increment_counter('cache_hits')
    else:
        apm_service.increment_counter('cache_misses')
    
    apm_service.record_metric(f'cache.{operation}', 1, 
                             tags={'hit': str(hit)}, 
                             metric_type=MetricType.COUNTER)

async def initialize_apm_service(
    enable_otel: bool = None,
    otel_endpoint: str = None,
    alert_webhook_url: str = None
):
    """Initialize the APM service with configuration"""
    
    # Set environment variables if provided
    if otel_endpoint:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otel_endpoint
    
    # Re-initialize OpenTelemetry with new config
    if enable_otel or otel_endpoint:
        apm_service._initialize_otel()
    
    # Start monitoring
    await apm_service.start_monitoring()
    
    logger.info("✅ Enhanced APM service initialized with architecture integration")
    return apm_service

# Enhanced tracing context manager
@asynccontextmanager
async def trace_request(request_id: str, operation: str, user_id: str = None):
    """Enhanced request tracing with architecture integration"""
    start_time = time.time()
    
    # Record request start
    await record_request_start(request_id, operation, user_id)
    
    try:
        async with apm_service.trace_operation(operation, tags={
            'request_id': request_id,
            'user_id': user_id or 'unknown'
        }) as span:
            yield span
            
        # Record success
        response_time = (time.time() - start_time) * 1000
        await record_request_success(request_id, response_time)
        
    except Exception as e:
        # Record failure
        response_time = (time.time() - start_time) * 1000
        await record_request_failure(request_id, type(e).__name__, response_time)
        raise

# Decorator for automatic operation tracing
def trace_operation(operation_name: str = None):
    """Decorator to automatically trace function execution"""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        
        async def async_wrapper(*args, **kwargs):
            async with apm_service.trace_operation(operation_name) as span:
                span.tags.update({
                    'function': func.__name__,
                    'module': func.__module__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                })
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we'll use a simplified approach
            import uuid
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                apm_service.profiler.record_call(operation_name, duration_ms)
                apm_service.record_metric(f"operation.{operation_name}.duration_ms", duration_ms)
                return result
            except Exception as e:
                apm_service.create_alert(
                    AlertSeverity.ERROR,
                    f"Function Error: {operation_name}",
                    str(e)
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator