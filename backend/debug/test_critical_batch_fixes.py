#!/usr/bin/env python3
"""
Test Critical Batch Parent Update Fixes
Senior Principal Engineer Implementation

Tests the critical fixes for modal monitor batch parent updates
and child job creation consistency.
"""

import asyncio
import time
import uuid
from unittest.mock import MagicMock, patch

async def test_modal_monitor_batch_parent_updates():
    """Test critical batch parent update functionality in modal monitor"""
    print("🔧 Testing Modal Monitor Batch Parent Updates")
    print("=" * 60)
    
    try:
        from services.modal_monitor import modal_monitor
        from models.enhanced_job_model import create_batch_parent_job, create_batch_child_job, JobStatus
        
        # Create test batch scenario
        print("\n🔬 Creating test batch parent-child scenario...")
        
        # Create batch parent
        batch_parent = create_batch_parent_job(
            "Test Batch Parent",
            "batch_protein_ligand_screening",
            {"protein_sequence": "MKLLVL", "ligands": [{"smiles": "CCO"}, {"smiles": "CCC"}]}
        )
        batch_parent.batch_total_ligands = 2
        
        # Create batch children
        child1 = create_batch_child_job("Child 1", batch_parent.id, 0, {"ligand_smiles": "CCO"})
        child2 = create_batch_child_job("Child 2", batch_parent.id, 1, {"ligand_smiles": "CCC"})
        
        print(f"   Created batch parent: {batch_parent.id}")
        print(f"   Created child 1: {child1.id}")
        print(f"   Created child 2: {child2.id}")
        
        # Test 1: Mock the unified_job_manager and unified_job_storage
        print("\n📊 Testing batch parent update method...")
        
        # Mock data that the monitor would encounter
        mock_child_job_data = {
            'id': child1.id,
            'batch_parent_id': batch_parent.id,
            'status': 'completed'
        }
        
        mock_parent_job_data = batch_parent.to_firestore_dict()
        
        mock_children_data = [child1, child2]  # Child1 completed, Child2 pending
        child2.status = JobStatus.PENDING  # Still pending
        
        # Test the batch parent update method directly
        with patch('services.modal_monitor.unified_job_manager') as mock_job_manager, \
             patch('services.unified_job_storage.unified_job_storage') as mock_storage:
            
            # Configure mocks
            mock_job_manager.get_job.side_effect = lambda job_id: (
                mock_child_job_data if job_id == child1.id else mock_parent_job_data
            )
            mock_storage.get_batch_children.return_value = mock_children_data
            
            # Call the critical fix method
            await modal_monitor._update_batch_parent_progress_if_needed(child1.id)
            
            # Verify the parent update was called
            assert mock_job_manager.update_job_status.called, "Parent job status should have been updated"
            
            # Get the update call arguments
            call_args = mock_job_manager.update_job_status.call_args
            updated_parent_id = call_args[0][0]
            updated_status = call_args[0][1]
            updated_data = call_args[0][2]
            
            assert updated_parent_id == batch_parent.id, "Correct parent ID should be updated"
            assert updated_status == 'running', "Parent should still be running (1 of 2 children complete)"
            assert 'batch_progress' in updated_data, "Batch progress should be included in update"
            
            print("   ✅ Batch parent update method works correctly")
            print(f"   Updated parent {updated_parent_id} with status: {updated_status}")
            print(f"   Progress data included: {list(updated_data.keys())}")
        
        # Test 2: Test batch completion scenario
        print("\n🎉 Testing batch completion scenario...")
        
        # Both children are now completed
        child2.status = JobStatus.COMPLETED
        mock_children_completed = [child1, child2]
        
        with patch('services.modal_monitor.unified_job_manager') as mock_job_manager, \
             patch('services.unified_job_storage.unified_job_storage') as mock_storage:
            
            mock_job_manager.get_job.side_effect = lambda job_id: (
                mock_child_job_data if job_id == child2.id else mock_parent_job_data
            )
            mock_storage.get_batch_children.return_value = mock_children_completed
            
            # Simulate child 2 completing
            await modal_monitor._update_batch_parent_progress_if_needed(child2.id)
            
            # Verify batch completion
            call_args = mock_job_manager.update_job_status.call_args
            updated_status = call_args[0][1]
            updated_data = call_args[0][2]
            
            assert updated_status == 'completed', "Batch parent should be completed when all children complete"
            assert 'completed_at' in updated_data, "Completion timestamp should be set"
            assert updated_data['completed_at'] is not None, "Completion timestamp should have value"
            
            print("   ✅ Batch completion logic works correctly")
            print(f"   Final status: {updated_status}")
            print(f"   Completion timestamp set: {'completed_at' in updated_data}")
        
        # Test 3: Test error handling (non-batch job)
        print("\n🛡️ Testing error handling for non-batch jobs...")
        
        # Create individual job (not part of batch)
        individual_job_data = {
            'id': str(uuid.uuid4()),
            'status': 'completed'
            # No batch_parent_id - this is an individual job
        }
        
        with patch('services.modal_monitor.unified_job_manager') as mock_job_manager:
            mock_job_manager.get_job.return_value = individual_job_data
            
            # Should handle gracefully without error
            await modal_monitor._update_batch_parent_progress_if_needed(individual_job_data['id'])
            
            # Should not attempt to update any parent
            assert not mock_job_manager.update_job_status.called, "Should not update anything for individual jobs"
            
            print("   ✅ Non-batch jobs handled correctly (no parent updates)")
        
        # Test 4: Test legacy format support
        print("\n🔄 Testing legacy format support...")
        
        # Legacy child job format (batch_parent_id in input_data)
        legacy_child_data = {
            'id': str(uuid.uuid4()),
            'status': 'completed',
            'input_data': {
                'parent_batch_id': batch_parent.id  # Legacy format
            }
        }
        
        with patch('services.modal_monitor.unified_job_manager') as mock_job_manager, \
             patch('services.unified_job_storage.unified_job_storage') as mock_storage:
            
            mock_job_manager.get_job.side_effect = lambda job_id: (
                legacy_child_data if job_id == legacy_child_data['id'] else mock_parent_job_data
            )
            mock_storage.get_batch_children.return_value = [child1]  # One child
            
            # Should handle legacy format
            await modal_monitor._update_batch_parent_progress_if_needed(legacy_child_data['id'])
            
            # Should update parent (found via legacy format)
            assert mock_job_manager.update_job_status.called, "Should update parent even for legacy format"
            
            print("   ✅ Legacy format support works correctly")
        
        print("\n" + "=" * 60)
        print("🎉 ALL CRITICAL BATCH FIXES TESTED SUCCESSFULLY!")
        print("✅ Modal monitor batch parent updates working")
        print("✅ Batch completion detection working")
        print("✅ Error handling robust")
        print("✅ Legacy format support maintained")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Critical batch fixes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enhanced_job_model_consistency():
    """Test that enhanced job model creates consistent batch relationships"""
    print("\n🔧 Testing Enhanced Job Model Batch Consistency")
    print("=" * 60)
    
    try:
        from models.enhanced_job_model import (
            create_batch_parent_job, create_batch_child_job, JobType
        )
        
        # Test 1: Verify batch parent creation
        print("\n📊 Testing batch parent creation consistency...")
        
        batch_parent = create_batch_parent_job(
            "Consistency Test Batch",
            "batch_protein_ligand_screening",
            {"protein_sequence": "MKLLVL"}
        )
        
        # Verify required fields
        assert batch_parent.job_type == JobType.BATCH_PARENT, "Job type should be BATCH_PARENT"
        assert batch_parent.batch_child_ids is not None, "Batch child IDs list should be initialized"
        assert isinstance(batch_parent.batch_child_ids, list), "Batch child IDs should be a list"
        assert len(batch_parent.batch_child_ids) == 0, "Initial child IDs list should be empty"
        
        print("   ✅ Batch parent creation consistent")
        print(f"   Job type: {batch_parent.job_type.value}")
        print(f"   Child IDs initialized: {batch_parent.batch_child_ids is not None}")
        
        # Test 2: Verify batch child creation
        print("\n👶 Testing batch child creation consistency...")
        
        child_job = create_batch_child_job(
            "Child Consistency Test",
            batch_parent.id,
            0,
            {"ligand_smiles": "CCO"}
        )
        
        # Verify required fields
        assert child_job.job_type == JobType.BATCH_CHILD, "Job type should be BATCH_CHILD"
        assert child_job.batch_parent_id == batch_parent.id, "Parent ID should be set correctly"
        assert child_job.batch_index == 0, "Batch index should be set correctly"
        
        print("   ✅ Batch child creation consistent")
        print(f"   Job type: {child_job.job_type.value}")
        print(f"   Parent ID: {child_job.batch_parent_id}")
        print(f"   Batch index: {child_job.batch_index}")
        
        # Test 3: Verify parent-child relationship
        print("\n🔗 Testing parent-child relationship...")
        
        # Add child to parent
        batch_parent.add_child_job(child_job.id)
        
        # Verify relationship
        assert child_job.id in batch_parent.batch_child_ids, "Child ID should be in parent's child list"
        assert len(batch_parent.batch_child_ids) == 1, "Parent should have exactly one child"
        
        print("   ✅ Parent-child relationship consistent")
        print(f"   Parent has {len(batch_parent.batch_child_ids)} children")
        print(f"   Child {child_job.id} in parent's list: {child_job.id in batch_parent.batch_child_ids}")
        
        # Test 4: Verify new format validation
        print("\n✅ Testing new format validation...")
        
        # Convert to firestore format and back
        parent_firestore = batch_parent.to_firestore_dict()
        child_firestore = child_job.to_firestore_dict()
        
        # Verify required fields are present
        assert 'job_type' in parent_firestore, "Parent firestore data should have job_type"
        assert 'job_type' in child_firestore, "Child firestore data should have job_type"
        
        # Verify from_job_data accepts the data
        from models.enhanced_job_model import EnhancedJobData
        
        reconstructed_parent = EnhancedJobData.from_job_data(parent_firestore)
        reconstructed_child = EnhancedJobData.from_job_data(child_firestore)
        
        assert reconstructed_parent is not None, "Parent should be reconstructable from firestore data"
        assert reconstructed_child is not None, "Child should be reconstructable from firestore data"
        
        print("   ✅ New format validation consistent")
        print(f"   Parent reconstructable: {reconstructed_parent is not None}")
        print(f"   Child reconstructable: {reconstructed_child is not None}")
        
        print("\n" + "=" * 60)
        print("🎉 ENHANCED JOB MODEL CONSISTENCY VERIFIED!")
        print("✅ Batch parent creation consistent")
        print("✅ Batch child creation consistent") 
        print("✅ Parent-child relationships working")
        print("✅ New format validation robust")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Job model consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all critical batch fix tests"""
    print("🔧 CRITICAL BATCH FIXES TEST SUITE")
    print("Senior Principal Engineer Implementation")
    print("=" * 70)
    
    tests = [
        ("Modal Monitor Batch Parent Updates", test_modal_monitor_batch_parent_updates),
        ("Enhanced Job Model Consistency", test_enhanced_job_model_consistency)
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
    print(f"📊 RESULTS: {passed}/{len(tests)} critical fix categories passed")
    
    if passed == len(tests):
        print("🎉 CRITICAL BATCH FIXES READY FOR PRODUCTION!")
        print("🚀 System ready for Phase 2: UnifiedBatchProcessor")
        return 0
    else:
        print("⚠️ Some critical fixes failed - review implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)