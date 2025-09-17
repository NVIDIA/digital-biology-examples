"""
Pytest configuration file for Boltz2 multi-endpoint tests.

This file provides common fixtures and configuration for all test modules.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    Boltz2Client,
    Boltz2SyncClient
)
from boltz2_client.models import PredictionResponse, HealthStatus, ServiceMetadata


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_prediction_response():
    """Create a sample prediction response for testing."""
    return PredictionResponse(
        structures=["structure1.cif", "structure2.cif"],
        confidence_scores=[0.85, 0.78],
        metadata={"test": "data", "timestamp": "2025-01-01T00:00:00Z"}
    )


@pytest.fixture
def sample_health_status():
    """Create a sample health status for testing."""
    return HealthStatus(
        status="healthy",
        details={
            "healthy_endpoints": 3,
            "total_endpoints": 3,
            "timestamp": "2025-01-01T00:00:00Z"
        }
    )


@pytest.fixture
def sample_service_metadata():
    """Create a sample service metadata for testing."""
    return ServiceMetadata(
        version="1.0.0",
        repository_override="test",
        assetInfo=["asset1", "asset2", "asset3"],
        modelInfo=[
            {"modelUrl": "https://example.com/model1", "shortName": "Model1"},
            {"modelUrl": "https://example.com/model2", "shortName": "Model2"}
        ]
    )


@pytest.fixture
def mock_single_client():
    """Create a mock single Boltz2 client."""
    client = Mock(spec=Boltz2Client)
    
    # Mock async methods
    client.predict_protein_structure = AsyncMock()
    client.predict_protein_ligand_complex = AsyncMock()
    client.predict_covalent_complex = AsyncMock()
    client.predict_dna_protein_complex = AsyncMock()
    client.predict_with_advanced_parameters = AsyncMock()
    client.predict_from_yaml_config = AsyncMock()
    client.predict_from_yaml_file = AsyncMock()
    client.health_check = AsyncMock()
    client.get_service_metadata = AsyncMock()
    
    # Mock sync methods
    client.predict_protein_structure_sync = Mock()
    client.predict_protein_ligand_complex_sync = Mock()
    client.predict_covalent_complex_sync = Mock()
    client.predict_dna_protein_complex_sync = Mock()
    client.predict_with_advanced_parameters_sync = Mock()
    client.predict_from_yaml_config_sync = Mock()
    client.predict_from_yaml_file_sync = Mock()
    client.health_check_sync = Mock()
    client.get_service_metadata_sync = Mock()
    
    return client


@pytest.fixture
def mock_multi_endpoint_client():
    """Create a mock multi-endpoint client."""
    # Create multiple mock clients
    clients = [Mock(spec=Boltz2Client) for _ in range(3)]
    
    for client in clients:
        # Mock async methods
        client.predict_protein_structure = AsyncMock()
        client.predict_protein_ligand_complex = AsyncMock()
        client.predict_covalent_complex = AsyncMock()
        client.predict_dna_protein_complex = AsyncMock()
        client.predict_with_advanced_parameters = AsyncMock()
        client.predict_from_yaml_config = AsyncMock()
        client.predict_from_yaml_file = AsyncMock()
        client.health_check = AsyncMock()
        client.get_service_metadata = AsyncMock()
        
        # Mock sync methods
        client.predict_protein_structure_sync = Mock()
        client.predict_protein_ligand_complex_sync = Mock()
        client.predict_covalent_complex_sync = Mock()
        client.predict_dna_protein_complex_sync = Mock()
        client.predict_with_advanced_parameters_sync = Mock()
        client.predict_from_yaml_config_sync = Mock()
        client.predict_from_yaml_file_sync = Mock()
        client.health_check_sync = Mock()
        client.get_service_metadata_sync = Mock()
    
    # Create multi-endpoint client
    endpoints = [
        EndpointConfig(base_url=f"http://localhost:800{i}", weight=1.0)
        for i in range(3)
    ]
    
    multi_client = MultiEndpointClient(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.LEAST_LOADED,
        is_async=True
    )
    
    # Replace the actual clients with mocks
    for i, endpoint in enumerate(multi_client.endpoints):
        endpoint.client = clients[i]
    
    return multi_client, clients


@pytest.fixture
def mock_healthy_endpoints():
    """Create mock healthy endpoints for testing."""
    import time
    
    endpoints = []
    for i in range(3):
        endpoint = Mock()
        endpoint.endpoint_config = Mock()
        endpoint.endpoint_config.base_url = f"http://localhost:800{i}"
        endpoint.endpoint_config.weight = 1.0
        endpoint.endpoint_config.max_concurrent_requests = 10
        endpoint.is_healthy = True
        endpoint.current_requests = 0
        endpoint.total_requests = 0
        endpoint.failed_requests = 0
        endpoint.average_response_time = 0.0
        endpoint.last_health_check = time.time()
        endpoints.append(endpoint)
    
    return endpoints


@pytest.fixture
def mock_mixed_health_endpoints():
    """Create mock endpoints with mixed health status."""
    import time
    
    endpoints = []
    
    # Healthy endpoint
    healthy = Mock()
    healthy.endpoint_config = Mock()
    healthy.endpoint_config.base_url = "http://localhost:8000"
    healthy.endpoint_config.weight = 1.0
    healthy.endpoint_config.max_concurrent_requests = 10
    healthy.is_healthy = True
    healthy.current_requests = 0
    healthy.total_requests = 10
    healthy.failed_requests = 0
    healthy.average_response_time = 2.5
    healthy.last_health_check = time.time()
    endpoints.append(healthy)
    
    # Unhealthy endpoint
    unhealthy = Mock()
    unhealthy.endpoint_config = Mock()
    unhealthy.endpoint_config.base_url = "http://localhost:8001"
    unhealthy.endpoint_config.weight = 1.0
    unhealthy.endpoint_config.max_concurrent_requests = 10
    unhealthy.is_healthy = False
    unhealthy.current_requests = 0
    unhealthy.total_requests = 5
    unhealthy.failed_requests = 3
    unhealthy.average_response_time = 10.0
    unhealthy.last_health_check = time.time()
    endpoints.append(unhealthy)
    
    # Recovered endpoint
    recovered = Mock()
    recovered.endpoint_config = Mock()
    recovered.endpoint_config.base_url = "http://localhost:8002"
    recovered.endpoint_config.weight = 1.0
    recovered.endpoint_config.max_concurrent_requests = 10
    recovered.is_healthy = True
    recovered.current_requests = 0
    recovered.total_requests = 8
    recovered.failed_requests = 0
    recovered.average_response_time = 3.0
    recovered.last_health_check = time.time()
    endpoints.append(recovered)
    
    return endpoints


@pytest.fixture
def temp_yaml_file():
    """Create a temporary YAML file for testing."""
    yaml_content = """
    polymers:
      - id: A
        molecule_type: protein
        sequence: MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
    recycling_steps: 3
    sampling_steps: 50
    diffusion_samples: 1
    step_scale: 1.638
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_file = f.name
    
    yield yaml_file
    
    # Cleanup
    try:
        os.unlink(yaml_file)
    except OSError:
        pass


