#!/usr/bin/env python3
"""
OMTX-Hub Credential Validation Script
Tests GCP and Modal connections before deployment
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_gcp_credentials() -> bool:
    """Test GCP Firestore and Storage connections"""
    try:
        # Test environment variable presence
        gcp_creds = os.getenv('GCP_CREDENTIALS_JSON')
        if not gcp_creds:
            logger.error("❌ GCP_CREDENTIALS_JSON environment variable not set")
            return False
        
        # Test JSON parsing
        try:
            creds_dict = json.loads(gcp_creds)
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [f for f in required_fields if f not in creds_dict]
            
            if missing_fields:
                logger.error(f"❌ Missing required fields in GCP credentials: {missing_fields}")
                return False
            
            logger.info(f"✅ GCP credentials JSON format valid")
            logger.info(f"   Project ID: {creds_dict['project_id']}")
            logger.info(f"   Service Account: {creds_dict['client_email']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid GCP credentials JSON format: {e}")
            return False
        
        # Test actual GCP connection
        try:
            from google.cloud import firestore
            from google.oauth2 import service_account
            
            credentials = service_account.Credentials.from_service_account_info(creds_dict)
            project_id = creds_dict['project_id']
            
            # Test Firestore connection
            db = firestore.Client(project=project_id, credentials=credentials)
            collections = list(db.collections())
            logger.info(f"✅ Firestore connection successful")
            logger.info(f"   Found {len(collections)} collections")
            
            # Test Cloud Storage connection
            from google.cloud import storage
            storage_client = storage.Client(project=project_id, credentials=credentials)
            buckets = list(storage_client.list_buckets())
            logger.info(f"✅ Cloud Storage connection successful")
            logger.info(f"   Found {len(buckets)} buckets")
            
            return True
            
        except ImportError:
            logger.error("❌ Google Cloud libraries not installed. Run: pip install google-cloud-firestore google-cloud-storage")
            return False
        except Exception as e:
            logger.error(f"❌ GCP connection failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ GCP credential test failed: {e}")
        return False

def test_modal_credentials() -> bool:
    """Test Modal API token connection"""
    try:
        # Test environment variables
        token_id = os.getenv('MODAL_TOKEN_ID')
        token_secret = os.getenv('MODAL_TOKEN_SECRET')
        
        if not token_id or not token_secret:
            logger.error("❌ MODAL_TOKEN_ID or MODAL_TOKEN_SECRET environment variables not set")
            return False
        
        # Validate token format
        if not token_id.startswith('ak-'):
            logger.error(f"❌ Invalid MODAL_TOKEN_ID format. Should start with 'ak-', got: {token_id[:10]}...")
            return False
            
        if not token_secret.startswith('as-'):
            logger.error(f"❌ Invalid MODAL_TOKEN_SECRET format. Should start with 'as-', got: {token_secret[:10]}...")
            return False
        
        logger.info(f"✅ Modal token format valid")
        logger.info(f"   Token ID: {token_id[:10]}...")
        logger.info(f"   Token Secret: {token_secret[:10]}...")
        
        # Test actual Modal connection
        try:
            import modal
            
            # Test connection by listing apps
            client = modal.Client()
            apps = list(client.list_apps())
            logger.info(f"✅ Modal connection successful")
            logger.info(f"   Found {len(apps)} apps in your Modal account")
            
            return True
            
        except ImportError:
            logger.error("❌ Modal library not installed. Run: pip install modal")
            return False
        except Exception as e:
            logger.error(f"❌ Modal connection failed: {e}")
            logger.info("   Make sure your tokens are valid and active")
            return False
            
    except Exception as e:
        logger.error(f"❌ Modal credential test failed: {e}")
        return False

def test_database_integration() -> bool:
    """Test actual database integration with the application"""
    try:
        # Import our GCP database manager
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from config.gcp_database import gcp_database
        
        if not gcp_database.available:
            logger.error("❌ GCP database manager not available")
            return False
        
        # Test job creation
        test_job = {
            'job_id': 'test-validation-job',
            'model_id': 'test',
            'status': 'test',
            'user_id': 'validation-test',
            'job_type': 'INDIVIDUAL'
        }
        
        job_id = gcp_database.create_job(test_job)
        if not job_id:
            logger.error("❌ Failed to create test job")
            return False
        
        # Test job retrieval
        retrieved_job = gcp_database.get_job(job_id)
        if not retrieved_job:
            logger.error("❌ Failed to retrieve test job")
            return False
        
        logger.info("✅ Database integration test successful")
        logger.info(f"   Created and retrieved test job: {job_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integration test failed: {e}")
        return False

def validate_production_readiness() -> Dict[str, Any]:
    """Run all validation tests and return summary"""
    logger.info("🔍 Starting OMTX-Hub credential validation...")
    logger.info("=" * 60)
    
    results = {
        'gcp_credentials': False,
        'modal_credentials': False,
        'database_integration': False,
        'overall_ready': False
    }
    
    # Test GCP credentials
    logger.info("\n📋 Testing GCP Credentials...")
    results['gcp_credentials'] = test_gcp_credentials()
    
    # Test Modal credentials
    logger.info("\n🚀 Testing Modal Credentials...")
    results['modal_credentials'] = test_modal_credentials()
    
    # Test database integration
    logger.info("\n💾 Testing Database Integration...")
    results['database_integration'] = test_database_integration()
    
    # Overall assessment
    all_tests_passed = all(results.values())
    results['overall_ready'] = all_tests_passed
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    status_icon = "✅" if results['gcp_credentials'] else "❌"
    logger.info(f"{status_icon} GCP Credentials: {'VALID' if results['gcp_credentials'] else 'INVALID'}")
    
    status_icon = "✅" if results['modal_credentials'] else "❌"
    logger.info(f"{status_icon} Modal Credentials: {'VALID' if results['modal_credentials'] else 'INVALID'}")
    
    status_icon = "✅" if results['database_integration'] else "❌"
    logger.info(f"{status_icon} Database Integration: {'WORKING' if results['database_integration'] else 'FAILED'}")
    
    logger.info("-" * 60)
    
    if all_tests_passed:
        logger.info("🎉 ALL TESTS PASSED - Production ready!")
        logger.info("   Your OMTX-Hub API can now process real batch jobs with GPU execution")
    else:
        logger.error("🚨 VALIDATION FAILED - See errors above")
        logger.info("   Follow the CREDENTIAL_SETUP_GUIDE.md to fix credential issues")
    
    return results

def main():
    """Main validation entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
OMTX-Hub Credential Validation Script

Usage:
  python validate_credentials.py

Tests:
  1. GCP service account credentials and connections
  2. Modal API token validity and authentication  
  3. Database integration and job creation

Environment Variables Required:
  - GCP_CREDENTIALS_JSON: Service account JSON (single line)
  - MODAL_TOKEN_ID: Modal token ID (starts with 'ak-')
  - MODAL_TOKEN_SECRET: Modal token secret (starts with 'as-')

Exit Codes:
  0: All tests passed
  1: One or more tests failed
        """)
        sys.exit(0)
    
    results = validate_production_readiness()
    
    # Exit with appropriate code
    if results['overall_ready']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()