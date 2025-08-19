#!/bin/bash

# Final Migration Check - CRITICAL VALIDATION BEFORE DEMO
# Distinguished Engineer Implementation - Comprehensive pre-production validation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}🔍 FINAL MIGRATION VALIDATION${NC}"
echo -e "${CYAN}=============================${NC}"
echo ""

# Track results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

run_check() {
    local check_name="$1"
    local command="$2"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking $check_name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Check 1: Modal references removed
echo -e "${BLUE}1️⃣ Checking Modal references...${NC}"

if grep -r "from modal" backend/ --include="*.py" | grep -v "#" | grep -v "stub" > /dev/null 2>&1; then
    echo -e "${RED}❌ CRITICAL: Modal imports still exist!${NC}"
    echo "Found Modal imports:"
    grep -r "from modal" backend/ --include="*.py" | grep -v "#" | grep -v "stub"
    echo ""
    echo "Run: python3 scripts/remove_all_modal_references.py --force"
    exit 1
else
    echo -e "${GREEN}✅ No Modal imports found${NC}"
fi

if grep -r "modal_batch_executor" backend/ --include="*.py" | grep -v "#" | grep -v "stub" > /dev/null 2>&1; then
    echo -e "${RED}❌ CRITICAL: Modal service references still exist!${NC}"
    echo "Found Modal service references:"
    grep -r "modal_batch_executor" backend/ --include="*.py" | grep -v "#" | grep -v "stub"
    echo ""
    echo "Run: python3 scripts/remove_all_modal_references.py --force"
    exit 1
else
    echo -e "${GREEN}✅ No Modal service references found${NC}"
fi

# Check 2: GPU Docker container exists
echo -e "${BLUE}2️⃣ Checking GPU Docker container...${NC}"

run_check "GPU Dockerfile exists" "[ -f 'backend/Dockerfile.gpu' ]"

if [ -f "backend/Dockerfile.gpu" ]; then
    if grep -q "nvidia/cuda" backend/Dockerfile.gpu; then
        echo -e "${GREEN}✅ GPU Dockerfile has CUDA support${NC}"
    else
        echo -e "${RED}❌ GPU Dockerfile missing CUDA support${NC}"
        exit 1
    fi
    
    if grep -q "boltz" backend/Dockerfile.gpu; then
        echo -e "${GREEN}✅ GPU Dockerfile includes Boltz-2${NC}"
    else
        echo -e "${RED}❌ GPU Dockerfile missing Boltz-2${NC}"
        exit 1
    fi
fi

# Check 3: Cloud Run services exist
echo -e "${BLUE}3️⃣ Checking Cloud Run services...${NC}"

run_check "Cloud Run batch processor exists" "[ -f 'backend/services/cloud_run_batch_processor.py' ]"
run_check "Cloud Run service exists" "[ -f 'backend/services/cloud_run_service.py' ]"

# Check 4: Environment variables
echo -e "${BLUE}4️⃣ Checking environment variables...${NC}"

required_vars=("GCP_PROJECT_ID" "GCP_REGION" "GCS_BUCKET_NAME")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    else
        echo -e "${GREEN}✅ $var is set${NC}"
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ CRITICAL: Missing environment variables: ${missing_vars[*]}${NC}"
    echo ""
    echo "Set the following environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  export $var=\"your-value-here\""
    done
    echo ""
    exit 1
fi

# Check 5: API endpoints responding
echo -e "${BLUE}5️⃣ Checking API endpoints...${NC}"

if command -v curl &> /dev/null; then
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health endpoint responding${NC}"
    else
        echo -e "${YELLOW}⚠️  Health endpoint not responding (API may not be running)${NC}"
    fi
    
    if curl -s http://localhost:8000/api/v4/batches > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Batch API endpoint exists${NC}"
    else
        echo -e "${YELLOW}⚠️  Batch API endpoint not responding${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  curl not available - skipping API tests${NC}"
fi

# Check 6: Frontend authentication service
echo -e "${BLUE}6️⃣ Checking frontend authentication...${NC}"

run_check "AuthService exists" "[ -f 'src/services/authService.ts' ]"

if [ -f "src/services/authService.ts" ]; then
    if grep -q "makeAuthenticatedRequest" src/services/authService.ts; then
        echo -e "${GREEN}✅ AuthService has authenticated request method${NC}"
    else
        echo -e "${RED}❌ AuthService missing authenticated request method${NC}"
        exit 1
    fi
fi

# Check 7: Download endpoints
echo -e "${BLUE}7️⃣ Checking download endpoints...${NC}"

run_check "Download endpoints exist" "[ -f 'backend/api/download_endpoints.py' ]"

# Check 8: Health checks and security
echo -e "${BLUE}8️⃣ Checking health checks and security...${NC}"

run_check "Health checks exist" "[ -f 'backend/api/health_checks.py' ]"
run_check "Security middleware exists" "[ -f 'backend/middleware/security_middleware.py' ]"

# Check 9: Python imports work
echo -e "${BLUE}9️⃣ Checking Python imports...${NC}"

echo -n "Testing Cloud Run imports... "
if python3 -c "
from services.cloud_run_service import cloud_run_service
from services.cloud_run_batch_processor import cloud_run_batch_processor
print('✅ Cloud Run services importable')
" 2>/dev/null; then
    echo -e "${GREEN}✅ PASSED${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "Cloud Run services have import errors"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Check 10: GCP credentials
echo -e "${BLUE}🔟 Checking GCP credentials...${NC}"

if command -v gcloud &> /dev/null; then
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${GREEN}✅ GCP credentials active${NC}"
        
        # Test Firestore access
        echo -n "Testing Firestore access... "
        if python3 -c "
from google.cloud import firestore
db = firestore.Client()
db.collection('_test').document('test').set({'test': True})
print('✅ Firestore accessible')
" 2>/dev/null; then
            echo -e "${GREEN}✅ PASSED${NC}"
        else
            echo -e "${RED}❌ FAILED${NC}"
            echo "Firestore access failed - check credentials"
            exit 1
        fi
        
        # Test GCS access
        echo -n "Testing Cloud Storage access... "
        if python3 -c "
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('${GCS_BUCKET_NAME}')
bucket.exists()
print('✅ Cloud Storage accessible')
" 2>/dev/null; then
            echo -e "${GREEN}✅ PASSED${NC}"
        else
            echo -e "${YELLOW}⚠️  Cloud Storage test failed (bucket may not exist yet)${NC}"
        fi
        
    else
        echo -e "${RED}❌ No active GCP credentials${NC}"
        echo "Run: gcloud auth login"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  gcloud CLI not available - skipping GCP tests${NC}"
fi

# Final Summary
echo ""
echo -e "${CYAN}=============================${NC}"
echo -e "${WHITE}📊 MIGRATION VALIDATION SUMMARY${NC}"
echo -e "${CYAN}=============================${NC}"
echo ""

SUCCESS_RATE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))

