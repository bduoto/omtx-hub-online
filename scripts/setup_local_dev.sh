#!/bin/bash
# OMTX-Hub Local Development Environment Setup
# Sets up frontend on port 8081 and backend with proper configuration

set -e

echo "🚀 Setting up OMTX-Hub Local Development Environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi
print_status "Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is required but not installed"
    exit 1
fi
print_status "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm is required but not installed"
    exit 1
fi
print_status "npm found: $(npm --version)"

# Setup backend environment
echo "🔧 Setting up backend environment..."

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
print_status "Virtual environment activated"

# Install backend dependencies
print_info "Installing backend dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please configure .env file with your credentials"
fi

# Setup frontend environment
echo "🎨 Setting up frontend environment..."
cd ..

# Install frontend dependencies
print_info "Installing frontend dependencies..."
npm install

# Create frontend .env if needed
if [ ! -f ".env.local" ]; then
    print_info "Creating frontend .env.local..."
    cat > .env.local << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
EOF
fi

# Create development scripts
echo "📝 Creating development scripts..."

# Backend start script
cat > start_backend_dev.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting OMTX-Hub Backend (Development Mode)"
cd backend
source venv/bin/activate
export ENVIRONMENT=development
export DEBUG=true
python main.py
EOF
chmod +x start_backend_dev.sh

# Frontend start script (port 8081)
cat > start_frontend_dev.sh << 'EOF'
#!/bin/bash
echo "🎨 Starting OMTX-Hub Frontend on port 8081"
export PORT=8081
npm run dev -- --port 8081
EOF
chmod +x start_frontend_dev.sh

# Combined start script
cat > start_dev.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting OMTX-Hub Development Environment"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:8081"

# Start backend in background
./start_backend_dev.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
./start_frontend_dev.sh &
FRONTEND_PID=$!

echo "✅ Development environment started"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Wait for user input to stop
echo "Press Ctrl+C to stop all services"
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
EOF
chmod +x start_dev.sh

print_status "Development environment setup complete!"

echo ""
echo "🎯 Next Steps:"
echo "1. Configure your .env file in the backend directory"
echo "2. Set up GCP credentials: gcloud auth application-default login"
echo "3. Set up Modal credentials: modal token set"
echo "4. Run: ./start_dev.sh to start both services"
echo ""
echo "📍 URLs:"
echo "   Backend API: http://localhost:8000"
echo "   Frontend App: http://localhost:8081"
echo "   API Docs: http://localhost:8000/docs"
echo ""
