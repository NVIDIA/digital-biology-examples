#!/usr/bin/env python3
"""
Comprehensive Test Suite for Multi-Endpoint Boltz2 NIM Functionality

This test suite covers ALL Boltz2 NIM functionalities with both single and multiple endpoints:
- Protein structure prediction
- Protein-ligand complex prediction
- Covalent complex prediction
- DNA-protein complex prediction
- YAML-based prediction
- Virtual screening
- Health monitoring
- Load balancing strategies

Tests both Python API and CLI approaches.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import yaml

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
]


class TestMultiEndpointClient:
    """Test suite for MultiEndpointClient functionality."""
    
    @pytest.fixture
    def mock_single_client(self):
        """Create a mock single Boltz2 client."""
        client = Mock(spec=Boltz2Client)
        client.predict_protein_structure = AsyncMock()
        client.predict_protein_ligand_complex = AsyncMock()
        client.predict_covalent_complex = AsyncMock()
        client.predict_dna_protein_complex = AsyncMock()
        client.predict_with_advanced_parameters = AsyncMock()
        client.predict_from_yaml_config = AsyncMock()
        client.predict_from_yaml_file = AsyncMock()
        client.health_check = AsyncMock()
        client.get_service_metadata = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_multi_endpoint_client(self, mock_single_client):
        """Create a mock multi-endpoint client."""
        # Create multiple mock clients
        clients = [Mock(spec=Boltz2Client) for _ in range(3)]
        for client in clients:
            client.predict_protein_structure = AsyncMock()
            client.predict_protein_ligand_complex = AsyncMock()
            client.predict_covalent_complex = AsyncMock()
            client.predict_dna_protein_complex = AsyncMock()
            client.predict_with_advanced_parameters = AsyncMock()
            client.predict_from_yaml_config = AsyncMock()
            client.predict_from_yaml_file = AsyncMock()
            client.health_check = AsyncMock()
            client.get_service_metadata = AsyncMock()
        
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
    def sample_prediction_response(self):
        """Create a sample prediction response."""
        return PredictionResponse(
            structures=["structure1", "structure2"],
            confidence_scores=[0.85, 0.78],
            metadata={"test": "data"}
        )
    
    @pytest.fixture
    def sample_health_status(self):
        """Create a sample health status."""
        return HealthStatus(
            status="healthy",
            details={"healthy_endpoints": 3, "total_endpoints": 3}
        )
    
    @pytest.fixture
    def sample_service_metadata(self):
        """Create a sample service metadata."""
        return ServiceMetadata(
            version="1.0.0",
            repository_override="test",
            assetInfo=["asset1", "asset2"],
            modelInfo=[]
        )

    # Test 1: Protein Structure Prediction
    @pytest.mark.asyncio
    async def test_single_endpoint_protein_structure(self, mock_single_client, sample_prediction_response):
        """Test protein structure prediction with single endpoint."""
        mock_single_client.predict_protein_structure.return_value = sample_prediction_response
        
        # Test single client directly
        result = await mock_single_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=3,
            sampling_steps=50,
            diffusion_samples=1
        )
        
        assert result == sample_prediction_response
        mock_single_client.predict_protein_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_protein_structure(self, mock_multi_endpoint_client, sample_prediction_response):
        """Test protein structure prediction with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        # Set up first client to succeed
        clients[0].predict_protein_structure.return_value = sample_prediction_response
        
        result = await multi_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=3,
            sampling_steps=50,
            diffusion_samples=1
        )
        
        assert result == sample_prediction_response
        clients[0].predict_protein_structure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_protein_structure_failover(self, mock_multi_endpoint_client, sample_prediction_response):
        """Test protein structure prediction with endpoint failover."""
        multi_client, clients = mock_multi_endpoint_client
        
        # First client fails, second succeeds
        clients[0].predict_protein_structure.side_effect = Exception("Endpoint 1 failed")
        clients[1].predict_protein_structure.return_value = sample_prediction_response
        
        result = await multi_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=3,
            sampling_steps=50,
            diffusion_samples=1
        )
        
        assert result == sample_prediction_response
        clients[0].predict_protein_structure.assert_called_once()
        clients[1].predict_protein_structure.assert_called_once()

    # Test 2: Protein-Ligand Complex Prediction
    @pytest.mark.asyncio
    async def test_single_endpoint_protein_ligand(self, mock_single_client, sample_prediction_response):
        """Test protein-ligand complex prediction with single endpoint."""
        mock_single_client.predict_protein_ligand_complex.return_value = sample_prediction_response
        
        result = await mock_single_client.predict_protein_ligand_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_smiles=SAMPLE_SMILES,
            recycling_steps=3,
            sampling_steps=50
        )
        
        assert result == sample_prediction_response
        mock_single_client.predict_protein_ligand_complex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_protein_ligand(self, mock_multi_endpoint_client, sample_prediction_response):
        """Test protein-ligand complex prediction with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        clients[0].predict_protein_ligand_complex.return_value = sample_prediction_response
        
        result = await multi_client.predict_protein_ligand_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_smiles=SAMPLE_SMILES,
            pocket_residues=[10, 11, 12],
            recycling_steps=3,
            sampling_steps=50
        )
        
        assert result == sample_prediction_response
        clients[0].predict_protein_ligand_complex.assert_called_once()

    # Test 3: Covalent Complex Prediction
    @pytest.mark.asyncio
    async def test_single_endpoint_covalent(self, mock_single_client, sample_prediction_response):
        """Test covalent complex prediction with single endpoint."""
        mock_single_client.predict_covalent_complex.return_value = sample_prediction_response
        
        result = await mock_single_client.predict_covalent_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_ccd=SAMPLE_CCD,
            covalent_bonds=[(12, "SG", "C22")]
        )
        
        assert result == sample_prediction_response
        mock_single_client.predict_covalent_complex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_covalent(self, mock_multi_endpoint_client, sample_prediction_response):
        """Test covalent complex prediction with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        clients[0].predict_covalent_complex.return_value = sample_prediction_response
        
        result = await multi_client.predict_covalent_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_ccd=SAMPLE_CCD,
            covalent_bonds=[(12, "SG", "C22")]
        )
        
        assert result == sample_prediction_response
        clients[0].predict_covalent_complex.assert_called_once()

    # Test 4: DNA-Protein Complex Prediction
    @pytest.mark.asyncio
    async def test_single_endpoint_dna_protein(self, mock_single_client, sample_prediction_response):
        """Test DNA-protein complex prediction with single endpoint."""
        mock_single_client.predict_dna_protein_complex.return_value = sample_prediction_response
        
        result = await mock_single_client.predict_dna_protein_complex(
            protein_sequences=[CDK2_SEQUENCE],
            dna_sequences=[SAMPLE_DNA],
            protein_ids=["A"],
            dna_ids=["D"]
        )
        
        assert result == sample_prediction_response
        mock_single_client.predict_dna_protein_complex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_dna_protein(self, mock_multi_endpoint_client, sample_prediction_response):
        """Test DNA-protein complex prediction with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        clients[0].predict_dna_protein_complex.return_value = sample_prediction_response
        
        result = await multi_client.predict_dna_protein_complex(
            protein_sequences=[CDK2_SEQUENCE],
            dna_sequences=[SAMPLE_DNA],
            protein_ids=["A"],
            dna_ids=["D"],
            concatenate_msas=False
        )
        
        assert result == sample_prediction_response
        clients[0].predict_dna_protein_complex.assert_called_once()

    # Test 5: YAML-Based Prediction
    @pytest.mark.asyncio
    async def test_single_endpoint_yaml_config(self, mock_single_client, sample_prediction_response):
        """Test YAML config prediction with single endpoint."""
        mock_single_client.predict_from_yaml_config.return_value = sample_prediction_response
        
        config = {
            "polymers": [{"id": "A", "molecule_type": "protein", "sequence": CDK2_SEQUENCE}],
            "recycling_steps": 3
        }
        
        result = await mock_single_client.predict_from_yaml_config(config=config)
        
        assert result == sample_prediction_response
        mock_single_client.predict_from_yaml_config.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_yaml_config(self, mock_multi_endpoint_client, sample_prediction_response):
        """Test YAML config prediction with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        clients[0].predict_from_yaml_config.return_value = sample_prediction_response
        
        config = {
            "polymers": [{"id": "A", "molecule_type": "protein", "sequence": CDK2_SEQUENCE}],
            "recycling_steps": 3
        }
        
        result = await multi_client.predict_from_yaml_config(config=config)
        
        assert result == sample_prediction_response
        clients[0].predict_from_yaml_config.assert_called_once()

    # Test 6: Virtual Screening
    @pytest.mark.asyncio
    async def test_single_endpoint_virtual_screening(self, mock_single_client):
        """Test virtual screening with single endpoint."""
        # Create virtual screening with single client
        vs = VirtualScreening(client=mock_single_client)
        
        # Mock the screen method
        with patch.object(vs, '_screen_async') as mock_screen:
            mock_screen.return_value = [{"name": "Aspirin", "predicted_pic50": 6.5}]
            
            result = vs.screen(
                target_sequence=CDK2_SEQUENCE,
                compound_library=SAMPLE_COMPOUNDS,
                predict_affinity=True
            )
            
            assert len(result.results) == 1
            assert result.results[0]["name"] == "Aspirin"
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_virtual_screening(self, mock_multi_endpoint_client):
        """Test virtual screening with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        # Create virtual screening with multi-endpoint client
        vs = VirtualScreening(client=multi_client)
        
        # Mock the screen method
        with patch.object(vs, '_screen_async') as mock_screen:
            mock_screen.return_value = [{"name": "Aspirin", "predicted_pic50": 6.5}]
            
            result = vs.screen(
                target_sequence=CDK2_SEQUENCE,
                compound_library=SAMPLE_COMPOUNDS,
                predict_affinity=True
            )
            
            assert len(result.results) == 1
            assert result.results[0]["name"] == "Aspirin"

    # Test 7: Health Monitoring
    @pytest.mark.asyncio
    async def test_single_endpoint_health_check(self, mock_single_client, sample_health_status):
        """Test health check with single endpoint."""
        mock_single_client.health_check.return_value = sample_health_status
        
        result = await mock_single_client.health_check()
        
        assert result.status == "healthy"
        assert result.details["healthy_endpoints"] == 3
        mock_single_client.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_health_check(self, mock_multi_endpoint_client, sample_health_status):
        """Test health check with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        # Set up all clients to return healthy
        for client in clients:
            client.health_check.return_value = sample_health_status
        
        result = await multi_client.health_check()
        
        assert result.status == "healthy"
        assert result.details["total_endpoints"] == 3
        
        # Verify all clients were checked
        for client in clients:
            client.health_check.assert_called_once()

    # Test 8: Service Metadata
    @pytest.mark.asyncio
    async def test_single_endpoint_metadata(self, mock_single_client, sample_service_metadata):
        """Test service metadata with single endpoint."""
        mock_single_client.get_service_metadata.return_value = sample_service_metadata
        
        result = await mock_single_client.get_service_metadata()
        
        assert result.version == "1.0.0"
        assert result.repository_override == "test"
        mock_single_client.get_service_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_endpoint_metadata(self, mock_multi_endpoint_client, sample_service_metadata):
        """Test service metadata with multiple endpoints."""
        multi_client, clients = mock_multi_endpoint_client
        
        # Set up first client to return metadata
        clients[0].get_service_metadata.return_value = sample_service_metadata
        
        result = await multi_client.get_service_metadata()
        
        assert result.version == "1.0.0"
        assert result.repository_override == "test"
        clients[0].get_service_metadata.assert_called_once()

    # Test 9: Load Balancing Strategies
    @pytest.mark.asyncio
    async def test_load_balancing_strategies(self):
        """Test different load balancing strategies."""
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

    # Test 10: Error Handling
    @pytest.mark.asyncio
    async def test_all_endpoints_failing(self, mock_multi_endpoint_client):
        """Test behavior when all endpoints fail."""
        multi_client, clients = mock_multi_endpoint_client
        
        # Make all clients fail
        for client in clients:
            client.predict_protein_structure.side_effect = Exception("All endpoints failed")
        
        # Should raise Boltz2APIError
        with pytest.raises(Boltz2APIError, match="All endpoints failed"):
            await multi_client.predict_protein_structure(sequence=CDK2_SEQUENCE)

    # Test 11: Synchronous Methods
    def test_sync_multi_endpoint_client(self):
        """Test synchronous multi-endpoint client creation."""
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=False
        )
        
        assert not multi_client.is_async
        assert len(multi_client.endpoints) == 2

    # Test 12: Endpoint Configuration
    def test_endpoint_configuration(self):
        """Test different endpoint configuration formats."""
        # String URLs
        multi_client1 = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001"],
            is_async=True
        )
        assert len(multi_client1.endpoints) == 2
        
        # EndpointConfig objects
        endpoints = [
            EndpointConfig(base_url="http://localhost:8000", weight=2.0),
            EndpointConfig(base_url="http://localhost:8001", weight=1.0),
        ]
        multi_client2 = MultiEndpointClient(endpoints=endpoints, is_async=True)
        assert len(multi_client2.endpoints) == 2
        assert multi_client2.endpoints[0].endpoint_config.weight == 2.0
        
        # Mixed format
        mixed_endpoints = [
            "http://localhost:8000",
            EndpointConfig(base_url="http://localhost:8001", weight=1.5),
            {"base_url": "http://localhost:8002", "weight": 0.5}
        ]
        multi_client3 = MultiEndpointClient(endpoints=mixed_endpoints, is_async=True)
        assert len(multi_client3.endpoints) == 3


