#!/bin/bash

echo "🧹 NUCLEAR CACHE CLEAR + FRESH START"
echo "===================================="

# Stop any existing frontend
pkill -f "vite" 2>/dev/null || true
sleep 2

cd frontend

# Nuclear cache clear
echo "Clearing ALL possible caches..."
rm -rf node_modules/.vite
rm -rf node_modules/.cache  
rm -rf dist
rm -rf .vite
rm -rf .turbo

# Clear npm cache for good measure
npm cache clean --force 2>/dev/null || true

# Set environment explicitly
export VITE_API_BASE_URL=http://localhost:8000

echo "Starting on port 5174 to avoid any browser cache..."
echo ""
echo "🚀 Frontend will be at: http://localhost:5174"
echo "📍 API will be at: http://localhost:8000"
echo ""

# Start on fresh port with force flag
npx vite --port 5174 --force --host 0.0.0.0