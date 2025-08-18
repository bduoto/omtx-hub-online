#!/usr/bin/env python3
"""
Debug batch submission issues
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_batch_submission():
    """Debug batch submission step by step"""
    
    print("🔍 DEBUGGING BATCH SUBMISSION")
    print("=" * 50)
    
    # Test 1: Check if unified batch processor can be imported
    print("\n1️⃣ Testing imports...")
    try:
        from services.unified_batch_processor import unified_batch_processor, BatchSubmissionRequest
        print("   ✅ Imports successful")
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    # Test 2: Create a simple request
    print("\n2️⃣ Creating test request...")
    try:
        request = BatchSubmissionRequest(
            job_name="Debug Test",
            protein_sequence="MKLLVLSLSLVLVLLLSHPQGSHM",
            protein_name="Debug Protein",
            ligands=[{"smiles": "CCO", "name": "Ethanol"}],
            model_name="boltz2",
            use_msa=True,
            use_potentials=False,
            user_id="debug_user"
        )
        print(f"   ✅ Request created: {request.job_name}")
    except Exception as e:
        print(f"   ❌ Request creation error: {e}")
        return False
    
    # Test 3: Test validation step
    print("\n3️⃣ Testing validation...")
    try:
        validation_result = await unified_batch_processor._validate_batch_request(request)
        print(f"   ✅ Validation result: {validation_result}")
    except Exception as e:
        print(f"   ❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Test execution plan creation
    print("\n4️⃣ Testing execution plan...")
    try:
        execution_plan = await unified_batch_processor._create_execution_plan(request)
        print(f"   ✅ Execution plan created")
        print(f"   📊 Total jobs: {execution_plan.total_jobs}")
        print(f"   📊 Estimated duration: {execution_plan.estimated_duration}")
    except Exception as e:
        print(f"   ❌ Execution plan error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test batch parent creation
    print("\n5️⃣ Testing batch parent creation...")
    try:
        batch_parent = await unified_batch_processor._create_batch_parent(request, execution_plan)
        print(f"   ✅ Batch parent created: {batch_parent.id}")
        print(f"   📊 Job type: {batch_parent.job_type}")
    except Exception as e:
        print(f"   ❌ Batch parent creation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Test child job creation
    print("\n6️⃣ Testing child job creation...")
    try:
        child_jobs = await unified_batch_processor._create_child_jobs(batch_parent, request, execution_plan)
        print(f"   ✅ Child jobs created: {len(child_jobs)}")
        for i, child in enumerate(child_jobs):
            print(f"   📝 Child {i+1}: {child.name}")
    except Exception as e:
        print(f"   ❌ Child job creation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 7: Test storage initialization (this might be where it hangs)
    print("\n7️⃣ Testing storage initialization...")
    try:
        print("   🔄 Starting storage initialization...")
        await unified_batch_processor._initialize_batch_storage(batch_parent, child_jobs)
        print("   ✅ Storage initialization completed")
    except Exception as e:
        print(f"   ❌ Storage initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 8: Test execution (this is likely where it hangs)
    print("\n8️⃣ Testing batch execution...")
    try:
        print("   🔄 Starting batch execution...")
        execution_result = await unified_batch_processor._execute_batch_with_intelligence(
            batch_parent, child_jobs, execution_plan
        )
        print(f"   ✅ Batch execution completed: {execution_result}")
    except Exception as e:
        print(f"   ❌ Batch execution error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 50)
    print("🎯 DEBUG COMPLETED")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    asyncio.run(debug_batch_submission())
