#!/bin/bash
# Simple Cloud Run deployment using source deploy

set -e

echo "🚀 Simple Cloud Run Deployment"
echo "=============================="
echo

# Configuration
PROJECT_ID="om-models"
SERVICE_NAME="omtx-hub-backend"
REGION="us-central1"
SERVICE_ACCOUNT="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Set project
gcloud config set project ${PROJECT_ID}

echo "☁️ Deploying directly from source code..."
echo "This will build and deploy in one step."
echo

# Deploy from source - Cloud Run will build the container for us
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
    --set-env-vars "ENABLE_CORS=true" \
    --set-env-vars "CORS_ORIGINS=*" \
    --project ${PROJECT_ID}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)')

echo
echo "✅ Deployment Complete!"
echo "======================="
echo
echo "Service URL: ${SERVICE_URL}"
echo
echo "Test your API:"
echo "  curl ${SERVICE_URL}/health"
echo "  curl ${SERVICE_URL}/api/v1/system/status"
echo
echo "View logs:"
echo "  gcloud run logs read --service ${SERVICE_NAME} --region ${REGION}"
echo
echo "Update your frontend .env:"
echo "  VITE_API_BASE_URL=${SERVICE_URL}"