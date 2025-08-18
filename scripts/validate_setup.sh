#!/bin/bash

# Comprehensive setup validation script
# Validates all components of the OMTX-Hub setup

set -e

echo "🔍 OMTX-Hub Setup Validation"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Validation counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to check and report
check_status() {
    if [ $1 -eq 0 ]; then
        print_status "$2"
        ((PASSED++))
        return 0
    else
        print_error "$2"
        ((FAILED++))
        return 1
    fi
}

check_warning() {
    print_warning "$1"
    ((WARNINGS++))
}

echo "🔧 Environment Validation"
echo "========================="

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -d "backend" ]; then
    print_error "Please run this script from the omtx-hub project root directory"
    exit 1
fi
print_status "Running from correct directory"

# Check Python virtual environment
if [ -d "backend/venv" ]; then
    print_status "Python virtual environment exists"
    ((PASSED++))
else
    print_error "Python virtual environment not found"
    ((FAILED++))
fi

# Check node_modules
if [ -d "node_modules" ]; then
    print_status "Frontend dependencies installed"
    ((PASSED++))
else
    print_error "Frontend dependencies not installed (run npm install)"
    ((FAILED++))
fi

# Check environment file
if [ -f "backend/.env" ]; then
    print_status "Backend environment file exists"
    ((PASSED++))
    
    # Check for key environment variables
    if grep -q "GCP_PROJECT_ID=" "backend/.env"; then
        print_status "GCP project configured"
        ((PASSED++))
    else
        check_warning "GCP project not configured in .env"
    fi
    
    if grep -q "MODAL_TOKEN_ID=" "backend/.env"; then
        print_status "Modal tokens configured"
        ((PASSED++))
    else
        check_warning "Modal tokens not configured in .env"
    fi
else
    print_error "Backend environment file not found (run setup_gcp_project.sh)"
    ((FAILED++))
fi

echo ""
echo "🌐 Service Validation"
echo "===================="

# Check if services are running
backend_running=false
frontend_running=false

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Backend service running (port 8000)"
    backend_running=true
    ((PASSED++))
else
    print_error "Backend service not running (port 8000)"
    ((FAILED++))
fi

# Check frontend
if curl -s http://localhost:8081 > /dev/null 2>&1; then
    print_status "Frontend service running (port 8081)"
    frontend_running=true
    ((PASSED++))
else
    print_error "Frontend service not running (port 8081)"
    ((FAILED++))
fi

# If services are running, do deeper validation
if [ "$backend_running" = true ]; then
    echo ""
    echo "🔍 API Validation"
    echo "================"
    
    # Test API endpoints
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        print_status "API documentation accessible"
        ((PASSED++))
    else
        print_error "API documentation not accessible"
        ((FAILED++))
    fi
    
    # Test health endpoint
    health_response=$(curl -s http://localhost:8000/health 2>/dev/null || echo "failed")
    if [[ "$health_response" == *"healthy"* ]] || [[ "$health_response" == *"ok"* ]]; then
        print_status "Health endpoint responding correctly"
        ((PASSED++))
    else
        check_warning "Health endpoint response unclear: $health_response"
    fi
fi

echo ""
echo "☁️ Cloud Service Validation"
echo "==========================="

# Check GCP authentication
if command -v gcloud &> /dev/null; then
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_status "GCP authentication active"
        ((PASSED++))
        
        # Check project
        current_project=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ ! -z "$current_project" ]; then
            print_status "GCP project set: $current_project"
            ((PASSED++))
        else
            check_warning "No GCP project configured"
        fi
    else
        check_warning "GCP authentication not active (run: gcloud auth application-default login)"
    fi
else
    check_warning "GCP CLI not installed"
fi

# Check Modal authentication
if command -v modal &> /dev/null; then
    if modal token list > /dev/null 2>&1; then
        print_status "Modal authentication active"
        ((PASSED++))
    else
        check_warning "Modal authentication not active (run: modal token new)"
    fi
else
    check_warning "Modal CLI not installed"
fi

# Check Firebase CLI
if command -v firebase &> /dev/null; then
    print_status "Firebase CLI installed"
    ((PASSED++))
else
    check_warning "Firebase CLI not installed (needed for Firestore)"
fi

echo ""
echo "📊 Validation Summary"
echo "===================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo "⚠️ Warnings: $WARNINGS"

if [ $FAILED -eq 0 ]; then
    echo ""
    print_status "Setup validation PASSED! 🎉"
    echo ""
    echo "🚀 Ready to use:"
    echo "   Frontend: http://localhost:8081"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    if [ $WARNINGS -gt 0 ]; then
        echo "💡 Consider addressing the warnings above for full functionality"
    fi
    exit 0
else
    echo ""
    print_error "Setup validation FAILED"
    echo ""
    echo "🔧 Common solutions:"
    echo "1. Run setup scripts: ./scripts/setup_gcp_project.sh && ./scripts/setup_modal.sh"
    echo "2. Install dependencies: ./scripts/setup_local_dev.sh"
    echo "3. Start services: ./start_dev.sh"
    echo "4. Check logs for specific errors"
    exit 1
fi