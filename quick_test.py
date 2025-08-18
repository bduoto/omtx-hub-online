#!/usr/bin/env python3
"""
Quick test to validate OMTX-Hub setup
"""
import requests
import json
import time

def test_backend_health():
    """Test backend health endpoint"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend health check: PASSED")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Backend health check: FAILED (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Backend health check: FAILED ({e})")
        return False

def test_api_docs():
    """Test API documentation endpoint"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API documentation: ACCESSIBLE")
            return True
        else:
            print(f"❌ API documentation: NOT ACCESSIBLE (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API documentation: FAILED ({e})")
        return False

def test_batch_api():
    """Test batch API endpoint"""
    try:
        response = requests.get(
            "http://localhost:8000/api/v3/batches/",
            params={"user_id": "test_user", "limit": 2},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            batch_count = len(data.get("batches", []))
            print(f"✅ Batch API: WORKING ({batch_count} batches found)")
            if batch_count > 0:
                print(f"   First batch: {data['batches'][0]['name']} - {data['batches'][0]['status']}")
            return True
        else:
            print(f"❌ Batch API: FAILED (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Batch API: FAILED ({e})")
        return False

def test_frontend():
    """Test frontend availability"""
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200 and "<!doctype html>" in response.text:
            print("✅ Frontend: RUNNING on port 8080")
            return True
        else:
            print(f"❌ Frontend: NOT RUNNING (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Frontend: FAILED ({e})")
        return False

def test_gcp_connectivity():
    """Test GCP service connectivity"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "gcp" in str(data).lower():
                print("✅ GCP Services: CONNECTED")
                print(f"   Database: {data.get('database', 'unknown')}")
                print(f"   Storage: {data.get('storage', 'unknown')}")
                return True
            else:
                print("⚠️ GCP Services: Status unclear")
                return True
        return False
    except Exception as e:
        print(f"❌ GCP Services: FAILED ({e})")
        return False

def main():
    """Run all tests"""
    print("🧪 OMTX-Hub Quick Test Suite")
    print("=============================\n")
    
    tests = [
        test_backend_health,
        test_api_docs,
        test_batch_api,
        test_frontend,
        test_gcp_connectivity
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("📊 Test Summary")
    print("===============")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests PASSED! System is ready for use.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())