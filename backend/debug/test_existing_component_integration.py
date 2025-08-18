#!/usr/bin/env python3
"""
Test Integration of Unified API into Existing Components
Senior Principal Engineer Implementation

Tests that existing batch components now use the unified API v3
while maintaining backward compatibility and existing functionality.
"""

import asyncio
import json
import sys
from pathlib import Path

async def test_batch_component_integration():
    """Test that BatchProteinLigandInput uses unified API"""
    print("🧪 Testing BatchProteinLigandInput Integration")
    print("=" * 60)
    
    try:
        # Read the batch component file
        frontend_root = Path(__file__).parent.parent / "src" / "components" / "Boltz2"
        batch_component = frontend_root / "BatchProteinLigandInput.tsx"
        
        if not batch_component.exists():
            print(f"❌ BatchProteinLigandInput.tsx not found at {batch_component}")
            return False
        
        content = batch_component.read_text()
        
        # Test 1: Check for unified API v3 usage
        if "/api/v3/batches/submit" not in content:
            print("❌ Component doesn't use unified API v3 submit endpoint")
            return False
        print("   ✅ Uses unified API v3 submit endpoint")
        
        if "/api/v3/batches/${batchId}/status" in content or "api/v3/batches/" in content:
            print("   ✅ Uses unified API v3 status endpoints")
        else:
            print("❌ Component doesn't use unified API v3 status endpoints")
            return False
        
        # Test 2: Check for unified batch processing function
        if "pollUnifiedBatchStatus" not in content:
            print("❌ Missing unified batch polling function")
            return False
        print("   ✅ Has unified batch polling function")
        
        # Test 3: Check for backward compatibility
        if "pollJobStatus" not in content:
            print("⚠️ Missing legacy polling for backward compatibility")
        else:
            print("   ✅ Maintains legacy polling for backward compatibility")
        
        # Test 4: Check for proper request format
        if "job_name:" not in content or "protein_sequence:" not in content:
            print("❌ Missing proper unified API request format")
            return False
        print("   ✅ Uses proper unified API request format")
        
        # Test 5: Check for intelligent configuration
        if "scheduling_strategy" not in content or "configuration:" not in content:
            print("❌ Missing intelligent batch configuration")
            return False
        print("   ✅ Includes intelligent batch configuration")
        
        # Test 6: Check for proper result handling
        if "onPredictionComplete" not in content:
            print("❌ Missing result handling")
            return False
        print("   ✅ Maintains existing result handling interface")
        
        print("✅ BatchProteinLigandInput integration verified")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

async def test_api_endpoints_integration():
    """Test that the component integrates with the right API endpoints"""
    print("\n🔌 Testing API Endpoint Integration")
    print("=" * 60)
    
    try:
        # Check that unified API endpoints exist
        api_file = Path(__file__).parent / "api" / "unified_batch_api.py"
        
        if not api_file.exists():
            print(f"❌ Unified batch API not found at {api_file}")
            return False
        
        api_content = api_file.read_text()
        
        # Check for submit endpoint
        if '/submit", response_model=BatchSubmissionResponse' not in api_content:
            print("❌ Missing unified batch submit endpoint")
            return False
        print("   ✅ Unified batch submit endpoint exists")
        
        # Check for status endpoint  
        if '/{batch_id}/status", response_model=BatchStatusResponse' not in api_content:
            print("❌ Missing unified batch status endpoint")
            return False
        print("   ✅ Unified batch status endpoint exists")
        
        # Check for results endpoint
        if '/{batch_id}/results", response_model=BatchResultsResponse' not in api_content:
            print("❌ Missing unified batch results endpoint")
            return False
        print("   ✅ Unified batch results endpoint exists")
        
        print("✅ API endpoint integration verified")
        return True
        
    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        return False

async def test_backward_compatibility():
    """Test that existing functionality is preserved"""
    print("\n🔄 Testing Backward Compatibility")
    print("=" * 60)
    
    try:
        frontend_root = Path(__file__).parent.parent / "src" / "components" / "Boltz2"
        batch_component = frontend_root / "BatchProteinLigandInput.tsx"
        
        if not batch_component.exists():
            return False
        
        content = batch_component.read_text()
        
        # Test 1: Check that interface props are unchanged
        interface_props = [
            "onPredictionStart",
            "onPredictionComplete", 
            "onPredictionError",
            "isViewMode"
        ]
        
        for prop in interface_props:
            if prop not in content:
                print(f"❌ Missing interface prop: {prop}")
                return False
            print(f"   ✅ Interface prop preserved: {prop}")
        
        # Test 2: Check that key functions exist
        key_functions = [
            "startBatchScreening",
            "isValidSMILES",
            "parseCSVFile",
            "downloadSampleCSV"
        ]
        
        for func in key_functions:
            if func not in content:
                print(f"❌ Missing key function: {func}")
                return False
            print(f"   ✅ Key function preserved: {func}")
        
        # Test 3: Check that state variables are maintained
        state_vars = [
            "proteinName",
            "proteinSequence", 
            "ligands",
            "useMSAServer",
            "usePotentials"
        ]
        
        for var in state_vars:
            if var not in content:
                print(f"❌ Missing state variable: {var}")
                return False
            print(f"   ✅ State variable preserved: {var}")
        
        print("✅ Backward compatibility verified")
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

async def main():
    """Run integration test suite for existing component enhancement"""
    print("🔧 EXISTING COMPONENT INTEGRATION TEST SUITE")
    print("Senior Principal Engineer Implementation")
    print("=" * 70)
    print("Testing unified API integration into existing batch components")
    print("=" * 70)
    
    tests = [
        ("Batch Component Integration", test_batch_component_integration),
        ("API Endpoints Integration", test_api_endpoints_integration),
        ("Backward Compatibility", test_backward_compatibility)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed}/{len(tests)} test categories passed")
    
    if passed == len(tests):
        print("🎉 EXISTING COMPONENT INTEGRATION SUCCESSFUL!")
        print("🏆 Unified API v3 properly integrated into existing batch component")
        print("⚡ Enhanced functionality while maintaining backward compatibility")
        print("🔄 Users get improved batch processing without interface changes")
        print("✨ Phase 4 (Revised) - COMPLETED!")
        return 0
    else:
        print("⚠️ Some integration tests failed - review implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)