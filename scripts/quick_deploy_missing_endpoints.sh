#!/bin/bash

# Quick Deploy Missing Endpoints - URGENT FRONTEND FIX
# Distinguished Engineer Implementation - Deploy missing API endpoints to GKE

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

echo -e "${CYAN}🚀 QUICK DEPLOY: MISSING ENDPOINTS${NC}"
echo -e "${CYAN}=================================${NC}"
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

# Step 1: Check if missing endpoints file exists
print_step "1️⃣" "Checking missing endpoints file..."
if [ ! -f "backend/api/missing_endpoints.py" ]; then
    print_error "missing_endpoints.py not found!"
    echo "Please ensure the missing endpoints file was created."
    exit 1
fi
print_success "Missing endpoints file exists"

# Step 2: Check if main.py includes the missing endpoints
print_step "2️⃣" "Checking main.py includes missing endpoints..."
if grep -q "missing_endpoints_router" backend/main.py; then
    print_success "main.py includes missing endpoints router"
else
    print_error "main.py does not include missing endpoints router"
    echo "Please add the missing endpoints router to main.py"
    exit 1
fi

# Step 3: Test locally first
print_step "3️⃣" "Testing missing endpoints locally..."
echo "Starting local backend for testing..."

# Start backend in background for testing
cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 10

# Test the endpoints
echo "Testing local endpoints..."
if curl -s "http://localhost:8000/api/v4/jobs/unified?user_id=demo-user" > /dev/null; then
    print_success "Local missing endpoints working"
else
    print_error "Local missing endpoints not working"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Stop local backend
kill $BACKEND_PID 2>/dev/null || true
print_success "Local testing complete"

# Step 4: Build new Docker image
print_step "4️⃣" "Building new Docker image..."
docker build -t gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints backend/
print_success "Docker image built"

# Step 5: Push to registry
print_step "5️⃣" "Pushing to Container Registry..."
docker push gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints
print_success "Image pushed to registry"

# Step 6: Update GKE deployment
print_step "6️⃣" "Updating GKE deployment..."

# Get current cluster credentials
gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE --project=$PROJECT_ID

# Update the deployment
kubectl set image deployment/omtx-hub-backend omtx-hub-backend=gcr.io/$PROJECT_ID/omtx-hub-backend:missing-endpoints

print_success "Deployment updated"

# Step 7: Wait for rollout
print_step "7️⃣" "Waiting for rollout to complete..."
kubectl rollout status deployment/omtx-hub-backend --timeout=300s
print_success "Rollout completed"

# Step 8: Test production endpoints
print_step "8️⃣" "Testing production endpoints..."

# Wait a bit for the service to be ready
sleep 30

echo "Testing production missing endpoints..."

# Test health first
if curl -s "http://34.29.29.170/health" > /dev/null; then
    print_success "Production API is responding"
else
    print_error "Production API not responding"
    exit 1
fi

# Test missing endpoints
endpoints=(
    "http://34.29.29.170/api/v4/jobs/unified?user_id=demo-user"
    "http://34.29.29.170/api/v4/jobs/ultra-fast?user_id=demo-user"
    "http://34.29.29.170/api/v4/batches?user_id=demo-user"
)

for endpoint in "${endpoints[@]}"; do
    echo -n "Testing $endpoint... "
    
    if curl -s "$endpoint" > /dev/null; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "Endpoint may not be ready yet, check logs:"
        echo "kubectl logs -l app=omtx-hub-backend --tail=20"
    fi
done

# Step 9: Show deployment status
print_step "9️⃣" "Deployment status..."

echo ""
echo -e "${WHITE}📊 GKE Deployment Status:${NC}"
kubectl get pods -l app=omtx-hub-backend
echo ""

echo -e "${WHITE}📊 Service Status:${NC}"
kubectl get services
echo ""

echo -e "${WHITE}🔗 Test URLs:${NC}"
echo "Health: http://34.29.29.170/health"
echo "Docs: http://34.29.29.170/docs"
echo "Jobs: http://34.29.29.170/api/v4/jobs/unified?user_id=demo-user"
echo "Batches: http://34.29.29.170/api/v4/batches?user_id=demo-user"
echo ""

print_success "Missing endpoints deployment complete!"

echo ""
echo -e "${CYAN}🎯 NEXT STEPS:${NC}"
echo "1. Test frontend: npm run dev"
echo "2. Check browser console for 404 errors"
echo "3. Verify 'My Results' page loads"
echo "4. Submit a test batch to verify end-to-end flow"
echo ""

echo -e "${GREEN}✅ Your frontend should now work without 404 errors!${NC}"
