#!/usr/bin/env python3
"""
Comprehensive Test Suite for UnifiedBatchProcessor
Senior Principal Engineer Implementation

Tests the enterprise-grade unified batch processing engine that consolidates
all 4 competing batch systems into a single intelligent solution.
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

async def test_unified_batch_processor_architecture():
    """Test the core UnifiedBatchProcessor architecture"""
    print("🏗️ Testing UnifiedBatchProcessor Architecture")
    print("=" * 60)
    
    try:
        from services.unified_batch_processor import (
            UnifiedBatchProcessor, BatchSubmissionRequest, BatchConfiguration,
            BatchPriority, BatchSchedulingStrategy
        )
        
        # Test 1: Processor initialization
        print("\n🚀 Testing processor initialization...")
        
        processor = UnifiedBatchProcessor()
        assert hasattr(processor, 'active_batches'), "Should have active_batches tracking"
        assert hasattr(processor, 'execution_plans'), "Should have execution_plans"
        assert hasattr(processor, 'performance_metrics'), "Should have performance_metrics"
        assert hasattr(processor, 'resource_monitor'), "Should have resource_monitor"
        
        print("   ✅ UnifiedBatchProcessor initialized correctly")
        print(f"   Active batches: {len(processor.active_batches)}")
        print(f"   Default config: {processor.default_config.scheduling_strategy.value}")
        
        # Test 2: Configuration classes
        print("\n⚙️ Testing configuration classes...")
        
        config = BatchConfiguration(
            priority=BatchPriority.HIGH,
            scheduling_strategy=BatchSchedulingStrategy.RESOURCE_AWARE,
            max_concurrent_jobs=10,
            retry_failed_jobs=True
        )
        
        assert config.priority == BatchPriority.HIGH, "Priority should be HIGH"
        assert config.scheduling_strategy == BatchSchedulingStrategy.RESOURCE_AWARE, "Strategy should be RESOURCE_AWARE"
        assert config.max_concurrent_jobs == 10, "Max concurrent should be 10"
        assert config.retry_failed_jobs == True, "Retry should be enabled"
        
        print("   ✅ Configuration classes working correctly")
        print(f"   Priority: {config.priority.value}")
        print(f"   Strategy: {config.scheduling_strategy.value}")
        print(f"   Max concurrent: {config.max_concurrent_jobs}")
        
        # Test 3: Batch submission request
        print("\n📝 Testing batch submission request...")
        
        test_ligands = [
            {'name': 'Aspirin', 'smiles': 'CC(=O)OC1=CC=CC=C1C(=O)O'},
            {'name': 'Caffeine', 'smiles': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C'},
            {'name': 'Acetaminophen', 'smiles': 'CC(=O)NC1=CC=C(C=C1)O'}
        ]
        
        request = BatchSubmissionRequest(
            job_name="Test Unified Batch",
            protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFCSVDNCASDNKQGPCALAHPKEAKPPRRRPGGGSLALSLGGGAATAGSGSGSGSAALAALPAAFGGAAKKLLVVALAVLSASAAA",
            protein_name="Test Protein",
            ligands=test_ligands,
            user_id="test_user",
            configuration=config
        )
        
        assert request.job_name == "Test Unified Batch", "Job name should match"
        assert len(request.ligands) == 3, "Should have 3 ligands"
        assert request.configuration == config, "Configuration should match"
        
        print("   ✅ Batch submission request created correctly")
        print(f"   Job name: {request.job_name}")
        print(f"   Ligands: {len(request.ligands)}")
        print(f"   Protein length: {len(request.protein_sequence)} AA")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Architecture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_batch_validation_and_planning():
    """Test batch request validation and execution planning"""
    print("\n🔍 Testing Batch Validation and Planning")
    print("=" * 60)
    
    try:
        from services.unified_batch_processor import (
            UnifiedBatchProcessor, BatchSubmissionRequest, BatchConfiguration
        )
        
        processor = UnifiedBatchProcessor()
        
        # Test 1: Valid request validation
        print("\n✅ Testing valid request validation...")
        
        valid_request = BatchSubmissionRequest(
            job_name="Valid Batch Test",
            protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFCSVDNCASDNKQGPCALAHPKEAKPPRRRPGGGSLALSLGGGAATAGSGSGSGSAALAALPAAFGGAAKKLLVVALAVLSASAAA",
            protein_name="Valid Protein",
            ligands=[
                {'name': 'Test Ligand 1', 'smiles': 'CCO'},
                {'name': 'Test Ligand 2', 'smiles': 'CCC'}
            ]
        )
        
        validation_result = await processor._validate_batch_request(valid_request)
        assert validation_result['valid'] == True, "Valid request should pass validation"
        
        print("   ✅ Valid request passed validation")
        
        # Test 2: Invalid request validation
        print("\n❌ Testing invalid request validation...")
        
        invalid_requests = [
            # Empty job name
            BatchSubmissionRequest(
                job_name="",
                protein_sequence="MKLLVVLALVL",
                protein_name="Test",
                ligands=[{'smiles': 'CCO'}]
            ),
            # Short protein sequence
            BatchSubmissionRequest(
                job_name="Test",
                protein_sequence="MKL",  # Too short
                protein_name="Test",
                ligands=[{'smiles': 'CCO'}]
            ),
            # No ligands
            BatchSubmissionRequest(
                job_name="Test",
                protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFC",
                protein_name="Test",
                ligands=[]  # Empty ligands
            ),
            # Invalid ligand format
            BatchSubmissionRequest(
                job_name="Test",
                protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFC",
                protein_name="Test",
                ligands=[{'name': 'Test'}]  # Missing smiles
            )
        ]
        
        expected_errors = [
            "Job name is required",
            "Protein sequence must be at least 10 amino acids", 
            "At least one ligand is required",
            "Ligand 1 missing SMILES string"
        ]
        
        for i, (invalid_request, expected_error) in enumerate(zip(invalid_requests, expected_errors)):
            validation_result = await processor._validate_batch_request(invalid_request)
            assert validation_result['valid'] == False, f"Invalid request {i+1} should fail validation"
            print(f"   ✅ Invalid request {i+1}: {validation_result['error']}")
        
        # Test 3: Execution plan creation
        print("\n📊 Testing execution plan creation...")
        
        execution_plan = await processor._create_execution_plan(valid_request)
        
        assert execution_plan.batch_id is not None, "Plan should have batch_id"
        assert execution_plan.total_jobs == len(valid_request.ligands), "Total jobs should match ligands"
        assert execution_plan.estimated_duration > 0, "Should have positive estimated duration"
        assert len(execution_plan.scheduling_timeline) > 0, "Should have scheduling timeline"
        assert execution_plan.resource_requirements is not None, "Should have resource requirements"
        
        print("   ✅ Execution plan created successfully")
        print(f"   Total jobs: {execution_plan.total_jobs}")
        print(f"   Estimated duration: {execution_plan.estimated_duration:.1f} seconds")
        print(f"   Resource requirements: {execution_plan.resource_requirements}")
        print(f"   Risk score: {execution_plan.risk_assessment['risk_score']:.2f}")
        print(f"   Recommendations: {len(execution_plan.optimization_recommendations)} items")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Validation and planning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_batch_job_creation():
    """Test batch parent and child job creation"""
    print("\n👨‍👩‍👧‍👦 Testing Batch Job Creation")
    print("=" * 60)
    
    try:
        from services.unified_batch_processor import (
            UnifiedBatchProcessor, BatchSubmissionRequest
        )
        from models.enhanced_job_model import JobType, JobStatus
        
        processor = UnifiedBatchProcessor()
        
        # Create test request
        request = BatchSubmissionRequest(
            job_name="Job Creation Test",
            protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFCSVDNCASDNKQGPCALAHPKEAKPPRRRPGGGSLALSLGGGAATAGSGSGSGSAALAALPAAFGGAAKKLLVVALAVLSASAAA",
            protein_name="Test Protein",
            ligands=[
                {'name': 'Ligand A', 'smiles': 'CCO'},
                {'name': 'Ligand B', 'smiles': 'CCC'},
                {'name': 'Ligand C', 'smiles': 'CCCC'}
            ]
        )
        
        # Create execution plan
        execution_plan = await processor._create_execution_plan(request)
        
        # Test batch parent creation (with mocked database calls)
        print("\n👨 Testing batch parent creation...")
        
        with patch('database.unified_job_manager.unified_job_manager') as mock_job_manager:
            mock_job_manager.create_job_async = AsyncMock()
            
            batch_parent = await processor._create_batch_parent(request, execution_plan)
            
            assert batch_parent.job_type == JobType.BATCH_PARENT, "Should be batch parent type"
            assert batch_parent.name == request.job_name, "Name should match request"
            assert batch_parent.batch_total_ligands == len(request.ligands), "Should track total ligands"
            assert batch_parent.batch_estimated_completion is not None, "Should have completion estimate"
            assert batch_parent.batch_metadata is not None, "Should have batch metadata"
            assert batch_parent.batch_metadata['created_by_unified_processor'] == True, "Should be marked as unified"
            
            print("   ✅ Batch parent created successfully")
            print(f"   Batch ID: {batch_parent.id}")
            print(f"   Job type: {batch_parent.job_type.value}")
            print(f"   Total ligands: {batch_parent.batch_total_ligands}")
            print(f"   Metadata keys: {list(batch_parent.batch_metadata.keys())}")
        
        # Test child job creation (with mocked database calls)
        print("\n👧‍👦 Testing child job creation...")
        
        with patch('database.unified_job_manager.unified_job_manager') as mock_job_manager, \
             patch.object(processor, '_batch_create_jobs') as mock_batch_create:
            
            mock_batch_create.return_value = None
            
            child_jobs = await processor._create_child_jobs(batch_parent, request, execution_plan)
            
            assert len(child_jobs) == len(request.ligands), "Should create one child per ligand"
            
            for i, child_job in enumerate(child_jobs):
                assert child_job.job_type == JobType.BATCH_CHILD, f"Child {i} should be batch child type"
                assert child_job.batch_parent_id == batch_parent.id, f"Child {i} should have correct parent ID"
                assert child_job.batch_index == i, f"Child {i} should have correct batch index"
                assert request.ligands[i]['smiles'] in child_job.input_data['ligand_smiles'], f"Child {i} should have correct ligand"
            
            # Check parent-child relationship
            assert len(batch_parent.batch_child_ids) == len(request.ligands), "Parent should track all children"
            for child_job in child_jobs:
                assert child_job.id in batch_parent.batch_child_ids, f"Parent should contain child {child_job.id}"
            
            print("   ✅ Child jobs created successfully")
            print(f"   Created {len(child_jobs)} child jobs")
            print(f"   Parent tracks {len(batch_parent.batch_child_ids)} children")
            
            # Verify child job names and metadata
            for i, child_job in enumerate(child_jobs):
                ligand_name = request.ligands[i].get('name', f'Ligand_{i+1}')
                expected_name = f"{request.job_name} - {ligand_name}"
                assert child_job.name == expected_name, f"Child {i} should have correct name"
                print(f"   Child {i+1}: {child_job.name}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Batch job creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_unified_batch_submission():
    """Test complete batch submission process"""
    print("\n🚀 Testing Unified Batch Submission")
    print("=" * 60)
    
    try:
        from services.unified_batch_processor import (
            UnifiedBatchProcessor, BatchSubmissionRequest, BatchConfiguration,
            BatchPriority, BatchSchedulingStrategy
        )
        
        processor = UnifiedBatchProcessor()
        
        # Create comprehensive test request
        print("\n📝 Creating comprehensive batch submission...")
        
        config = BatchConfiguration(
            priority=BatchPriority.HIGH,
            scheduling_strategy=BatchSchedulingStrategy.ADAPTIVE,
            max_concurrent_jobs=3,
            retry_failed_jobs=True,
            enable_predictive_completion=True
        )
        
        request = BatchSubmissionRequest(
            job_name="Unified Submission Test",
            protein_sequence="MKLLVVLALVLGFLLFSASAAQQEGEVAVRFCSVDNCASDNKQGPCALAHPKEAKPPRRRPGGGSLALSLGGGAATAGSGSGSGSAALAALPAAFGGAAKKLLVVALAVLSASAAA",
            protein_name="Target Protein",
            ligands=[
                {'name': 'Compound Alpha', 'smiles': 'CC(=O)OC1=CC=CC=C1C(=O)O'},
                {'name': 'Compound Beta', 'smiles': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C'},
                {'name': 'Compound Gamma', 'smiles': 'CC(=O)NC1=CC=C(C=C1)O'},
                {'name': 'Compound Delta', 'smiles': 'CCO'}
            ],
            configuration=config,
            metadata={'experiment': 'unified_processor_test', 'version': '2.0'}
        )
        
        print(f"   Job name: {request.job_name}")
        print(f"   Ligands: {len(request.ligands)}")
        print(f"   Configuration: {config.scheduling_strategy.value}")
        
        # Mock all external dependencies
        print("\n🔧 Mocking external dependencies...")
        
        with patch('database.unified_job_manager.unified_job_manager') as mock_job_manager, \
             patch('services.gcp_storage_service.gcp_storage_service') as mock_storage, \
             patch('tasks.task_handlers.task_handler_registry') as mock_task_registry:
            
            # Configure mocks
            mock_job_manager.create_job_async = AsyncMock()
            mock_job_manager.update_job_async = AsyncMock()
            mock_storage.store_file_content = AsyncMock()
            mock_task_registry.process_task = AsyncMock(return_value={
                'status': 'running',
                'modal_call_id': f'call_{uuid.uuid4()}'
            })
            
            # Execute batch submission
            print("\n🎯 Executing unified batch submission...")
            
            result = await processor.submit_batch(request)
            
            # Verify submission result
            assert result['success'] == True, "Submission should succeed"
            assert 'batch_id' in result, "Should return batch_id"
            assert 'batch_parent' in result, "Should return batch_parent"
            assert result['total_jobs'] == len(request.ligands), "Should match ligand count"
            assert 'execution_plan' in result, "Should include execution_plan"
            assert 'execution_details' in result, "Should include execution_details"
            
            batch_id = result['batch_id']
            batch_parent = result['batch_parent']
            execution_plan = result['execution_plan']
            
            print("   ✅ Unified batch submission successful!")
            print(f"   Batch ID: {batch_id}")
            print(f"   Total jobs: {result['total_jobs']}")
            print(f"   Estimated duration: {execution_plan['estimated_duration']:.1f}s")
            print(f"   Scheduling strategy: {execution_plan['scheduling_strategy']}")
            print(f"   Started jobs: {result['execution_details']['started_jobs']}")
            
            # Verify processor state
            assert batch_id in processor.active_batches, "Batch should be tracked in active batches"
            assert batch_id in processor.execution_plans, "Execution plan should be stored"
            
            # Verify method calls
            assert mock_job_manager.create_job_async.called, "Should create jobs in database"
            assert mock_storage.store_file_content.called, "Should initialize batch storage"
            assert mock_task_registry.process_task.called, "Should start processing jobs"
            
            print(f"   Active batches: {len(processor.active_batches)}")
            print(f"   Execution plans: {len(processor.execution_plans)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Unified batch submission test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_batch_status_and_intelligence():
    """Test batch status retrieval and intelligence features"""
    print("\n📊 Testing Batch Status and Intelligence")
    print("=" * 60)
    
    try:
        from services.unified_batch_processor import UnifiedBatchProcessor
        from models.enhanced_job_model import create_batch_parent_job, create_batch_child_job, JobStatus
        
        processor = UnifiedBatchProcessor()
        
        # Create test batch scenario
        print("\n🔬 Creating test batch scenario...")
        
        batch_parent = create_batch_parent_job(
            "Intelligence Test Batch",
            "batch_protein_ligand_screening",
            {"protein_sequence": "MKLLVL", "total_ligands": 4}
        )
        batch_parent.batch_total_ligands = 4
        
        # Create children with different statuses
        child_jobs = [
            create_batch_child_job("Child 1", batch_parent.id, 0, {"ligand_smiles": "CCO"}),
            create_batch_child_job("Child 2", batch_parent.id, 1, {"ligand_smiles": "CCC"}),  
            create_batch_child_job("Child 3", batch_parent.id, 2, {"ligand_smiles": "CCCC"}),
            create_batch_child_job("Child 4", batch_parent.id, 3, {"ligand_smiles": "CCCCC"})
        ]
        
        # Set diverse statuses for testing
        child_jobs[0].status = JobStatus.COMPLETED
        child_jobs[0].completed_at = time.time()
        child_jobs[1].status = JobStatus.COMPLETED  
        child_jobs[1].completed_at = time.time()
        child_jobs[2].status = JobStatus.RUNNING
        child_jobs[2].started_at = time.time() - 60
        child_jobs[3].status = JobStatus.FAILED
        child_jobs[3].completed_at = time.time()
        child_jobs[3].error_message = "Test failure"
        
        # Add children to parent
        for child in child_jobs:
            batch_parent.add_child_job(child.id)
        
        # Test batch status retrieval with mocks
        print("\n📈 Testing batch status retrieval...")
        
        with patch('database.unified_job_manager.unified_job_manager') as mock_job_manager:
            # Mock job manager responses
            mock_job_manager.get_job_async = AsyncMock()
            
            def mock_get_job(job_id):
                if job_id == batch_parent.id:
                    return batch_parent.to_firestore_dict()
                for child in child_jobs:
                    if job_id == child.id:
                        return child.to_firestore_dict()
                return None
            
            mock_job_manager.get_job_async.side_effect = mock_get_job
            
            # Get batch status
            status_result = await processor.get_batch_status(batch_parent.id)
            
            # Verify status result structure
            assert 'batch_id' in status_result, "Should include batch_id"
            assert 'batch_parent' in status_result, "Should include batch_parent"
            assert 'child_jobs' in status_result, "Should include child_jobs"
            assert 'progress' in status_result, "Should include progress"
            assert 'insights' in status_result, "Should include insights"
            
            # Verify progress calculations
            progress = status_result['progress']
            assert progress['total'] == 4, "Should track 4 total jobs"
            assert progress['completed'] == 2, "Should show 2 completed"
            assert progress['running'] == 1, "Should show 1 running"
            assert progress['failed'] == 1, "Should show 1 failed"
            assert progress['progress_percentage'] == 75.0, "Should be 75% complete (3/4 finished)"
            
            # Verify intelligence insights
            insights = status_result['insights']
            assert 'batch_health' in insights, "Should include batch health"
            assert 'performance_rating' in insights, "Should include performance rating" 
            assert 'current_progress' in insights, "Should include current progress"
            
            print("   ✅ Batch status retrieval successful")
            print(f"   Progress: {progress['completed']}/{progress['total']} completed")
            print(f"   Progress percentage: {progress['progress_percentage']:.1f}%")
            print(f"   Batch health: {insights['batch_health']}")
            print(f"   Performance rating: {insights['performance_rating']}")
            print(f"   Child jobs returned: {len(status_result['child_jobs'])}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Batch status and intelligence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all UnifiedBatchProcessor tests"""
    print("🚀 UNIFIED BATCH PROCESSOR TEST SUITE")
    print("Senior Principal Engineer Implementation")
    print("=" * 70)
    print("Testing enterprise-grade batch processing engine")
    print("=" * 70)
    
    tests = [
        ("Architecture and Initialization", test_unified_batch_processor_architecture),
        ("Validation and Planning", test_batch_validation_and_planning),
        ("Batch Job Creation", test_batch_job_creation),
        ("Unified Batch Submission", test_unified_batch_submission),
        ("Status and Intelligence", test_batch_status_and_intelligence)
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
        print("🎉 UNIFIED BATCH PROCESSOR READY FOR PRODUCTION!")
        print("🏆 Successfully consolidated 4 competing systems into unified architecture")
        print("🚀 Phase 2 complete - ready for Phase 3: Unified API Extension")
        return 0
    else:
        print("⚠️ Some tests failed - review implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)