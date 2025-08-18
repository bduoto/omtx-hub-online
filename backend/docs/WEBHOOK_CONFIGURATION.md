# Modal Webhook Configuration Guide

This guide explains how to configure Modal apps to send webhook notifications to OMTX-Hub for real-time job completion processing.

## 🎯 Overview

**Problem**: Polling Modal for job completion introduces latency and resource waste.

**Solution**: Configure Modal apps to send webhooks to OMTX-Hub endpoints when jobs complete, enabling real-time processing with zero latency.

## 🏗️ Architecture

```
Modal Function Execution
         ↓
    Job Completes
         ↓
   Webhook Triggered  →  OMTX-Hub Webhook Endpoint
         ↓                        ↓
  HMAC Verification       Background Processing
         ↓                        ↓
   Payload Validated       Update Job Status
         ↓                        ↓
  Process Completion      Store Results to GCP
         ↓                        ↓
   Update Database        Trigger Batch Logic
```

## 🔧 Configuration Steps

### 1. Environment Setup

Set the required environment variables:

```bash
# Production webhook URL
export WEBHOOK_BASE_URL="https://api.omtx-hub.com"

# Webhook security secret (generate with: openssl rand -base64 32)
export MODAL_WEBHOOK_SECRET="your-webhook-secret-here"

# Optional: Dry run mode for testing
export DRY_RUN="false"
```

### 2. Kubernetes Secret Configuration

Add webhook configuration to your Kubernetes secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: omtx-hub-secrets
  namespace: omtx-hub
stringData:
  WEBHOOK_BASE_URL: "https://api.omtx-hub.com"
  MODAL_WEBHOOK_SECRET: "your-webhook-secret-here"
```

### 3. Modal App Configuration

#### Automatic Configuration (Recommended)

Use the configuration script:

```bash
cd backend/scripts
python configure_modal_webhooks.py
```

#### Manual Configuration via API

```bash
curl -X POST "https://api.omtx-hub.com/api/v3/webhooks/configure" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_base_url": "https://api.omtx-hub.com",
    "webhook_secret": "your-webhook-secret",
    "auto_configure": true
  }'
```

#### Programmatic Configuration

```python
from services.production_modal_service import production_modal_service

# Configure webhooks for all Modal apps
success = await production_modal_service.configure_webhooks(
    webhook_base_url="https://api.omtx-hub.com",
    webhook_secret="your-webhook-secret"
)

if success:
    print("✅ All webhooks configured successfully")
else:
    print("❌ Some webhook configurations failed")
```

### 4. Modal App Code Integration

#### Update Modal Functions

Add webhook configuration to your Modal apps:

```python
# In your Modal app file (e.g., boltz2_persistent_app.py)

@app.function(
    # ... existing configuration ...
    webhook_config={
        "url": "https://api.omtx-hub.com/api/v3/webhooks/modal/completion",
        "events": ["function.success", "function.failure", "function.timeout"],
        "secret": os.getenv("MODAL_WEBHOOK_SECRET"),
        "retry_policy": {
            "max_retries": 3,
            "backoff": "exponential"
        }
    }
)
def boltz2_predict_modal(/* ... parameters ... */):
    # Your function implementation
    pass
