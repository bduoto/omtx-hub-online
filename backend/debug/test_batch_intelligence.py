#!/usr/bin/env python3
"""
Test Suite for Enhanced Batch Intelligence Features
Senior Principal Engineer Implementation

Tests the advanced batch intelligence methods added to EnhancedJobData
"""

import time
import asyncio
from typing import List

async def test_batch_intelligence():
    """Test advanced batch intelligence features"""
    print("🧠 Testing Enhanced Batch Intelligence Features")
    print("=" * 60)
    
    try:
        from models.enhanced_job_model import (
            EnhancedJobData, JobType, JobStatus, 
            create_batch_parent_job, create_batch_child_job
        )
        
        # Create a comprehensive batch scenario
        print("\n🔬 Creating test batch scenario...")
        
        # Create batch parent
        batch_parent = create_batch_parent_job(
            "Intelligence Test Batch",
            "batch_protein_ligand_screening", 
            {"protein_sequence": "MKLLVL", "total_ligands": 10}
        )
        batch_parent.batch_total_ligands = 10
        
        # Create diverse batch children with different scenarios
        children: List[EnhancedJobData] = []
        
        # Fast completed children (good performance)
        for i in range(3):
            child = create_batch_child_job(
                f"Fast Child {i+1}", batch_parent.id, i, 
                {"ligand_name": f"ligand_{i+1}", "ligand_smiles": "CCO"}
            )
            child.status = JobStatus.COMPLETED
            child.started_at = time.time() - 300  # 5 minutes ago
            child.completed_at = time.time() - 180  # 3 minutes ago (2 min execution)
            children.append(child)
        
        # Slow completed children (performance variance)
        for i in range(3, 5):
            child = create_batch_child_job(
                f"Slow Child {i+1}", batch_parent.id, i,
                {"ligand_name": f"ligand_{i+1}", "ligand_smiles": "CCC"}
            )
            child.status = JobStatus.COMPLETED
            child.started_at = time.time() - 600  # 10 minutes ago
            child.completed_at = time.time() - 120  # 2 minutes ago (8 min execution)
            children.append(child)
        
        # Failed children
        for i in range(5, 7):
            child = create_batch_child_job(
                f"Failed Child {i+1}", batch_parent.id, i,
                {"ligand_name": f"ligand_{i+1}", "ligand_smiles": "INVALID"}
            )
            child.status = JobStatus.FAILED
            child.started_at = time.time() - 240
            child.completed_at = time.time() - 180
            child.error_message = "Invalid SMILES"
            children.append(child)
        
        # Currently running children
        for i in range(7, 9):
            child = create_batch_child_job(
                f"Running Child {i+1}", batch_parent.id, i,
                {"ligand_name": f"ligand_{i+1}", "ligand_smiles": "CCCC"}
            )
            child.status = JobStatus.RUNNING
            child.started_at = time.time() - 120  # 2 minutes ago
            children.append(child)
        
        # Pending child
        child = create_batch_child_job(
            "Pending Child 10", batch_parent.id, 9,
            {"ligand_name": "ligand_10", "ligand_smiles": "CCCCC"}
        )
        child.status = JobStatus.PENDING
        children.append(child)
        
        print(f"   Created batch with {len(children)} children")
        print(f"   Completed: {len([c for c in children if c.status == JobStatus.COMPLETED])}")
        print(f"   Failed: {len([c for c in children if c.status == JobStatus.FAILED])}")
        print(f"   Running: {len([c for c in children if c.status == JobStatus.RUNNING])}")
        print(f"   Pending: {len([c for c in children if c.status == JobStatus.PENDING])}")
        
        # Test 1: Basic progress update
        print("\n📊 Testing batch progress intelligence...")
        
        child_statuses = [child.status for child in children]
        batch_parent.update_batch_progress(child_statuses, children)
        
        assert batch_parent.batch_progress is not None, "Batch progress not calculated"
        assert batch_parent.batch_estimated_completion is not None, "Completion time not estimated"
        assert batch_parent.batch_completion_rate is not None, "Completion rate not calculated"
        assert batch_parent.batch_metadata is not None, "Batch metadata not populated"
        
        print("   ✅ Progress intelligence calculated successfully")
        print(f"   Progress: {batch_parent.batch_progress['completed']}/{batch_parent.batch_progress['total']}")
        print(f"   Estimated completion: {batch_parent.batch_estimated_completion:.1f} seconds")
        print(f"   Completion rate: {batch_parent.batch_completion_rate:.2%}")
        
        # Test 2: Performance insights
        print("\n⚡ Testing performance insights...")
        
        metadata = batch_parent.batch_metadata
        assert 'avg_execution_time' in metadata, "Average execution time not calculated"
        assert 'performance_variance' in metadata, "Performance variance not calculated"
        assert 'resource_efficiency' in metadata, "Resource efficiency not calculated"
        
        print("   ✅ Performance metrics calculated")
        print(f"   Avg execution time: {metadata['avg_execution_time']:.1f} seconds")
        print(f"   Performance variance: {metadata['performance_variance']:.1f} seconds")
        print(f"   Resource efficiency: {metadata['resource_efficiency']:.2%}")
        print(f"   Completion trend: {metadata['completion_trend']}")
        
        # Test 3: Batch insights
        print("\n🎯 Testing comprehensive batch insights...")
        
        insights = batch_parent.get_batch_insights()
        required_insight_fields = [
            'batch_id', 'batch_name', 'current_progress', 
            'estimated_completion_time', 'batch_health', 'performance_rating'
        ]
        
        for field in required_insight_fields:
            assert field in insights, f"Missing insight field: {field}"
        
        print("   ✅ Comprehensive insights generated")
        print(f"   Batch health: {insights['batch_health']}")
        print(f"   Performance rating: {insights['performance_rating']}")
        print(f"   Recommendations: {len(insights.get('recommendations', []))} items")
        
        if insights.get('recommendations'):
            print("   Recommendations:")
            for rec in insights['recommendations'][:3]:  # Show first 3
                print(f"     • {rec}")
        
        # Test 4: Dynamic completion estimation
        print("\n⏱️ Testing dynamic completion estimation...")
        
        # Simulate more children completing
        for child in children[7:9]:  # Mark running children as completed
            child.status = JobStatus.COMPLETED
            child.completed_at = time.time()
        
        # Recalculate with new status
        child_statuses = [child.status for child in children]
        batch_parent.update_batch_progress(child_statuses, children)
        
        new_estimate = batch_parent.batch_estimated_completion
        print(f"   ✅ Dynamic estimation updated: {new_estimate:.1f} seconds")
        print(f"   Progress now: {batch_parent.batch_progress['completed']}/{batch_parent.batch_progress['total']}")
        
        # Test 5: Completion scenario
        print("\n🎉 Testing batch completion scenario...")
        
        # Complete the remaining pending child
        children[-1].status = JobStatus.COMPLETED
        children[-1].started_at = time.time() - 60
        children[-1].completed_at = time.time()
        
        child_statuses = [child.status for child in children]
        batch_parent.update_batch_progress(child_statuses, children)
        
        final_estimate = batch_parent.batch_estimated_completion
        final_insights = batch_parent.get_batch_insights()
        
        print(f"   ✅ Final completion estimate: {final_estimate} seconds (should be 0.0)")
        print(f"   Final batch health: {final_insights['batch_health']}")
        print(f"   Final performance rating: {final_insights['performance_rating']}")
        
        # Validation checks
        assert final_estimate == 0.0, "Completed batch should have 0 estimated time"
        assert batch_parent.batch_progress['completed'] + batch_parent.batch_progress['failed'] == batch_parent.batch_progress['total'], "Batch should be complete"
        
        print("\n" + "=" * 60)
        print("🎉 ALL BATCH INTELLIGENCE TESTS PASSED!")
        print("✅ Advanced batch intelligence is working correctly")
        print("✅ Performance insights are being calculated") 
        print("✅ Dynamic completion estimation is functional")
        print("✅ Comprehensive batch health assessment is operational")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Batch intelligence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_batch_health_assessment():
    """Test batch health assessment logic"""
    print("\n🏥 Testing Batch Health Assessment...")
    
    try:
        from models.enhanced_job_model import create_batch_parent_job, JobStatus
        
        # Test different health scenarios
        scenarios = [
            {
                'name': 'Excellent Batch',
                'statuses': [JobStatus.COMPLETED] * 9 + [JobStatus.FAILED] * 1,  # 90% success, 10% failure
                'expected_health': 'excellent'
            },
            {
                'name': 'Unhealthy Batch', 
                'statuses': [JobStatus.COMPLETED] * 6 + [JobStatus.FAILED] * 4,  # 60% success, 40% failure
                'expected_health': 'unhealthy'
            },
            {
                'name': 'Concerning Batch',
                'statuses': [JobStatus.COMPLETED] * 2 + [JobStatus.FAILED] * 2 + [JobStatus.RUNNING] * 6,  # 20% complete, 20% failed
                'expected_health': 'concerning'
            },
            {
                'name': 'Healthy Batch',
                'statuses': [JobStatus.COMPLETED] * 7 + [JobStatus.FAILED] * 1 + [JobStatus.RUNNING] * 2,  # 70% complete, 10% failed
                'expected_health': 'healthy'
            }
        ]
        
        for scenario in scenarios:
            batch = create_batch_parent_job(scenario['name'], "batch_protein_ligand_screening", {})
            progress = batch.calculate_batch_progress(scenario['statuses'])
            health = batch._assess_batch_health(progress)
            
            print(f"   {scenario['name']}: {health} (expected: {scenario['expected_health']})")
            assert health == scenario['expected_health'], f"Health assessment mismatch for {scenario['name']}"
        
        print("   ✅ All health assessment scenarios passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Health assessment test failed: {e}")
        return False

async def main():
    """Run all batch intelligence tests"""
    print("🧠 ENHANCED BATCH INTELLIGENCE TEST SUITE")
    print("Senior Principal Engineer Implementation")
    print("=" * 60)
    
    tests = [
        ("Core Intelligence Features", test_batch_intelligence),
        ("Health Assessment Logic", test_batch_health_assessment)
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
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed}/{len(tests)} test categories passed")
    
    if passed == len(tests):
        print("🎉 ENHANCED BATCH INTELLIGENCE READY FOR PRODUCTION!")
        return 0
    else:
        print("⚠️ Some tests failed - review implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)