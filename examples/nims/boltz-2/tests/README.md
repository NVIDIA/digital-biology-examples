# 🧪 Test Suite for Multi-Endpoint Boltz2 NIM Functionality

This directory contains comprehensive test cases for **ALL** Boltz2 NIM functionalities with both single and multiple endpoints, covering both Python API and CLI approaches.

## 📋 **Test Coverage Overview**

### **✅ Core Functionality Tests**
- **Protein Structure Prediction** - Single vs Multi-endpoint
- **Protein-Ligand Complex Prediction** - Single vs Multi-endpoint  
- **Covalent Complex Prediction** - Single vs Multi-endpoint
- **DNA-Protein Complex Prediction** - Single vs Multi-endpoint
- **YAML-Based Prediction** - Single vs Multi-endpoint
- **Virtual Screening** - Single vs Multi-endpoint
- **Health Monitoring** - Single vs Multi-endpoint
- **Service Metadata** - Single vs Multi-endpoint

### **✅ Load Balancing & Failover Tests**
- **Load Balancing Strategies** - Round Robin, Random, Least Loaded, Weighted
- **Endpoint Failover** - Automatic failover to healthy endpoints
- **Health Recovery** - Endpoint recovery and reintegration
- **Error Handling** - Graceful degradation and error reporting

### **✅ Integration & Workflow Tests**
- **End-to-End Workflows** - Complete prediction workflows
- **Performance Monitoring** - Request tracking and statistics
- **Resource Management** - Proper cleanup and resource handling
- **Configuration Testing** - Various endpoint configuration formats

## 🚀 **Running the Tests**

### **Prerequisites**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock click-testing

# Install the boltz2-client package
pip install -e .
```

### **Basic Test Execution**
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=boltz2_client --cov-report=html
```

### **Running Specific Test Categories**

#### **1. Python API Tests**
```bash
# Run only Python API tests
pytest -m api

# Run specific API test file
pytest tests/test_multi_endpoint_functionality.py -v

# Run specific test class
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient -v
```

#### **2. CLI Tests**
```bash
# Run only CLI tests
pytest -m cli

# Run specific CLI test file
pytest tests/test_cli_multi_endpoint.py -v

# Run specific CLI test class
pytest tests/test_cli_multi_endpoint.py::TestCLIMultiEndpoint -v
```

#### **3. Integration Tests**
```bash
# Run only integration tests
pytest -m integration

# Run specific integration test file
pytest tests/test_integration_scenarios.py -v

# Run specific integration test class
pytest tests/test_integration_scenarios.py::TestIntegrationScenarios -v
```

#### **4. Unit Tests**
```bash
# Run only unit tests
pytest -m unit

# Run tests excluding slow ones
pytest -m "not slow"
```

### **Running Specific Test Functions**

#### **Protein Structure Prediction Tests**
```bash
# Test single endpoint protein prediction
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_single_endpoint_protein_structure -v

# Test multi-endpoint protein prediction
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_protein_structure -v

# Test protein prediction failover
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_protein_structure_failover -v
```

#### **Virtual Screening Tests**
```bash
# Test single endpoint virtual screening
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_single_endpoint_virtual_screening -v

# Test multi-endpoint virtual screening
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_virtual_screening -v
```

#### **Load Balancing Tests**
```bash
# Test load balancing strategies
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_load_balancing_strategies -v

# Test endpoint configuration
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_endpoint_configuration -v
```

#### **CLI Command Tests**
```bash
# Test health command with single endpoint
pytest tests/test_cli_multi_endpoint.py::TestCLIMultiEndpoint::test_health_single_endpoint -v

# Test health command with multiple endpoints
pytest tests/test_cli_multi_endpoint.py::TestCLIMultiEndpoint::test_health_multi_endpoint -v

# Test protein command with multiple endpoints
pytest tests/test_cli_multi_endpoint.py::TestCLIMultiEndpoint::test_protein_multi_endpoint -v
```

#### **Integration Scenario Tests**
```bash
# Test end-to-end protein prediction workflow
pytest tests/test_integration_scenarios.py::TestIntegrationScenarios::test_end_to_end_protein_prediction_multi_endpoint -v

# Test virtual screening workflow
pytest tests/test_integration_scenarios.py::TestIntegrationScenarios::test_end_to_end_virtual_screening_multi_endpoint -v

# Test load balancing scenarios
pytest tests/test_integration_scenarios.py::TestIntegrationScenarios::test_load_balancing_least_loaded_strategy -v
```

## 🔧 **Test Configuration**

### **Test Markers**
The test suite uses custom markers for organization:

- **`@pytest.mark.api`** - Python API tests
- **`@pytest.mark.cli`** - CLI command tests  
- **`@pytest.mark.integration`** - Integration workflow tests
- **`@pytest.mark.unit`** - Unit tests
- **`@pytest.mark.slow`** - Tests that might take longer

