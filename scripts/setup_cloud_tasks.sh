#!/bin/bash
# Set up Cloud Tasks queue for GPU job orchestration

set -e

echo "🚀 Setting up Cloud Tasks for GPU Job Queue"
echo "==========================================="
echo

# Configuration
PROJECT_ID="om-models"
LOCATION="us-central1"
QUEUE_NAME="gpu-job-queue"
HIGH_PRIORITY_QUEUE="gpu-job-queue-high"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Set project
gcloud config set project ${PROJECT_ID}

echo "📋 Step 1: Enable Cloud Tasks API"
echo "---------------------------------"
gcloud services enable cloudtasks.googleapis.com

echo
echo "📋 Step 2: Create Standard Priority Queue"
echo "-----------------------------------------"

# Check if queue exists
if gcloud tasks queues describe ${QUEUE_NAME} --location=${LOCATION} &>/dev/null; then
    echo -e "${YELLOW}Queue ${QUEUE_NAME} already exists. Updating...${NC}"
    gcloud tasks queues update ${QUEUE_NAME} \
        --location=${LOCATION} \
        --max-dispatches-per-second=10 \
        --max-concurrent-dispatches=50 \
        --max-attempts=3 \
        --min-backoff=10s \
        --max-backoff=300s \
        --max-retry-duration=3600s
else
    echo "Creating new queue: ${QUEUE_NAME}"
    gcloud tasks queues create ${QUEUE_NAME} \
        --location=${LOCATION} \
        --max-dispatches-per-second=10 \
        --max-concurrent-dispatches=50 \
        --max-attempts=3 \
        --min-backoff=10s \
        --max-backoff=300s \
        --max-retry-duration=3600s
fi

echo -e "${GREEN}✅ Standard queue configured${NC}"

echo
echo "📋 Step 3: Create High Priority Queue"
echo "-------------------------------------"

if gcloud tasks queues describe ${HIGH_PRIORITY_QUEUE} --location=${LOCATION} &>/dev/null; then
    echo -e "${YELLOW}Queue ${HIGH_PRIORITY_QUEUE} already exists. Updating...${NC}"
    gcloud tasks queues update ${HIGH_PRIORITY_QUEUE} \
        --location=${LOCATION} \
        --max-dispatches-per-second=20 \
        --max-concurrent-dispatches=100 \
        --max-attempts=5 \
        --min-backoff=5s \
        --max-backoff=60s \
        --max-retry-duration=7200s
else
    echo "Creating new queue: ${HIGH_PRIORITY_QUEUE}"
    gcloud tasks queues create ${HIGH_PRIORITY_QUEUE} \
        --location=${LOCATION} \
        --max-dispatches-per-second=20 \
        --max-concurrent-dispatches=100 \
        --max-attempts=5 \
        --min-backoff=5s \
        --max-backoff=60s \
        --max-retry-duration=7200s
fi

echo -e "${GREEN}✅ High priority queue configured${NC}"

echo
echo "📋 Step 4: Create Service Account for Cloud Tasks"
echo "-------------------------------------------------"

SA_NAME="cloud-tasks-invoker"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe ${SA_EMAIL} --project=${PROJECT_ID} &>/dev/null; then
    echo -e "${YELLOW}Service account already exists${NC}"
else
    gcloud iam service-accounts create ${SA_NAME} \
        --description="Service account for Cloud Tasks to invoke Cloud Run" \
        --display-name="Cloud Tasks Invoker"
fi

# Grant permissions
echo "Granting permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" &>/dev/null || true

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtasks.enqueuer" &>/dev/null || true

echo -e "${GREEN}✅ Service account configured${NC}"

echo
echo "📋 Step 5: Verify Queue Status"
echo "------------------------------"

echo "Standard Queue Status:"
gcloud tasks queues describe ${QUEUE_NAME} \
    --location=${LOCATION} \
    --format="table(name,state,rateLimits.maxDispatchesPerSecond,retryConfig.maxAttempts)"

echo
echo "High Priority Queue Status:"
gcloud tasks queues describe ${HIGH_PRIORITY_QUEUE} \
    --location=${LOCATION} \
    --format="table(name,state,rateLimits.maxDispatchesPerSecond,retryConfig.maxAttempts)"

echo
echo -e "${GREEN}🎉 Cloud Tasks Setup Complete!${NC}"
echo
echo "Queue Details:"
echo "  Standard Queue: projects/${PROJECT_ID}/locations/${LOCATION}/queues/${QUEUE_NAME}"
echo "  High Priority: projects/${PROJECT_ID}/locations/${LOCATION}/queues/${HIGH_PRIORITY_QUEUE}"
echo "  Service Account: ${SA_EMAIL}"
echo
echo "Next steps:"
echo "  1. Update your API to submit jobs to these queues"
echo "  2. Deploy GPU worker service to process tasks"
echo "  3. Test with: gcloud tasks create-http-task --queue=${QUEUE_NAME} --url=https://your-worker-url/process"