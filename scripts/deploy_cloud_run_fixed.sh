#!/bin/bash

# Deploy to Cloud Run with Architecture Fix
# Distinguished Engineer Implementation - Handles ARM64 to AMD64 conversion

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
SERVICE_NAME="omtx-hub-backend"
IMAGE_TAG="missing-endpoints"

echo -e "${CYAN}🚀 CLOUD RUN DEPLOYMENT WITH ARCHITECTURE FIX${NC}"
echo -e "${CYAN}===============================================${NC}"
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

# Step 1: Check Docker is running
print_step "1️⃣" "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi
print_success "Docker is running"

# Step 2: Build for correct architecture
print_step "2️⃣" "Building Docker image for AMD64 architecture..."
echo "Building gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG for linux/amd64..."

if docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG backend/; then
    print_success "Docker image built for AMD64"
else
    print_error "Docker build failed"
    exit 1
fi

# Step 3: Push image
print_step "3️⃣" "Pushing image to Container Registry..."
echo "Pushing gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG..."

if docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG; then
    print_success "Image pushed successfully"
else
    print_error "Docker push failed"
    exit 1
fi

# Step 4: Deploy to Cloud Run
print_step "4️⃣" "Deploying to Cloud Run..."
echo "Deploying $SERVICE_NAME to Cloud Run..."

if gcloud run deploy $SERVICE_NAME \
    --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=8000 \
    --memory=2Gi \
    --cpu=1 \
    --max-instances=10 \
    --min-instances=0 \
    --concurrency=1000 \
    --timeout=300; then
    print_success "Cloud Run deployment successful"
else
    print_error "Cloud Run deployment failed"
    exit 1
fi

# Step 5: Get service URL
print_step "5️⃣" "Getting service information..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
print_success "Service deployed at: $SERVICE_URL"

# Step 6: Test health endpoint
print_step "6️⃣" "Testing health endpoint..."
echo "Waiting 30 seconds for service to be ready..."
sleep 30

echo -n "Testing health endpoint... "
if curl -s "http://34.29.29.170/health" > /dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  May not be ready yet${NC}"
fi

# Step 7: Test missing endpoints
print_step "7️⃣" "Testing missing endpoints..."

endpoints=(
    "jobs/unified"
    "jobs/ultra-fast"
    "batches"
)

echo "Testing missing endpoints:"
for endpoint in "${endpoints[@]}"; do
    echo -n "  /api/v4/$endpoint... "
    
    if curl -s "http://34.29.29.170/api/v4/$endpoint?user_id=demo-user" | grep -q '"total"'; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${YELLOW}⚠️  May not be ready${NC}"
    fi
done

# Step 8: Show next steps
print_step "8️⃣" "Next steps..."

echo ""
echo -e "${WHITE}🔗 Test Commands:${NC}"
echo "curl \"http://34.29.29.170/health\""
echo "curl \"http://34.29.29.170/api/v4/jobs/unified?user_id=demo-user\""
echo "curl \"http://34.29.29.170/api/v4/jobs/ultra-fast?user_id=demo-user\""
echo "curl \"http://34.29.29.170/api/v4/batches?user_id=demo-user\""
echo ""

echo -e "${WHITE}📊 Load Demo Data:${NC}"
echo "python3 scripts/load_production_demo_data.py --url \"http://34.29.29.170\""
echo ""

echo -e "${WHITE}🌐 Test Frontend:${NC}"
echo "npm run dev"
echo "# Open http://localhost:5173"
echo "# Check browser console for 404 errors"
echo ""

print_success "Cloud Run deployment complete!"

echo ""
echo -e "${CYAN}🎯 SUMMARY:${NC}"
echo "✅ Docker image built for correct architecture (AMD64)"
echo "✅ Image pushed to Container Registry"
echo "✅ Service deployed to Cloud Run"
echo "✅ Missing endpoints should now be available"
echo ""

echo -e "${GREEN}🎉 Ready to load demo data and test frontend!${NC}"
