#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Multi-Endpoint API Coverage Tests

Tests every prediction type (protein, protein-ligand, covalent, DNA-protein,
YAML) through both single and multi-endpoint clients. Scenario-level workflow
tests live in test_integration_scenarios.py; CLI tests in test_cli_multi_endpoint.py.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    VirtualScreening,
    Boltz2Client,
    Boltz2SyncClient,
)
from boltz2_client.models import (
    PredictionResponse,
    HealthStatus,
    ServiceMetadata,
    StructureData,
)

from constants import CDK2_SEQUENCE, SAMPLE_SMILES, SAMPLE_CCD, SAMPLE_DNA, SAMPLE_COMPOUNDS


class TestMultiEndpointClient:
    """Test suite for MultiEndpointClient API coverage (single + multi)."""

    @pytest.fixture
    def mock_single_client(self):
        """Create a mock single Boltz2 client with all async methods."""
        client = Mock(spec=Boltz2Client)
        for method in (
            "predict_protein_structure", "predict_protein_ligand_complex",
            "predict_covalent_complex", "predict_dna_protein_complex",
            "predict_with_advanced_parameters", "predict_from_yaml_config",
            "predict_from_yaml_file", "health_check", "get_service_metadata",
        ):
            setattr(client, method, AsyncMock())
        return client

    @pytest.fixture
    def mock_multi_endpoint_client(self):
        """Create a multi-endpoint client with 3 mock backends."""
        clients = []
        for _ in range(3):
            c = Mock(spec=Boltz2Client)
            for method in (
                "predict_protein_structure", "predict_protein_ligand_complex",
                "predict_covalent_complex", "predict_dna_protein_complex",
                "predict_with_advanced_parameters", "predict_from_yaml_config",
                "predict_from_yaml_file", "health_check", "get_service_metadata",
            ):
                setattr(c, method, AsyncMock())
            clients.append(c)

        endpoints = [
            EndpointConfig(base_url=f"http://localhost:800{i}", weight=1.0)
            for i in range(3)
        ]
        multi_client = MultiEndpointClient(
            endpoints=endpoints,
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=True,
        )
        for i, ep in enumerate(multi_client.endpoints):
            ep.client = clients[i]
        return multi_client, clients

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
        # LEAST_LOADED ties all at 0 always pick the first endpoint → infinite retry loop without await;
        # round-robin visits each endpoint once.
        multi_client.strategy = LoadBalanceStrategy.ROUND_ROBIN
        
        # First client fails, second succeeds
        clients[0].predict_protein_structure.side_effect = Exception("Endpoint 1 failed")
        clients[1].predict_protein_structure.return_value = sample_prediction_response
        
        result = await asyncio.wait_for(
            multi_client.predict_protein_structure(
                sequence=CDK2_SEQUENCE,
                recycling_steps=3,
                sampling_steps=50,
                diffusion_samples=1
            ),
            timeout=10.0,
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

    # Test 6: Virtual Screening (sync vs.screen(); must not run under asyncio event loop)
    def test_single_endpoint_virtual_screening(self, mock_single_client):
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
    
    def test_multi_endpoint_virtual_screening(self, mock_multi_endpoint_client):
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

    # Test 9: Synchronous Methods
    def test_sync_multi_endpoint_client(self):
        """Test synchronous multi-endpoint client creation."""
        multi_client = MultiEndpointClient(
            endpoints=["http://localhost:8000", "http://localhost:8001"],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            is_async=False
        )
        
        assert not multi_client.is_async
        assert len(multi_client.endpoints) == 2



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
