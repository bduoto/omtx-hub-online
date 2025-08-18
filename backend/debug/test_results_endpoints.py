#!/usr/bin/env python3
"""
Test script for results endpoints
Tests the enhanced my-results and job details endpoints
"""

import asyncio
import json
import sys
from typing import Dict, Any

async def test_my_results_endpoint():
    """Test the enhanced my-results endpoint"""
    print("🧪 Testing my-results-enhanced endpoint...")
    
    try:
        # Import the endpoint function directly
        from api.unified_endpoints import get_my_results_enhanced
        
        # Call the endpoint
        result = await get_my_results_enhanced(
            user_id="current_user",
            limit=10,
            enrich_results=True
        )
        
        print(f"   ✅ Endpoint returned {len(result.get('results', []))} results")
        print(f"   Source: {result.get('source', 'unknown')}")
        print(f"   Enriched: {result.get('enriched', False)}")
        
        # Return first job ID for testing individual job endpoint
        results = result.get('results', [])
        if results:
            first_job = results[0]
            job_id = first_job.get('id') or first_job.get('job_id')
            print(f"   First job ID: {job_id}")
            return job_id
        else:
            print("   ⚠️ No results returned")
            return None
            
    except Exception as e:
        print(f"   ❌ My-results endpoint failed: {e}")
        return None

async def test_job_details_endpoint(job_id: str):
    """Test the enhanced job details endpoint"""
    print(f"🧪 Testing enhanced job details endpoint for {job_id}...")
    
    try:
        # Import the endpoint function directly
        from api.unified_endpoints import get_job_details_enhanced
        
        # Call the endpoint
        result = await get_job_details_enhanced(job_id)
        
        print(f"   ✅ Job details loaded")
        print(f"   Result type: {result.get('result_type', 'unknown')}")
        print(f"   Enriched: {result.get('enriched', False)}")
        print(f"   Status: {result.get('status', 'unknown')}")
        
        if result.get('result_type') == 'batch':
            batch_results = result.get('batch_results', {})
            print(f"   Batch children: {batch_results.get('completed_children', 0)}/{batch_results.get('total_children', 0)}")
        elif result.get('has_structure'):
            print(f"   Has structure data: ✅")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Job details endpoint failed: {e}")
        return False

async def test_regular_job_endpoint(job_id: str):
    """Test the regular job endpoint"""
    print(f"🧪 Testing regular job endpoint for {job_id}...")
    
    try:
        # Import the endpoint function directly
        from api.unified_endpoints import get_job_status
        
        # Call the endpoint
        result = await get_job_status(job_id)
        
        print(f"   ✅ Regular job endpoint worked")
        print(f"   Status: {result.status}")
        print(f"   Task type: {result.task_type}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Regular job endpoint failed: {e}")
        return False

def test_unified_job_manager():
    """Test the unified job manager directly"""
    print("🧪 Testing unified job manager...")
    
    try:
        from database.unified_job_manager import unified_job_manager
        
        # Test getting user job results
        user_results = unified_job_manager.get_user_job_results(5)
        print(f"   ✅ Got {len(user_results)} user results")
        
        # Test getting recent jobs
        recent_jobs = unified_job_manager.get_recent_jobs(5)
        print(f"   ✅ Got {len(recent_jobs)} recent jobs")
        
        # Return a job ID if available
        if user_results:
            job_id = user_results[0].get('id') or user_results[0].get('job_id')
            print(f"   First user result ID: {job_id}")
            return job_id
        elif recent_jobs:
            job_id = recent_jobs[0].get('id') or recent_jobs[0].get('job_id')
            print(f"   First recent job ID: {job_id}")
            return job_id
        else:
            print("   ⚠️ No jobs found")
            return None
            
    except Exception as e:
        print(f"   ❌ Unified job manager test failed: {e}")
        return None

async def main():
    """Run all tests"""
    print("🚀 Testing Results Endpoints")
    print("=" * 50)
    
    # Test unified job manager first
    job_id = test_unified_job_manager()
    
    if not job_id:
        print("❌ No job ID available for testing endpoints")
        return 1
    
    print(f"\n📋 Using job ID for testing: {job_id}")
    print("=" * 50)
    
    # Test my-results endpoint
    my_results_job_id = await test_my_results_endpoint()
    
    # Use job ID from my-results if available, otherwise use the one from job manager
    test_job_id = my_results_job_id or job_id
    
    # Test enhanced job details endpoint
    enhanced_success = await test_job_details_endpoint(test_job_id)
    
    # Test regular job endpoint
    regular_success = await test_regular_job_endpoint(test_job_id)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Job Manager: ✅")
    print(f"   My Results: {'✅' if my_results_job_id else '⚠️'}")
    print(f"   Enhanced Job Details: {'✅' if enhanced_success else '❌'}")
    print(f"   Regular Job Details: {'✅' if regular_success else '❌'}")
    
    if enhanced_success and regular_success:
        print("🎉 All endpoint tests passed!")
        return 0
    else:
        print("⚠️ Some endpoint tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print(f"\nExit code: {exit_code}")
    sys.exit(exit_code)
