#!/bin/bash
# OMTX-Hub Production Deployment Script
# Complete end-to-end deployment with all fixes

set -e

echo "🚀 Deploying OMTX-Hub Backend to Production"
echo "============================================"

# Set variables
PROJECT_ID="om-models"
SERVICE_NAME="omtx-hub-backend"
REGION="us-central1"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed"
    exit 1
fi

# Set project
echo "📦 Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Trigger build and deploy
echo ""
echo "🔨 Building and deploying backend..."
gcloud builds submit \
  --config=cloudbuild-production.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
  --timeout=600s

# Wait for deployment to complete
echo ""
echo "⏳ Waiting for deployment to stabilize..."
sleep 10

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --format="value(status.url)")

# Test health endpoint
echo ""
echo "🏥 Testing health endpoint..."
if curl -s "${SERVICE_URL}/health" > /dev/null; then
    echo "✅ Health check passed!"
else
    echo "⚠️  Health check failed or service not ready yet"
fi

# Display useful information
echo ""
echo "================== DEPLOYMENT COMPLETE =================="
echo ""
echo "🌐 Service URL: ${SERVICE_URL}"
echo ""
echo "📊 View logs:"
echo "   gcloud run services logs read ${SERVICE_NAME} --region=${REGION}"
echo ""
echo "🔍 View metrics:"
echo "   https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics"
echo ""
echo "🚀 Test the API:"
echo "   curl ${SERVICE_URL}/docs"
echo ""
echo "📝 Submit a test job:"
echo "   curl -X POST ${SERVICE_URL}/api/v1/predict \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"model\": \"boltz2\", \"protein_sequence\": \"MVLSPADKTN\", \"ligand_smiles\": \"CCO\", \"job_name\": \"test\"}'"
echo ""
echo "========================================================"