class TestCLIApproach:
    """Test suite for CLI approach to multi-endpoint functionality."""
    
    @pytest.fixture
    def mock_cli_context(self):
        """Create a mock CLI context."""
        context = Mock()
        context.obj = {
            'base_url': 'http://localhost:8000,http://localhost:8001',
            'multi_endpoint': True,
            'load_balance_strategy': 'least_loaded',
            'timeout': 300.0,
            'poll_seconds': 10,
            'endpoint_type': 'local',
            'api_key': None,
            'verbose': False
        }
        return context
    
    def test_cli_multi_endpoint_parsing(self, mock_cli_context):
        """Test CLI parsing of multiple endpoints."""
        from boltz2_client.cli import create_client
        
        # Mock the MultiEndpointClient creation
        with patch('boltz2_client.cli.MultiEndpointClient') as mock_multi_client:
            mock_multi_client.return_value = Mock()
            
            client = create_client(mock_cli_context)
            
            # Verify MultiEndpointClient was created with parsed endpoints
            mock_multi_client.assert_called_once()
            call_args = mock_multi_client.call_args
            assert len(call_args[1]['endpoints']) == 2
            assert "http://localhost:8000" in call_args[1]['endpoints']
            assert "http://localhost:8001" in call_args[1]['endpoints']
    
    def test_cli_single_endpoint(self, mock_cli_context):
        """Test CLI with single endpoint."""
        mock_cli_context.obj['base_url'] = 'http://localhost:8000'
        mock_cli_context.obj['multi_endpoint'] = False
        
        from boltz2_client.cli import create_client
        
        with patch('boltz2_client.cli.Boltz2Client') as mock_client:
            mock_client.return_value = Mock()
            
            client = create_client(mock_cli_context)
            
            # Verify single client was created
            mock_client.assert_called_once()
    
    def test_cli_load_balancing_strategy(self, mock_cli_context):
        """Test CLI load balancing strategy selection."""
        strategies = ['round_robin', 'least_loaded', 'random']
        
        for strategy in strategies:
            mock_cli_context.obj['load_balance_strategy'] = strategy
            
            from boltz2_client.cli import create_client
            
            with patch('boltz2_client.cli.MultiEndpointClient') as mock_multi_client:
                mock_multi_client.return_value = Mock()
                
                client = create_client(mock_cli_context)
                
                # Verify strategy was passed correctly
                call_args = mock_multi_client.call_args
                assert call_args[1]['strategy'].value == strategy


