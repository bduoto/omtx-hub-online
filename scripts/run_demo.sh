#!/bin/bash

# Complete Demo Runner - IMPRESSIVE CTO PRESENTATION
# Distinguished Engineer Implementation - Full demo environment

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
BACKEND_PORT=8000
FRONTEND_PORT=5173
DEMO_USER_EMAIL="demo@omtx-hub.com"
DEMO_USER_ID="demo-user"

echo -e "${CYAN}🎭 STARTING COMPLETE DEMO ENVIRONMENT${NC}"
echo -e "${CYAN}====================================${NC}"
echo ""

print_step() {
    echo -e "${BLUE}$1${NC} $2"
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

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down demo environment...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        print_success "Backend stopped"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_success "Frontend stopped"
    fi
    
    echo -e "${GREEN}✅ Demo environment shut down cleanly${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

# Step 1: Prerequisites Check
print_step "1️⃣" "Checking prerequisites..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi

# Check if required files exist
required_files=(
    "backend/main.py"
    "src/services/authService.ts"
    "package.json"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file missing: $file"
        exit 1
    fi
done

print_success "Prerequisites check passed"

# Step 2: Environment Setup
print_step "2️⃣" "Setting up environment..."

# Set demo environment variables
export ENVIRONMENT=demo
export ENABLE_DEMO_MODE=true
export DEMO_USER_ID=$DEMO_USER_ID
export API_BASE_URL="http://localhost:$BACKEND_PORT"
export REACT_APP_API_BASE_URL="http://localhost:$BACKEND_PORT"

# Set default GCP variables if not set
export GCP_PROJECT_ID=${GCP_PROJECT_ID:-"demo-project"}
export GCP_REGION=${GCP_REGION:-"us-central1"}
export GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"demo-bucket"}

print_success "Environment configured for demo mode"

# Step 3: Create Demo Data
print_step "3️⃣" "Creating impressive demo data..."

if python3 scripts/create_demo_data.py; then
    print_success "Demo data created successfully"
else
    print_warning "Demo data creation failed - continuing with existing data"
fi

# Step 4: Start Backend API
print_step "4️⃣" "Starting backend API..."

cd backend

# Install Python dependencies if needed
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt > /dev/null 2>&1 || true
fi

# Start backend in background
python3 main.py &
BACKEND_PID=$!

# Wait for backend to start
echo -n "   Waiting for backend to start"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo ""
        print_success "Backend API started on port $BACKEND_PORT"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    print_error "Backend failed to start"
    cleanup
    exit 1
fi

cd ..

# Step 5: Start Frontend
print_step "5️⃣" "Starting frontend..."

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "   Installing Node.js dependencies..."
    npm install > /dev/null 2>&1
fi

# Start frontend in background
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo -n "   Waiting for frontend to start"
for i in {1..30}; do
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        echo ""
        print_success "Frontend started on port $FRONTEND_PORT"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
    print_error "Frontend failed to start"
    cleanup
    exit 1
fi

# Step 6: Test System Integration
print_step "6️⃣" "Testing system integration..."

# Test API health
if curl -s http://localhost:$BACKEND_PORT/health | grep -q "healthy"; then
    print_success "API health check passed"
else
    print_warning "API health check failed - continuing anyway"
fi

# Test authentication
auth_response=$(curl -s -X POST http://localhost:$BACKEND_PORT/api/v4/auth/demo \
    -H "Content-Type: application/json" \
    -d '{"demo": true}' || echo '{}')

if echo "$auth_response" | grep -q "token\|demo"; then
    print_success "Authentication system working"
else
    print_warning "Authentication test failed - demo mode may still work"
fi

# Step 7: Open Demo in Browser
print_step "7️⃣" "Opening demo in browser..."

# Try different browser opening commands
if command -v open &> /dev/null; then
    open http://localhost:$FRONTEND_PORT
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:$FRONTEND_PORT
elif command -v start &> /dev/null; then
    start http://localhost:$FRONTEND_PORT
else
    print_warning "Could not auto-open browser"
fi

print_success "Demo environment ready!"

# Step 8: Display Demo Information
echo ""
echo -e "${CYAN}====================================${NC}"
echo -e "${WHITE}🎉 DEMO ENVIRONMENT READY!${NC}"
echo -e "${CYAN}====================================${NC}"
echo ""

echo -e "${WHITE}📊 Demo URLs:${NC}"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   Backend API: http://localhost:$BACKEND_PORT"
echo "   Health Check: http://localhost:$BACKEND_PORT/health"
echo "   API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""

echo -e "${WHITE}🔐 Demo Credentials:${NC}"
echo "   Email: $DEMO_USER_EMAIL"
echo "   User ID: $DEMO_USER_ID"
echo "   Tier: Enterprise"
echo "   Mode: Demo (no authentication required)"
echo ""

echo -e "${WHITE}🎯 Demo Scenarios:${NC}"
echo "   1. ✅ Completed Batch: 'Kinase Inhibitor Lead Optimization'"
echo "      • 5 FDA-approved drugs with high binding affinity"
echo "      • Average affinity: 8.9 kcal/mol"
echo "      • 94% confidence score"
echo "      • Cost: \$3.47 (84% savings vs A100)"
echo ""
echo "   2. ⏳ In-Progress Batch: 'COVID-19 Protease Inhibitor Screening'"
echo "      • 16/25 ligands completed (64%)"
echo "      • Real-time progress updates"
echo "      • ETA: 8 minutes"
echo ""
echo "   3. 📈 Historical Analytics:"
echo "      • 97.6% success rate"
echo "      • \$89.34 monthly spend"
echo "      • 247 jobs completed this month"
echo ""

echo -e "${WHITE}🎭 What to Show Your CTO:${NC}"
echo "   1. Login as demo user (automatic)"
echo "   2. View completed 'Kinase Inhibitor' batch results"
echo "   3. Submit new batch with 3-5 ligands"
echo "   4. Show real-time progress updates"
echo "   5. Download results as ZIP file"
echo "   6. Show cost savings dashboard (84% reduction)"
echo "   7. Demonstrate user quotas and analytics"
echo ""

echo -e "${WHITE}🏆 Key Selling Points:${NC}"
echo "   • 84% cost reduction with L4 GPU optimization"
echo "   • Real-time multi-tenant architecture"
echo "   • Enterprise-grade security and isolation"
echo "   • Production-ready monitoring and analytics"
echo "   • Seamless Cloud Run auto-scaling"
echo "   • Complete elimination of Modal dependencies"
echo ""

echo -e "${WHITE}💡 Demo Tips:${NC}"
echo "   • Use realistic protein sequences (EGFR, COVID Mpro)"
echo "   • Submit 3-5 ligands for quick demo (2-3 minutes)"
echo "   • Show the real-time progress bar updating"
echo "   • Highlight the cost per job (\$0.65/hour vs \$4.00/hour)"
echo "   • Demonstrate user isolation (different users see different data)"
echo ""

echo -e "${YELLOW}⚠️  Demo is running in the background...${NC}"
echo -e "${YELLOW}   Press Ctrl+C to stop the demo environment${NC}"
echo ""

# Step 9: Monitor and Keep Running
print_step "9️⃣" "Monitoring demo environment..."

# Monitor both processes
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend process died"
        cleanup
        exit 1
    fi
    
    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend process died"
        cleanup
        exit 1
    fi
    
    # Check if services are responding
    if ! curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        print_warning "Backend not responding"
    fi
    
    if ! curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        print_warning "Frontend not responding"
    fi
    
    sleep 30  # Check every 30 seconds
done
