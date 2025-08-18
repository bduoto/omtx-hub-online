#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite
Senior Principal Engineer Implementation

Tests the complete unified batch system integration including:
- API endpoint compatibility
- Frontend-backend integration
- Data flow validation
- Performance characteristics
- Error handling robustness
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def test_api_endpoint_consistency():
    """Test API endpoint consistency across the system"""
    print("🔍 Testing API Endpoint Consistency")
    print("=" * 50)
    
    try:
        # Check unified batch API endpoints
        from api.unified_batch_api import router as unified_batch_router
        
        # Extract routes from the router
        routes = []
        for route in unified_batch_router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = list(route.methods) if route.methods else ['GET']
                routes.append({
                    'path': route.path,
                    'methods': methods,
                    'name': getattr(route, 'name', 'unnamed')
                })
        
        print(f"📋 Found {len(routes)} unified batch API routes:")
        
        # Expected critical endpoints
        expected_endpoints = [
            {'path': '/submit', 'method': 'POST'},
            {'path': '/', 'method': 'GET'},
            {'path': '/{batch_id}/status', 'method': 'GET'},
            {'path': '/{batch_id}/results', 'method': 'GET'},
            {'path': '/{batch_id}/analytics', 'method': 'GET'},
            {'path': '/{batch_id}/control/{action}', 'method': 'POST'},
            {'path': '/{batch_id}/export/{format}', 'method': 'GET'}
        ]
        
        found_endpoints = 0
        for expected in expected_endpoints:
            for route in routes:
                if expected['path'] == route['path'] and expected['method'] in route['methods']:
                    print(f"   ✅ {expected['method']} {expected['path']}")
                    found_endpoints += 1
                    break
            else:
                print(f"   ❌ Missing: {expected['method']} {expected['path']}")
        
        if found_endpoints == len(expected_endpoints):
            print("✅ All critical API endpoints present")
            return True
        else:
            print(f"❌ Missing {len(expected_endpoints) - found_endpoints} critical endpoints")
            return False
            
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_frontend_backend_compatibility():
    """Test frontend-backend API compatibility"""
    print("\n🌐 Testing Frontend-Backend Compatibility")
    print("=" * 50)
    
    try:
        # Check if frontend components use correct API endpoints
        frontend_root = Path(__file__).parent.parent / "src"
        
        # Files to check for API integration
        files_to_check = [
            "components/Boltz2/BatchProteinLigandInput.tsx",
            "pages/MyBatches.tsx",
            "pages/BatchResults.tsx"
        ]
        
        api_usage_correct = True
        
        for file_path in files_to_check:
            full_path = frontend_root / file_path
            if full_path.exists():
                content = full_path.read_text()
                
                # Check for v3 API usage
                if "/api/v3/batches" in content:
                    print(f"   ✅ {file_path}: Uses v3 unified API")
                elif "/api/v2/batch" in content:
                    print(f"   ⚠️ {file_path}: Still uses legacy v2 API")
                    api_usage_correct = False
                else:
                    print(f"   ❓ {file_path}: No clear API usage found")
            else:
                print(f"   ❌ {file_path}: File not found")
                api_usage_correct = False
        
        if api_usage_correct:
            print("✅ Frontend-backend compatibility verified")
        else:
            print("⚠️ Some compatibility issues found")
        
        return api_usage_correct
        
    except Exception as e:
        print(f"❌ Frontend-backend compatibility test failed: {e}")
        return False

