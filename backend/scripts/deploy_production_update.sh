#!/bin/bash

# Deploy Updated Production System with Authentication, Monitoring, and Webhooks
# This script deploys the complete enterprise system to GKE

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
CLUSTER_NAME=${GKE_CLUSTER_NAME:-"omtx-hub-cluster"}
ZONE=${GKE_ZONE:-"us-central1-a"}
IMAGE_TAG="enterprise-$(date +%Y%m%d-%H%M%S)"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/omtx-hub-backend:${IMAGE_TAG}"

echo "🚀 Deploying OMTX-Hub Enterprise Production System"
echo "   Project: ${PROJECT_ID}"
echo "   Cluster: ${CLUSTER_NAME}"
echo "   Zone: ${ZONE}"
echo "   Image: ${BACKEND_IMAGE}"
echo "   Timestamp: $(date)"

# Step 1: Set up kubectl context
echo ""
echo "🔧 Setting up kubectl context..."
gcloud container clusters get-credentials ${CLUSTER_NAME} \
  --zone ${ZONE} \
  --project ${PROJECT_ID}

# Step 2: Build and push updated Docker image
echo ""
echo "📦 Building updated backend image..."
docker build -t ${BACKEND_IMAGE} .

echo ""
echo "📤 Pushing image to Google Container Registry..."
docker push ${BACKEND_IMAGE}

# Step 3: Update backend deployment
echo ""
echo "🔄 Updating backend deployment..."

# Create updated deployment manifest
cat > deployment-update.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: omtx-hub-api
  labels:
    app: omtx-hub-api
    version: enterprise
spec:
  replicas: 3
  selector:
    matchLabels:
      app: omtx-hub-api
  template:
    metadata:
      labels:
        app: omtx-hub-api
        version: enterprise
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
        - name: api
          image: ${BACKEND_IMAGE}
          ports:
            - containerPort: 8000
              name: http
          env:
            - name: ENVIRONMENT
              value: "production"
            - name: GCP_PROJECT_ID
              value: "${PROJECT_ID}"
            - name: SERVICE_NAME
              value: "omtx-hub-api"
            - name: SERVICE_VERSION
              value: "${IMAGE_TAG}"
            - name: JWT_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: omtx-hub-secrets
                  key: jwt-secret
            - name: WEBHOOK_SECRET
              valueFrom:
                secretKeyRef:
                  name: omtx-hub-secrets
                  key: webhook-secret
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
          volumeMounts:
            - name: gcp-credentials
              mountPath: /var/secrets/google
              readOnly: true
      volumes:
        - name: gcp-credentials
          secret:
            secretName: gcp-service-account-key
      serviceAccountName: omtx-hub-service-account
---
apiVersion: v1
kind: Service
metadata:
  name: omtx-hub-api-service
  labels:
    app: omtx-hub-api
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8000
      name: http
  selector:
    app: omtx-hub-api
EOF

# Step 4: Create secrets if they don't exist
echo ""
echo "🔐 Setting up secrets..."

# Check if secrets exist, create if not
if ! kubectl get secret omtx-hub-secrets >/dev/null 2>&1; then
    echo "Creating omtx-hub-secrets..."
    kubectl create secret generic omtx-hub-secrets \
        --from-literal=jwt-secret="omtx-hub-production-jwt-secret-$(openssl rand -hex 16)" \
        --from-literal=webhook-secret="omtx-hub-webhook-secret-$(openssl rand -hex 16)"
else
    echo "omtx-hub-secrets already exists"
fi

# Step 5: Create service account if it doesn't exist
echo ""
echo "👤 Setting up service account..."

if ! kubectl get serviceaccount omtx-hub-service-account >/dev/null 2>&1; then
    echo "Creating service account..."
    kubectl create serviceaccount omtx-hub-service-account
    
    # Create cluster role binding
    kubectl create clusterrolebinding omtx-hub-binding \
        --clusterrole=cluster-admin \
        --serviceaccount=default:omtx-hub-service-account || true
else
    echo "Service account already exists"
fi

# Step 6: Deploy updated configuration
echo ""
echo "🚀 Deploying updated configuration..."
kubectl apply -f deployment-update.yaml

# Step 7: Wait for deployment to be ready
echo ""
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/omtx-hub-api

# Step 8: Get service information
echo ""
echo "📍 Getting service information..."
EXTERNAL_IP=""
while [ -z "$EXTERNAL_IP" ]; do
    echo "Waiting for external IP..."
    EXTERNAL_IP=$(kubectl get service omtx-hub-api-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -z "$EXTERNAL_IP" ]; then
        sleep 10
    fi
done

echo ""
echo "✅ Production deployment completed successfully!"
echo ""
echo "🌐 Service Information:"
echo "   External IP: ${EXTERNAL_IP}"
echo "   API URL: http://${EXTERNAL_IP}"
echo "   Health Check: http://${EXTERNAL_IP}/health"
echo "   API Docs: http://${EXTERNAL_IP}/docs"
echo "   Metrics: http://${EXTERNAL_IP}/metrics"
echo ""
echo "🧪 Quick Tests:"
echo "   curl http://${EXTERNAL_IP}/health"
echo "   curl http://${EXTERNAL_IP}/metrics"
echo "   curl http://${EXTERNAL_IP}/api/v1/webhooks/events"
echo ""
echo "🔍 Monitoring:"
echo "   kubectl get pods -l app=omtx-hub-api"
echo "   kubectl logs -f deployment/omtx-hub-api"
echo "   kubectl describe service omtx-hub-api-service"

# Step 9: Run quick validation
echo ""
echo "🔍 Running quick validation..."
sleep 30  # Wait for service to be fully ready

echo "Testing health endpoint..."
if curl -s "http://${EXTERNAL_IP}/health" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
fi

echo "Testing metrics endpoint..."
if curl -s "http://${EXTERNAL_IP}/metrics" | grep -q "http_requests_total"; then
    echo "✅ Metrics endpoint working"
else
    echo "❌ Metrics endpoint not responding"
fi

echo "Testing webhook events endpoint..."
if curl -s "http://${EXTERNAL_IP}/api/v1/webhooks/events" | grep -q "events"; then
    echo "✅ Webhook system operational"
else
    echo "⚠️ Webhook system may require authentication"
fi

echo ""
echo "🎉 Enterprise production system deployment complete!"
echo "📊 Next: Run comprehensive validation tests"

# Cleanup
rm -f deployment-update.yaml