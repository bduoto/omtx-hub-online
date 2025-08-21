#!/bin/bash
# Deploy GPU Worker as Cloud Run Service (for HTTP accessibility)
# Cloud Run Jobs are for batch processing - we need a persistent service

set -e

echo "🚀 Deploying GPU Worker Service (Fixed)"
echo "========================================"
echo

# Configuration
PROJECT_ID="om-models"
SERVICE_NAME="gpu-worker-service"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
SERVICE_ACCOUNT="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "📦 Step 1: Building Fixed GPU Worker Image"
echo "------------------------------------------"

cd gpu_worker

# Build with fixed Dockerfile
docker build --platform linux/amd64 -f Dockerfile.fixed -t ${IMAGE_NAME}:latest .

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
echo "☁️ Step 3: Deploying as Cloud Run Service"
echo "----------------------------------------"

# Deploy as Cloud Run Service (persistent, HTTP-accessible)
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
    --set-env-vars GCS_BUCKET_NAME=hub-job-files \
    --set-env-vars ENVIRONMENT=production \
    --memory 8Gi \
    --cpu 2 \
    --timeout 30m \
    --max-instances 3 \
    --min-instances 0 \
    --port 8080 \
    --allow-unauthenticated \
    --execution-environment gen2

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Service deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Cloud Run Service deployed${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo
echo "🧪 Step 4: Testing GPU Worker Service"
echo "------------------------------------"

# Wait for service to be ready
echo "Waiting for service to be ready..."
sleep 30

# Test health endpoint
echo "Testing health endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health)

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed (HTTP $HTTP_STATUS)${NC}"
    curl -s ${SERVICE_URL}/health | python3 -m json.tool
else
    echo -e "${YELLOW}⚠️ Health check returned HTTP $HTTP_STATUS${NC}"
    echo "Checking service logs..."
    gcloud logging read "resource.type=cloud_run_revision" --limit=10 --format=json | jq -r '.[].textPayload // .[].jsonPayload.message // "No message"'
fi

# Test process endpoint with sample data
echo
echo "Testing process endpoint..."
PROCESS_RESPONSE=$(curl -s -X POST ${SERVICE_URL}/process \
    -H 'Content-Type: application/json' \
    -d '{
        "job_id": "test_job_' $(date +%s)'",
        "job_type": "INDIVIDUAL",
        "batch_id": null
    }')

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Process endpoint test completed${NC}"
    echo "$PROCESS_RESPONSE" | python3 -m json.tool
else
    echo -e "${YELLOW}⚠️ Process endpoint test had issues${NC}"
fi

echo
echo -e "${GREEN}🎉 GPU Worker Service Deployment Complete!${NC}"
echo
echo "Service Details:"
echo "  Name: ${SERVICE_NAME}"
echo "  URL: ${SERVICE_URL}"
echo "  Region: ${REGION}"
echo "  Image: ${IMAGE_NAME}:latest"
echo "  Memory: 8GB"
echo "  CPU: 2 cores"
echo
echo "Next steps:"
echo "  1. Test job processing: curl -X POST ${SERVICE_URL}/process -H 'Content-Type: application/json' -d '{\"job_id\":\"test123\"}'"
echo "  2. Update GPU_WORKER_URL in job submission service: ${SERVICE_URL}"
echo "  3. Check logs: gcloud logging read 'resource.type=cloud_run_revision' --limit=50"
echo "  4. Add GPU support when ready for production workloads"

cd ..