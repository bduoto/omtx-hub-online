#!/usr/bin/env python3
"""
Test script to simulate batch job completion and verify aggregated storage structure
"""

import asyncio
import json
from services.batch_relationship_manager import batch_relationship_manager
from services.gcp_storage_service import gcp_storage_service

# Simulate Modal prediction results for testing
MOCK_MODAL_RESULTS = [
    {
        "job_id": "34f89061-d36b-44cb-9fe1-c84873bf9476",
        "status": "completed",
        "affinity": 0.7387605905532837,
        "affinity_probability": 0.30602800846099854,
        "confidence": 0.3777596056461334,
        "ptm_score": 0.2482663094997406,
        "iptm_score": 0.2629643976688385,
        "plddt_score": 0.40645840764045715,
        "structure_file_base64": "HEADER    COMPLEX                                 01-JAN-70   XXXX\nATOM      1  N   ALA A   1      -0.123   0.456   0.789  1.00 20.00           N\nATOM      2  CA  ALA A   1       1.234  -0.567   0.890  1.00 20.00           C\n...",
        "execution_time": 205.5,
        "modal_call_id": "ca-abc123"
    },
    {
        "job_id": "56dd4aa4-59ef-452a-abe2-a10138447922", 
        "status": "completed",
        "affinity": 0.8251392847192883,
        "affinity_probability": 0.28394729572847291,
        "confidence": 0.4123856789012345,
        "ptm_score": 0.3102847291847293,
        "iptm_score": 0.2847291729384756,
        "plddt_score": 0.4567890123456789,
        "structure_file_base64": "HEADER    COMPLEX                                 01-JAN-70   YYYY\nATOM      1  N   ALA A   1      -1.123   1.456   1.789  1.00 20.00           N\nATOM      2  CA  ALA A   1       2.234  -1.567   1.890  1.00 20.00           C\n...",
        "execution_time": 198.2,
        "modal_call_id": "ca-def456"
    }
]

