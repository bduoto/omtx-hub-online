#!/bin/bash
# Script to restart the frontend with corrected API URLs

echo "🔄 RESTARTING FRONTEND WITH FIXED API URLS"
echo "========================================="
echo ""

# Kill existing frontend process
echo "1. Stopping existing frontend processes..."
pkill -f "vite" 2>/dev/null || true
pkill -f "node.*5173" 2>/dev/null || true
sleep 2

# Verify port is free
if lsof -i:5173 >/dev/null 2>&1; then
    echo "   Force killing port 5173 processes..."
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Check if backend is running
echo ""
echo "2. Verifying backend is running..."
if curl -s http://localhost:8000/health >/dev/null; then
    echo "   ✅ Backend is healthy at http://localhost:8000"
else
    echo "   ❌ Backend not responding. Please start it first:"
    echo "      cd backend && python3 simplified_api.py"
    exit 1
fi

# Show environment configuration
echo ""
echo "3. Frontend environment configuration:"
cat frontend/.env 2>/dev/null || echo "No .env file found"

# Start frontend
echo ""
echo "4. Starting frontend development server..."
cd frontend
echo "   Starting in frontend directory..."

# Clear any cached modules
echo "   Clearing Vite cache..."
rm -rf node_modules/.vite 2>/dev/null || true

# Start the development server
echo "   Starting Vite dev server..."
npm run dev &

# Wait a moment for startup
sleep 3

echo ""
echo "========================================="
echo "✅ FRONTEND RESTART COMPLETE"
echo "========================================="
echo ""
echo "Frontend should now be running at: http://localhost:5173"
echo "Backend API endpoint: http://localhost:8000"
echo ""
echo "Open your browser and go to: http://localhost:5173"
echo "The console errors should now be fixed!"
echo ""
echo "If you still see errors, do a hard refresh: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)"