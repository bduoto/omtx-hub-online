#!/bin/bash
# Deploy GPU Worker Service to Cloud Run Jobs

set -e

echo "🚀 Deploying GPU Worker Service"
echo "==============================="
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

echo "📦 Step 1: Building GPU Worker Image"
echo "------------------------------------"

cd gpu_worker

# Build Docker image
docker build -t ${IMAGE_NAME}:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built successfully${NC}"

echo
echo "📤 Step 2: Pushing to Container Registry"
echo "----------------------------------------"

# Configure Docker for GCR
gcloud auth configure-docker

# Push image
docker push ${IMAGE_NAME}:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Image push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image pushed to GCR${NC}"

echo
echo "☁️ Step 3: Deploying Cloud Run Job"
echo "----------------------------------"

# Deploy as Cloud Run Job (not Service)
gcloud run jobs create ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
    --set-env-vars GCS_BUCKET_NAME=hub-job-files \
    --set-env-vars ENVIRONMENT=production \
    --memory 32Gi \
    --cpu 8 \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --task-timeout 30m \
    --max-retries 2 \
    --parallelism 1 \
    --execution-environment gen2 \
    --replace

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️ Job creation failed, trying to update existing job...${NC}"
    
    # Update existing job
    gcloud run jobs update ${SERVICE_NAME} \
        --image ${IMAGE_NAME}:latest \
        --region ${REGION} \
        --service-account ${SERVICE_ACCOUNT} \
        --clear-env-vars \
        --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
        --set-env-vars GCS_BUCKET_NAME=hub-job-files \
        --set-env-vars ENVIRONMENT=production \
        --memory 32Gi \
        --cpu 8 \
        --gpu 1 \
        --gpu-type nvidia-l4 \
        --task-timeout 30m \
        --max-retries 2 \
        --parallelism 1
fi

echo -e "${GREEN}✅ Cloud Run Job deployed${NC}"

echo
echo "🧪 Step 4: Testing GPU Worker"
echo "-----------------------------"

# Create a test execution to verify the job works
echo "Creating test execution..."

JOB_EXECUTION=$(gcloud run jobs execute ${SERVICE_NAME} \
    --region ${REGION} \
    --format="value(metadata.name)" \
    --wait)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test execution completed: ${JOB_EXECUTION}${NC}"
else
    echo -e "${YELLOW}⚠️ Test execution had issues, but job is deployed${NC}"
fi

echo
echo "📊 Step 5: Job Information"
echo "-------------------------"

# Get job details
gcloud run jobs describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format="table(
        metadata.name,
        spec.template.spec.template.spec.serviceAccountName,
        spec.template.spec.template.spec.containers[0].resources.limits.memory,
        spec.template.spec.template.spec.containers[0].resources.limits['nvidia.com/gpu']
    )"

echo
echo -e "${GREEN}🎉 GPU Worker Deployment Complete!${NC}"
echo
echo "Job Details:"
echo "  Name: ${SERVICE_NAME}"
echo "  Region: ${REGION}"
echo "  Image: ${IMAGE_NAME}:latest"
echo "  GPU: 1x NVIDIA L4"
echo "  Memory: 32GB"
echo "  CPU: 8 cores"
echo "  Service Account: ${SERVICE_ACCOUNT}"
echo
echo "Next steps:"
echo "  1. Test job processing: gcloud run jobs execute ${SERVICE_NAME} --region ${REGION}"
echo "  2. Check logs: gcloud logging read 'resource.type=cloud_run_job' --limit=50"
echo "  3. Monitor executions: gcloud run jobs executions list --job=${SERVICE_NAME} --region=${REGION}"

cd ..