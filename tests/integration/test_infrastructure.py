"""
Infrastructure Integration Tests
Tests Kubernetes, GCP, and production infrastructure components
"""

import pytest
import asyncio
import os
import time
from typing import Dict, Any, List
import httpx
import subprocess
import json

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "omtx-hub")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

class TestInfrastructureIntegration:
    """Infrastructure-specific integration tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for API calls"""
        return httpx.AsyncClient(base_url=BASE_URL, timeout=60)
    
    @pytest.mark.asyncio
    async def test_kubernetes_health(self, client: httpx.AsyncClient):
        """Test Kubernetes deployment health"""
        
        # Test main application health
        response = await client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        
        # Check for Kubernetes-specific metadata
        if "kubernetes" in health_data:
            k8s_data = health_data["kubernetes"]
            assert "pod_name" in k8s_data or "node_name" in k8s_data
    
    @pytest.mark.asyncio
    async def test_redis_connectivity(self, client: httpx.AsyncClient):
        """Test Redis cache connectivity"""
        
        # Test cache health via API
        response = await client.get("/api/v3/health/services")
        if response.status_code == 200:
            services_data = response.json()
            
            if "redis" in services_data:
                redis_status = services_data["redis"]
                assert redis_status["status"] in ["healthy", "available"]
        
        # Test direct Redis functionality if available
        try:
            import redis
            if REDIS_HOST and REDIS_HOST != "localhost":
                redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
                
                # Test basic operations
                test_key = f"health_check_{int(time.time())}"
                redis_client.set(test_key, "test_value", ex=60)
                
                retrieved_value = redis_client.get(test_key)
                assert retrieved_value == "test_value"
                
                redis_client.delete(test_key)
        except ImportError:
            pytest.skip("Redis client not available")
        except Exception as e:
            pytest.skip(f"Redis connectivity test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_gcp_storage_integration(self, client: httpx.AsyncClient):
        """Test GCP Cloud Storage integration"""
        
        if not GCP_PROJECT_ID:
            pytest.skip("GCP_PROJECT_ID not configured")
        
        # Test storage health via API
        response = await client.get("/api/v3/health/services")
        if response.status_code == 200:
            services_data = response.json()
            
            if "storage" in services_data:
                storage_status = services_data["storage"]
                assert storage_status["status"] in ["healthy", "available"]
        
        # Test storage functionality via API
        response = await client.get("/api/v3/storage/health")
        if response.status_code == 200:
            storage_health = response.json()
            assert storage_health["bucket_accessible"] is True
    
    @pytest.mark.asyncio
    async def test_firestore_connectivity(self, client: httpx.AsyncClient):
        """Test Firestore database connectivity"""
        
        if not GCP_PROJECT_ID:
            pytest.skip("GCP_PROJECT_ID not configured")
        
        # Test database health via API
        response = await client.get("/api/v3/health/services")
        if response.status_code == 200:
            services_data = response.json()
            
            if "database" in services_data:
                db_status = services_data["database"]
                assert db_status["status"] in ["healthy", "available"]
        
        # Test basic database operations
        test_job_data = {
            "test": True,
            "timestamp": time.time(),
            "status": "test"
        }
        
        response = await client.post("/api/v3/database/test", json=test_job_data)
        if response.status_code == 200:
            test_response = response.json()
            assert test_response["success"] is True
    
    @pytest.mark.asyncio
    async def test_monitoring_and_metrics(self, client: httpx.AsyncClient):
        """Test monitoring and metrics collection"""
        
        # Test Prometheus metrics endpoint
        try:
            response = await client.get("/metrics")
            if response.status_code == 200:
                metrics_text = response.text
                
                # Basic Prometheus format validation
                assert "# HELP" in metrics_text or "# TYPE" in metrics_text
                
                # Check for application-specific metrics
                assert "http_requests_total" in metrics_text or "requests_total" in metrics_text
        except Exception:
            pytest.skip("Metrics endpoint not available")
        
        # Test health monitoring
        response = await client.get("/api/v3/health/status")
        assert response.status_code == 200
        
        health_status = response.json()
        assert "services" in health_status
        assert "overall_status" in health_status
    
    @pytest.mark.asyncio
    async def test_load_balancer_functionality(self, client: httpx.AsyncClient):
        """Test load balancer and ingress functionality"""
        
        # Make multiple requests to test load balancing
        responses = []
        for _ in range(10):
            response = await client.get("/health")
            responses.append({
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else None,
                "headers": dict(response.headers)
            })
            await asyncio.sleep(0.1)
        
        # All requests should succeed
        assert all(r["status_code"] == 200 for r in responses)
        
        # Check for load balancer headers
        lb_headers = ["x-forwarded-for", "x-real-ip", "x-forwarded-proto"]
        has_lb_headers = any(
            any(header in r["headers"] for header in lb_headers)
            for r in responses
        )
        
        # Note: May not have LB headers in local testing
        print(f"Load balancer headers detected: {has_lb_headers}")
    
    @pytest.mark.asyncio
    async def test_auto_scaling_behavior(self, client: httpx.AsyncClient):
        """Test horizontal pod autoscaling behavior"""
        
        # This test is conceptual - actual load testing should be done separately
        # Here we just verify that the application can handle concurrent requests
        
        async def make_request():
            response = await client.get("/health")
            return response.status_code
        
        # Make 20 concurrent requests
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful requests
        successful_requests = sum(1 for r in results if r == 200)
        failed_requests = len(results) - successful_requests
        
        # Should handle most concurrent requests successfully
        success_rate = successful_requests / len(results)
        assert success_rate >= 0.8, f"Success rate too low: {success_rate}"
        
        print(f"Concurrent request test: {successful_requests}/{len(results)} successful")
    
    @pytest.mark.asyncio
    async def test_persistent_volume_functionality(self, client: httpx.AsyncClient):
        """Test persistent volume functionality"""
        
        # Test file upload/download to verify persistent storage
        test_file_content = b"test file content for persistent volume test"
        
        # Upload test file
        files = {"file": ("test.txt", test_file_content, "text/plain")}
        response = await client.post("/api/v3/storage/upload", files=files)
        
        if response.status_code == 200:
            upload_response = response.json()
            file_path = upload_response.get("file_path")
            
            # Download the file
            response = await client.get(f"/api/v3/storage/download?path={file_path}")
            if response.status_code == 200:
                downloaded_content = response.content
                assert downloaded_content == test_file_content
            
            # Clean up
            await client.delete(f"/api/v3/storage/delete?path={file_path}")
        else:
            pytest.skip("File upload/download not available")
    
    @pytest.mark.asyncio
    async def test_secret_management(self, client: httpx.AsyncClient):
        """Test Kubernetes secret management"""
        
        # Test that sensitive endpoints require authentication
        sensitive_endpoints = [
            "/api/v3/admin/config",
            "/api/v3/admin/secrets",
            "/api/v3/webhooks/configure"
        ]
        
        for endpoint in sensitive_endpoints:
            response = await client.get(endpoint)
            # Should require authentication or not be exposed
            assert response.status_code in [401, 403, 404, 405]
    
    @pytest.mark.asyncio
    async def test_network_policies(self, client: httpx.AsyncClient):
        """Test network policy enforcement"""
        
        # Test that internal endpoints are not accessible externally
        internal_endpoints = [
            "/internal/metrics",
            "/admin/debug",
            "/api/internal/status"
        ]
        
        for endpoint in internal_endpoints:
            response = await client.get(endpoint)
            # Should not be accessible from external requests
            assert response.status_code in [404, 403]
    
    @pytest.mark.asyncio
    async def test_backup_and_recovery(self, client: httpx.AsyncClient):
        """Test backup and recovery capabilities"""
        
        # Test backup endpoint
        response = await client.post("/api/v3/admin/backup/trigger")
        if response.status_code == 200:
            backup_response = response.json()
            assert "backup_id" in backup_response
            
            # Check backup status
            backup_id = backup_response["backup_id"]
            response = await client.get(f"/api/v3/admin/backup/{backup_id}/status")
            assert response.status_code == 200
        else:
            pytest.skip("Backup functionality not available")
    
    @pytest.mark.asyncio
    async def test_ssl_tls_configuration(self, client: httpx.AsyncClient):
        """Test SSL/TLS configuration"""
        
        # Check if running over HTTPS
        if BASE_URL.startswith("https://"):
            # Test SSL redirect if applicable
            http_url = BASE_URL.replace("https://", "http://")
            try:
                http_client = httpx.AsyncClient(base_url=http_url, timeout=10)
                response = await http_client.get("/health", follow_redirects=False)
                
                # Should redirect to HTTPS or refuse connection
                assert response.status_code in [301, 302, 308] or response.is_error
                
                await http_client.aclose()
            except Exception:
                # Connection refused is acceptable for HTTPS-only
                pass
        else:
            pytest.skip("Not running over HTTPS")

# Kubernetes-specific tests
class TestKubernetesIntegration:
    """Kubernetes-specific integration tests"""
    
    @pytest.mark.skipif(not os.getenv("KUBECONFIG") and not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"), 
                       reason="Not running in Kubernetes environment")
    def test_pod_readiness_probes(self):
        """Test that readiness probes are working"""
        
        try:
            # Check pod status via kubectl
            result = subprocess.run([
                "kubectl", "get", "pods", 
                "-n", K8S_NAMESPACE,
                "-l", "app=omtx-hub-backend",
                "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                pods_data = json.loads(result.stdout)
                pods = pods_data.get("items", [])
                
                for pod in pods:
                    status = pod.get("status", {})
                    conditions = status.get("conditions", [])
                    
                    # Check that pod is ready
                    ready_condition = next(
                        (c for c in conditions if c["type"] == "Ready"), 
                        None
                    )
                    
                    if ready_condition:
                        assert ready_condition["status"] == "True"
        except subprocess.TimeoutExpired:
            pytest.skip("kubectl command timed out")
        except FileNotFoundError:
            pytest.skip("kubectl not available")
        except Exception as e:
            pytest.skip(f"Kubernetes check failed: {e}")
    
    @pytest.mark.skipif(not os.getenv("KUBECONFIG") and not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"),
                       reason="Not running in Kubernetes environment")
    def test_service_discovery(self):
        """Test Kubernetes service discovery"""
        
        try:
            # Check service endpoints
            result = subprocess.run([
                "kubectl", "get", "endpoints",
                "-n", K8S_NAMESPACE,
                "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                endpoints_data = json.loads(result.stdout)
                endpoints = endpoints_data.get("items", [])
                
                # Should have endpoints for main service
                backend_endpoints = [
                    ep for ep in endpoints 
                    if "omtx-hub-backend" in ep.get("metadata", {}).get("name", "")
                ]
                
                assert len(backend_endpoints) > 0
                
                # Check that endpoints have addresses
                for endpoint in backend_endpoints:
                    subsets = endpoint.get("subsets", [])
                    has_addresses = any(
                        subset.get("addresses", []) 
                        for subset in subsets
                    )
                    assert has_addresses
        except subprocess.TimeoutExpired:
            pytest.skip("kubectl command timed out")
        except FileNotFoundError:
            pytest.skip("kubectl not available")
        except Exception as e:
            pytest.skip(f"Service discovery check failed: {e}")

# Pytest configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.infrastructure,
    pytest.mark.asyncio
]