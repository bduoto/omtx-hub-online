#!/usr/bin/env python3
"""
Production Deployment Validation Script
Validates production deployment with comprehensive checks
"""

import asyncio
import httpx
import json
import time
import sys
import os
import subprocess
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import argparse

@dataclass
class DeploymentCheck:
    """Result of a deployment validation check"""
    check_name: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    critical: bool = True  # Whether failure should block deployment

class ProductionDeploymentValidator:
    """Validates production deployment readiness"""
    
    def __init__(self, base_url: str, environment: str = "staging"):
        self.base_url = base_url.rstrip('/')
        self.environment = environment
        self.results: List[DeploymentCheck] = []
    
    async def run_all_checks(self) -> bool:
        """Run all deployment validation checks"""
        print(f"🔍 Validating {self.environment.upper()} Deployment: {self.base_url}")
        print("=" * 80)
        
        checks = [
            self.check_basic_connectivity,
            self.check_health_endpoints,
            self.check_authentication_security,
            self.check_api_functionality,
            self.check_database_connectivity,
            self.check_storage_integration,
            self.check_modal_integration,
            self.check_webhook_security,
            self.check_rate_limiting,
            self.check_monitoring_endpoints,
            self.check_error_handling,
            self.check_performance_baseline,
            self.check_security_headers,
            self.check_ssl_configuration,
            self.check_kubernetes_health,
        ]
        
        for check in checks:
            try:
                start_time = time.time()
                result = await check()
                duration = (time.time() - start_time) * 1000
                
                self.results.append(result)
                
                status = "✅" if result.success else ("❌" if result.critical else "⚠️")
                criticality = " (CRITICAL)" if result.critical and not result.success else ""
                print(f"{status} {result.check_name}: {result.message}{criticality} ({duration:.1f}ms)")
                
                if result.details:
                    for key, value in result.details.items():
                        print(f"   {key}: {value}")
                        
            except Exception as e:
                error_result = DeploymentCheck(
                    check_name=check.__name__,
                    success=False,
                    message=f"Check failed with exception: {str(e)}",
                    critical=True
                )
                self.results.append(error_result)
                print(f"❌ {check.__name__}: {str(e)} (CRITICAL)")
        
        # Print summary
        self.print_summary()
        
        # Return deployment readiness
        critical_failures = [r for r in self.results if not r.success and r.critical]
        return len(critical_failures) == 0
    
    async def check_basic_connectivity(self) -> DeploymentCheck:
        """Test basic connectivity to the deployment"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    return DeploymentCheck(
                        check_name="Basic Connectivity",
                        success=True,
                        message="Deployment is accessible",
                        details={"response_time_ms": response.elapsed.total_seconds() * 1000}
                    )
                else:
                    return DeploymentCheck(
                        check_name="Basic Connectivity",
                        success=False,
                        message=f"Health endpoint returned {response.status_code}",
                        critical=True
                    )
                    
        except httpx.ConnectError:
            return DeploymentCheck(
                check_name="Basic Connectivity",
                success=False,
                message="Cannot connect to deployment URL",
                critical=True
            )
        except Exception as e:
            return DeploymentCheck(
                check_name="Basic Connectivity",
                success=False,
                message=f"Connection error: {str(e)}",
                critical=True
            )
    
    async def check_health_endpoints(self) -> DeploymentCheck:
        """Test health and status endpoints"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test main health endpoint
                health_response = await client.get(f"{self.base_url}/health")
                health_ok = health_response.status_code == 200
                
                # Test system status endpoint
                status_response = await client.get(f"{self.base_url}/api/system/status")
                status_ok = status_response.status_code == 200
                
                if health_ok and status_ok:
                    health_data = health_response.json()
                    status_data = status_response.json()
                    
                    return DeploymentCheck(
                        check_name="Health Endpoints",
                        success=True,
                        message="All health endpoints responding",
                        details={
                            "health_status": health_data.get("status"),
                            "uptime": health_data.get("uptime"),
                            "services_available": len([k for k, v in status_data.items() if isinstance(v, dict) and v.get("available")])
                        }
                    )
                else:
                    return DeploymentCheck(
                        check_name="Health Endpoints",
                        success=False,
                        message=f"Health endpoints failing: health={health_response.status_code}, status={status_response.status_code}",
                        critical=True
                    )
                    
        except Exception as e:
            return DeploymentCheck(
                check_name="Health Endpoints",
                success=False,
                message=f"Health check failed: {str(e)}",
                critical=True
            )
    
    async def check_authentication_security(self) -> DeploymentCheck:
        """Test authentication and security measures"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test that protected endpoints require authentication
                protected_endpoints = [
                    "/api/v3/batches/",
                    "/api/v2/results/ultra-fast"
                ]
                
                auth_working = True
                for endpoint in protected_endpoints:
                    response = await client.get(f"{self.base_url}{endpoint}")
                    # Should return 401/403 (unauthorized) or 422 (missing user_id)
                    if response.status_code not in [401, 403, 422]:
                        auth_working = False
                        break
                
                return DeploymentCheck(
                    check_name="Authentication Security",
                    success=auth_working,
                    message="Authentication properly enforced" if auth_working else "Authentication may be bypassed",
                    critical=True
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="Authentication Security",
                success=False,
                message=f"Auth check failed: {str(e)}",
                critical=True
            )
    
    async def check_api_functionality(self) -> DeploymentCheck:
        """Test core API functionality"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test models endpoint
                models_response = await client.get(f"{self.base_url}/api/v2/models")
                models_ok = models_response.status_code == 200
                
                # Test API documentation
                docs_response = await client.get(f"{self.base_url}/docs")
                docs_ok = docs_response.status_code == 200
                
                success = models_ok and docs_ok
                
                return DeploymentCheck(
                    check_name="API Functionality",
                    success=success,
                    message="Core APIs functioning" if success else "Some APIs not responding",
                    details={
                        "models_endpoint": "✅" if models_ok else "❌",
                        "docs_endpoint": "✅" if docs_ok else "❌"
                    },
                    critical=True
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="API Functionality",
                success=False,
                message=f"API test failed: {str(e)}",
                critical=True
            )
    
    async def check_database_connectivity(self) -> DeploymentCheck:
        """Test database connectivity"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/system/status")
                
                if response.status_code == 200:
                    status_data = response.json()
                    db_status = status_data.get("database", {})
                    db_available = db_status.get("available", False)
                    
                    return DeploymentCheck(
                        check_name="Database Connectivity",
                        success=db_available,
                        message="Database connected" if db_available else "Database not available",
                        details={
                            "database_type": db_status.get("type", "unknown"),
                            "connection_pool": db_status.get("connection_pool", "unknown")
                        },
                        critical=True
                    )
                else:
                    return DeploymentCheck(
                        check_name="Database Connectivity",
                        success=False,
                        message="Cannot get database status",
                        critical=True
                    )
                    
        except Exception as e:
            return DeploymentCheck(
                check_name="Database Connectivity",
                success=False,
                message=f"Database check failed: {str(e)}",
                critical=True
            )
    
    async def check_storage_integration(self) -> DeploymentCheck:
        """Test storage integration"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/system/status")
                
                if response.status_code == 200:
                    status_data = response.json()
                    storage_status = status_data.get("storage", {})
                    storage_available = storage_status.get("available", False)
                    
                    return DeploymentCheck(
                        check_name="Storage Integration",
                        success=storage_available,
                        message="Storage connected" if storage_available else "Storage not available",
                        details={
                            "bucket_name": storage_status.get("bucket_name", "unknown"),
                            "storage_type": storage_status.get("type", "unknown")
                        },
                        critical=True
                    )
                else:
                    return DeploymentCheck(
                        check_name="Storage Integration",
                        success=False,
                        message="Cannot get storage status",
                        critical=True
                    )
                    
        except Exception as e:
            return DeploymentCheck(
                check_name="Storage Integration",
                success=False,
                message=f"Storage check failed: {str(e)}",
                critical=True
            )
    
    async def check_modal_integration(self) -> DeploymentCheck:
        """Test Modal integration"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/system/status")
                
                if response.status_code == 200:
                    status_data = response.json()
                    modal_status = status_data.get("modal", {})
                    modal_available = modal_status.get("available", False)
                    
                    return DeploymentCheck(
                        check_name="Modal Integration",
                        success=modal_available,
                        message="Modal connected" if modal_available else "Modal not available",
                        details={
                            "functions_loaded": modal_status.get("functions_loaded", 0),
                            "authentication": "configured" if modal_available else "missing"
                        },
                        critical=True
                    )
                else:
                    return DeploymentCheck(
                        check_name="Modal Integration",
                        success=False,
                        message="Cannot get Modal status",
                        critical=True
                    )
                    
        except Exception as e:
            return DeploymentCheck(
                check_name="Modal Integration",
                success=False,
                message=f"Modal check failed: {str(e)}",
                critical=True
            )
    
    async def check_webhook_security(self) -> DeploymentCheck:
        """Test webhook security"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test webhook endpoint exists
                response = await client.get(f"{self.base_url}/api/v3/webhooks/modal/completion")
                
                # Should return 405 Method Not Allowed for GET
                if response.status_code == 405:
                    # Test webhook with invalid signature
                    webhook_payload = {"test": "data"}
                    response = await client.post(
                        f"{self.base_url}/api/v3/webhooks/modal/completion",
                        json=webhook_payload,
                        headers={"X-Modal-Signature": "invalid"}
                    )
                    
                    # Should reject invalid signature
                    security_ok = response.status_code in [401, 403]
                    
                    return DeploymentCheck(
                        check_name="Webhook Security",
                        success=security_ok,
                        message="Webhook security configured" if security_ok else "Webhook security may be bypassed",
                        critical=True
                    )
                else:
                    return DeploymentCheck(
                        check_name="Webhook Security",
                        success=False,
                        message="Webhook endpoint not found",
                        critical=True
                    )
                    
        except Exception as e:
            return DeploymentCheck(
                check_name="Webhook Security",
                success=False,
                message=f"Webhook check failed: {str(e)}",
                critical=True
            )
    
    async def check_rate_limiting(self) -> DeploymentCheck:
        """Test rate limiting"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Make multiple rapid requests
                responses = []
                for i in range(20):
                    response = await client.get(f"{self.base_url}/api/v2/models")
                    responses.append(response.status_code)
                
                # Check if any requests were rate limited (429)
                rate_limited = any(status == 429 for status in responses)
                success_responses = sum(1 for status in responses if status == 200)
                
                return DeploymentCheck(
                    check_name="Rate Limiting",
                    success=True,  # Rate limiting is optional
                    message=f"Rate limiting {'active' if rate_limited else 'not detected'} - {success_responses}/20 requests succeeded",
                    details={
                        "rate_limited_requests": sum(1 for status in responses if status == 429),
                        "successful_requests": success_responses
                    },
                    critical=False
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="Rate Limiting",
                success=False,
                message=f"Rate limiting check failed: {str(e)}",
                critical=False
            )
    
    async def check_monitoring_endpoints(self) -> DeploymentCheck:
        """Test monitoring endpoints"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test metrics endpoint if available
                metrics_response = await client.get(f"{self.base_url}/metrics")
                metrics_ok = metrics_response.status_code == 200
                
                # Test health endpoint
                health_response = await client.get(f"{self.base_url}/health")
                health_ok = health_response.status_code == 200
                
                return DeploymentCheck(
                    check_name="Monitoring Endpoints",
                    success=health_ok,  # Health is required, metrics optional
                    message=f"Monitoring endpoints: health={'✅' if health_ok else '❌'}, metrics={'✅' if metrics_ok else '❌'}",
                    details={
                        "health_endpoint": health_ok,
                        "metrics_endpoint": metrics_ok
                    },
                    critical=False
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="Monitoring Endpoints",
                success=False,
                message=f"Monitoring check failed: {str(e)}",
                critical=False
            )
    
    async def check_error_handling(self) -> DeploymentCheck:
        """Test error handling"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test 404 handling
                response_404 = await client.get(f"{self.base_url}/nonexistent-endpoint")
                handles_404 = response_404.status_code == 404
                
                # Test malformed request handling
                response_400 = await client.post(f"{self.base_url}/api/predict", json={"invalid": True})
                handles_400 = response_400.status_code in [400, 422]
                
                success = handles_404 and handles_400
                
                return DeploymentCheck(
                    check_name="Error Handling",
                    success=success,
                    message="Error handling working" if success else "Error handling issues detected",
                    details={
                        "404_handling": "✅" if handles_404 else "❌",
                        "400_handling": "✅" if handles_400 else "❌"
                    },
                    critical=False
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="Error Handling",
                success=False,
                message=f"Error handling check failed: {str(e)}",
                critical=False
            )
    
    async def check_performance_baseline(self) -> DeploymentCheck:
        """Test basic performance"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test response times
                start_time = time.time()
                response = await client.get(f"{self.base_url}/health")
                health_time = (time.time() - start_time) * 1000
                
                start_time = time.time()
                response = await client.get(f"{self.base_url}/api/v2/models")
                api_time = (time.time() - start_time) * 1000
                
                # Performance thresholds
                health_ok = health_time < 1000  # 1 second
                api_ok = api_time < 5000  # 5 seconds
                
                success = health_ok and api_ok
                
                return DeploymentCheck(
                    check_name="Performance Baseline",
                    success=success,
                    message=f"Performance {'acceptable' if success else 'concerning'}",
                    details={
                        "health_response_ms": f"{health_time:.1f}",
                        "api_response_ms": f"{api_time:.1f}",
                        "health_threshold": "< 1000ms",
                        "api_threshold": "< 5000ms"
                    },
                    critical=False
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="Performance Baseline",
                success=False,
                message=f"Performance check failed: {str(e)}",
                critical=False
            )
    
    async def check_security_headers(self) -> DeploymentCheck:
        """Test security headers"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/health")
                
                headers = response.headers
                security_headers = {
                    "X-Content-Type-Options": headers.get("x-content-type-options"),
                    "X-Frame-Options": headers.get("x-frame-options"),
                    "X-XSS-Protection": headers.get("x-xss-protection"),
                    "Strict-Transport-Security": headers.get("strict-transport-security")
                }
                
                present_headers = {k: v for k, v in security_headers.items() if v}
                
                return DeploymentCheck(
                    check_name="Security Headers",
                    success=len(present_headers) > 0,
                    message=f"{len(present_headers)}/4 security headers present",
                    details=present_headers,
                    critical=False
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="Security Headers",
                success=False,
                message=f"Security headers check failed: {str(e)}",
                critical=False
            )
    
    async def check_ssl_configuration(self) -> DeploymentCheck:
        """Test SSL configuration"""
        try:
            if self.base_url.startswith("https://"):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(f"{self.base_url}/health")
                    
                    return DeploymentCheck(
                        check_name="SSL Configuration",
                        success=True,
                        message="HTTPS enabled and working",
                        critical=False
                    )
            else:
                return DeploymentCheck(
                    check_name="SSL Configuration",
                    success=False,
                    message="HTTPS not enabled (acceptable for development)",
                    critical=False
                )
                
        except Exception as e:
            return DeploymentCheck(
                check_name="SSL Configuration",
                success=False,
                message=f"SSL check failed: {str(e)}",
                critical=False
            )
    
    async def check_kubernetes_health(self) -> DeploymentCheck:
        """Test Kubernetes health (if applicable)"""
        try:
            # This would require kubectl access in production
            # For now, just check if the deployment seems to be running in K8s
            
            # Check for K8s-style health endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/healthz")
                k8s_health = response.status_code == 200
                
                if k8s_health:
                    return DeploymentCheck(
                        check_name="Kubernetes Health",
                        success=True,
                        message="Kubernetes health endpoint responding",
                        critical=False
                    )
                else:
                    return DeploymentCheck(
                        check_name="Kubernetes Health",
                        success=True,  # Not critical if not K8s
                        message="Not running in Kubernetes or health endpoint not configured",
                        critical=False
                    )
                    
        except Exception as e:
            return DeploymentCheck(
                check_name="Kubernetes Health",
                success=True,  # Not critical
                message="Kubernetes health check skipped",
                critical=False
            )
    
    def print_summary(self):
        """Print deployment validation summary"""
        print("\n" + "=" * 80)
        print(f"📊 {self.environment.upper()} DEPLOYMENT VALIDATION SUMMARY")
        print("=" * 80)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.success)
        critical_failures = sum(1 for r in self.results if not r.success and r.critical)
        
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {total_checks - passed_checks}")
        print(f"🚨 Critical Failures: {critical_failures}")
        print(f"Success Rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if critical_failures > 0:
            print(f"\n🚨 CRITICAL FAILURES (DEPLOYMENT BLOCKED):")
            for result in self.results:
                if not result.success and result.critical:
                    print(f"   ❌ {result.check_name}: {result.message}")
        
        if critical_failures == 0:
            print(f"\n🎉 DEPLOYMENT READY!")
            print(f"   All critical checks passed. {self.environment.title()} deployment can proceed.")
        else:
            print(f"\n🛑 DEPLOYMENT BLOCKED!")
            print(f"   Fix critical failures before deploying to {self.environment}.")

async def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(description="Production Deployment Validator")
    parser.add_argument("url", help="Base URL of the deployment to validate")
    parser.add_argument("--environment", default="staging", choices=["staging", "production"], help="Environment type")
    
    args = parser.parse_args()
    
    validator = ProductionDeploymentValidator(args.url, args.environment)
    success = await validator.run_all_checks()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
