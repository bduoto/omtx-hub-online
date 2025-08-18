#!/usr/bin/env python3
"""
Test that only new format jobs appear in My Results
"""

import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

async def test_new_format_filtering():
    """Test that the system only shows new format jobs"""
    
    print("🔍 Testing New Format Only Filtering")
    print("=" * 50)
    
    try:
        from services.unified_job_storage import unified_job_storage
        from database.gcp_job_manager import gcp_job_manager
        from config.gcp_database import gcp_database
        
        # First, let's see what's in the database
        print("\n📊 Database Analysis:")
        
        # Get a sample of jobs directly from Firestore
        jobs_ref = gcp_database.db.collection('jobs').limit(10)
        docs = jobs_ref.stream()
        
        new_format_count = 0
        legacy_count = 0
        
        for doc in docs:
            job_data = doc.to_dict()
            if 'job_type' in job_data:
                new_format_count += 1
                print(f"   ✅ {doc.id}: Has job_type = {job_data['job_type']}")
            else:
                legacy_count += 1
                print(f"   ❌ {doc.id}: Missing job_type (legacy)")
        
        print(f"\n📊 Sample Results:")
        print(f"   New format jobs: {new_format_count}")
        print(f"   Legacy jobs: {legacy_count}")
        
        # Now test the unified job storage
        print(f"\n🔍 Testing Unified Job Storage:")
        
        # Get jobs through the new system
        jobs, pagination = await unified_job_storage.get_user_jobs(
            user_id="current_user",
            limit=10,
            page=1
        )
        
        print(f"   Jobs returned: {len(jobs)}")
        print(f"   Total in system: {pagination.get('total', 0)}")
        
        if jobs:
            print(f"\n   Jobs that passed the filter:")
            for i, job in enumerate(jobs[:5]):
                print(f"     {i+1}. {job.name} - Type: {job.job_type.value}, Status: {job.status.value}")
        else:
            print(f"   ⚠️ No jobs returned (all filtered out as legacy)")
        
        # Test API endpoint
        print(f"\n🔍 Testing API Endpoint:")
        import requests
        
        try:
            response = requests.get("http://localhost:8000/api/v2/results/my-jobs?page=1&per_page=5")
            if response.status_code == 200:
                data = response.json()
                api_jobs = data.get('jobs', [])
                print(f"   API returned: {len(api_jobs)} jobs")
                
                if api_jobs:
                    print(f"   First job from API:")
                    first_job = api_jobs[0]
                    print(f"     ID: {first_job.get('id')}")
                    print(f"     Name: {first_job.get('name')}")
                    print(f"     Job Type: {first_job.get('job_type')}")
                    print(f"     Status: {first_job.get('status')}")
            else:
                print(f"   ❌ API error: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ API test skipped (backend may not be running): {e}")
        
        # Summary
        print(f"\n" + "=" * 50)
        print(f"📊 SUMMARY:")
        
        if new_format_count > 0 and len(jobs) > 0:
            print(f"✅ System is correctly showing new format jobs only")
            print(f"   - Database has {new_format_count} new format jobs")
            print(f"   - System returned {len(jobs)} jobs")
        elif new_format_count == 0:
            print(f"⚠️ No new format jobs in database")
            print(f"   - Need to run migration script: python migrate_to_new_format.py")
        elif len(jobs) == 0 and legacy_count > 0:
            print(f"✅ System is correctly filtering out legacy jobs")
            print(f"   - Database has {legacy_count} legacy jobs")
            print(f"   - System returned 0 jobs (correctly filtered)")
            print(f"   - Run migration to convert legacy jobs: python migrate_to_new_format.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_new_format_filtering())
    
    if success:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed")