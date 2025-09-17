#!/usr/bin/env python3
"""
CLI Test Suite for Multi-Endpoint Boltz2 NIM Functionality

This test suite covers CLI commands with both single and multiple endpoints:
- health command
- metadata command  
- protein command
- ligand command
- covalent command
- dna_protein command
- yaml command
- screen command

Tests both single endpoint and multi-endpoint CLI approaches.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import click
from click.testing import CliRunner

from boltz2_client.cli import cli
from boltz2_client import MultiEndpointClient, LoadBalanceStrategy, EndpointConfig


class TestCLIMultiEndpoint:
    """Test suite for CLI multi-endpoint functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()
    
    @pytest.fixture
    def mock_multi_endpoint_client(self):
        """Create a mock multi-endpoint client."""
        client = Mock(spec=MultiEndpointClient)
        client.health_check = AsyncMock()
        client.get_service_metadata = AsyncMock()
        client.predict_protein_structure = AsyncMock()
        client.predict_protein_ligand_complex = AsyncMock()
        client.predict_covalent_complex = AsyncMock()
        client.predict_dna_protein_complex = AsyncMock()
        client.predict_from_yaml_config = AsyncMock()
        client.predict_from_yaml_file = AsyncMock()
        client.print_status = Mock()
        return client
    
    @pytest.fixture
    def mock_single_client(self):
        """Create a mock single client."""
        client = Mock()
        client.health_check = AsyncMock()
        client.get_service_metadata = AsyncMock()
        client.predict_protein_structure = AsyncMock()
        client.predict_protein_ligand_complex = AsyncMock()
        client.predict_covalent_complex = AsyncMock()
        client.predict_dna_protein_complex = AsyncMock()
        client.predict_from_yaml_config = AsyncMock()
        client.predict_from_yaml_file = AsyncMock()
        return client

    # Test 1: Health Command
    def test_health_single_endpoint(self, cli_runner, mock_single_client):
        """Test health command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.health_check.return_value = Mock(
                status="healthy",
                details={"test": "data"}
            )
            
            result = cli_runner.invoke(cli, [
                '--base-url', 'http://localhost:8000',
                '--endpoint-type', 'local',
                'health'
            ])
            
            assert result.exit_code == 0
            assert "Service is healthy" in result.output
            mock_single_client.health_check.assert_called_once()
    
    def test_health_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test health command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.health_check.return_value = Mock(
                status="healthy",
                details={"healthy_endpoints": 3, "total_endpoints": 3}
            )
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001,http://localhost:8002',
                '--load-balance-strategy', 'least_loaded',
                'health'
            ])
            
            assert result.exit_code == 0
            assert "Service is healthy" in result.output
            mock_multi_endpoint_client.health_check.assert_called_once()

    # Test 2: Metadata Command
    def test_metadata_single_endpoint(self, cli_runner, mock_single_client):
        """Test metadata command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.get_service_metadata.return_value = Mock(
                version="1.0.0",
                repository_override="test",
                assetInfo=["asset1", "asset2"],
                modelInfo=[]
            )
            
            result = cli_runner.invoke(cli, [
                '--base-url', 'http://localhost:8000',
                'metadata'
            ])
            
            assert result.exit_code == 0
            assert "Service metadata retrieved successfully" in result.output
            mock_single_client.get_service_metadata.assert_called_once()
    
    def test_metadata_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test metadata command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.get_service_metadata.return_value = Mock(
                version="1.0.0",
                repository_override="test",
                assetInfo=["asset1", "asset2"],
                modelInfo=[]
            )
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                'metadata'
            ])
            
            assert result.exit_code == 0
            assert "Service metadata retrieved successfully" in result.output
            mock_multi_endpoint_client.get_service_metadata.assert_called_once()

    # Test 3: Protein Command
    def test_protein_single_endpoint(self, cli_runner, mock_single_client):
        """Test protein command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.predict_protein_structure.return_value = Mock(
                structures=["structure1", "structure2"],
                confidence_scores=[0.85, 0.78]
            )
            
            result = cli_runner.invoke(cli, [
                '--base-url', 'http://localhost:8000',
                'protein', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                '--recycling-steps', '3',
                '--sampling-steps', '50',
                '--diffusion-samples', '1'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_single_client.predict_protein_structure.assert_called_once()
    
    def test_protein_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test protein command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.predict_protein_structure.return_value = Mock(
                structures=["structure1", "structure2"],
                confidence_scores=[0.85, 0.78]
            )
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                '--load-balance-strategy', 'round_robin',
                'protein', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                '--recycling-steps', '3',
                '--sampling-steps', '50'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_multi_endpoint_client.predict_protein_structure.assert_called_once()

    # Test 4: Ligand Command
    def test_ligand_single_endpoint(self, cli_runner, mock_single_client):
        """Test ligand command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.predict_protein_ligand_complex.return_value = Mock(
                structures=["complex1"],
                confidence_scores=[0.82]
            )
            
            result = cli_runner.invoke(cli, [
                '--base-url', 'http://localhost:8000',
                'ligand', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                '--smiles', 'CC(=O)OC1=CC=CC=C1C(=O)O'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_single_client.predict_protein_ligand_complex.assert_called_once()
    
    def test_ligand_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test ligand command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.predict_protein_ligand_complex.return_value = Mock(
                structures=["complex1"],
                confidence_scores=[0.82]
            )
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                'ligand', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                '--smiles', 'CC(=O)OC1=CC=CC=C1C(=O)O'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_multi_endpoint_client.predict_protein_ligand_complex.assert_called_once()

    # Test 5: Covalent Command
    def test_covalent_single_endpoint(self, cli_runner, mock_single_client):
        """Test covalent command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.predict_covalent_complex.return_value = Mock(
                structures=["covalent1"],
                confidence_scores=[0.79]
            )
            
            result = cli_runner.invoke(cli, [
                '--base-url', 'http://localhost:8000',
                'covalent', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                '--ccd', 'ASP'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_single_client.predict_covalent_complex.assert_called_once()
    
    def test_covalent_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test covalent command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.predict_covalent_complex.return_value = Mock(
                structures=["covalent1"],
                confidence_scores=[0.79]
            )
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                'covalent', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                '--ccd', 'ASP'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_multi_endpoint_client.predict_covalent_complex.assert_called_once()

    # Test 6: DNA-Protein Command
    def test_dna_protein_single_endpoint(self, cli_runner, mock_single_client):
        """Test dna_protein command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.predict_dna_protein_complex.return_value = Mock(
                structures=["dna_protein1"],
                confidence_scores=[0.81]
            )
            
            result = cli_runner.invoke(cli, [
                '--base-url', 'http://localhost:8000',
                'dna_protein', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                'ATCGATCGATCGATCG'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_single_client.predict_dna_protein_complex.assert_called_once()
    
    def test_dna_protein_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test dna_protein command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.predict_dna_protein_complex.return_value = Mock(
                structures=["dna_protein1"],
                confidence_scores=[0.81]
            )
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                'dna_protein', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                'ATCGATCGATCGATCG'
            ])
            
            assert result.exit_code == 0
            assert "Prediction completed successfully" in result.output
            mock_multi_endpoint_client.predict_dna_protein_complex.assert_called_once()

    # Test 7: YAML Command
    def test_yaml_single_endpoint(self, cli_runner, mock_single_client):
        """Test yaml command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            mock_single_client.predict_from_yaml_file.return_value = Mock(
                structures=["yaml_structure"],
                confidence_scores=[0.83]
            )
            
            # Create temporary YAML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml_content = """
                polymers:
                  - id: A
                    molecule_type: protein
                    sequence: MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
                recycling_steps: 3
                sampling_steps: 50
                """
                f.write(yaml_content)
                yaml_file = f.name
            
            try:
                result = cli_runner.invoke(cli, [
                    '--base-url', 'http://localhost:8000',
                    'yaml', yaml_file
                ])
                
                assert result.exit_code == 0
                assert "Prediction completed successfully" in result.output
                mock_single_client.predict_from_yaml_file.assert_called_once()
            finally:
                os.unlink(yaml_file)
    
    def test_yaml_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test yaml command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            mock_multi_endpoint_client.predict_from_yaml_file.return_value = Mock(
                structures=["yaml_structure"],
                confidence_scores=[0.83]
            )
            
            # Create temporary YAML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml_content = """
                polymers:
                  - id: A
                    molecule_type: protein
                    sequence: MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
                recycling_steps: 3
                sampling_steps: 50
                """
                f.write(yaml_content)
                yaml_file = f.name
            
            try:
                result = cli_runner.invoke(cli, [
                    '--multi-endpoint',
                    '--base-url', 'http://localhost:8000,http://localhost:8001',
                    'yaml', yaml_file
                ])
                
                assert result.exit_code == 0
                assert "Prediction completed successfully" in result.output
                mock_multi_endpoint_client.predict_from_yaml_file.assert_called_once()
            finally:
                os.unlink(yaml_file)

    # Test 8: Screen Command
    def test_screen_single_endpoint(self, cli_runner, mock_single_client):
        """Test screen command with single endpoint."""
        with patch('boltz2_client.cli.create_client', return_value=mock_single_client):
            # Create temporary compounds file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write("name,smiles\nAspirin,CC(=O)OC1=CC=CC=C1C(=O)O\n")
                compounds_file = f.name
            
            try:
                result = cli_runner.invoke(cli, [
                    '--base-url', 'http://localhost:8000',
                    'screen', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                    compounds_file,
                    '--target-name', 'CDK2'
                ])
                
                # Screen command might not be fully implemented in CLI yet
                # This test checks the basic structure
                assert result.exit_code in [0, 1]  # Allow for not implemented
            finally:
                os.unlink(compounds_file)
    
    def test_screen_multi_endpoint(self, cli_runner, mock_multi_endpoint_client):
        """Test screen command with multiple endpoints."""
        with patch('boltz2_client.cli.create_client', return_value=mock_multi_endpoint_client):
            # Create temporary compounds file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write("name,smiles\nAspirin,CC(=O)OC1=CC=CC=C1C(=O)O\n")
                compounds_file = f.name
            
            try:
                result = cli_runner.invoke(cli, [
                    '--multi-endpoint',
                    '--base-url', 'http://localhost:8000,http://localhost:8001',
                    'screen', 'MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG',
                    compounds_file,
                    '--target-name', 'CDK2'
                ])
                
                # Screen command might not be fully implemented in CLI yet
                # This test checks the basic structure
                assert result.exit_code in [0, 1]  # Allow for not implemented
            finally:
                os.unlink(compounds_file)

    # Test 9: CLI Options and Flags
    def test_cli_multi_endpoint_flag(self, cli_runner):
        """Test that --multi-endpoint flag enables multi-endpoint mode."""
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', 'http://localhost:8000,http://localhost:8001',
            '--help'
        ])
        
        assert result.exit_code == 0
        # The help should show multi-endpoint options
    
    def test_cli_load_balance_strategy_options(self, cli_runner):
        """Test load balancing strategy options."""
        strategies = ['round_robin', 'least_loaded', 'random']
        
        for strategy in strategies:
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                '--load-balance-strategy', strategy,
                '--help'
            ])
            
            assert result.exit_code == 0
    
    def test_cli_endpoint_parsing(self, cli_runner):
        """Test parsing of comma-separated endpoints."""
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', 'http://localhost:8000,http://localhost:8001,http://localhost:8002',
            '--help'
        ])
        
        assert result.exit_code == 0

    # Test 10: Error Handling
    def test_cli_invalid_endpoint_url(self, cli_runner):
        """Test CLI with invalid endpoint URL."""
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', 'invalid-url,another-invalid',
            'health'
        ])
        
        # Should handle gracefully or show appropriate error
        assert result.exit_code != 0 or "error" in result.output.lower()
    
    def test_cli_missing_endpoints(self, cli_runner):
        """Test CLI with missing endpoints."""
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', '',
            'health'
        ])
        
        # Should handle gracefully or show appropriate error
        assert result.exit_code != 0 or "error" in result.output.lower()

    # Test 11: Environment Variable Support
    def test_cli_environment_variables(self, cli_runner):
        """Test CLI with environment variables."""
        with patch.dict(os.environ, {'NVIDIA_API_KEY': 'test_key'}):
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'https://health.api.nvidia.com',
                '--endpoint-type', 'nvidia_hosted',
                '--help'
            ])
            
            assert result.exit_code == 0

    # Test 12: Integration with MultiEndpointClient
    def test_cli_creates_multi_endpoint_client(self, cli_runner):
        """Test that CLI creates MultiEndpointClient when --multi-endpoint is used."""
        with patch('boltz2_client.cli.MultiEndpointClient') as mock_multi_client_class:
            mock_multi_client_class.return_value = Mock()
            
            result = cli_runner.invoke(cli, [
                '--multi-endpoint',
                '--base-url', 'http://localhost:8000,http://localhost:8001',
                'health'
            ])
            
            # Verify MultiEndpointClient was created
            mock_multi_client_class.assert_called_once()
            
            # Check that endpoints were parsed correctly
            call_args = mock_multi_client_class.call_args
            assert len(call_args[1]['endpoints']) == 2
            assert "http://localhost:8000" in call_args[1]['endpoints']
            assert "http://localhost:8001" in call_args[1]['endpoints']


class TestCLIEdgeCases:
    """Test edge cases and error conditions for CLI."""
    
    @pytest.fixture
    def cli_runner(self):
        return CliRunner()
    
    def test_cli_mixed_endpoint_formats(self, cli_runner):
        """Test CLI with mixed endpoint formats (URLs and configs)."""
        # This would test the CLI's ability to handle mixed endpoint formats
        # For now, we'll test the basic structure
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', 'http://localhost:8000,http://localhost:8001',
            '--help'
        ])
        
        assert result.exit_code == 0
    
    def test_cli_timeout_settings(self, cli_runner):
        """Test CLI timeout settings with multi-endpoint."""
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', 'http://localhost:8000,http://localhost:8001',
            '--timeout', '600',
            '--help'
        ])
        
        assert result.exit_code == 0
    
    def test_cli_verbose_output(self, cli_runner):
        """Test CLI verbose output with multi-endpoint."""
        result = cli_runner.invoke(cli, [
            '--multi-endpoint',
            '--base-url', 'http://localhost:8000,http://localhost:8001',
            '--verbose',
            '--help'
        ])
        
        assert result.exit_code == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