@pytest.fixture
def temp_compounds_file():
    """Create a temporary compounds file for testing."""
    compounds_content = "name,smiles,weight\nAspirin,CC(=O)OC1=CC=CC=C1C(=O)O,180.16\nIbuprofen,CC(C)CC1=CC=C(C=C1)C(C)C(=O)O,206.29"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(compounds_content)
        compounds_file = f.name
    
    yield compounds_file
    
    # Cleanup
    try:
        os.unlink(compounds_file)
    except OSError:
        pass


@pytest.fixture
def test_data():
    """Provide common test data."""
    return {
        "cdk2_sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        "sample_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
        "sample_ccd": "ASP",
        "sample_dna": "ATCGATCGATCGATCG",
        "sample_compounds": [
            {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
            {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
            {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1"},
        ]
    }


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "cli: marks tests as CLI tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Mark CLI tests
        if "cli" in item.nodeid.lower() or "CLI" in item.nodeid:
            item.add_marker(pytest.mark.cli)
        
        # Mark API tests
        if "api" in item.nodeid.lower() or "API" in item.nodeid:
            item.add_marker(pytest.mark.api)
        
        # Mark integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark unit tests
        if "unit" in item.nodeid.lower():
            item.add_marker(pytest.mark.unit)
        
        # Mark slow tests (those that might take longer)
        if any(keyword in item.nodeid.lower() for keyword in ["integration", "end_to_end", "workflow"]):
            item.add_marker(pytest.mark.slow)
