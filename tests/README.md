# OMTX-Hub Testing Suite

Comprehensive testing framework for OMTX-Hub with integration, end-to-end, and infrastructure tests.

## 🎯 Overview

This testing suite provides comprehensive validation of the OMTX-Hub platform including:

- **Integration Tests**: API endpoints, database operations, service integration
- **End-to-End Tests**: Complete user workflows from job submission to completion
- **Modal Integration**: Real Modal function execution and webhook processing
- **Infrastructure Tests**: Kubernetes, GCP services, networking, and security
- **Performance Tests**: Load testing and performance validation

## 🚀 Quick Start

### 1. Setup Test Environment

```bash
cd tests
python run_tests.py --setup
```

### 2. Run Tests

```bash
# Run quick smoke tests
python run_tests.py smoke

# Run full integration test suite
python run_tests.py integration

# Run end-to-end tests
python run_tests.py e2e

# Run all tests
python run_tests.py all
```

### 3. Environment-Specific Testing

```bash
# Test against staging environment
python run_tests.py integration --environment staging

# Test against production (read-only tests)
python run_tests.py smoke --environment production
```

## 📁 Test Structure

```
tests/
├── integration/                 # Integration test modules
│   ├── test_end_to_end.py      # Complete workflow tests
│   ├── test_modal_integration.py # Modal-specific tests  
│   └── test_infrastructure.py   # Infrastructure tests
├── conftest.py                  # Pytest configuration and fixtures
├── pytest.ini                  # Pytest settings
├── requirements.txt             # Testing dependencies
├── run_tests.py                # Test runner script
└── README.md                   # This file
```

## 🧪 Test Suites

### Smoke Tests (`smoke`)
**Duration**: ~1 minute  
**Purpose**: Quick validation that core services are operational

- Health check endpoints
- Basic API connectivity
- Service availability

```bash
python run_tests.py smoke
```

### Integration Tests (`integration`)
**Duration**: ~5 minutes  
**Purpose**: Test service integration and API functionality

- API endpoint validation
- Database operations
- Service communication
- Error handling

```bash
python run_tests.py integration --coverage
```

### End-to-End Tests (`e2e`)
**Duration**: ~10 minutes  
**Purpose**: Test complete user workflows

- Individual job submission and completion
- Batch job processing
- File upload/download
- Results retrieval

```bash
python run_tests.py e2e --environment staging
```

### Modal Integration Tests (`modal`)
**Duration**: ~15 minutes  
**Purpose**: Test Modal function integration

- Direct Modal function calls
- Webhook delivery and processing
- QoS lane functionality
- Batch optimization

```bash
python run_tests.py modal --environment staging
```

### Infrastructure Tests (`infrastructure`)
**Duration**: ~3 minutes  
**Purpose**: Test infrastructure components

- Kubernetes health and scaling
- GCP service connectivity
- Redis cache functionality
- Network policies and security

```bash
python run_tests.py infrastructure
```

## 🔧 Configuration

### Environment Variables

**Required:**
```bash
TEST_BASE_URL=http://localhost:8000    # Target API URL
```

**Optional:**
```bash
GCP_PROJECT_ID=your-project-id         # For GCP integration tests
MODAL_WEBHOOK_SECRET=your-secret       # For webhook security tests
K8S_NAMESPACE=omtx-hub                 # Kubernetes namespace
MODAL_TEST_MODE=mock                   # mock or real
TEST_TIMEOUT=300                       # Default test timeout
```

### Test Runner Options

```bash
# Basic usage
python run_tests.py <suite> [options]

# Common options
--environment staging     # Target environment (local/staging/production)
--coverage               # Generate coverage report
--verbose                # Detailed output
--fail-fast              # Stop on first failure
--no-parallel           # Disable parallel execution
--junit                 # Generate JUnit XML report
--html-report           # Generate HTML report

# Environment configuration
--gcp-project PROJECT_ID      # GCP project for testing
--webhook-secret SECRET       # Modal webhook secret

# Advanced usage
--pytest-args "--maxfail=3 -k test_batch"  # Pass additional pytest args
```

## 🎭 Test Environments

### Local Development
```bash
python run_tests.py integration --environment local
```
- **Target**: `http://localhost:8000`
- **Modal**: Mock mode
- **Features**: Full test suite, fast execution
- **Use Case**: Development and debugging

### Staging Environment
```bash
python run_tests.py e2e --environment staging
```
- **Target**: `https://api-staging.omtx-hub.com`
- **Modal**: Real Modal functions
- **Features**: Production-like testing
- **Use Case**: Pre-deployment validation

### Production Environment
```bash
python run_tests.py smoke --environment production
```
- **Target**: `https://api.omtx-hub.com`
- **Modal**: Real Modal functions (read-only)
- **Features**: Health checks and validation
- **Use Case**: Production monitoring

## 📊 Test Categories

### API Testing
```python
# Example API test
async def test_job_submission(client: httpx.AsyncClient):
    response = await client.post("/api/v2/predict", json=job_data)
    assert response.status_code == 200
    assert "job_id" in response.json()
```

