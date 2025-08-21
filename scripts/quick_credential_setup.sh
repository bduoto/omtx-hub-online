#!/bin/bash
# OMTX-Hub Quick Credential Setup Script
# This script helps you quickly set up GCP and Modal credentials

set -e

echo "🚀 OMTX-Hub Quick Credential Setup"
echo "=================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ID="om-models"

echo "📋 Step 1: Setting up GCP Service Account"
echo "----------------------------------------"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first:${NC}"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged into gcloud. Please run:${NC}"
    echo "   gcloud auth login"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI ready${NC}"

# Create service account if it doesn't exist
SA_EMAIL="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &> /dev/null; then
    echo "🔧 Creating service account..."
    gcloud iam service-accounts create omtx-hub-service \
        --description="OMTX-Hub production service account" \
        --display-name="OMTX-Hub Service Account" \
        --project=$PROJECT_ID
    
    # Wait for service account to be fully created
    echo "⏳ Waiting for service account to be ready..."
    sleep 5
    
    # Verify service account exists
    if ! gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &> /dev/null; then
        echo -e "${RED}❌ Failed to create service account${NC}"
        exit 1
    fi
    
    echo "🔐 Granting permissions..."
    # Add roles one by one with error handling
    for role in "roles/datastore.user" "roles/storage.admin" "roles/storage.objectAdmin"; do
        echo "   Adding role: $role"
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role" \
            --project=$PROJECT_ID || echo -e "${YELLOW}⚠️  Warning: Could not add $role (may already exist)${NC}"
    done
    
    echo -e "${GREEN}✅ Service account created and configured${NC}"
else
    echo -e "${GREEN}✅ Service account already exists${NC}"
    
    # Ensure permissions are set even if account exists
    echo "🔐 Ensuring permissions are configured..."
    for role in "roles/datastore.user" "roles/storage.admin" "roles/storage.objectAdmin"; do
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role" \
            --project=$PROJECT_ID &> /dev/null || true
    done
fi

# Generate key
KEY_FILE="$HOME/omtx-hub-credentials.json"
if [ ! -f "$KEY_FILE" ]; then
    echo "🔑 Generating service account key..."
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account=$SA_EMAIL \
        --project=$PROJECT_ID
    echo -e "${GREEN}✅ Key saved to: $KEY_FILE${NC}"
else
    echo -e "${YELLOW}⚠️  Key file already exists at: $KEY_FILE${NC}"
    read -p "Do you want to generate a new key? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account=$SA_EMAIL \
            --project=$PROJECT_ID
        echo -e "${GREEN}✅ New key generated${NC}"
    fi
fi

echo
echo "📋 Step 2: Modal Token Setup"
echo "----------------------------"

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo -e "${YELLOW}⚠️  Modal CLI not found. Installing...${NC}"
    pip install modal
fi

# Check if authenticated
if ! modal token show &> /dev/null; then
    echo "🔐 Setting up Modal authentication..."
    echo "This will open a browser for authentication..."
    modal token new
else
    echo -e "${GREEN}✅ Modal already authenticated${NC}"
fi

# Get token values
MODAL_CONFIG="$HOME/.modal.toml"
if [ -f "$MODAL_CONFIG" ]; then
    echo "📋 Your Modal tokens:"
    cat "$MODAL_CONFIG"
else
    echo -e "${RED}❌ Modal config not found${NC}"
    exit 1
fi

echo
echo "📋 Step 3: Generating Secrets"
echo "-----------------------------"

# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)
WEBHOOK_SECRET=$(openssl rand -hex 32)

echo -e "${GREEN}✅ Generated JWT secret: ${JWT_SECRET:0:10}...${NC}"
echo -e "${GREEN}✅ Generated webhook secret: ${WEBHOOK_SECRET:0:10}...${NC}"

echo
echo "📋 Step 4: Creating Environment File"
echo "-----------------------------------"

# Create environment file for local testing
ENV_FILE=".env.production"
cat > "$ENV_FILE" <<EOF
# GCP Configuration
GOOGLE_CLOUD_PROJECT=om-models
GCP_CREDENTIALS_JSON=$(cat "$KEY_FILE" | jq -c .)

# Modal Configuration (get from ~/.modal.toml)
MODAL_TOKEN_ID=$(grep -A 10 '\[default\]' "$MODAL_CONFIG" | grep 'token_id' | cut -d'"' -f2)
MODAL_TOKEN_SECRET=$(grep -A 10 '\[default\]' "$MODAL_CONFIG" | grep 'token_secret' | cut -d'"' -f2)

# Generated Secrets
JWT_SECRET_KEY=$JWT_SECRET
MODAL_WEBHOOK_SECRET=$WEBHOOK_SECRET

# Optional
REDIS_PASSWORD=""
EOF

echo -e "${GREEN}✅ Created environment file: $ENV_FILE${NC}"

echo
echo "📋 Step 5: Updating Kubernetes Secrets"
echo "--------------------------------------"

# Update production secrets file with real values
SECRETS_FILE="production-secrets.yaml"
if [ -f "$SECRETS_FILE" ]; then
    # Create backup
    cp "$SECRETS_FILE" "${SECRETS_FILE}.backup"
    
    # Update with real values
    sed -i.tmp "s|YOUR_PRIVATE_KEY_ID|$(jq -r .private_key_id "$KEY_FILE")|g" "$SECRETS_FILE"
    sed -i.tmp "s|YOUR_PRIVATE_KEY_CONTENT|$(jq -r .private_key "$KEY_FILE" | sed 's/\\n/\\\\n/g')|g" "$SECRETS_FILE"
    sed -i.tmp "s|YOUR_CLIENT_ID|$(jq -r .client_id "$KEY_FILE")|g" "$SECRETS_FILE"
    sed -i.tmp "s|ak-YOUR_ACTUAL_MODAL_TOKEN_ID|$(grep -A 10 '\[default\]' "$MODAL_CONFIG" | grep 'token_id' | cut -d'"' -f2)|g" "$SECRETS_FILE"
    sed -i.tmp "s|as-YOUR_ACTUAL_MODAL_TOKEN_SECRET|$(grep -A 10 '\[default\]' "$MODAL_CONFIG" | grep 'token_secret' | cut -d'"' -f2)|g" "$SECRETS_FILE"
    sed -i.tmp "s|GENERATE_WITH_OPENSSL_RAND_HEX_32|$JWT_SECRET|g" "$SECRETS_FILE"
    
    # Clean up temp files
    rm -f "${SECRETS_FILE}.tmp"
    
    echo -e "${GREEN}✅ Updated Kubernetes secrets file${NC}"
else
    echo -e "${RED}❌ Kubernetes secrets file not found${NC}"
fi

echo
echo "🎯 Next Steps"
echo "============"
echo "1. Review the updated secrets file: $SECRETS_FILE"
echo "2. Apply to your cluster: kubectl apply -f $SECRETS_FILE"
echo "3. Restart deployment: kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub"
echo "4. Test with: python scripts/validate_credentials.py"
echo
echo -e "${GREEN}🎉 Setup complete! Your credentials are ready for production.${NC}"