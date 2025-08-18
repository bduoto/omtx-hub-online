"""
Pytest configuration for OMTX-Hub integration tests
"""

import pytest
import asyncio
import os
from typing import Generator, AsyncGenerator
import httpx

# Test configuration
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "300"))  # 5 minutes default

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "modal: marks tests that require Modal integration"
    )
    config.addinivalue_line(
        "markers", "infrastructure: marks tests for infrastructure components"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create a test HTTP client for the entire test session"""
    async with httpx.AsyncClient(
        base_url=TEST_BASE_URL,
        timeout=TEST_TIMEOUT,
        follow_redirects=True
    ) as client:
        yield client

@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create a test HTTP client for each test function"""
    async with httpx.AsyncClient(
        base_url=TEST_BASE_URL,
        timeout=TEST_TIMEOUT,
        follow_redirects=True
    ) as client:
        yield client

@pytest.fixture(scope="session")
async def verify_service_availability(test_client: httpx.AsyncClient):
    """Verify that the service is available before running tests"""
    try:
        response = await test_client.get("/health")
        if response.status_code != 200:
            pytest.skip(f"Service not available at {TEST_BASE_URL}")
    except Exception as e:
        pytest.skip(f"Could not connect to service at {TEST_BASE_URL}: {e}")

@pytest.fixture
def test_protein_sequence():
    """Standard test protein sequence (insulin A chain)"""
    return "GIVEQCCTSICSLYQLENYCN"

@pytest.fixture
def test_ligand_smiles():
    """Standard test ligand SMILES (caffeine)"""
    return "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

@pytest.fixture
def test_ligands_batch():
    """Batch of test ligands for batch testing"""
    return [
        {"smiles": "CCO", "name": "ethanol"},
        {"smiles": "CC(=O)O", "name": "acetic_acid"},
        {"smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "name": "caffeine"},
        {"smiles": "CC(C)O", "name": "isopropanol"},
        {"smiles": "C1=CC=CC=C1", "name": "benzene"}
    ]

@pytest.fixture
def modal_test_config():
    """Configuration for Modal integration tests"""
    return {
        "timeout": 600,  # 10 minutes for Modal jobs
        "polling_interval": 10,  # seconds
        "max_retries": 3,
        "mock_mode": os.getenv("MODAL_TEST_MODE", "mock").lower() == "mock"
    }

# Skip conditions for different environments
skip_if_no_modal = pytest.mark.skipif(
    os.getenv("MODAL_TEST_MODE", "mock").lower() == "mock",
    reason="Requires real Modal environment"
)

skip_if_no_kubernetes = pytest.mark.skipif(
    not os.getenv("KUBECONFIG") and not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"),
    reason="Not running in Kubernetes environment"
)

skip_if_no_gcp = pytest.mark.skipif(
    not os.getenv("GCP_PROJECT_ID"),
    reason="GCP project not configured"
)

# Pytest collection modifiers
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names and paths"""
    
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        if "modal" in str(item.fspath):
            item.add_marker(pytest.mark.modal)
        
        if "infrastructure" in str(item.fspath):
            item.add_marker(pytest.mark.infrastructure)
        
        # Add slow marker for tests that take longer
        if "end_to_end" in item.name or "batch" in item.name:
            item.add_marker(pytest.mark.slow)
        
        # Add e2e marker for end-to-end tests
        if "end_to_end" in str(item.fspath) or "e2e" in item.name:
            item.add_marker(pytest.mark.e2e)

# Test environment validation
@pytest.fixture(scope="session", autouse=True)
def validate_test_environment():
    """Validate test environment configuration"""
    
    # Check required environment variables
    required_vars = ["TEST_BASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {missing_vars}")
    
    # Check optional environment variables and warn if missing
    optional_vars = {
        "GCP_PROJECT_ID": "GCP integration tests will be skipped",
        "MODAL_WEBHOOK_SECRET": "Webhook security tests will be limited",
        "K8S_NAMESPACE": "Kubernetes tests will use default namespace"
    }
    
    for var, warning in optional_vars.items():
        if not os.getenv(var):
            print(f"Warning: {var} not set - {warning}")

# Custom assertions
def assert_valid_job_response(response_data: dict):
    """Assert that a job response has the expected structure"""
    assert "job_id" in response_data
    assert "status" in response_data
    assert response_data["status"] in ["pending", "running", "completed", "failed"]

def assert_valid_batch_response(response_data: dict):
    """Assert that a batch response has the expected structure"""
    assert "batch_id" in response_data
    assert "status" in response_data or "total_jobs" in response_data

def assert_valid_health_response(response_data: dict):
    """Assert that a health response has the expected structure"""
    assert "status" in response_data
    assert response_data["status"] in ["healthy", "unhealthy", "degraded"]

# Helper functions for tests
async def wait_for_job_completion(client: httpx.AsyncClient, job_id: str, timeout: int = 300) -> str:
    """Wait for a job to complete and return the final status"""
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = await client.get(f"/api/jobs/{job_id}")
        if response.status_code == 200:
            job_data = response.json()
            status = job_data.get("status")
            
            if status in ["completed", "failed"]:
                return status
        
        await asyncio.sleep(5)
    
    raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

async def wait_for_batch_completion(client: httpx.AsyncClient, batch_id: str, timeout: int = 600) -> str:
    """Wait for a batch to complete and return the final status"""
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = await client.get(f"/api/v3/batches/{batch_id}")
        if response.status_code == 200:
            batch_data = response.json()
            status = batch_data.get("status")
            
            if status in ["completed", "failed", "partial"]:
                return status
        
        await asyncio.sleep(10)
    
    raise TimeoutError(f"Batch {batch_id} did not complete within {timeout} seconds")