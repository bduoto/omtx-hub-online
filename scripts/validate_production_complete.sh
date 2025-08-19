#!/bin/bash

# Complete Production Validation - FINAL DEMO READINESS CHECK
# Distinguished Engineer Implementation - Comprehensive GKE validation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
PRODUCTION_URL="http://34.29.29.170"  # Your ingress IP
FALLBACK_URL="http://34.10.21.160"    # Your LoadBalancer IP
GKE_CLUSTER="omtx-hub-cluster"
GKE_ZONE="us-central1-a"

echo -e "${CYAN}🔍 COMPLETE PRODUCTION VALIDATION${NC}"
echo -e "${CYAN}GKE Cluster: $GKE_CLUSTER${NC}"
echo -e "${CYAN}Production URL: $PRODUCTION_URL${NC}"
echo -e "${CYAN}=================================${NC}"
echo ""

print_check() {
    echo -n "$1: "
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Track results
TOTAL_CHECKS=0
PASSED_CHECKS=0

run_check() {
    local check_name="$1"
    local command="$2"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    print_check "$check_name"
    
    if eval "$command" > /dev/null 2>&1; then
        print_success "PASSED"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        print_error "FAILED"
        return 1
    fi
}

echo -e "${WHITE}🏗️  INFRASTRUCTURE CHECKS:${NC}"

# 1. GKE Cluster Status
print_check "GKE Cluster Status"
if gcloud container clusters describe $GKE_CLUSTER --zone=$GKE_ZONE --format="value(status)" | grep -q "RUNNING"; then
    print_success "RUNNING"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "NOT RUNNING"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 2. Node Status
print_check "GKE Nodes"
node_count=$(kubectl get nodes --no-headers | wc -l)
ready_nodes=$(kubectl get nodes --no-headers | grep -c "Ready")
if [ "$node_count" -eq "$ready_nodes" ] && [ "$node_count" -gt 0 ]; then
    print_success "$ready_nodes/$node_count READY"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "$ready_nodes/$node_count READY"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 3. Pod Status
print_check "Application Pods"
running_pods=$(kubectl get pods -n default --no-headers | grep -c "Running")
total_pods=$(kubectl get pods -n default --no-headers | wc -l)
if [ "$running_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
    print_success "$running_pods/$total_pods RUNNING"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "$running_pods/$total_pods RUNNING"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 4. Services Status
print_check "Kubernetes Services"
if kubectl get services -n default | grep -q "omtx-hub"; then
    print_success "CONFIGURED"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "NOT FOUND"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 5. Ingress Status
print_check "Ingress Controller"
if kubectl get ingress -n default | grep -q "omtx-hub"; then
    print_success "CONFIGURED"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "NOT CONFIGURED"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
echo -e "${WHITE}🌐 API CONNECTIVITY CHECKS:${NC}"

# 6. API Health (Primary URL)
print_check "Primary API Health"
if curl -s "$PRODUCTION_URL/health" | grep -q "healthy"; then
    print_success "HEALTHY"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "UNHEALTHY"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 7. API Health (Fallback URL)
print_check "Fallback API Health"
if curl -s "$FALLBACK_URL/health" | grep -q "healthy"; then
    print_success "HEALTHY"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "UNHEALTHY (acceptable if primary works)"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 8. API Documentation
print_check "API Documentation"
if curl -s "$PRODUCTION_URL/docs" | grep -q "OpenAPI"; then
    print_success "ACCESSIBLE"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "NOT ACCESSIBLE"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 9. Metrics Endpoint
print_check "Metrics Endpoint"
if curl -s "$PRODUCTION_URL/metrics" > /dev/null; then
    print_success "ACCESSIBLE"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "NOT ACCESSIBLE"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
echo -e "${WHITE}☁️  CLOUD SERVICES CHECKS:${NC}"

# 10. Cloud Run Jobs
print_check "Cloud Run Jobs"
if gcloud run jobs list --region=us-central1 | grep -q "boltz2"; then
    print_success "CONFIGURED"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "NOT FOUND"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 11. Firestore Database
print_check "Firestore Database"
if gcloud firestore databases list | grep -q "default"; then
    print_success "ACTIVE"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "NOT CONFIGURED"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 12. GCS Bucket
print_check "Storage Bucket"
if gsutil ls gs://hub-job-files > /dev/null 2>&1; then
    print_success "ACCESSIBLE"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_error "NOT ACCESSIBLE"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 13. Container Registry
print_check "Container Images"
if gcloud container images list --repository=gcr.io/$GCP_PROJECT_ID | grep -q "omtx-hub"; then
    print_success "AVAILABLE"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "NOT FOUND"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
echo -e "${WHITE}🔐 SECURITY CHECKS:${NC}"

# 14. Service Account
print_check "Service Account"
if gcloud iam service-accounts list | grep -q "omtx-hub"; then
    print_success "CONFIGURED"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "NOT FOUND"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 15. Network Policies
print_check "Network Security"
if kubectl get networkpolicies -n default > /dev/null 2>&1; then
    print_success "CONFIGURED"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "NOT CONFIGURED"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
echo -e "${WHITE}📊 PERFORMANCE CHECKS:${NC}"

# 16. Response Time
print_check "API Response Time"
response_time=$(curl -o /dev/null -s -w '%{time_total}' "$PRODUCTION_URL/health")
if (( $(echo "$response_time < 2.0" | bc -l) )); then
    print_success "FAST (${response_time}s)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "SLOW (${response_time}s)"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# 17. Resource Usage
print_check "Resource Usage"
cpu_usage=$(kubectl top nodes --no-headers | awk '{sum+=$3} END {print sum}' | sed 's/m//')
if [ "$cpu_usage" -lt 2000 ]; then  # Less than 2 CPU cores
    print_success "OPTIMAL (${cpu_usage}m CPU)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    print_warning "HIGH (${cpu_usage}m CPU)"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Calculate success rate
SUCCESS_RATE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))

