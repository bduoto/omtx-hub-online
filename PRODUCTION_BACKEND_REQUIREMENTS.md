# Production Backend Requirements Checklist

## 🚨 Critical Missing Components for Full End-to-End Backend

### 1. **Python Dependencies** 🔴 CRITICAL
Missing packages that will cause import failures:
```txt
# Add to requirements.txt
aiohttp>=3.8.0              # For webhook service
PyJWT>=2.8.0                # For JWT authentication
passlib>=1.7.4              # For password hashing (if using auth)
python-jose[cryptography]>=3.3.0  # For JWT token handling
httpx>=0.24.0               # For async HTTP client
asyncpg>=0.27.0             # For async PostgreSQL (if using)
aiocache>=0.12.0            # For async caching
croniter>=1.3.0             # For cron job scheduling
tenacity>=8.2.0             # For retry logic
structlog>=23.1.0           # For structured logging
sentry-sdk>=1.40.0          # For error tracking
```

### 2. **Import Path Issues** 🔴 CRITICAL
Files with relative imports that need fixing:
- `api/async_prediction_api.py`: Change `from ..services` to `from services`
- Check all files in `/api/` folder for relative imports
- Check all files in `/services/` folder for circular imports
- Ensure all imports work from `/app/` root in container

### 3. **Environment Variables** 🔴 CRITICAL
Required environment variables not set:
```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=om-models
GCP_PROJECT_ID=om-models
GCP_BUCKET_NAME=hub-job-files
FIRESTORE_DATABASE=(default)

# Cloud Tasks
CLOUD_TASKS_QUEUE=gpu-jobs-queue
CLOUD_TASKS_LOCATION=us-central1
CLOUD_RUN_JOB_NAME=boltz2-processor
CLOUD_RUN_JOB_REGION=us-central1

# Service URLs
CLOUD_RUN_SERVICE_URL=https://omtx-hub-backend-xxx.run.app
GPU_WORKER_URL=https://gpu-worker-xxx.run.app

# Redis (if using caching)
REDIS_HOST=redis-instance-ip
REDIS_PORT=6379
REDIS_PASSWORD=your-password

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# Monitoring
ENABLE_JOB_MONITORING=false
ENABLE_SYSTEM_MONITORING=false
ENABLE_METRICS=false

# Feature Flags
ENABLE_RATE_LIMITING=true
ENABLE_CACHING=false
ENABLE_WEBHOOKS=false
USE_CLOUD_TASKS=true
USE_CLOUD_RUN_JOBS=true
```

### 4. **Google Cloud IAM Permissions** 🔴 CRITICAL
Service account needs these roles:
```bash
# Required IAM roles for omtx-hub-service@om-models.iam.gserviceaccount.com
roles/cloudstorage.admin           # For GCS bucket operations
roles/firestore.dataEditor         # For Firestore read/write
roles/cloudtasks.enqueuer          # For Cloud Tasks queue operations
roles/run.invoker                  # For invoking Cloud Run services
roles/run.developer                # For Cloud Run Jobs
roles/logging.logWriter            # For Cloud Logging
roles/monitoring.metricWriter      # For Cloud Monitoring
roles/secretmanager.secretAccessor # For Secret Manager (if using)
```

### 5. **Cloud Tasks Setup** 🟡 IMPORTANT
```bash
# Create queues if not exists
gcloud tasks queues create gpu-jobs-queue \
  --location=us-central1 \
  --max-concurrent-dispatches=10 \
  --max-attempts=3

gcloud tasks queues create batch-jobs-queue \
  --location=us-central1 \
  --max-concurrent-dispatches=5 \
  --max-attempts=3
```

### 6. **Firestore Indexes** 🟡 IMPORTANT
```json
// firestore.indexes.json
{
  "indexes": [
    {
      "collectionGroup": "jobs",
      "fields": [
        {"fieldPath": "user_id", "mode": "ASCENDING"},
        {"fieldPath": "created_at", "mode": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "jobs",
      "fields": [
        {"fieldPath": "status", "mode": "ASCENDING"},
        {"fieldPath": "created_at", "mode": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "jobs",
      "fields": [
        {"fieldPath": "batch_parent_id", "mode": "ASCENDING"},
        {"fieldPath": "created_at", "mode": "ASCENDING"}
      ]
    }
  ]
}
```

### 7. **Cloud Storage Bucket Configuration** 🟡 IMPORTANT
```bash
# Set CORS for frontend access
gsutil cors set cors.json gs://hub-job-files

# cors.json:
[
  {
    "origin": ["http://localhost:3000", "http://localhost:8080", "https://your-frontend.com"],
    "method": ["GET", "POST", "PUT", "DELETE"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
```

### 8. **Database Connection Issues** 🔴 CRITICAL
- `database/unified_job_manager.py` needs proper Firestore initialization
- Add connection retry logic
- Add connection pooling for PostgreSQL (if using)
- Fix async/sync context issues

