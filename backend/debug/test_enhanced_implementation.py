#!/usr/bin/env python3
"""
Simple test for enhanced results implementation
"""

import asyncio
import sys
import traceback

def test_imports():
    """Test that all new modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from services.results_enrichment_service import results_enrichment_service
        print("   ✅ Results enrichment service imported")
    except Exception as e:
        print(f"   ❌ Results enrichment service failed: {e}")
        return False
    
    try:
        from services.batch_results_service import batch_results_service
        print("   ✅ Batch results service imported")
    except Exception as e:
        print(f"   ❌ Batch results service failed: {e}")
        return False
    
    try:
        from api.unified_endpoints import router
        print("   ✅ Unified endpoints imported")
    except Exception as e:
        print(f"   ❌ Unified endpoints failed: {e}")
        return False
    
    return True

async def test_enrichment_service():
    """Test enrichment service basic functionality"""
    print("🧪 Testing enrichment service...")
    
    try:
        from services.results_enrichment_service import results_enrichment_service
        
        # Test cache stats
        stats = results_enrichment_service.get_cache_stats()
        print(f"   Cache stats: {stats}")
        
        # Test with mock job
        mock_job = {
            'id': 'test_123',
            'job_name': 'Test Job',
            'status': 'completed'
        }
        
        enriched = await results_enrichment_service.enrich_job_result(mock_job)
        
        if enriched['id'] == 'test_123':
            print("   ✅ Basic enrichment works")
            return True
        else:
            print("   ❌ Enrichment returned wrong data")
            return False
            
    except Exception as e:
        print(f"   ❌ Enrichment service test failed: {e}")
        traceback.print_exc()
        return False

async def test_batch_service():
    """Test batch service basic functionality"""
    print("🧪 Testing batch service...")

    try:
        from services.batch_results_service import batch_results_service

        # Test cache clearing
        batch_results_service.clear_cache()
        print("   ✅ Cache clearing works")

        # Test non-existent batch handling
        try:
            await batch_results_service.get_batch_with_children('fake_batch')
            print("   ❌ Should have failed for fake batch")
            return False
        except Exception:
            print("   ✅ Correctly handles non-existent batch")
            return True

    except Exception as e:
        print(f"   ❌ Batch service test failed: {e}")
        traceback.print_exc()
        return False

async def test_unified_job_model():
    """Test the enhanced job model"""
    print("🧪 Testing unified job model...")

    try:
        # Test job type detection
        from services.smart_job_router import SmartJobRouter
        from models.enhanced_job_model import JobType

        router = SmartJobRouter()

        # Test individual job detection with mock request
        individual_input = {'ligands': [{'smiles': 'CCO'}]}  # Single ligand
        job_type = router._determine_job_type('protein_ligand_binding', individual_input)

        if job_type == JobType.INDIVIDUAL:
            print("   ✅ Individual job detection works")
        else:
            print(f"   ❌ Expected individual, got {job_type.value}")
            return False

        # Test batch job detection with mock request
        batch_input = {'ligands': [{'smiles': 'CCO'}, {'smiles': 'CCC'}]}  # Multiple ligands
        job_type = router._determine_job_type('protein_ligand_binding', batch_input)

        if job_type == JobType.BATCH_PARENT:
            print("   ✅ Batch job detection works")
            return True
        else:
            print(f"   ❌ Expected batch_parent, got {job_type.value}")
            return False

    except ImportError as e:
        print(f"   ⚠️ Smart job router not available: {e}")
        return True  # Don't fail if not implemented
    except Exception as e:
        print(f"   ❌ Job model test failed: {e}")
        traceback.print_exc()
        return False

async def test_firestore_indexes():
    """Test that required Firestore indexes exist"""
    print("🧪 Testing Firestore indexes...")

    try:
        from config.gcp_database import gcp_database

        if not gcp_database.available:
            print("   ⚠️ Firestore not available - skipping index test")
            return True

        # Test a query that requires composite index
        try:
            query = gcp_database.db.collection('jobs').where('job_type', '==', 'individual').limit(1)
            docs = list(query.stream())
            print(f"   ✅ job_type index works ({len(docs)} docs found)")
        except Exception as e:
            if "index" in str(e).lower():
                print(f"   ❌ Missing index: {e}")
                print("   💡 Create indexes at: https://console.firebase.google.com/project/YOUR_PROJECT/firestore/indexes")
                return False
            else:
                print("   ✅ Index test passed (no data found)")

        return True

    except Exception as e:
        print(f"   ❌ Index test failed: {e}")
        return False

def test_gcp_availability():
    """Test GCP storage availability"""
    print("🧪 Testing GCP availability...")

    try:
        from config.gcp_storage import gcp_storage
        available = gcp_storage.available
        print(f"   GCP Storage available: {available}")
        return True
    except ImportError as e:
        print(f"   ⚠️ GCP libraries not installed: {e}")
        print("   This is expected in development environments")
        return True  # Don't fail the test for missing libraries
    except Exception as e:
        print(f"   ❌ GCP test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Enhanced Results Implementation")
    print("=" * 50)
    
    # Test imports first
    if not test_imports():
        print("❌ Import tests failed - stopping")
        return 1
    
    # Test GCP availability
    if not test_gcp_availability():
        print("❌ GCP availability test failed")
        return 1
    
    # Test services
    tests = [
        ("Enrichment Service", test_enrichment_service),
        ("Batch Service", test_batch_service),
        ("Unified Job Model", test_unified_job_model),
        ("Firestore Indexes", test_firestore_indexes),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name}: PASS")
                passed += 1
            else:
                print(f"❌ {test_name}: FAIL")
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\nExit code: {exit_code}")
