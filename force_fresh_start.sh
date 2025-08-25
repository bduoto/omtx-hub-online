#!/bin/bash
# Force a completely fresh start

echo "🔥 FORCING COMPLETELY FRESH FRONTEND START"
echo "========================================="

# Kill everything on port 5173
echo "1. Killing all processes on port 5173..."
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Kill all vite processes
echo "2. Killing all Vite processes..."
pkill -f vite 2>/dev/null || true
pkill -f "node.*dev" 2>/dev/null || true

sleep 2

# Clear all caches
echo "3. Clearing all caches..."
cd frontend
rm -rf node_modules/.vite
rm -rf node_modules/.cache
rm -rf dist
rm -rf .vite

# Verify backend is running
echo "4. Checking backend..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend is running"
else
    echo "   ❌ Backend not running - starting it..."
    cd ../backend
    python3 simplified_api.py &
    sleep 2
    cd ../frontend
fi

# Show environment
echo "5. Environment check:"
echo "   VITE_API_BASE_URL from .env: $(grep VITE_API_BASE_URL .env)"
echo "   Backend health: $(curl -s http://localhost:8000/health | jq -r .status 2>/dev/null || echo 'unknown')"

# Start on port 5174 to avoid cache issues
echo "6. Starting frontend on fresh port 5174..."
echo "   This avoids any browser caching issues"

# Export environment variable and start
export VITE_API_BASE_URL=http://localhost:8000
npx vite --port 5174 --host 0.0.0.0 --force

echo "✅ Frontend should start at: http://localhost:5174"
echo "   This is a completely fresh instance with no cache"