#!/bin/bash
# Deploy Boltz-2 as Cloud Run Job for async GPU processing

set -e

echo "🚀 Deploying Boltz-2 Cloud Run Job for Production"
echo "================================================"

PROJECT_ID="om-models"
REGION="us-central1"
JOB_NAME="boltz2-job"
IMAGE="gcr.io/om-models/boltz2-production:v2"

# Create Cloud Run Job (not Service)
echo "📦 Creating Cloud Run Job: $JOB_NAME"
gcloud run jobs create $JOB_NAME \
    --image=$IMAGE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --parallelism=1 \
    --task-count=1 \
    --max-retries=2 \
    --cpu=4 \
    --memory=16Gi \
    --task-timeout=600 \
    --set-env-vars="PYTHONUNBUFFERED=1,BOLTZ_CACHE=/app/.boltz_cache" \
    --service-account=boltz2-worker@${PROJECT_ID}.iam.gserviceaccount.com \
    2>&1 || {
        echo "⚠️  Job might already exist, trying update..."
        gcloud run jobs update $JOB_NAME \
            --image=$IMAGE \
            --region=$REGION \
            --project=$PROJECT_ID \
            --parallelism=1 \
            --task-count=1 \
            --max-retries=2 \
            --cpu=4 \
            --memory=16Gi \
            --task-timeout=600 \
            --set-env-vars="PYTHONUNBUFFERED=1,BOLTZ_CACHE=/app/.boltz_cache"
    }

echo ""
echo "✅ Cloud Run Job deployed successfully!"
echo ""
echo "📊 Job Configuration:"
echo "  - Name: $JOB_NAME"
echo "  - Region: $REGION"
echo "  - CPU: 4 cores"
echo "  - Memory: 16 GB"
echo "  - Timeout: 600 seconds"
echo "  - Max Retries: 2"
echo ""
echo "🔧 To execute the job manually:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION"
echo ""
echo "📝 To check job executions:"
echo "  gcloud run jobs executions list --job=$JOB_NAME --region=$REGION"
echo ""
echo "📋 To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME\" --limit=50"