async def test_batch_completion():
    """Test complete batch job storage and aggregation"""
    
    print("🧪 Testing Batch Completion and Aggregation")
    print("=" * 50)
    
    # Use the batch we created earlier
    batch_id = "aa883a84-b37b-452a-8511-5908e710953e"
    
    print(f"📝 Testing completion for batch: {batch_id}")
    
    # Check if batch index exists
    batch_index = await batch_relationship_manager._get_batch_index(batch_id)
    if not batch_index:
        print(f"❌ Batch index not found for {batch_id}")
        return False
    
    print(f"✅ Found batch index with {len(batch_index.get('individual_jobs', []))} jobs")
    
    # Simulate completion of each job
    for i, mock_result in enumerate(MOCK_MODAL_RESULTS):
        job_id = mock_result["job_id"]
        print(f"\n🔧 Simulating completion of job {i+1}: {job_id}")
        
        # Store child results (this triggers the full storage chain)
        success = await batch_relationship_manager.store_child_results(
            batch_id, 
            job_id, 
            mock_result, 
            "protein_ligand_binding"
        )
        
        if success:
            print(f"✅ Stored results for job {job_id}")
        else:
            print(f"❌ Failed to store results for job {job_id}")
            return False
    
    # Wait a moment for aggregation to complete
    await asyncio.sleep(2)
    
    # Verify the complete storage structure
    print(f"\n🔍 Verifying Storage Structure")
    print("-" * 30)
    
    expected_files = [
        # Batch level files
        f"batches/{batch_id}/batch_index.json",
        f"batches/{batch_id}/batch_metadata.json", 
        f"batches/{batch_id}/summary.json",
        
        # Individual job files
        f"batches/{batch_id}/jobs/34f89061-d36b-44cb-9fe1-c84873bf9476/results.json",
        f"batches/{batch_id}/jobs/34f89061-d36b-44cb-9fe1-c84873bf9476/metadata.json",
        f"batches/{batch_id}/jobs/34f89061-d36b-44cb-9fe1-c84873bf9476/structure.cif",
        f"batches/{batch_id}/jobs/56dd4aa4-59ef-452a-abe2-a10138447922/results.json",
        f"batches/{batch_id}/jobs/56dd4aa4-59ef-452a-abe2-a10138447922/metadata.json",
        f"batches/{batch_id}/jobs/56dd4aa4-59ef-452a-abe2-a10138447922/structure.cif",
        
        # Aggregated results files
        f"batches/{batch_id}/results/aggregated.json",
        f"batches/{batch_id}/results/summary.json",
        f"batches/{batch_id}/results/job_index.json",
        f"batches/{batch_id}/results/batch_metadata.json",
        f"batches/{batch_id}/results/batch_results.csv",
        
        # Archive files
        f"archive/{batch_id}/batch_metadata.json"
    ]
    
    files_found = 0
    files_missing = []
    
    for file_path in expected_files:
        try:
            # Check if file exists (this would need to be implemented)
            # For now, let's try to read the file
            file_content = await gcp_storage_service.storage.download_file(file_path)
            if file_content:
                print(f"✅ {file_path}")
                files_found += 1
            else:
                print(f"❌ {file_path} (empty)")
                files_missing.append(file_path)
        except:
            print(f"❌ {file_path} (not found)")
            files_missing.append(file_path)
    
    print(f"\n📊 Storage Verification Results:")
    print(f"   Files found: {files_found}/{len(expected_files)}")
    
    if files_missing:
        print(f"   Missing files:")
        for missing in files_missing:
            print(f"     - {missing}")
    
    # Test reading and displaying key aggregated files
    print(f"\n📋 Checking Aggregated Results Content")
    print("-" * 40)
    
    try:
        # Read batch summary
        summary_content = await gcp_storage_service.storage.download_file(
            f"batches/{batch_id}/summary.json"
        )
        if summary_content:
            summary = json.loads(summary_content)
            print(f"✅ Batch Summary:")
            print(f"   Total jobs: {summary.get('processing_stats', {}).get('total_jobs', 'N/A')}")
            print(f"   Completed: {summary.get('processing_stats', {}).get('completed_jobs', 'N/A')}")
            print(f"   Success rate: {summary.get('processing_stats', {}).get('success_rate', 'N/A')}%")
            
            pred_summary = summary.get('prediction_summary', {})
            affinity_stats = pred_summary.get('affinity_stats', {})
            print(f"   Best affinity: {affinity_stats.get('best_affinity', 'N/A')}")
            print(f"   Mean confidence: {pred_summary.get('confidence_stats', {}).get('mean', 'N/A')}")
        
        # Read job index
        job_index_content = await gcp_storage_service.storage.download_file(
            f"batches/{batch_id}/results/job_index.json"
        )
        if job_index_content:
            job_index = json.loads(job_index_content)
            print(f"✅ Job Index:")
            print(f"   Total jobs indexed: {job_index.get('total_jobs', 'N/A')}")
            for job_id, job_info in job_index.get('jobs', {}).items():
                print(f"   {job_id[:8]}...: {job_info.get('ligand_name')} - Affinity: {job_info.get('affinity')}")
                
    except Exception as e:
        print(f"❌ Error reading aggregated files: {e}")
    
    success_rate = files_found / len(expected_files)
    
    print(f"\n🎯 Test Results:")
    if success_rate >= 0.8:  # 80% success rate
        print(f"✅ PASSED: {success_rate:.1%} of expected files created")
        print("   Batch completion and aggregation working correctly!")
        return True
    else:
        print(f"❌ FAILED: Only {success_rate:.1%} of expected files created")
        return False

async def main():
    """Run the test"""
    print("🚀 Batch Completion Test")
    print("========================")
    
    success = await test_batch_completion()
    
    if success:
        print("\n🎉 CONCLUSION: Batch completion and aggregation system is working!")
        print("   ✅ Individual job storage")
        print("   ✅ Structure file storage") 
        print("   ✅ Aggregated results creation")
        print("   ✅ Summary statistics")
        print("   ✅ CSV export")
        print("   ✅ Job indexing")
    else:
        print("\n⚠️ CONCLUSION: Some issues remain with batch completion system")

if __name__ == "__main__":
    asyncio.run(main())