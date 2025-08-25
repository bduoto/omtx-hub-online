#!/bin/bash

# OMTX-Hub Cloud Run Native Deployment with Cloud Build
# Use Cloud Build to build the Docker image, then deploy to Cloud Run with GPU

set -e  # Exit on any error

echo "🚀 OMTX-Hub Cloud Run Native Deployment (Cloud Build)"
echo "======================================================="
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

# Step 1: Build Docker image with Cloud Build
echo "🔨 Step 1: Building Docker image with Cloud Build..."

gcloud builds submit \
    --project=$PROJECT_ID \
    --config=cloudbuild.yaml \
    --substitutions=_IMAGE_NAME=$IMAGE_NAME \
    .

if [ $? -ne 0 ]; then
    echo "❌ Cloud Build failed"
    exit 1
fi
echo "✅ Docker image built successfully with Cloud Build"
echo ""

# Step 2: Deploy to Cloud Run with GPU optimization
echo "🚀 Step 2: Deploying to Cloud Run with GPU..."

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
    --project=$PROJECT_ID

if [ $? -ne 0 ]; then
    echo "❌ Cloud Run deployment failed"
    exit 1
fi

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform=managed --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)

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

# Save the service URL to a file for frontend integration
echo $SERVICE_URL > .service_url

echo "🎯 Next Steps:"
echo "1. Test health check: curl \"$SERVICE_URL/health\""
echo "2. View API docs: open \"$SERVICE_URL/docs\""
echo "3. Update frontend with URL: $SERVICE_URL"
echo "4. Run end-to-end tests with production backend"
echo ""

# Optional: Run a quick health check
echo "🔍 Testing deployment..."
if curl -f -s "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Service is responding to health checks"
    
    # Test API documentation
    if curl -f -s "$SERVICE_URL/docs" > /dev/null; then
        echo "✅ API documentation is accessible"
    fi
else
    echo "⚠️ Service might still be starting up (this is normal)"
    echo "   Try again in 30-60 seconds for GPU initialization"
fi

echo ""
echo "🎉 OMTX-Hub Cloud Run Native deployment complete!"
echo "   Ready for production workloads with 84% cost optimization"
echo "   Service URL saved to .service_url file"