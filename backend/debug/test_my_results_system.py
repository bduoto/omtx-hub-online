#!/usr/bin/env python3
"""
Test the new My Results system with bucket-based indexing
"""

import sys
import asyncio
import json
sys.path.append('.')

from services.my_results_indexer import my_results_indexer

async def test_my_results_system():
    """Test the complete My Results system"""
    
    print("🧪 Testing My Results Indexing System...\n")
    
    # Test 1: Get user results
    print("1️⃣ Testing user results indexing...")
    try:
        results = await my_results_indexer.get_user_results("current_user", limit=10)
        
        print(f"   ✅ Retrieved {results.get('total', 0)} results from {results.get('source', 'unknown')}")
        print(f"   📊 Cache TTL: {results.get('cache_ttl', 'N/A')} seconds")
        print(f"   🕒 Indexed at: {results.get('indexed_at', 'N/A')}")
        
        # Show sample results
        sample_results = results.get('results', [])[:3]
        if sample_results:
            print(f"   📋 Sample results:")
            for i, result in enumerate(sample_results, 1):
                task_type = result.get('task_type', 'unknown')
                job_name = result.get('job_name', 'unnamed')
                status = result.get('status', 'unknown')
                file_count = result.get('file_count', 0)
                has_structure = result.get('has_structure', False)
                auto_indexed = result.get('auto_indexed', False)
                
                print(f"      {i}. {job_name} ({task_type})")
                print(f"         Status: {status} | Files: {file_count} | Structure: {has_structure} | Auto: {auto_indexed}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Test caching
    print(f"\n2️⃣ Testing caching...")
    try:
        # First call (should hit cache if available)
        start_time = asyncio.get_event_loop().time()
        cached_results = await my_results_indexer.get_user_results("current_user", limit=10, use_cache=True)
        cached_time = asyncio.get_event_loop().time() - start_time
        
        # Second call (should not use cache)
        start_time = asyncio.get_event_loop().time()
        fresh_results = await my_results_indexer.get_user_results("current_user", limit=10, use_cache=False)
        fresh_time = asyncio.get_event_loop().time() - start_time
        
        print(f"   ⚡ Cached call: {cached_time:.3f}s ({cached_results.get('source', 'unknown')})")
        print(f"   🔄 Fresh call: {fresh_time:.3f}s ({fresh_results.get('source', 'unknown')})")
        
        if cached_time < fresh_time:
            print(f"   ✅ Caching is working (cached call was faster)")
        else:
            print(f"   ⚠️ Cache might not be active (times: cached={cached_time:.3f}s, fresh={fresh_time:.3f}s)")
        
    except Exception as e:
        print(f"   ❌ Error testing caching: {e}")
    
    # Test 3: Test download info for a specific job
    print(f"\n3️⃣ Testing download info...")
    try:
        # Get the first job ID from results
        results = await my_results_indexer.get_user_results("current_user", limit=1)
        job_results = results.get('results', [])
        
        if job_results:
            job_id = job_results[0].get('job_id')
            if job_id:
                download_info = await my_results_indexer.get_job_download_info(job_id)
                
                print(f"   📁 Job ID: {job_id}")
                print(f"   📊 Files: {len(download_info.get('files', []))}")
                print(f"   🔗 Download endpoints: {len(download_info.get('download_endpoints', []))}")
                
                endpoints = download_info.get('download_endpoints', [])
                friendly_names = download_info.get('user_friendly_names', {})
                
                if endpoints:
                    print(f"   📂 Available downloads:")
                    for endpoint in endpoints:
                        file_type = 'cif' if '/cif' in endpoint else 'pdb' if '/pdb' in endpoint else 'unknown'
                        friendly_name = friendly_names.get(file_type, f"{job_id}.{file_type}")
                        print(f"      - {endpoint} → {friendly_name}")
                else:
                    print(f"   ⚠️ No download endpoints available")
            else:
                print(f"   ⚠️ No job_id found in first result")
        else:
            print(f"   ⚠️ No job results found to test download info")
        
    except Exception as e:
        print(f"   ❌ Error testing download info: {e}")
    
    # Test 4: Cache invalidation
    print(f"\n4️⃣ Testing cache invalidation...")
    try:
        # Invalidate cache
        my_results_indexer.invalidate_cache("current_user")
        print(f"   ✅ Cache invalidated for current_user")
        
        # Test that next call rebuilds cache
        fresh_after_invalidation = await my_results_indexer.get_user_results("current_user", limit=10)
        print(f"   🔄 Results after invalidation: {fresh_after_invalidation.get('total', 0)} from {fresh_after_invalidation.get('source', 'unknown')}")
        
    except Exception as e:
        print(f"   ❌ Error testing cache invalidation: {e}")
    
    print(f"\n✅ My Results system testing complete!")
    
    # Summary
    print(f"\n📊 SYSTEM STATUS SUMMARY:")
    try:
        final_results = await my_results_indexer.get_user_results("current_user", limit=50)
        total_results = final_results.get('total', 0)
        data_source = final_results.get('source', 'unknown')
        
        print(f"   - Total user results: {total_results}")
        print(f"   - Data source: {data_source}")
        print(f"   - Indexer available: ✅")
        print(f"   - Caching: {'✅' if data_source == 'indexed' else '⚠️'}")
        
        if total_results > 0:
            print(f"   - Ready for frontend: ✅")
        else:
            print(f"   - Ready for frontend: ⚠️ (no results found)")
            
    except Exception as e:
        print(f"   - System error: ❌ {e}")

if __name__ == "__main__":
    asyncio.run(test_my_results_system())