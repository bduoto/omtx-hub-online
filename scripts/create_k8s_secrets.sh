#!/bin/bash
# Create Kubernetes secrets from actual credential files

set -e

echo "🔐 Creating Kubernetes Secrets from Credentials"
echo "=============================================="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if credentials exist
GCP_CREDS_FILE="$HOME/omtx-hub-credentials.json"
MODAL_CONFIG="$HOME/.modal.toml"

if [ ! -f "$GCP_CREDS_FILE" ]; then
    echo -e "${RED}❌ GCP credentials not found at $GCP_CREDS_FILE${NC}"
    echo "   Run: ./scripts/fix_service_account.sh first"
    exit 1
fi

if [ ! -f "$MODAL_CONFIG" ]; then
    echo -e "${RED}❌ Modal config not found at $MODAL_CONFIG${NC}"
    echo "   Run: modal token new"
    exit 1
fi

echo -e "${GREEN}✅ Found credential files${NC}"

# Extract Modal tokens
MODAL_TOKEN_ID=$(grep -A 10 '\[default\]' "$MODAL_CONFIG" | grep 'token_id' | cut -d'"' -f2)
MODAL_TOKEN_SECRET=$(grep -A 10 '\[default\]' "$MODAL_CONFIG" | grep 'token_secret' | cut -d'"' -f2)

if [ -z "$MODAL_TOKEN_ID" ] || [ -z "$MODAL_TOKEN_SECRET" ]; then
    echo -e "${RED}❌ Could not extract Modal tokens${NC}"
    exit 1
fi

echo "📋 Creating Kubernetes secret..."

# Delete existing secret if it exists
kubectl delete secret omtx-hub-secrets -n omtx-hub 2>/dev/null || true

# Create secret from literal values and files
kubectl create secret generic omtx-hub-secrets \
  --namespace=omtx-hub \
  --from-file=GCP_CREDENTIALS_JSON="$GCP_CREDS_FILE" \
  --from-literal=MODAL_TOKEN_ID="$MODAL_TOKEN_ID" \
  --from-literal=MODAL_TOKEN_SECRET="$MODAL_TOKEN_SECRET" \
  --from-literal=REDIS_PASSWORD="" \
  --from-literal=JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=MODAL_WEBHOOK_SECRET="$(openssl rand -hex 32)"

echo -e "${GREEN}✅ Secret created successfully${NC}"

# Verify secret
echo
echo "📋 Verifying secret..."
kubectl get secret omtx-hub-secrets -n omtx-hub -o json | jq '.data | keys'

echo
echo "🔄 Restarting deployment..."
kubectl rollout restart deployment/omtx-hub-backend -n omtx-hub

echo
echo "⏳ Waiting for rollout..."
kubectl rollout status deployment/omtx-hub-backend -n omtx-hub --timeout=120s

echo
echo -e "${GREEN}🎉 Deployment updated with real credentials!${NC}"
echo
echo "Test with:"
echo "  curl http://34.29.29.170/api/v1/system/status"