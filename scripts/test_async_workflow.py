#!/usr/bin/env python3
"""
Test Async Prediction Workflow
Tests the new Cloud Run Jobs async prediction system
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8002"  # Update for production
TEST_PROTEIN = "MKWVTFISLLFSSAYSRGVFRRDTHKSEIAHRFKDLGEEHFKGLVLIAFSQYLQ"[:50]  # Short for testing
TEST_LIGAND = "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"  # Ibuprofen
LIGAND_NAME = "ibuprofen_test"

def test_async_single_prediction():
    """Test single async prediction workflow"""
    print("🧬 Testing Async Single Prediction")
    print("=" * 50)
    
    # Submit job
    print("📤 Submitting prediction job...")
    response = requests.post(f"{BACKEND_URL}/api/v1/predict/async", json={
        "protein_sequence": TEST_PROTEIN,
        "ligand_smiles": TEST_LIGAND,
        "ligand_name": LIGAND_NAME,
        "user_id": "test_user"
    })
    
    if response.status_code != 200:
        print(f"❌ Job submission failed: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    job_id = result["job_id"]
    
    print(f"✅ Job submitted successfully!")
    print(f"   Job ID: {job_id}")
    print(f"   Status: {result['status']}")
    print(f"   Estimated time: {result['estimated_completion_time']}")
    
    # Poll for completion
    print(f"\n⏳ Polling job status...")
    max_attempts = 30  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(10)  # Wait 10 seconds between polls
        attempt += 1
        
        print(f"   Attempt {attempt}/{max_attempts}: Checking status...")
        
        response = requests.get(f"{BACKEND_URL}/api/v1/jobs/{job_id}")
        
        if response.status_code != 200:
            print(f"   ❌ Status check failed: {response.status_code}")
            continue
        
        job_status = response.json()
        status = job_status["status"]
        
        print(f"   Status: {status}")
        
        if status == "completed":
            print(f"✅ Job completed successfully!")
            results = job_status.get("results", {})
            print(f"   📊 Results:")
            print(f"      Affinity: {results.get('affinity', 'N/A')} kcal/mol")
            print(f"      Confidence: {results.get('confidence', 'N/A')}")
            print(f"      Processing time: {job_status.get('processing_time_seconds', 'N/A')}s")
            print(f"      Real Boltz-2: {results.get('real_boltz2', 'N/A')}")
            return True
            
        elif status == "failed":
            print(f"❌ Job failed!")
            return False
            
        elif status in ["processing", "submitted"]:
            print(f"   ⏳ Still processing...")
            continue
        
        else:
            print(f"   ⚠️ Unknown status: {status}")
    
    print(f"❌ Job did not complete within {max_attempts * 10} seconds")
    return False

def test_async_batch_prediction():
    """Test batch async prediction workflow"""
    print("\n📦 Testing Async Batch Prediction")
    print("=" * 50)
    
    ligands = [
        {"smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "name": "ibuprofen"},
        {"smiles": "CCO", "name": "ethanol"},
        {"smiles": "CC(=O)O", "name": "acetic_acid"}
    ]
    
    # Submit batch
    print("📤 Submitting batch job...")
    response = requests.post(f"{BACKEND_URL}/api/v1/predict/batch/async", json={
        "protein_sequence": TEST_PROTEIN,
        "ligands": ligands,
        "user_id": "test_user",
        "batch_name": "test_batch"
    })
    
    if response.status_code != 200:
        print(f"❌ Batch submission failed: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    batch_id = result["batch_id"]
    
    print(f"✅ Batch submitted successfully!")
    print(f"   Batch ID: {batch_id}")
    print(f"   Total jobs: {result['total_jobs']}")
    print(f"   Submitted jobs: {result['submitted_jobs']}")
    
    # Poll batch status
    print(f"\n⏳ Polling batch status...")
    max_attempts = 30  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(15)  # Wait 15 seconds between polls for batch
        attempt += 1
        
        print(f"   Attempt {attempt}/{max_attempts}: Checking batch status...")
        
        response = requests.get(f"{BACKEND_URL}/api/v1/batches/{batch_id}")
        
        if response.status_code != 200:
            print(f"   ❌ Batch status check failed: {response.status_code}")
            continue
        
        batch_status = response.json()
        status = batch_status["status"]
        completed = batch_status.get("completed_jobs", 0)
        total = batch_status.get("total_jobs", 0)
        progress = batch_status.get("progress_percentage", 0)
        
        print(f"   Status: {status}")
        print(f"   Progress: {completed}/{total} ({progress:.1f}%)")
        
        if status == "completed":
            print(f"✅ Batch completed successfully!")
            jobs = batch_status.get("jobs", [])
            print(f"   📊 Individual Results:")
            for job in jobs:
                job_id = job["job_id"]
                job_status = job["status"]
                results = job.get("results", {})
                affinity = results.get("affinity", "N/A")
                print(f"      {job_id}: {job_status} (affinity: {affinity})")
            return True
            
        elif completed > 0:
            print(f"   ⏳ {completed} jobs completed, {total - completed} remaining...")
            continue
        
        else:
            print(f"   ⏳ Still processing...")
    
    print(f"❌ Batch did not complete within {max_attempts * 15} seconds")
    return False

def test_job_listing():
    """Test job listing functionality"""
    print("\n📋 Testing Job Listing")
    print("=" * 50)
    
    response = requests.get(f"{BACKEND_URL}/api/v1/jobs?user_id=test_user&limit=10")
    
    if response.status_code != 200:
        print(f"❌ Job listing failed: {response.status_code}")
        return False
    
    result = response.json()
    jobs = result.get("jobs", [])
    
    print(f"✅ Found {len(jobs)} jobs for test_user")
    for job in jobs[:3]:  # Show first 3
        print(f"   {job['job_id']}: {job['status']} ({job.get('job_type', 'N/A')})")
    
    return True

def run_comprehensive_async_test():
    """Run comprehensive async workflow test"""
    print("🚀 OMTX-Hub Async Prediction Test Suite")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print()
    
    tests = [
        ("Single Async Prediction", test_async_single_prediction),
        ("Batch Async Prediction", test_async_batch_prediction),
        ("Job Listing", test_job_listing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ASYNC TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL ASYNC TESTS PASSED! Cloud Run Jobs system is working!")
        print("\n✅ Async prediction API operational")
        print("✅ Job status polling working")
        print("✅ Batch processing functional")
        print("✅ Job listing and management working")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - check logs above")
    
    return passed == total

if __name__ == "__main__":
    # First check if backend is running
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Backend not accessible at {BACKEND_URL}")
            print("   Make sure the backend is running with: uvicorn main:app --reload")
            exit(1)
    except Exception as e:
        print(f"❌ Backend not accessible: {e}")
        print("   Make sure the backend is running with: uvicorn main:app --reload")
        exit(1)
    
    success = run_comprehensive_async_test()
    exit(0 if success else 1)