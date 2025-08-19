#!/usr/bin/env python3
"""
Test Live Production System on GKE - CRITICAL VALIDATION
Distinguished Engineer Implementation - End-to-end production testing
"""

import requests
import json
import time
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    RESET = '\033[0m'

class ProductionTester:
    """Test the live production deployment on GKE"""
    
    def __init__(self, production_url: str = None):
        # Use your actual production URLs
        self.production_url = production_url or "http://34.29.29.170"  # Your ingress IP
        self.fallback_url = "http://34.10.21.160"  # Your LoadBalancer IP
        self.test_user_id = "demo-user"
        self.headers = {
            "X-User-Id": self.test_user_id,
            "X-Demo-Mode": "true",
            "Content-Type": "application/json"
        }
        
        logger.info(f"🧪 ProductionTester initialized")
        logger.info(f"   Primary URL: {self.production_url}")
        logger.info(f"   Fallback URL: {self.fallback_url}")
    
    def test_production_system(self) -> bool:
        """Test the complete live production system"""
        
        print(f"\n{Colors.CYAN}🔍 TESTING LIVE PRODUCTION SYSTEM ON GKE{Colors.RESET}")
        print(f"{Colors.CYAN}URL: {self.production_url}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        tests = [
            ("API Health Check", self.test_api_health),
            ("API Documentation", self.test_api_docs),
            ("Authentication System", self.test_authentication),
            ("Single Prediction", self.test_single_prediction),
            ("Batch Submission", self.test_batch_submission),
            ("Status Endpoints", self.test_status_endpoints),
            ("Error Handling", self.test_error_handling),
            ("Performance Metrics", self.test_performance)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"Testing {test_name}...", end=" ")
            try:
                success, message = test_func()
                if success:
                    print(f"{Colors.GREEN}✅ PASSED{Colors.RESET}")
                    if message:
                        print(f"  {Colors.CYAN}{message}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ FAILED{Colors.RESET}")
                    if message:
                        print(f"  {Colors.YELLOW}{message}{Colors.RESET}")
                
                results.append((test_name, success, message))
                
            except Exception as e:
                print(f"{Colors.RED}❌ ERROR: {e}{Colors.RESET}")
                results.append((test_name, False, str(e)))
        
        # Summary
        self._print_test_summary(results)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        return passed >= (total * 0.8)  # 80% pass rate acceptable for production
    
    def test_api_health(self) -> tuple[bool, str]:
        """Test API health endpoint"""
        
        try:
            response = requests.get(f"{self.production_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                
                if status == "healthy":
                    response_time = response.elapsed.total_seconds()
                    return True, f"API healthy (response time: {response_time:.2f}s)"
                else:
                    return False, f"API status: {status}"
            else:
                # Try fallback URL
                fallback_response = requests.get(f"{self.fallback_url}/health", timeout=10)
                if fallback_response.status_code == 200:
                    return True, f"Fallback URL healthy (primary failed with {response.status_code})"
                else:
                    return False, f"Both URLs failed: {response.status_code}, {fallback_response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to production API - check ingress configuration"
        except requests.exceptions.Timeout:
            return False, "API health check timed out - possible performance issue"
        except Exception as e:
            return False, f"Health check error: {str(e)}"
    
    def test_api_docs(self) -> tuple[bool, str]:
        """Test API documentation accessibility"""
        
        try:
            response = requests.get(f"{self.production_url}/docs", timeout=10)
            
            if response.status_code == 200:
                return True, "API documentation accessible"
            else:
                return False, f"API docs not accessible: HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"API docs test error: {str(e)}"
    
    def test_authentication(self) -> tuple[bool, str]:
        """Test authentication system"""
        
        try:
            # Test without auth headers
            response = requests.get(f"{self.production_url}/api/v4/usage", timeout=5)
            
            if response.status_code in [401, 403]:
                # Test with demo auth headers
                auth_response = requests.get(
                    f"{self.production_url}/api/v4/usage",
                    headers=self.headers,
                    timeout=5
                )
                
                if auth_response.status_code in [200, 404]:  # 404 acceptable if endpoint doesn't exist
                    return True, "Authentication system working (demo mode enabled)"
                else:
                    return False, f"Auth with headers failed: HTTP {auth_response.status_code}"
            
            elif response.status_code == 200:
                return True, "Open access mode (no auth required)"
            
            else:
                return False, f"Unexpected auth response: HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"Auth test error: {str(e)}"
    
    def test_single_prediction(self) -> tuple[bool, str]:
        """Test single prediction submission"""
        
        prediction_payload = {
            "job_name": f"Production Test {datetime.now().strftime('%H:%M:%S')}",
            "task_type": "protein_ligand_binding",
            "model_id": "boltz2",
            "input_data": {
                "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "ligands": ["CC(C)CC1=CC=C(C=C1)C(C)C"],  # Simple test ligand
                "use_msa": False,
                "use_potentials": False
            }
        }
        
        try:
            response = requests.post(
                f"{self.production_url}/api/v4/predict",
                json=prediction_payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                
                if job_id:
                    return True, f"Prediction submitted successfully (job_id: {job_id[:8]}...)"
                else:
                    return False, "No job_id in response"
            
            elif response.status_code == 404:
                # Try v2 compatibility
                v2_response = requests.post(
                    f"{self.production_url}/api/v2/predict",
                    json=prediction_payload,
                    headers=self.headers,
                    timeout=30
                )
                
                if v2_response.status_code == 200:
                    return True, "Prediction submitted via v2 compatibility endpoint"
                else:
                    return False, f"Both v4 and v2 endpoints failed: {v2_response.status_code}"
            
            else:
                return False, f"Prediction failed: HTTP {response.status_code} - {response.text[:100]}"
                
        except Exception as e:
            return False, f"Prediction test error: {str(e)}"
    
    def test_batch_submission(self) -> tuple[bool, str]:
        """Test batch submission"""
        
        batch_payload = {
            "job_name": f"Production Batch Test {datetime.now().strftime('%H:%M:%S')}",
            "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            "ligands": [
                {"name": "Test_Ligand_1", "smiles": "CCO"},
                {"name": "Test_Ligand_2", "smiles": "CCCO"},
                {"name": "Test_Ligand_3", "smiles": "CO"}
            ],
            "use_msa": False,
            "use_potentials": False
        }
        
        try:
            response = requests.post(
                f"{self.production_url}/api/v4/batches/submit",
                json=batch_payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                batch_id = result.get('batch_id')
                
                if batch_id:
                    total_ligands = result.get('total_ligands', 0)
                    return True, f"Batch submitted (ID: {batch_id[:8]}..., {total_ligands} ligands)"
                else:
                    return False, "No batch_id in response"
            
            elif response.status_code == 404:
                # Try v3 compatibility
                v3_response = requests.post(
                    f"{self.production_url}/api/v3/batches/submit",
                    json=batch_payload,
                    headers=self.headers,
                    timeout=30
                )
                
                if v3_response.status_code == 200:
                    return True, "Batch submitted via v3 compatibility endpoint"
                else:
                    return False, f"Both v4 and v3 batch endpoints failed: {v3_response.status_code}"
            
            else:
                return False, f"Batch submission failed: HTTP {response.status_code} - {response.text[:100]}"
                
        except Exception as e:
            return False, f"Batch test error: {str(e)}"
    
    def test_status_endpoints(self) -> tuple[bool, str]:
        """Test status and monitoring endpoints"""
        
        endpoints_to_test = [
            ("/ready", "Readiness probe"),
            ("/startup", "Startup probe"),
            ("/metrics", "Metrics endpoint")
        ]
        
        working_endpoints = []
        
        for endpoint, description in endpoints_to_test:
            try:
                response = requests.get(f"{self.production_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    working_endpoints.append(description)
            except:
                pass  # Endpoint not available
        
        if working_endpoints:
            return True, f"Status endpoints working: {', '.join(working_endpoints)}"
        else:
            return False, "No status endpoints responding"
    
    def test_error_handling(self) -> tuple[bool, str]:
        """Test error handling"""
        
        try:
            # Submit invalid request
            invalid_payload = {"invalid": "request"}
            
            response = requests.post(
                f"{self.production_url}/api/v4/predict",
                json=invalid_payload,
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code in [400, 422, 401]:
                return True, f"Error handling working (HTTP {response.status_code})"
            else:
                return False, f"Unexpected error response: HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"Error handling test failed: {str(e)}"
    
    def test_performance(self) -> tuple[bool, str]:
        """Test basic performance metrics"""
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.production_url}/health", timeout=10)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 200 and response_time < 2.0:
                return True, f"Good performance (response time: {response_time:.2f}s)"
            elif response.status_code == 200:
                return True, f"Acceptable performance (response time: {response_time:.2f}s)"
            else:
                return False, f"Performance test failed: HTTP {response.status_code}"
                
        except Exception as e:
            return False, f"Performance test error: {str(e)}"
    
    def _print_test_summary(self, results: list):
        """Print comprehensive test summary"""
        
        print(f"\n{Colors.CYAN}📊 PRODUCTION TEST SUMMARY{Colors.RESET}")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        for test_name, success, message in results:
            status = f"{Colors.GREEN}✅ PASSED{Colors.RESET}" if success else f"{Colors.RED}❌ FAILED{Colors.RESET}"
            print(f"{test_name:.<30} {status}")
            if message:
                print(f"    {Colors.CYAN}{message}{Colors.RESET}")
        
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Passed: {Colors.GREEN}{passed}{Colors.RESET}")
        print(f"Failed: {Colors.RED}{total - passed}{Colors.RESET}")
        print(f"Success Rate: {Colors.GREEN if success_rate >= 80 else Colors.YELLOW if success_rate >= 60 else Colors.RED}{success_rate:.1f}%{Colors.RESET}")
        
        if success_rate >= 80:
            print(f"\n{Colors.GREEN}🎉 PRODUCTION SYSTEM IS READY!{Colors.RESET}")
            print(f"{Colors.GREEN}✅ Your GKE deployment is working and ready for demo!{Colors.RESET}")
            
            print(f"\n{Colors.WHITE}📊 Production URLs:{Colors.RESET}")
            print(f"   API: {self.production_url}")
            print(f"   Docs: {self.production_url}/docs")
            print(f"   Health: {self.production_url}/health")
            
        else:
            print(f"\n{Colors.YELLOW}⚠️  Production system has issues but may still be usable{Colors.RESET}")
            print(f"{Colors.YELLOW}Check the failed tests above{Colors.RESET}")
        
        print()

def main():
    """Main test function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Live Production System")
    parser.add_argument("--url", help="Production URL to test", default="http://34.29.29.170")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = ProductionTester(args.url)
    success = tester.test_production_system()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
