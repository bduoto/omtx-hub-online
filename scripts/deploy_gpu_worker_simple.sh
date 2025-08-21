#!/bin/bash
# Deploy GPU Worker Service (Simple version for testing)

set -e

echo "🚀 Deploying GPU Worker Service (Simple)"
echo "========================================"
echo

# Configuration
PROJECT_ID="om-models"
SERVICE_NAME="gpu-worker"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
SERVICE_ACCOUNT="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "📦 Step 1: Building Simple GPU Worker Image"
echo "--------------------------------------------"

cd gpu_worker

# Build with simple Dockerfile for AMD64 platform (Cloud Run requirement)
docker build --platform linux/amd64 -f Dockerfile.simple -t ${IMAGE_NAME}:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built successfully${NC}"

echo
echo "📤 Step 2: Pushing to Container Registry"
echo "----------------------------------------"

# Configure Docker for GCR
gcloud auth configure-docker --quiet

# Push image
docker push ${IMAGE_NAME}:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Image push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image pushed to GCR${NC}"

echo
echo "☁️ Step 3: Deploying as Cloud Run Service (for testing)"
echo "-------------------------------------------------------"

# Deploy as Cloud Run Service first (easier to test)
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
    --set-env-vars GCS_BUCKET_NAME=hub-job-files \
    --set-env-vars ENVIRONMENT=production \
    --memory 4Gi \
    --cpu 2 \
    --timeout 30m \
    --max-instances 10 \
    --min-instances 0 \
    --allow-unauthenticated \
    --port 8080 \
    --execution-environment gen2

echo -e "${GREEN}✅ Cloud Run Service deployed${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo
echo "🧪 Step 4: Testing GPU Worker"
echo "-----------------------------"

echo "Testing health endpoint..."
curl -s ${SERVICE_URL}/health | python3 -m json.tool || echo "Health check failed"

echo
echo -e "${GREEN}🎉 GPU Worker Service Deployment Complete!${NC}"
echo
echo "Service Details:"
echo "  Name: ${SERVICE_NAME}"
echo "  URL: ${SERVICE_URL}"
echo "  Region: ${REGION}"
echo "  Image: ${IMAGE_NAME}:latest"
echo "  Memory: 4GB"
echo "  CPU: 2 cores"
echo
echo "Next steps:"
echo "  1. Test job processing: curl -X POST ${SERVICE_URL}/process -H 'Content-Type: application/json' -d '{\"job_id\":\"test123\"}'"
echo "  2. Update GPU_WORKER_URL in your GKE API: ${SERVICE_URL}"
echo "  3. Later: Convert to Cloud Run Job with GPU support"

cd ..