### **Test Fixtures**
Common test fixtures are defined in `conftest.py`:

- **`mock_single_client`** - Mock single Boltz2 client
- **`mock_multi_endpoint_client`** - Mock multi-endpoint client
- **`mock_healthy_endpoints`** - Mock healthy endpoints
- **`mock_mixed_health_endpoints`** - Mock endpoints with mixed health
- **`sample_prediction_response`** - Sample prediction response
- **`sample_health_status`** - Sample health status
- **`temp_yaml_file`** - Temporary YAML file for testing
- **`temp_compounds_file`** - Temporary compounds file for testing

## 📊 **Test Results and Coverage**

### **Running with Coverage**
```bash
# Generate coverage report
pytest --cov=boltz2_client --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### **Test Output Examples**
```bash
# Example test run output
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_protein_structure -v

# Output:
# test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_protein_structure PASSED
# 
# ============================== 1 passed in 0.05s ===============================
```

## 🐛 **Debugging Tests**

### **Running Tests in Debug Mode**
```bash
# Run with print statements visible
pytest -s

# Run specific test with debug output
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_protein_structure -v -s
```

### **Common Test Issues**

#### **1. Import Errors**
```bash
# If you get import errors, ensure you're in the right directory
cd /path/to/boltz2-python-client
pip install -e .
```

#### **2. Async Test Issues**
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Run async tests with proper event loop
pytest --asyncio-mode=auto
```

#### **3. Mock Issues**
```bash
# If mocks aren't working, ensure pytest-mock is installed
pip install pytest-mock

# Run with mock debugging
pytest -v -s --tb=short
```

## 🧪 **Adding New Tests**

### **Test File Structure**
```python
# Example test structure
class TestNewFunctionality:
    """Test suite for new functionality."""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data."""
        return {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_new_functionality_single_endpoint(self, mock_single_client):
        """Test new functionality with single endpoint."""
        # Test implementation
        pass
    
    @pytest.mark.asyncio
    async def test_new_functionality_multi_endpoint(self, mock_multi_endpoint_client):
        """Test new functionality with multiple endpoints."""
        # Test implementation
        pass
```

### **Test Naming Conventions**
- **Single endpoint tests**: `test_functionality_single_endpoint`
- **Multi-endpoint tests**: `test_functionality_multi_endpoint`
- **Failover tests**: `test_functionality_failover`
- **Integration tests**: `test_end_to_end_workflow`

## 📈 **Performance Testing**

### **Load Testing**
```bash
# Run performance tests
pytest tests/test_integration_scenarios.py::TestIntegrationScenarios::test_performance_monitoring -v

# Run with timing
pytest --durations=10
```

### **Stress Testing**
```bash
# Test with many endpoints
pytest tests/test_integration_scenarios.py::TestIntegrationScenarios::test_endpoint_configuration_formats -v
```

## 🔍 **Continuous Integration**

### **GitHub Actions Example**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-mock click-testing
      - name: Run tests
        run: |
          pytest --cov=boltz2_client --cov-report=xml
```

## 📚 **Test Documentation**

### **Generated Test Reports**
```bash
# Generate HTML test report
pytest --html=test_report.html --self-contained-html

# Generate JUnit XML report
pytest --junitxml=test_results.xml
```

### **Coverage Reports**
```bash
# Generate detailed coverage report
pytest --cov=boltz2_client --cov-report=html --cov-report=term-missing
```

## 🎯 **Test Goals and Success Criteria**

### **Test Coverage Goals**
- **100% Function Coverage** - All public methods tested
- **100% Branch Coverage** - All code paths tested
- **100% Error Path Coverage** - All error conditions tested
- **100% Integration Coverage** - All workflows tested

### **Success Criteria**
- **All tests pass** - No test failures
- **High coverage** - >95% code coverage
- **Fast execution** - Tests complete in <30 seconds
- **Reliable results** - Tests are deterministic

## 🚀 **Quick Start Commands**

```bash
# Quick test run
pytest

# Test specific functionality
pytest -k "protein_structure" -v

# Test multi-endpoint only
pytest -k "multi_endpoint" -v

# Test CLI only
pytest -m cli -v

# Test with coverage
pytest --cov=boltz2_client --cov-report=term

# Debug failing test
pytest tests/test_multi_endpoint_functionality.py::TestMultiEndpointClient::test_multi_endpoint_protein_structure -v -s --tb=long
```

## 📞 **Support and Issues**

If you encounter issues with the tests:

1. **Check dependencies** - Ensure all packages are installed
2. **Check Python version** - Tests require Python 3.8+
3. **Check directory** - Ensure you're in the project root
4. **Check imports** - Ensure the package is installed in editable mode

For additional help, check the test output and error messages for specific guidance.
