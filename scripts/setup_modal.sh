#!/bin/bash

# Modal.com Setup Script
# Configures Modal authentication and deploys prediction functions

set -e

echo "🤖 OMTX-Hub Modal Setup"
echo "======================="

# Check if modal is installed
if ! command -v modal &> /dev/null; then
    echo "📦 Installing Modal CLI..."
    pip install modal
fi

# Check Modal authentication
echo "🔐 Checking Modal authentication..."
if ! modal token list &> /dev/null; then
    echo "🔑 Modal authentication required."
    echo "   1. Go to https://modal.com/settings/tokens"
    echo "   2. Create a new token"
    echo "   3. Run the command below with your token details:"
    echo ""
    echo "   modal token new"
    echo ""
    echo "   Then run this script again."
    exit 1
fi

echo "✅ Modal authentication verified"

# Get Modal token info for environment variables
echo "📋 Getting Modal token information..."
MODAL_TOKEN_INFO=$(modal token list --json | head -n1)
MODAL_TOKEN_ID=$(echo $MODAL_TOKEN_INFO | python3 -c "import sys, json; print(json.load(sys.stdin)['token_id'])")
MODAL_TOKEN_SECRET=$(echo $MODAL_TOKEN_INFO | python3 -c "import sys, json; print(json.load(sys.stdin)['token_secret'])")

echo "Token ID: $MODAL_TOKEN_ID"
echo "Token Secret: ${MODAL_TOKEN_SECRET:0:8}..."

# Update .env file with Modal credentials
ENV_FILE="backend/.env"
if [ -f "$ENV_FILE" ]; then
    echo "🔧 Updating environment file with Modal credentials..."
    
    # Update Modal configuration in .env
    sed -i.bak "s/MODAL_TOKEN_ID=.*/MODAL_TOKEN_ID=$MODAL_TOKEN_ID/" "$ENV_FILE"
    sed -i.bak "s/MODAL_TOKEN_SECRET=.*/MODAL_TOKEN_SECRET=$MODAL_TOKEN_SECRET/" "$ENV_FILE"
    
    echo "✅ Environment file updated"
else
    echo "❌ Environment file not found: $ENV_FILE"
    echo "   Please run setup_gcp_project.sh first"
    exit 1
fi

# Check if Modal apps exist and deploy them
echo "🚀 Checking Modal app deployments..."

# Create a simple test to verify Modal setup
cat > test_modal_setup.py << 'EOF'
#!/usr/bin/env python3
"""
Test Modal setup and deployment
"""
import modal
import os

# Test Modal authentication
try:
    stub = modal.Stub("omtx-hub-test")
    
    @stub.function(
        image=modal.Image.debian_slim().pip_install("requests"),
        timeout=60
    )
    def test_function():
        return "Modal setup successful!"
    
    # Test the function
    with stub.run():
        result = test_function.remote()
        print(f"✅ Modal test successful: {result}")
        
except Exception as e:
    print(f"❌ Modal test failed: {e}")
    exit(1)
EOF

echo "🧪 Testing Modal connection..."
python3 test_modal_setup.py

# Clean up test file
rm test_modal_setup.py

# Check if Boltz-2 app needs to be deployed
echo "🔬 Checking Boltz-2 Modal app deployment..."

# Create a deployment verification script
cat > verify_modal_apps.py << 'EOF'
#!/usr/bin/env python3
"""
Verify Modal app deployments
"""
import subprocess
import sys

def check_app_deployed(app_name):
    try:
        result = subprocess.run(['modal', 'app', 'list'], capture_output=True, text=True)
        return app_name in result.stdout
    except:
        return False

def main():
    required_apps = ['boltz2-app', 'omtx-hub-production']
    
    print("📋 Checking Modal app deployments...")
    
    missing_apps = []
    for app in required_apps:
        if check_app_deployed(app):
            print(f"✅ {app}: Deployed")
        else:
            print(f"⚠️ {app}: Not deployed")
            missing_apps.append(app)
    
    if missing_apps:
        print(f"\n📝 Missing apps: {', '.join(missing_apps)}")
        print("📚 To deploy apps:")
        print("   1. Navigate to backend/modal_apps/")
        print("   2. Run: modal deploy boltz2_app.py")
        print("   3. Run: modal deploy production_modal_service.py")
        return False
    else:
        print("\n✅ All required Modal apps are deployed!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

python3 verify_modal_apps.py
APPS_STATUS=$?

# Clean up verification script
rm verify_modal_apps.py

if [ $APPS_STATUS -eq 0 ]; then
    echo "✅ Modal apps verified"
else
    echo "⚠️ Some Modal apps need deployment"
    echo "   This is normal for first-time setup"
    echo "   Apps will be deployed when you run the backend"
fi

# Create webhook configuration script
echo "🪝 Creating webhook configuration..."
cat > configure_modal_webhooks.py << 'EOF'
#!/usr/bin/env python3
"""
Configure Modal webhooks for production deployment
"""
import argparse
import os
import secrets
import requests

def generate_webhook_secret():
    """Generate a secure webhook secret"""
    return secrets.token_urlsafe(32)

def configure_webhooks(environment, base_url):
    """Configure Modal webhooks for the specified environment"""
    
    webhook_secret = generate_webhook_secret()
    webhook_url = f"{base_url}/api/v3/webhooks/modal/completion"
    
    print(f"🪝 Configuring webhooks for {environment}...")
    print(f"   Webhook URL: {webhook_url}")
    print(f"   Secret: {webhook_secret[:8]}...")
    
    # Update environment file
    env_file = f"backend/.env.{environment}" if environment != "development" else "backend/.env"
    
    if os.path.exists(env_file):
        with open(env_file, "a") as f:
            f.write(f"\n# Modal Webhook Configuration\n")
            f.write(f"MODAL_WEBHOOK_SECRET={webhook_secret}\n")
            f.write(f"MODAL_WEBHOOK_URL={webhook_url}\n")
        
        print(f"✅ Webhook configuration added to {env_file}")
    else:
        print(f"❌ Environment file not found: {env_file}")
    
    print(f"\n📋 Manual Configuration Required:")
    print(f"   1. Go to Modal Dashboard: https://modal.com/")
    print(f"   2. Navigate to your app settings")
    print(f"   3. Add webhook URL: {webhook_url}")
    print(f"   4. Add webhook secret: {webhook_secret}")

def main():
    parser = argparse.ArgumentParser(description="Configure Modal webhooks")
    parser.add_argument("--environment", default="development", 
                       choices=["development", "staging", "production"],
                       help="Environment to configure")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="Base URL for webhook endpoints")
    
    args = parser.parse_args()
    configure_webhooks(args.environment, args.base_url)

if __name__ == "__main__":
    main()
EOF

chmod +x configure_modal_webhooks.py

echo ""
echo "🎉 Modal Setup Complete!"
echo "========================"
echo "✅ Modal CLI installed and authenticated"
echo "✅ Environment variables configured"
echo "✅ Webhook configuration script created"
echo ""
echo "📋 Next Steps:"
echo "1. Run backend to deploy Modal apps automatically"
echo "2. Configure webhooks: python configure_modal_webhooks.py --environment development"
echo "3. For production: python configure_modal_webhooks.py --environment production --base-url https://your-domain.com"
echo ""
echo "🔗 Useful Links:"
echo "Modal Dashboard: https://modal.com/"
echo "Modal Tokens: https://modal.com/settings/tokens"
echo "Modal Apps: https://modal.com/apps"