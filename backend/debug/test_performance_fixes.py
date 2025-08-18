#!/usr/bin/env python3
"""
Test Performance Fixes
Quick test to verify the performance improvements are working
"""

import sys
import os
import asyncio
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.gcp_results_indexer import gcp_results_indexer

async def test_performance():
    """Test the performance improvements"""
    print("🚀 Testing Performance Improvements")
    print("=" * 50)
    
    # Test 1: First call (cache miss)
    print("Test 1: First call (cache miss expected)")
    start_time = time.time()
    
    try:
        results = await gcp_results_indexer.get_user_results("current_user", limit=20)
        
        elapsed = time.time() - start_time
        print(f"⏱️  First call: {elapsed:.2f}s")
        print(f"📊 Results: {len(results.get('results', []))} jobs")
        print(f"📦 Source: {results.get('source', 'unknown')}")
        print(f"🔄 Cache status: {results.get('cache_status', 'unknown')}")
        
    except Exception as e:
        print(f"❌ First call failed: {e}")
        return
    
    # Test 2: Second call (cache hit expected)
    print("\nTest 2: Second call (cache hit expected)")
    start_time = time.time()
    
    try:
        results2 = await gcp_results_indexer.get_user_results("current_user", limit=20)
        
        elapsed = time.time() - start_time
        print(f"⚡ Second call: {elapsed:.2f}s")
        print(f"📦 Source: {results2.get('source', 'unknown')}")
        
        if elapsed < 0.1:
            print("🎉 EXCELLENT: Cache working perfectly!")
        elif elapsed < 1.0:
            print("✅ GOOD: Significant speedup from caching")
        else:
            print("⚠️  SLOW: Cache may not be working properly")
            
    except Exception as e:
        print(f"❌ Second call failed: {e}")
        return
    
    # Test 3: Check cache stats
    print("\nTest 3: Cache statistics")
    try:
        if hasattr(gcp_results_indexer, 'get_cache_stats'):
            stats = gcp_results_indexer.get_cache_stats()
            print(f"📈 Cache stats: {stats}")
        
        print(f"🔧 Job list cache: {'exists' if gcp_results_indexer._job_list_cache else 'empty'}")
        if gcp_results_indexer._job_list_cache:
            print(f"📋 Cached job count: {len(gcp_results_indexer._job_list_cache)}")
            
    except Exception as e:
        print(f"⚠️  Could not get cache stats: {e}")
    
    print("\n" + "=" * 50)
    print("Performance test complete!")
    
    # Performance expectations
    if elapsed < 0.1:
        print("🚀 STATUS: BLAZING FAST")
    elif elapsed < 2.0:
        print("✅ STATUS: FAST")
    elif elapsed < 5.0:
        print("🔄 STATUS: IMPROVED")
    else:
        print("⚠️  STATUS: NEEDS MORE WORK")

if __name__ == "__main__":
    asyncio.run(test_performance())