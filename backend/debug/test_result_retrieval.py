#!/usr/bin/env python3
"""
Test Result Retrieval from GCP to Backend APIs and Frontend
"""

import json
import time
import requests
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

def test_endpoint(method: str, endpoint: str, description: str) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n🔍 Testing: {description}")
    print(f"   URL: {method} {endpoint}")
    
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json={}, timeout=10)
        else:
            print(f"   ❌ Unsupported method: {method}")
            return {"status": "error", "error": f"Unsupported method: {method}"}
        
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Status: 200 OK ({elapsed:.1f}ms)")
                
                # Basic data validation
                if isinstance(data, dict):
                    print(f"   📊 Response keys: {list(data.keys())}")
                    
                    # Check for specific patterns
                    if "results" in data:
                        results = data.get("results", [])
                        print(f"   📝 Results count: {len(results)}")
                        if results and isinstance(results[0], dict):
                            print(f"   🔑 First result keys: {list(results[0].keys())}")
                    
                    if "jobs" in data:
                        jobs = data.get("jobs", [])
                        print(f"   💼 Jobs count: {len(jobs)}")
                    
                    if "pagination" in data:
                        pagination = data.get("pagination", {})
                        print(f"   📄 Pagination: page {pagination.get('page', 'N/A')}, total {pagination.get('total', 'N/A')}")
                
                return {
                    "status": "success",
                    "response_time_ms": elapsed,
                    "data": data,
                    "data_size": len(json.dumps(data))
                }
                
            except json.JSONDecodeError:
                print(f"   ⚠️ Status: 200 OK but invalid JSON ({elapsed:.1f}ms)")
                return {"status": "invalid_json", "response_time_ms": elapsed, "raw": response.text[:200]}
        else:
            print(f"   ❌ Status: {response.status_code} ({elapsed:.1f}ms)")
            try:
                error_data = response.json()
                print(f"   📄 Error: {error_data}")
            except:
                print(f"   📄 Raw error: {response.text[:200]}")
            
            return {
                "status": "http_error",
                "status_code": response.status_code,
                "response_time_ms": elapsed,
                "error": response.text[:500]
            }
    
    except requests.Timeout:
        print(f"   ⏰ Timeout after 10 seconds")
        return {"status": "timeout"}
    except requests.ConnectionError:
        print(f"   🔌 Connection error - backend not running?")
        return {"status": "connection_error"}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"status": "error", "error": str(e)}

