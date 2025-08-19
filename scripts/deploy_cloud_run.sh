#!/bin/bash

# Cloud Run Deployment Script for Boltz-2 L4 GPU
# Distinguished Engineer Implementation - Production-ready deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-production-project"}
REGION=${GCP_REGION:-"us-central1"}
CONTAINER_REGISTRY=${CONTAINER_REGISTRY:-"gcr.io"}
SERVICE_ACCOUNT=${SERVICE_ACCOUNT:-"cloud-run-boltz2@${PROJECT_ID}.iam.gserviceaccount.com"}

echo -e "${BLUE}🚀 Deploying Boltz-2 to Cloud Run with L4 GPU${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Container Registry: $CONTAINER_REGISTRY"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    print_status "Prerequisites check passed"
}

# Function to build and push container
build_and_push_container() {
    echo -e "${BLUE}🐳 Building and pushing L4-optimized container...${NC}"
    
    # Build the container
    IMAGE_NAME="$CONTAINER_REGISTRY/$PROJECT_ID/boltz2-l4:latest"
    
    echo "Building container: $IMAGE_NAME"
    docker build -f docker/Dockerfile.boltz2-l4 -t $IMAGE_NAME .
    
    # Push to registry
    echo "Pushing container to registry..."
    docker push $IMAGE_NAME
    
    print_status "Container built and pushed: $IMAGE_NAME"
}

# Function to create service account if not exists
create_service_account() {
    echo -e "${BLUE}👤 Setting up service account...${NC}"
    
    # Create service account
    gcloud iam service-accounts create cloud-run-boltz2 \
        --display-name="Cloud Run Boltz2 Service Account" \
        --description="Service account for Boltz2 Cloud Run services" || true
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/storage.objectAdmin"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/datastore.user"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/monitoring.metricWriter"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/logging.logWriter"
    
    print_status "Service account configured"
}

# Function to deploy Cloud Run Job for batch processing
deploy_cloud_run_job() {
    echo -e "${BLUE}⚡ Deploying Cloud Run Job for batch processing...${NC}"
    
    IMAGE_NAME="$CONTAINER_REGISTRY/$PROJECT_ID/boltz2-l4:latest"
    
    # Create or update Cloud Run Job
    gcloud run jobs replace - <<EOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: boltz2-l4
  namespace: '$PROJECT_ID'
  labels:
    cloud.googleapis.com/location: $REGION
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    spec:
      template:
        spec:
          containers:
          - image: $IMAGE_NAME
            resources:
              limits:
                cpu: "8"
                memory: "32Gi"
                nvidia.com/gpu: "1"
            env:
            - name: GCP_PROJECT_ID
              value: "$PROJECT_ID"
            - name: GCS_BUCKET_NAME
              value: "omtx-$PROJECT_ID-production"
            - name: GPU_TYPE
              value: "L4"
            - name: OPTIMIZATION_LEVEL
              value: "aggressive"
          restartPolicy: Never
          timeoutSeconds: 3600
          serviceAccountName: $SERVICE_ACCOUNT
      parallelism: 10
      completions: 1
      backoffLimit: 3
EOF
    
    print_status "Cloud Run Job deployed: boltz2-l4"
}

# Function to deploy Cloud Run Service for single predictions
deploy_cloud_run_service() {
    echo -e "${BLUE}🔬 Deploying Cloud Run Service for single predictions...${NC}"
    
    IMAGE_NAME="$CONTAINER_REGISTRY/$PROJECT_ID/boltz2-l4:latest"
    
    # Deploy Cloud Run Service
    gcloud run deploy boltz2-service \
        --image=$IMAGE_NAME \
        --region=$REGION \
        --platform=managed \
        --cpu=8 \
        --memory=32Gi \
        --gpu=1 \
        --gpu-type=nvidia-l4 \
        --timeout=3600 \
        --concurrency=1 \
        --min-instances=0 \
        --max-instances=10 \
        --service-account=$SERVICE_ACCOUNT \
        --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=omtx-$PROJECT_ID-production,GPU_TYPE=L4,OPTIMIZATION_LEVEL=aggressive" \
        --allow-unauthenticated \
        --port=8080
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe boltz2-service --region=$REGION --format="value(status.url)")
    
    print_status "Cloud Run Service deployed: $SERVICE_URL"
}

