# 🚀 Production Deployment Commands

## **Step 1: Authenticate and Deploy Backend**

```bash
# 1. Authenticate with Google Cloud
gcloud auth login

# 2. Set project
gcloud config set project om-models

# 3. Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# 4. Deploy to Cloud Run with GPU
cd /Users/bryanduoto/Desktop/omtx-hub-online
gcloud builds submit --config=backend/cloudbuild.yaml .

# 5. Deploy Cloud Run service with GPU
gcloud run deploy omtx-hub-native \
    --image=gcr.io/om-models/omtx-hub-native:latest \
    --platform=managed \
    --region=us-central1 \
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
    --set-env-vars="ENVIRONMENT=production,GPU_ENABLED=true"

# 6. Get the service URL
SERVICE_URL=$(gcloud run services describe omtx-hub-native --platform=managed --region=us-central1 --format="value(status.url)")
echo "Service URL: $SERVICE_URL"
echo $SERVICE_URL > backend/.service_url
```

## **Step 2: Update Frontend Configuration**

```bash
# Update frontend environment with production URL
echo "VITE_API_BASE_URL=$SERVICE_URL" > frontend/.env
```

## **Step 3: Test Production Deployment**

```bash
# Test the deployed service
curl -X GET "$SERVICE_URL/health"

# Test API documentation
open "$SERVICE_URL/docs"

# Run comprehensive tests
TEST_URL=$SERVICE_URL python3 backend/test_cloud_run_native.py
```

## **Expected Service URL Format**
Based on your project and region, the service URL will be:
`https://omtx-hub-native-[random-hash]-uc.a.run.app`

Example: `https://omtx-hub-native-abcd1234-uc.a.run.app`