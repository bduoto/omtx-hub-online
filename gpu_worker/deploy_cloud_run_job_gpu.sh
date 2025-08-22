#!/bin/bash
# Alternative: Deploy as Cloud Run Job with GPU (Better GPU Support)
# Cloud Run Jobs have more mature GPU support than Cloud Run Services

set -e

PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${REGION:-"us-central1"}
JOB_NAME="boltz2-gpu-job"
IMAGE="gcr.io/om-models/boltz2-worker:v1"
SERVICE_ACCOUNT="boltz2-gpu-worker@om-models.iam.gserviceaccount.com"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎯 Cloud Run Jobs GPU Deployment (Alternative Solution)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Using Cloud Run Jobs for better GPU support and job queuing"
echo ""

# Step 1: Create the job with GPU
echo -e "${YELLOW}🚀 Creating Cloud Run Job with GPU...${NC}"

gcloud beta run jobs create ${JOB_NAME} \
  --image=${IMAGE} \
  --region=${REGION} \
  --service-account=${SERVICE_ACCOUNT} \
  --memory=16Gi \
  --cpu=4 \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --task-timeout=30m \
  --parallelism=1 \
  --max-retries=2 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},GCS_BUCKET_NAME=hub-job-files,FIRESTORE_PROJECT_ID=${PROJECT_ID},NVIDIA_VISIBLE_DEVICES=all,CUDA_VISIBLE_DEVICES=0,GPU_TYPE=L4,ENVIRONMENT=production" \
  --project=${PROJECT_ID} || {
    echo -e "${YELLOW}Job might already exist, updating...${NC}"
    
    gcloud beta run jobs update ${JOB_NAME} \
      --image=${IMAGE} \
      --region=${REGION} \
      --service-account=${SERVICE_ACCOUNT} \
      --memory=16Gi \
      --cpu=4 \
      --gpu=1 \
      --gpu-type=nvidia-l4 \
      --task-timeout=30m \
      --parallelism=1 \
      --max-retries=2 \
      --set-env-vars="PROJECT_ID=${PROJECT_ID},GCS_BUCKET_NAME=hub-job-files,FIRESTORE_PROJECT_ID=${PROJECT_ID},NVIDIA_VISIBLE_DEVICES=all,CUDA_VISIBLE_DEVICES=0,GPU_TYPE=L4,ENVIRONMENT=production" \
      --project=${PROJECT_ID}
}

echo -e "${GREEN}✅ Cloud Run Job created/updated${NC}"

# Step 2: Create a wrapper Cloud Run Service (no GPU) to trigger jobs
echo -e "${YELLOW}🔧 Creating job trigger service...${NC}"

cat > job_trigger.py <<'EOF'
import os
import json
from flask import Flask, request, jsonify
from google.cloud import run_v2
from google.cloud import firestore
import uuid
from datetime import datetime

app = Flask(__name__)

# Initialize clients
jobs_client = run_v2.JobsClient()
db = firestore.Client()

PROJECT_ID = os.environ.get('PROJECT_ID', 'om-models')
REGION = os.environ.get('REGION', 'us-central1')
JOB_NAME = os.environ.get('JOB_NAME', 'boltz2-gpu-job')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "job-trigger"})

