#!/bin/bash

# OMTX-Hub Production Deployment Script
# Distinguished Engineer Implementation - Complete multi-tenant production setup

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
ENVIRONMENT=${ENVIRONMENT:-"production"}

echo -e "${BLUE}🚀 OMTX-Hub Production Deployment${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
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
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed"
        exit 1
    fi
    
    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Function to setup GCP project
setup_gcp_project() {
    echo -e "${BLUE}🏗️ Setting up GCP project...${NC}"
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    # Enable required APIs
    echo "Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        containerregistry.googleapis.com \
        firestore.googleapis.com \
        storage.googleapis.com \
        eventarc.googleapis.com \
        pubsub.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com \
        secretmanager.googleapis.com
    
    print_status "GCP project setup complete"
}

# Function to create service accounts
create_service_accounts() {
    echo -e "${BLUE}👤 Creating service accounts...${NC}"
    
    # Cloud Run service account
    gcloud iam service-accounts create cloud-run-boltz2 \
        --display-name="Cloud Run Boltz2 Service Account" \
        --description="Service account for Boltz2 Cloud Run services" || true
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/storage.objectAdmin"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/datastore.user"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/monitoring.metricWriter"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/pubsub.publisher"
    
    print_status "Service accounts created and configured"
}

# Function to setup storage
setup_storage() {
    echo -e "${BLUE}🗄️ Setting up storage...${NC}"
    
    # Create GCS bucket
    BUCKET_NAME="omtx-$PROJECT_ID-$ENVIRONMENT"
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/ || true
    
    # Set bucket permissions
    gsutil iam ch serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://$BUCKET_NAME/
    
    # Create bucket structure
    echo "Creating bucket structure..."
    echo "" | gsutil cp - gs://$BUCKET_NAME/users/.keep
    echo "" | gsutil cp - gs://$BUCKET_NAME/system/.keep
    echo "" | gsutil cp - gs://$BUCKET_NAME/backups/.keep
    
    print_status "Storage setup complete"
}

# Function to setup Firestore
setup_firestore() {
    echo -e "${BLUE}🔥 Setting up Firestore...${NC}"
    
    # Create Firestore database (if not exists)
    gcloud firestore databases create --region=$REGION || true
    
    # Deploy security rules
    if [ -f "firestore.rules" ]; then
        firebase deploy --only firestore:rules --project $PROJECT_ID || print_warning "Firebase CLI not available, deploy rules manually"
    else
        print_warning "firestore.rules not found, create and deploy manually"
    fi
    
    # Create indexes
    if [ -f "firestore.indexes.json" ]; then
        gcloud firestore indexes create --file=firestore.indexes.json || print_warning "Index creation failed, create manually"
    fi
    
    print_status "Firestore setup complete"
}

# Function to build and push container
build_and_push_container() {
    echo -e "${BLUE}🐳 Building and pushing container...${NC}"
    
    # Build L4-optimized container
    docker build -f docker/Dockerfile.l4 -t gcr.io/$PROJECT_ID/boltz2-l4:latest .
    
    # Push to registry
    docker push gcr.io/$PROJECT_ID/boltz2-l4:latest
    
    print_status "Container built and pushed"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    echo -e "${BLUE}🏗️ Deploying infrastructure with Terraform...${NC}"
    
    cd infrastructure/terraform
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars
    cat > terraform.tfvars <<EOF
project_id = "$PROJECT_ID"
region = "$REGION"
environment = "$ENVIRONMENT"
container_registry = "gcr.io"
storage_bucket_name = "omtx-$PROJECT_ID-$ENVIRONMENT"
allow_public_access = false
EOF
    
    # Plan and apply
    terraform plan -var-file=terraform.tfvars
    terraform apply -var-file=terraform.tfvars -auto-approve
    
    cd ../..
    
    print_status "Infrastructure deployed"
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "${BLUE}📊 Setting up monitoring...${NC}"
    
    # Create custom metrics
    gcloud logging metrics create omtx_job_completions \
        --description="OMTX job completions" \
        --log-filter='resource.type="cloud_run_revision" AND jsonPayload.event_type="job_completed"' || true
    
    gcloud logging metrics create omtx_job_failures \
        --description="OMTX job failures" \
        --log-filter='resource.type="cloud_run_revision" AND jsonPayload.event_type="job_failed"' || true
    
    # Create alerting policies
    cat > alerting-policy.json <<EOF
{
  "displayName": "OMTX High Error Rate",
  "conditions": [
    {
      "displayName": "Error rate too high",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"boltz2-service\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 0.05,
        "duration": "300s"
      }
    }
  ],
  "alertStrategy": {
    "autoClose": "1800s"
  },
  "enabled": true
}
EOF
    
    gcloud alpha monitoring policies create --policy-from-file=alerting-policy.json || print_warning "Alerting policy creation failed"
    rm -f alerting-policy.json
    
    print_status "Monitoring setup complete"
}