### Database Testing
```python
# Example database test
async def test_job_persistence(client: httpx.AsyncClient):
    # Submit job
    response = await client.post("/api/v2/predict", json=job_data)
    job_id = response.json()["job_id"]
    
    # Retrieve job
    response = await client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
```

### Modal Integration Testing
```python
# Example Modal test
@pytest.mark.modal
async def test_modal_webhook_delivery(client: httpx.AsyncClient):
    webhook_payload = create_test_webhook()
    response = await client.post("/api/v3/webhooks/modal/completion", 
                               json=webhook_payload)
    assert response.status_code == 200
```

### Infrastructure Testing
```python
# Example infrastructure test
@pytest.mark.infrastructure
async def test_kubernetes_health():
    pods = get_kubernetes_pods()
    assert all(pod.status == "Running" for pod in pods)
```

## 🔍 Debugging Tests

### View Available Tests
```bash
python run_tests.py integration --list-tests
```

### Run Specific Test
```bash
python run_tests.py integration --pytest-args "-k test_individual_job_workflow"
```

### Debug Failed Tests
```bash
python run_tests.py integration --verbose --fail-fast --pytest-args "--pdb"
```

### Coverage Analysis
```bash
python run_tests.py integration --coverage
# View report: tests/coverage_html/index.html
```

## 🚦 CI/CD Integration

### GitHub Actions Integration

The tests are automatically integrated with GitHub Actions:

```yaml
# .github/workflows/ci-cd.yml
- name: Run Integration Tests
  run: |
    cd tests
    python run_tests.py integration --coverage --junit
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: tests/coverage.xml
```

### Test Selection by Environment

```bash
# Development pipeline
python run_tests.py smoke && python run_tests.py integration

# Staging pipeline  
python run_tests.py e2e --environment staging

# Production pipeline
python run_tests.py smoke --environment production
```

## 📈 Performance Testing

### Load Testing Integration
```bash
# Run performance tests
python run_tests.py performance --environment staging

# Custom load test
cd backend/testing
python load_test_suite.py --users 100 --spawn-rate 10
```

### Performance Benchmarks
```python
@pytest.mark.performance
def test_api_response_time(benchmark):
    result = benchmark(api_call_function)
    assert result.response_time < 1.0  # 1 second SLA
```

## 🛡️ Security Testing

### Vulnerability Scanning
```bash
# Run security tests
python run_tests.py security

# Manual security scan
bandit -r backend/
safety check --json
```

### Authentication Testing
```python
@pytest.mark.security
async def test_authentication_required():
    response = await client.get("/api/admin/config")
    assert response.status_code in [401, 403]
```

## 🚨 Common Issues and Solutions

### Test Failures

**1. Connection Refused**
```bash
# Check if service is running
curl http://localhost:8000/health

# Start service if needed
cd backend && python main.py
```

**2. Timeout Errors**
```bash
# Increase timeout for slow tests
export TEST_TIMEOUT=600
python run_tests.py e2e
```

**3. Modal Integration Failures**
```bash
# Check Modal authentication
modal token set your-token-id your-token-secret

# Use mock mode for development
export MODAL_TEST_MODE=mock
```

**4. Kubernetes Test Failures**
```bash
# Check kubectl access
kubectl cluster-info

# Verify namespace
kubectl get pods -n omtx-hub
```

### Performance Issues

**1. Slow Test Execution**
```bash
# Enable parallel execution
python run_tests.py integration --workers 8

# Run only fast tests
python run_tests.py integration --pytest-args "-m 'not slow'"
```

**2. Memory Issues**
```bash
# Reduce parallel workers
python run_tests.py integration --workers 2

# Run tests sequentially
python run_tests.py integration --no-parallel
```

## 📋 Test Maintenance

### Adding New Tests

1. **Create test file** in appropriate directory
2. **Add test markers** for categorization
3. **Update test documentation**
4. **Validate in CI/CD pipeline**

```python
@pytest.mark.integration
@pytest.mark.api
async def test_new_feature(client: httpx.AsyncClient):
    # Test implementation
    pass
```

### Updating Test Configuration

1. **Modify `conftest.py`** for fixtures
2. **Update `pytest.ini`** for pytest settings
3. **Adjust `run_tests.py`** for test runner options
4. **Update documentation**

### Test Data Management

```python
# Use fixtures for test data
@pytest.fixture
def test_protein_sequence():
    return "GIVEQCCTSICSLYQLENYCN"

# Use factories for complex data
def create_test_job(protein_seq, ligand_smiles):
    return {...}
```

## 🔗 Related Documentation

- [API Documentation](../backend/docs/)
- [Deployment Guide](../infrastructure/k8s/README.md)
- [Modal Integration](../backend/docs/WEBHOOK_CONFIGURATION.md)
- [Performance Testing](../backend/testing/README.md)
- [Security Guidelines](../backend/docs/SECURITY.md)