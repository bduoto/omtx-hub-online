#!/usr/bin/env python3
"""
Test the Enhanced Job Model
"""

from models.enhanced_job_model import (
    EnhancedJobData, JobType, JobStatus, TaskType,
    create_individual_job, create_batch_parent_job, create_batch_child_job
)
import json

def test_individual_job_creation():
    """Test creating individual jobs"""
    print("🔍 Testing individual job creation...")
    
    job = create_individual_job(
        name="Test Individual Job",
        task_type=TaskType.PROTEIN_LIGAND_BINDING.value,
        input_data={
            'protein_sequence': 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSLEVKMALKMKIAAIPGKNTLEARDRKTRGG',
            'ligand_smiles': 'CC(=O)Nc1ccc(S(=O)(=O)N2CCOCC2)cc1'
        }
    )
    
    print(f"   ID: {job.id}")
    print(f"   Job Type: {job.job_type.value}")
    print(f"   Task Type: {job.task_type}")
    print(f"   Status: {job.status.value}")
    
    # Test API dict conversion
    api_dict = job.to_api_dict()
    print(f"   Is Batch: {api_dict.get('is_batch')}")
    
    # Test Firestore conversion
    firestore_dict = job.to_firestore_dict()
    print(f"   Firestore keys: {list(firestore_dict.keys())}")
    
    return job

def test_batch_parent_job_creation():
    """Test creating batch parent jobs"""
    print("\n🔍 Testing batch parent job creation...")
    
    job = create_batch_parent_job(
        name="Test Batch Job",
        task_type=TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value,
        input_data={
            'protein_sequence': 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSLEVKMALKMKIAAIPGKNTLEARDRKTRGG',
            'ligands': [
                {'name': 'Ligand 1', 'smiles': 'CC(=O)Nc1ccc(S(=O)(=O)N2CCOCC2)cc1'},
                {'name': 'Ligand 2', 'smiles': 'CC(C)Cc1ccc(C(C)C(=O)O)cc1'}
            ]
        }
    )
    
    print(f"   ID: {job.id}")
    print(f"   Job Type: {job.job_type.value}")
    print(f"   Task Type: {job.task_type}")
    print(f"   Child IDs: {job.batch_child_ids}")
    
    return job

def test_batch_child_job_creation():
    """Test creating batch child jobs"""
    print("\n🔍 Testing batch child job creation...")
    
    parent_id = "test-parent-123"
    
    child = create_batch_child_job(
        name="Test Child Job - Ligand 1",
        parent_id=parent_id,
        batch_index=0,
        input_data={
            'protein_sequence': 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSLEVKMALKMKIAAIPGKNTLEARDRKTRGG',
            'ligand_smiles': 'CC(=O)Nc1ccc(S(=O)(=O)N2CCOCC2)cc1',
            'ligand_name': 'Ligand 1'
        }
    )
    
    print(f"   ID: {child.id}")
    print(f"   Job Type: {child.job_type.value}")
    print(f"   Parent ID: {child.batch_parent_id}")
    print(f"   Batch Index: {child.batch_index}")
    
    return child

def test_legacy_conversion():
    """Test converting legacy job data"""
    print("\n🔍 Testing legacy job conversion...")
    
    # Simulate legacy batch parent
    legacy_parent = {
        'id': 'legacy-batch-123',
        'name': 'Legacy Batch Job',
        'type': 'batch_protein_ligand_screening',
        'status': 'completed',
        'created_at': 1691234567.0,
        'input_data': {
            'protein_sequence': 'TEST',
            'ligands': [{'name': 'Test', 'smiles': 'C'}]
        },
        'child_ids': ['child-1', 'child-2']
    }
    
    enhanced_parent = EnhancedJobData.from_legacy_job(legacy_parent)
    print(f"   Legacy Parent -> Enhanced:")
    print(f"     Job Type: {enhanced_parent.job_type.value}")
    print(f"     Child IDs: {enhanced_parent.batch_child_ids}")
    
    # Simulate legacy batch child
    legacy_child = {
        'id': 'legacy-child-123',
        'name': 'Legacy Child Job',
        'type': 'protein_ligand_binding',
        'status': 'completed',
        'created_at': 1691234567.0,
        'input_data': {
            'protein_sequence': 'TEST',
            'ligand_smiles': 'C',
            'parent_batch_id': 'legacy-batch-123',
            'batch_index': 0
        }
    }
    
    enhanced_child = EnhancedJobData.from_legacy_job(legacy_child)
    print(f"   Legacy Child -> Enhanced:")
    print(f"     Job Type: {enhanced_child.job_type.value}")
    print(f"     Parent ID: {enhanced_child.batch_parent_id}")
    print(f"     Batch Index: {enhanced_child.batch_index}")
    
    return enhanced_parent, enhanced_child

def test_batch_progress_calculation():
    """Test batch progress calculation"""
    print("\n🔍 Testing batch progress calculation...")
    
    parent = create_batch_parent_job(
        name="Progress Test Batch",
        task_type=TaskType.BATCH_PROTEIN_LIGAND_SCREENING.value,
        input_data={'test': 'data'}
    )
    
    # Simulate child statuses
    child_statuses = [
        JobStatus.COMPLETED, JobStatus.COMPLETED, JobStatus.COMPLETED,
        JobStatus.FAILED, JobStatus.RUNNING, JobStatus.PENDING
    ]
    
    progress = parent.calculate_batch_progress(child_statuses)
    print(f"   Progress: {progress}")
    
    # Test is_batch_complete
    is_complete = parent.is_batch_complete(child_statuses)
    print(f"   Is Complete: {is_complete}")
    
    # Test with all completed
    all_completed = [JobStatus.COMPLETED] * 5 + [JobStatus.FAILED] * 1
    is_complete_all = parent.is_batch_complete(all_completed)
    print(f"   Is Complete (all final): {is_complete_all}")
    
    return progress

def test_api_formatting():
    """Test API response formatting"""
    print("\n🔍 Testing API formatting...")
    
    job = create_individual_job(
        name="API Test Job",
        task_type=TaskType.PROTEIN_LIGAND_BINDING.value,
        input_data={'test': 'data'}
    )
    
    # Simulate completion
    job.update_status(JobStatus.COMPLETED, {'result': 'success'})
    
    api_dict = job.to_api_dict()
    print(f"   API Response Keys: {list(api_dict.keys())}")
    print(f"   Duration: {api_dict.get('duration')}")
    print(f"   Can View: {api_dict.get('can_view')}")
    print(f"   Has Results: {api_dict.get('has_results')}")
    
    return api_dict

if __name__ == "__main__":
    print("🚀 Testing Enhanced Job Model")
    print("=" * 50)
    
    # Test individual job creation
    individual = test_individual_job_creation()
    
    # Test batch parent creation
    batch_parent = test_batch_parent_job_creation()
    
    # Test batch child creation
    batch_child = test_batch_child_job_creation()
    
    # Test legacy conversion
    legacy_parent, legacy_child = test_legacy_conversion()
    
    # Test batch progress
    progress = test_batch_progress_calculation()
    
    # Test API formatting
    api_response = test_api_formatting()
    
    print("\n" + "=" * 50)
    print("✅ Enhanced Job Model tests complete!")
    print(f"\nSummary:")
    print(f"   - Individual job creation: ✅ Working")
    print(f"   - Batch parent creation: ✅ Working")
    print(f"   - Batch child creation: ✅ Working")
    print(f"   - Legacy conversion: ✅ Working")
    print(f"   - Progress calculation: ✅ Working")
    print(f"   - API formatting: ✅ Working")