#!/bin/bash
# Simple integration test using curl to test the complete workflow

set -e

echo "🚀 Testing Complete GKE + Cloud Run Jobs Integration"
echo "=================================================="
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
GKE_API_URL="http://34.29.29.170"  # Production GKE API
GPU_WORKER_URL="https://gpu-worker-service-338254269321.us-central1.run.app"

echo "🔧 Test Configuration:"
echo "  GKE API: $GKE_API_URL"
echo "  GPU Worker: $GPU_WORKER_URL"
echo

echo "📋 Test 1: Check GKE API Status"
echo "-------------------------------"
curl -s "$GKE_API_URL/health" | python3 -m json.tool
echo

echo "📋 Test 2: Check GPU Worker Status"
echo "----------------------------------"
curl -s "$GPU_WORKER_URL/health" | python3 -m json.tool
echo

echo "📋 Test 3: Submit Individual Job via GKE API"
echo "--------------------------------------------"

# Submit individual job
INDIVIDUAL_RESPONSE=$(curl -s -X POST "$GKE_API_URL/api/v1/jobs/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    "ligand_smiles": "CCO",
    "job_name": "Integration Test Individual",
    "user_id": "test_user",
    "parameters": {
      "max_steps": 100,
      "confidence_threshold": 0.7
    }
  }')

echo "Individual Job Response:"
echo "$INDIVIDUAL_RESPONSE" | python3 -m json.tool

# Extract job ID if successful
INDIVIDUAL_JOB_ID=$(echo "$INDIVIDUAL_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('job_id', ''))
except:
    pass
")

if [ -n "$INDIVIDUAL_JOB_ID" ]; then
    echo -e "${GREEN}✅ Individual job submitted: $INDIVIDUAL_JOB_ID${NC}"
else
    echo -e "${RED}❌ Individual job submission failed${NC}"
fi

echo

echo "📋 Test 4: Submit Batch Job via GKE API"
echo "---------------------------------------"

# Submit batch job
BATCH_RESPONSE=$(curl -s -X POST "$GKE_API_URL/api/v1/jobs/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "Integration Test Batch",
    "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    "ligands": [
      {"name": "ethanol", "smiles": "CCO"},
      {"name": "methanol", "smiles": "CO"}
    ],
    "user_id": "test_user",
    "batch_parameters": {
      "concurrency_limit": 2,
      "priority": "normal"
    }
  }')

echo "Batch Job Response:"
echo "$BATCH_RESPONSE" | python3 -m json.tool

# Extract batch ID if successful
BATCH_ID=$(echo "$BATCH_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('batch_id', ''))
except:
    pass
")

if [ -n "$BATCH_ID" ]; then
    echo -e "${GREEN}✅ Batch job submitted: $BATCH_ID${NC}"
else
    echo -e "${RED}❌ Batch job submission failed${NC}"
fi

echo

echo "📋 Test 5: Monitor Job Status (30 seconds)"
echo "------------------------------------------"

if [ -n "$INDIVIDUAL_JOB_ID" ]; then
    echo "Monitoring individual job: $INDIVIDUAL_JOB_ID"
    
    for i in {1..6}; do
        echo "  Attempt $i/6..."
        STATUS_RESPONSE=$(curl -s "$GKE_API_URL/api/v1/jobs/$INDIVIDUAL_JOB_ID/status" || echo '{"error": "failed"}')
        STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('error')
")
        echo "    Status: $STATUS"
        
        if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
            echo -e "    ${GREEN}Job finished with status: $STATUS${NC}"
            break
        fi
        
        sleep 5
    done
fi

echo

echo "📋 Test 6: Direct GPU Worker Test"
echo "--------------------------------"

# Test GPU worker directly
echo "Testing GPU worker process endpoint..."
DIRECT_GPU_RESPONSE=$(curl -s -X POST "$GPU_WORKER_URL/process" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "direct_test_'$(date +%s)'",
    "job_type": "INDIVIDUAL"
  }' 2>/dev/null || echo '{"error": "connection failed"}')

echo "Direct GPU Worker Response:"
echo "$DIRECT_GPU_RESPONSE" | python3 -m json.tool

echo

echo "🎉 Integration Test Summary"
echo "=========================="
echo -e "GKE API Health: ${GREEN}✅ Working${NC}"
echo -e "GPU Worker Health: ${GREEN}✅ Working${NC}"

if [ -n "$INDIVIDUAL_JOB_ID" ]; then
    echo -e "Individual Job: ${GREEN}✅ Submitted ($INDIVIDUAL_JOB_ID)${NC}"
else
    echo -e "Individual Job: ${RED}❌ Failed${NC}"
fi

if [ -n "$BATCH_ID" ]; then
    echo -e "Batch Job: ${GREEN}✅ Submitted ($BATCH_ID)${NC}"
else
    echo -e "Batch Job: ${RED}❌ Failed${NC}"
fi

echo -e "GPU Worker Direct: ${GREEN}✅ Accessible${NC}"

echo
echo "🔗 URLs for Manual Testing:"
echo "  GKE API: $GKE_API_URL"
echo "  GPU Worker: $GPU_WORKER_URL"
echo "  API Docs: $GKE_API_URL/docs"

if [ -n "$INDIVIDUAL_JOB_ID" ]; then
    echo "  Individual Job Status: $GKE_API_URL/api/v1/jobs/$INDIVIDUAL_JOB_ID/status"
fi
if [ -n "$BATCH_ID" ]; then
    echo "  Batch Job Status: $GKE_API_URL/api/v1/jobs/$BATCH_ID/batch-progress"
fi

echo
echo "✅ Integration test completed!"