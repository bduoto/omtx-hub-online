#!/bin/bash

# Deploy Frontend to Cloud Run - PRODUCTION HOSTING
# Distinguished Engineer Implementation - Complete frontend deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"om-models"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="omtx-hub-frontend"
BACKEND_URL="http://34.29.29.170"

echo -e "${CYAN}🌐 DEPLOYING FRONTEND TO CLOUD RUN${NC}"
echo -e "${CYAN}=================================${NC}"
echo ""

# Step 1: Create production environment file
echo -e "${BLUE}1️⃣${NC} Creating production environment..."
cat > .env.production << EOF
REACT_APP_API_BASE_URL=$BACKEND_URL
REACT_APP_ENVIRONMENT=production
REACT_APP_DEMO_MODE=true
REACT_APP_ENABLE_ANALYTICS=true
EOF

echo -e "${GREEN}✅ Production environment configured${NC}"

# Step 2: Build production frontend
echo -e "${BLUE}2️⃣${NC} Building production frontend..."
npm run build

echo -e "${GREEN}✅ Frontend built successfully${NC}"

# Step 3: Create Dockerfile for frontend
echo -e "${BLUE}3️⃣${NC} Creating frontend Dockerfile..."
cat > Dockerfile.frontend << EOF
# Frontend Dockerfile for Cloud Run
FROM nginx:alpine

# Copy built files
COPY dist/ /usr/share/nginx/html/

# Create nginx config for SPA
RUN echo 'server {' > /etc/nginx/conf.d/default.conf && \
    echo '    listen 8080;' >> /etc/nginx/conf.d/default.conf && \
    echo '    server_name localhost;' >> /etc/nginx/conf.d/default.conf && \
    echo '    root /usr/share/nginx/html;' >> /etc/nginx/conf.d/default.conf && \
    echo '    index index.html;' >> /etc/nginx/conf.d/default.conf && \
    echo '    location / {' >> /etc/nginx/conf.d/default.conf && \
    echo '        try_files \$uri \$uri/ /index.html;' >> /etc/nginx/conf.d/default.conf && \
    echo '    }' >> /etc/nginx/conf.d/default.conf && \
    echo '    location /api/ {' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_pass $BACKEND_URL;' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_set_header Host \$host;' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_set_header X-Real-IP \$remote_addr;' >> /etc/nginx/conf.d/default.conf && \
    echo '    }' >> /etc/nginx/conf.d/default.conf && \
    echo '}' >> /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
EOF

echo -e "${GREEN}✅ Frontend Dockerfile created${NC}"

# Step 4: Build and push container
echo -e "${BLUE}4️⃣${NC} Building and pushing container..."
docker build -f Dockerfile.frontend -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

echo -e "${GREEN}✅ Container pushed to registry${NC}"

# Step 5: Deploy to Cloud Run
echo -e "${BLUE}5️⃣${NC} Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --cpu=1 \
    --memory=512Mi \
    --min-instances=0 \
    --max-instances=10 \
    --set-env-vars="BACKEND_URL=$BACKEND_URL"

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo -e "${GREEN}✅ Frontend deployed successfully!${NC}"
echo ""
echo -e "${WHITE}📊 Frontend URLs:${NC}"
echo "  Production: $FRONTEND_URL"
echo "  Backend API: $BACKEND_URL"
echo ""
echo -e "${GREEN}🎉 Frontend is now live and ready for demo!${NC}"
