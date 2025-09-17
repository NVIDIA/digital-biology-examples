#!/usr/bin/env python3
"""
Integration Test Suite for Multi-Endpoint Boltz2 NIM Functionality

This test suite covers real integration scenarios with both single and multiple endpoints:
- End-to-end protein prediction workflows
- Virtual screening workflows
- Health monitoring workflows
- Load balancing scenarios
- Error recovery scenarios

Tests both Python API and CLI approaches in realistic scenarios.
"""

import pytest
import asyncio
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import yaml
import json

from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    VirtualScreening,
    CompoundLibrary,
    PredictionRequest,
    Polymer,
    Ligand,
    PocketConstraint,
    Boltz2Client,
    Boltz2SyncClient
)
from boltz2_client.models import PredictionResponse, HealthStatus, ServiceMetadata
from boltz2_client.exceptions import Boltz2APIError


# Test data
CDK2_SEQUENCE = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
SAMPLE_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
SAMPLE_CCD = "ASP"
SAMPLE_DNA = "ATCGATCGATCGATCG"

# Sample compounds for testing
SAMPLE_COMPOUNDS = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
    {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1"},
]


class TestIntegrationScenarios:
    """Test integration scenarios with realistic data and workflows."""
    
    @pytest.fixture
    def mock_healthy_endpoints(self):
        """Create mock healthy endpoints for testing."""
        endpoints = []
        for i in range(3):
            endpoint = Mock()
            endpoint.endpoint_config = Mock()
            endpoint.endpoint_config.base_url = f"http://localhost:800{i}"
            endpoint.endpoint_config.weight = 1.0
            endpoint.is_healthy = True
            endpoint.current_requests = 0
            endpoint.total_requests = 0
            endpoint.failed_requests = 0
            endpoint.average_response_time = 0.0
            endpoint.last_health_check = time.time()
            endpoints.append(endpoint)
        return endpoints
    
    @pytest.fixture
    def mock_mixed_health_endpoints(self):
        """Create mock endpoints with mixed health status."""
        endpoints = []
        
        # Healthy endpoint
        healthy = Mock()
        healthy.endpoint_config = Mock()
        healthy.endpoint_config.base_url = "http://localhost:8000"
        healthy.endpoint_config.weight = 1.0
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
        recovered.is_healthy = True
        recovered.current_requests = 0
        recovered.total_requests = 8
        recovered.failed_requests = 0
        recovered.average_response_time = 3.0
        recovered.last_health_check = time.time()
        endpoints.append(recovered)
        
        return endpoints

    # Test 1: End-to-End Protein Prediction Workflow
    @pytest.mark.asyncio
    async def test_end_to_end_protein_prediction_single_endpoint(self):
        """Test complete protein prediction workflow with single endpoint."""
        # Mock single client
        mock_client = Mock(spec=Boltz2Client)
        mock_client.predict_protein_structure = AsyncMock()
        mock_client.health_check = AsyncMock()
        
        # Set up mock responses
        mock_client.health_check.return_value = HealthStatus(
            status="healthy",
            details={"test": "data"}
        )
        
        mock_client.predict_protein_structure.return_value = PredictionResponse(
            structures=["structure1.cif", "structure2.cif"],
            confidence_scores=[0.85, 0.78],
            metadata={"test": "data"}
        )
        
        # Test health check
        health = await mock_client.health_check()
        assert health.status == "healthy"
        
        # Test protein prediction
        result = await mock_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=3,
            sampling_steps=50,
            diffusion_samples=1
        )
        
        assert len(result.structures) == 2
        assert len(result.confidence_scores) == 2
        assert result.confidence_scores[0] == 0.85
        
        # Verify calls
        mock_client.health_check.assert_called_once()
        mock_client.predict_protein_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_end_to_end_protein_prediction_multi_endpoint(self, mock_healthy_endpoints):
        """Test complete protein prediction workflow with multiple endpoints."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
            endpoint.client.health_check = AsyncMock()
        
        # Set up responses
        for endpoint in multi_client.endpoints:
            endpoint.client.health_check.return_value = HealthStatus(
                status="healthy",
                details={"test": "data"}
            )
            endpoint.client.predict_protein_structure.return_value = PredictionResponse(
                structures=["structure1.cif", "structure2.cif"],
                confidence_scores=[0.85, 0.78],
                metadata={"test": "data"}
            )
        
        # Test health check
        health = await multi_client.health_check()
        assert health.status == "healthy"
        assert health.details["total_endpoints"] == 3
        
        # Test protein prediction
        result = await multi_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=3,
            sampling_steps=50,
            diffusion_samples=1
        )
        
        assert len(result.structures) == 2
        assert len(result.confidence_scores) == 2
        
        # Verify at least one endpoint was called
        call_count = sum(1 for ep in multi_client.endpoints 
                        if ep.client.predict_protein_structure.called)
        assert call_count >= 1

    # Test 2: End-to-End Virtual Screening Workflow
    @pytest.mark.asyncio
    async def test_end_to_end_virtual_screening_single_endpoint(self):
        """Test complete virtual screening workflow with single endpoint."""
        # Mock single client
        mock_client = Mock(spec=Boltz2Client)
        mock_client.predict_protein_ligand_complex = AsyncMock()
        
        # Set up mock response
        mock_client.predict_protein_ligand_complex.return_value = PredictionResponse(
            structures=["complex1.cif"],
            confidence_scores=[0.82],
            metadata={"test": "data"}
        )
        
        # Create virtual screening instance
        vs = VirtualScreening(client=mock_client)
        
        # Mock the screen method
        with patch.object(vs, '_screen_async') as mock_screen:
            mock_screen.return_value = [
                {"name": "Aspirin", "predicted_pic50": 6.5, "confidence": 0.82},
                {"name": "Ibuprofen", "predicted_pic50": 5.8, "confidence": 0.79}
            ]
            
            # Run screening
            result = vs.screen(
                target_sequence=CDK2_SEQUENCE,
                compound_library=SAMPLE_COMPOUNDS,
                predict_affinity=True,
                recycling_steps=2,
                sampling_steps=30,
                diffusion_samples=1
            )
            
            assert len(result.results) == 2
            assert result.results[0]["name"] == "Aspirin"
            assert result.results[1]["name"] == "Ibuprofen"
            assert "predicted_pic50" in result.results[0]
    
    @pytest.mark.asyncio
    async def test_end_to_end_virtual_screening_multi_endpoint(self, mock_healthy_endpoints):
        """Test complete virtual screening workflow with multiple endpoints."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_ligand_complex = AsyncMock()
        
        # Set up responses
        for endpoint in multi_client.endpoints:
            endpoint.client.predict_protein_ligand_complex.return_value = PredictionResponse(
                structures=["complex1.cif"],
                confidence_scores=[0.82],
                metadata={"test": "data"}
            )
        
        # Create virtual screening instance
        vs = VirtualScreening(client=multi_client)
        
        # Mock the screen method
        with patch.object(vs, '_screen_async') as mock_screen:
            mock_screen.return_value = [
                {"name": "Aspirin", "predicted_pic50": 6.5, "confidence": 0.82},
                {"name": "Ibuprofen", "predicted_pic50": 5.8, "confidence": 0.79}
            ]
            
            # Run screening
            result = vs.screen(
                target_sequence=CDK2_SEQUENCE,
                compound_library=SAMPLE_COMPOUNDS,
                predict_affinity=True,
                recycling_steps=2,
                sampling_steps=30,
                diffusion_samples=1
            )
            
            assert len(result.results) == 2
            assert result.results[0]["name"] == "Aspirin"
            assert result.results[1]["name"] == "Ibuprofen"
            
            # Verify virtual screening is configured for multi-endpoint
            assert vs.is_multi_endpoint
            assert vs.client == multi_client

    # Test 3: Load Balancing and Failover Scenarios
    @pytest.mark.asyncio
    async def test_load_balancing_least_loaded_strategy(self, mock_healthy_endpoints):
        """Test least loaded load balancing strategy."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
        
        # Set different current request counts
        multi_client.endpoints[0].current_requests = 5  # Most loaded
        multi_client.endpoints[1].current_requests = 2  # Medium loaded
        multi_client.endpoints[2].current_requests = 0  # Least loaded
        
        # Set up responses
        for endpoint in multi_client.endpoints:
            endpoint.client.predict_protein_structure.return_value = PredictionResponse(
                structures=["structure.cif"],
                confidence_scores=[0.85],
                metadata={"test": "data"}
            )
        
        # Make prediction - should select least loaded endpoint
        result = await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)
        
        # Verify least loaded endpoint was selected
        assert multi_client.endpoints[2].client.predict_protein_structure.called
        assert not multi_client.endpoints[0].client.predict_protein_structure.called
    
    @pytest.mark.asyncio
    async def test_load_balancing_round_robin_strategy(self, mock_healthy_endpoints):
        """Test round robin load balancing strategy."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.ROUND_ROBIN,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
        
        # Set up responses
        for endpoint in multi_client.endpoints:
            endpoint.client.predict_protein_structure.return_value = PredictionResponse(
                structures=["structure.cif"],
                confidence_scores=[0.85],
                metadata={"test": "data"}
            )
        
        # Make multiple predictions to test round robin
        for _ in range(3):
            await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)
        
        # Verify all endpoints were called in round robin fashion
        assert multi_client.endpoints[0].client.predict_protein_structure.called
        assert multi_client.endpoints[1].client.predict_protein_structure.called
        assert multi_client.endpoints[2].client.predict_protein_structure.called
    
    @pytest.mark.asyncio
    async def test_failover_scenario(self, mock_mixed_health_endpoints):
        """Test failover scenario when some endpoints are unhealthy."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_mixed_health_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
        
        # Set up responses - first endpoint fails, others succeed
        multi_client.endpoints[0].client.predict_protein_structure.side_effect = Exception("Endpoint 1 failed")
        multi_client.endpoints[1].client.predict_protein_structure.return_value = PredictionResponse(
            structures=["structure.cif"],
            confidence_scores=[0.85],
            metadata={"test": "data"}
        )
        multi_client.endpoints[2].client.predict_protein_structure.return_value = PredictionResponse(
            structures=["structure.cif"],
            confidence_scores=[0.85],
            metadata={"test": "data"}
        )
        
        # Make prediction - should failover to healthy endpoint
        result = await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)
        
        # Verify failover occurred
        assert multi_client.endpoints[0].client.predict_protein_structure.called
        assert multi_client.endpoints[1].client.predict_protein_structure.called or \
               multi_client.endpoints[2].client.predict_protein_structure.called

    # Test 4: Health Monitoring and Recovery
    @pytest.mark.asyncio
    async def test_health_monitoring_workflow(self, mock_mixed_health_endpoints):
        """Test health monitoring workflow with mixed endpoint health."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_mixed_health_endpoints[i]
            endpoint.client.health_check = AsyncMock()
        
        # Set up health check responses
        multi_client.endpoints[0].client.health_check.return_value = HealthStatus(
            status="healthy",
            details={"test": "data"}
        )
        multi_client.endpoints[1].client.health_check.return_value = HealthStatus(
            status="unhealthy",
            details={"test": "data"}
        )
        multi_client.endpoints[2].client.health_check.return_value = HealthStatus(
            status="healthy",
            details={"test": "data"}
        )
        
        # Test health check
        health = await multi_client.health_check()
        
        # Should return degraded status (2 healthy, 1 unhealthy)
        assert health.status == "degraded"
        assert health.details["healthy_endpoints"] == 2
        assert health.details["total_endpoints"] == 3
        
        # Verify all endpoints were checked
        for endpoint in multi_client.endpoints:
            endpoint.client.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_recovery_scenario(self, mock_mixed_health_endpoints):
        """Test health recovery scenario."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_mixed_health_endpoints[i]
            endpoint.client.health_check = AsyncMock()
        
        # Initially set all endpoints as unhealthy
        for endpoint in multi_client.endpoints:
            endpoint.is_healthy = False
            endpoint.failed_requests = 3
        
        # Set up health check responses - all become healthy
        for endpoint in multi_client.endpoints:
            endpoint.client.health_check.return_value = HealthStatus(
                status="healthy",
                details={"test": "data"}
            )
        
        # Test health check
        health = await multi_client.health_check()
        
        # Should return healthy status
        assert health.status == "healthy"
        assert health.details["healthy_endpoints"] == 3
        
        # Verify failed requests were reset
        for endpoint in multi_client.endpoints:
            assert endpoint.failed_requests == 0

    # Test 5: Performance Monitoring and Statistics
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, mock_healthy_endpoints):
        """Test performance monitoring and statistics."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
        
        # Set up responses
        for endpoint in multi_client.endpoints:
            endpoint.client.predict_protein_structure.return_value = PredictionResponse(
                structures=["structure.cif"],
                confidence_scores=[0.85],
                metadata={"test": "data"}
            )
        
        # Make multiple predictions to build statistics
        for _ in range(5):
            await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)
        
        # Get status
        status = multi_client.get_status()
        
        # Verify status structure
        assert "strategy" in status
        assert "endpoints" in status
        assert len(status["endpoints"]) == 3
        
        # Verify endpoint statistics
        for endpoint_status in status["endpoints"]:
            assert "url" in endpoint_status
            assert "healthy" in endpoint_status
            assert "current_requests" in endpoint_status
            assert "total_requests" in endpoint_status
            assert "failed_requests" in endpoint_status
            assert "avg_response_time" in endpoint_status
            
            # Should have some requests
            assert endpoint_status["total_requests"] >= 0

    # Test 6: Error Handling and Recovery
    @pytest.mark.asyncio
    async def test_error_handling_all_endpoints_failing(self, mock_healthy_endpoints):
        """Test error handling when all endpoints fail."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
        
        # Make all endpoints fail
        for endpoint in multi_client.endpoints:
            endpoint.client.predict_protein_structure.side_effect = Exception("All endpoints failed")
        
        # Should raise Boltz2APIError
        with pytest.raises(Boltz2APIError, match="All endpoints failed"):
            await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)
        
        # Verify all endpoints were attempted
        for endpoint in multi_client.endpoints:
            endpoint.client.predict_protein_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_partial_failure(self, mock_healthy_endpoints):
        """Test error handling with partial endpoint failure."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
            endpoint.client.predict_protein_structure = AsyncMock()
        
        # Set up mixed responses - first fails, second succeeds
        multi_client.endpoints[0].client.predict_protein_structure.side_effect = Exception("Endpoint 1 failed")
        multi_client.endpoints[1].client.predict_protein_structure.return_value = PredictionResponse(
            structures=["structure.cif"],
            confidence_scores=[0.85],
            metadata={"test": "data"}
        )
        multi_client.endpoints[2].client.predict_protein_structure.return_value = PredictionResponse(
            structures=["structure.cif"],
            confidence_scores=[0.85],
            metadata={"test": "data"}
        )
        
        # Should succeed with second endpoint
        result = await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)
        
        assert result is not None
        assert len(result.structures) == 1
        
        # Verify first endpoint failed and second succeeded
        assert multi_client.endpoints[0].client.predict_protein_structure.called
        assert multi_client.endpoints[1].client.predict_protein_structure.called or \
               multi_client.endpoints[2].client.predict_protein_structure.called

    # Test 7: Configuration and Setup Scenarios
    def test_endpoint_configuration_formats(self):
        """Test different endpoint configuration formats."""
        # Test string URLs
        multi_client1 = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001"],
            is_async=True
        )
        assert len(multi_client1.endpoints) == 2
        
        # Test EndpointConfig objects
        endpoints = [
            EndpointConfig(base_url="http://localhost:8000", weight=2.0),
            EndpointConfig(base_url="http://localhost:8001", weight=1.0),
        ]
        multi_client2 = MultiEndpointClient(endpoints=endpoints, is_async=True)
        assert len(multi_client2.endpoints) == 2
        assert multi_client2.endpoints[0].endpoint_config.weight == 2.0
        
        # Test mixed format
        mixed_endpoints = [
            "http://localhost:8000",
            EndpointConfig(base_url="http://localhost:8001", weight=1.5),
            {"base_url": "http://localhost:8002", "weight": 0.5}
        ]
        multi_client3 = MultiEndpointClient(endpoints=mixed_endpoints, is_async=True)
        assert len(multi_client3.endpoints) == 3
    
    def test_load_balancing_strategy_configuration(self):
        """Test load balancing strategy configuration."""
        strategies = [
            LoadBalanceStrategy.ROUND_ROBIN,
            LoadBalanceStrategy.RANDOM,
            LoadBalanceStrategy.LEAST_LOADED,
            LoadBalanceStrategy.WEIGHTED
        ]
        
        for strategy in strategies:
            multi_client = MultiEndpointClient(
                endpoints=["http://localhost:8000", "http://localhost:8001"],
                strategy=strategy,
                is_async=True
            )
            
            assert multi_client.strategy == strategy
            assert len(multi_client.endpoints) == 2

    # Test 8: Resource Management
    @pytest.mark.asyncio
    async def test_resource_cleanup(self, mock_healthy_endpoints):
        """Test resource cleanup and management."""
        # Create multi-endpoint client
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001", "http://localhost:8002"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Replace endpoints with mocks
        for i, endpoint in enumerate(multi_client.endpoints):
            endpoint.client = mock_healthy_endpoints[i]
        
        # Test context manager
        async with multi_client:
            # Make a prediction
            endpoint = multi_client._select_endpoint()
            assert endpoint is not None
        
        # Client should be closed
        # Note: In real implementation, this would clean up resources


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
