#!/bin/bash
# Quick fix script for frontend to backend connectivity

echo "🔧 QUICK FIX FOR FRONTEND-BACKEND CONNECTIVITY"
echo "=============================================="
echo ""
echo "This script will help fix the frontend issues."
echo ""

# Step 1: Update frontend environment
echo "📝 Step 1: Update frontend environment configuration"
echo ""
echo "Add these to your frontend/.env file:"
echo ""
cat << 'EOF'
# Frontend Environment Configuration
VITE_API_BASE_URL=http://34.29.29.170
VITE_GPU_WORKER_URL=https://boltz2-production-v2-zhye5az7za-uc.a.run.app
VITE_ENABLE_MOCK_DATA=false
VITE_POLLING_INTERVAL=5000
EOF

echo ""
echo "---"
echo ""

# Step 2: Fix CORS on backend
echo "📝 Step 2: Backend CORS Configuration"
echo ""
echo "The backend at 34.29.29.170 needs CORS headers."
echo "To fix this, you need to:"
echo ""
echo "1. SSH into your GKE cluster or update the deployment"
echo "2. Ensure the backend has these CORS settings:"
echo ""
cat << 'EOF'
# In your FastAPI backend main.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
EOF

echo ""
echo "---"
echo ""

# Step 3: Test endpoints
echo "📝 Step 3: Test the endpoints"
echo ""
echo "Test these endpoints to ensure they work:"
echo ""
echo "# Test backend health"
echo "curl http://34.29.29.170/health"
echo ""
echo "# Test jobs listing (should return empty array or jobs)"
echo 'curl "http://34.29.29.170/api/v1/jobs?user_id=current_user&limit=200"'
echo ""
echo "# Test GPU worker"
echo "curl https://boltz2-production-v2-zhye5az7za-uc.a.run.app/health"
echo ""

echo "---"
echo ""

# Step 4: Frontend modifications
echo "📝 Step 4: Frontend Code Fixes"
echo ""
echo "In frontend/src/stores/unifiedJobStore.ts, update the API calls:"
echo ""
cat << 'EOF'
// Fix the preload function to handle 422 errors gracefully
private async _doPreload(): Promise<void> {
  try {
    const response = await fetch(
      `${this.apiBaseUrl}/api/v1/jobs?user_id=current_user&limit=200`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    if (!response.ok) {
      // Return empty array on error instead of throwing
      console.warn('Jobs preload failed, using empty state');
      this.cachedJobs = [];
      return;
    }
    
    const data = await response.json();
    this.cachedJobs = data.jobs || [];
  } catch (error) {
    console.warn('Jobs preload error:', error);
    this.cachedJobs = [];
  }
}
EOF

echo ""
echo "---"
echo ""

# Step 5: Run the simplified API locally if needed
echo "📝 Step 5: Alternative - Run Simplified API Locally"
echo ""
echo "If the backend isn't working, run this locally:"
echo ""
echo "cd backend"
echo "python3 simplified_api.py"
echo ""
echo "Then update frontend/.env to use:"
echo "VITE_API_BASE_URL=http://localhost:8000"
echo ""

echo "=============================================="
echo "🎯 QUICK FIX STEPS COMPLETE"
echo "=============================================="
echo ""
echo "Follow the steps above to fix the connectivity issues."
echo ""
echo "Priority actions:"
echo "1. Update frontend/.env with correct API URLs"
echo "2. Ensure backend has CORS enabled"
echo "3. Test endpoints manually"
echo "4. Update frontend error handling"
echo ""
echo "If you need to redeploy the backend with fixes:"
echo "  gcloud auth login"
echo "  kubectl apply -f backend/k8s/deployment.yaml"