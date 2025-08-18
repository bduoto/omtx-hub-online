#!/usr/bin/env python3
"""
Test that file naming service now requires protein_name
"""

import sys
import os
sys.path.append('.')

from services.file_naming import file_naming

def test_file_naming_requires_protein_name():
    """Test that file naming now requires protein_name"""
    
    print("🧪 Testing file naming service requires protein_name...")
    
    # Test 1: Job data without protein_name should raise error
    job_data_without_protein_name = {
        'id': 'test_job_123',
        'input_data': {
            'job_name': 'test_job',
            'protein_sequence': 'MKTAYIAKQRQISFVKSHFSRQ',
            'parent_batch_id': 'batch_123',
            'batch_index': 0,
            'ligand_name': 'test_ligand'
            # Missing protein_name
        }
    }
    
    try:
        result = file_naming.generate_job_file_names(job_data_without_protein_name)
        print("❌ Expected error but got result:", result)
        return False
    except ValueError as e:
        if "protein_name is required" in str(e):
            print("✅ Correctly rejected job without protein_name")
            print(f"   Error message: {e}")
        else:
            print(f"❌ Got unexpected error: {e}")
            return False
    
    # Test 2: Job data with protein_name should work
    job_data_with_protein_name = {
        'id': 'test_job_123',
        'input_data': {
            'job_name': 'dwDO5y68',
            'protein_name': 'TRIM25',  # Now provided
            'protein_sequence': 'MKTAYIAKQRQISFVKSHFSRQ',
            'parent_batch_id': 'batch_123',
            'batch_index': 0,
            'ligand_name': 'compound_A'
        }
    }
    
    try:
        result = file_naming.generate_job_file_names(job_data_with_protein_name)
        expected_cif = "dwDO5y68_TRIM25_1_compound_A.cif"
        actual_cif = result.get('structure_cif')
        
        print(f"   Generated file names:")
        for file_type, file_name in result.items():
            print(f"      {file_type}: {file_name}")
        
        if actual_cif == expected_cif:
            print(f"✅ Correctly generated file name: {actual_cif}")
            return True
        else:
            print(f"❌ Expected {expected_cif}, got {actual_cif}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error with valid data: {e}")
        return False

def test_non_batch_job():
    """Test non-batch job naming (should still work)"""
    
    print("🧪 Testing non-batch job naming...")
    
    job_data_single = {
        'id': 'single_job_123',
        'name': 'Single Job Test',
        'input_data': {
            'job_name': 'single_test',
            'protein_sequence': 'MKTAYIAKQRQISFVKSHFSRQ',
            # No parent_batch_id - this is a single job
        }
    }
    
    try:
        result = file_naming.generate_job_file_names(job_data_single)
        expected_cif = "single_test.cif"
        actual_cif = result.get('structure_cif')
        
        print(f"   Generated file names for single job:")
        for file_type, file_name in result.items():
            print(f"      {file_type}: {file_name}")
        
        if actual_cif == expected_cif:
            print(f"✅ Correctly generated single job file name: {actual_cif}")
            return True
        else:
            print(f"❌ Expected {expected_cif}, got {actual_cif}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error with single job data: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🚀 Testing protein_name requirement enforcement...\n")
    
    test1_passed = test_file_naming_requires_protein_name()
    print()
    
    test2_passed = test_non_batch_job()
    print()
    
    if test1_passed and test2_passed:
        print("✅ All tests passed! File naming now properly requires protein_name for batch jobs.")
        print("🎯 No more auto-generated fallback names like 'protein_60aa'")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())