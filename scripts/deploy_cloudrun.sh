#!/bin/bash
# Deploy OMTX-Hub to Cloud Run

set -e

echo "🚀 Deploying OMTX-Hub to Cloud Run"
echo "==================================="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_ID="om-models"
SERVICE_NAME="omtx-hub-backend"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
SERVICE_ACCOUNT="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if gcloud is configured
if ! gcloud config get-value project &> /dev/null; then
    echo "Setting project to ${PROJECT_ID}..."
    gcloud config set project ${PROJECT_ID}
fi

echo "📦 Step 1: Building Docker image..."
echo "-----------------------------------"

# First, let's build locally and push to GCR
# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "Building with Docker..."
    docker build -t ${IMAGE_NAME}:latest -f Dockerfile.cloudrun .
    
    # Configure Docker for GCR
    gcloud auth configure-docker
    
    # Push to GCR
    docker push ${IMAGE_NAME}:latest
else
    echo "Docker not found, using Cloud Build..."
    # Use Cloud Build with inline config
    cat > /tmp/cloudbuild-temp.yaml <<EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '${IMAGE_NAME}:latest', '-f', 'Dockerfile.cloudrun', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${IMAGE_NAME}:latest']
images:
  - '${IMAGE_NAME}:latest'
EOF
    
    gcloud builds submit \
        --config=/tmp/cloudbuild-temp.yaml \
        --timeout=20m
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image built successfully${NC}"

echo
echo "☁️ Step 2: Deploying to Cloud Run..."
echo "------------------------------------"

# Deploy to Cloud Run with all configurations
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 100 \
    --max-instances 10 \
    --min-instances 1 \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars "PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "API_PORT=8080" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "GCP_BUCKET_NAME=hub-job-files" \
    --set-env-vars "FIRESTORE_DATABASE=(default)" \
    --set-env-vars "ENABLE_TRACING=false" \
    --set-env-vars "DEFAULT_RPS_LIMIT=60" \
    --set-env-vars "PREMIUM_RPS_LIMIT=300" \
    --set-env-vars "ENTERPRISE_RPS_LIMIT=600"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Deployed successfully${NC}"

echo
echo "🔍 Step 3: Getting service URL..."
echo "---------------------------------"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo -e "${GREEN}✅ Service URL: ${SERVICE_URL}${NC}"

echo
echo "🧪 Step 4: Testing deployment..."
echo "--------------------------------"

# Test the health endpoint
echo "Testing health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health)

if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check returned: ${HEALTH_STATUS}${NC}"
fi

# Test the API status endpoint
echo "Testing API status endpoint..."
curl -s ${SERVICE_URL}/api/v1/system/status | python3 -m json.tool | head -20

echo
echo "📊 Step 5: Service Information"
echo "------------------------------"
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "URL: ${SERVICE_URL}"
echo "Service Account: ${SERVICE_ACCOUNT}"
echo

echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo
echo "Your API endpoints:"
echo "  - Health: ${SERVICE_URL}/health"
echo "  - Status: ${SERVICE_URL}/api/v1/system/status"
echo "  - Predict: ${SERVICE_URL}/api/v1/predict"
echo "  - Docs: ${SERVICE_URL}/docs"
echo
echo "To view logs:"
echo "  gcloud run logs read --service ${SERVICE_NAME} --region ${REGION}"
echo
echo "To update frontend to use this URL:"
echo "  export VITE_API_BASE_URL=${SERVICE_URL}"