# OMTX-Hub Backend Deployment Guide

## Environment Variables

### Required Configuration

```bash
# GCP Project Configuration
GOOGLE_CLOUD_PROJECT=om-models
GCP_REGION=us-central1
GCP_BUCKET_NAME=hub-job-files

# Service URLs
GPU_WORKER_URL=https://boltz2-production-zhye5az7za-uc.a.run.app

# Cloud Tasks Configuration
CLOUD_TASKS_LOCATION=us-central1

# Optional Configuration
ENVIRONMENT=production  # or 'development'
JWT_SECRET_KEY=your-secret-key-here  # Optional for dev/testing
ENABLE_JOB_MONITORING=false  # Set to 'true' to enable background monitoring
ENABLE_SYSTEM_MONITORING=false  # Set to 'true' to enable system monitoring
```

### Legacy Environment Variables (Deprecated)

These are still supported for backward compatibility but should be migrated:

```bash
# Deprecated - use GOOGLE_CLOUD_PROJECT instead
GCP_PROJECT_ID=om-models

# Deprecated - use GCP_BUCKET_NAME instead  
GCS_BUCKET_NAME=hub-job-files
```

## Cloud Run Deployment

### 1. Build and Deploy Main API

```bash
# Build the main API service
gcloud builds submit --config=backend/cloudbuild.yaml .

# Deploy to Cloud Run
gcloud run deploy omtx-hub-native \
  --image=gcr.io/om-models/omtx-hub-native:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=om-models,GCP_REGION=us-central1,GCP_BUCKET_NAME=hub-job-files,ENVIRONMENT=production"
```

### 2. Deploy GPU Worker Service

```bash
# Deploy GPU worker (requires L4 GPU)
gcloud run deploy boltz2-production \
  --image=gcr.io/om-models/boltz2-gpu-worker:latest \
  --platform=managed \
  --region=us-central1 \
  --no-allow-unauthenticated \
  --port=8080 \
  --memory=8Gi \
  --cpu=4 \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --max-instances=5 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=om-models,GCP_BUCKET_NAME=hub-job-files,ENVIRONMENT=production"
```

## Cloud Tasks Setup

### 1. Create Queues

```bash
# Create individual job queue
gcloud tasks queues create boltz2-predictions \
  --location=us-central1 \
  --max-dispatches-per-second=10 \
  --max-concurrent-dispatches=100

# Create batch job queue  
gcloud tasks queues create boltz2-batch-predictions \
  --location=us-central1 \
  --max-dispatches-per-second=20 \
  --max-concurrent-dispatches=200
```

### 2. IAM Configuration

```bash
# Create Cloud Tasks service account
gcloud iam service-accounts create cloud-tasks-service \
  --display-name="Cloud Tasks Service Account"

# Grant Cloud Tasks permission to invoke GPU worker
gcloud run services add-iam-policy-binding boltz2-production \
  --member="serviceAccount:cloud-tasks-service@om-models.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1

# Grant Cloud Tasks permission to create tasks
gcloud projects add-iam-policy-binding om-models \
  --member="serviceAccount:cloud-tasks-service@om-models.iam.gserviceaccount.com" \
  --role="roles/cloudtasks.enqueuer"
```

## Firestore Setup

### 1. Enable Firestore

```bash
# Enable Firestore in Native mode
gcloud firestore databases create --region=us-central1
```

### 2. Create Indexes

```bash
# Create composite indexes for efficient queries
gcloud firestore indexes composite create \
  --collection-group=jobs \
  --field-config=field-path=user_id,order=ascending \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=created_at,order=descending

gcloud firestore indexes composite create \
  --collection-group=jobs \
  --field-config=field-path=batch_parent_id,order=ascending \
  --field-config=field-path=batch_index,order=ascending
```

## GCS Bucket Setup

```bash
# Create bucket for job files
gsutil mb -p om-models -c STANDARD -l us-central1 gs://hub-job-files

# Set bucket permissions
gsutil iam ch serviceAccount:cloud-tasks-service@om-models.iam.gserviceaccount.com:objectAdmin gs://hub-job-files
```

## Monitoring and Logging

### Health Check Endpoints

- Main API: `https://omtx-hub-native-338254269321.us-central1.run.app/health`
- GPU Worker: `https://boltz2-production-zhye5az7za-uc.a.run.app/health`

### Key Metrics to Monitor

- Cloud Run request latency and error rates
- Cloud Tasks queue depth and processing rate
- Firestore read/write operations
- GCS storage usage and transfer rates
- GPU utilization on worker instances

### Log Correlation

All services log with structured JSON including:
- `job_id`: For tracing individual jobs
- `batch_id`: For tracing batch operations  
- `user_id`: For user-specific debugging
- `service`: Service name for filtering

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure Cloud Tasks service account has proper IAM roles
2. **Queue Backlog**: Monitor queue depth and scale GPU workers if needed
3. **Storage Errors**: Check GCS bucket permissions and quotas
4. **Memory Issues**: GPU workers may need more memory for large proteins

### Debug Commands

```bash
# Check Cloud Tasks queue status
gcloud tasks queues describe boltz2-predictions --location=us-central1

# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=omtx-hub-native" --limit=50

# Check Firestore usage
gcloud firestore operations list
```

## Security Considerations

- GPU worker service is not publicly accessible (no-allow-unauthenticated)
- OIDC tokens used for Cloud Tasks → GPU worker authentication
- User data isolated in GCS under users/{user_id}/ paths
- Firestore security rules should restrict access by user_id
- JWT tokens optional and only for development/testing

## Scaling Configuration

### Auto-scaling Settings

- Main API: 0-10 instances, scales on CPU/memory
- GPU Worker: 0-5 instances, scales on request volume
- Cloud Tasks: Configured for burst capacity

### Resource Limits

- Main API: 2 CPU, 2Gi memory per instance
- GPU Worker: 4 CPU, 8Gi memory, 1x L4 GPU per instance
- Firestore: 50K reads/writes per second limit
- GCS: No specific limits, pay-per-use
