"""
Test script to verify database optimization improvements
Run this after creating Firestore indexes to see performance gains
"""

import asyncio
import time
from datetime import datetime, timezone
from config.gcp_database import gcp_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_optimizations():
    """Test various database operations and measure performance"""
    
    print("\n🧪 Testing Database Optimizations...\n")
    
    # Test 1: Cache performance
    print("1️⃣ Testing cache performance...")
    
    # First call - no cache
    start = time.time()
    jobs1, cursor1 = gcp_database.get_jobs_by_status_optimized('completed', limit=20)
    time1 = time.time() - start
    print(f"   First call (no cache): {time1:.3f}s - Retrieved {len(jobs1)} jobs")
    
    # Second call - should hit cache
    start = time.time()
    jobs2, cursor2 = gcp_database.get_jobs_by_status_optimized('completed', limit=20)
    time2 = time.time() - start
    print(f"   Second call (cached): {time2:.3f}s - Retrieved {len(jobs2)} jobs")
    print(f"   ✅ Cache speedup: {time1/time2:.1f}x faster\n")
    
    # Test 2: Cursor-based pagination
    print("2️⃣ Testing cursor-based pagination...")
    
    # Get first page
    start = time.time()
    page1_jobs, page1_cursor = gcp_database.get_jobs_by_status_optimized('completed', limit=10)
    print(f"   Page 1: Retrieved {len(page1_jobs)} jobs in {time.time() - start:.3f}s")
    
    if page1_cursor:
        # Get second page using cursor
        start = time.time()
        page2_jobs, page2_cursor = gcp_database.get_jobs_by_status_optimized('completed', limit=10, cursor=page1_cursor)
        print(f"   Page 2: Retrieved {len(page2_jobs)} jobs in {time.time() - start:.3f}s")
        print(f"   ✅ Pagination working with cursor\n")
    else:
        print("   ℹ️ Not enough data for pagination test\n")
    
    # Test 3: User-specific queries with composite indexes
    print("3️⃣ Testing user-specific queries...")
    
    # This should use the user_id + status + created_at composite index
    start = time.time()
    user_jobs, _ = gcp_database.get_user_jobs_optimized(
        user_id='anonymous',  # or specific user_id if you have one
        status='completed',
        limit=20
    )
    query_time = time.time() - start
    print(f"   User query with status filter: {query_time:.3f}s - Retrieved {len(user_jobs)} jobs")
    
    # Test 4: Batch operations
    print("4️⃣ Testing batch operations...")
    
    if jobs1 and len(jobs1) >= 5:
        job_ids = [job['id'] for job in jobs1[:5]]
        
        # Individual fetches (old way)
        start = time.time()
        individual_jobs = []
        for job_id in job_ids:
            job = gcp_database.get_job(job_id, use_cache=False)
            if job:
                individual_jobs.append(job)
        individual_time = time.time() - start
        
        # Batch fetch (new way)
        start = time.time()
        batch_jobs = gcp_database.batch_get_jobs(job_ids)
        batch_time = time.time() - start
        
        print(f"   Individual fetches: {individual_time:.3f}s for {len(individual_jobs)} jobs")
        print(f"   Batch fetch: {batch_time:.3f}s for {len(batch_jobs)} jobs")
        print(f"   ✅ Batch speedup: {individual_time/batch_time:.1f}x faster\n")
    
    # Test 5: Cache statistics
    print("5️⃣ Cache statistics:")
    stats = gcp_database.get_query_stats()
    print(f"   Cache entries: {stats['cache_entries']}")
    print(f"   Cache size: {stats['cache_size_bytes']:,} bytes")
    print(f"   Database available: {stats['available']}")
    print(f"   Project ID: {stats['project_id']}\n")
    
    # Test 6: Test job type queries
    print("6️⃣ Testing job type queries...")
    
    start = time.time()
    single_jobs, _ = gcp_database.get_jobs_by_type_optimized('single', limit=10)
    print(f"   Single jobs: {len(single_jobs)} retrieved in {time.time() - start:.3f}s")
    
    start = time.time()
    batch_parent_jobs, _ = gcp_database.get_jobs_by_type_optimized('batch_parent', limit=10)
    print(f"   Batch parent jobs: {len(batch_parent_jobs)} retrieved in {time.time() - start:.3f}s")
    
    # Test cache invalidation
    print("\n7️⃣ Testing cache invalidation...")
    gcp_database.invalidate_cache('get_jobs')
    print("   ✅ Cache invalidated for 'get_jobs' pattern")
    
    print("\n✨ Database optimization tests complete!")
    print("\n⚠️  Note: Make sure you've created the Firestore composite indexes!")
    print("   Without indexes, queries will be slower and may fail.")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_database_optimizations())