
"""
Unit tests for MSA Search functionality.

Tests the MSA Search client, format conversion, and integration features.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

from boltz2_client import Boltz2Client
from boltz2_client.msa_search import (
    MSASearchClient, MSASearchRequest, MSASearchResponse,
    MSAFormatConverter, MSASearchIntegration
)
from boltz2_client.models import AlignmentFileRecord


# Test data
TEST_SEQUENCE = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
TEST_A3M_CONTENT = """>query
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>UniRef90_A0A1234567|organism=Test_organism|identity=90.0
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVL---
>UniRef90_B0B9876543|organism=Another_organism|identity=85.0
MKTVRQERLKSIVR-LERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
"""

TEST_FASTA_CONTENT = """>query
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
>UniRef90_A0A1234567
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVL
>UniRef90_B0B9876543
MKTVRQERLKSIVRLERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
"""

TEST_STO_CONTENT = """# STOCKHOLM 1.0
#=GF ID Test_MSA
#=GF DE Test MSA for unit tests
query                    MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
UniRef90_A0A1234567      MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVL---
UniRef90_B0B9876543      MKTVRQERLKSIVR-LERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
//
"""


class TestMSASearchClient:
    """Test MSA Search client functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test MSA search client."""
        return MSASearchClient(
            endpoint_url="http://test-msa-nim:8000",
            api_key="test-key"
        )
    
    @pytest.fixture
    def mock_response(self):
        """Create mock MSA search response."""
        return {
            "alignments": {
                "uniref90": {
                    "a3m": {
                        "alignment": TEST_A3M_CONTENT,
                        "format": "a3m"
                    },
                    "fasta": {
                        "alignment": TEST_FASTA_CONTENT,
                        "format": "fasta"
                    }
                }
            },
            "metrics": {
                "search_time": 5.2,
                "total_sequences": 3
            }
        }
    
    @pytest.mark.asyncio
    async def test_search_basic(self, client, mock_response):
        """Test basic MSA search functionality."""
        # Create a proper async context manager mock for aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Create the mock session object
            mock_session = AsyncMock()
            
            # Create mock response object
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            # Set up the post context manager properly
            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_cm
            
            # Set up the session context manager properly
            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_cm
            
            response = await client.search(
                sequence=TEST_SEQUENCE,
                databases=["uniref90"],
                max_msa_sequences=500
            )
            
            assert isinstance(response, MSASearchResponse)
            assert "uniref90" in response.alignments
            assert "a3m" in response.alignments["uniref90"]
            assert response.metrics["total_sequences"] == 3
    
    @pytest.mark.asyncio
    async def test_search_with_params(self, client, mock_response):
        """Test MSA search with custom parameters."""
        # Create a proper async context manager mock for aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Create the mock session object
            mock_session = AsyncMock()
            
            # Create mock response object
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            # Set up the post context manager properly
            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_cm
            
            # Set up the session context manager properly
            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_cm
            
            response = await client.search(
                sequence=TEST_SEQUENCE,
                databases=["uniref90", "pdb70"],
                e_value=0.001,
                max_msa_sequences=1000,
                iterations=3,
                output_alignment_formats=["a3m", "fasta", "sto"]
            )
            
            # Verify request was made correctly
            call_args = mock_session.post.call_args
            assert call_args[0][0].endswith("/biology/colabfold/msa-search/predict")
            request_data = call_args[1]["json"]
            assert request_data["sequence"] == TEST_SEQUENCE
            assert request_data["databases"] == ["uniref90", "pdb70"]
            assert request_data["e_value"] == 0.001
            assert request_data["max_msa_sequences"] == 1000
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling in MSA search."""
        # Import the exception class
        from boltz2_client.exceptions import Boltz2APIError
        
        # Create a proper async context manager mock for aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Create the mock session object
            mock_session = AsyncMock()
            
            # Create mock response object
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value={"error": "Invalid sequence"})
            mock_resp.text = AsyncMock(return_value='{"error": "Invalid sequence"}')
            
            # Set up the post context manager properly
            mock_post_cm = AsyncMock()
            mock_post_cm.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_post_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_cm
            
            # Set up the session context manager properly
            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_cm
            
            with pytest.raises(Boltz2APIError) as exc_info:
                await client.search(sequence="INVALID")
            
            assert "Invalid sequence" in str(exc_info.value)


