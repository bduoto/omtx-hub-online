#!/bin/bash

# OMTX-Hub GCP Project Setup Script
# Creates and configures all required GCP services

set -e

echo "🚀 OMTX-Hub GCP Project Setup"
echo "==============================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project configuration
read -p "Enter your GCP Project ID (or press Enter to create new): " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID="omtx-hub-$(date +%s)"
    echo "🆕 Creating new project: $PROJECT_ID"
    gcloud projects create $PROJECT_ID --name="OMTX-Hub"
else
    echo "📋 Using existing project: $PROJECT_ID"
fi

# Set the project
gcloud config set project $PROJECT_ID

echo "✅ Project configured: $PROJECT_ID"

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable \
    compute.googleapis.com \
    container.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    cloudbuild.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    secretmanager.googleapis.com

echo "✅ APIs enabled successfully"

# Check billing account
BILLING_ACCOUNT=$(gcloud billing accounts list --filter="open=true" --format="value(name)" | head -n1)
if [ -z "$BILLING_ACCOUNT" ]; then
    echo "⚠️ No billing account found. Please set up billing in the Google Cloud Console:"
    echo "   https://console.cloud.google.com/billing"
    echo "   Then link it to project: $PROJECT_ID"
else
    echo "💳 Linking billing account to project..."
    gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
    echo "✅ Billing account linked"
fi

# Set up Firebase project
echo "🔥 Setting up Firebase..."
if ! command -v firebase &> /dev/null; then
    echo "📦 Installing Firebase CLI..."
    npm install -g firebase-tools
fi

# Create Firebase configuration
echo "🔧 Configuring Firebase project..."
firebase use --add $PROJECT_ID

# Create default Firestore database
echo "🗃️ Creating Firestore database..."
gcloud firestore databases create --location=us-central

echo "✅ Firebase setup complete"

# Create storage bucket
BUCKET_NAME="${PROJECT_ID}-omtx-hub-storage"
echo "🪣 Creating Cloud Storage bucket: $BUCKET_NAME"
gsutil mb gs://$BUCKET_NAME/ || echo "Bucket already exists or created"

# Set bucket permissions
echo "🔐 Configuring bucket permissions..."
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME/ || true

echo "✅ Storage bucket created: $BUCKET_NAME"

# Create service account
SERVICE_ACCOUNT_NAME="omtx-hub-service"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "👤 Creating service account: $SERVICE_ACCOUNT_NAME"
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="OMTX-Hub Service Account" \
    --description="Service account for OMTX-Hub application" || echo "Service account already exists"

# Grant necessary roles
echo "🔑 Granting IAM roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/monitoring.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/logging.logWriter"

echo "✅ IAM roles configured"

# Generate service account key
KEY_FILE="$PWD/backend/gcp-service-account-key.json"
echo "🔑 Creating service account key: $KEY_FILE"
gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SERVICE_ACCOUNT_EMAIL"

echo "✅ Service account key created"

# Create .env file
echo "📝 Creating environment configuration..."
cat > backend/.env << EOF
# GCP Configuration
GCP_PROJECT_ID=$PROJECT_ID
GCP_BUCKET_NAME=$BUCKET_NAME
GOOGLE_APPLICATION_CREDENTIALS=gcp-service-account-key.json

# Firestore Configuration
FIRESTORE_PROJECT_ID=$PROJECT_ID

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Configuration
FRONTEND_URL=http://localhost:8081
CORS_ORIGINS=["http://localhost:8081", "http://localhost:3000", "http://localhost:5173"]

# Modal Configuration (to be configured separately)
MODAL_TOKEN_ID=your_modal_token_id
MODAL_TOKEN_SECRET=your_modal_token_secret

# Security
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
EOF

echo "✅ Environment file created: backend/.env"

# Display setup summary
echo ""
echo "🎉 GCP Setup Complete!"
echo "======================="
echo "Project ID: $PROJECT_ID"
echo "Storage Bucket: $BUCKET_NAME"
echo "Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "Service Account Key: $KEY_FILE"
echo "Environment File: backend/.env"
echo ""
echo "📋 Next Steps:"
echo "1. Configure Modal authentication (run setup_modal.sh)"
echo "2. Deploy Firestore indexes (run setup_firestore_indexes.sh)"
echo "3. Start the application (run start_dev.sh)"
echo ""
echo "🔗 Useful Links:"
echo "Google Cloud Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"
echo "Firestore Console: https://console.firebase.google.com/project/$PROJECT_ID/firestore"
echo "Storage Console: https://console.cloud.google.com/storage/browser?project=$PROJECT_ID"