#!/usr/bin/env python3
"""
Real Endpoint Tests for Boltz2 NIM

This file contains tests that run against actual Boltz2 NIM endpoints
to verify real functionality and performance.
"""

import pytest
import asyncio
import time
from pathlib import Path

from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    Boltz2Client
)

# Real endpoint configuration
REAL_ENDPOINTS = [
    "http://10.185.105.21:8000",
    "http://10.185.105.21:8001", 
    "http://10.185.105.21:8002",
    "http://10.185.105.21:8003"
]

# Test data
CDK2_SEQUENCE = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
SAMPLE_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
SAMPLE_CCD = "ASP"  # Aspartic acid
SAMPLE_DNA = "ATCGATCGATCGATCG"


@pytest.mark.asyncio
class TestRealSingleEndpoint:
    """Test single endpoint functionality with real Boltz2 NIM."""
    
    @pytest.fixture
    def single_client(self):
        """Create a single endpoint client."""
        return Boltz2Client(
            base_url=REAL_ENDPOINTS[0],
            timeout=300.0,
            max_retries=3
        )
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_health_check_single(self, single_client):
        """Test health check with real endpoint."""
        health = await single_client.health_check()
        assert health is not None
        print(f"Health status: {health}")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_service_metadata_single(self, single_client):
        """Test service metadata retrieval with real endpoint."""
        metadata = await single_client.get_service_metadata()
        assert metadata is not None
        print(f"Service metadata: {metadata}")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_protein_structure_prediction_single(self, single_client):
        """Test protein structure prediction with real endpoint."""
        print("Starting protein structure prediction...")
        start_time = time.time()
        
        result = await single_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=1,  # Reduced for testing
            sampling_steps=10,  # Reduced for testing
            diffusion_samples=1,
            step_scale=1.638
        )
        
        elapsed = time.time() - start_time
        print(f"Protein structure prediction completed in {elapsed:.2f}s")
        
        assert result is not None
        assert hasattr(result, 'structures')
        print(f"Generated {len(result.structures)} structure(s)")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_protein_ligand_complex_single(self, single_client):
        """Test protein-ligand complex prediction with real endpoint."""
        print("Starting protein-ligand complex prediction...")
        start_time = time.time()
        
        result = await single_client.predict_protein_ligand_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_smiles=SAMPLE_SMILES,
            protein_id="A",
            ligand_id="LIG",
            recycling_steps=1,  # Reduced for testing
            sampling_steps=10   # Reduced for testing
        )
        
        elapsed = time.time() - start_time
        print(f"Protein-ligand complex prediction completed in {elapsed:.2f}s")
        
        assert result is not None
        assert hasattr(result, 'structures')
        print(f"Generated {len(result.structures)} structure(s)")


@pytest.mark.asyncio
class TestRealMultiEndpoint:
    """Test multi-endpoint functionality with real Boltz2 NIM."""
    
    @pytest.fixture
    def multi_client(self):
        """Create a multi-endpoint client."""
        return MultiEndpointClient(
            endpoints=REAL_ENDPOINTS,
            strategy=LoadBalanceStrategy.ROUND_ROBIN,
            timeout=300.0,
            max_retries=3,
            is_async=True
        )
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_health_check_multi(self, multi_client):
        """Test health check across multiple real endpoints."""
        health = await multi_client.health_check()
        assert health is not None
        print(f"Multi-endpoint health status: {health}")
        
        # Print individual endpoint status
        status = multi_client.get_status()
        print(f"Endpoint status: {status}")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_service_metadata_multi(self, multi_client):
        """Test service metadata retrieval from multi-endpoint."""
        metadata = await multi_client.get_service_metadata()
        assert metadata is not None
        print(f"Multi-endpoint service metadata: {metadata}")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_protein_structure_prediction_multi(self, multi_client):
        """Test protein structure prediction with load balancing."""
        print("Starting multi-endpoint protein structure prediction...")
        start_time = time.time()
        
        result = await multi_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            recycling_steps=1,  # Reduced for testing
            sampling_steps=10,  # Reduced for testing
            diffusion_samples=1,
            step_scale=1.638
        )
        
        elapsed = time.time() - start_time
        print(f"Multi-endpoint protein structure prediction completed in {elapsed:.2f}s")
        
        assert result is not None
        assert hasattr(result, 'structures')
        print(f"Generated {len(result.structures)} structure(s)")
        
        # Show which endpoint was used
        status = multi_client.get_status()
        print(f"Endpoint usage after prediction: {status}")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_load_balancing_strategies(self, multi_client):
        """Test different load balancing strategies."""
        strategies = [
            LoadBalanceStrategy.ROUND_ROBIN,
            LoadBalanceStrategy.LEAST_LOADED,
            LoadBalanceStrategy.RANDOM
        ]
        
        for strategy in strategies:
            print(f"\nTesting {strategy.value} strategy...")
            multi_client.strategy = strategy
            
            # Make a quick prediction to test the strategy
            result = await multi_client.predict_protein_structure(
                sequence=CDK2_SEQUENCE[:50],  # Shorter sequence for quick test
                recycling_steps=1,
                sampling_steps=10,  # Minimum required value
                diffusion_samples=1
            )
            
            assert result is not None
            status = multi_client.get_status()
            print(f"Strategy {strategy.value} - Endpoint status: {status}")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_failover_scenario(self, multi_client):
        """Test failover when some endpoints are unavailable."""
        print("Testing failover scenario...")
        
        # Get initial status
        initial_status = multi_client.get_status()
        print(f"Initial endpoint status: {initial_status}")
        
        # Make a prediction (should work even if some endpoints are down)
        result = await multi_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE[:50],
            recycling_steps=1,
            sampling_steps=10,  # Minimum required value
            diffusion_samples=1
        )
        
        assert result is not None
        final_status = multi_client.get_status()
        print(f"Final endpoint status: {final_status}")
        
        # Show which endpoints were used
        for endpoint in multi_client.endpoints:
            print(f"Endpoint {endpoint.endpoint_config.base_url}: "
                  f"healthy={endpoint.is_healthy}, "
                  f"requests={endpoint.total_requests}, "
                  f"failed={endpoint.failed_requests}")


@pytest.mark.asyncio
class TestRealPerformance:
    """Test performance characteristics with real endpoints."""
    
    @pytest.fixture
    def performance_client(self):
        """Create a client for performance testing."""
        return MultiEndpointClient(
            endpoints=REAL_ENDPOINTS,
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            timeout=300.0,
            max_retries=3,
            is_async=True
        )
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    @pytest.mark.performance
    async def test_concurrent_predictions(self, performance_client):
        """Test concurrent predictions across multiple endpoints."""
        print("Testing concurrent predictions...")
        start_time = time.time()
        
        # Create multiple prediction tasks
        tasks = []
        for i in range(min(4, len(REAL_ENDPOINTS))):  # One per endpoint
            sequence = CDK2_SEQUENCE[:50 + i*10]  # Vary sequence length
            task = performance_client.predict_protein_structure(
                sequence=sequence,
                recycling_steps=1,
                sampling_steps=10,  # Minimum required value
                diffusion_samples=1
            )
            tasks.append(task)
        
        # Run all predictions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        print(f"Completed {len(tasks)} concurrent predictions in {elapsed:.2f}s")
        
        # Check results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        print(f"Successful predictions: {successful}/{len(tasks)}")
        
        # Show endpoint usage
        status = performance_client.get_status()
        print(f"Endpoint usage after concurrent predictions: {status}")
        
        assert successful > 0, "At least one prediction should succeed"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
