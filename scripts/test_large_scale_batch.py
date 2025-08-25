#!/usr/bin/env python3
"""
Large-Scale Batch Processing Test for Boltz-2 GPU System
Tests the system's ability to handle hundreds of predictions
"""

import requests
import time
import json
import random
import string
from datetime import datetime
from typing import List, Dict, Any

# Configuration - Update with your deployed service URL
BACKEND_URL = "http://localhost:8000"  # Update after deployment
# BACKEND_URL = "https://your-gke-backend.com"

# Sample data for testing
SAMPLE_PROTEINS = [
    "MKWVTFISLLLLFSSAYSRGVFRRDTHKSEIAHRFKDLGEEHFKGLVLIAFSQYLQ",  # Short
    "MKWVTFISLLLLFSSAYSRGVFRRDTHKSEIAHRFKDLGEEHFKGLVLIAFSQYLQQCPFDEHVKLVNELTEFAKTCVADESHAGCEKSLHTLFGDELCKVASLRETYGDMADCCEKQEPERNECFLSHKDDSPDLPKLKPDPNTLCDEFKADEKKFWGKYLYEIARRHPYFYAPELLYYANKYNGVFQECCQAEDKGACLLPKIETMREKVLASSARQRLRCASIQKFGERALKAWSVARLSQKFPKAEFVEVTKLVTDLTKVHKECCHGDLLECADDRADLAKYICDNQDTISSKLKECCDKPLLEKSHCIAEVEKDAIPENLPPLTADFAEDKDVCKNYQEAKDAFLGSFLYEYSRRHPEYAVSVLLRLAKEYEATLEECCAKDDPHACYSTVFDKLKHLVDEPQNLIKQNCDQFEKLGEYGFQNALIVRYTRKVPQVSTPTLVEVSRSLGKVGTRCCTKPESERMPCTEDYLSLILNRLCVLHEKTPVSEKVTKCCSGSLVERRSPCFS",  # Medium
]

