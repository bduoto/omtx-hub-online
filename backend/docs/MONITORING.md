# OMTX-Hub Monitoring & Observability

Comprehensive monitoring setup for OMTX-Hub using Prometheus, Grafana, and Google Cloud Monitoring.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Applications  │───▶│   Prometheus     │───▶│    Grafana      │
│   (GKE + CRun)  │    │   (Metrics)      │    │  (Dashboards)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Cloud Logging  │    │  Cloud Monitoring│    │   Alerting      │
│   (Structured)  │    │   (Custom Metrics)│    │  (Multi-channel)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📊 Metrics Collection

### Application Metrics (Prometheus)
- **HTTP Metrics**: Request rate, latency, error rate
- **Job Metrics**: Submissions, completions, failures, duration
- **System Metrics**: GPU utilization, storage usage, active users
- **Authentication Metrics**: Login attempts, failures
- **Webhook Metrics**: Delivery success/failure rates

### Infrastructure Metrics (Node Exporter)
- **Node Metrics**: CPU, memory, disk, network usage
- **Container Metrics**: Resource consumption per pod
- **Kubernetes Metrics**: Pod status, service health

### Custom Metrics (Google Cloud Monitoring)
- **API Performance**: Response times, throughput
- **Job Processing**: Queue depths, processing rates
- **Resource Utilization**: GPU efficiency, storage growth
- **User Activity**: Active users, usage patterns

## 🚀 Deployment

### Prerequisites
```bash
# Set environment variables
export GCP_PROJECT_ID="om-models"
export GKE_CLUSTER_NAME="omtx-hub-cluster"
export GKE_ZONE="us-central1-a"
```

### Deploy Monitoring Stack
```bash
# Deploy complete monitoring stack
cd backend
./scripts/deploy_monitoring.sh

# Or deploy components individually
kubectl apply -f k8s/monitoring/prometheus-config.yaml -n monitoring
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml -n monitoring
kubectl apply -f k8s/monitoring/grafana-deployment.yaml -n monitoring
```

### Verify Deployment
```bash
# Check all monitoring pods
kubectl get pods -n monitoring

# Check services and external IPs
kubectl get services -n monitoring

# View logs
kubectl logs -f deployment/prometheus -n monitoring
kubectl logs -f deployment/grafana -n monitoring
```

## 🔍 Access & Configuration

### Prometheus
- **URL**: `http://<PROMETHEUS_IP>:9090`
- **Port Forward**: `kubectl port-forward -n monitoring svc/prometheus 9090:9090`
- **Query Examples**:
  - API requests: `rate(http_requests_total[5m])`
  - Error rate: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])`
  - Job duration: `histogram_quantile(0.95, rate(omtx_hub_job_duration_seconds_bucket[5m]))`

### Grafana
- **URL**: `http://<GRAFANA_IP>:3000`
- **Port Forward**: `kubectl port-forward -n monitoring svc/grafana 3000:3000`
- **Login**: admin / omtx-hub-grafana-admin
- **Pre-configured Dashboards**:
  - OMTX-Hub System Overview
  - API Performance Dashboard
  - Job Processing Dashboard
  - Infrastructure Metrics

### Google Cloud Monitoring
- **Console**: Google Cloud Console → Monitoring
- **Custom Metrics**: Prefixed with `custom.googleapis.com/omtx_hub/`
- **Integration**: Automatic via Google Cloud Logging client

## 📈 Key Dashboards

### 1. System Overview Dashboard
- **System health status** (UP/DOWN indicators)
- **Active jobs** and **completed jobs** counters
- **API request rate** and **response time** trends
- **Error rate** percentage with thresholds
- **GPU utilization** and **storage usage** over time

### 2. API Performance Dashboard
- **Request throughput** by endpoint
- **Response time percentiles** (50th, 95th, 99th)
- **Error rate breakdown** by status code
- **Authentication success/failure** rates

### 3. Job Processing Dashboard
- **Job submission rate** by type
- **Processing pipeline** status
- **Queue depths** and **wait times**
- **Completion rates** and **failure analysis**
- **GPU efficiency** metrics

### 4. Infrastructure Dashboard
- **Node resource utilization** (CPU, memory, disk)
- **Pod status** and **restart counts**
- **Network traffic** and **storage I/O**
- **Kubernetes cluster health**

## 🚨 Alerting Rules

### Critical Alerts
- **API High Error Rate**: >5% errors for 2+ minutes
- **High Memory Usage**: >90% memory utilization for 5+ minutes
- **Low Disk Space**: <10% available disk space
- **Stuck Jobs**: >5 jobs running for 2+ hours

### Warning Alerts
- **API High Latency**: >2s 95th percentile for 5+ minutes
- **High Job Failure Rate**: >20% failure rate for 10+ minutes
- **High CPU Usage**: >90% CPU utilization for 10+ minutes
- **GPU High Utilization**: >95% GPU utilization for 15+ minutes

