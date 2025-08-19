#!/bin/bash

# OMTX-Hub GKE Deployment Script
# Deploys the backend to Google Kubernetes Engine

set -e

echo "🚀 OMTX-Hub GKE Deployment"
echo "=========================="

# Configuration
PROJECT_ID="om-models"
CLUSTER_NAME="omtx-hub-cluster"
REGION="us-central1"
ZONE="us-central1-a"
IMAGE_NAME="omtx-hub-backend"
IMAGE_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Step 1: Check prerequisites
echo "1️⃣ Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    print_info "Installing kubectl..."
    gcloud components install kubectl
fi

print_status "Prerequisites met"

# Step 2: Set project and authenticate
echo ""
echo "2️⃣ Setting up GCP project..."
gcloud config set project $PROJECT_ID
print_status "Project set to: $PROJECT_ID"

# Step 3: Check if cluster exists, create if not
echo ""
echo "3️⃣ Checking GKE cluster..."

if gcloud container clusters describe $CLUSTER_NAME --zone=$ZONE &>/dev/null; then
    print_status "Cluster $CLUSTER_NAME exists"
else
    print_info "Creating GKE cluster..."
    gcloud container clusters create $CLUSTER_NAME \
        --zone=$ZONE \
        --num-nodes=3 \
        --machine-type=e2-standard-4 \
        --disk-size=50GB \
        --enable-autoscaling \
        --min-nodes=2 \
        --max-nodes=10 \
        --enable-autorepair \
        --enable-autoupgrade \
        --addons HorizontalPodAutoscaling,HttpLoadBalancing \
        --workload-pool=${PROJECT_ID}.svc.id.goog
    
    print_status "Cluster created successfully"
fi

# Step 4: Get cluster credentials
echo ""
echo "4️⃣ Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE --project=$PROJECT_ID
print_status "kubectl configured for $CLUSTER_NAME"

# Step 5: Build Docker image
echo ""
echo "5️⃣ Building Docker image..."

# Create Dockerfile if it doesn't exist
if [ ! -f "backend/Dockerfile" ]; then
    print_info "Creating Dockerfile..."
    cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
    print_status "Dockerfile created"
fi

# Build the image
docker build -t gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG} backend/
print_status "Docker image built"

# Step 6: Push to Google Container Registry
echo ""
echo "6️⃣ Pushing image to GCR..."
docker push gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}
print_status "Image pushed to GCR"

# Step 7: Create Kubernetes namespace
echo ""
echo "7️⃣ Setting up Kubernetes namespace..."
kubectl create namespace omtx-hub --dry-run=client -o yaml | kubectl apply -f -
print_status "Namespace created/updated"

# Step 8: Create secrets from .env file
echo ""
echo "8️⃣ Creating Kubernetes secrets..."

# Read .env file and create secret
if [ -f "backend/.env" ]; then
    kubectl create secret generic omtx-hub-env \
        --from-env-file=backend/.env \
        --namespace=omtx-hub \
        --dry-run=client -o yaml | kubectl apply -f -
    print_status "Secrets created from .env file"
else
    print_warning ".env file not found, skipping secret creation"
fi

# Step 9: Deploy application
echo ""
echo "9️⃣ Deploying application..."

# Create deployment
cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: omtx-hub-backend
  namespace: omtx-hub
spec:
  replicas: 3
  selector:
    matchLabels:
      app: omtx-hub-backend
  template:
    metadata:
      labels:
        app: omtx-hub-backend
    spec:
      containers:
      - name: backend
        image: gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: omtx-hub-env
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
EOF

print_status "Deployment created"

# Step 10: Create service
echo ""
echo "🔟 Creating service..."

cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: omtx-hub-backend-service
  namespace: omtx-hub
spec:
  type: LoadBalancer
  selector:
    app: omtx-hub-backend
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
EOF

print_status "Service created"

# Step 11: Create HPA
echo ""
echo "1️⃣1️⃣ Creating auto-scaler..."

cat << EOF | kubectl apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: omtx-hub-backend-hpa
  namespace: omtx-hub
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: omtx-hub-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF

print_status "HPA created"

# Step 12: Wait for deployment
echo ""
echo "1️⃣2️⃣ Waiting for deployment..."
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub --timeout=5m

# Step 13: Get external IP
echo ""
echo "1️⃣3️⃣ Getting external IP..."

EXTERNAL_IP=""
while [ -z "$EXTERNAL_IP" ]; do
    echo "Waiting for external IP..."
    EXTERNAL_IP=$(kubectl get service omtx-hub-backend-service -n omtx-hub -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    [ -z "$EXTERNAL_IP" ] && sleep 10
done

print_status "External IP assigned: $EXTERNAL_IP"

# Final summary
echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo "Cluster: $CLUSTER_NAME"
echo "Project: $PROJECT_ID"
echo "Namespace: omtx-hub"
echo "External IP: $EXTERNAL_IP"
echo ""
echo "📋 Access your application:"
echo "   API: http://$EXTERNAL_IP"
echo "   Docs: http://$EXTERNAL_IP/docs"
echo "   Health: http://$EXTERNAL_IP/health"
echo ""
echo "📊 Monitor your deployment:"
echo "   kubectl get pods -n omtx-hub"
echo "   kubectl get hpa -n omtx-hub"
echo "   kubectl logs -f deployment/omtx-hub-backend -n omtx-hub"
echo ""
echo "🔧 Scale manually if needed:"
echo "   kubectl scale deployment/omtx-hub-backend --replicas=5 -n omtx-hub"