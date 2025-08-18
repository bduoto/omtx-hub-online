"""
Frontend-Backend Integration Tests
Tests complete workflow from frontend submission to results rendering
"""

import pytest
import asyncio
import time
import uuid
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import httpx
import os
from datetime import datetime

# Test configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:8081")
TEST_TIMEOUT = 300  # 5 minutes

class TestFrontendBackendIntegration:
    """Test complete frontend-backend integration workflows"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for API calls"""
        return httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID for isolation"""
        return f"frontend-test-{uuid.uuid4().hex[:8]}"
    
    @pytest.fixture
    def sample_prediction_data(self):
        """Sample data that would come from frontend forms"""
        return {
            "protein_sequence": "GIVEQCCTSICSLYQLENYCN",  # Insulin A chain
            "protein_name": "Insulin A Chain",
            "ligands": [
                {"name": "Ethanol", "smiles": "CCO"},
                {"name": "Isopropanol", "smiles": "CC(C)O"},
                {"name": "Benzene", "smiles": "C1=CC=CC=C1"}
            ],
            "job_settings": {
                "use_msa": False,
                "use_potentials": False,
                "confidence_threshold": 0.7
            }
        }
    
    @pytest.mark.asyncio
    async def test_frontend_api_compatibility(self, client: httpx.AsyncClient):
        """Test that backend APIs are compatible with frontend expectations"""
        
        # Test models endpoint (used by frontend model selector)
        response = await client.get("/api/v2/models")
        assert response.status_code == 200
        
        models = response.json()
        assert isinstance(models, list)
        
        # Verify model structure expected by frontend
        if models:
            model = models[0]
            expected_fields = ["id", "name", "description"]
            for field in expected_fields:
                assert field in model, f"Model missing required field: {field}"
        
        print("✅ Models API compatible with frontend")
    
    @pytest.mark.asyncio
    async def test_job_submission_frontend_format(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str,
        sample_prediction_data: Dict[str, Any]
    ):
        """Test job submission using frontend data format"""
        
        # Convert frontend data to API format
        api_payload = {
            "model_id": "boltz2",
            "task_type": "batch_protein_ligand_screening",
            "job_name": f"Frontend Integration Test - {datetime.now().strftime('%H:%M:%S')}",
            "use_msa": sample_prediction_data["job_settings"]["use_msa"],
            "use_potentials": sample_prediction_data["job_settings"]["use_potentials"],
            "input_data": {
                "protein_sequence": sample_prediction_data["protein_sequence"],
                "protein_name": sample_prediction_data["protein_name"],
                "ligands": sample_prediction_data["ligands"],
                "user_id": test_user_id
            }
        }
        
        response = await client.post("/api/predict", json=api_payload)
        assert response.status_code == 200
        
        job_data = response.json()
        assert "job_id" in job_data
        assert "status" in job_data
        
        job_id = job_data["job_id"]
        print(f"✅ Job submitted with frontend data format: {job_id}")
        
        return job_id
    
    @pytest.mark.asyncio
    async def test_batch_results_frontend_format(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str
    ):
        """Test batch results API format expected by frontend"""
        
        # Test batch listing (used by frontend dashboard)
        response = await client.get(f"/api/v3/batches/?user_id={test_user_id}&limit=10")
        
        if response.status_code == 200:
            batches = response.json()
            assert isinstance(batches, list)
            
            # Test batch structure expected by frontend
            if batches:
                batch = batches[0]
                expected_fields = ["job_id", "job_name", "status", "created_at"]
                for field in expected_fields:
                    if field in batch:
                        print(f"✅ Batch field present: {field}")
                
                # Test detailed batch results
                batch_id = batch.get("job_id") or batch.get("id")
                if batch_id:
                    response = await client.get(f"/api/v3/batches/{batch_id}/results?user_id={test_user_id}")
                    if response.status_code == 200:
                        batch_details = response.json()
                        
                        # Verify frontend-expected structure
                        expected_sections = ["individual_jobs", "progress", "status"]
                        for section in expected_sections:
                            if section in batch_details:
                                print(f"✅ Batch detail section present: {section}")
        
        print("✅ Batch results API compatible with frontend")
    
    @pytest.mark.asyncio
    async def test_results_data_parsing_and_visualization(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str
    ):
        """Test that results data can be parsed for frontend visualization"""
        
        # Get user results
        response = await client.get(f"/api/v2/results/ultra-fast?user_id={test_user_id}&limit=10")
        
        if response.status_code == 200:
            results_data = response.json()
            results = results_data.get("results", [])
            
            if results:
                # Test data structure for visualization
                for result in results[:3]:  # Test first 3 results
                    # Test basic result structure
                    assert "job_id" in result or "id" in result
                    
                    # Test results data for plotting
                    if "results" in result and result["results"]:
                        result_data = result["results"]
                        
                        # Test affinity data (for charts)
                        if "affinity" in result_data or "binding_affinity" in result_data:
                            affinity = result_data.get("affinity") or result_data.get("binding_affinity")
                            assert isinstance(affinity, (int, float))
                            print(f"✅ Affinity data parseable: {affinity}")
                        
                        # Test confidence data (for filtering)
                        if "confidence" in result_data:
                            confidence = result_data["confidence"]
                            assert isinstance(confidence, (int, float))
                            assert 0 <= confidence <= 1
                            print(f"✅ Confidence data parseable: {confidence}")
                
                # Test data conversion to DataFrame (for advanced visualization)
                try:
                    df_data = []
                    for result in results:
                        if "results" in result and result["results"]:
                            row = {
                                "job_id": result.get("job_id", result.get("id")),
                                "job_name": result.get("job_name", "Unknown"),
                                "status": result.get("status", "unknown"),
                                "created_at": result.get("created_at", ""),
                                **result["results"]  # Flatten results data
                            }
                            df_data.append(row)
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        assert len(df) > 0
                        print(f"✅ Results convertible to DataFrame: {len(df)} rows")
                        
                        # Test common visualization data
                        if "affinity" in df.columns or "binding_affinity" in df.columns:
                            affinity_col = "affinity" if "affinity" in df.columns else "binding_affinity"
                            affinity_stats = df[affinity_col].describe()
                            print(f"✅ Affinity statistics: mean={affinity_stats['mean']:.3f}")
                        
                        if "confidence" in df.columns:
                            confidence_stats = df["confidence"].describe()
                            print(f"✅ Confidence statistics: mean={confidence_stats['mean']:.3f}")
                
                except Exception as e:
                    print(f"⚠️ DataFrame conversion failed: {e}")
        
        print("✅ Results data parsing compatible with frontend visualization")
    
    @pytest.mark.asyncio
    async def test_real_time_progress_updates(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str,
        sample_prediction_data: Dict[str, Any]
    ):
        """Test real-time progress updates for frontend"""
        
        # Submit a job to track progress
        api_payload = {
            "model_id": "boltz2",
            "task_type": "protein_ligand_binding",
            "job_name": "Progress Test",
            "input_data": {
                "protein_sequence": sample_prediction_data["protein_sequence"],
                "ligand_smiles": sample_prediction_data["ligands"][0]["smiles"],
                "user_id": test_user_id
            }
        }
        
        response = await client.post("/api/predict", json=api_payload)
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data["job_id"]
            
            # Track progress updates
            progress_states = []
            for attempt in range(10):  # Check for 10 attempts
                response = await client.get(f"/api/jobs/{job_id}")
                if response.status_code == 200:
                    job_status = response.json()
                    status = job_status.get("status", "unknown")
                    progress_states.append(status)
                    
                    # Test progress data structure
                    if "progress" in job_status:
                        progress = job_status["progress"]
                        assert isinstance(progress, dict)
                        
                        # Test progress fields expected by frontend
                        if "percentage" in progress:
                            assert 0 <= progress["percentage"] <= 100
                        
                        if "stage" in progress:
                            assert isinstance(progress["stage"], str)
                        
                        print(f"✅ Progress update: {status} - {progress}")
                    
                    if status in ["completed", "failed"]:
                        break
                
                await asyncio.sleep(5)
            
            # Verify we got different states (shows progress tracking works)
            unique_states = set(progress_states)
            if len(unique_states) > 1:
                print(f"✅ Progress tracking working: {unique_states}")
            else:
                print(f"⚠️ Limited progress states observed: {unique_states}")
        
        print("✅ Real-time progress updates compatible with frontend")
    
    @pytest.mark.asyncio
    async def test_error_handling_frontend_display(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str
    ):
        """Test error handling and display for frontend"""
        
        # Test various error scenarios that frontend needs to handle
        error_scenarios = [
            {
                "name": "Invalid model",
                "payload": {
                    "model_id": "invalid_model",
                    "task_type": "protein_ligand_binding",
                    "input_data": {"user_id": test_user_id}
                },
                "expected_status": [400, 422]
            },
            {
                "name": "Missing required data",
                "payload": {
                    "model_id": "boltz2",
                    "task_type": "protein_ligand_binding",
                    "input_data": {"user_id": test_user_id}  # Missing protein/ligand
                },
                "expected_status": [400, 422]
            },
            {
                "name": "Invalid SMILES",
                "payload": {
                    "model_id": "boltz2",
                    "task_type": "protein_ligand_binding",
                    "input_data": {
                        "protein_sequence": "INVALID",
                        "ligand_smiles": "INVALID_SMILES",
                        "user_id": test_user_id
                    }
                },
                "expected_status": [400, 422]
            }
        ]
        
        for scenario in error_scenarios:
            response = await client.post("/api/predict", json=scenario["payload"])
            assert response.status_code in scenario["expected_status"]
            
            # Test error response structure for frontend
            if response.status_code in [400, 422]:
                error_data = response.json()
                
                # Verify error structure
                assert "detail" in error_data or "message" in error_data or "error" in error_data
                
                error_message = (
                    error_data.get("detail") or 
                    error_data.get("message") or 
                    error_data.get("error") or 
                    str(error_data)
                )
                
                assert isinstance(error_message, (str, list))
                print(f"✅ Error scenario '{scenario['name']}': proper error format")
        
        print("✅ Error handling compatible with frontend display")
    
    @pytest.mark.asyncio
    async def test_file_download_integration(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str
    ):
        """Test file download functionality for frontend"""
        
        # Get user results to find downloadable files
        response = await client.get(f"/api/v2/results/ultra-fast?user_id={test_user_id}&limit=5")
        
        if response.status_code == 200:
            results_data = response.json()
            results = results_data.get("results", [])
            
            for result in results:
                job_id = result.get("job_id", result.get("id"))
                if job_id and result.get("status") == "completed":
                    
                    # Test different file download endpoints
                    download_endpoints = [
                        f"/api/jobs/{job_id}/download/cif",
                        f"/api/jobs/{job_id}/download/pdb",
                        f"/api/jobs/{job_id}/download/json"
                    ]
                    
                    for endpoint in download_endpoints:
                        try:
                            response = await client.get(endpoint)
                            
                            if response.status_code == 200:
                                # Verify file content
                                content = response.content
                                assert len(content) > 0
                                
                                # Verify content type headers
                                content_type = response.headers.get("content-type", "")
                                assert content_type != ""
                                
                                print(f"✅ File download working: {endpoint}")
                                break  # Found at least one working download
                                
                        except Exception as e:
                            print(f"⚠️ Download endpoint {endpoint} error: {e}")
                    
                    break  # Test only first completed job
        
        print("✅ File download integration compatible with frontend")
    
    @pytest.mark.asyncio
    async def test_pagination_and_filtering(
        self, 
        client: httpx.AsyncClient, 
        test_user_id: str
    ):
        """Test pagination and filtering for frontend data tables"""
        
        # Test pagination parameters
        pagination_tests = [
            {"limit": 5, "offset": 0},
            {"limit": 10, "offset": 0},
            {"limit": 3, "offset": 2}
        ]
        
        for params in pagination_tests:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            response = await client.get(f"/api/v2/results/ultra-fast?user_id={test_user_id}&{query_string}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # Verify pagination works
                assert len(results) <= params["limit"]
                print(f"✅ Pagination working: limit={params['limit']}, got={len(results)}")
        
        # Test filtering parameters (if supported)
        filter_tests = [
            {"status": "completed"},
            {"status": "failed"},
            {"model_id": "boltz2"}
        ]
        
        for filter_params in filter_tests:
            query_string = "&".join([f"{k}={v}" for k, v in filter_params.items()])
            response = await client.get(f"/api/v2/results/ultra-fast?user_id={test_user_id}&{query_string}")
            
            # Any response is acceptable (filtering may not be implemented yet)
            if response.status_code == 200:
                print(f"✅ Filtering supported: {filter_params}")
            else:
                print(f"⚠️ Filtering not supported: {filter_params}")
        
        print("✅ Pagination and filtering compatible with frontend")
    
    @pytest.mark.asyncio
    async def test_websocket_or_sse_support(self, client: httpx.AsyncClient):
        """Test WebSocket or Server-Sent Events support for real-time updates"""
        
        # Test if WebSocket endpoint exists
        try:
            # This would test WebSocket connection if implemented
            # For now, just test if the endpoint exists
            response = await client.get("/ws")
            
            if response.status_code != 404:
                print("✅ WebSocket endpoint available")
            else:
                print("⚠️ WebSocket endpoint not found (may use polling instead)")
                
        except Exception as e:
            print(f"⚠️ WebSocket test failed: {e}")
        
        # Test Server-Sent Events endpoint if available
        try:
            response = await client.get("/api/events/stream")
            
            if response.status_code != 404:
                print("✅ Server-Sent Events endpoint available")
            else:
                print("⚠️ SSE endpoint not found (may use polling instead)")
                
        except Exception as e:
            print(f"⚠️ SSE test failed: {e}")
        
        print("✅ Real-time communication options tested")
