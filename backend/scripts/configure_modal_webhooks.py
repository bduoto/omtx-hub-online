#!/usr/bin/env python3
"""
Modal Webhook Configuration Script
Configures Modal apps to send webhooks to OMTX-Hub production endpoints
"""

import os
import sys
import json
import hashlib
import hmac
import requests
from typing import Dict, Any, List
import modal

# Configuration
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://api.omtx-hub.com")
MODAL_WEBHOOK_SECRET = os.getenv("MODAL_WEBHOOK_SECRET")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Modal apps to configure
MODAL_APPS = [
    {
        "app_name": "omtx-boltz2-persistent",
        "functions": ["predict_shard", "boltz2_predict_modal"],
        "environment": "production"
    },
    {
        "app_name": "omtx-hub-chai1",
        "functions": ["chai1_predict_modal"],
        "environment": "production"
    },
    {
        "app_name": "omtx-hub-rfantibody-phase2",
        "functions": ["rfantibody_predict"],
        "environment": "production"
    }
]

def generate_webhook_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for webhook payload"""
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def configure_modal_app_webhooks(app_config: Dict[str, Any]) -> bool:
    """Configure webhooks for a Modal app"""
    
    app_name = app_config["app_name"]
    functions = app_config["functions"]
    environment = app_config["environment"]
    
    print(f"\n🔧 Configuring webhooks for {app_name}")
    
    try:
        # Get Modal app
        if DRY_RUN:
            print(f"[DRY RUN] Would configure app: {app_name}")
            return True
        
        # Load Modal app
        app = modal.App.lookup(app_name, create_if_missing=False)
        if not app:
            print(f"❌ App {app_name} not found")
            return False
        
        webhook_config = {
            "url": f"{WEBHOOK_BASE_URL}/api/v3/webhooks/modal/completion",
            "events": ["function.success", "function.failure", "function.timeout"],
            "secret": MODAL_WEBHOOK_SECRET,
            "retry_policy": {
                "max_retries": 3,
                "backoff": "exponential",
                "initial_delay": 1.0,
                "max_delay": 60.0
            },
            "timeout": 30,
            "headers": {
                "Content-Type": "application/json",
                "User-Agent": "Modal-Webhook/1.0 (OMTX-Hub)"
            }
        }
        
        # Configure webhooks for each function
        for function_name in functions:
            print(f"  📡 Configuring function: {function_name}")
            
            try:
                # This is a conceptual API - Modal's actual webhook configuration
                # API may differ. Check Modal documentation for exact implementation.
                
                # Configure the webhook endpoint
                app.configure_webhook(function_name, webhook_config)
                print(f"  ✅ Webhook configured for {function_name}")
                
            except Exception as e:
                print(f"  ❌ Failed to configure {function_name}: {e}")
                return False
        
        print(f"✅ Successfully configured {app_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error configuring {app_name}: {e}")
        return False

def test_webhook_endpoint() -> bool:
    """Test webhook endpoint connectivity"""
    
    print("\n🧪 Testing webhook endpoint...")
    
    test_payload = {
        "call_id": "test_123",
        "status": "success",
        "result": {"test": True},
        "metadata": {"test_mode": True}
    }
    
    payload_str = json.dumps(test_payload)
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Modal-Webhook-Test/1.0"
    }
    
    if MODAL_WEBHOOK_SECRET:
        headers["X-Modal-Signature"] = generate_webhook_signature(payload_str, MODAL_WEBHOOK_SECRET)
        headers["X-Modal-Timestamp"] = str(int(time.time()))
    
    try:
        response = requests.post(
            f"{WEBHOOK_BASE_URL}/api/v3/webhooks/modal/test",
            headers=headers,
            data=payload_str,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Webhook endpoint is accessible")
            return True
        else:
            print(f"❌ Webhook endpoint returned {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to reach webhook endpoint: {e}")
        return False

def verify_webhook_health() -> bool:
    """Verify webhook service health"""
    
    print("\n🏥 Checking webhook service health...")
    
    try:
        response = requests.get(
            f"{WEBHOOK_BASE_URL}/api/v3/webhooks/modal/health",
            timeout=10
        )
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Webhook service is healthy")
            print(f"  Features: {health_data.get('features', {})}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def generate_deployment_config() -> Dict[str, Any]:
    """Generate configuration for deployment"""
    
    config = {
        "webhook_configuration": {
            "base_url": WEBHOOK_BASE_URL,
            "endpoints": {
                "completion": "/api/v3/webhooks/modal/completion",
                "health": "/api/v3/webhooks/modal/health",
                "test": "/api/v3/webhooks/modal/test"
            },
            "security": {
                "hmac_verification": bool(MODAL_WEBHOOK_SECRET),
                "timestamp_verification": True,
                "replay_protection": True
            },
            "retry_policy": {
                "max_retries": 3,
                "backoff": "exponential",
                "timeout": 30
            }
        },
        "modal_apps": MODAL_APPS,
        "environment_variables": {
            "WEBHOOK_BASE_URL": WEBHOOK_BASE_URL,
            "MODAL_WEBHOOK_SECRET": "*** REDACTED ***" if MODAL_WEBHOOK_SECRET else None
        }
    }
    
    return config

def main():
    """Main configuration script"""
    
    print("🚀 Modal Webhook Configuration Script")
    print("=====================================")
    
    # Validate environment
    if not WEBHOOK_BASE_URL:
        print("❌ WEBHOOK_BASE_URL not configured")
        sys.exit(1)
    
    if not MODAL_WEBHOOK_SECRET:
        print("⚠️ MODAL_WEBHOOK_SECRET not configured - webhooks will not be secure")
    
    print(f"🎯 Target URL: {WEBHOOK_BASE_URL}")
    print(f"🔒 Security: {'HMAC enabled' if MODAL_WEBHOOK_SECRET else 'No HMAC'}")
    print(f"🔧 Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    
    # Step 1: Verify webhook endpoint
    if not verify_webhook_health():
        print("❌ Webhook service not available")
        sys.exit(1)
    
    # Step 2: Test webhook endpoint
    if not test_webhook_endpoint():
        print("❌ Webhook endpoint test failed")
        sys.exit(1)
    
    # Step 3: Configure Modal apps
    success_count = 0
    for app_config in MODAL_APPS:
        if configure_modal_app_webhooks(app_config):
            success_count += 1
    
    print(f"\n📊 Configuration Summary:")
    print(f"  Total apps: {len(MODAL_APPS)}")
    print(f"  Configured successfully: {success_count}")
    print(f"  Failed: {len(MODAL_APPS) - success_count}")
    
    # Step 4: Generate deployment config
    config = generate_deployment_config()
    config_file = "modal_webhook_config.json"
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"📁 Configuration saved to: {config_file}")
    
    if success_count == len(MODAL_APPS):
        print("\n🎉 All Modal apps configured successfully!")
        print("\nNext steps:")
        print("1. Deploy OMTX-Hub backend with webhook endpoints")
        print("2. Test webhook delivery with actual Modal job")
        print("3. Monitor webhook logs for successful delivery")
        return 0
    else:
        print("\n⚠️ Some configurations failed. Check logs above.")
        return 1

if __name__ == "__main__":
    import time
    sys.exit(main())