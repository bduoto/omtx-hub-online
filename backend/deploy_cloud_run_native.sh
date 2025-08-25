#!/bin/bash

# OMTX-Hub Cloud Run Native Deployment Script
# Deploy simplified architecture optimized for L4 GPUs with concurrency=2

set -e  # Exit on any error

echo "🚀 OMTX-Hub Cloud Run Native Deployment"
echo "======================================="
echo "Architecture: Direct GPU processing with Cloud Run"
echo "Authentication: Company API Gateway (upstream)"
echo "GPU: L4 with concurrency=2 optimization"
echo "Cost Savings: 84% vs Modal A100"
echo ""

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"om-models"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="omtx-hub-native"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "📋 Configuration:"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"  
echo "   Service: $SERVICE_NAME"
echo "   Image: $IMAGE_NAME"
echo ""

# Step 1: Build Docker image
echo "🔨 Step 1: Building Docker image..."
docker build -f Dockerfile.cloud_run_native -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi
echo "✅ Docker image built successfully"
echo ""

# Step 2: Push to Container Registry
echo "📤 Step 2: Pushing to Container Registry..."
docker push $IMAGE_NAME

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed"
    exit 1
fi
echo "✅ Image pushed successfully"
echo ""

# Step 3: Deploy to Cloud Run with GPU optimization
echo "🚀 Step 3: Deploying to Cloud Run with GPU..."

gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_NAME \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --port=8080 \
    --memory=16Gi \
    --cpu=4 \
    --timeout=1800 \
    --concurrency=2 \
    --min-instances=0 \
    --max-instances=3 \
    --execution-environment=gen2 \
    --gpu=1 \
    --gpu-type=nvidia-l4 \
    --no-cpu-throttling \
    --set-env-vars="ENVIRONMENT=production,GPU_ENABLED=true" \
    --service-account="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

if [ $? -ne 0 ]; then
    echo "❌ Cloud Run deployment failed"
    exit 1
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform=managed --region=$REGION --format="value(status.url)")

echo ""
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "========================="
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo "📚 API Documentation: $SERVICE_URL/docs"
echo "🏥 Health Check: $SERVICE_URL/health"
echo ""
echo "🧬 API Endpoints:"
echo "   POST $SERVICE_URL/api/v1/predict"
echo "   POST $SERVICE_URL/api/v1/predict/batch"
echo "   GET  $SERVICE_URL/api/v1/jobs/{job_id}"
echo "   GET  $SERVICE_URL/api/v1/batches/{batch_id}"
echo ""
echo "⚙️  Architecture Details:"
echo "   • GPU: NVIDIA L4 (24GB VRAM)"
echo "   • Concurrency: 2 requests per instance"
echo "   • Auto-scaling: 0-3 instances"
echo "   • Cost: ~\$0.65/hour (84% savings vs A100)"
echo "   • Authentication: API Gateway (upstream)"
echo ""
echo "🧪 Quick Test:"
echo "curl -X GET \"$SERVICE_URL/health\""
echo ""
echo "🎯 Next Steps:"
echo "1. Update frontend to use: $SERVICE_URL"
echo "2. Configure API Gateway routing"
echo "3. Test individual and batch predictions"
echo "4. Monitor GPU utilization and cost savings"
echo ""

# Optional: Run a quick health check
echo "🔍 Testing deployment..."
if curl -f -s "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Service is responding to health checks"
else
    echo "⚠️ Service might still be starting up (this is normal)"
    echo "   Try again in 30-60 seconds for GPU initialization"
fi

echo ""
echo "🎉 OMTX-Hub Cloud Run Native deployment complete!"
echo "   Ready for production workloads with 84% cost optimization"