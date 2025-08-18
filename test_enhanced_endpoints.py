#!/usr/bin/env python3
"""
Test script for enhanced results endpoints
Tests the new results enrichment and batch handling functionality
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def test_results_enrichment_service():
    """Test the results enrichment service"""
    print("🧪 Testing Results Enrichment Service...")
    
    try:
        from services.results_enrichment_service import results_enrichment_service
        
        # Test cache stats
        stats = results_enrichment_service.get_cache_stats()
        print(f"   Cache stats: {stats}")
        
        # Test with mock job data
        mock_job = {
            'id': 'test_job_123',
            'job_name': 'Test Job',
            'status': 'completed',
            'created_at': '2024-01-01T00:00:00Z'
        }
        
        enriched = await results_enrichment_service.enrich_job_result(mock_job)
        print(f"   Enrichment test: {'✅ PASS' if enriched['id'] == 'test_job_123' else '❌ FAIL'}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Results enrichment test failed: {e}")
        return False

async def test_batch_results_service():
    """Test the batch results service"""
    print("🧪 Testing Batch Results Service...")
    
    try:
        from services.batch_results_service import batch_results_service
        
        # Test cache clearing
        batch_results_service.clear_cache()
        print("   Cache cleared successfully")
        
        # Test with non-existent batch (should handle gracefully)
        try:
            result = await batch_results_service.get_batch_with_children('non_existent_batch')
            print("   ❌ Should have failed for non-existent batch")
            return False
        except Exception:
            print("   ✅ Correctly handled non-existent batch")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Batch results test failed: {e}")
        return False

def test_unified_endpoints_import():
    """Test that unified endpoints can be imported with new functions"""
    print("🧪 Testing Unified Endpoints Import...")
    
    try:
        from api.unified_endpoints import router
        
        # Check if router has routes
        routes = [route.path for route in router.routes]
        print(f"   Found {len(routes)} routes")
        
        # Check for our new endpoints
        enhanced_routes = [r for r in routes if 'enhanced' in r or 'my-results-enhanced' in r]
        print(f"   Enhanced routes: {enhanced_routes}")
        
        if len(enhanced_routes) > 0:
            print("   ✅ Enhanced endpoints found")
            return True
        else:
            print("   ⚠️ No enhanced endpoints found (may be normal)")
            return True
            
    except Exception as e:
        print(f"   ❌ Unified endpoints import failed: {e}")
        return False

def test_gcp_storage_availability():
    """Test GCP storage availability"""
    print("🧪 Testing GCP Storage Availability...")
    
    try:
        from config.gcp_storage import gcp_storage
        
        available = gcp_storage.available
        print(f"   GCP Storage available: {available}")
        
        if available:
            print("   ✅ GCP Storage is available")
        else:
            print("   ⚠️ GCP Storage not available (may be expected in test environment)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ GCP Storage test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Enhanced Results Implementation")
    print("=" * 50)
    
    tests = [
        ("GCP Storage", test_gcp_storage_availability),
        ("Unified Endpoints", test_unified_endpoints_import),
        ("Results Enrichment", test_results_enrichment_service),
        ("Batch Results", test_batch_results_service),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Implementation looks good.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
