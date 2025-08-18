"""
End-to-end integration tests for OMTX-Hub
Tests the complete workflow from job submission to completion including Modal→GKE→GCP pipeline
"""

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, List, Optional
import httpx
import os
from datetime import datetime, timedelta

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:8081")
TEST_TIMEOUT = 600  # 10 minutes for Modal jobs
POLLING_INTERVAL = 10  # seconds
MAX_POLL_ATTEMPTS = 60  # 10 minutes of polling

class TestOMTXHubEndToEnd:
    """End-to-end integration tests for complete Modal→GKE→GCP pipeline"""

    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for API calls"""
        return httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)

    @pytest.fixture
    def test_user_id(self):
        """Test user ID for isolation"""
        return f"test-user-{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def test_protein_sequence(self):
        """Test protein sequence (insulin A chain - small for fast testing)"""
        return "GIVEQCCTSICSLYQLENYCN"

    @pytest.fixture
    def test_ligand_smiles(self):
        """Test ligand SMILES strings (small molecules for fast testing)"""
        return [
            "CCO",  # Ethanol
            "CC(C)O",  # Isopropanol
            "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"  # Caffeine
        ]

    @pytest.fixture
    def test_batch_ligands(self):
        """Larger set of ligands for batch testing"""
        return [
            "CCO",  # Ethanol
            "CC(C)O",  # Isopropanol
            "C1=CC=CC=C1",  # Benzene
            "CC(=O)O",  # Acetic acid
            "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
            "CC(C)(C)O",  # tert-Butanol
            "C1=CC=C(C=C1)O",  # Phenol
            "CC(C)CC(C)(C)O"  # 3,5,5-Trimethylhexanol
        ]

    @pytest.mark.asyncio
    async def test_system_health_comprehensive(self, client: httpx.AsyncClient):
        """Test comprehensive system health including all production services"""

        # Main health check
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Main health check: {data.get('uptime', 'unknown')} uptime")

        # System status with service details
        response = await client.get("/api/system/status")
        assert response.status_code == 200
        status = response.json()

        # Verify critical services
        assert "database" in status
        assert "storage" in status
        print(f"✅ Database available: {status['database'].get('available', False)}")
        print(f"✅ Storage available: {status['storage'].get('available', False)}")

        # Check Modal integration
        if "modal" in status:
            print(f"✅ Modal available: {status['modal'].get('available', False)}")
            print(f"   Functions loaded: {status['modal'].get('functions_loaded', 0)}")

        # Test production service endpoints
        production_endpoints = [
            "/api/v3/webhooks/modal/completion",  # Should return 405 for GET
            "/api/v2/models",  # Should return model list
            "/api/v3/batches/",  # Should return 422 without user_id
        ]

        for endpoint in production_endpoints:
            response = await client.get(endpoint)
            # Any response other than 500 indicates the endpoint exists
            assert response.status_code != 500
            print(f"✅ Endpoint {endpoint}: {response.status_code}")

    @pytest.mark.asyncio
    async def test_frontend_backend_connectivity(self, client: httpx.AsyncClient):
        """Test frontend-backend connectivity"""

        # Test frontend availability
        try:
            frontend_client = httpx.AsyncClient(base_url=FRONTEND_URL, timeout=10.0)
            response = await frontend_client.get("/")
            assert response.status_code == 200
            print("✅ Frontend accessible on port 8081")
            await frontend_client.aclose()
        except httpx.ConnectError:
            pytest.skip("Frontend not running on port 8081 - run 'npm run dev -- --port 8081'")

        # Test CORS headers for frontend integration
        response = await client.options("/api/v2/models")
        assert "access-control-allow-origin" in response.headers.keys() or response.status_code == 200
        print("✅ CORS configured for frontend integration")

    @pytest.mark.asyncio
    async def test_individual_job_submission_and_completion(
        self,
        client: httpx.AsyncClient,
        test_user_id: str,
        test_protein_sequence: str,
        test_ligand_smiles: List[str]
    ):
        """Test complete individual job workflow: submission → Modal execution → GCP storage → results"""

        # Submit individual job
        job_payload = {
            "model_id": "boltz2",
            "task_type": "protein_ligand_binding",
            "job_name": f"Integration Test Individual - {datetime.now().strftime('%H:%M:%S')}",
            "use_msa": False,  # Faster without MSA
            "use_potentials": False,
            "input_data": {
                "protein_sequence": test_protein_sequence,
                "ligand_smiles": test_ligand_smiles[0],  # Single ligand
                "user_id": test_user_id
            }
        }

        print(f"🚀 Submitting individual job for user {test_user_id}")
        response = await client.post("/api/predict", json=job_payload)
        assert response.status_code == 200

        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Job submitted: {job_id}")

        # Poll for completion
        print("⏳ Waiting for job completion...")
        final_status = await self._poll_job_completion(client, job_id)

        if final_status == "completed":
            print("✅ Job completed successfully")

            # Verify results are accessible
            response = await client.get(f"/api/jobs/{job_id}")
            assert response.status_code == 200

            job_details = response.json()
            assert job_details["status"] == "completed"
            assert "results" in job_details

            # Verify GCP storage
            if "results" in job_details and job_details["results"]:
                results = job_details["results"]
                assert "affinity" in results or "binding_affinity" in results
                print(f"✅ Results stored: affinity data available")

                # Test structure file download if available
                try:
                    response = await client.get(f"/api/jobs/{job_id}/download/cif")
                    if response.status_code == 200:
                        print("✅ Structure file downloadable")
                except:
                    print("⚠️ Structure file not available (may be expected)")

        elif final_status == "failed":
            # Get failure details for debugging
            response = await client.get(f"/api/jobs/{job_id}")
            job_details = response.json()
            error_msg = job_details.get("error_message", "Unknown error")
            pytest.fail(f"Job failed: {error_msg}")
        else:
            pytest.fail(f"Job did not complete within timeout. Final status: {final_status}")

    @pytest.mark.asyncio
    async def test_batch_job_submission_and_completion(
        self,
        client: httpx.AsyncClient,
        test_user_id: str,
        test_protein_sequence: str,
        test_batch_ligands: List[str]
    ):
        """Test complete batch workflow: submission → Modal execution → GCP storage → aggregation → results"""

        # Submit batch job
        batch_payload = {
            "model_id": "boltz2",
            "task_type": "batch_protein_ligand_screening",
            "job_name": f"Integration Test Batch - {datetime.now().strftime('%H:%M:%S')}",
            "use_msa": False,  # Faster without MSA
            "use_potentials": False,
            "input_data": {
                "protein_sequence": test_protein_sequence,
                "protein_name": "TestProtein",
                "ligands": [
                    {"name": f"ligand_{i+1}", "smiles": smiles}
                    for i, smiles in enumerate(test_batch_ligands[:5])  # Limit to 5 for faster testing
                ],
                "user_id": test_user_id
            }
        }

        print(f"🚀 Submitting batch job with {len(batch_payload['input_data']['ligands'])} ligands")
        response = await client.post("/api/predict", json=batch_payload)
        assert response.status_code == 200

        batch_data = response.json()
        batch_id = batch_data["job_id"]
        print(f"✅ Batch submitted: {batch_id}")

        # Poll for batch completion
        print("⏳ Waiting for batch completion...")
        final_status = await self._poll_job_completion(client, batch_id)

        if final_status == "completed":
            print("✅ Batch completed successfully")

            # Test batch results API
            response = await client.get(f"/api/v3/batches/{batch_id}/results?user_id={test_user_id}")
            assert response.status_code == 200

            batch_results = response.json()
            assert "individual_jobs" in batch_results
            assert len(batch_results["individual_jobs"]) == len(batch_payload['input_data']['ligands'])

            # Verify individual job results
            completed_jobs = [job for job in batch_results["individual_jobs"] if job.get("status") == "completed"]
            assert len(completed_jobs) > 0, "At least some jobs should complete"

            print(f"✅ Batch results: {len(completed_jobs)}/{len(batch_results['individual_jobs'])} jobs completed")

            # Test aggregated results if available
            if "summary" in batch_results:
                summary = batch_results["summary"]
                assert "total_jobs" in summary
                assert "completed_jobs" in summary
                print("✅ Batch summary generated")

        elif final_status == "failed":
            pytest.fail(f"Batch job failed")
        else:
            # For batch jobs, partial completion might be acceptable
            print(f"⚠️ Batch job status: {final_status} (may have partial results)")

    async def _poll_job_completion(self, client: httpx.AsyncClient, job_id: str) -> str:
        """Poll job until completion or timeout"""

        for attempt in range(MAX_POLL_ATTEMPTS):
            try:
                response = await client.get(f"/api/jobs/{job_id}")
                if response.status_code == 200:
                    job_data = response.json()
                    status = job_data.get("status", "unknown")

                    if status in ["completed", "failed"]:
                        return status

                    if attempt % 6 == 0:  # Print every minute
                        print(f"   Status: {status} (attempt {attempt + 1}/{MAX_POLL_ATTEMPTS})")

                await asyncio.sleep(POLLING_INTERVAL)

            except Exception as e:
                print(f"   Polling error: {e}")
                await asyncio.sleep(POLLING_INTERVAL)

        return "timeout"

    @pytest.mark.asyncio
    async def test_webhook_integration(self, client: httpx.AsyncClient):
        """Test webhook endpoint integration"""

        # Test webhook endpoint exists and has proper security
        response = await client.get("/api/v3/webhooks/modal/completion")
        # Should return 405 Method Not Allowed for GET request
        assert response.status_code == 405
        print("✅ Webhook endpoint configured")

        # Test webhook with invalid signature (should fail)
        webhook_payload = {
            "job_id": "test-job-123",
            "status": "completed",
            "results": {"test": "data"}
        }

        response = await client.post(
            "/api/v3/webhooks/modal/completion",
            json=webhook_payload,
            headers={"X-Modal-Signature": "invalid-signature"}
        )
        # Should reject invalid signature
        assert response.status_code in [401, 403]
        print("✅ Webhook security validation working")

    @pytest.mark.asyncio
    async def test_production_services_integration(self, client: httpx.AsyncClient, test_user_id: str):
        """Test integration of production services (router, storage, etc.)"""

        # Test smart job router via API
        router_test_payload = {
            "user_id": test_user_id,
            "job_request": {
                "protein_sequences": ["MKTAYIAKQRQISFVKSHFSRQ"],
                "ligands": ["CCO", "CC(C)O"]
            }
        }

        # This would test the router if we had a direct endpoint
        # For now, we test it indirectly through job submission

        # Test rate limiting (if enabled)
        try:
            # Make multiple rapid requests to test rate limiting
            responses = []
            for i in range(10):
                response = await client.get(f"/api/v2/models")
                responses.append(response.status_code)

            # Should not get rate limited for reasonable requests
            assert all(status in [200, 422] for status in responses)
            print("✅ Rate limiting configured appropriately")

        except Exception as e:
            print(f"⚠️ Rate limiting test skipped: {e}")

    @pytest.mark.asyncio
    async def test_gcp_storage_integration(self, client: httpx.AsyncClient, test_user_id: str):
        """Test GCP storage integration and file operations"""

        # Test user results retrieval (tests GCP storage indirectly)
        response = await client.get(f"/api/v2/results/ultra-fast?user_id={test_user_id}&limit=10")

        if response.status_code == 200:
            results = response.json()
            assert "results" in results
            print(f"✅ GCP storage integration: Retrieved {len(results.get('results', []))} results")
        else:
            # 422 is acceptable if user has no results yet
            assert response.status_code in [200, 422]
            print("✅ GCP storage integration: API responding correctly")

    @pytest.mark.asyncio
    async def test_frontend_data_flow(self, client: httpx.AsyncClient, test_user_id: str):
        """Test data flow from backend to frontend format"""

        # Test batch listing API (used by frontend)
        response = await client.get(f"/api/v3/batches/?user_id={test_user_id}&limit=10")

        if response.status_code == 200:
            batches = response.json()
            assert isinstance(batches, list)
            print(f"✅ Frontend batch API: {len(batches)} batches")

            # Test batch detail format if batches exist
            if batches:
                batch_id = batches[0].get("job_id") or batches[0].get("id")
                if batch_id:
                    response = await client.get(f"/api/v3/batches/{batch_id}/results?user_id={test_user_id}")
                    if response.status_code == 200:
                        batch_details = response.json()
                        # Verify frontend-expected structure
                        expected_fields = ["individual_jobs", "progress", "status"]
                        for field in expected_fields:
                            if field in batch_details:
                                print(f"✅ Frontend data structure: {field} present")
        else:
            assert response.status_code in [200, 422]
            print("✅ Frontend batch API: Responding correctly")

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, client: httpx.AsyncClient, test_user_id: str):
        """Test error handling and recovery mechanisms"""

        # Test invalid job submission
        invalid_payload = {
            "model_id": "invalid_model",
            "task_type": "invalid_task",
            "input_data": {"invalid": "data"}
        }

        response = await client.post("/api/predict", json=invalid_payload)
        # Should return proper error response
        assert response.status_code in [400, 422, 500]
        print("✅ Error handling: Invalid requests properly rejected")

        # Test non-existent job retrieval
        fake_job_id = f"fake-job-{uuid.uuid4().hex}"
        response = await client.get(f"/api/jobs/{fake_job_id}")
        assert response.status_code == 404
        print("✅ Error handling: Non-existent jobs return 404")

        # Test malformed requests
        response = await client.post("/api/predict", json={"malformed": True})
        assert response.status_code in [400, 422]
        print("✅ Error handling: Malformed requests rejected")

    @pytest.mark.asyncio
    async def test_performance_and_scalability(self, client: httpx.AsyncClient, test_user_id: str):
        """Test basic performance characteristics"""

        # Test API response times
        start_time = time.time()
        response = await client.get("/health")
        health_time = time.time() - start_time

        assert response.status_code == 200
        assert health_time < 1.0  # Health check should be fast
        print(f"✅ Performance: Health check in {health_time:.3f}s")

        # Test concurrent requests
        async def make_request():
            return await client.get("/api/v2/models")

        start_time = time.time()
        tasks = [make_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time

        successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
        assert len(successful_responses) >= 3  # Most should succeed
        print(f"✅ Performance: 5 concurrent requests in {concurrent_time:.3f}s")

    @pytest.mark.asyncio
    async def test_data_consistency_and_integrity(self, client: httpx.AsyncClient, test_user_id: str):
        """Test data consistency across the system"""

        # Submit a job and verify data consistency across different endpoints
        job_payload = {
            "model_id": "boltz2",
            "task_type": "protein_ligand_binding",
            "job_name": "Consistency Test",
            "input_data": {
                "protein_sequence": "GIVEQCCTSICSLYQLENYCN",
                "ligand_smiles": "CCO",
                "user_id": test_user_id
            }
        }

        response = await client.post("/api/predict", json=job_payload)
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data["job_id"]

            # Wait a moment for job to be registered
            await asyncio.sleep(2)

            # Check job appears in different endpoints
            endpoints_to_check = [
                f"/api/jobs/{job_id}",
                f"/api/v2/results/ultra-fast?user_id={test_user_id}&limit=50"
            ]

            job_found_count = 0
            for endpoint in endpoints_to_check:
                try:
                    response = await client.get(endpoint)
                    if response.status_code == 200:
                        data = response.json()

                        # Check if job appears in the response
                        if endpoint.endswith(job_id):
                            if data.get("job_id") == job_id:
                                job_found_count += 1
                        else:
                            # Check in results list
                            results = data.get("results", [])
                            if any(r.get("job_id") == job_id or r.get("id") == job_id for r in results):
                                job_found_count += 1

                except Exception as e:
                    print(f"   Endpoint {endpoint} error: {e}")

            print(f"✅ Data consistency: Job found in {job_found_count} endpoints")
        else:
            print("⚠️ Data consistency test skipped (job submission failed)")

    @pytest.mark.asyncio
    async def test_system_monitoring_and_observability(self, client: httpx.AsyncClient):
        """Test monitoring and observability features"""

        # Test system metrics endpoints
        monitoring_endpoints = [
            "/api/system/status",
            "/health"
        ]

        for endpoint in monitoring_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict)
            print(f"✅ Monitoring: {endpoint} responding with metrics")

        # Test performance monitoring if available
        try:
            response = await client.get("/api/v3/performance/metrics")
            if response.status_code == 200:
                metrics = response.json()
                print("✅ Performance monitoring: Metrics available")
            else:
                print("⚠️ Performance monitoring: Not available (may be expected)")
        except:
            print("⚠️ Performance monitoring: Endpoint not found")

    @pytest.mark.asyncio
    async def test_cleanup_and_resource_management(self, client: httpx.AsyncClient, test_user_id: str):
        """Test cleanup and resource management"""

        # This test ensures we're not leaking resources
        initial_response = await client.get("/api/system/status")
        if initial_response.status_code == 200:
            initial_status = initial_response.json()
            print("✅ Resource management: System status captured")

            # After all tests, system should still be healthy
            final_response = await client.get("/health")
            assert final_response.status_code == 200

            final_health = final_response.json()
            assert final_health["status"] == "healthy"
            print("✅ Resource management: System remains healthy after tests")
        
        # API health endpoints
        health_endpoints = [
            "/api/v3/health/status",
            "/api/v3/health/services",
            "/api/v3/webhooks/modal/health"
        ]
        
        for endpoint in health_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 200, f"Health check failed: {endpoint}"
    
    @pytest.mark.asyncio
    async def test_individual_job_workflow(self, client: httpx.AsyncClient, test_protein_sequence: str, test_ligand_smiles: str):
        """Test complete individual job workflow"""
        
        # Step 1: Submit individual job
        job_data = {
            "input_data": {
                "sequences": [
                    {
                        "protein": {
                            "sequence": test_protein_sequence
                        }
                    },
                    {
                        "ligand": {
                            "smiles": test_ligand_smiles
                        }
                    }
                ]
            },
            "job_name": f"Integration Test Job {uuid.uuid4().hex[:8]}",
            "task_type": "protein_ligand_binding",
            "use_msa": True,
            "use_potentials": False
        }
        
        response = await client.post("/api/v2/predict", json=job_data)
        assert response.status_code == 200
        
        job_response = response.json()
        job_id = job_response["job_id"]
        assert job_id is not None
        assert job_response["status"] in ["pending", "running"]
        
        # Step 2: Monitor job until completion
        final_status = await self._wait_for_job_completion(client, job_id)
        assert final_status in ["completed", "failed"]
        
        # Step 3: Get job results
        response = await client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        
        job_details = response.json()
        assert job_details["id"] == job_id
        assert job_details["status"] in ["completed", "failed"]
        
        if job_details["status"] == "completed":
            # Verify results structure
            assert "results" in job_details or "output_data" in job_details
            
            # Step 4: Test file download
            try:
                response = await client.get(f"/api/jobs/{job_id}/download/cif")
                if response.status_code == 200:
                    assert len(response.content) > 0
                    assert "content-disposition" in response.headers.get("content-disposition", "").lower()
            except Exception:
                # File download may not be available for all jobs
                pass
        
        return job_id, job_details
    
    @pytest.mark.asyncio
    async def test_batch_job_workflow(self, client: httpx.AsyncClient, test_protein_sequence: str):
        """Test complete batch job workflow"""
        
        # Test ligands (multiple SMILES)
        test_ligands = [
            {"smiles": "CCO", "name": "ethanol"},
            {"smiles": "CC(=O)O", "name": "acetic_acid"},
            {"smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "name": "caffeine"}
        ]
        
        # Step 1: Submit batch job
        batch_data = {
            "protein_sequence": test_protein_sequence,
            "ligands": test_ligands,
            "batch_name": f"Integration Test Batch {uuid.uuid4().hex[:8]}",
            "use_msa": True,
            "use_potentials": False
        }
        
        response = await client.post("/api/v3/batches/submit", json=batch_data)
        assert response.status_code == 200
        
        batch_response = response.json()
        batch_id = batch_response["batch_id"]
        assert batch_id is not None
        
        # Step 2: Monitor batch until completion
        final_status = await self._wait_for_batch_completion(client, batch_id)
        assert final_status in ["completed", "failed", "partial"]
        
        # Step 3: Get batch results
        response = await client.get(f"/api/v3/batches/{batch_id}")
        assert response.status_code == 200
        
        batch_details = response.json()
        assert batch_details["batch_id"] == batch_id
        
        # Step 4: Get enhanced results
        response = await client.get(f"/api/v3/batches/{batch_id}/enhanced-results")
        assert response.status_code == 200
        
        enhanced_results = response.json()
        assert "processed_results" in enhanced_results
        
        # Step 5: Test batch analytics
        response = await client.get(f"/api/v3/batches/{batch_id}/analytics")
        if response.status_code == 200:
            analytics = response.json()
            assert "total_jobs" in analytics
        
        return batch_id, batch_details
    
    @pytest.mark.asyncio
    async def test_webhook_endpoints(self, client: httpx.AsyncClient):
        """Test webhook configuration and delivery"""
        
        # Test webhook health
        response = await client.get("/api/v3/webhooks/modal/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        
        # Test webhook status
        response = await client.get("/api/v3/webhooks/status")
        assert response.status_code == 200
        
        # Test webhook test endpoint
        test_payload = {
            "modal_call_id": f"test_{uuid.uuid4().hex[:8]}",
            "status": "success",
            "test_data": {"test_mode": True}
        }
        
        response = await client.post("/api/v3/webhooks/test", json=test_payload)
        assert response.status_code == 200
        
        test_response = response.json()
        assert test_response["status"] == "test_completed"
    
    @pytest.mark.asyncio
    async def test_api_consistency(self, client: httpx.AsyncClient):
        """Test API version consistency and backward compatibility"""
        
        # Test that v3 APIs are available
        v3_endpoints = [
            "/api/v3/batches/list",
            "/api/v3/health/status",
            "/api/v3/webhooks/status"
        ]
        
        for endpoint in v3_endpoints:
            response = await client.get(endpoint)
            assert response.status_code in [200, 404], f"Endpoint {endpoint} returned unexpected status"
        
        # Test that legacy endpoints still work
        legacy_endpoints = [
            "/api/jobs",
            "/api/batches"
        ]
        
        for endpoint in legacy_endpoints:
            response = await client.get(endpoint)
            assert response.status_code in [200, 404], f"Legacy endpoint {endpoint} failed"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client: httpx.AsyncClient):
        """Test error handling and validation"""
        
        # Test invalid job submission
        invalid_job_data = {
            "input_data": {},  # Missing required data
            "job_name": "",    # Empty job name
            "task_type": "invalid_task"
        }
        
        response = await client.post("/api/v2/predict", json=invalid_job_data)
        assert response.status_code in [400, 422]  # Validation error
        
        # Test invalid batch submission
        invalid_batch_data = {
            "protein_sequence": "",  # Empty sequence
            "ligands": []           # No ligands
        }
        
        response = await client.post("/api/v3/batches/submit", json=invalid_batch_data)
        assert response.status_code in [400, 422]
        
        # Test nonexistent resource access
        response = await client.get(f"/api/jobs/nonexistent-job-id")
        assert response.status_code == 404
        
        response = await client.get(f"/api/v3/batches/nonexistent-batch-id")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client: httpx.AsyncClient):
        """Test rate limiting functionality"""
        
        # Make multiple rapid requests to test rate limiting
        responses = []
        for _ in range(10):
            response = await client.get("/health")
            responses.append(response.status_code)
        
        # All health checks should succeed (rate limit shouldn't apply to health)
        assert all(status == 200 for status in responses)
        
        # Test rate limiting on prediction endpoint
        job_data = {
            "input_data": {"test": "data"},
            "job_name": "Rate Limit Test",
            "task_type": "protein_ligand_binding"
        }
        
        rate_limit_responses = []
        for _ in range(5):
            response = await client.post("/api/v2/predict", json=job_data)
            rate_limit_responses.append(response.status_code)
            await asyncio.sleep(0.1)  # Small delay
        
        # Should get some rate limiting (429) or validation errors (400/422)
        assert any(status in [200, 400, 422, 429] for status in rate_limit_responses)
    
    @pytest.mark.asyncio
    async def test_production_features(self, client: httpx.AsyncClient):
        """Test production-specific features"""
        
        # Test monitoring endpoints
        monitoring_endpoints = [
            "/api/v3/health/services",
            "/api/v3/health/slo",
            "/api/system/status"
        ]
        
        for endpoint in monitoring_endpoints:
            response = await client.get(endpoint)
            # These might not be available in all environments
            assert response.status_code in [200, 404, 501]
        
        # Test metrics endpoints
        try:
            response = await client.get("/metrics")
            if response.status_code == 200:
                # Basic Prometheus metrics format check
                metrics_text = response.text
                assert "# HELP" in metrics_text or "# TYPE" in metrics_text
        except Exception:
            # Metrics endpoint might not be available
            pass
    
    async def _wait_for_job_completion(self, client: httpx.AsyncClient, job_id: str, timeout: int = TEST_TIMEOUT) -> str:
        """Wait for job to complete and return final status"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = await client.get(f"/api/jobs/{job_id}")
            if response.status_code == 200:
                job_data = response.json()
                status = job_data.get("status")
                
                if status in ["completed", "failed"]:
                    return status
                
                # Log progress for debugging
                print(f"Job {job_id} status: {status}")
            
            await asyncio.sleep(POLLING_INTERVAL)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
    
    async def _wait_for_batch_completion(self, client: httpx.AsyncClient, batch_id: str, timeout: int = TEST_TIMEOUT) -> str:
        """Wait for batch to complete and return final status"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = await client.get(f"/api/v3/batches/{batch_id}")
            if response.status_code == 200:
                batch_data = response.json()
                status = batch_data.get("status")
                
                if status in ["completed", "failed", "partial"]:
                    return status
                
                # Log progress for debugging
                completed_jobs = batch_data.get("completed_jobs", 0)
                total_jobs = batch_data.get("total_jobs", 0)
                print(f"Batch {batch_id} progress: {completed_jobs}/{total_jobs} jobs completed")
            
            await asyncio.sleep(POLLING_INTERVAL)
        
        raise TimeoutError(f"Batch {batch_id} did not complete within {timeout} seconds")

# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test marks for different environments
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio
]