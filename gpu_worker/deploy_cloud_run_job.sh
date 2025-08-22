#!/bin/bash

# Deploy Boltz-2 GPU Worker to Cloud Run Jobs
# This script builds and deploys the production GPU worker

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="boltz2-gpu-worker"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
JOB_NAME="boltz2-processor"

echo "🚀 Deploying Boltz-2 GPU Worker to Cloud Run Jobs"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo "   Image: ${IMAGE_NAME}"
echo ""

# Step 1: Build the GPU-enabled Docker image
echo "📦 Building GPU-enabled Docker image..."
docker build \
    --platform linux/amd64 \
    -f Dockerfile.gpu \
    -t ${IMAGE_NAME} \
    .

# Step 2: Push to Google Container Registry
echo "📤 Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Step 3: Create or update Cloud Run Job
echo "☁️ Deploying Cloud Run Job..."

# Check if job exists
if gcloud run jobs describe ${JOB_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} &>/dev/null; then
    echo "Updating existing job..."
    
    gcloud run jobs update ${JOB_NAME} \
        --image=${IMAGE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --memory=8Gi \
        --cpu=4 \
        --task-timeout=30m \
        --max-retries=2 \
        --parallelism=1 \
        --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
        --set-env-vars="GCS_BUCKET_NAME=hub-job-files" \
        --set-env-vars="GPU_TYPE=L4" \
        --set-env-vars="MODEL_DIR=/models/boltz" \
        --set-env-vars="ENVIRONMENT=production" \
        --service-account="boltz2-gpu-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --cpu-boost
else
    echo "Creating new job..."
    
    gcloud run jobs create ${JOB_NAME} \
        --image=${IMAGE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --memory=8Gi \
        --cpu=4 \
        --task-timeout=30m \
        --max-retries=2 \
        --parallelism=1 \
        --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
        --set-env-vars="GCS_BUCKET_NAME=hub-job-files" \
        --set-env-vars="GPU_TYPE=L4" \
        --set-env-vars="MODEL_DIR=/models/boltz" \
        --set-env-vars="ENVIRONMENT=production" \
        --service-account="boltz2-gpu-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --cpu-boost
fi

# Step 4: Create Cloud Run Service for HTTP endpoint (called by Cloud Tasks)
echo "🌐 Deploying Cloud Run Service for HTTP endpoint..."

gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --platform=managed \
    --memory=8Gi \
    --cpu=4 \
    --timeout=1800 \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=1 \
    --port=8080 \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="GCS_BUCKET_NAME=hub-job-files" \
    --set-env-vars="GPU_TYPE=L4" \
    --set-env-vars="MODEL_DIR=/models/boltz" \
    --set-env-vars="ENVIRONMENT=production" \
    --service-account="boltz2-gpu-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --cpu-boost

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --format="value(status.url)")

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📍 Service Information:"
echo "   Service URL: ${SERVICE_URL}"
echo "   Job Name: ${JOB_NAME}"
echo "   Region: ${REGION}"
echo ""
echo "🧪 Test Commands:"
echo "   Health check: curl ${SERVICE_URL}/health"
echo "   Run job: gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "📝 Update backend configuration:"
echo "   Set GPU_WORKER_URL=${SERVICE_URL} in backend/.env"
echo ""
echo "⚠️ Important Notes:"
echo "   1. Ensure the service account has necessary permissions"
echo "   2. Model weights should be mounted or downloaded at runtime"
echo "   3. Cloud Tasks should point to ${SERVICE_URL}/process"
echo "   4. Monitor costs - L4 GPUs are $0.65/hour when running"