@app.route('/predict', methods=['POST'])
def trigger_prediction():
    """Trigger a Cloud Run Job for GPU prediction"""
    try:
        data = request.json
        job_id = data.get('job_id', str(uuid.uuid4()))
        
        # Store job request in Firestore
        job_doc = {
            'job_id': job_id,
            'status': 'queued',
            'created_at': datetime.utcnow(),
            'request_data': data
        }
        db.collection('jobs').document(job_id).set(job_doc)
        
        # Trigger Cloud Run Job
        job_path = f"projects/{PROJECT_ID}/locations/{REGION}/jobs/{JOB_NAME}"
        
        # Create execution request with job data as env vars
        execution_request = run_v2.RunJobRequest(
            name=job_path,
            overrides=run_v2.RunJobRequest.Overrides(
                container_overrides=[
                    run_v2.RunJobRequest.Overrides.ContainerOverride(
                        env=[
                            run_v2.EnvVar(name="JOB_ID", value=job_id),
                            run_v2.EnvVar(name="JOB_DATA", value=json.dumps(data))
                        ]
                    )
                ]
            )
        )
        
        # Execute job
        operation = jobs_client.run_job(request=execution_request)
        
        return jsonify({
            "job_id": job_id,
            "status": "job_triggered",
            "message": "GPU job has been queued for processing",
            "operation_name": operation.name
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get job status from Firestore"""
    try:
        doc = db.collection('jobs').document(job_id).get()
        if doc.exists:
            return jsonify(doc.to_dict())
        return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
EOF

# Create requirements for trigger service
cat > trigger_requirements.txt <<EOF
Flask==3.0.0
google-cloud-run==0.10.0
google-cloud-firestore==2.14.0
gunicorn==21.2.0
EOF

# Create Dockerfile for trigger service
cat > Dockerfile.trigger <<EOF
FROM python:3.11-slim
WORKDIR /app
COPY trigger_requirements.txt .
RUN pip install --no-cache-dir -r trigger_requirements.txt
COPY job_trigger.py .
CMD exec gunicorn --bind :\$PORT --workers 1 --threads 8 --timeout 0 job_trigger:app
EOF

# Build and deploy trigger service
echo -e "${YELLOW}📦 Building trigger service...${NC}"
docker build -f Dockerfile.trigger -t gcr.io/${PROJECT_ID}/boltz2-trigger:latest .
docker push gcr.io/${PROJECT_ID}/boltz2-trigger:latest

echo -e "${YELLOW}🚀 Deploying trigger service...${NC}"
gcloud run deploy boltz2-trigger \
  --image=gcr.io/${PROJECT_ID}/boltz2-trigger:latest \
  --region=${REGION} \
  --platform=managed \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=100 \
  --concurrency=1000 \
  --timeout=60 \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},REGION=${REGION},JOB_NAME=${JOB_NAME}" \
  --service-account=${SERVICE_ACCOUNT} \
  --no-allow-unauthenticated \
  --project=${PROJECT_ID}

TRIGGER_URL=$(gcloud run services describe boltz2-trigger \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format='value(status.url)')

echo ""
echo -e "${GREEN}🎉 Cloud Run Jobs GPU Solution Deployed!${NC}"
echo ""
echo -e "${BLUE}Architecture:${NC}"
echo "━━━━━━━━━━━━━"
echo "1. Trigger Service (No GPU): ${TRIGGER_URL}"
echo "   - Handles API requests"
echo "   - Queues jobs in Firestore"
echo "   - Triggers Cloud Run Jobs"
echo ""
echo "2. GPU Job (L4 GPU): ${JOB_NAME}"
echo "   - Processes predictions with GPU"
echo "   - Auto-scales based on queue"
echo "   - Updates results in Firestore"
echo ""

# Test execution
echo -e "${YELLOW}🧪 Testing job execution...${NC}"
AUTH_TOKEN=$(gcloud auth print-identity-token)

echo "1. Testing trigger service health..."
curl -s -H "Authorization: Bearer ${AUTH_TOKEN}" ${TRIGGER_URL}/health | jq .

echo ""
echo "2. Submitting test prediction..."
TEST_RESPONSE=$(curl -s -X POST ${TRIGGER_URL}/predict \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
    "ligand_smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
    "ligand_name": "ibuprofen"
  }')

echo "$TEST_RESPONSE" | jq .
JOB_ID=$(echo "$TEST_RESPONSE" | jq -r .job_id)

echo ""
echo -e "${BLUE}📋 Commands:${NC}"
echo "━━━━━━━━━━━━"
echo "View job executions:"
echo "  gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION}"
echo ""
echo "View job logs:"
echo "  gcloud run jobs executions logs --job=${JOB_NAME} --region=${REGION}"
echo ""
echo "Check job status:"
echo "  curl -H 'Authorization: Bearer \$(gcloud auth print-identity-token)' ${TRIGGER_URL}/status/${JOB_ID}"
echo ""

# Clean up temp files
rm -f job_trigger.py trigger_requirements.txt Dockerfile.trigger

echo -e "${GREEN}✨ Cloud Run Jobs GPU deployment complete!${NC}"
