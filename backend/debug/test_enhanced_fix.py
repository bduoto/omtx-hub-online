#!/usr/bin/env python3
"""
Test Enhanced Job Model Fix
"""

import os
from dotenv import load_dotenv
load_dotenv()

try:
    from database.gcp_job_manager import gcp_job_manager
    from models.enhanced_job_model import EnhancedJobData
    
    print("🔍 Testing Enhanced Job Model Fix")
    print("=" * 40)
    
    # Get some my_results data
    print("📊 Getting user job results...")
    user_results = gcp_job_manager.get_user_job_results(limit=2)
    print(f"Retrieved {len(user_results)} results")
    
    if user_results:
        print(f"\n🔍 Testing conversion of first result...")
        first_result = user_results[0]
        print(f"   Original keys: {list(first_result.keys())}")
        
        try:
            enhanced_job = EnhancedJobData.from_my_results(first_result)
            print(f"   ✅ Conversion successful!")
            print(f"   Enhanced job ID: {enhanced_job.id}")
            print(f"   Enhanced job name: {enhanced_job.name}")
            print(f"   Enhanced job type: {enhanced_job.job_type.value}")
            print(f"   Enhanced job status: {enhanced_job.status.value}")
            
            # Test API dict conversion
            api_dict = enhanced_job.to_api_dict()
            print(f"   ✅ API dict conversion successful!")
            print(f"   API dict keys: {list(api_dict.keys())}")
            
        except Exception as e:
            print(f"   ❌ Conversion failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No user results to test with")
    
    print(f"\n🔍 Testing unified job storage...")
    import asyncio
    
    async def test_unified_storage():
        try:
            from services.unified_job_storage import unified_job_storage
            
            # Test the method directly
            jobs, pagination = await unified_job_storage.get_user_jobs(
                user_id="current_user",
                limit=2,
                page=1
            )
            
            print(f"   ✅ Unified storage test successful!")
            print(f"   Retrieved {len(jobs)} jobs")
            print(f"   Pagination: {pagination}")
            
            for i, job in enumerate(jobs):
                print(f"   Job {i+1}: {job.name} ({job.status.value})")
        
        except Exception as e:
            print(f"   ❌ Unified storage test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the async test
    asyncio.run(test_unified_storage())

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback  
    traceback.print_exc()