```

#### Webhook Payload Format

Modal will send webhooks with this structure:

```json
{
  "call_id": "call-123456789",
  "status": "success",
  "result": {
    "affinity": 0.6385,
    "confidence": 0.5071,
    "ptm_score": 0.5423,
    "iptm_score": 0.8717,
    "plddt_score": 0.4159,
    "structure_file_base64": "...",
    "execution_time": 205.3
  },
  "metadata": {
    "job_id": "job-abc123",
    "batch_id": "batch-xyz789",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## 🔒 Security

### HMAC Verification

All webhooks are secured with HMAC-SHA256 signatures:

```python
# Webhook signature verification
def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    expected_mac = hmac.new(
        MODAL_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    
    signature = signature_header.split('=', 1)[1]
    return hmac.compare_digest(expected_mac, signature)
```

### Timestamp Verification

Webhooks include timestamps to prevent replay attacks:

```python
# Verify webhook timestamp (5-minute window)
def verify_timestamp(timestamp_header: str) -> bool:
    webhook_time = int(timestamp_header)
    current_time = int(time.time())
    return abs(current_time - webhook_time) <= 300
```

### Headers

Required webhook headers:

- `X-Modal-Signature`: HMAC signature (format: `sha256=<hex>`)
- `X-Modal-Timestamp`: Unix timestamp
- `Content-Type`: application/json
- `User-Agent`: Modal-Webhook/1.0

## 🧪 Testing

### Health Check

Test webhook endpoint availability:

```bash
curl https://api.omtx-hub.com/api/v3/webhooks/modal/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "modal_webhook_handler",
  "features": {
    "hmac_verification": true,
    "timestamp_verification": true,
    "background_processing": true,
    "batch_intelligence": true
  }
}
```

### Test Webhook Delivery

```bash
curl -X POST "https://api.omtx-hub.com/api/v3/webhooks/modal/test" \
  -H "Content-Type: application/json" \
  -d '{
    "modal_call_id": "test_123",
    "status": "success",
    "test_data": {"test": true}
  }'
```

### Webhook Status Check

```bash
curl https://api.omtx-hub.com/api/v3/webhooks/status
```

Expected response:
```json
{
  "configured": true,
  "base_url": "https://api.omtx-hub.com",
  "apps_configured": 3,
  "total_apps": 3,
  "health_status": "healthy"
}
```

## 📊 Monitoring

### Active Executions

Monitor currently running Modal jobs:

```bash
curl https://api.omtx-hub.com/api/v3/webhooks/active-executions
```

### Webhook Metrics

Get webhook processing metrics:

```bash
curl https://api.omtx-hub.com/api/v3/webhooks/metrics
```

### Cancel Execution

Cancel a running Modal execution:

```bash
curl -X POST "https://api.omtx-hub.com/api/v3/webhooks/executions/call-123/cancel"
```

## 🚨 Troubleshooting

### Common Issues

**1. Webhook Endpoint Not Reachable**
```bash
# Check endpoint accessibility
curl -I https://api.omtx-hub.com/api/v3/webhooks/modal/health

# Check DNS resolution
nslookup api.omtx-hub.com

# Check firewall rules
kubectl get ingress -n omtx-hub
```

**2. HMAC Verification Failures**
```bash
# Check secret configuration
kubectl get secret omtx-hub-secrets -n omtx-hub -o yaml

# Verify secret matches across Modal and OMTX-Hub
echo $MODAL_WEBHOOK_SECRET | base64
```

**3. Webhook Timeouts**
```bash
# Check webhook processing logs
kubectl logs -f deployment/omtx-hub-backend -n omtx-hub | grep webhook

# Check background task processing
kubectl describe pod -l app=omtx-hub-backend -n omtx-hub
```

**4. Modal Function Configuration**
```bash
# Verify Modal app deployment
modal app list

# Check function status
modal function list omtx-boltz2-persistent

# Test Modal function directly
modal run omtx-boltz2-persistent::boltz2_predict_modal --help
```

### Debugging Commands

**Check webhook configuration status:**
```python
from services.production_modal_service import production_modal_service

# Get current configuration
metrics = await production_modal_service.get_metrics()
print(f"Active executions: {metrics['total_active']}")

# List active executions
executions = await production_modal_service.list_active_executions()
for exec in executions:
    print(f"Job {exec.job_id}: {exec.modal_call_id}")
```

**Manual webhook processing:**
```python
from api.webhook_handlers import _process_completion_background

# Manually process a completion
await _process_completion_background(
    modal_call_id="test_123",
    status="success",
    result_data={"test": True},
    error_data={},
    metadata={}
)
```

## 🔄 Migration from Polling

### Phase 1: Dual Mode (Recommended)
- Keep existing polling system active
- Add webhook configuration
- Monitor webhook delivery success
- Gradually increase webhook confidence

### Phase 2: Webhook Primary
- Set webhook as primary completion method
- Use polling as fallback for failed webhooks
- Monitor for missed completions

### Phase 3: Webhook Only
- Disable polling system
- Full webhook-based completion processing
- Monitor performance improvements

### Performance Benefits

**Before (Polling):**
- Completion latency: 30-60 seconds
- Resource usage: Continuous polling overhead
- Scalability: Limited by polling frequency

**After (Webhooks):**
- Completion latency: <5 seconds
- Resource usage: Event-driven processing only
- Scalability: Handles unlimited concurrent jobs

## 📋 Deployment Checklist

- [ ] Set environment variables (`WEBHOOK_BASE_URL`, `MODAL_WEBHOOK_SECRET`)
- [ ] Update Kubernetes secrets
- [ ] Deploy OMTX-Hub backend with webhook endpoints
- [ ] Configure Modal apps with webhook URLs
- [ ] Test webhook delivery end-to-end
- [ ] Monitor webhook processing logs
- [ ] Verify job completion latency improvements
- [ ] Set up webhook monitoring and alerting
- [ ] Document webhook failure recovery procedures
- [ ] Train team on webhook troubleshooting

## 🔗 Related Documentation

- [Production Modal Service](../services/production_modal_service.py)
- [Webhook Handlers](../api/webhook_handlers.py)
- [Webhook Management API](../api/webhook_management.py)
- [Kubernetes Deployment Guide](../../infrastructure/k8s/README.md)
- [Security Best Practices](../docs/SECURITY.md)