### 9. **GPU Worker Integration** 🔴 CRITICAL
- Fix `services/gpu_worker_service.py` Cloud Tasks integration
- Ensure proper job status updates in Firestore
- Add proper error handling and retry logic
- Fix authentication between services

### 10. **Missing Service Implementations** 🟡 IMPORTANT
Services that may not be fully implemented:
- `services/batch_monitor_service.py` - Needs Cloud Tasks integration
- `services/cloud_tasks_service.py` - Needs proper queue configuration
- `services/webhook_service.py` - Needs endpoint configuration
- `services/redis_cache_service.py` - Needs Redis connection

### 11. **API Endpoint Issues** 🔴 CRITICAL
- Fix all v1/v2/v3 version conflicts
- Ensure all endpoints return proper status codes
- Add proper error handling middleware
- Fix CORS for production domains

### 12. **Docker Configuration** 🟡 IMPORTANT
```dockerfile
# Optimized Dockerfile.cloud_run_native
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/
COPY gpu_worker/boltz2_predictor.py /app/

# Set Python path
ENV PYTHONPATH=/app

# Create required directories
RUN mkdir -p logs /tmp/uploads /tmp/results

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
```

### 13. **Simple Cloud Build Configuration** 🟢 READY
```yaml
# cloudbuild-simple.yaml
steps:
  # Build image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/omtx-hub-backend:$SHORT_SHA', '-f', 'backend/Dockerfile.cloud_run_native', '.']
  
  # Push image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/omtx-hub-backend:$SHORT_SHA']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'omtx-hub-backend'
      - '--image=gcr.io/$PROJECT_ID/omtx-hub-backend:$SHORT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--port=8080'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--timeout=300'
      - '--concurrency=100'
      - '--max-instances=10'
      - '--service-account=omtx-hub-service@$PROJECT_ID.iam.gserviceaccount.com'

timeout: '600s'
images: ['gcr.io/$PROJECT_ID/omtx-hub-backend:$SHORT_SHA']
```

### 14. **Deployment Script** 🟢 READY
```bash
#!/bin/bash
# deploy-production.sh

set -e

echo "🚀 Deploying OMTX-Hub Backend to Production"

# Set variables
PROJECT_ID="om-models"
SERVICE_NAME="omtx-hub-backend"
REGION="us-central1"

# Build and deploy
gcloud builds submit \
  --config=cloudbuild-simple.yaml \
  --substitutions=_PROJECT_ID=${PROJECT_ID},SHORT_SHA=$(git rev-parse --short HEAD)

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --format="value(status.url)")

echo "✅ Deployment complete!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "📊 View logs: gcloud run services logs read ${SERVICE_NAME} --region=${REGION}"
```

## 🎯 Priority Order for Fixes

### Phase 1: Critical Foundation (Must fix first)
1. ✅ Fix all Python dependencies
2. ✅ Fix all import paths
3. ✅ Set up environment variables
4. ✅ Configure service account IAM

### Phase 2: Core Services
5. ✅ Fix database connections
6. ✅ Set up Cloud Tasks queues
7. ✅ Configure Firestore indexes
8. ✅ Fix GPU worker integration

### Phase 3: Production Ready
9. ✅ Set up GCS bucket CORS
10. ✅ Implement health checks
11. ✅ Add monitoring/logging
12. ✅ Test end-to-end flows

### Phase 4: Optimization
13. ✅ Add caching layer
14. ✅ Implement rate limiting
15. ✅ Add webhook support
16. ✅ Performance tuning

## 🔥 Quick Start Commands

```bash
# 1. Fix dependencies
cd backend
echo "aiohttp>=3.8.0
PyJWT>=2.8.0
python-jose[cryptography]>=3.3.0
httpx>=0.24.0
tenacity>=8.2.0" >> requirements.txt

# 2. Set environment variables
export GOOGLE_CLOUD_PROJECT=om-models
export GCP_BUCKET_NAME=hub-job-files
export CLOUD_TASKS_QUEUE=gpu-jobs-queue
export CLOUD_RUN_SERVICE_URL=https://omtx-hub-backend-xxx.run.app

# 3. Deploy
chmod +x deploy-production.sh
./deploy-production.sh

# 4. Test
curl https://omtx-hub-backend-xxx.run.app/health
```

## ⚠️ Current Blockers

1. **Import Errors**: Multiple services have incorrect import paths
2. **Missing Dependencies**: Several Python packages not installed
3. **No Credentials**: Service account not configured with proper permissions
4. **Queue Not Created**: Cloud Tasks queues don't exist
5. **Database Not Initialized**: Firestore connection not properly configured

## ✅ Success Criteria

- [ ] Backend starts without import errors
- [ ] Health check endpoint returns 200
- [ ] Can submit individual job via API
- [ ] Can submit batch job via API
- [ ] Jobs are processed by GPU worker
- [ ] Results stored in GCS
- [ ] Job status updated in Firestore
- [ ] Results retrievable via API
- [ ] Frontend can display results
- [ ] No errors in Cloud Run logs