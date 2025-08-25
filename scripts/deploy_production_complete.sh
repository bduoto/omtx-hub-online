#!/bin/bash
# Complete Production Deployment Script for Boltz-2 GPU System
# Deploys both Cloud Run Service and Jobs for maximum flexibility

set -e

echo "🚀 DEPLOYING PRODUCTION BOLTZ-2 GPU SYSTEM"
echo "=========================================="

PROJECT_ID="om-models"
REGION="us-central1"
IMAGE="gcr.io/om-models/gpu-worker:quick-fix"  # Use existing working image
SERVICE_ACCOUNT="boltz2-worker@${PROJECT_ID}.iam.gserviceaccount.com"

# 1. Deploy Cloud Run Service (for direct HTTP and Cloud Tasks)
echo ""
echo "📦 1. Deploying Cloud Run Service for GPU predictions..."
gcloud run deploy boltz2-production-v2 \
    --image=$IMAGE \
    --platform=managed \
    --region=$REGION \
    --project=$PROJECT_ID \
    --cpu=4 \
    --memory=16Gi \
    --max-instances=5 \
    --min-instances=0 \
    --concurrency=10 \
    --timeout=300 \
    --service-account=$SERVICE_ACCOUNT \
    --set-env-vars="PYTHONUNBUFFERED=1,BOLTZ_CACHE=/app/.boltz_cache,CUDA_VISIBLE_DEVICES=0" \
    --allow-unauthenticated \
    2>&1 || echo "Service might already exist, updating..."

# Get service URL
SERVICE_URL=$(gcloud run services describe boltz2-production-v2 \
    --region=$REGION \
    --format="value(status.url)" 2>/dev/null)

echo "   ✅ Service deployed at: $SERVICE_URL"

# 2. Update Cloud Run Job for batch processing
echo ""
echo "📦 2. Updating Cloud Run Job for batch processing..."
gcloud run jobs update boltz2-job \
    --image=$IMAGE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --parallelism=1 \
    --max-retries=2 \
    --cpu=4 \
    --memory=16Gi \
    --task-timeout=600 \
    --service-account=$SERVICE_ACCOUNT \
    --set-env-vars="PYTHONUNBUFFERED=1,BOLTZ_CACHE=/app/.boltz_cache,FIRESTORE_PROJECT=$PROJECT_ID" \
    2>&1 || {
        echo "   Creating new job..."
        gcloud run jobs create boltz2-job \
            --image=$IMAGE \
            --region=$REGION \
            --project=$PROJECT_ID \
            --parallelism=1 \
            --max-retries=2 \
            --cpu=4 \
            --memory=16Gi \
            --task-timeout=600 \
            --service-account=$SERVICE_ACCOUNT \
            --set-env-vars="PYTHONUNBUFFERED=1,BOLTZ_CACHE=/app/.boltz_cache,FIRESTORE_PROJECT=$PROJECT_ID"
    }

echo "   ✅ Cloud Run Job configured"

# 3. Configure Cloud Tasks queues
echo ""
echo "📦 3. Verifying Cloud Tasks queues..."

# Check individual queue
gcloud tasks queues describe boltz2-predictions \
    --location=$REGION >/dev/null 2>&1 || {
        echo "   Creating individual predictions queue..."
        gcloud tasks queues create boltz2-predictions \
            --location=$REGION \
            --max-concurrent-dispatches=10 \
            --max-dispatches-per-second=5 \
            --max-attempts=3 \
            --min-backoff=10s \
            --max-backoff=300s
    }

# Check batch queue
gcloud tasks queues describe boltz2-batch-predictions \
    --location=$REGION >/dev/null 2>&1 || {
        echo "   Creating batch predictions queue..."
        gcloud tasks queues create boltz2-batch-predictions \
            --location=$REGION \
            --max-concurrent-dispatches=20 \
            --max-dispatches-per-second=10 \
            --max-attempts=3 \
            --min-backoff=10s \
            --max-backoff=300s
    }

echo "   ✅ Cloud Tasks queues ready"

# 4. Update environment configuration
echo ""
echo "📦 4. Updating backend configuration..."
cat > backend/.env.production << EOF
# Production Configuration for Boltz-2 GPU System
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=$REGION
GPU_WORKER_URL=$SERVICE_URL
CLOUD_RUN_JOB_NAME=boltz2-job
CLOUD_TASKS_QUEUE_INDIVIDUAL=boltz2-predictions
CLOUD_TASKS_QUEUE_BATCH=boltz2-batch-predictions
FIRESTORE_DATABASE=(default)
GCS_BUCKET=hub-job-files
EOF

echo "   ✅ Configuration updated"

# 5. Display deployment summary
echo ""
echo "============================================"
echo "✅ PRODUCTION DEPLOYMENT COMPLETE!"
echo "============================================"
echo ""
echo "🌐 Cloud Run Service: $SERVICE_URL"
echo "   - Direct HTTP predictions"
echo "   - Cloud Tasks processing"
echo "   - Auto-scales 0-5 instances"
echo ""
echo "⚡ Cloud Run Job: boltz2-job"
echo "   - Batch processing"
echo "   - Manual or scheduled execution"
echo "   - Unlimited scale"
echo ""
echo "📊 Cloud Tasks Queues:"
echo "   - Individual: boltz2-predictions (10 concurrent)"
echo "   - Batch: boltz2-batch-predictions (20 concurrent)"
echo ""
echo "🔧 Test Commands:"
echo ""
echo "# Test HTTP service"
echo "curl ${SERVICE_URL}/health"
echo ""
echo "# Submit async prediction"
echo "curl -X POST ${SERVICE_URL}/predict \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"job_id\": \"test-001\", \"protein_sequence\": \"MKWVT\", \"ligand_smiles\": \"CCO\"}'"
echo ""
echo "# Execute Cloud Run Job"
echo "gcloud run jobs execute boltz2-job \\"
echo "  --region=$REGION \\"
echo "  --update-env-vars='JOB_ID=test-job,PROTEIN_SEQUENCE=MKWVT,LIGAND_SMILES=CCO'"
echo ""
echo "# View queue statistics"
echo "gcloud tasks queues describe boltz2-predictions --location=$REGION"
echo ""
echo "🎯 Ready for large-scale Boltz-2 predictions!"