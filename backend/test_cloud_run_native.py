#!/usr/bin/env python3
"""
Test script for OMTX-Hub Cloud Run Native API
Validates the new auth-free, GPU-optimized service
"""

import os
import time
import json
import requests
import asyncio
from datetime import datetime

# Test configuration
BASE_URL = os.getenv('TEST_URL', 'http://localhost:8080')
API_BASE = f"{BASE_URL}/api/v1"

# Test data
TEST_PROTEIN = "MKFLKFSLLTLLLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLRETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYKAAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVTDLTKVHTECCHGDLLECADDRADLAKYICENQDSISSKLKECCEKPLLEKSHCIAEVENDEMPADLPSLAADFVESKDVCKNYAEAKDVFLGMFLYEYARRHPDYSVVLLLRLAKTYETTLEKCCAAADPHECYAKVFDEFKPLVEEPQNLIKQNCELFEQLGEYKFQNALLVRYTKKVPQVSTPTLVEVSRNLGKVGSKCCKHPEAKRMPCAEDYLSVVLNQLCVLHEKTPVSDRVTKCCTESLVNRRPCFSALEVDETYVPKEFNAETFTFHADICTLSEKERQIKKQTALVELVKHKPKATKEQLKAVMDDFAAFVEKCCKADDKETCFAEEGKKLVAASQAALGL"
TEST_LIGAND = "CCO"  # Ethanol (simple test ligand)

def test_health_check():
    """Test health check endpoint"""
    print("🏥 Testing health check...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed")
            print(f"   Status: {data.get('status')}")
            print(f"   GPU Status: {data.get('gpu_status')}")
            print(f"   Architecture: {data.get('architecture')}")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Health check error: {e}")
        return False

def test_individual_prediction():
    """Test individual Boltz-2 prediction"""
    print("🔬 Testing individual prediction...")
    
    try:
        payload = {
            "protein_sequence": TEST_PROTEIN,
            "ligand_smiles": TEST_LIGAND,
            "job_name": "test_individual_prediction",
            "user_id": "test_user",
            "recycling_steps": 2,  # Reduced for faster testing
            "sampling_steps": 100,  # Reduced for faster testing
            "diffusion_samples": 1
        }
        
        response = requests.post(
            f"{API_BASE}/predict", 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id')
            print(f"   ✅ Prediction submitted successfully")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            
            # Wait a moment then check job status
            print("   ⏳ Waiting for processing...")
            time.sleep(3)
            return test_job_status(job_id)
            
        else:
            print(f"   ❌ Prediction failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Prediction error: {e}")
        return False

def test_job_status(job_id):
    """Test job status endpoint"""
    print(f"📊 Testing job status for {job_id}...")
    
    try:
        response = requests.get(f"{API_BASE}/jobs/{job_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Job status retrieved successfully")
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Progress: {data.get('progress')}%")
            
            results = data.get('results', {})
            if results:
                print(f"   Affinity: {results.get('affinity')}")
                print(f"   Confidence: {results.get('confidence')}")
                
            return True
        else:
            print(f"   ❌ Job status failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Job status error: {e}")
        return False

def test_batch_prediction():
    """Test batch Boltz-2 prediction"""
    print("📦 Testing batch prediction...")
    
    try:
        payload = {
            "protein_sequence": TEST_PROTEIN,
            "ligands": [
                {"name": "ethanol", "smiles": "CCO"},
                {"name": "methanol", "smiles": "CO"},
                {"name": "propanol", "smiles": "CCCO"}
            ],
            "batch_name": "test_batch_prediction",
            "user_id": "test_user",
            "max_concurrent": 2,
            "recycling_steps": 2,
            "sampling_steps": 50,
            "diffusion_samples": 1
        }
        
        response = requests.post(
            f"{API_BASE}/predict/batch",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            batch_id = data.get('batch_id')
            print(f"   ✅ Batch submitted successfully")
            print(f"   Batch ID: {batch_id}")
            print(f"   Total Jobs: {data.get('total_jobs')}")
            print(f"   Status: {data.get('status')}")
            
            # Wait then check batch status
            print("   ⏳ Waiting for batch processing...")
            time.sleep(5)
            return test_batch_status(batch_id)
            
        else:
            print(f"   ❌ Batch prediction failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Batch prediction error: {e}")
        return False

def test_batch_status(batch_id):
    """Test batch status endpoint"""
    print(f"📊 Testing batch status for {batch_id}...")
    
    try:
        response = requests.get(f"{API_BASE}/batches/{batch_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Batch status retrieved successfully")
            print(f"   Batch ID: {data.get('batch_id')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Progress: {data.get('progress')}%")
            print(f"   Completed Jobs: {data.get('completed_jobs')}/{data.get('total_jobs')}")
            
            results = data.get('results', {})
            if results:
                print(f"   Best Affinity: {results.get('best_affinity')}")
                print(f"   Average Affinity: {results.get('average_affinity')}")
                
            return True
        else:
            print(f"   ❌ Batch status failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Batch status error: {e}")
        return False

def test_api_docs():
    """Test API documentation endpoints"""
    print("📚 Testing API documentation...")
    
    try:
        # Test root endpoint
        response = requests.get(BASE_URL, timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Root endpoint accessible")
        
        # Test docs endpoint
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ API documentation accessible")
            return True
        else:
            print(f"   ❌ API docs failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API docs error: {e}")
        return False

def main():
    """Run comprehensive test suite"""
    print("🚀 OMTX-Hub Cloud Run Native API Test Suite")
    print("=" * 50)
    print(f"Testing URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    tests = [
        ("Health Check", test_health_check),
        ("API Documentation", test_api_docs),
        ("Individual Prediction", test_individual_prediction),
        ("Batch Prediction", test_batch_prediction)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        
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
    print(f"\n{'=' * 50}")
    print("🎯 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(tests)
    passed_tests = sum(1 for r in results.values() if r.get("success", False))
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
        duration = result.get("duration", 0)
        print(f"{status:8} {test_name:25} ({duration:.2f}s)")
        
        if "error" in result:
            print(f"         Error: {result['error']}")
    
    print()
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Cloud Run Native API is ready!")
        print()
        print("Next steps:")
        print("1. Deploy to Google Cloud Run with GPU")
        print("2. Update frontend to use new API")
        print("3. Configure company API gateway routing")
        return True
    else:
        print("⚠️ Some tests failed - check logs and fix issues")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)