class TestMSAFormatConverter:
    """Test MSA format conversion functionality."""
    
    @pytest.fixture
    def response(self):
        """Create test MSA search response."""
        return MSASearchResponse(
            alignments={
                "uniref90": {
                    "a3m": {
                        "alignment": TEST_A3M_CONTENT,
                        "format": "a3m"
                    },
                    "fasta": {
                        "alignment": TEST_FASTA_CONTENT,
                        "format": "fasta"
                    },
                    "sto": {
                        "alignment": TEST_STO_CONTENT,
                        "format": "sto"
                    }
                }
            }
        )
    
    def test_extract_a3m(self, response):
        """Test A3M format extraction."""
        a3m_content = MSAFormatConverter.extract_alignment(response, "a3m")
        assert a3m_content == TEST_A3M_CONTENT
    
    def test_extract_fasta(self, response):
        """Test FASTA format extraction."""
        fasta_content = MSAFormatConverter.extract_alignment(response, "fasta")
        assert fasta_content == TEST_FASTA_CONTENT
    
    def test_extract_sto(self, response):
        """Test Stockholm format extraction."""
        sto_content = MSAFormatConverter.extract_alignment(response, "sto")
        assert sto_content == TEST_STO_CONTENT
    
    def test_extract_format(self, response):
        """Test generic format extraction."""
        # Test extracting different formats
        assert MSAFormatConverter.extract_alignment(response, "a3m") == TEST_A3M_CONTENT
        assert MSAFormatConverter.extract_alignment(response, "fasta") == TEST_FASTA_CONTENT
        assert MSAFormatConverter.extract_alignment(response, "sto") == TEST_STO_CONTENT
        
        # Test missing format
        assert MSAFormatConverter.extract_alignment(response, "nonexistent") is None
    
    def test_get_all_alignments(self, response):
        """Test getting all alignments."""
        all_alignments = MSAFormatConverter.get_all_alignments(response)
        
        assert isinstance(all_alignments, dict)
        assert "uniref90" in all_alignments
        assert "a3m" in all_alignments["uniref90"]
        assert all_alignments["uniref90"]["a3m"] == TEST_A3M_CONTENT
        assert all_alignments["uniref90"]["fasta"] == TEST_FASTA_CONTENT
        assert all_alignments["uniref90"]["sto"] == TEST_STO_CONTENT


class TestMSASearchIntegration:
    """Test MSA Search integration functionality."""
    
    @pytest.fixture
    def integration(self, tmp_path):
        """Create test MSA search integration."""
        client = MSASearchClient(
            endpoint_url="http://test-msa-nim:8000",
            api_key="test-key"
        )
        return MSASearchIntegration(client)
    
    @pytest.fixture
    def mock_response(self):
        """Create mock MSA search response."""
        return MSASearchResponse(
            alignments={
                "uniref90": {
                    "a3m": {
                        "alignment": TEST_A3M_CONTENT,
                        "format": "a3m"
                    }
                }
            }
        )
    
    @pytest.mark.asyncio
    async def test_search_and_save(self, integration, mock_response, tmp_path):
        """Test search and save functionality."""
        with patch.object(integration.client, 'search', return_value=mock_response):
            file_path = await integration.search_and_save(
                sequence=TEST_SEQUENCE,
                output_format="a3m",
                output_path=str(tmp_path / "test.a3m")
            )
            
            assert Path(file_path).exists()
            with open(file_path, 'r') as f:
                content = f.read()
            assert content == TEST_A3M_CONTENT
    
    @pytest.mark.asyncio
    async def test_search_and_prepare_for_boltz(self, integration, mock_response):
        """Test search and prepare for Boltz functionality."""
        with patch.object(integration.client, 'search', return_value=mock_response):
            boltz_data = await integration.search_and_prepare_for_boltz(
                sequence=TEST_SEQUENCE,
                polymer_id="A",
                databases=["uniref90"]
            )
            
            assert isinstance(boltz_data, dict)
            assert "uniref90" in boltz_data
            assert "a3m" in boltz_data["uniref90"]


class TestBoltz2ClientIntegration:
    """Test integration with main Boltz2Client."""
    
    @pytest.fixture
    def client(self):
        """Create test Boltz2 client."""
        return Boltz2Client()
    
    def test_configure_msa_search(self, client):
        """Test MSA search configuration."""
        client.configure_msa_search(
            msa_endpoint_url="http://test-msa-nim:8000",
            api_key="test-key"
        )
        
        assert client._msa_search_client is not None
        assert client._msa_search_integration is not None
        assert client._msa_search_client.endpoint_url == "http://test-msa-nim:8000"
    
    @pytest.mark.asyncio
    async def test_search_msa(self, client):
        """Test MSA search through main client."""
        client.configure_msa_search(
            msa_endpoint_url="http://test-msa-nim:8000",
            api_key="test-key"
        )
        
        mock_response = MSASearchResponse(
            alignments={
                "uniref90": {
                    "a3m": {
                        "alignment": TEST_A3M_CONTENT,
                        "format": "a3m"
                    }
                }
            }
        )
        
        with patch.object(client._msa_search_client, 'search', return_value=mock_response):
            response = await client.search_msa(
                sequence=TEST_SEQUENCE,
                output_format="a3m"
            )
            
            assert isinstance(response, MSASearchResponse)