# Function to setup secrets
setup_secrets() {
    echo -e "${BLUE}🔐 Setting up secrets...${NC}"
    
    # Create secrets in Secret Manager
    echo -n "your-jwt-secret-here" | gcloud secrets create jwt-secret --data-file=- || true
    echo -n "your-webhook-secret-here" | gcloud secrets create webhook-secret --data-file=- || true
    
    # Grant access to service account
    gcloud secrets add-iam-policy-binding jwt-secret \
        --member="serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
    
    gcloud secrets add-iam-policy-binding webhook-secret \
        --member="serviceAccount:cloud-run-boltz2@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
    
    print_status "Secrets setup complete"
}

# Function to run tests
run_tests() {
    echo -e "${BLUE}🧪 Running integration tests...${NC}"
    
    # Install test dependencies
    pip install -r backend/requirements-test.txt
    
    # Run tests
    cd backend
    python -m pytest tests/integration/ -v --tb=short
    cd ..
    
    print_status "Integration tests passed"
}

# Function to setup monitoring dashboard
setup_dashboard() {
    echo -e "${BLUE}📈 Setting up monitoring dashboard...${NC}"
    
    # Create dashboard configuration
    cat > dashboard-config.json <<EOF
{
  "displayName": "OMTX-Hub Production Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE"
                    }
                  }
                }
              }
            ]
          }
        }
      }
    ]
  }
}
EOF
    
    gcloud monitoring dashboards create --config-from-file=dashboard-config.json || print_warning "Dashboard creation failed"
    rm -f dashboard-config.json
    
    print_status "Dashboard setup complete"
}

# Function to validate deployment
validate_deployment() {
    echo -e "${BLUE}✅ Validating deployment...${NC}"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe boltz2-service --region=$REGION --format="value(status.url)")
    
    # Test health endpoint
    if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
        print_status "Health check passed"
    else
        print_error "Health check failed"
        exit 1
    fi
    
    # Test authentication endpoint
    if curl -f "$SERVICE_URL/api/system/status" > /dev/null 2>&1; then
        print_status "API endpoints accessible"
    else
        print_warning "API endpoints may require authentication"
    fi
    
    print_status "Deployment validation complete"
}

# Function to print deployment summary
print_summary() {
    echo ""
    echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
    echo -e "${GREEN}=====================${NC}"
    echo ""
    echo "Service URL: $(gcloud run services describe boltz2-service --region=$REGION --format="value(status.url)")"
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Environment: $ENVIRONMENT"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Update your main application to use the new service URL"
    echo "2. Configure JWT_SECRET and other environment variables"
    echo "3. Set up your webhook endpoints"
    echo "4. Configure user tiers and quotas"
    echo "5. Monitor the deployment in Cloud Console"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "- Update .env.production with your actual values"
    echo "- Configure Firestore security rules for your use case"
    echo "- Set up proper SSL certificates for production"
    echo "- Configure backup and disaster recovery"
}

# Main execution
main() {
    echo -e "${BLUE}Starting production deployment...${NC}"
    
    check_prerequisites
    setup_gcp_project
    create_service_accounts
    setup_storage
    setup_firestore
    setup_secrets
    build_and_push_container
    deploy_infrastructure
    setup_monitoring
    setup_dashboard
    run_tests
    validate_deployment
    print_summary
    
    echo -e "${GREEN}✅ Production deployment completed successfully!${NC}"
}

# Run main function
main "$@"
