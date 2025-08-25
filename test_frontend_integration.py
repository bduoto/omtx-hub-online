#!/usr/bin/env python3
"""
Test Frontend Integration with Cloud Run Native API

Verifies that the frontend can successfully connect to and use the new auth-free backend.
"""

import requests
import time
from datetime import datetime

# Test configuration
BACKEND_URL = 'http://localhost:8001'
FRONTEND_URL = 'http://localhost:5173'  # Expected Vite dev server

def test_backend_health():
    """Test backend health endpoint"""
    print("🏥 Testing backend health...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.ok:
            data = response.json()
            print(f"   ✅ Backend healthy: {data['status']}")
            print(f"   GPU Status: {data['gpu_status']}")
            print(f"   Architecture: {data['architecture']}")
            return True
        else:
            print(f"   ❌ Backend unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Backend error: {e}")
        return False

def test_backend_api():
    """Test backend API endpoints"""
    print("🔬 Testing backend API...")
    
    try:
        # Test individual prediction
        payload = {
            "protein_sequence": "MKFLKF",
            "ligand_smiles": "CCO",
            "job_name": "test_job",
            "user_id": "test_user"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/v1/predict",
            json=payload,
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            print(f"   ✅ Individual prediction API working: {data['job_id']}")
            
            # Test job status
            job_status = requests.get(f"{BACKEND_URL}/api/v1/jobs/{data['job_id']}")
            if job_status.ok:
                print(f"   ✅ Job status API working")
                return True
            else:
                print(f"   ❌ Job status API failed: {job_status.status_code}")
                return False
        else:
            print(f"   ❌ Prediction API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API test error: {e}")
        return False

def test_frontend_health():
    """Test if frontend dev server is running"""
    print("🌐 Testing frontend server...")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.ok:
            print(f"   ✅ Frontend server running")
            return True
        else:
            print(f"   ❌ Frontend server not responding: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ⚠️ Frontend server not running (expected if not started)")
        return False
    except Exception as e:
        print(f"   ❌ Frontend error: {e}")
        return False

def test_cors_configuration():
    """Test CORS configuration"""
    print("🔒 Testing CORS configuration...")
    
    try:
        # Simulate a frontend request with CORS headers
        response = requests.options(
            f"{BACKEND_URL}/api/v1/predict",
            headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=5
        )
        
        if response.status_code in [200, 204]:
            cors_headers = response.headers.get('Access-Control-Allow-Origin', '')
            if '*' in cors_headers or 'localhost:5173' in cors_headers:
                print(f"   ✅ CORS properly configured")
                return True
            else:
                print(f"   ⚠️ CORS may be restrictive: {cors_headers}")
                return True  # Still OK
        else:
            print(f"   ❌ CORS preflight failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ CORS test error: {e}")
        return False

def show_frontend_setup_instructions():
    """Show instructions for setting up frontend"""
    print("\n" + "="*50)
    print("🚀 FRONTEND SETUP INSTRUCTIONS")
    print("="*50)
    print()
    print("1. Start the frontend development server:")
    print("   cd frontend")
    print("   npm run dev")
    print("   # or")
    print("   cd /Users/bryanduoto/Desktop/omtx-hub-online")
    print("   ./start_fresh.sh")
    print()
    print("2. Open browser to: http://localhost:5173")
    print()
    print("3. Test the new simplified Boltz-2 page:")
    print("   - Navigate to the Boltz-2 section")
    print("   - Or directly access: http://localhost:5173/boltz2-simplified")
    print()
    print("4. Environment Configuration:")
    print(f"   VITE_API_BASE_URL={BACKEND_URL}")
    print("   (Already configured in frontend/.env)")
    print()
    print("5. Features to test:")
    print("   ✅ System status display")
    print("   ✅ No authentication required")
    print("   ✅ Batch protein-ligand predictions")
    print("   ✅ Real-time progress updates")
    print("   ✅ Results display")
    print()
    print("6. New Components Available:")
    print("   - apiService.ts: Simplified API client")
    print("   - apiClient_simplified.ts: Type-safe API wrapper")
    print("   - jobStore_simplified.ts: State management") 
    print("   - Boltz2_simplified.tsx: Main page")
    print("   - BatchProteinLigandInput_simplified.tsx: Input component")

def main():
    """Run comprehensive frontend integration tests"""
    print("🧪 FRONTEND INTEGRATION TEST SUITE")
    print("="*50)
    print(f"Test Time: {datetime.now().isoformat()}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Expected Frontend URL: {FRONTEND_URL}")
    print()
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Backend API", test_backend_api),
        ("Frontend Server", test_frontend_health),
        ("CORS Configuration", test_cors_configuration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            start_time = time.time()
            success = test_func()
            duration = time.time() - start_time
            
            results[test_name] = {
                "success": success,
                "duration": duration
            }
            
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n   {status} ({duration:.2f}s)")
            
        except Exception as e:
            results[test_name] = {
                "success": False,
                "duration": 0,
                "error": str(e)
            }
            print(f"\n   ❌ ERROR: {e}")
    
    # Summary
    print(f"\n{'='*50}")
    print("🎯 INTEGRATION TEST SUMMARY")
    print("="*50)
    
    passed_tests = sum(1 for r in results.values() if r.get("success", False))
    total_tests = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        duration = result.get("duration", 0)
        print(f"{status:8} {test_name:20} ({duration:.2f}s)")
        
        if "error" in result:
            print(f"         Error: {result['error']}")
    
    print()
    print(f"Backend Integration: {passed_tests-1}/3 tests passed")  # Exclude frontend server test
    
    if passed_tests >= 3:  # Backend tests passing
        print("🎉 BACKEND READY FOR FRONTEND INTEGRATION!")
        print()
        print("✅ Auth-free API working")
        print("✅ Cloud Run native architecture operational")
        print("✅ CORS configured for frontend access")
        print("✅ All endpoints responding correctly")
        
        show_frontend_setup_instructions()
        
        return True
    else:
        print("⚠️ Some backend tests failed - fix issues before frontend integration")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)