#!/usr/bin/env python3
"""
Test GCP Connection and Basic Functionality
"""

import os
import sys
import json
import time
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")
except ImportError:
    print("⚠️ python-dotenv not available, using system env vars")

def test_environment_variables():
    """Test if required environment variables are present"""
    print("\n🔍 Testing Environment Variables...")
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'GCP_BUCKET_NAME',
        'GCP_CREDENTIALS_JSON'
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'SET' if var != 'GCP_CREDENTIALS_JSON' else 'SET (JSON)'}")
        else:
            print(f"   ❌ {var}: NOT SET")
            all_present = False
    
    return all_present

def test_gcp_credentials_format():
    """Test if GCP credentials JSON is properly formatted"""
    print("\n🔍 Testing GCP Credentials Format...")
    
    try:
        gcp_creds_json = os.getenv('GCP_CREDENTIALS_JSON')
        if not gcp_creds_json:
            print("   ❌ GCP_CREDENTIALS_JSON not found")
            return False
        
        creds_dict = json.loads(gcp_creds_json)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field in creds_dict:
                print(f"   ✅ {field}: Present")
            else:
                print(f"   ❌ {field}: Missing")
                return False
        
        # Check project ID matches
        project_id = creds_dict.get('project_id')
        env_project = os.getenv('GOOGLE_CLOUD_PROJECT')
        if project_id == env_project:
            print(f"   ✅ Project ID consistency: {project_id}")
        else:
            print(f"   ⚠️ Project ID mismatch: JSON={project_id}, ENV={env_project}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"   ❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error parsing credentials: {e}")
        return False

def test_google_cloud_import():
    """Test if Google Cloud libraries can be imported"""
    print("\n🔍 Testing Google Cloud Library Imports...")
    
    try:
        from google.cloud import storage
        print("   ✅ google.cloud.storage imported successfully")
        
        from google.oauth2 import service_account
        print("   ✅ google.oauth2.service_account imported successfully")
        
        from google.cloud import firestore
        print("   ✅ google.cloud.firestore imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        print("   💡 Try: pip install google-cloud-storage google-cloud-firestore")
        return False

def test_gcp_storage_connection():
    """Test actual GCP Storage connection"""
    print("\n🔍 Testing GCP Storage Connection...")
    
    try:
        from config.gcp_storage import gcp_storage
        
        if gcp_storage.available:
            print("   ✅ GCP Storage initialized successfully")
            print(f"   📦 Bucket name: {gcp_storage.bucket_name}")
            
            # Test bucket access
            try:
                bucket = gcp_storage.bucket
                if bucket.exists():
                    print(f"   ✅ Bucket '{gcp_storage.bucket_name}' exists and accessible")
                else:
                    print(f"   ❌ Bucket '{gcp_storage.bucket_name}' not found")
                    return False
            except Exception as e:
                print(f"   ❌ Bucket access failed: {e}")
                return False
                
            return True
        else:
            print("   ❌ GCP Storage not available")
            return False
            
    except Exception as e:
        print(f"   ❌ GCP Storage connection failed: {e}")
        return False

def test_firestore_connection():
    """Test Firestore connection"""
    print("\n🔍 Testing Firestore Connection...")
    
    try:
        from database.gcp_job_manager import gcp_job_manager
        
        if gcp_job_manager.available:
            print("   ✅ Firestore initialized successfully")
            
            # Test basic query
            try:
                # Try to get recent jobs (should work even if empty)
                recent_jobs = gcp_job_manager.get_recent_jobs(limit=1)
                print(f"   ✅ Firestore query successful ({len(recent_jobs)} jobs found)")
                return True
            except Exception as e:
                print(f"   ❌ Firestore query failed: {e}")
                return False
        else:
            print("   ❌ Firestore not available")
            return False
            
    except Exception as e:
        print(f"   ❌ Firestore connection failed: {e}")
        return False

def test_composite_indexes():
    """Test if Firestore composite indexes are working"""
    print("\n🔍 Testing Firestore Composite Indexes...")
    
    try:
        from database.gcp_job_manager import gcp_job_manager
        
        if not gcp_job_manager.available:
            print("   ❌ Firestore not available")
            return False
        
        # Test queries that require composite indexes
        test_queries = [
            ("Recent jobs", lambda: gcp_job_manager.get_recent_jobs(limit=5)),
            ("Jobs by status", lambda: gcp_job_manager.get_jobs_by_status("completed", limit=5)),
            ("User jobs", lambda: gcp_job_manager.get_user_jobs("current_user", limit=5))
        ]
        
        all_passed = True
        for test_name, query_func in test_queries:
            try:
                result = query_func()
                print(f"   ✅ {test_name}: OK ({len(result)} results)")
            except Exception as e:
                if "index" in str(e).lower():
                    print(f"   ⚠️ {test_name}: NEEDS INDEX - {e}")
                else:
                    print(f"   ❌ {test_name}: ERROR - {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ Index testing failed: {e}")
        return False

def test_end_to_end_job_flow():
    """Test creating, storing, and retrieving a job"""
    print("\n🔍 Testing End-to-End Job Flow...")
    
    try:
        from database.unified_job_manager import unified_job_manager
        import uuid
        
        # Create test job data
        test_job_id = str(uuid.uuid4())
        test_job_data = {
            'id': test_job_id,
            'name': 'GCP Connection Test',
            'type': 'protein_ligand_binding',
            'status': 'pending',
            'created_at': time.time(),
            'input_data': {
                'protein_sequence': 'TEST',
                'ligand_smiles': 'C'
            },
            'user_id': 'test_user'
        }
        
        # Create job
        print("   📝 Creating test job...")
        created_id = unified_job_manager.create_job(test_job_data)
        if created_id:
            print(f"   ✅ Job created: {created_id}")
        else:
            print("   ❌ Failed to create job")
            return False
        
        # Retrieve job
        print("   📖 Retrieving test job...")
        retrieved_job = unified_job_manager.get_job(test_job_id)
        if retrieved_job:
            print(f"   ✅ Job retrieved: {retrieved_job.get('name')}")
        else:
            print("   ❌ Failed to retrieve job")
            return False
        
        # Update job status
        print("   📝 Updating job status...")
        update_success = unified_job_manager.update_job_status(test_job_id, "completed")
        if update_success:
            print("   ✅ Job status updated")
        else:
            print("   ❌ Failed to update job status")
        
        # Clean up test job
        print("   🗑️ Cleaning up test job...")
        try:
            # Note: Implement delete if needed
            print("   ✅ Test job cleanup skipped (no delete method)")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"   ❌ End-to-end test failed: {e}")
        return False

def main():
    """Run all GCP connection tests"""
    print("🚀 GCP Connection Diagnostic Test")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("GCP Credentials Format", test_gcp_credentials_format),
        ("Google Cloud Imports", test_google_cloud_import),
        ("GCP Storage Connection", test_gcp_storage_connection),
        ("Firestore Connection", test_firestore_connection),
        ("Composite Indexes", test_composite_indexes),
        ("End-to-End Job Flow", test_end_to_end_job_flow),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🔍 DIAGNOSTIC SUMMARY:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! GCP connection is healthy.")
    else:
        print(f"⚠️ {total - passed} test(s) failed. Issues need attention.")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not results.get("Environment Variables"):
            print("   - Check .env file and ensure all GCP variables are set")
        if not results.get("GCP Credentials Format"):
            print("   - Verify GCP service account JSON format")
        if not results.get("Google Cloud Imports"):
            print("   - Install: pip install google-cloud-storage google-cloud-firestore")
        if not results.get("GCP Storage Connection"):
            print("   - Check GCP bucket exists and permissions are correct")
        if not results.get("Firestore Connection"):
            print("   - Verify Firestore is enabled and accessible")
        if not results.get("Composite Indexes"):
            print("   - Create required Firestore composite indexes")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)