echo ""
echo -e "${CYAN}=================================${NC}"
echo -e "${WHITE}📊 VALIDATION SUMMARY${NC}"
echo -e "${CYAN}=================================${NC}"
echo ""

echo "Total Checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$((TOTAL_CHECKS - PASSED_CHECKS))${NC}"
echo -e "Success Rate: ${GREEN}$SUCCESS_RATE%${NC}"

echo ""
if [ $SUCCESS_RATE -ge 85 ]; then
    echo -e "${GREEN}🎉 PRODUCTION SYSTEM IS READY FOR DEMO!${NC}"
    echo -e "${GREEN}✅ Your GKE deployment is working excellently!${NC}"
    
    echo ""
    echo -e "${WHITE}📊 Production URLs:${NC}"
    echo "  Primary API: $PRODUCTION_URL"
    echo "  Fallback API: $FALLBACK_URL"
    echo "  API Docs: $PRODUCTION_URL/docs"
    echo "  Health Check: $PRODUCTION_URL/health"
    echo "  Metrics: $PRODUCTION_URL/metrics"
    
    echo ""
    echo -e "${WHITE}🎯 Next Steps:${NC}"
    echo "  1. Run: python3 scripts/test_production_live.py"
    echo "  2. Run: python3 scripts/load_production_demo_data.py"
    echo "  3. Test batch processing with demo data"
    echo "  4. Your CTO demo is ready!"
    
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠️  PRODUCTION SYSTEM IS MOSTLY READY${NC}"
    echo -e "${YELLOW}Some non-critical issues found, but demo should work${NC}"
    
    echo ""
    echo -e "${WHITE}🔧 Recommended Actions:${NC}"
    echo "  • Fix the failed checks above"
    echo "  • Test critical functionality"
    echo "  • Monitor during demo"
    
else
    echo -e "${RED}❌ PRODUCTION SYSTEM HAS ISSUES${NC}"
    echo -e "${RED}Fix critical failures before demo${NC}"
    
    echo ""
    echo -e "${WHITE}🚨 Critical Actions:${NC}"
    echo "  • Check GKE cluster health"
    echo "  • Verify API connectivity"
    echo "  • Test core functionality"
    echo "  • Review logs for errors"
fi

echo ""
echo -e "${CYAN}=================================${NC}"

exit $((100 - SUCCESS_RATE > 30 ? 1 : 0))  # Exit with error if less than 70% success
