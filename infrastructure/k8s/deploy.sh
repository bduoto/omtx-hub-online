#!/bin/bash

# OMTX-Hub Kubernetes Deployment Script
# This script deploys the complete OMTX-Hub infrastructure to GKE

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
CLUSTER_NAME=${CLUSTER_NAME:-"omtx-hub-cluster"}
REGION=${REGION:-"us-central1"}
ENVIRONMENT=${ENVIRONMENT:-"production"}

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install gcloud first."
        exit 1
    fi
    
    # Check if connected to correct cluster
    CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
    if [[ "$CURRENT_CONTEXT" != *"$CLUSTER_NAME"* ]]; then
        log_warning "Not connected to $CLUSTER_NAME cluster"
        log_info "Run: gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed"
}

create_namespace() {
    log_info "Creating namespace..."
    kubectl apply -f namespace.yaml
    log_success "Namespace created"
}

setup_secrets() {
    log_info "Setting up secrets..."
    
    # Check if secrets exist
    if kubectl get secret omtx-hub-secrets -n omtx-hub &> /dev/null; then
        log_warning "Secrets already exist. Skipping creation."
        return
    fi
    
    log_warning "Secrets template created but NOT populated with actual values!"
    log_warning "Please update secrets.yaml with real values before deploying to production."
    log_warning "For production, create secrets using:"
    echo "  kubectl create secret generic omtx-hub-secrets \\"
    echo "    --from-file=gcp-credentials.json=path/to/service-account.json \\"
    echo "    --from-literal=MODAL_TOKEN_ID=your-token-id \\"
    echo "    --from-literal=MODAL_TOKEN_SECRET=your-token-secret \\"
    echo "    --from-literal=REDIS_PASSWORD=your-redis-password \\"
    echo "    --namespace omtx-hub"
    
    read -p "Continue with template secrets? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl apply -f secrets.yaml
        log_success "Template secrets applied"
    else
        log_error "Deployment stopped. Please create secrets first."
        exit 1
    fi
}

deploy_config() {
    log_info "Deploying configuration..."
    kubectl apply -f configmap.yaml
    log_success "Configuration deployed"
}

deploy_rbac() {
    log_info "Deploying RBAC..."
    kubectl apply -f rbac.yaml
    log_success "RBAC deployed"
}

deploy_redis() {
    log_info "Deploying Redis..."
    kubectl apply -f redis.yaml
    
    log_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n omtx-hub
    log_success "Redis deployed and ready"
}

deploy_backend() {
    log_info "Deploying backend application..."
    
    # Update image tag in deployment
    if [[ "$ENVIRONMENT" == "production" ]]; then
        IMAGE_TAG=${IMAGE_TAG:-"latest"}
    else
        IMAGE_TAG=${IMAGE_TAG:-"staging"}
    fi
    
    log_info "Using image tag: $IMAGE_TAG"
    sed "s|gcr.io/PROJECT_ID/omtx-hub-backend:latest|gcr.io/$PROJECT_ID/omtx-hub-backend:$IMAGE_TAG|g" backend-deployment.yaml > backend-deployment-temp.yaml
    
    kubectl apply -f backend-deployment-temp.yaml
    kubectl apply -f backend-service.yaml
    
    rm -f backend-deployment-temp.yaml
    
    log_info "Waiting for backend deployment to be ready..."
    kubectl wait --for=condition=available --timeout=600s deployment/omtx-hub-backend -n omtx-hub
    log_success "Backend deployed and ready"
}

deploy_ingress() {
    log_info "Deploying ingress..."
    kubectl apply -f ingress.yaml
    log_success "Ingress deployed"
}

deploy_autoscaling() {
    log_info "Deploying autoscaling..."
    kubectl apply -f hpa.yaml
    log_success "Autoscaling deployed"
}

deploy_monitoring() {
    log_info "Deploying monitoring..."
    kubectl apply -f monitoring.yaml
    
    log_info "Waiting for Prometheus to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n omtx-hub
    log_success "Monitoring deployed and ready"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pod status
    log_info "Pod status:"
    kubectl get pods -n omtx-hub
    
    # Check service status
    log_info "Service status:"
    kubectl get services -n omtx-hub
    
    # Check ingress status
    log_info "Ingress status:"
    kubectl get ingress -n omtx-hub
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    BACKEND_IP=$(kubectl get service omtx-hub-backend-lb -n omtx-hub -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    if [[ "$BACKEND_IP" != "pending" && "$BACKEND_IP" != "" ]]; then
        if curl -f "http://$BACKEND_IP/health" &> /dev/null; then
            log_success "Health check passed"
        else
            log_warning "Health check failed - service may still be starting"
        fi
    else
        log_warning "Load balancer IP not yet assigned"
    fi
    
    log_success "Deployment verification complete"
}

print_access_info() {
    log_info "Access Information:"
    
    # Get load balancer IP
    BACKEND_IP=$(kubectl get service omtx-hub-backend-lb -n omtx-hub -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    echo "================================"
    echo "OMTX-Hub Deployment Complete!"
    echo "================================"
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: omtx-hub"
    echo "Backend IP: $BACKEND_IP"
    echo "Health Check: http://$BACKEND_IP/health"
    echo "API Endpoints: http://$BACKEND_IP/api"
    echo "Metrics: http://$BACKEND_IP/metrics"
    echo ""
    echo "Useful Commands:"
    echo "  kubectl get pods -n omtx-hub"
    echo "  kubectl logs -f deployment/omtx-hub-backend -n omtx-hub"
    echo "  kubectl port-forward service/prometheus-service 9090:9090 -n omtx-hub"
    echo ""
    echo "Next Steps:"
    echo "1. Configure DNS to point to $BACKEND_IP"
    echo "2. Update secrets with production values"
    echo "3. Set up SSL certificates"
    echo "4. Configure monitoring alerts"
}

# Main deployment flow
main() {
    log_info "Starting OMTX-Hub deployment to $ENVIRONMENT environment..."
    
    check_prerequisites
    create_namespace
    setup_secrets
    deploy_config
    deploy_rbac
    deploy_redis
    deploy_backend
    deploy_ingress
    deploy_autoscaling
    deploy_monitoring
    verify_deployment
    print_access_info
    
    log_success "Deployment completed successfully!"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -p, --project PROJECT_ID    GCP Project ID"
    echo "  -c, --cluster CLUSTER_NAME  GKE Cluster name"
    echo "  -r, --region REGION         GCP Region"
    echo "  -e, --env ENVIRONMENT       Environment (production/staging)"
    echo "  -t, --tag IMAGE_TAG         Docker image tag"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  PROJECT_ID                  GCP Project ID"
    echo "  CLUSTER_NAME                GKE Cluster name" 
    echo "  REGION                      GCP Region"
    echo "  ENVIRONMENT                 Deployment environment"
    echo "  IMAGE_TAG                   Docker image tag"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main "$@"