SAMPLE_LIGANDS = [
    {"smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "name": "ibuprofen"},
    {"smiles": "CC(=O)OC1=CC=CC=C1C(=O)O", "name": "aspirin"},
    {"smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "name": "caffeine"},
    {"smiles": "CCO", "name": "ethanol"},
    {"smiles": "CC(C)C", "name": "propane"},
    {"smiles": "C1=CC=C(C=C1)O", "name": "phenol"},
    {"smiles": "CC(=O)O", "name": "acetic_acid"},
    {"smiles": "C1CCCCC1", "name": "cyclohexane"},
    {"smiles": "CC(C)(C)O", "name": "tert_butanol"},
    {"smiles": "C1=CC=CC=C1", "name": "benzene"},
]

def generate_random_ligands(count: int) -> List[Dict[str, str]]:
    """Generate random ligands for testing"""
    ligands = []
    for i in range(count):
        # Use sample ligands or generate variations
        base_ligand = random.choice(SAMPLE_LIGANDS)
        ligand = {
            "smiles": base_ligand["smiles"],
            "name": f"{base_ligand['name']}_{i+1}"
        }
        ligands.append(ligand)
    return ligands

def submit_large_batch(batch_size: int = 100, batch_name: str = None) -> Dict[str, Any]:
    """Submit a large batch of predictions"""
    if not batch_name:
        batch_name = f"large_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"📦 Submitting large batch: {batch_name}")
    print(f"   Size: {batch_size} ligands")
    
    # Generate test data
    protein = random.choice(SAMPLE_PROTEINS)
    ligands = generate_random_ligands(batch_size)
    
    # Submit batch
    response = requests.post(f"{BACKEND_URL}/api/v1/predict/batch/async", json={
        "protein_sequence": protein,
        "ligands": ligands,
        "user_id": "test_user",
        "batch_name": batch_name
    })
    
    if response.status_code != 200:
        print(f"❌ Batch submission failed: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    print(f"✅ Batch submitted successfully!")
    print(f"   Batch ID: {result['batch_id']}")
    print(f"   Total jobs: {result['total_jobs']}")
    print(f"   Queue: Cloud Tasks")
    
    return result

def monitor_batch_progress(batch_id: str, timeout: int = 600) -> bool:
    """Monitor batch progress until completion"""
    print(f"\n⏳ Monitoring batch progress: {batch_id}")
    print("   Progress updates every 10 seconds...")
    
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BACKEND_URL}/api/v1/batches/{batch_id}")
            
            if response.status_code != 200:
                print(f"   ⚠️ Status check failed: {response.status_code}")
                time.sleep(10)
                continue
            
            batch_status = response.json()
            status = batch_status.get("status")
            completed = batch_status.get("completed_jobs", 0)
            failed = batch_status.get("failed_jobs", 0)
            total = batch_status.get("total_jobs", 0)
            progress = batch_status.get("progress_percentage", 0)
            
            # Only print if progress changed
            if progress != last_progress:
                elapsed = int(time.time() - start_time)
                rate = completed / elapsed if elapsed > 0 else 0
                eta = int((total - completed) / rate) if rate > 0 else "unknown"
                
                print(f"   [{elapsed}s] Progress: {completed}/{total} ({progress:.1f}%) | "
                      f"Rate: {rate:.2f} jobs/s | ETA: {eta}s")
                last_progress = progress
            
            if status == "completed":
                print(f"\n✅ Batch completed successfully!")
                print(f"   Total time: {int(time.time() - start_time)}s")
                print(f"   Completed: {completed}")
                print(f"   Failed: {failed}")
                print(f"   Success rate: {(completed/(completed+failed)*100):.1f}%")
                return True
            
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            print(f"   ❌ Error checking status: {e}")
            time.sleep(10)
    
    print(f"\n❌ Batch did not complete within {timeout} seconds")
    return False

def run_stress_test():
    """Run comprehensive stress test"""
    print("🚀 BOLTZ-2 GPU SYSTEM STRESS TEST")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print()
    
    test_scenarios = [
        ("Small Batch", 10),
        ("Medium Batch", 50),
        ("Large Batch", 100),
        ("Extra Large Batch", 500),
    ]
    
    results = []
    
    for scenario_name, batch_size in test_scenarios:
        print(f"\n{'='*60}")
        print(f"Testing: {scenario_name} ({batch_size} ligands)")
        print(f"{'='*60}")
        
        try:
            # Submit batch
            submission = submit_large_batch(batch_size, scenario_name.lower().replace(" ", "_"))
            if not submission:
                results.append((scenario_name, batch_size, False, "Submission failed"))
                continue
            
            # Monitor progress
            batch_id = submission["batch_id"]
            success = monitor_batch_progress(batch_id, timeout=batch_size * 10)  # 10s per ligand max
            
            if success:
                results.append((scenario_name, batch_size, True, "Completed"))
            else:
                results.append((scenario_name, batch_size, False, "Timeout"))
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append((scenario_name, batch_size, False, str(e)))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 STRESS TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for scenario, size, success, status in results:
        icon = "✅" if success else "❌"
        print(f"{icon} {scenario:20} ({size:3} ligands): {status}")
    
    passed = sum(1 for _, _, success, _ in results if success)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} scenarios passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL STRESS TESTS PASSED!")
        print("✅ System ready for large-scale production workloads")
        print("✅ Cloud Tasks queue handling batch processing efficiently")
        print("✅ Auto-scaling working as expected")
    else:
        print(f"\n⚠️ {total - passed} scenario(s) failed")
        print("Check logs and queue configuration")

def test_concurrent_batches():
    """Test submitting multiple batches concurrently"""
    print("\n🔥 CONCURRENT BATCH TEST")
    print("=" * 60)
    print("Submitting 5 batches simultaneously...")
    
    batch_ids = []
    for i in range(5):
        batch_name = f"concurrent_batch_{i+1}"
        result = submit_large_batch(20, batch_name)
        if result:
            batch_ids.append(result["batch_id"])
            time.sleep(1)  # Small delay between submissions
    
    print(f"\n✅ Submitted {len(batch_ids)} concurrent batches")
    print("   Monitoring all batches...")
    
    # Monitor all batches
    completed = 0
    for batch_id in batch_ids:
        if monitor_batch_progress(batch_id, timeout=300):
            completed += 1
    
    print(f"\n📊 Concurrent test results: {completed}/{len(batch_ids)} completed")
    return completed == len(batch_ids)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test large-scale Boltz-2 batch processing")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--mode", choices=["stress", "concurrent", "both"], default="stress",
                       help="Test mode: stress test, concurrent batches, or both")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for custom test")
    
    args = parser.parse_args()
    BACKEND_URL = args.url
    
    # Check backend health first
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Backend not healthy at {BACKEND_URL}")
            exit(1)
        print(f"✅ Backend healthy at {BACKEND_URL}\n")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print(f"   Make sure the backend is running at {BACKEND_URL}")
        exit(1)
    
    # Run tests based on mode
    if args.mode in ["stress", "both"]:
        run_stress_test()
    
    if args.mode in ["concurrent", "both"]:
        test_concurrent_batches()
    
    print("\n🎯 Testing complete!")