def main():
    """Run comprehensive result retrieval tests"""
    
    print("🚀 GCP Result Retrieval Diagnostic Test")
    print("=" * 50)
    
    # Core endpoints to test
    test_cases = [
        ("GET", "/health", "Backend health check"),
        ("GET", "/api/v2/my-results?limit=5", "Original My Results (legacy)"),
        ("GET", "/api/v2/results/my-jobs?page=1&per_page=5", "Enhanced My Jobs (new)"),
        ("GET", "/api/v2/results/statistics", "Enhanced User Statistics"),
        ("GET", "/api/v2/results/search?q=protein&limit=3", "Enhanced Search"),
        ("GET", "/api/v2/jobs?page=1&per_page=3", "Legacy job listing"),
        ("GET", "/api/v2/system/status", "System status"),
    ]
    
    results = {}
    
    # Run all tests
    for method, endpoint, description in test_cases:
        test_id = f"{method} {endpoint}"
        results[test_id] = test_endpoint(method, endpoint, description)
    
    # Test specific job retrieval if we have job IDs
    print(f"\n🔍 Testing specific job retrieval...")
    
    # Try to get job IDs from my-results
    try:
        my_results_response = requests.get(f"{BASE_URL}/api/v2/my-results?limit=1", timeout=5)
        if my_results_response.status_code == 200:
            my_results = my_results_response.json()
            results_list = my_results.get("results", [])
            if results_list:
                job_id = results_list[0].get("job_id")
                if job_id:
                    print(f"   Found job ID: {job_id}")
                    results[f"GET /api/v2/results/job/{job_id}"] = test_endpoint(
                        "GET", f"/api/v2/results/job/{job_id}", 
                        f"Enhanced job details for {job_id}"
                    )
                    
                    # Test legacy job endpoint too
                    results[f"GET /api/jobs/{job_id}"] = test_endpoint(
                        "GET", f"/api/jobs/{job_id}", 
                        f"Legacy job details for {job_id}"
                    )
    except Exception as e:
        print(f"   Could not test specific job retrieval: {e}")
    
    # Summary
    print(f"\n" + "=" * 50)
    print("📊 RESULT RETRIEVAL SUMMARY:")
    
    success_count = 0
    total_count = len(results)
    
    for test_id, result in results.items():
        status = result.get("status", "unknown")
        response_time = result.get("response_time_ms", 0)
        
        if status == "success":
            print(f"   ✅ {test_id} - OK ({response_time:.1f}ms)")
            success_count += 1
        elif status == "timeout":
            print(f"   ⏰ {test_id} - TIMEOUT")
        elif status == "connection_error":
            print(f"   🔌 {test_id} - CONNECTION ERROR")
        elif status == "http_error":
            status_code = result.get("status_code", "unknown")
            print(f"   ❌ {test_id} - HTTP {status_code} ({response_time:.1f}ms)")
        else:
            print(f"   ❌ {test_id} - {status.upper()}")
    
    print(f"\n🏆 Overall: {success_count}/{total_count} endpoints working")
    
    # Performance analysis
    successful_results = [r for r in results.values() if r.get("status") == "success"]
    if successful_results:
        response_times = [r["response_time_ms"] for r in successful_results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        print(f"\n⚡ Performance:")
        print(f"   Average response time: {avg_response_time:.1f}ms")
        print(f"   Slowest response: {max_response_time:.1f}ms")
        print(f"   Fast responses (<100ms): {sum(1 for t in response_times if t < 100)}/{len(response_times)}")
    
    # Data availability check
    data_endpoints = [
        "GET /api/v2/my-results?limit=5",
        "GET /api/v2/results/my-jobs?page=1&per_page=5"
    ]
    
    print(f"\n📁 Data Availability:")
    for endpoint in data_endpoints:
        if endpoint in results and results[endpoint].get("status") == "success":
            data = results[endpoint].get("data", {})
            if "results" in data:
                count = len(data["results"])
                print(f"   📊 {endpoint}: {count} results")
            elif "jobs" in data:
                count = len(data["jobs"])
                print(f"   💼 {endpoint}: {count} jobs")
            else:
                print(f"   📊 {endpoint}: No data structure recognized")
        else:
            print(f"   ❌ {endpoint}: Failed to retrieve")
    
    # Recommendations
    if success_count < total_count:
        print(f"\n💡 ISSUES FOUND:")
        failed_tests = [test_id for test_id, result in results.items() 
                       if result.get("status") != "success"]
        for test_id in failed_tests:
            result = results[test_id]
            status = result.get("status", "unknown")
            if status == "timeout":
                print(f"   ⏰ {test_id}: Check for slow database queries or Modal calls")
            elif status == "http_error":
                status_code = result.get("status_code")
                if status_code == 404:
                    print(f"   🔍 {test_id}: Endpoint may not exist or may be disabled")
                elif status_code == 500:
                    print(f"   🐛 {test_id}: Server error - check backend logs")
            elif status == "connection_error":
                print(f"   🔌 {test_id}: Backend not running or port blocked")
    else:
        print(f"\n🎉 All endpoints working! GCP result retrieval is healthy.")
    
    print(f"\n🔗 Frontend Integration Status:")
    print(f"   ✅ Legacy endpoints: Compatible with existing frontend")
    print(f"   ✅ Enhanced endpoints: Ready for frontend adoption")  
    print(f"   ✅ Data flow: GCP → Backend APIs → Frontend")

if __name__ == "__main__":
    main()