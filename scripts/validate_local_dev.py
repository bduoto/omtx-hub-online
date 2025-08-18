#!/usr/bin/env python3
"""
Local Development Environment Validation Script
Tests all critical components of the OMTX-Hub development setup
"""

import asyncio
import httpx
import json
import time
import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_name: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0

class LocalDevValidator:
    """Validates local development environment"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:8081"
        self.results: List[ValidationResult] = []
    
    async def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print("🔍 Validating OMTX-Hub Local Development Environment")
        print("=" * 60)
        
        tests = [
            self.test_backend_health,
            self.test_frontend_availability,
            self.test_api_endpoints,
            self.test_database_connection,
            self.test_modal_integration,
            self.test_gcp_services,
            self.test_production_services,
            self.test_webhook_handlers,
        ]
        
        for test in tests:
            try:
                start_time = time.time()
                result = await test()
                duration = (time.time() - start_time) * 1000
                result.duration_ms = duration
                self.results.append(result)
                
                status = "✅" if result.success else "❌"
                print(f"{status} {result.test_name}: {result.message} ({duration:.1f}ms)")
                
                if result.details:
                    for key, value in result.details.items():
                        print(f"   {key}: {value}")
                        
            except Exception as e:
                error_result = ValidationResult(
                    test_name=test.__name__,
                    success=False,
                    message=f"Test failed with exception: {str(e)}",
                    duration_ms=(time.time() - start_time) * 1000
                )
                self.results.append(error_result)
                print(f"❌ {test.__name__}: {str(e)}")
        
        # Print summary
        self.print_summary()
        
        # Return overall success
        return all(result.success for result in self.results)
    
    async def test_backend_health(self) -> ValidationResult:
        """Test backend health endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/health", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return ValidationResult(
                        test_name="Backend Health Check",
                        success=True,
                        message="Backend is healthy and responding",
                        details={
                            "status": data.get("status"),
                            "version": data.get("version", "unknown"),
                            "uptime": data.get("uptime", "unknown")
                        }
                    )
                else:
                    return ValidationResult(
                        test_name="Backend Health Check",
                        success=False,
                        message=f"Backend returned status {response.status_code}"
                    )
                    
        except httpx.ConnectError:
            return ValidationResult(
                test_name="Backend Health Check",
                success=False,
                message="Cannot connect to backend - is it running on port 8000?"
            )
    
    async def test_frontend_availability(self) -> ValidationResult:
        """Test frontend availability"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.frontend_url}", timeout=10.0)
                
                if response.status_code == 200:
                    return ValidationResult(
                        test_name="Frontend Availability",
                        success=True,
                        message="Frontend is accessible and serving content"
                    )
                else:
                    return ValidationResult(
                        test_name="Frontend Availability",
                        success=False,
                        message=f"Frontend returned status {response.status_code}"
                    )
                    
        except httpx.ConnectError:
            return ValidationResult(
                test_name="Frontend Availability",
                success=False,
                message="Cannot connect to frontend - is it running on port 8081?"
            )
    
    async def test_api_endpoints(self) -> ValidationResult:
        """Test critical API endpoints"""
        try:
            async with httpx.AsyncClient() as client:
                # Test unified endpoints
                response = await client.get(f"{self.backend_url}/api/v2/models", timeout=10.0)
                models_ok = response.status_code == 200
                
                # Test batch API
                response = await client.get(f"{self.backend_url}/api/v3/batches/", timeout=10.0)
                batches_ok = response.status_code in [200, 422]  # 422 is OK for missing user_id
                
                # Test results API
                response = await client.get(f"{self.backend_url}/api/v2/results/ultra-fast", timeout=10.0)
                results_ok = response.status_code in [200, 422]  # 422 is OK for missing user_id
                
                success = models_ok and batches_ok and results_ok
                
                return ValidationResult(
                    test_name="API Endpoints",
                    success=success,
                    message="All critical API endpoints are responding" if success else "Some API endpoints are not responding",
                    details={
                        "models_endpoint": "✅" if models_ok else "❌",
                        "batches_endpoint": "✅" if batches_ok else "❌",
                        "results_endpoint": "✅" if results_ok else "❌"
                    }
                )
                
        except Exception as e:
            return ValidationResult(
                test_name="API Endpoints",
                success=False,
                message=f"API endpoint test failed: {str(e)}"
            )
    
    async def test_database_connection(self) -> ValidationResult:
        """Test database connectivity"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/api/system/status", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    db_status = data.get("database", {})
                    
                    return ValidationResult(
                        test_name="Database Connection",
                        success=db_status.get("available", False),
                        message="Database connection is working" if db_status.get("available") else "Database connection failed",
                        details={
                            "firestore_available": db_status.get("available", False),
                            "connection_type": db_status.get("type", "unknown")
                        }
                    )
                else:
                    return ValidationResult(
                        test_name="Database Connection",
                        success=False,
                        message="Cannot get database status"
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="Database Connection",
                success=False,
                message=f"Database test failed: {str(e)}"
            )
    
    async def test_modal_integration(self) -> ValidationResult:
        """Test Modal integration"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/api/system/status", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    modal_status = data.get("modal", {})
                    
                    return ValidationResult(
                        test_name="Modal Integration",
                        success=modal_status.get("available", False),
                        message="Modal integration is working" if modal_status.get("available") else "Modal integration not available",
                        details={
                            "modal_available": modal_status.get("available", False),
                            "functions_loaded": modal_status.get("functions_loaded", 0)
                        }
                    )
                else:
                    return ValidationResult(
                        test_name="Modal Integration",
                        success=False,
                        message="Cannot get Modal status"
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="Modal Integration",
                success=False,
                message=f"Modal test failed: {str(e)}"
            )
    
    async def test_gcp_services(self) -> ValidationResult:
        """Test GCP services"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/api/system/status", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    storage_status = data.get("storage", {})
                    
                    return ValidationResult(
                        test_name="GCP Services",
                        success=storage_status.get("available", False),
                        message="GCP services are working" if storage_status.get("available") else "GCP services not available",
                        details={
                            "storage_available": storage_status.get("available", False),
                            "bucket_name": storage_status.get("bucket_name", "unknown")
                        }
                    )
                else:
                    return ValidationResult(
                        test_name="GCP Services",
                        success=False,
                        message="Cannot get GCP status"
                    )
                    
        except Exception as e:
            return ValidationResult(
                test_name="GCP Services",
                success=False,
                message=f"GCP test failed: {str(e)}"
            )
    
    async def test_production_services(self) -> ValidationResult:
        """Test production services availability"""
        services_to_test = [
            "production_modal_service",
            "atomic_storage_service", 
            "smart_job_router",
            "webhook_completion_checker"
        ]
        
        available_services = []
        
        for service in services_to_test:
            try:
                # Try to import the service
                if service == "production_modal_service":
                    from backend.services.production_modal_service import production_modal_service
                    available_services.append(service)
                elif service == "atomic_storage_service":
                    from backend.services.atomic_storage_service import atomic_storage_service
                    available_services.append(service)
                elif service == "smart_job_router":
                    from backend.services.smart_job_router import smart_job_router
                    available_services.append(service)
                elif service == "webhook_completion_checker":
                    from backend.services.webhook_completion_checker import WebhookCompletionChecker
                    available_services.append(service)
            except ImportError:
                pass
        
        success = len(available_services) == len(services_to_test)
        
        return ValidationResult(
            test_name="Production Services",
            success=success,
            message=f"{len(available_services)}/{len(services_to_test)} production services available",
            details={
                "available_services": available_services,
                "missing_services": [s for s in services_to_test if s not in available_services]
            }
        )
    
    async def test_webhook_handlers(self) -> ValidationResult:
        """Test webhook handlers"""
        try:
            async with httpx.AsyncClient() as client:
                # Test webhook endpoint exists (should return 405 for GET)
                response = await client.get(f"{self.backend_url}/api/v3/webhooks/modal/completion", timeout=10.0)
                
                # 405 Method Not Allowed is expected for GET on POST endpoint
                success = response.status_code == 405
                
                return ValidationResult(
                    test_name="Webhook Handlers",
                    success=success,
                    message="Webhook endpoints are configured" if success else "Webhook endpoints not found",
                    details={
                        "webhook_endpoint_status": response.status_code
                    }
                )
                
        except Exception as e:
            return ValidationResult(
                test_name="Webhook Handlers",
                success=False,
                message=f"Webhook test failed: {str(e)}"
            )
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔧 FAILED TESTS:")
            for result in self.results:
                if not result.success:
                    print(f"   ❌ {result.test_name}: {result.message}")
        
        print("\n🎯 NEXT STEPS:")
        if failed_tests == 0:
            print("   ✅ All tests passed! Your development environment is ready.")
            print("   🚀 You can now run: ./start_dev.sh")
        else:
            print("   🔧 Fix the failed tests above")
            print("   📖 Check the setup documentation")
            print("   🆘 Run with --help for troubleshooting")

async def main():
    """Main validation function"""
    validator = LocalDevValidator()
    success = await validator.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
