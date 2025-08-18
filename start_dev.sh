#!/bin/bash

# Start OMTX-Hub Development Environment
# Backend on port 8000, Frontend on port 8081

set -e

echo "🚀 Starting OMTX-Hub Development Environment"
echo "============================================"

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes on the ports
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8081 | xargs kill -9 2>/dev/null || true
    
    echo "✅ Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if ports are available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Port 8000 is already in use"
    echo "   Please stop the service using port 8000 and try again"
    exit 1
fi

if lsof -Pi :8081 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Port 8081 is already in use"
    echo "   Please stop the service using port 8081 and try again"
    exit 1
fi

# Start backend
echo "🖥️ Starting backend (port 8000)..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies if needed
pip install -q -r requirements.txt

# Start backend in background
python main.py > ../backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend started (PID: $BACKEND_PID)"
        break
    fi
    sleep 1
done

cd ..

# Start frontend
echo "🌐 Starting frontend (port 8081)..."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend on port 8081
PORT=8081 npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 10

echo "✅ Frontend started (PID: $FRONTEND_PID)"

# Display service URLs
echo ""
echo "🎉 OMTX-Hub Development Environment Ready!"
echo "=========================================="
echo "Frontend: http://localhost:8081"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "📊 Service Status:"
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "📜 Logs:"
echo "Backend:  tail -f backend.log"
echo "Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep script running and wait for interrupt
while true; do
    sleep 1
    
    # Check if processes are still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process died. Check backend.log"
        cleanup
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend process died. Check frontend.log"
        cleanup
    fi
done