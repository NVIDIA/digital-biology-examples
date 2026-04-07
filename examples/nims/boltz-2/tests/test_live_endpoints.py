#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Live endpoint tests for Boltz2 NIM.

Tests run against real NIM, SageMaker, and NVIDIA hosted endpoints.
All tests are marked @pytest.mark.real_endpoint and can be skipped with:
    pytest -m "not real_endpoint"

Environment variables:
    BOLTZ2_NIM_URL           - NIM endpoint URL (default: http://localhost:8000)
    SAGEMAKER_ENDPOINT_NAME  - SageMaker endpoint name (skip SageMaker tests if unset)
    SAGEMAKER_REGION         - AWS region for SageMaker (default: us-east-1)
    NVIDIA_API_KEY           - NVIDIA API key (skip NVIDIA hosted tests if unset)
    NVIDIA_HOSTED_URL        - NVIDIA hosted base URL
                               (default: https://health.api.nvidia.com)
"""

import os
import asyncio
import time
import pytest
from pathlib import Path

from boltz2_client import Boltz2Client, Boltz2SyncClient, MultiEndpointClient, LoadBalanceStrategy
from boltz2_client.client import EndpointType
from boltz2_client.models import PredictionResponse, HealthStatus

BOLTZ2_NIM_URL = os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000")
SAGEMAKER_ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME")
SAGEMAKER_REGION = os.getenv("SAGEMAKER_REGION", "us-east-1")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_HOSTED_URL = os.getenv(
    "NVIDIA_HOSTED_URL", "https://health.api.nvidia.com"
)

from constants import CDK2_SEQUENCE as SHORT_SEQ, SAMPLE_SMILES as ASPIRIN_SMILES


# ---------------------------------------------------------------------------
# NIM endpoint tests
# ---------------------------------------------------------------------------
@pytest.mark.real_endpoint
class TestNIMEndpoint:
    """Tests against a self-hosted NIM endpoint."""

    @pytest.fixture
    def client(self):
        return Boltz2Client(
            base_url=BOLTZ2_NIM_URL,
            endpoint_type=EndpointType.LOCAL,
            timeout=300.0,
        )

    @pytest.fixture
    def sync_client(self):
        return Boltz2SyncClient(
            base_url=BOLTZ2_NIM_URL,
            endpoint_type=EndpointType.LOCAL,
            timeout=300.0,
        )

    async def test_health_check(self, client):
        health = await client.health_check()
        assert isinstance(health, HealthStatus)
        assert health.status == "healthy"

    async def test_protein_prediction(self, client):
        result = await client.predict_protein_structure(
            sequence=SHORT_SEQ,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1
        assert len(result.confidence_scores) >= 1

    async def test_protein_with_pae_pde(self, client):
        result = await client.predict_protein_structure(
            sequence=SHORT_SEQ,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
            write_full_pae=True,
            write_full_pde=True,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1

    async def test_multimer_prediction(self, client):
        from boltz2_client.models import Polymer, PredictionRequest

        polymers = [
            Polymer(id="A", molecule_type="protein", sequence=SHORT_SEQ),
            Polymer(id="B", molecule_type="protein", sequence=SHORT_SEQ[:30]),
        ]
        request = PredictionRequest(
            polymers=polymers,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
        )
        result = await client.predict(request)
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1

    def test_sync_health_check(self, sync_client):
        health = sync_client.health_check_sync()
        assert isinstance(health, HealthStatus)
        assert health.status == "healthy"

    def test_sync_protein_prediction(self, sync_client):
        result = sync_client.predict_protein_structure_sync(
            sequence=SHORT_SEQ,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1


# ---------------------------------------------------------------------------
# SageMaker endpoint tests
# ---------------------------------------------------------------------------
@pytest.mark.real_endpoint
@pytest.mark.skipif(
    not SAGEMAKER_ENDPOINT_NAME,
    reason="SAGEMAKER_ENDPOINT_NAME not set",
)
class TestSageMakerEndpoint:
    """Tests against an AWS SageMaker endpoint."""

    @pytest.fixture
    def client(self):
        return Boltz2Client(
            endpoint_type=EndpointType.SAGEMAKER,
            sagemaker_endpoint_name=SAGEMAKER_ENDPOINT_NAME,
            sagemaker_region=SAGEMAKER_REGION,
            timeout=300.0,
        )

    async def test_health_check(self, client):
        health = await client.health_check()
        assert isinstance(health, HealthStatus)

    async def test_protein_prediction(self, client):
        result = await client.predict_protein_structure(
            sequence=SHORT_SEQ,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1


# ---------------------------------------------------------------------------
# NVIDIA hosted endpoint tests
# ---------------------------------------------------------------------------
@pytest.mark.real_endpoint
@pytest.mark.skipif(
    not NVIDIA_API_KEY,
    reason="NVIDIA_API_KEY not set",
)
class TestNVIDIAHostedEndpoint:
    """Tests against the NVIDIA hosted API."""

    @pytest.fixture
    def client(self):
        return Boltz2Client(
            base_url=NVIDIA_HOSTED_URL,
            api_key=NVIDIA_API_KEY,
            endpoint_type=EndpointType.NVIDIA_HOSTED,
            timeout=600.0,
        )

    async def test_health_check(self, client):
        health = await client.health_check()
        assert isinstance(health, HealthStatus)

    async def test_protein_prediction(self, client):
        result = await client.predict_protein_structure(
            sequence=SHORT_SEQ,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1


# ---------------------------------------------------------------------------
# Multi-endpoint tests (NIM)
# ---------------------------------------------------------------------------
@pytest.mark.real_endpoint
class TestNIMMultiEndpoint:
    """Multi-endpoint behaviour against a real NIM."""

    @pytest.fixture
    def multi_client(self):
        return MultiEndpointClient(
            endpoints=[BOLTZ2_NIM_URL],
            strategy=LoadBalanceStrategy.ROUND_ROBIN,
            timeout=300.0,
            max_retries=3,
            is_async=True,
        )

    async def test_multi_health_check(self, multi_client):
        health = await multi_client.health_check()
        assert health is not None

    async def test_multi_service_metadata(self, multi_client):
        metadata = await multi_client.get_service_metadata()
        assert metadata is not None

    async def test_multi_protein_prediction(self, multi_client):
        result = await multi_client.predict_protein_structure(
            sequence=SHORT_SEQ,
            recycling_steps=1,
            sampling_steps=10,
            diffusion_samples=1,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1

    async def test_multi_protein_ligand(self, multi_client):
        result = await multi_client.predict_protein_ligand_complex(
            protein_sequence=SHORT_SEQ,
            ligand_smiles=ASPIRIN_SMILES,
            protein_id="A",
            ligand_id="LIG",
            recycling_steps=1,
            sampling_steps=10,
        )
        assert isinstance(result, PredictionResponse)
        assert len(result.structures) >= 1


# ---------------------------------------------------------------------------
# Performance / concurrency tests (NIM)
# ---------------------------------------------------------------------------
@pytest.mark.real_endpoint
@pytest.mark.performance
class TestNIMPerformance:
    """Concurrent prediction tests against a real NIM."""

    @pytest.fixture
    def perf_client(self):
        return MultiEndpointClient(
            endpoints=[BOLTZ2_NIM_URL],
            strategy=LoadBalanceStrategy.LEAST_LOADED,
            timeout=300.0,
            max_retries=3,
            is_async=True,
        )

    async def test_concurrent_predictions(self, perf_client):
        tasks = [
            perf_client.predict_protein_structure(
                sequence=SHORT_SEQ[:50 + i * 5],
                recycling_steps=1,
                sampling_steps=10,
                diffusion_samples=1,
            )
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful > 0, "At least one concurrent prediction should succeed"


# ---------------------------------------------------------------------------
# CLI smoke tests against the NIM endpoint
# ---------------------------------------------------------------------------
@pytest.mark.real_endpoint
class TestCLILive:
    """Smoke-test CLI commands against the NIM endpoint."""

    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_cli_health(self, runner):
        from boltz2_client.cli import cli

        result = runner.invoke(cli, [
            "--base-url", BOLTZ2_NIM_URL,
            "--endpoint-type", "local",
            "health",
        ])
        assert result.exit_code == 0
        assert "healthy" in result.output.lower()

    def test_cli_protein(self, runner, tmp_path):
        from boltz2_client.cli import cli

        result = runner.invoke(cli, [
            "--base-url", BOLTZ2_NIM_URL,
            "--endpoint-type", "local",
            "protein", SHORT_SEQ,
            "--recycling-steps", "1",
            "--sampling-steps", "10",
            "--diffusion-samples", "1",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Prediction completed successfully" in result.output

    @pytest.mark.skipif(
        not SAGEMAKER_ENDPOINT_NAME,
        reason="SAGEMAKER_ENDPOINT_NAME not set",
    )
    def test_cli_sagemaker_health(self, runner):
        from boltz2_client.cli import cli

        result = runner.invoke(cli, [
            "--endpoint-type", "sagemaker",
            "--sagemaker-endpoint-name", SAGEMAKER_ENDPOINT_NAME,
            "--sagemaker-region", SAGEMAKER_REGION,
            "health",
        ])
        assert result.exit_code == 0
