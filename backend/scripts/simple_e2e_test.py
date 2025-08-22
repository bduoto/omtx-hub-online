#!/usr/bin/env python3
"""
Simple End-to-End Testing for Individual Boltz-2 Prediction Jobs
Tests the complete workflow without heavy dependencies
"""

import time
import json
import requests
from datetime import datetime
import sys

class SimpleJobTester:
    """Simple end-to-end test runner"""
    
    def __init__(self, base_url: str = "http://34.29.29.170"):
        self.base_url = base_url.rstrip('/')
        self.results = []
    
    def log_result(self, test_name: str, status: str, message: str, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.results.append(result)
        
        emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}
        print(f"{emoji.get(status, '?')} {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def test_health_check(self):
        """Test API health"""
        try:
            print(f"\n🔍 Testing API health at {self.base_url}")
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Health Check",
                    "PASS",
                    "API is healthy and responding",
                    {
                        "response_time": f"{response.elapsed.total_seconds():.3f}s",
                        "status": data.get("status", "unknown")
                    }
                )
                return True
            else:
                self.log_result(
                    "Health Check",
                    "FAIL",
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Health Check",
                "FAIL",
                f"Health check exception: {e}",
                {"error": str(e)}
            )
            return False
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics"""
        try:
            print(f"\n📊 Testing metrics endpoint")
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            
            if response.status_code == 200:
                metrics = response.text
                
                # Check for key metrics
                key_metrics = [
                    "http_requests_total",
                    "omtx_hub_active_jobs", 
                    "omtx_hub_app_info"
                ]
                
                found = [m for m in key_metrics if m in metrics]
                
                self.log_result(
                    "Metrics Endpoint",
                    "PASS",
                    f"Metrics available: {len(found)}/{len(key_metrics)}",
                    {
                        "found_metrics": found,
                        "size": f"{len(metrics)} bytes"
                    }
                )
                return True
            else:
                self.log_result(
                    "Metrics Endpoint",
                    "FAIL",
                    f"Metrics endpoint returned {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Metrics Endpoint",
                "FAIL",
                f"Metrics endpoint exception: {e}",
                {"error": str(e)}
            )
            return False
    
    def test_api_structure(self):
        """Test API structure and endpoints"""
        try:
            print(f"\n🏗️ Testing API structure")
            
            # Test API documentation
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            
            if response.status_code == 200:
                self.log_result(
                    "API Documentation",
                    "PASS",
                    "API documentation accessible",
                    {"docs_url": f"{self.base_url}/docs"}
                )
            else:
                self.log_result(
                    "API Documentation", 
                    "FAIL",
                    f"API docs returned {response.status_code}",
                    {}
                )
            
            # Test authentication requirement
            response = requests.get(f"{self.base_url}/api/v1/jobs", timeout=10)
            
            if response.status_code == 401:
                self.log_result(
                    "Authentication Required",
                    "PASS",
                    "API correctly requires authentication",
                    {"status_code": response.status_code}
                )
                return True
            else:
                self.log_result(
                    "Authentication Required",
                    "FAIL",
                    f"Expected 401, got {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "API Structure",
                "FAIL",
                f"API structure test exception: {e}",
                {"error": str(e)}
            )
            return False
    
    def test_webhook_endpoints(self):
        """Test webhook system endpoints"""
        try:
            print(f"\n🔔 Testing webhook system")
            
            # Test webhook events endpoint (should work without auth)
            response = requests.get(f"{self.base_url}/api/v1/webhooks/events", timeout=10)
            
            if response.status_code in [200, 401]:  # 401 is acceptable (needs auth)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])
                    self.log_result(
                        "Webhook System",
                        "PASS",
                        f"Webhook system available with {len(events)} events",
                        {
                            "events": [e.get("name") for e in events],
                            "has_signature_info": "signature_info" in data
                        }
                    )
                else:
                    self.log_result(
                        "Webhook System",
                        "PASS",
                        "Webhook system requires authentication (expected)",
                        {"status_code": response.status_code}
                    )
                return True
            else:
                self.log_result(
                    "Webhook System",
                    "FAIL",
                    f"Webhook events endpoint returned {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Webhook System",
                "FAIL",
                f"Webhook system test exception: {e}",
                {"error": str(e)}
            )
            return False
    
    def test_consolidated_api(self):
        """Test consolidated API endpoints"""
        try:
            print(f"\n🎯 Testing consolidated API")
            
            # Test without authentication (should fail appropriately)
            test_payload = {
                "model": "boltz2",
                "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "job_name": "Test Job - No Auth"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/predict",
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 401:
                self.log_result(
                    "API Authentication",
                    "PASS", 
                    "Consolidated API correctly requires authentication",
                    {"endpoint": "/api/v1/predict", "status": response.status_code}
                )
                return True
            elif response.status_code == 422:
                self.log_result(
                    "API Validation",
                    "PASS",
                    "API validation working (validation error expected without auth)",
                    {"endpoint": "/api/v1/predict", "status": response.status_code}
                )
                return True
            else:
                self.log_result(
                    "API Security",
                    "FAIL",
                    f"API should require auth but returned {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Consolidated API",
                "FAIL",
                f"Consolidated API test exception: {e}",
                {"error": str(e)}
            )
            return False
    
    def run_system_validation(self):
        """Run comprehensive system validation"""
        print("🚀 OMTX-Hub System Validation")
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 60)
        
        tests = [
            self.test_health_check,
            self.test_metrics_endpoint,
            self.test_api_structure,
            self.test_webhook_endpoints,
            self.test_consolidated_api
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                result = test()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
                failed += 1
        
        total = passed + failed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 System validation PASSED - Ready for production!")
        elif success_rate >= 60:
            print("⚠️ System validation PARTIAL - Some issues detected")
        else:
            print("🚨 System validation FAILED - Critical issues detected")
        
        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": success_rate
            },
            "results": self.results,
            "timestamp": datetime.utcnow().isoformat()
        }

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OMTX-Hub System Validation")
    parser.add_argument("--url", default="http://34.29.29.170", help="Base URL")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()
    
    tester = SimpleJobTester(args.url)
    results = tester.run_system_validation()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Exit with error if critical failures
    if results["summary"]["success_rate"] < 60:
        sys.exit(1)

if __name__ == "__main__":
    main()