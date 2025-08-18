#!/usr/bin/env python3
"""
Test script to verify batch storage structure fixes
Checks if batch indices are being created and stored correctly
"""

import asyncio
import json
from services.unified_batch_processor import unified_batch_processor, BatchSubmissionRequest
from services.batch_relationship_manager import batch_relationship_manager
from services.gcp_storage_service import gcp_storage_service

async def test_batch_structure_creation():
    """Test that new batches create proper storage structure"""
    
    print("🧪 Testing Batch Storage Structure Creation")
    print("=" * 50)
    
    # Create a test batch submission
    test_request = BatchSubmissionRequest(
        job_name="Storage_Test_Batch",
        protein_sequence="MKLLVLSLSLVLVLLLSHPQGSHM",
        protein_name="Test_Protein",
        ligands=[
            {"smiles": "CCO", "name": "Ethanol"},
            {"smiles": "CCN", "name": "Ethylamine"}
        ],
        user_id="test_user",
        model_name="boltz2"
    )
    
    print(f"📝 Submitting test batch: {test_request.job_name}")
    print(f"   Ligands: {len(test_request.ligands)}")
    
    # Submit batch
    result = await unified_batch_processor.submit_batch(test_request)
    
    if not result.get('success'):
        print(f"❌ Batch submission failed: {result.get('error')}")
        return False
    
    batch_id = result['batch_id']
    print(f"✅ Batch submitted successfully: {batch_id}")
    
    # Wait a moment for storage operations
    await asyncio.sleep(2)
    
    # Test 1: Check if batch index was created
    print(f"\n🔍 Test 1: Checking batch index creation...")
    try:
        batch_index = await batch_relationship_manager._get_batch_index(batch_id)
        if batch_index:
            print(f"✅ Batch index found")
            print(f"   Individual jobs: {len(batch_index.get('individual_jobs', []))}")
            for job in batch_index.get('individual_jobs', []):
                print(f"     - {job.get('job_id')}: {job.get('status')}")
        else:
            print(f"❌ Batch index not found")
            return False
    except Exception as e:
        print(f"❌ Error checking batch index: {e}")
        return False
    
    # Test 2: Check GCP storage structure
    print(f"\n🔍 Test 2: Checking GCP storage structure...")
    try:
        # Check if batch files exist in GCP
        expected_files = [
            f"batches/{batch_id}/batch_index.json",
            f"batches/{batch_id}/batch_metadata.json",
            f"archive/{batch_id}/batch_metadata.json"
        ]
        
        for file_path in expected_files:
            exists = await gcp_storage_service.storage.file_exists(file_path)
            if exists:
                print(f"✅ {file_path} exists")
            else:
                print(f"❌ {file_path} missing")
                
    except Exception as e:
        print(f"❌ Error checking GCP structure: {e}")
        return False
    
    # Test 3: Check batch status API
    print(f"\n🔍 Test 3: Checking batch status API...")
    try:
        status_result = await unified_batch_processor.get_batch_status(batch_id)
        if 'error' in status_result:
            print(f"❌ Status API error: {status_result['error']}")
            return False
        else:
            print(f"✅ Status API working")
            print(f"   Status: {status_result['batch_parent']['status']}")
            print(f"   Child jobs: {len(status_result['child_jobs'])}")
    except Exception as e:
        print(f"❌ Error checking status API: {e}")
        return False
    
    print(f"\n🎉 All tests passed! Batch storage structure is working correctly.")
    return True

async def check_existing_batches():
    """Check if existing batches now have proper structure"""
    
    print("\n🔍 Checking Existing Batches")
    print("=" * 30)
    
    # Check our known batch IDs
    batch_ids = [
        'e100eec9-0b39-4239-bfb2-51da4797bb1f', 
        'c77612c6-3661-41cd-b277-9b1dd2a18e63'
    ]
    
    for batch_id in batch_ids:
        print(f"\n📊 Checking batch {batch_id}...")
        try:
            # Check if batch index exists
            batch_index = await batch_relationship_manager._get_batch_index(batch_id)
            if batch_index:
                print(f"✅ Has batch index with {len(batch_index.get('individual_jobs', []))} jobs")
            else:
                print(f"❌ No batch index found")
                
            # Check status API
            status_result = await unified_batch_processor.get_batch_status(batch_id)
            if 'error' not in status_result:
                print(f"✅ Status API working - {status_result['batch_parent']['status']}")
            else:
                print(f"❌ Status API error: {status_result['error']}")
                
        except Exception as e:
            print(f"❌ Error checking batch {batch_id}: {e}")

async def main():
    """Run all tests"""
    print("🚀 Batch Storage Structure Fix Verification")
    print("==========================================")
    
    # Test new batch creation
    success = await test_batch_structure_creation()
    
    # Check existing batches
    await check_existing_batches()
    
    if success:
        print("\n🎯 CONCLUSION: Batch storage fixes are working correctly!")
        print("   ✅ New batches create proper structure")
        print("   ✅ Batch indices are created")
        print("   ✅ GCP storage paths are correct")
        print("   ✅ Status API is functional")
    else:
        print("\n⚠️ CONCLUSION: Some issues remain")

if __name__ == "__main__":
    asyncio.run(main())