### Configuration
```yaml
# Alert rules are defined in:
# k8s/monitoring/prometheus-config.yaml

# Example alert rule:
- alert: APIHighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "API error rate is {{ $value | humanizePercentage }}"
```

## 📊 Structured Logging

### Log Configuration
- **Format**: Structured JSON with consistent fields
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context**: Request ID, user ID, job ID when available
- **Destinations**: Console + Google Cloud Logging

### Log Structure
```json
{
  "timestamp": "2025-01-20T18:00:00Z",
  "level": "INFO",
  "logger": "services.gpu_worker_service",
  "message": "Job completed successfully",
  "service": {
    "name": "omtx-hub-api",
    "version": "1.0.0",
    "environment": "production"
  },
  "request_id": "req-12345",
  "user_id": "user-67890",
  "job_id": "job-abcdef",
  "performance": {
    "duration_ms": 1250,
    "operation": "job_execution"
  }
}
```

### Usage Examples
```python
from services.logging_service import RequestLoggingContext, JobLoggingContext

# Request-scoped logging
with RequestLoggingContext("req-12345", "user-67890"):
    # All logs in this context include request_id and user_id
    logger.info("Processing API request")

# Job-scoped logging
with JobLoggingContext("job-abc", "user-123", "boltz2"):
    # All logs include job context
    logger.info("Starting job execution")
```

## 🔧 Monitoring Service Features

### Real-time Metrics Collection
- **System metrics** updated every 60 seconds
- **Job health monitoring** every 5 minutes
- **API health checks** every 30 seconds
- **Storage and resource monitoring**

### Intelligent Alerting
- **Alert state tracking** with cooldown periods
- **Multi-channel notifications** (logs, metrics, external)
- **Alert correlation** and **noise reduction**
- **Automatic recovery detection**

### Historical Data
- **Metrics retention**: 15 days in Prometheus
- **Log retention**: 30 days configurable
- **Trend analysis** and **capacity planning**
- **Performance baseline** tracking

## 🎯 Best Practices

### Metrics Naming
- Use consistent prefixes: `omtx_hub_*`
- Include units in names: `*_seconds`, `*_bytes`, `*_total`
- Use labels for dimensions: `{job_type="boltz2", status="completed"}`

### Alert Management
- Define clear **severity levels** (critical, warning, info)
- Set appropriate **evaluation periods** to avoid flapping
- Include **actionable descriptions** in alerts
- Test alert rules before production deployment

### Dashboard Design
- **Group related metrics** on the same panel
- Use **consistent time ranges** across dashboards
- Include **target lines** and **SLA indicators**
- Optimize for **readability** at different screen sizes

### Performance Optimization
- Use **recording rules** for expensive queries
- Implement **metric sampling** for high-cardinality data
- **Cache dashboard** data where appropriate
- **Monitor monitoring** - track Prometheus resource usage

## 🔍 Troubleshooting

### Common Issues

#### Prometheus Not Scraping
```bash
# Check Prometheus targets
curl http://<prometheus-ip>:9090/api/v1/targets

# Verify service annotations
kubectl get service omtx-hub-api -o yaml | grep prometheus

# Check network policies
kubectl get networkpolicies -n monitoring
```

#### Grafana Dashboard Issues
```bash
# Check Grafana logs
kubectl logs deployment/grafana -n monitoring

# Verify data source
curl -u admin:omtx-hub-grafana-admin \
  http://<grafana-ip>:3000/api/datasources

# Test Prometheus connection
kubectl exec -it deployment/grafana -n monitoring -- \
  curl http://prometheus:9090/api/v1/query?query=up
```

#### Missing Metrics
```bash
# Check application logs
kubectl logs deployment/omtx-hub-api

# Verify metrics endpoint
curl http://<api-ip>/metrics

# Check Prometheus configuration
kubectl get configmap prometheus-config -n monitoring -o yaml
```

### Log Analysis Queries

#### Google Cloud Logging
```sql
-- High error rate detection
resource.type="k8s_container"
resource.labels.cluster_name="omtx-hub-cluster"
severity >= ERROR
timestamp >= "2025-01-20T17:00:00Z"

-- Job processing analysis
jsonPayload.job_id != ""
jsonPayload.performance.duration_ms > 5000
timestamp >= "2025-01-20T17:00:00Z"

-- Authentication events
jsonPayload.auth_event != ""
jsonPayload.success = false
timestamp >= "2025-01-20T17:00:00Z"
```

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Google Cloud Monitoring](https://cloud.google.com/monitoring/docs)
- [Kubernetes Monitoring Best Practices](https://kubernetes.io/docs/concepts/cluster-administration/monitoring/)

## 🚀 Next Steps

1. **Deploy monitoring stack** using provided scripts
2. **Configure external alerting** (PagerDuty, Slack, email)
3. **Create custom dashboards** for specific use cases
4. **Set up log-based alerts** in Google Cloud Monitoring
5. **Implement capacity planning** based on trend analysis
6. **Train team members** on monitoring tools and procedures