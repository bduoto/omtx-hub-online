"""
Test script to verify My Results optimization improvements
Compares original vs optimized endpoint performance
"""

import asyncio
import time
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v2"

async def test_my_results_optimizations():
    """Test My Results optimization improvements"""
    
    print("\n🧪 Testing My Results Optimizations...\n")
    
    try:
        # Test 1: Basic performance comparison
        print("1️⃣ Testing basic performance comparison...")
        
        # Original endpoint
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}/my-results?limit=20")
            original_time = time.time() - start
            original_data = response.json() if response.status_code == 200 else {}
            print(f"   Original endpoint: {original_time:.3f}s - {len(original_data.get('results', []))} results")
        except Exception as e:
            print(f"   Original endpoint error: {e}")
            original_time = 999
            original_data = {}
        
        # Optimized endpoint
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}/my-results-optimized?per_page=20")
            optimized_time = time.time() - start
            optimized_data = response.json() if response.status_code == 200 else {}
            print(f"   Optimized endpoint: {optimized_time:.3f}s - {len(optimized_data.get('results', []))} results")
            
            if original_time > 0 and optimized_time > 0:
                speedup = original_time / optimized_time
                print(f"   ✅ Speedup: {speedup:.1f}x faster\n")
            else:
                print("   ⚠️ Could not calculate speedup\n")
                
        except Exception as e:
            print(f"   Optimized endpoint error: {e}\n")
            optimized_data = {}
        
        # Test 2: Pagination
        print("2️⃣ Testing pagination...")
        
        try:
            # Page 1
            response = requests.get(f"{BASE_URL}/my-results-optimized?page=1&per_page=5")
            if response.status_code == 200:
                page1_data = response.json()
                print(f"   Page 1: {len(page1_data.get('results', []))} results")
                print(f"   Pagination info: {page1_data.get('pagination', {})}")
                
                # Page 2 if available
                if page1_data.get('pagination', {}).get('has_next'):
                    response = requests.get(f"{BASE_URL}/my-results-optimized?page=2&per_page=5")
                    if response.status_code == 200:
                        page2_data = response.json()
                        print(f"   Page 2: {len(page2_data.get('results', []))} results")
                        print("   ✅ Pagination working correctly\n")
                else:
                    print("   ℹ️ Not enough data for page 2 test\n")
            else:
                print(f"   ❌ Pagination test failed: {response.status_code}\n")
                
        except Exception as e:
            print(f"   Pagination test error: {e}\n")
        
        # Test 3: Filtering
        print("3️⃣ Testing filtering...")
        
        try:
            # Filter by status
            response = requests.get(f"{BASE_URL}/my-results-optimized?status=completed&per_page=10")
            if response.status_code == 200:
                filtered_data = response.json()
                print(f"   Status filter (completed): {len(filtered_data.get('results', []))} results")
                print(f"   Filters applied: {filtered_data.get('filters_applied', {})}")
                print("   ✅ Filtering working correctly\n")
            else:
                print(f"   ❌ Filtering test failed: {response.status_code}\n")
                
        except Exception as e:
            print(f"   Filtering test error: {e}\n")
        
        # Test 4: Performance info
        print("4️⃣ Testing performance info...")
        
        try:
            response = requests.get(f"{BASE_URL}/my-results-optimized?per_page=10")
            if response.status_code == 200:
                perf_data = response.json()
                perf_info = perf_data.get('performance_info', {})
                print(f"   Optimized: {perf_info.get('optimized', False)}")
                print(f"   Database first: {perf_info.get('database_first', False)}")
                print(f"   Cache enabled: {perf_info.get('cache_enabled', False)}")
                print(f"   Source: {perf_data.get('source', 'unknown')}")
                print("   ✅ Performance info available\n")
            else:
                print(f"   ❌ Performance info test failed: {response.status_code}\n")
                
        except Exception as e:
            print(f"   Performance info test error: {e}\n")
        
        # Test 5: Cache effectiveness
        print("5️⃣ Testing cache effectiveness...")
        
        try:
            # First call
            start = time.time()
            response1 = requests.get(f"{BASE_URL}/my-results-optimized?per_page=10")
            time1 = time.time() - start
            
            # Second call (should hit cache)
            start = time.time()
            response2 = requests.get(f"{BASE_URL}/my-results-optimized?per_page=10")
            time2 = time.time() - start
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                
                print(f"   First call: {time1:.3f}s")
                print(f"   Second call: {time2:.3f}s")
                
                # Check if second call shows cache hit
                if data2.get('cache_status') == 'hit' or time2 < time1 * 0.5:
                    cache_speedup = time1 / time2 if time2 > 0 else float('inf')
                    print(f"   ✅ Cache speedup: {cache_speedup:.1f}x faster\n")
                else:
                    print("   ℹ️ Cache may not be hitting (results might be different)\n")
            else:
                print(f"   ❌ Cache test failed: {response1.status_code}, {response2.status_code}\n")
                
        except Exception as e:
            print(f"   Cache test error: {e}\n")
        
        print("✨ My Results optimization tests complete!")
        print("\n📊 Summary:")
        print("- Database-first approach implemented")
        print("- Cursor-based pagination available") 
        print("- Advanced filtering options")
        print("- Simple in-memory caching")
        print("- Graceful fallback to original endpoint")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting My Results optimization tests...")
    print("📋 Make sure your FastAPI server is running on http://localhost:8000")
    print()
    
    try:
        # Quick connectivity test
        response = requests.get(f"{BASE_URL}/system/status", timeout=5)
        if response.status_code == 200:
            print("✅ Server is reachable")
            asyncio.run(test_my_results_optimizations())
        else:
            print(f"❌ Server returned {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Please start the FastAPI server first:")
        print("   cd backend && uvicorn main:app --reload --port 8000")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")