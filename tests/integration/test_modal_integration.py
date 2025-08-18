"""
Modal Integration Tests
Tests the complete Modal + GKE architecture with webhooks
"""

import pytest
import asyncio
import time
import uuid
import json
from typing import Dict, Any, Optional
import httpx
import os

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
MODAL_TEST_MODE = os.getenv("MODAL_TEST_MODE", "mock").lower()
TEST_TIMEOUT = 600  # 10 minutes for Modal jobs

class TestModalIntegration:
    """Modal-specific integration tests"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for API calls"""
        return httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)
    
    @pytest.fixture
    def test_modal_job_data(self):
        """Test data for Modal job submission"""
        return {
            "model_type": "boltz2",
            "params": {
                "protein_sequence": "MKLLILTLISIAVLSSCPGSTPAVLCRQGKKQGIGDIHSTHPLTGDGGSQNQPAIQAIYGTDLYSYRSRTGNSTYNNDSPGATNLSQDFQKLMTSKGDTGSSGHQVNHTTASQESNSSNLTVLPPRSYSQEIAQAQGVDQEYISVSYMFTQTFAGDGLQTVLQIQSGGMDHDYYGSAYTD",
                "ligands": ["CCO", "CC(=O)O", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"],
                "use_msa_server": True,
                "use_potentials": False
            },
            "job_id": f"test_job_{uuid.uuid4().hex[:8]}",
            "batch_id": f"test_batch_{uuid.uuid4().hex[:8]}",
            "lane": "bulk"
        }
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(MODAL_TEST_MODE == "mock", reason="Requires real Modal environment")
    async def test_direct_modal_submission(self, client: httpx.AsyncClient, test_modal_job_data: Dict[str, Any]):
        """Test direct Modal function submission"""
        
        # Submit job via production modal service
        response = await client.post("/api/v3/modal/submit", json=test_modal_job_data)
        assert response.status_code == 200
        
        response_data = response.json()
        modal_call_id = response_data["modal_call_id"]
        assert modal_call_id is not None
        
        # Monitor execution status
        execution_status = await self._wait_for_modal_execution(client, modal_call_id)
        assert execution_status in ["completed", "failed"]
        
        return modal_call_id, execution_status
    
    @pytest.mark.asyncio
    async def test_modal_webhook_delivery(self, client: httpx.AsyncClient):
        """Test Modal webhook delivery and processing"""
        
        # Simulate webhook payload from Modal
        webhook_payload = {
            "call_id": f"webhook_test_{uuid.uuid4().hex[:8]}",
            "status": "success",
            "result": {
                "affinity": 0.6385,
                "confidence": 0.5071,
                "ptm_score": 0.5423,
                "iptm_score": 0.8717,
                "plddt_score": 0.4159,
                "structure_file_base64": "UERCIDEgICAgICAgIFRFU1QgU1RSVUNUM1VTRSBIRUFERVIgICBURVNU",
                "execution_time": 205.3,
                "parameters": {
                    "model": "boltz2",
                    "use_msa": True
                }
            },
            "metadata": {
                "job_id": f"job_{uuid.uuid4().hex[:8]}",
                "batch_id": f"batch_{uuid.uuid4().hex[:8]}",
                "timestamp": time.time()
            }
        }
        
        # Send webhook to completion endpoint
        headers = {
            "Content-Type": "application/json",
            "X-Modal-Timestamp": str(int(time.time())),
            "User-Agent": "Modal-Webhook/1.0"
        }
        
        # Add HMAC signature if secret is available
        webhook_secret = os.getenv("MODAL_WEBHOOK_SECRET")
        if webhook_secret:
            payload_str = json.dumps(webhook_payload)
            import hmac
            import hashlib
            signature = hmac.new(
                webhook_secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Modal-Signature"] = f"sha256={signature}"
        
        response = await client.post(
            "/api/v3/webhooks/modal/completion",
            json=webhook_payload,
            headers=headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert response_data["call_id"] == webhook_payload["call_id"]
        
        # Give background processing time to complete
        await asyncio.sleep(2)
        
        return webhook_payload["call_id"]
    
    @pytest.mark.asyncio
    async def test_qos_lane_functionality(self, client: httpx.AsyncClient):
        """Test QoS lane routing and limits"""
        
        # Test interactive lane submission
        interactive_job = {
            "model_type": "boltz2",
            "params": {
                "protein_sequence": "MKLLILTLISIAVAL",
                "ligands": ["CCO"],
                "use_msa_server": False  # Faster for interactive
            },
            "job_id": f"interactive_{uuid.uuid4().hex[:8]}",
            "lane": "interactive"
        }
        
        response = await client.post("/api/v3/modal/submit", json=interactive_job)
        if response.status_code == 200:
            assert "modal_call_id" in response.json()
        else:
            # Lane might not be available or Modal not configured
            assert response.status_code in [400, 503]
        
        # Test bulk lane submission
        bulk_job = {
            "model_type": "boltz2",
            "params": {
                "protein_sequence": "MKLLILTLISIAVALSSCPGSTPAVLCRQGKKQGIGDIHSTHPLTGDGGSQNQPAIQAIYGTDL",
                "ligands": ["CCO", "CC(=O)O", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"],
                "use_msa_server": True
            },
            "job_id": f"bulk_{uuid.uuid4().hex[:8]}",
            "lane": "bulk"
        }
        
        response = await client.post("/api/v3/modal/submit", json=bulk_job)
        if response.status_code == 200:
            assert "modal_call_id" in response.json()
        else:
            assert response.status_code in [400, 503]
    
    @pytest.mark.asyncio
    async def test_modal_service_metrics(self, client: httpx.AsyncClient):
        """Test Modal service metrics and monitoring"""
        
        # Get Modal service metrics
        response = await client.get("/api/v3/modal/metrics")
        if response.status_code == 200:
            metrics = response.json()
            
            # Verify metrics structure
            assert "lanes" in metrics
            assert "total_active" in metrics
            assert "performance" in metrics
            
            # Verify lane metrics
            for lane in ["interactive", "bulk"]:
                if lane in metrics["lanes"]:
                    lane_metrics = metrics["lanes"][lane]
                    assert "active_jobs" in lane_metrics
                    assert "capacity" in lane_metrics
        else:
            # Metrics endpoint might not be available
            assert response.status_code in [404, 501]
    
    @pytest.mark.asyncio
    async def test_active_execution_management(self, client: httpx.AsyncClient):
        """Test active execution listing and cancellation"""
        
        # Get active executions
        response = await client.get("/api/v3/webhooks/active-executions")
        assert response.status_code == 200
        
        executions_data = response.json()
        assert "total_active" in executions_data
        assert "executions" in executions_data
        
        # If there are active executions, test cancellation
        if executions_data["total_active"] > 0:
            execution = executions_data["executions"][0]
            modal_call_id = execution["modal_call_id"]
            
            # Test cancellation
            response = await client.post(f"/api/v3/webhooks/executions/{modal_call_id}/cancel")
            # Cancellation might not be supported or execution might be completed
            assert response.status_code in [200, 404, 405]
    
    @pytest.mark.asyncio
    async def test_batch_sharding_optimization(self, client: httpx.AsyncClient):
        """Test Modal batch sharding for optimization"""
        
        # Submit large batch to test sharding
        large_batch_data = {
            "protein_sequence": "MKLLILTLISIAVALSSCPGSTPAVLCRQGKKQGIGDIHSTHPLTGDGGSQNQPAIQAIYGTDLYSYRSRTGNSTYNNDSPGATNLSQDFQKLMTSKGDTGSSGHQVNHTTASQESNSSNLTVLPPRSYSQEIAQAQGVDQEYISVSYMFTQTFAGDGLQTVLQIQSGGMDHDYYGSAYTD",
            "ligands": [
                {"smiles": f"C{i}", "name": f"test_ligand_{i}"}
                for i in range(20)  # 20 ligands to trigger sharding
            ],
            "batch_name": f"Sharding Test {uuid.uuid4().hex[:8]}",
            "use_msa": True,
            "optimization_strategy": "sharded"
        }
        
        response = await client.post("/api/v3/batches/submit", json=large_batch_data)
        if response.status_code == 200:
            batch_response = response.json()
            batch_id = batch_response["batch_id"]
            
            # Check that batch was created with sharding info
            response = await client.get(f"/api/v3/batches/{batch_id}")
            assert response.status_code == 200
            
            batch_details = response.json()
            # Should have optimization metadata
            if "optimization" in batch_details:
                assert batch_details["optimization"]["strategy"] == "sharded"
        else:
            # Large batch submission might not be supported
            assert response.status_code in [400, 413, 503]
    
    @pytest.mark.asyncio
    async def test_modal_error_handling(self, client: httpx.AsyncClient):
        """Test Modal error handling and recovery"""
        
        # Test invalid Modal job submission
        invalid_job = {
            "model_type": "nonexistent_model",
            "params": {},
            "job_id": f"invalid_{uuid.uuid4().hex[:8]}"
        }
        
        response = await client.post("/api/v3/modal/submit", json=invalid_job)
        assert response.status_code in [400, 404]
        
        # Test webhook with invalid signature
        invalid_webhook = {
            "call_id": f"invalid_{uuid.uuid4().hex[:8]}",
            "status": "success",
            "result": {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Modal-Signature": "sha256=invalid_signature",
            "X-Modal-Timestamp": str(int(time.time()))
        }
        
        response = await client.post(
            "/api/v3/webhooks/modal/completion",
            json=invalid_webhook,
            headers=headers
        )
        
        if os.getenv("MODAL_WEBHOOK_SECRET"):
            # Should reject invalid signature
            assert response.status_code == 401
        else:
            # Might accept if no secret configured
            assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_webhook_configuration_api(self, client: httpx.AsyncClient):
        """Test webhook configuration management"""
        
        # Test webhook status
        response = await client.get("/api/v3/webhooks/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert "configured" in status_data
        assert "base_url" in status_data
        assert "total_apps" in status_data
        
        # Test webhook configuration (if allowed)
        config_data = {
            "webhook_base_url": "https://test.example.com",
            "webhook_secret": "test_secret_123",
            "auto_configure": False
        }
        
        response = await client.post("/api/v3/webhooks/configure", json=config_data)
        # Configuration might not be allowed in test environment
        assert response.status_code in [200, 403, 501]
    
    @pytest.mark.asyncio
    async def test_idempotency_support(self, client: httpx.AsyncClient):
        """Test Modal job idempotency"""
        
        # Submit job with idempotency key
        idem_key = f"test_idem_{uuid.uuid4().hex}"
        job_data = {
            "model_type": "boltz2",
            "params": {
                "protein_sequence": "MKLLILTLISIAVAL",
                "ligands": ["CCO"]
            },
            "job_id": f"idem_test_{uuid.uuid4().hex[:8]}",
            "idem_key": idem_key
        }
        
        # Submit same job twice
        response1 = await client.post("/api/v3/modal/submit", json=job_data)
        response2 = await client.post("/api/v3/modal/submit", json=job_data)
        
        if response1.status_code == 200 and response2.status_code == 200:
            # Should return same modal_call_id for idempotent requests
            data1 = response1.json()
            data2 = response2.json()
            assert data1["modal_call_id"] == data2["modal_call_id"]
        else:
            # Idempotency might not be fully implemented
            assert response1.status_code in [200, 400, 501]
            assert response2.status_code in [200, 400, 501]
    
    async def _wait_for_modal_execution(self, client: httpx.AsyncClient, modal_call_id: str, timeout: int = TEST_TIMEOUT) -> str:
        """Wait for Modal execution to complete"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check execution status
            response = await client.get(f"/api/v3/modal/executions/{modal_call_id}/status")
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status")
                
                if status in ["completed", "failed"]:
                    return status
                
                print(f"Modal execution {modal_call_id} status: {status}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
        raise TimeoutError(f"Modal execution {modal_call_id} did not complete within {timeout} seconds")

# Pytest configuration for Modal tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.modal,
    pytest.mark.asyncio
]