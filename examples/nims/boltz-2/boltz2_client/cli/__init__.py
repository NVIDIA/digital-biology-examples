# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Command-line interface for Boltz-2 Python Client.

This package provides a comprehensive CLI for all Boltz-2 features including
protein structure prediction, protein-ligand complexes, covalent complexes,
DNA-protein complexes, and advanced parameter control.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
import yaml as pyyaml

from .. import __version__ as _pkg_version
from ..client import Boltz2Client
from ..models import (
    PredictionRequest, Polymer, Ligand, BondConstraint,
    Atom, AlignmentFileRecord,
)


console = Console()


def print_success(message: str):
    """Print success message."""
    console.print(f"\u2705 {message}", style="green")


def print_error(message: str):
    """Print error message."""
    console.print(f"\u274c {message}", style="red")


def print_info(message: str):
    """Print info message."""
    console.print(f"\u2139\ufe0f {message}", style="blue")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"\u26a0\ufe0f {message}", style="yellow")


@click.group()
@click.version_option(_pkg_version, "-V", "--version", prog_name="boltz2",
                      message="%(prog)s %(version)s")
@click.option('--base-url', default='http://localhost:8000', help='Service base URL (can be comma-separated for multiple endpoints)')
@click.option('--api-key', help='API key for NVIDIA hosted endpoints (or set NVIDIA_API_KEY env var)')
@click.option('--endpoint-type',
              type=click.Choice(['local', 'nvidia_hosted', 'sagemaker']),
              default='local',
              help='Type of endpoint: local, nvidia_hosted, or sagemaker')
@click.option('--timeout', default=300.0, help='Request timeout in seconds')
@click.option('--poll-seconds', default=10, help='Polling interval for NVIDIA hosted endpoints')
@click.option('--multi-endpoint', is_flag=True, help='Enable multi-endpoint load balancing')
@click.option('--load-balance-strategy',
              type=click.Choice(['round_robin', 'least_loaded', 'random']),
              default='least_loaded',
              help='Load balancing strategy for multi-endpoint')
@click.option('--sagemaker-endpoint-name', default=None,
              help='SageMaker endpoint name (or set SAGEMAKER_ENDPOINT_NAME env var)')
@click.option('--sagemaker-region', default=None,
              help='AWS region for SageMaker endpoint')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, base_url: str, api_key: Optional[str], endpoint_type: str,
        timeout: float, poll_seconds: int, multi_endpoint: bool,
        load_balance_strategy: str, sagemaker_endpoint_name: Optional[str],
        sagemaker_region: Optional[str], verbose: bool):
    """
    Boltz-2 Python Client CLI

    Supports both local deployments and NVIDIA hosted endpoints.

    Examples:

    # Local endpoint
    boltz2 --base-url http://localhost:8000 protein "MKTVRQERLK..."

    # Multi-endpoint for parallel processing
    boltz2 --multi-endpoint --base-url "http://localhost:8000,http://localhost:8001,http://localhost:8002,http://localhost:8003" screen target.fasta compounds.csv

    # Multi-endpoint with custom strategy
    boltz2 --multi-endpoint --base-url "http://localhost:8000,http://localhost:8001" --load-balance-strategy round_robin protein "MKTVRQERLK..."

    # NVIDIA hosted endpoint
    boltz2 --base-url https://health.api.nvidia.com --endpoint-type nvidia_hosted --api-key YOUR_KEY protein "MKTVRQERLK..."

    # Using environment variable for API key
    export NVIDIA_API_KEY=your_api_key
    boltz2 --base-url https://health.api.nvidia.com --endpoint-type nvidia_hosted protein "MKTVRQERLK..."

    # AWS SageMaker endpoint
    boltz2 --endpoint-type sagemaker --sagemaker-endpoint-name my-boltz2-endpoint protein "MKTVRQERLK..."

    # SageMaker with environment variable
    export SAGEMAKER_ENDPOINT_NAME=my-boltz2-endpoint
    boltz2 --endpoint-type sagemaker protein "MKTVRQERLK..."
    """
    ctx.ensure_object(dict)
    ctx.obj['base_url'] = base_url
    ctx.obj['api_key'] = api_key
    ctx.obj['endpoint_type'] = endpoint_type
    ctx.obj['timeout'] = timeout
    ctx.obj['poll_seconds'] = poll_seconds
    ctx.obj['multi_endpoint'] = multi_endpoint
    ctx.obj['load_balance_strategy'] = load_balance_strategy
    ctx.obj['sagemaker_endpoint_name'] = sagemaker_endpoint_name
    ctx.obj['sagemaker_region'] = sagemaker_region
    ctx.obj['verbose'] = verbose

    if verbose:
        if multi_endpoint:
            endpoints = [url.strip() for url in base_url.split(',')]
            print_info(f"Using multi-endpoint mode with {len(endpoints)} endpoints")
            print_info(f"Load balance strategy: {load_balance_strategy}")
            for ep in endpoints:
                print_info(f"  - {ep}")
        elif endpoint_type == 'sagemaker':
            ep_name = sagemaker_endpoint_name or os.getenv("SAGEMAKER_ENDPOINT_NAME", "<not set>")
            print_info(f"Using SageMaker endpoint: {ep_name}")
            if sagemaker_region:
                print_info(f"AWS region: {sagemaker_region}")
        else:
            print_info(f"Using {endpoint_type} endpoint: {base_url}")
            if endpoint_type == 'nvidia_hosted':
                if api_key:
                    print_info("API key provided via command line")
                else:
                    print_info("API key will be read from NVIDIA_API_KEY environment variable")


def create_client(ctx):
    """Create a Boltz2Client or MultiEndpointClient from context."""
    from ..multi_endpoint_client import MultiEndpointClient, LoadBalanceStrategy

    if ctx.obj['multi_endpoint']:
        endpoints = [url.strip() for url in ctx.obj['base_url'].split(',')]
        strategy_map = {
            'round_robin': LoadBalanceStrategy.ROUND_ROBIN,
            'least_loaded': LoadBalanceStrategy.LEAST_LOADED,
            'random': LoadBalanceStrategy.RANDOM
        }
        strategy = strategy_map[ctx.obj['load_balance_strategy']]

        if ctx.obj['verbose']:
            print_info(f"Using multi-endpoint with {len(endpoints)} endpoints")
            print_info(f"Load balance strategy: {strategy.value}")

        return MultiEndpointClient(
            endpoints=endpoints,
            strategy=strategy,
            timeout=ctx.obj['timeout']
        )
    else:
        return Boltz2Client(
            base_url=ctx.obj['base_url'],
            api_key=ctx.obj['api_key'],
            endpoint_type=ctx.obj['endpoint_type'],
            timeout=ctx.obj['timeout'],
            poll_seconds=ctx.obj['poll_seconds'],
            console=console,
            sagemaker_endpoint_name=ctx.obj.get('sagemaker_endpoint_name'),
            sagemaker_region=ctx.obj.get('sagemaker_region'),
        )


# Import submodules to register their commands on the cli group.
# These must come after `cli` and `create_client` are defined.
from . import info  # noqa: E402, F401
from . import predict  # noqa: E402, F401
from . import msa  # noqa: E402, F401
from . import screen  # noqa: E402, F401
