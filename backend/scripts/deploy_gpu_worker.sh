#!/bin/bash

# Deploy GPU Worker Service to Cloud Run
# This script builds and deploys the GPU worker service with L4 GPU support

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="gpu-worker-service"
IMAGE_NAME="gpu-worker"
IMAGE_TAG="latest"
FULL_IMAGE="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "🚀 Deploying GPU Worker Service to Cloud Run"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo "   Image: ${FULL_IMAGE}"

# Step 1: Build Docker image
echo ""
echo "📦 Building Docker image..."
docker build -f gpu_worker.Dockerfile -t ${FULL_IMAGE} .

# Step 2: Push to Google Container Registry
echo ""
echo "📤 Pushing image to GCR..."
docker push ${FULL_IMAGE}

# Step 3: Deploy to Cloud Run with GPU
echo ""
echo "🎮 Deploying to Cloud Run with L4 GPU..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${FULL_IMAGE} \
  --platform managed \
  --region ${REGION} \
  --no-allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --timeout 3600 \
  --max-instances 10 \
  --min-instances 0 \
  --service-account gpu-worker@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},GCS_BUCKET_NAME=hub-job-files,ENVIRONMENT=production" \
  --project ${PROJECT_ID}

# Step 4: Get service URL
echo ""
echo "📍 Getting service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo ""
echo "✅ GPU Worker Service deployed successfully!"
echo "   Service URL: ${SERVICE_URL}"
echo ""
echo "📝 Update the GPU_WORKER_URL environment variable:"
echo "   export GPU_WORKER_URL=${SERVICE_URL}"
echo ""
echo "🔧 To test the service:"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo "🔐 Note: The service requires authentication. Use gcloud auth or service account."