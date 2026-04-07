# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Basic tests for the Boltz-2 Python client.

These tests verify that the package can be imported and basic functionality works.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from boltz2_client import (
    Boltz2Client,
    Boltz2SyncClient,
    PredictionRequest,
    Polymer,
    Ligand,
    get_version,
)
from boltz2_client.utils import validate_sequence, calculate_sequence_stats


def test_version():
    """Test that version can be retrieved."""
    version = get_version()
    assert isinstance(version, str)
    assert len(version) > 0


def test_polymer_creation():
    """Test creating a valid polymer."""
    polymer = Polymer(
        id="A",
        molecule_type="protein",
        sequence="MKTVRQERLK"
    )
    
    assert polymer.id == "A"
    assert polymer.molecule_type == "protein"
    assert polymer.sequence == "MKTVRQERLK"
    assert polymer.cyclic is False
    assert len(polymer.modifications) == 0


def test_polymer_validation():
    """Test polymer sequence validation."""
    # Valid protein sequence
    polymer = Polymer(
        id="A",
        molecule_type="protein",
        sequence="MKTVRQERLK"
    )
    assert polymer.sequence == "MKTVRQERLK"
    
    # Invalid protein sequence should raise validation error
    with pytest.raises(ValueError):
        Polymer(
            id="A",
            molecule_type="protein",
            sequence="INVALID123"
        )


def test_ligand_creation():
    """Test creating a valid ligand."""
    ligand = Ligand(
        id="LIG1",
        smiles="CC(=O)OC1=CC=CC=C1C(=O)O"
    )
    
    assert ligand.id == "LIG1"
    assert ligand.smiles == "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_prediction_request():
    """Test creating a prediction request."""
    polymer = Polymer(
        id="A",
        molecule_type="protein",
        sequence="MKTVRQERLK"
    )
    
    request = PredictionRequest(polymers=[polymer])
    
    assert len(request.polymers) == 1
    assert request.polymers[0].id == "A"
    assert request.recycling_steps == 3  # default
    assert request.sampling_steps == 50  # default


def test_sequence_validation():
    """Test sequence validation utility."""
    # Valid sequences
    assert validate_sequence("MKTVRQERLK", "protein") is True
    assert validate_sequence("ATCG", "dna") is True
    assert validate_sequence("AUCG", "rna") is True
    
    # Invalid sequences
    with pytest.raises(ValueError):
        validate_sequence("INVALID123", "protein")
    
    with pytest.raises(ValueError):
        validate_sequence("", "protein")


def test_sequence_stats():
    """Test sequence statistics calculation."""
    stats = calculate_sequence_stats("MKTVRQERLK", "protein")
    
    assert stats["length"] == 10
    assert stats["type"] == "protein"
    assert "composition" in stats
    assert "molecular_weight" in stats
    assert stats["molecular_weight"] > 0


def test_client_initialization():
    """Test client initialization."""
    # Async client
    client = Boltz2Client("http://localhost:8000")
    assert client.base_url == "http://localhost:8000"
    assert client.timeout == 300.0
    
    # Sync client
    sync_client = Boltz2SyncClient("http://localhost:8000")
    assert sync_client._async_client.base_url == "http://localhost:8000"


@pytest.mark.asyncio
@patch('boltz2_client.client.httpx.AsyncClient')
async def test_health_check_mock(mock_client_cls):
    """Test health check with mocked response."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response

    mock_client_cls.return_value.__aenter__.return_value = mock_client_instance

    client = Boltz2Client("http://localhost:8000")
    result = await client.health_check()

    assert result.status == "healthy"


def test_imports():
    """Test that all expected modules can be imported."""
    # Test main imports
    from boltz2_client import Boltz2Client, Boltz2SyncClient
    from boltz2_client.models import Polymer, Ligand, PredictionRequest
    from boltz2_client.exceptions import Boltz2Error, Boltz2ValidationError
    from boltz2_client.utils import validate_sequence, save_structure
    
    # Verify classes exist
    assert Boltz2Client is not None
    assert Boltz2SyncClient is not None
    assert Polymer is not None
    assert Ligand is not None
    assert PredictionRequest is not None


if __name__ == "__main__":
    pytest.main([__file__]) 