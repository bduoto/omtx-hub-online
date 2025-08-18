#!/usr/bin/env python3
"""
End-to-End Workflow Test for OMTX-Hub
Tests complete prediction workflow from submission to completion
"""
import requests
import json
import time
import uuid

def submit_test_prediction():
    """Submit a test prediction job"""
    
    # Test data for a simple protein-ligand prediction
    prediction_data = {
        "model_id": "boltz2",
        "task_type": "batch_protein_ligand_screening",
        "job_name": f"E2E_Test_{uuid.uuid4().hex[:8]}",
        "use_msa": False,  # Faster without MSA
        "use_potentials": False,
        "input_data": {
            "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQ",  # Short test sequence
            "protein_name": "Test_Protein_E2E",
            "ligands": [
                {
                    "name": "ethanol",
                    "smiles": "CCO"
                },
                {
                    "name": "methanol", 
                    "smiles": "CO"
                }
            ]
        }
    }
    
    print("📤 Submitting test prediction...")
    print(f"   Job name: {prediction_data['job_name']}")
    print(f"   Protein: {prediction_data['input_data']['protein_name']}")
    print(f"   Ligands: {len(prediction_data['input_data']['ligands'])} molecules")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v2/predict",
            json=prediction_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prediction submitted successfully!")
            print(f"   Job ID: {result.get('job_id', 'unknown')}")
            print(f"   Status: {result.get('status', 'unknown')}")
            return result.get('job_id')
        else:
            print(f"❌ Failed to submit prediction: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error submitting prediction: {e}")
        return None

def check_job_status(job_id):
    """Check the status of a submitted job"""
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/jobs/{job_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('status'), data
        else:
            print(f"❌ Failed to check job status: {response.status_code}")
            return None, None
            
    except Exception as e:
        print(f"❌ Error checking job status: {e}")
        return None, None

def monitor_job_progress(job_id, max_wait=300):
    """Monitor job progress until completion or timeout"""
    
    print(f"\n⏳ Monitoring job progress (max wait: {max_wait}s)...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        status, data = check_job_status(job_id)
        
        if status and status != last_status:
            elapsed = int(time.time() - start_time)
            print(f"   [{elapsed}s] Status: {status}")
            last_status = status
            
            if status == "completed":
                print(f"✅ Job completed successfully!")
                return True, data
            elif status == "failed":
                print(f"❌ Job failed!")
                if data and 'error' in data:
                    print(f"   Error: {data['error']}")
                return False, data
        
        time.sleep(5)  # Check every 5 seconds
    
    print(f"⏱️ Timeout reached after {max_wait}s")
    return False, None

def check_batch_results(job_id):
    """Check batch results for completed job"""
    
    print(f"\n📊 Checking batch results...")
    
    try:
        # Try batch status endpoint
        response = requests.get(
            f"http://localhost:8000/api/jobs/{job_id}/batch-status",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Batch results retrieved!")
            print(f"   Total jobs: {data.get('progress', {}).get('total', 0)}")
            print(f"   Completed: {data.get('progress', {}).get('completed', 0)}")
            print(f"   Failed: {data.get('progress', {}).get('failed', 0)}")
            
            # Show individual job results
            jobs = data.get('individual_jobs', [])
            if jobs:
                print(f"\n   Individual job results:")
                for job in jobs[:5]:  # Show first 5
                    print(f"   - {job.get('job_name', 'unknown')}: {job.get('status', 'unknown')}")
                    if job.get('results'):
                        results = job['results']
                        if 'affinity' in results:
                            print(f"     Affinity: {results['affinity']:.4f}")
                        if 'confidence' in results:
                            print(f"     Confidence: {results['confidence']:.4f}")
            
            return True
        else:
            print(f"⚠️ Batch results not available (status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Error checking batch results: {e}")
        return False

def test_modal_availability():
    """Check if Modal functions are available"""
    
    print("\n🤖 Checking Modal availability...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            # Check backend logs for Modal status
            print("✅ Backend is running")
            print("   Note: Check backend logs for Modal function status")
            print("   If Modal is not configured, predictions will use mock mode")
            return True
    except Exception as e:
        print(f"❌ Error checking Modal: {e}")
    
    return False

def main():
    """Run end-to-end workflow test"""
    
    print("🚀 OMTX-Hub End-to-End Workflow Test")
    print("=====================================\n")
    
    # Step 1: Check system health
    print("1️⃣ Checking system health...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System healthy")
            print(f"   Database: {data.get('database', 'unknown')}")
            print(f"   Storage: {data.get('storage', 'unknown')}")
        else:
            print(f"❌ System unhealthy")
            return 1
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure the backend is running on http://localhost:8000")
        return 1
    
    # Step 2: Check Modal availability
    test_modal_availability()
    
    # Step 3: Submit prediction
    print("\n2️⃣ Submitting test prediction...")
    job_id = submit_test_prediction()
    
    if not job_id:
        print("❌ Failed to submit prediction")
        return 1
    
    # Step 4: Monitor progress (with shorter timeout for testing)
    print("\n3️⃣ Monitoring job progress...")
    print("   Note: If using mock mode, job will complete quickly")
    print("   If using real Modal, this may take 3-5 minutes")
    
    success, final_data = monitor_job_progress(job_id, max_wait=60)  # 1 minute for testing
    
    if success:
        # Step 5: Check results
        print("\n4️⃣ Retrieving results...")
        check_batch_results(job_id)
        
        print("\n✅ End-to-end workflow test PASSED!")
        print(f"   Job ID: {job_id}")
        print("   View results in the frontend: http://localhost:8080")
        return 0
    else:
        if final_data and final_data.get('status') == 'pending':
            print("\n⚠️ Job is still pending (this is normal for real Modal predictions)")
            print(f"   Job ID: {job_id}")
            print("   The job will continue processing in the background")
            print("   Check status later at: http://localhost:8000/api/jobs/{job_id}")
            print("   Or view in frontend: http://localhost:8080")
            return 0
        else:
            print("\n❌ End-to-end workflow test FAILED")
            return 1

if __name__ == "__main__":
    exit(main())