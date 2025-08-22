#!/usr/bin/env python3
"""
End-to-End Testing for Individual Boltz-2 Prediction Jobs
Tests the complete workflow: API → Cloud Tasks → Cloud Run GPU → Results
"""

import os
import sys
import time
import json
import asyncio
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.logging_service import RequestLoggingContext
import logging

logger = logging.getLogger(__name__)

class JobTestRunner:
    """End-to-end test runner for individual jobs"""
    
    def __init__(self, base_url: str = "http://34.29.29.170"):
        self.base_url = base_url.rstrip('/')
        self.auth_token = None
        self.test_results = {
            "start_time": datetime.utcnow().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
    
    def log_test_result(self, test_name: str, status: str, message: str, details: Optional[Dict] = None):
        """Log test result"""
        result = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        
        self.test_results["tests"].append(result)
        self.test_results["summary"]["total"] += 1
        self.test_results["summary"][status] += 1
        
        status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}
        print(f"{status_emoji.get(status, '?')} {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    async def test_health_check(self):
        """Test 1: Basic health check"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                self.log_test_result(
                    "Health Check",
                    "passed",
                    "API is healthy and responding",
                    {
                        "response_time": f"{response.elapsed.total_seconds():.3f}s",
                        "status": health_data.get("status", "unknown"),
                        "message": health_data.get("message", "")
                    }
                )
                return True
            else:
                self.log_test_result(
                    "Health Check",
                    "failed",
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Health Check",
                "failed",
                f"Health check exception: {e}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_authentication(self):
        """Test 2: Authentication flow"""
        try:
            # Try to access protected endpoint without auth
            response = requests.get(f"{self.base_url}/api/v1/jobs", timeout=10)
            
            if response.status_code == 401:
                self.log_test_result(
                    "Authentication Required",
                    "passed",
                    "API correctly requires authentication",
                    {"status_code": response.status_code}
                )
            else:
                self.log_test_result(
                    "Authentication Required",
                    "failed",
                    f"Expected 401, got {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
            
            # Test development mode token creation (if available)
            try:
                from auth.jwt_auth import create_user_token
                self.auth_token = create_user_token("test_user", "test@omtx.ai")
                
                self.log_test_result(
                    "Token Generation",
                    "passed",
                    "Successfully generated test token",
                    {"token_length": len(self.auth_token)}
                )
                return True
                
            except Exception as e:
                self.log_test_result(
                    "Token Generation",
                    "failed",
                    f"Failed to generate token: {e}",
                    {"error_type": type(e).__name__}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Authentication Test",
                "failed",
                f"Authentication test exception: {e}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_metrics_endpoint(self):
        """Test 3: Prometheus metrics endpoint"""
        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for key metrics
                expected_metrics = [
                    "http_requests_total",
                    "omtx_hub_active_jobs",
                    "omtx_hub_app_info"
                ]
                
                found_metrics = []
                for metric in expected_metrics:
                    if metric in metrics_text:
                        found_metrics.append(metric)
                
                self.log_test_result(
                    "Metrics Endpoint",
                    "passed",
                    f"Metrics endpoint responding with {len(found_metrics)}/{len(expected_metrics)} expected metrics",
                    {
                        "found_metrics": found_metrics,
                        "metrics_size": f"{len(metrics_text)} bytes"
                    }
                )
                return True
            else:
                self.log_test_result(
                    "Metrics Endpoint",
                    "failed",
                    f"Metrics endpoint returned {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Metrics Endpoint",
                "failed",
                f"Metrics endpoint exception: {e}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_job_submission(self):
        """Test 4: Job submission to Cloud Tasks"""
        if not self.auth_token:
            self.log_test_result(
                "Job Submission",
                "skipped",
                "Skipped due to missing authentication token",
                {}
            )
            return False
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}"
            }
            
            job_payload = {
                "model": "boltz2",
                "protein_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "ligand_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "job_name": "E2E Test - Aspirin-Protein Complex",
                "parameters": {
                    "confidence_threshold": 0.7,
                    "test_mode": True
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/predict",
                headers=headers,
                json=job_payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                job_data = response.json()
                job_id = job_data.get("job_id")
                
                if job_id:
                    self.log_test_result(
                        "Job Submission",
                        "passed",
                        f"Successfully submitted job to Cloud Tasks",
                        {
                            "job_id": job_id,
                            "status": job_data.get("status"),
                            "model": job_data.get("model"),
                            "response_time": f"{response.elapsed.total_seconds():.3f}s"
                        }
                    )
                    return job_id
                else:
                    self.log_test_result(
                        "Job Submission",
                        "failed",
                        "Job submitted but no job_id returned",
                        {"response": job_data}
                    )
                    return False
            else:
                self.log_test_result(
                    "Job Submission",
                    "failed",
                    f"Job submission failed with status {response.status_code}",
                    {"response": response.text[:500]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Job Submission",
                "failed",
                f"Job submission exception: {e}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_job_status_monitoring(self, job_id: str, timeout_minutes: int = 10):
        """Test 5: Job status monitoring and completion"""
        if not job_id:
            self.log_test_result(
                "Job Status Monitoring",
                "skipped",
                "Skipped due to no job ID",
                {}
            )
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            start_time = time.time()
            timeout_seconds = timeout_minutes * 60
            last_status = None
            status_changes = []
            
            while time.time() - start_time < timeout_seconds:
                response = requests.get(
                    f"{self.base_url}/api/v1/jobs/{job_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    job_data = response.json()
                    current_status = job_data.get("status")
                    
                    if current_status != last_status:
                        status_changes.append({
                            "status": current_status,
                            "timestamp": datetime.utcnow().isoformat(),
                            "elapsed": f"{time.time() - start_time:.1f}s"
                        })
                        print(f"   Job {job_id} status: {current_status}")
                        last_status = current_status
                    
                    if current_status == "completed":
                        self.log_test_result(
                            "Job Status Monitoring",
                            "passed",
                            f"Job completed successfully in {time.time() - start_time:.1f}s",
                            {
                                "job_id": job_id,
                                "final_status": current_status,
                                "status_changes": status_changes,
                                "total_time": f"{time.time() - start_time:.1f}s"
                            }
                        )
                        return job_data
                    elif current_status == "failed":
                        self.log_test_result(
                            "Job Status Monitoring",
                            "failed",
                            f"Job failed after {time.time() - start_time:.1f}s",
                            {
                                "job_id": job_id,
                                "final_status": current_status,
                                "error": job_data.get("error_message"),
                                "status_changes": status_changes
                            }
                        )
                        return False
                else:
                    print(f"   Status check failed: {response.status_code}")
                
                await asyncio.sleep(5)  # Check every 5 seconds
            
            # Timeout reached
            self.log_test_result(
                "Job Status Monitoring",
                "failed",
                f"Job did not complete within {timeout_minutes} minutes",
                {
                    "job_id": job_id,
                    "last_status": last_status,
                    "status_changes": status_changes,
                    "timeout": f"{timeout_minutes} minutes"
                }
            )
            return False
            
        except Exception as e:
            self.log_test_result(
                "Job Status Monitoring",
                "failed",
                f"Job status monitoring exception: {e}",
                {"error_type": type(e).__name__, "job_id": job_id}
            )
            return False
    
    async def test_results_retrieval(self, job_data: Dict[str, Any]):
        """Test 6: Results retrieval and validation"""
        if not job_data:
            self.log_test_result(
                "Results Retrieval",
                "skipped",
                "Skipped due to no completed job data",
                {}
            )
            return False
        
        try:
            job_id = job_data.get("job_id")
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Get results
            response = requests.get(
                f"{self.base_url}/api/v1/jobs/{job_id}/results",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                
                # Validate results structure
                expected_fields = ["status", "results"]
                found_fields = [field for field in expected_fields if field in results]
                
                self.log_test_result(
                    "Results Retrieval",
                    "passed",
                    f"Successfully retrieved results with {len(found_fields)}/{len(expected_fields)} expected fields",
                    {
                        "job_id": job_id,
                        "found_fields": found_fields,
                        "results_size": len(str(results)),
                        "has_download_links": "download_links" in results
                    }
                )
                return True
            else:
                self.log_test_result(
                    "Results Retrieval",
                    "failed",
                    f"Results retrieval failed with status {response.status_code}",
                    {"job_id": job_id, "response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Results Retrieval",
                "failed",
                f"Results retrieval exception: {e}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def test_webhook_system(self):
        """Test 7: Webhook system functionality"""
        if not self.auth_token:
            self.log_test_result(
                "Webhook System",
                "skipped",
                "Skipped due to missing authentication token",
                {}
            )
            return False
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}"
            }
            
            # List webhook events
            response = requests.get(
                f"{self.base_url}/api/v1/webhooks/events",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get("events", [])
                
                self.log_test_result(
                    "Webhook System",
                    "passed",
                    f"Webhook system responding with {len(events)} available events",
                    {
                        "available_events": [e.get("name") for e in events],
                        "signature_info": events_data.get("signature_info", {})
                    }
                )
                return True
            else:
                self.log_test_result(
                    "Webhook System",
                    "failed",
                    f"Webhook events endpoint returned {response.status_code}",
                    {"response": response.text[:200]}
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "Webhook System",
                "failed",
                f"Webhook system test exception: {e}",
                {"error_type": type(e).__name__}
            )
            return False
    
    async def run_all_tests(self):
        """Run complete end-to-end test suite"""
        print("🚀 Starting End-to-End Individual Job Testing")
        print(f"   Target: {self.base_url}")
        print(f"   Time: {datetime.utcnow().isoformat()}")
        print("")
        
        # Test 1: Health Check
        health_ok = await self.test_health_check()
        if not health_ok:
            print("❌ Cannot proceed without healthy API")
            return self.test_results
        
        # Test 2: Authentication
        auth_ok = await self.test_authentication()
        
        # Test 3: Metrics
        await self.test_metrics_endpoint()
        
        # Test 4: Job Submission
        job_id = await self.test_job_submission()
        
        # Test 5: Job Status Monitoring
        job_data = None
        if job_id:
            job_data = await self.test_job_status_monitoring(job_id)
        
        # Test 6: Results Retrieval
        if job_data:
            await self.test_results_retrieval(job_data)
        
        # Test 7: Webhook System
        await self.test_webhook_system()
        
        # Summary
        print("")
        print("📊 Test Summary:")
        summary = self.test_results["summary"]
        print(f"   Total: {summary['total']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⏭️ Skipped: {summary['skipped']}")
        
        success_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
        print(f"   Success Rate: {success_rate:.1f}%")
        
        self.test_results["end_time"] = datetime.utcnow().isoformat()
        self.test_results["success_rate"] = success_rate
        
        return self.test_results

async def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="End-to-End Individual Job Testing")
    parser.add_argument("--url", default="http://34.29.29.170", help="Base URL for testing")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    args = parser.parse_args()
    
    runner = JobTestRunner(args.url)
    results = await runner.run_all_tests()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Test results saved to: {args.output}")
    
    # Exit with error code if tests failed
    if results["summary"]["failed"] > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())