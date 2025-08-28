#!/bin/bash

# Deploy auth simplification changes
echo "🚀 Deploying auth simplification changes..."

cd backend

# Use source deployment with current directory
gcloud run deploy omtx-hub-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars DEPLOYMENT_USER_ID=omtx_deployment_user

echo "✅ Deployment completed!"

# Test the deployment
echo "🧪 Testing deployment..."
sleep 10

# Test health endpoint
echo "Testing health endpoint..."
curl -s https://omtx-hub-backend-338254269321.us-central1.run.app/health | jq

# Test jobs listing with deployment user
echo "Testing jobs listing..."
curl -s "https://omtx-hub-backend-338254269321.us-central1.run.app/api/v1/jobs?user_id=omtx_deployment_user&limit=5" | jq

echo "🎉 Auth simplification deployment complete!"