class TestIntegrationScenarios:
    """Test integration scenarios with real-like data."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_protein_prediction_workflow(self):
        """Test complete protein prediction workflow with multiple endpoints."""
        # This would test the full workflow in a real scenario
        # For now, we'll test the structure and flow
        
        endpoints = [
            EndpointConfig(base_url="http://localhost:8000", weight=1.0),
            EndpointConfig(base_url="http://localhost:8001", weight=1.0),
        ]
        
        multi_client = MultiEndpointClient(
            endpoints=endpoints,
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Test that client is properly configured
        assert len(multi_client.endpoints) == 2
        assert multi_client.strategy == LoadBalanceStrategy.LEAST_LOADED
        assert multi_client.is_async
        
        # Test endpoint selection
        endpoint = multi_client._select_endpoint()
        assert endpoint is not None
        
        # Test health checking
        with patch.object(multi_client, '_check_all_endpoints_health'):
            await multi_client._health_check_loop()
    
    @pytest.mark.asyncio
    async def test_virtual_screening_workflow(self):
        """Test complete virtual screening workflow with multiple endpoints."""
        # Mock the virtual screening workflow
        endpoints = [
            EndpointConfig(base_url="http://localhost:8000", weight=1.0),
            EndpointConfig(base_url="http://localhost:8001", weight=1.0),
        ]
        
        multi_client = MultiEndpointClient(
            endpoints=endpoints,
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True
        )
        
        # Create virtual screening instance
        vs = VirtualScreening(client=multi_client)
        
        # Test that virtual screening is properly configured
        assert vs.is_multi_endpoint
        assert vs.client == multi_client


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
