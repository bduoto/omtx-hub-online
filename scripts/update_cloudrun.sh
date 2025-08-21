#!/bin/bash
# Update Cloud Run with the latest consolidated API

set -e

echo "🔄 Updating Cloud Run with Consolidated API v1"
echo "=============================================="
echo

# Configuration
PROJECT_ID="om-models"
SERVICE_NAME="omtx-hub-backend"
REGION="us-central1"
SERVICE_ACCOUNT="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Set project
gcloud config set project ${PROJECT_ID}

echo "📦 Building and deploying latest code..."
echo

# Deploy from source with the latest changes
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 100 \
    --max-instances 10 \
    --min-instances 0 \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars "PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "GCP_BUCKET_NAME=hub-job-files" \
    --set-env-vars "FIRESTORE_DATABASE=(default)" \
    --project ${PROJECT_ID} \
    --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo
echo "✅ Update Complete!"
echo "==================="
echo
echo "Service URL: ${SERVICE_URL}"
echo
echo "Testing new v1 endpoints:"
curl -s ${SERVICE_URL}/api/v1/system/status | python3 -m json.tool || echo "v1 endpoints not yet available"
echo
echo "Current endpoints:"
curl -s ${SERVICE_URL}/ | python3 -m json.tool
echo