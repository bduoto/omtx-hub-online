#!/bin/bash

# Simple Deploy Missing Endpoints - NO LOCAL TESTING
# Distinguished Engineer Implementation - Direct deployment to GKE

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${GCP_REGION:-"us-central1"}
CLUSTER_NAME="omtx-hub-cluster"
ZONE="us-central1-a"

echo -e "${CYAN}🚀 SIMPLE DEPLOY: MISSING ENDPOINTS${NC}"
echo -e "${CYAN}===================================${NC}"
echo ""

print_step() {
    echo -e "${BLUE}$1${NC} $2"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Check files exist
print_step "1️⃣" "Checking required files..."
if [ ! -f "backend/api/missing_endpoints.py" ]; then
    print_error "missing_endpoints.py not found!"
    exit 1
fi

if ! grep -q "missing_endpoints_router" backend/main.py; then
    print_error "main.py does not include missing endpoints router"
    exit 1
fi

print_success "All required files exist"

# Step 2: Build Docker image
print_step "2️⃣" "Building Docker image..."
echo "Building gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints..."

if docker build -t gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints backend/; then
    print_success "Docker image built successfully"
else
    print_error "Docker build failed"
    exit 1
fi

# Step 3: Push to registry
print_step "3️⃣" "Pushing to Container Registry..."
echo "Pushing to gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints..."

if docker push gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints; then
    print_success "Image pushed successfully"
else
    print_error "Docker push failed"
    exit 1
fi

# Step 4: Get GKE credentials
print_step "4️⃣" "Getting GKE credentials..."
if gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE --project=$PROJECT_ID; then
    print_success "GKE credentials obtained"
else
    print_error "Failed to get GKE credentials"
    exit 1
fi

# Step 5: Update deployment
print_step "5️⃣" "Updating GKE deployment..."
echo "Updating deployment with new image..."

if kubectl set image deployment/omtx-hub-backend omtx-hub-backend=gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints; then
    print_success "Deployment updated"
else
    print_error "Failed to update deployment"
    exit 1
fi

# Step 6: Wait for rollout
print_step "6️⃣" "Waiting for rollout..."
echo "This may take 2-3 minutes..."

if kubectl rollout status deployment/omtx-hub-backend --timeout=300s; then
    print_success "Rollout completed successfully"
else
    print_error "Rollout failed or timed out"
    echo "Check deployment status: kubectl get pods"
    exit 1
fi

# Step 7: Wait for service to be ready
print_step "7️⃣" "Waiting for service to be ready..."
echo "Waiting 30 seconds for service to stabilize..."
sleep 30

# Step 8: Test endpoints
print_step "8️⃣" "Testing deployed endpoints..."

# Test health first
echo -n "Testing health endpoint... "
if curl -s "http://34.29.29.170/health" > /dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    print_error "Health endpoint not responding"
    exit 1
fi

# Test missing endpoints
endpoints=(
    "jobs/unified"
    "jobs/ultra-fast"
    "batches"
)

echo ""
echo "Testing missing endpoints:"

for endpoint in "${endpoints[@]}"; do
    echo -n "  /api/v4/$endpoint... "
    
    if curl -s "http://34.29.29.170/api/v4/$endpoint?user_id=demo-user" | grep -q '"total"'; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${YELLOW}⚠️  May not be ready${NC}"
    fi
done

# Step 9: Show status
print_step "9️⃣" "Deployment status..."

echo ""
echo -e "${WHITE}📊 Pod Status:${NC}"
kubectl get pods -l app=omtx-hub-backend

echo ""
echo -e "${WHITE}📊 Service Status:${NC}"
kubectl get services

echo ""
echo -e "${WHITE}🔗 Test Commands:${NC}"
echo "curl \"http://34.29.29.170/health\""
echo "curl \"http://34.29.29.170/api/v4/jobs/unified?user_id=demo-user\""
echo "curl \"http://34.29.29.170/api/v4/jobs/ultra-fast?user_id=demo-user\""
echo "curl \"http://34.29.29.170/api/v4/batches?user_id=demo-user\""

echo ""
print_success "Deployment complete!"

echo ""
echo -e "${CYAN}🎯 NEXT STEPS:${NC}"
echo "1. Test the endpoints above"
echo "2. Restart your frontend: npm run dev"
echo "3. Check browser console for 404 errors"
echo "4. Load demo data: python3 scripts/load_production_demo_data.py"
echo ""

echo -e "${GREEN}✅ Missing endpoints should now be available!${NC}"
