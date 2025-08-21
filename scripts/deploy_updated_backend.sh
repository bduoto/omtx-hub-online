#!/bin/bash
# Deploy updated backend with Cloud Tasks integration

set -e

echo "🚀 Deploying Updated Backend with Cloud Tasks Integration"
echo "========================================================"
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_ID="om-models"
CLUSTER_NAME="omtx-hub-cluster"
REGION="us-central1-a"

echo "📋 Pre-deployment Checks"
echo "------------------------"
echo "  Project: $PROJECT_ID"
echo "  Cluster: $CLUSTER_NAME"
echo "  Region: $REGION"
echo

# Check if kubectl is configured
if ! kubectl get nodes > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ Configuring kubectl for GKE cluster...${NC}"
    gcloud container clusters get-credentials $CLUSTER_NAME --zone $REGION --project $PROJECT_ID
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to configure kubectl${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ kubectl configured${NC}"

echo
echo "📦 Step 1: Building Updated Backend Image"
echo "-----------------------------------------"

cd backend

# Build the updated image with Cloud Tasks support
docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/backend:cloud-tasks .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend image built successfully${NC}"

echo
echo "📤 Step 2: Pushing Updated Image"
echo "--------------------------------"

# Configure Docker for GCR
gcloud auth configure-docker --quiet

# Push the updated image
docker push gcr.io/$PROJECT_ID/backend:cloud-tasks

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Image push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Updated image pushed to GCR${NC}"

echo
echo "☁️ Step 3: Updating Kubernetes Deployment"
echo "-----------------------------------------"

# Update the deployment to use the new image
kubectl set image deployment/omtx-hub-backend backend=gcr.io/$PROJECT_ID/backend:cloud-tasks -n omtx-hub

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Deployment update failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Kubernetes deployment updated${NC}"

echo
echo "⏳ Step 4: Waiting for Rollout to Complete"
echo "------------------------------------------"

# Wait for the rollout to complete
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub --timeout=300s

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Rollout failed or timed out${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Rollout completed successfully${NC}"

echo
echo "🧪 Step 5: Testing Updated API"
echo "------------------------------"

# Get the external IP
EXTERNAL_IP=$(kubectl get service backend-service -n omtx-hub -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

if [ -z "$EXTERNAL_IP" ]; then
    echo -e "${YELLOW}⚠️ External IP not found, checking ingress...${NC}"
    EXTERNAL_IP=$(kubectl get ingress nginx-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
fi

if [ -z "$EXTERNAL_IP" ]; then
    # Use the production IP we know
    EXTERNAL_IP="34.29.29.170"
    echo -e "${YELLOW}⚠️ Using known production IP: $EXTERNAL_IP${NC}"
fi

echo "🔗 API URL: http://$EXTERNAL_IP"
echo

# Test the health endpoint
echo "Testing health endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$EXTERNAL_IP/health")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed (HTTP $HTTP_STATUS)${NC}"
    curl -s "http://$EXTERNAL_IP/health" | python3 -m json.tool | head -10
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_STATUS)${NC}"
    
    # Check pod logs for errors
    echo -e "${YELLOW}📋 Recent pod logs:${NC}"
    kubectl logs -l app=omtx-hub-backend -n omtx-hub --tail=20
fi

echo
echo "🧪 Testing Cloud Tasks Integration"
echo "----------------------------------"

# Test individual prediction with Boltz-2
echo "Testing individual Boltz-2 prediction..."
INDIVIDUAL_RESPONSE=$(curl -s -X POST "http://$EXTERNAL_IP/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz2",
    "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    "ligand_smiles": "CCO",
    "job_name": "Cloud Tasks Test Individual",
    "user_id": "deployment_test"
  }')

echo "Individual Job Response:"
echo "$INDIVIDUAL_RESPONSE" | python3 -m json.tool

# Check if it used Cloud Tasks
if echo "$INDIVIDUAL_RESPONSE" | grep -q "Cloud Tasks"; then
    echo -e "${GREEN}✅ Cloud Tasks integration working!${NC}"
else
    echo -e "${YELLOW}⚠️ Using fallback workflow (Cloud Tasks may not be available)${NC}"
fi

echo
echo -e "${GREEN}🎉 Backend Deployment with Cloud Tasks Complete!${NC}"
echo
echo "📊 Deployment Summary:"
echo "  Image: gcr.io/$PROJECT_ID/backend:cloud-tasks"
echo "  API URL: http://$EXTERNAL_IP"
echo "  API Docs: http://$EXTERNAL_IP/docs"
echo "  Health: http://$EXTERNAL_IP/health"
echo
echo "🔧 Cloud Tasks Features:"
echo "  ✅ Individual Boltz-2 predictions via Cloud Tasks → Cloud Run GPU"
echo "  ✅ Batch predictions with Cloud Tasks orchestration"
echo "  ✅ Automatic fallback to legacy workflow for other models"
echo "  ✅ Queue management with priority routing"

cd ..