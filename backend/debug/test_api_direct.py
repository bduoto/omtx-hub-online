#!/usr/bin/env python3
"""
Test API endpoint directly to isolate the issue
"""

import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

# Mock BackgroundTasks for testing
class MockBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        print(f"📌 Background task added: {func.__name__}")

async def test_api_endpoint():
    """Test the enhanced results endpoint directly"""
    
    try:
        from api.enhanced_results_endpoints import get_my_jobs
        from fastapi import Query
        
        print("🔍 Testing Enhanced Results API Endpoint Directly")
        print("=" * 50)
        
        # Mock request parameters
        background_tasks = MockBackgroundTasks()
        page = 1
        per_page = 3
        job_type = None
        status = None
        task_type = None
        search = None
        
        print(f"📝 Parameters: page={page}, per_page={per_page}")
        
        # Call the endpoint function directly
        result = await get_my_jobs(
            background_tasks=background_tasks,
            page=page,
            per_page=per_page,
            job_type=job_type,
            status=status,
            task_type=task_type,
            search=search
        )
        
        print(f"✅ API endpoint call successful!")
        print(f"📊 Result type: {type(result)}")
        
        # Check if it's the expected response model
        if hasattr(result, 'jobs'):
            print(f"💼 Jobs count: {len(result.jobs)}")
            for i, job in enumerate(result.jobs[:2]):
                print(f"   Job {i+1}: {job.name} ({job.status})")
        
        if hasattr(result, 'pagination'):
            print(f"📄 Pagination: {result.pagination}")
            
        if hasattr(result, 'statistics'):
            print(f"📈 Statistics keys: {list(result.statistics.keys()) if result.statistics else 'None'}")
            
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_endpoint())
    if success:
        print(f"\n🎉 API endpoint works directly!")
        print(f"💡 The issue might be with FastAPI routing or validation")
    else:
        print(f"\n💔 API endpoint has an internal error")