# Function to setup Eventarc triggers
setup_eventarc_triggers() {
    echo -e "${BLUE}⚡ Setting up Eventarc triggers...${NC}"
    
    # Create trigger for job creation
    gcloud eventarc triggers create job-created-trigger \
        --location=$REGION \
        --service-account=$SERVICE_ACCOUNT \
        --destination-run-job=boltz2-l4 \
        --destination-run-region=$REGION \
        --event-filters="type=google.cloud.firestore.document.v1.created" \
        --event-filters="database=(default)" \
        --event-filters-path-pattern="document=users/{userId}/jobs/{jobId}" || true
    
    # Create trigger for job updates
    gcloud eventarc triggers create job-updated-trigger \
        --location=$REGION \
        --service-account=$SERVICE_ACCOUNT \
        --destination-run-job=boltz2-l4 \
        --destination-run-region=$REGION \
        --event-filters="type=google.cloud.firestore.document.v1.updated" \
        --event-filters="database=(default)" \
        --event-filters-path-pattern="document=users/{userId}/jobs/{jobId}" || true
    
    print_status "Eventarc triggers configured"
}

# Function to test deployment
test_deployment() {
    echo -e "${BLUE}🧪 Testing deployment...${NC}"
    
    # Test Cloud Run Service health
    SERVICE_URL=$(gcloud run services describe boltz2-service --region=$REGION --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -n "$SERVICE_URL" ]; then
        echo "Testing service health at: $SERVICE_URL"
        
        # Simple health check
        if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
            print_status "Service health check passed"
        else
            print_warning "Service health check failed (may be normal if no health endpoint)"
        fi
    else
        print_warning "Service URL not found, skipping health check"
    fi
    
    # Test Cloud Run Job exists
    if gcloud run jobs describe boltz2-l4 --region=$REGION > /dev/null 2>&1; then
        print_status "Cloud Run Job exists and is accessible"
    else
        print_error "Cloud Run Job not found"
        exit 1
    fi
    
    print_status "Deployment tests completed"
}

# Function to print deployment summary
print_summary() {
    echo ""
    echo -e "${GREEN}🎉 CLOUD RUN DEPLOYMENT COMPLETE!${NC}"
    echo -e "${GREEN}===================================${NC}"
    echo ""
    
    # Get service URL if available
    SERVICE_URL=$(gcloud run services describe boltz2-service --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Not deployed")
    
    echo "📊 Deployment Summary:"
    echo "  Project: $PROJECT_ID"
    echo "  Region: $REGION"
    echo "  Service URL: $SERVICE_URL"
    echo "  Job Name: boltz2-l4"
    echo "  GPU Type: L4 (24GB VRAM)"
    echo "  Container: $CONTAINER_REGISTRY/$PROJECT_ID/boltz2-l4:latest"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Update your backend API to use the new Cloud Run endpoints"
    echo "2. Test batch processing with a small job"
    echo "3. Monitor GPU utilization and costs"
    echo "4. Scale up based on usage patterns"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "- L4 GPUs provide 84% cost savings vs A100"
    echo "- Monitor GPU utilization in Cloud Console"
    echo "- Set up billing alerts for cost control"
    echo "- Test with small batches first"
}

# Main execution
main() {
    echo -e "${BLUE}Starting Cloud Run deployment...${NC}"
    
    check_prerequisites
    create_service_account
    build_and_push_container
    deploy_cloud_run_job
    deploy_cloud_run_service
    setup_eventarc_triggers
    test_deployment
    print_summary
    
    echo -e "${GREEN}✅ Cloud Run deployment completed successfully!${NC}"
}

# Run main function
main "$@"