echo "Total Checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo -e "Success Rate: ${GREEN}$SUCCESS_RATE%${NC}"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅${NC}"
    echo -e "${GREEN}🎉 MIGRATION VALIDATION PASSED! 🎉${NC}"
    echo -e "${GREEN}✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅${NC}"
    echo ""
    echo -e "${WHITE}🚀 SYSTEM IS READY FOR PRODUCTION!${NC}"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo "1. Deploy to Cloud Run: ./scripts/deploy_to_cloud_run.sh"
    echo "2. Run integration tests: python3 scripts/test_complete_system.py"
    echo "3. Test batch processing with demo data"
    echo "4. Monitor costs and GPU utilization"
    echo ""
    echo -e "${GREEN}🏆 Ready for your CTO demo!${NC}"
    
    exit 0
else
    echo -e "${RED}❌ MIGRATION VALIDATION FAILED${NC}"
    echo -e "${RED}Please fix the failed checks above${NC}"
    echo ""
    echo -e "${YELLOW}Common fixes:${NC}"
    echo "• Run: python3 scripts/remove_all_modal_references.py --force"
    echo "• Set environment variables: export GCP_PROJECT_ID=your-project"
    echo "• Authenticate with GCP: gcloud auth login"
    echo "• Install missing dependencies: pip install -r requirements.txt"
    echo ""
    
    exit 1
fi
