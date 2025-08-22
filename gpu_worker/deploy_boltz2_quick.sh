#!/bin/bash
# Quick deployment script for Boltz-2 using auto-download approach
# This gets you running in < 15 minutes

set -e

echo "🚀 Quick Boltz-2 Deployment Script"
echo "=================================="

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="boltz2-worker"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:slim"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo ""

# Step 1: Build slim Docker image
echo -e "${GREEN}Step 1: Building slim Docker image...${NC}"
echo "This uses pip-installed Boltz that auto-downloads weights"

docker build \
  --platform linux/amd64 \
  -f Dockerfile.boltz2-slim \
  -t ${IMAGE_NAME} \
  . || {
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
}

echo -e "${GREEN}✅ Docker image built successfully${NC}"

# Step 2: Push to Google Container Registry
echo -e "${GREEN}Step 2: Pushing to GCR...${NC}"

# Configure Docker for GCR
gcloud auth configure-docker gcr.io --quiet

# Push image
docker push ${IMAGE_NAME} || {
    echo -e "${RED}❌ Failed to push image to GCR${NC}"
    echo "Make sure you have permissions to push to gcr.io/${PROJECT_ID}"
    exit 1
}

echo -e "${GREEN}✅ Image pushed to GCR${NC}"

# Step 3: Deploy to Cloud Run
echo -e "${GREEN}Step 3: Deploying to Cloud Run...${NC}"

# Note: Cloud Run doesn't support GPUs yet, so this runs on CPU
# For GPU, you'd need to deploy to GKE or use Cloud Run Jobs with GPU preview
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --memory 16Gi \
  --cpu 4 \
  --timeout 1200 \
  --concurrency 1 \
  --max-instances 10 \
  --no-allow-unauthenticated \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},BOLTZ_CACHE=/app/.boltz_cache" \
  --project ${PROJECT_ID} || {
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo -e "${YELLOW}📌 Service Details:${NC}"
echo "   URL: ${SERVICE_URL}"
echo "   Region: ${REGION}"
echo "   Memory: 16Gi"
echo "   CPU: 4 cores"
echo ""

# Step 4: Test the deployment
echo -e "${GREEN}Step 4: Testing deployment...${NC}"

# Get auth token for testing
AUTH_TOKEN=$(gcloud auth print-identity-token)

# Test health endpoint
curl -H "Authorization: Bearer ${AUTH_TOKEN}" \
     ${SERVICE_URL}/health \
     -w "\n" || {
    echo -e "${YELLOW}⚠️  Health check failed (service may still be starting)${NC}"
}

echo ""
echo -e "${GREEN}🎉 Boltz-2 Quick Deployment Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update backend/.env with:"
echo "   BOLTZ2_ENDPOINT=${SERVICE_URL}"
echo ""
echo "2. First prediction will download weights (~2GB)"
echo "   This takes 5-10 minutes on first run"
echo ""
echo "3. For GPU support, consider:"
echo "   - Deploy to GKE with GPU nodes"
echo "   - Use Vertex AI Prediction"
echo "   - Wait for Cloud Run GPU support"
echo ""
echo "4. Monitor logs:"
echo "   gcloud run logs read ${SERVICE_NAME} --region ${REGION}"
echo ""

# Optional: Create a test prediction
echo -e "${YELLOW}Optional: Run a test prediction? (y/n)${NC}"
read -r response
if [[ "$response" == "y" ]]; then
    echo "Sending test prediction..."
    
    curl -X POST ${SERVICE_URL}/predict \
      -H "Authorization: Bearer ${AUTH_TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{
        "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        "ligand_smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "ligand_name": "ibuprofen"
      }' \
      -w "\n"
    
    echo "Check logs for progress:"
    echo "gcloud run logs read ${SERVICE_NAME} --region ${REGION} --tail 50"
fi

echo ""
echo -e "${GREEN}✨ Done! Your Boltz-2 service is ready.${NC}"
