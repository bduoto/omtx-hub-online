#!/usr/bin/env python3
"""
Chai-1 Backend Testing Suite
===========================

Comprehensive tests for Chai-1 integration in OMTX-Hub.
Tests API endpoints, Modal integration, and database operations.

Usage:
    python test_chai1.py
    python test_chai1.py --verbose
    python test_chai1.py --integration  # For full end-to-end tests
"""

import asyncio
import json
import sys
import time
import requests
import argparse
from typing import Dict, Any, Optional
from datetime import datetime


class Chai1Tester:
    """Test suite for Chai-1 backend functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages."""
        if self.verbose or level in ["ERROR", "SUCCESS", "FAIL"]:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
    
    def assert_equal(self, actual, expected, message: str = ""):
        """Assert equality with detailed error reporting."""
        if actual != expected:
            error_msg = f"Assertion failed: {message}\n  Expected: {expected}\n  Actual: {actual}"
            self.log(error_msg, "ERROR")
            return False
        return True
    
    def assert_in(self, item, container, message: str = ""):
        """Assert item in container."""
        if item not in container:
            error_msg = f"Assertion failed: {message}\n  Item '{item}' not found in {container}"
            self.log(error_msg, "ERROR")
            return False
        return True
    
    def run_test(self, test_name: str, test_func):
        """Run a single test with error handling."""
        self.log(f"Running test: {test_name}")
        start_time = time.time()
        
        try:
            success = test_func()
            duration = time.time() - start_time
            
            if success:
                self.log(f"✅ PASSED: {test_name} ({duration:.2f}s)", "SUCCESS")
                self.test_results.append({"test": test_name, "status": "PASSED", "duration": duration})
            else:
                self.log(f"❌ FAILED: {test_name} ({duration:.2f}s)", "FAIL")
                self.test_results.append({"test": test_name, "status": "FAILED", "duration": duration})
                
        except Exception as e:
            duration = time.time() - start_time
            self.log(f"💥 ERROR: {test_name} - {str(e)} ({duration:.2f}s)", "ERROR")
            self.test_results.append({"test": test_name, "status": "ERROR", "duration": duration, "error": str(e)})
    
    def test_backend_health(self) -> bool:
        """Test that the backend is running and healthy."""
        self.log("Testing backend health...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if not self.assert_equal(response.status_code, 200, "Health endpoint status code"):
                return False
                
            data = response.json()
            
            required_fields = ["status", "timestamp", "database", "storage"]
            for field in required_fields:
                if not self.assert_in(field, data, f"Health response missing field: {field}"):
                    return False
            
            if not self.assert_equal(data["status"], "healthy", "Backend health status"):
                return False
                
            self.log("Backend is healthy and accessible")
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"Cannot reach backend at {self.base_url}: {e}", "ERROR")
            return False
    
    def test_chai1_health(self) -> bool:
        """Test Chai-1 specific health endpoint."""
        self.log("Testing Chai-1 health endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/api/v2/models/chai1/health", timeout=30)
            
            if not self.assert_equal(response.status_code, 200, "Chai-1 health endpoint status"):
                return False
                
            data = response.json()
            
            required_fields = ["status", "model", "modal_app"]
            for field in required_fields:
                if not self.assert_in(field, data, f"Chai-1 health missing field: {field}"):
                    return False
            
            if not self.assert_equal(data["model"], "chai1", "Model name in health response"):
                return False
                
            if not self.assert_equal(data["modal_app"], "omtx-hub-chai1", "Modal app name"):
                return False
            
            self.log(f"Chai-1 health status: {data.get('status')}")
            return True
            
        except requests.exceptions.Timeout:
            self.log("Chai-1 health check timed out (Modal loading issue?)", "ERROR")
            return False
        except requests.exceptions.RequestException as e:
            self.log(f"Chai-1 health check failed: {e}", "ERROR")
            return False
    
    def test_fasta_validation(self) -> bool:
        """Test FASTA input validation."""
        self.log("Testing FASTA validation...")
        
        # Test invalid FASTA (no header)
        invalid_fasta = "MGSSHHHHHHSSGLVPRGSHMASMTGGQQMGRGS"
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": invalid_fasta,
                "num_samples": 1,
                "job_name": "Invalid FASTA Test"
            },
            timeout=10
        )
        
        if not self.assert_equal(response.status_code, 422, "Invalid FASTA should return validation error"):
            return False
        
        # Test empty FASTA
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": "",
                "num_samples": 1,
                "job_name": "Empty FASTA Test"
            },
            timeout=10
        )
        
        if not self.assert_equal(response.status_code, 422, "Empty FASTA should return validation error"):
            return False
        
        self.log("FASTA validation working correctly")
        return True
    
    def test_prediction_submission(self) -> bool:
        """Test successful prediction job submission."""
        self.log("Testing prediction job submission...")
        
        valid_fasta = ">Test_Protein\nMGSSHHHHHHSSGLVPRGSHMASMTGGQQMGRGS"
        
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": valid_fasta,
                "num_samples": 2,
                "use_msa": False,
                "use_templates": False,
                "job_name": "Test Chai-1 Prediction"
            },
            timeout=30
        )
        
        if not self.assert_equal(response.status_code, 200, "Prediction submission status"):
            self.log(f"Response: {response.text}", "ERROR")
            return False
        
        data = response.json()
        
        required_fields = ["job_id", "status", "message", "estimated_time"]
        for field in required_fields:
            if not self.assert_in(field, data, f"Prediction response missing field: {field}"):
                return False
        
        if not self.assert_equal(data["status"], "pending", "Job initial status"):
            return False
        
        # Validate job_id format (UUID)
        job_id = data["job_id"]
        if len(job_id) != 36 or job_id.count('-') != 4:
            self.log(f"Invalid job_id format: {job_id}", "ERROR")
            return False
        
        self.log(f"Job submitted successfully with ID: {job_id}")
        self.last_job_id = job_id  # Store for other tests
        return True
    
    def test_job_status_polling(self) -> bool:
        """Test job status polling endpoint."""
        if not hasattr(self, 'last_job_id'):
            self.log("No job_id from previous test, skipping status polling", "ERROR")
            return False
        
        self.log(f"Testing job status polling for {self.last_job_id}...")
        
        response = requests.get(
            f"{self.base_url}/api/v2/jobs/{self.last_job_id}",
            timeout=10
        )
        
        if not self.assert_equal(response.status_code, 200, "Job status endpoint"):
            return False
        
        data = response.json()
        
        required_fields = ["job_id", "status", "model_name", "task_type"]
        for field in required_fields:
            if not self.assert_in(field, data, f"Job status missing field: {field}"):
                return False
        
        if not self.assert_equal(data["job_id"], self.last_job_id, "Job ID matches"):
            return False
        
        if not self.assert_equal(data["model_name"], "chai1", "Model name in job status"):
            return False
        
        expected_status = ["pending", "running", "completed", "failed"]
        if not self.assert_in(data["status"], expected_status, "Job status is valid"):
            return False
        
        self.log(f"Job status: {data['status']}")
        return True
    
    def test_parameter_validation(self) -> bool:
        """Test parameter validation and edge cases."""
        self.log("Testing parameter validation...")
        
        valid_fasta = ">Test\nMGSS"
        
        # Test num_samples validation (too high)
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": valid_fasta,
                "num_samples": 15,  # Max is 10
                "job_name": "Invalid num_samples"
            },
            timeout=10
        )
        
        if not self.assert_equal(response.status_code, 422, "High num_samples should be rejected"):
            return False
        
        # Test num_samples validation (too low)
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": valid_fasta,
                "num_samples": 0,  # Min is 1
                "job_name": "Invalid num_samples"
            },
            timeout=10
        )
        
        if not self.assert_equal(response.status_code, 422, "Low num_samples should be rejected"):
            return False
        
        # Test missing required fields
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": valid_fasta,
                # Missing job_name
                "num_samples": 1
            },
            timeout=10
        )
        
        if not self.assert_equal(response.status_code, 422, "Missing job_name should be rejected"):
            return False
        
        self.log("Parameter validation working correctly")
        return True
    
    def test_multi_sequence_fasta(self) -> bool:
        """Test handling of multi-sequence FASTA."""
        self.log("Testing multi-sequence FASTA...")
        
        multi_fasta = """>Protein1
MGSSHHHHHHSSGLVPRGSH
>DNA|DNA
ATCGATCG
>Ligand|SMILES
CCO"""
        
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": multi_fasta,
                "num_samples": 1,
                "job_name": "Multi-sequence Test"
            },
            timeout=30
        )
        
        if not self.assert_equal(response.status_code, 200, "Multi-sequence FASTA submission"):
            self.log(f"Response: {response.text}", "ERROR")
            return False
        
        data = response.json()
        if not self.assert_equal(data["status"], "pending", "Multi-sequence job status"):
            return False
        
        self.log("Multi-sequence FASTA handled successfully")
        return True
    
    def test_integration_modal_connection(self) -> bool:
        """Test end-to-end Modal integration (integration test only)."""
        self.log("Testing Modal integration (this may take several minutes)...")
        
        # Simple protein for faster testing
        test_fasta = ">Test_Small_Protein\nMGSS"
        
        response = requests.post(
            f"{self.base_url}/api/v2/models/chai1/predict",
            json={
                "fasta_content": test_fasta,
                "num_samples": 1,
                "use_msa": False,
                "use_templates": False,
                "job_name": "Modal Integration Test"
            },
            timeout=30
        )
        
        if response.status_code != 200:
            self.log(f"Job submission failed: {response.text}", "ERROR")
            return False
        
        job_id = response.json()["job_id"]
        self.log(f"Submitted job {job_id}, waiting for Modal processing...")
        
        # Poll for completion (up to 10 minutes)
        max_polls = 60  # 10 minutes with 10-second intervals
        poll_count = 0
        
        while poll_count < max_polls:
            time.sleep(10)
            poll_count += 1
            
            response = requests.get(f"{self.base_url}/api/v2/jobs/{job_id}", timeout=10)
            if response.status_code != 200:
                self.log(f"Status polling failed: {response.text}", "ERROR")
                return False
            
            data = response.json()
            status = data["status"]
            
            self.log(f"Poll {poll_count}: Job status = {status}")
            
            if status == "completed":
                self.log("✅ Modal integration successful - job completed!")
                
                # Validate result structure
                if "result_data" in data and "structures" in data["result_data"]:
                    num_structures = len(data["result_data"]["structures"])
                    self.log(f"Generated {num_structures} structure(s)")
                    return True
                else:
                    self.log("Job completed but missing structure results", "ERROR")
                    return False
                    
            elif status == "failed":
                error_msg = data.get("error_message", "Unknown error")
                self.log(f"❌ Job failed: {error_msg}", "ERROR")
                return False
        
        self.log(f"❌ Job did not complete within {max_polls * 10} seconds", "ERROR")
        return False
    
    def run_all_tests(self, include_integration: bool = False):
        """Run all test suites."""
        self.log("=" * 50)
        self.log("Starting Chai-1 Backend Test Suite")
        self.log("=" * 50)
        
        # Basic functionality tests
        basic_tests = [
            ("Backend Health Check", self.test_backend_health),
            ("Chai-1 Health Check", self.test_chai1_health),
            ("FASTA Validation", self.test_fasta_validation),
            ("Prediction Submission", self.test_prediction_submission),
            ("Job Status Polling", self.test_job_status_polling),
            ("Parameter Validation", self.test_parameter_validation),
            ("Multi-sequence FASTA", self.test_multi_sequence_fasta),
        ]
        
        for test_name, test_func in basic_tests:
            self.run_test(test_name, test_func)
        
        # Integration tests (optional, slow)
        if include_integration:
            self.log("\n" + "=" * 50)
            self.log("Running Integration Tests (may take 10+ minutes)")
            self.log("=" * 50)
            
            integration_tests = [
                ("Modal Integration End-to-End", self.test_integration_modal_connection),
            ]
            
            for test_name, test_func in integration_tests:
                self.run_test(test_name, test_func)
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary."""
        self.log("\n" + "=" * 50)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 50)
        
        passed = len([r for r in self.test_results if r["status"] == "PASSED"])
        failed = len([r for r in self.test_results if r["status"] == "FAILED"])
        errors = len([r for r in self.test_results if r["status"] == "ERROR"])
        total = len(self.test_results)
        
        self.log(f"Total Tests: {total}")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"💥 Errors: {errors}")
        
        if failed > 0 or errors > 0:
            self.log("\nFailed/Error Tests:")
            for result in self.test_results:
                if result["status"] in ["FAILED", "ERROR"]:
                    error_info = f" - {result.get('error', '')}" if result.get('error') else ""
                    self.log(f"  {result['status']}: {result['test']}{error_info}")
        
        total_time = sum(r["duration"] for r in self.test_results)
        self.log(f"\nTotal execution time: {total_time:.2f} seconds")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        self.log(f"Success rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            self.log("\n🎉 All tests passed! Chai-1 backend is ready for production.")
        elif success_rate >= 80:
            self.log("\n⚠️ Most tests passed, but some issues need attention.")
        else:
            self.log("\n🚨 Multiple test failures - backend needs fixes before deployment.")


def main():
    parser = argparse.ArgumentParser(description="Test Chai-1 backend functionality")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--integration", "-i", action="store_true", help="Run integration tests (slow)")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    
    args = parser.parse_args()
    
    tester = Chai1Tester(base_url=args.url, verbose=args.verbose)
    tester.run_all_tests(include_integration=args.integration)
    
    # Exit with error code if tests failed
    failed_tests = len([r for r in tester.test_results if r["status"] in ["FAILED", "ERROR"]])
    sys.exit(1 if failed_tests > 0 else 0)


if __name__ == "__main__":
    main()