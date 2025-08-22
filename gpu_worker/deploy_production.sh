#!/bin/bash

# Deploy Production Boltz-2 GPU Worker
# Simplified deployment for Cloud Run Service (HTTP endpoint)

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="boltz2-gpu-worker"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:production"

echo "🚀 Deploying Production Boltz-2 GPU Worker"
echo "   Project: ${PROJECT_ID}"
echo "   Region: ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo "   Image: ${IMAGE_NAME}"
echo ""

# Step 1: Check if image is built
echo "📦 Checking Docker image..."
if docker images | grep -q "${SERVICE_NAME}.*production"; then
    echo "✅ Image found locally"
else
    echo "❌ Image not found. Building now..."
    docker build --platform linux/amd64 -f Dockerfile.production -t ${IMAGE_NAME} .
fi

# Step 2: Push to Google Container Registry
echo ""
echo "📤 Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Step 3: Create service account if it doesn't exist
echo ""
echo "👤 Setting up service account..."
SERVICE_ACCOUNT="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT} --project=${PROJECT_ID} &>/dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create ${SERVICE_NAME} \
        --display-name="Boltz-2 GPU Worker Service" \
        --project=${PROJECT_ID}
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/storage.objectViewer"
    
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/datastore.user"
    
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/storage.objectCreator"
else
    echo "Service account already exists"
fi

# Step 4: Deploy Cloud Run Service
echo ""
echo "☁️ Deploying Cloud Run Service..."

gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --platform=managed \
    --memory=4Gi \
    --cpu=2 \
    --timeout=1800 \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=1 \
    --port=8080 \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="GCS_BUCKET_NAME=hub-job-files" \
    --set-env-vars="GPU_TYPE=CPU" \
    --set-env-vars="BOLTZ_CACHE=/app/.boltz_cache" \
    --set-env-vars="ENVIRONMENT=production" \
    --service-account="${SERVICE_ACCOUNT}"

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
echo "   Service Name: ${SERVICE_NAME}"
echo "   Region: ${REGION}"
echo "   Project: ${PROJECT_ID}"
echo ""
echo "🧪 Test Commands:"
echo "   # Health check"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo "   # Test prediction (will use mock if weights not downloaded)"
echo "   curl -X POST ${SERVICE_URL}/process \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"job_id\": \"test-123\", \"job_type\": \"INDIVIDUAL\"}'"
echo ""
echo "📝 Backend Configuration:"
echo "   Add to backend/.env:"
echo "   GPU_WORKER_URL=${SERVICE_URL}"
echo ""
echo "⚠️ Important Notes:"
echo "   1. First prediction will download ~400MB weights (one-time)"
echo "   2. Using CPU mode - for GPU, deploy on GKE with GPU nodes"
echo "   3. Cloud Tasks should point to ${SERVICE_URL}/process"
echo "   4. Monitor costs and scale as needed"