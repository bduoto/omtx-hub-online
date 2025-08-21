#!/bin/bash
# Fix service account permissions for OMTX-Hub

set -e

echo "🔧 OMTX-Hub Service Account Permission Fix"
echo "=========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ID="om-models"
SA_EMAIL="omtx-hub-service@${PROJECT_ID}.iam.gserviceaccount.com"

echo "📋 Checking service account status..."

# Check if service account exists
if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &> /dev/null; then
    echo -e "${GREEN}✅ Service account exists: $SA_EMAIL${NC}"
else
    echo -e "${RED}❌ Service account not found. Creating...${NC}"
    gcloud iam service-accounts create omtx-hub-service \
        --description="OMTX-Hub production service account" \
        --display-name="OMTX-Hub Service Account" \
        --project=$PROJECT_ID
    
    # Wait for creation
    sleep 5
fi

echo
echo "🔐 Setting up IAM permissions..."
echo "--------------------------------"

# Define required roles
ROLES=(
    "roles/datastore.user"
    "roles/storage.admin"
    "roles/storage.objectAdmin"
    "roles/firebase.viewer"
)

# Add each role
for role in "${ROLES[@]}"; do
    echo "Adding role: $role"
    if gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --project=$PROJECT_ID \
        --condition=None 2>/dev/null; then
        echo -e "  ${GREEN}✅ Added successfully${NC}"
    else
        # Try without condition flag
        if gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$role" \
            --project=$PROJECT_ID 2>/dev/null; then
            echo -e "  ${GREEN}✅ Added successfully${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Role may already exist or require additional permissions${NC}"
        fi
    fi
done

echo
echo "📋 Verifying permissions..."
echo "--------------------------"

# List current roles
echo "Current IAM roles for $SA_EMAIL:"
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:$SA_EMAIL" || echo "Could not list roles"

echo
echo "🔑 Generating service account key..."
echo "------------------------------------"

KEY_FILE="$HOME/omtx-hub-credentials.json"

# Check if key exists
if [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}⚠️  Key file already exists at: $KEY_FILE${NC}"
    read -p "Do you want to generate a new key? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing key file."
    else
        # Backup old key
        mv "$KEY_FILE" "${KEY_FILE}.backup.$(date +%s)"
        echo "Old key backed up."
        
        # Generate new key
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account=$SA_EMAIL \
            --project=$PROJECT_ID
        echo -e "${GREEN}✅ New key generated: $KEY_FILE${NC}"
    fi
else
    # Generate key
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account=$SA_EMAIL \
        --project=$PROJECT_ID
    echo -e "${GREEN}✅ Key generated: $KEY_FILE${NC}"
fi

echo
echo "📋 Key Information"
echo "-----------------"
echo "Service Account: $SA_EMAIL"
echo "Key File: $KEY_FILE"
echo "Project ID: $PROJECT_ID"

# Verify key format
if [ -f "$KEY_FILE" ]; then
    KEY_ID=$(jq -r .private_key_id "$KEY_FILE" 2>/dev/null || echo "unknown")
    CLIENT_ID=$(jq -r .client_id "$KEY_FILE" 2>/dev/null || echo "unknown")
    echo "Key ID: ${KEY_ID:0:10}..."
    echo "Client ID: ${CLIENT_ID:0:10}..."
fi

echo
echo "🎯 Next Steps"
echo "============"
echo "1. Run the full setup script: ./scripts/quick_credential_setup.sh"
echo "2. Or manually update production-secrets.yaml with the key from: $KEY_FILE"
echo "3. Apply to Kubernetes: kubectl apply -f production-secrets.yaml"
echo "4. Restart deployment: kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub"
echo
echo -e "${GREEN}🎉 Service account fix complete!${NC}"