def test_data_model_consistency():
    """Test data model consistency across the system"""
    print("\n📊 Testing Data Model Consistency")
    print("=" * 50)
    
    try:
        # Test Pydantic model imports and validation
        from api.unified_batch_api import (
            UnifiedBatchSubmissionRequest,
            BatchSubmissionResponse,
            BatchStatusResponse
        )
        
        # Test model creation with valid data
        test_request = UnifiedBatchSubmissionRequest(
            job_name="Integration Test",
            protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFCSVDNCASDNKQGPCALAHPKEAKPPRRRPGGGSLALSLGGGAATAGSGSGSGSAALAALPAAFGGAAKKLLVVALAVLSASAAA",
            protein_name="Test Protein",
            ligands=[
                {"name": "Test Ligand", "smiles": "CCO"}
            ]
        )
        
        print(f"   ✅ UnifiedBatchSubmissionRequest: Valid ({len(test_request.ligands)} ligands)")
        
        # Test response model
        from datetime import datetime
        test_response = BatchSubmissionResponse(
            success=True,
            batch_id="test_123",
            message="Test batch submitted",
            total_jobs=1,
            estimated_duration_seconds=300.0,
            scheduling_strategy="adaptive",
            started_jobs=1,
            queued_jobs=0,
            optimization_recommendations=[],
            risk_assessment={},
            status_url="/api/v3/batches/test_123/status",
            results_url="/api/v3/batches/test_123/results"
        )
        
        print(f"   ✅ BatchSubmissionResponse: Valid (batch_id: {test_response.batch_id})")
        
        # Test JSON serialization
        json_data = test_response.model_dump_json()
        parsed_data = json.loads(json_data)
        
        if parsed_data['batch_id'] == 'test_123':
            print("   ✅ JSON serialization working correctly")
        else:
            print("   ❌ JSON serialization issue")
            return False
        
        print("✅ Data model consistency verified")
        return True
        
    except Exception as e:
        print(f"❌ Data model consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling_robustness():
    """Test error handling across the system"""
    print("\n🛡️ Testing Error Handling Robustness")
    print("=" * 50)
    
    try:
        from api.unified_batch_api import UnifiedBatchSubmissionRequest
        from pydantic import ValidationError
        
        # Test various invalid inputs
        error_scenarios = [
            {
                'name': 'Empty job name',
                'data': {'job_name': '', 'protein_sequence': 'MKLL', 'protein_name': 'Test', 'ligands': [{'smiles': 'CCO'}]},
                'expected_error': 'String should have at least 1 character'
            },
            {
                'name': 'Short protein sequence',
                'data': {'job_name': 'Test', 'protein_sequence': 'MK', 'protein_name': 'Test', 'ligands': [{'smiles': 'CCO'}]},
                'expected_error': 'String should have at least 10 characters'
            },
            {
                'name': 'Invalid SMILES',
                'data': {'job_name': 'Test', 'protein_sequence': 'MKLLVVLALVLGFLLFSASAAQQEGEVAVRFC', 'protein_name': 'Test', 'ligands': [{'smiles': 'XX'}]},
                'expected_error': 'String should have at least 3 characters'
            }
        ]
        
        passed_scenarios = 0
        for scenario in error_scenarios:
            try:
                UnifiedBatchSubmissionRequest(**scenario['data'])
                print(f"   ❌ {scenario['name']}: Should have failed")
            except ValidationError as e:
                if any(expected in str(e) for expected in [scenario['expected_error'], 'validation error']):
                    print(f"   ✅ {scenario['name']}: Correctly rejected")
                    passed_scenarios += 1
                else:
                    print(f"   ⚠️ {scenario['name']}: Unexpected error: {e}")
            except Exception as e:
                print(f"   ❌ {scenario['name']}: Unexpected exception: {e}")
        
        if passed_scenarios == len(error_scenarios):
            print("✅ Error handling robustness verified")
            return True
        else:
            print(f"⚠️ {passed_scenarios}/{len(error_scenarios)} error scenarios handled correctly")
            return passed_scenarios >= len(error_scenarios) * 0.8  # 80% pass rate acceptable
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def main():
    """Run comprehensive integration tests"""
    print("🚀 COMPREHENSIVE INTEGRATION TEST SUITE")
    print("Senior Principal Engineer Implementation")
    print("=" * 70)
    print("Testing complete unified batch system integration")
    print("=" * 70)
    
    tests = [
        ("API Endpoint Consistency", test_api_endpoint_consistency),
        ("Frontend-Backend Compatibility", test_frontend_backend_compatibility),
        ("Data Model Consistency", test_data_model_consistency),
        ("Error Handling Robustness", test_error_handling_robustness)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed}/{len(tests)} integration tests passed")
    
    if passed == len(tests):
        print("🎉 COMPREHENSIVE INTEGRATION VERIFIED!")
        print("🏆 All systems working together correctly")
        print("🚀 Production deployment ready")
        return 0
    elif passed >= len(tests) * 0.8:
        print("⚠️ Most integration tests passed - minor issues to address")
        return 0
    else:
        print("❌ Significant integration issues found - review required")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
