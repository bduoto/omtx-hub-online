#!/bin/bash

# Deploy Application to Existing GKE Cluster
# Builds image, pushes to GCR, and deploys to Kubernetes

set -e

PROJECT_ID="om-models"
CLUSTER_NAME="omtx-hub-cluster"
ZONE="us-central1-a"
IMAGE_NAME="omtx-hub-backend"
IMAGE_TAG="latest"

echo "🚀 Deploying OMTX-Hub to existing GKE cluster"
echo "=============================================="

# Step 1: Build and push Docker image
echo "1️⃣ Building Docker image..."
docker build -t gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG} backend/

echo "2️⃣ Pushing to GCR..."
docker push gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}

# Step 2: Get cluster credentials
echo "3️⃣ Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --zone=$ZONE --project=$PROJECT_ID

# Step 3: Create namespace
echo "4️⃣ Creating namespace..."
kubectl create namespace omtx-hub --dry-run=client -o yaml | kubectl apply -f -

# Step 4: Create secrets
echo "5️⃣ Creating secrets..."
if [ -f "backend/.env" ]; then
    kubectl create secret generic omtx-hub-env \
        --from-env-file=backend/.env \
        --namespace=omtx-hub \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ Secrets created"
else
    echo "⚠️ .env file not found"
fi

# Step 5: Deploy application
echo "6️⃣ Deploying application..."
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
---
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
---
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
EOF

echo "7️⃣ Waiting for deployment..."
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub --timeout=5m

echo "8️⃣ Getting external IP..."
echo "Waiting for LoadBalancer IP..."
kubectl get service omtx-hub-backend-service -n omtx-hub --watch

echo "🎉 Deployment complete!"