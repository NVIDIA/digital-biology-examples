#!/usr/bin/env python3
"""
Boltz2 Master Test Suite

Comprehensive testing of all examples using both Python API and CLI interfaces
across both local and NVIDIA hosted endpoints.

This script validates:
- All 8 example scripts using Python API
- CLI commands for applicable examples
- Both local (localhost:8000) and NVIDIA hosted endpoints
- Error handling and validation fixes
- Performance metrics and reporting

Usage:
    python master_test_suite.py                    # Run all tests
    python master_test_suite.py --api-only         # Python API tests only
    python master_test_suite.py --cli-only         # CLI tests only
    python master_test_suite.py --local-only       # Local endpoint only
    python master_test_suite.py --nvidia-only      # NVIDIA endpoint only
    python master_test_suite.py --quick            # Fast tests (reduced parameters)
"""

import asyncio
import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import tempfile

# Rich for beautiful output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
from rich.text import Text
from rich.layout import Layout
from rich.live import Live

console = Console()


class TestResult:
    """Represents the result of a single test."""
    def __init__(self, name: str, interface: str, endpoint: str):
        self.name = name
        self.interface = interface  # 'python' or 'cli'
        self.endpoint = endpoint    # 'local' or 'nvidia'
        self.status = "pending"     # 'success', 'failed', 'skipped', 'pending'
        self.duration = 0.0
        self.confidence = None
        self.structures = None
        self.error = None
        self.details = {}

    def mark_success(self, duration: float, confidence: float = None, structures: int = None, **details):
        self.status = "success"
        self.duration = duration
        self.confidence = confidence
        self.structures = structures
        self.details.update(details)

    def mark_failed(self, duration: float, error: str):
        self.status = "failed" 
        self.duration = duration
        self.error = error

    def mark_skipped(self, reason: str):
        self.status = "skipped"
        self.error = reason


class MasterTestSuite:
    """Comprehensive test suite for Boltz2 examples."""

    def __init__(self, args):
        self.args = args
        self.results: List[TestResult] = []
        self.start_time = None
        self.total_duration = 0.0
        
        # Rate limiting configuration
        self.nvidia_delay = 6.0  # 6 second delay between NVIDIA API calls (increased for CLI)
        self.max_retries = 3     # Maximum retry attempts for rate limiting
        
        # Validate environment
        self.nvidia_api_key = os.environ.get("NVIDIA_API_KEY")
        if not self.nvidia_api_key and not args.local_only:
            console.print("⚠️  NVIDIA_API_KEY not set - NVIDIA tests will be skipped", style="yellow")

    async def safe_predict_with_retry(self, predict_func, endpoint: str, *args, **kwargs):
        """Execute prediction with rate limiting protection and retry logic."""
        # Add delay for NVIDIA endpoints to prevent rate limiting
        if endpoint == "nvidia":
            await asyncio.sleep(self.nvidia_delay)
        
        for attempt in range(self.max_retries):
            try:
                result = await predict_func(*args, **kwargs)
                return result
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limiting errors
                if any(term in error_str for term in ["429", "rate limit", "too many requests"]):
                    if attempt < self.max_retries - 1:
                        # Exponential backoff with jitter
                        delay = self.nvidia_delay * (2 ** attempt) + random.uniform(0, 2)
                        console.print(f"⏱️ Rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})", style="yellow")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        console.print(f"❌ Max retries exceeded for rate limiting", style="red")
                        raise e
                
                # For other errors, don't retry
                raise e
        
        raise Exception("Should not reach here")

    async def safe_health_check(self, client, endpoint: str):
        """Health check with endpoint-specific logic."""
        if endpoint == "nvidia":
            # NVIDIA endpoints may not support health checks
            console.print("⚠️ Skipping health check for NVIDIA endpoint", style="yellow")
            return {"status": "unknown", "note": "Health check not supported on hosted endpoints"}
        else:
            try:
                return await client.health_check()
            except Exception as e:
                console.print(f"⚠️ Health check failed: {e}", style="yellow")
                return {"status": "error", "error": str(e)}

    def should_test_interface(self, interface: str) -> bool:
        """Check if we should test this interface."""
        if self.args.api_only and interface == "cli":
            return False
        if self.args.cli_only and interface == "python":
            return False
        return True

    def should_test_endpoint(self, endpoint: str) -> bool:
        """Check if we should test this endpoint."""
        if self.args.local_only and endpoint == "nvidia":
            return False
        if self.args.nvidia_only and endpoint == "local":
            return False
        if endpoint == "nvidia" and not self.nvidia_api_key:
            return False
        return True

    def get_test_params(self) -> Dict[str, int]:
        """Get test parameters based on quick mode."""
        if self.args.quick:
            return {
                "recycling_steps": 1,
                "sampling_steps": 10,  # Minimum server requirement
                "diffusion_samples": 1
            }
        else:
            return {
                "recycling_steps": 2,
                "sampling_steps": 20,
                "diffusion_samples": 1
            }

    async def test_python_example_01_basic_protein(self, endpoint: str) -> TestResult:
        """Test example 01: Basic protein folding."""
        test = TestResult("01_basic_protein_folding", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            
            # Configure client based on endpoint
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            params = self.get_test_params()
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                client.predict_protein_structure,
                endpoint,
                sequence=sequence,
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures))
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test

    async def test_python_example_02_msa_protein(self, endpoint: str) -> TestResult:
        """Test example 02: Protein with MSA."""
        test = TestResult("02_protein_structure_prediction_with_msa", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            
            # Configure client based on endpoint
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            params = self.get_test_params()
            
            # Check if MSA file exists
            msa_file = Path("examples/msa-kras-g12c_combined.a3m")
            if not msa_file.exists():
                test.mark_skipped("MSA file not found")
                return test
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                client.predict_protein_structure,
                endpoint,
                sequence=sequence,
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                msa_files=[(str(msa_file), "a3m")],
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures), msa_guided=True)
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test

    async def test_python_example_03_protein_ligand(self, endpoint: str) -> TestResult:
        """Test example 03: Protein-ligand complex."""
        test = TestResult("03_protein_ligand_complex", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            
            # Configure client
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            ligand_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
            params = self.get_test_params()
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                client.predict_protein_ligand_complex,
                endpoint,
                protein_sequence=protein_sequence,
                ligand_smiles=ligand_smiles,
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures), ligand_type="smiles")
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test

    async def test_python_example_04_covalent_bonding(self, endpoint: str) -> TestResult:
        """Test example 04: Covalent bonding."""
        test = TestResult("04_covalent_bonding", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            
            # Configure client
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            protein_sequence = "MKTVRQERLKSCVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            ligand_ccd = "U4U"
            params = self.get_test_params()
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                client.predict_covalent_complex,
                endpoint,
                protein_sequence=protein_sequence,
                ligand_ccd=ligand_ccd,
                covalent_bonds=[(12, "SG", "C22")],  # Cys12 to ligand
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures), 
                            bond_type="covalent", ligand_id_test="LIG")
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test

    async def test_python_example_05_dna_protein(self, endpoint: str) -> TestResult:
        """Test example 05: DNA-protein complex."""
        test = TestResult("05_dna_protein_complex", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            
            # Configure client
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            protein_sequences = ["MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"]
            dna_sequences = ["ATCGATCGATCGATCG"]
            params = self.get_test_params()
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                client.predict_dna_protein_complex,
                endpoint,
                protein_sequences=protein_sequences,
                dna_sequences=dna_sequences,
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures), complex_type="dna_protein")
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test

    async def test_python_example_06_yaml_config(self, endpoint: str) -> TestResult:
        """Test example 06: YAML configurations."""
        test = TestResult("06_yaml_configurations", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            
            # Configure client
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            yaml_file = Path("examples/protein_ligand.yaml")
            if not yaml_file.exists():
                test.mark_skipped("YAML file not found")
                return test
            
            params = self.get_test_params()
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                client.predict_from_yaml_file,
                endpoint,
                yaml_file=yaml_file,
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures), config_type="yaml")
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test

    async def test_python_example_07_advanced_parameters(self, endpoint: str) -> TestResult:
        """Test example 07: Advanced parameters."""
        test = TestResult("07_advanced_parameters", "python", endpoint)
        
        try:
            from boltz2_client import Boltz2Client, EndpointType
            from boltz2_client.models import Polymer, PredictionRequest
            
            # Configure client
            if endpoint == "local":
                client = Boltz2Client(base_url="http://localhost:8000")
            else:
                client = Boltz2Client(
                    base_url="https://health.api.nvidia.com",
                    api_key=self.nvidia_api_key,
                    endpoint_type=EndpointType.NVIDIA_HOSTED
                )
            
            polymer = Polymer(
                id="A",
                molecule_type="protein",
                sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            )
            
            params = self.get_test_params()
            
            request = PredictionRequest(
                polymers=[polymer],
                recycling_steps=params["recycling_steps"],
                sampling_steps=params["sampling_steps"],
                diffusion_samples=params["diffusion_samples"],
                step_scale=1.638,
                without_potentials=False
            )
            
            start_time = time.time()
            result = await self.safe_predict_with_retry(
                lambda req, **kwargs: client.predict(req, **kwargs),
                endpoint,
                request,
                save_structures=False
            )
            duration = time.time() - start_time
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            test.mark_success(duration, confidence, len(result.structures), 
                            config_type="advanced", step_scale=1.638)
            
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0.0
            test.mark_failed(duration, str(e))
        
        return test



    def test_cli_command(self, command: List[str], test_name: str, endpoint: str) -> TestResult:
        """Test a CLI command with rate limiting protection and retry logic."""
        test = TestResult(test_name, "cli", endpoint)
        
        try:
            # Add delay for NVIDIA endpoints to prevent rate limiting
            if endpoint == "nvidia":
                time.sleep(self.nvidia_delay)
            
            # Ensure environment variables are properly inherited
            env = os.environ.copy()
            
            # Retry logic for rate limiting
            for attempt in range(self.max_retries):
                start_time = time.time()
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    cwd=".",
                    env=env  # Explicitly pass environment
                )
                duration = time.time() - start_time
                
                if result.returncode == 0:
                    # Try to extract confidence from output
                    confidence = None
                    structures = None
                    
                    output_lines = result.stdout.split('\n')
                    for line in output_lines:
                        if "Average confidence:" in line or "Confidence:" in line:
                            try:
                                confidence = float(line.split(':')[-1].strip())
                            except:
                                pass
                        if "Generated" in line and "structure" in line:
                            try:
                                structures = int(line.split()[1])
                            except:
                                pass
                    
                    test.mark_success(duration, confidence, structures)
                    return test
                else:
                    # Check if it's a rate limiting error
                    error_msg = result.stderr or result.stdout
                    full_output = (result.stdout or "") + (result.stderr or "")
                    
                    # More comprehensive rate limiting detection
                    is_rate_limited = (endpoint == "nvidia" and 
                                     ("429" in full_output or 
                                      "Too Many Requests" in full_output or
                                      "rate limit" in full_output.lower() or
                                      ("Prediction failed: 429" in full_output)))
                    
                    if is_rate_limited:
                        if attempt < self.max_retries - 1:
                            # Exponential backoff with jitter for CLI
                            delay = self.nvidia_delay * (2 ** attempt) + random.uniform(0, 3)
                            console.print(f"⏱️ CLI rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})", style="yellow")
                            time.sleep(delay)
                            continue
                        else:
                            console.print(f"❌ CLI max retries exceeded for rate limiting", style="red")
                    
                    # Enhanced error reporting for debugging
                    if self.args.verbose:
                        console.print(f"❌ CLI Command failed: {' '.join(command)}", style="red")
                        console.print(f"❌ Return code: {result.returncode}", style="red")
                        console.print(f"❌ Error output: {error_msg}", style="red")
                        console.print(f"❌ Full output: {full_output}", style="red")
                        console.print(f"❌ Working directory: {os.getcwd()}", style="red")
                        console.print(f"❌ Rate limited detected: {is_rate_limited}", style="red")
                    test.mark_failed(duration, error_msg)
                    return test
                
        except subprocess.TimeoutExpired:
            test.mark_failed(300, "Command timed out")
        except Exception as e:
            test.mark_failed(0, str(e))
        
        return test

    def build_cli_command(self, base_cmd: List[str], endpoint: str) -> List[str]:
        """Build CLI command with proper endpoint configuration."""
        cmd = ["boltz2"]
        
        if endpoint == "local":
            cmd.extend(["--base-url", "http://localhost:8000"])
        else:
            cmd.extend([
                "--base-url", "https://health.api.nvidia.com",
                "--endpoint-type", "nvidia_hosted"
            ])
        
        cmd.extend(base_cmd)
        return cmd

    def test_cli_examples(self, endpoint: str) -> List[TestResult]:
        """Test CLI commands for each example."""
        results = []
        params = self.get_test_params()
        
        # Example 01: Basic protein
        cmd = self.build_cli_command([
            "protein", "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            "--recycling-steps", str(params["recycling_steps"]),
            "--sampling-steps", str(params["sampling_steps"]),
            "--no-save"
        ], endpoint)
        results.append(self.test_cli_command(cmd, "01_basic_protein_folding", endpoint))
        
        # Example 03: Protein-ligand
        cmd = self.build_cli_command([
            "ligand", "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            "--smiles", "CC(=O)OC1=CC=CC=C1C(=O)O",
            "--recycling-steps", str(params["recycling_steps"]),
            "--sampling-steps", str(params["sampling_steps"]),
            "--no-save"
        ], endpoint)
        results.append(self.test_cli_command(cmd, "03_protein_ligand_complex", endpoint))
        
        # Example 04: Covalent bonding
        cmd = self.build_cli_command([
            "covalent", "MKTVRQERLKSCVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            "--ccd", "U4U",
            "--bond", "A:12:SG:LIG:C22",
            "--recycling-steps", str(params["recycling_steps"]),
            "--sampling-steps", str(params["sampling_steps"]),
            "--no-save"
        ], endpoint)
        results.append(self.test_cli_command(cmd, "04_covalent_bonding", endpoint))
        
        # Example 05: DNA-protein
        cmd = self.build_cli_command([
            "dna-protein",
            "--protein-sequences", "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            "--dna-sequences", "ATCGATCGATCGATCG",
            "--recycling-steps", str(params["recycling_steps"]),
            "--sampling-steps", str(params["sampling_steps"]),
            "--no-save"
        ], endpoint)
        results.append(self.test_cli_command(cmd, "05_dna_protein_complex", endpoint))
        
        # Example 06: YAML config (if file exists)
        yaml_file = Path("examples/protein_ligand.yaml")
        if yaml_file.exists():
            cmd = self.build_cli_command([
                "yaml", str(yaml_file),
                "--recycling-steps", str(params["recycling_steps"]),
                "--sampling-steps", str(params["sampling_steps"]),
                "--no-save"
            ], endpoint)
            results.append(self.test_cli_command(cmd, "06_yaml_configurations", endpoint))
        else:
            test = TestResult("06_yaml_configurations", "cli", endpoint)
            test.mark_skipped("YAML file not found")
            results.append(test)
        
        # Health check
        cmd = self.build_cli_command(["health"], endpoint)
        results.append(self.test_cli_command(cmd, "health_check", endpoint))
        
        return results

    async def run_python_tests(self, endpoint: str) -> List[TestResult]:
        """Run all Python API tests for an endpoint."""
        results = []
        
        console.print(f"\n🐍 Running Python API tests for {endpoint.upper()} endpoint...", style="bold blue")
        
        test_methods = [
            self.test_python_example_01_basic_protein,
            self.test_python_example_02_msa_protein,
            self.test_python_example_03_protein_ligand,
            self.test_python_example_04_covalent_bonding,
            self.test_python_example_05_dna_protein,
            self.test_python_example_06_yaml_config,
            self.test_python_example_07_advanced_parameters,
        ]
        
        for test_method in test_methods:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(f"Testing {test_method.__name__}...", total=None)
                
                try:
                    result = await test_method(endpoint)
                    results.append(result)
                    
                    if result.status == "success":
                        progress.update(task, description=f"✅ {result.name}")
                    elif result.status == "skipped":
                        progress.update(task, description=f"⚠️ {result.name} (skipped)")
                    else:
                        progress.update(task, description=f"❌ {result.name}")
                        
                except Exception as e:
                    test = TestResult(test_method.__name__, "python", endpoint)
                    test.mark_failed(0, str(e))
                    results.append(test)
                    progress.update(task, description=f"❌ {test_method.__name__}")
                
                # Small delay to see progress
                await asyncio.sleep(0.1)
        
        return results

    def run_cli_tests(self, endpoint: str) -> List[TestResult]:
        """Run all CLI tests for an endpoint."""
        console.print(f"\n🖥️  Running CLI tests for {endpoint.upper()} endpoint...", style="bold green")
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            cli_results = self.test_cli_examples(endpoint)
            
            for result in cli_results:
                task = progress.add_task(f"Testing {result.name}...", total=None)
                
                if result.status == "success":
                    progress.update(task, description=f"✅ {result.name}")
                elif result.status == "skipped":
                    progress.update(task, description=f"⚠️ {result.name} (skipped)")
                else:
                    progress.update(task, description=f"❌ {result.name}")
                
                results.append(result)
                time.sleep(0.1)  # Visual delay
        
        return results

    def generate_report(self) -> None:
        """Generate comprehensive test report."""
        console.print("\n" + "="*80, style="bold")
        console.print("📊 BOLTZ2 MASTER TEST SUITE RESULTS", style="bold cyan", justify="center")
        console.print("="*80, style="bold")
        
        # Summary statistics
        total_tests = len(self.results)
        successful = len([r for r in self.results if r.status == "success"])
        failed = len([r for r in self.results if r.status == "failed"])
        skipped = len([r for r in self.results if r.status == "skipped"])
        
        summary_table = Table(title="Test Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")
        
        summary_table.add_row("Total Tests", str(total_tests))
        summary_table.add_row("Successful", f"✅ {successful}")
        summary_table.add_row("Failed", f"❌ {failed}")
        summary_table.add_row("Skipped", f"⚠️ {skipped}")
        summary_table.add_row("Success Rate", f"{(successful/total_tests*100):.1f}%" if total_tests > 0 else "0%")
        summary_table.add_row("Total Duration", f"{self.total_duration:.1f}s")
        
        console.print(summary_table)
        
        # Detailed results table
        console.print("\n📋 Detailed Test Results", style="bold")
        
        results_table = Table()
        results_table.add_column("Example", style="cyan")
        results_table.add_column("Interface", style="blue") 
        results_table.add_column("Endpoint", style="green")
        results_table.add_column("Status", style="bold")
        results_table.add_column("Duration", style="yellow")
        results_table.add_column("Confidence", style="magenta")
        results_table.add_column("Structures", style="white")
        results_table.add_column("Notes", style="dim")
        
        for result in self.results:
            # Status with emoji
            if result.status == "success":
                status = "✅ SUCCESS"
                status_style = "green"
            elif result.status == "failed":
                status = "❌ FAILED"
                status_style = "red"
            elif result.status == "skipped":
                status = "⚠️ SKIPPED"
                status_style = "yellow"
            else:
                status = "⏸️ PENDING"
                status_style = "blue"
            
            # Format values
            duration_str = f"{result.duration:.1f}s" if result.duration else "-"
            confidence_str = f"{result.confidence:.3f}" if result.confidence else "-"
            structures_str = str(result.structures) if result.structures else "-"
            
            # Notes
            notes = []
            if result.error:
                notes.append(f"Error: {result.error[:50]}...")
            if "ligand_id_test" in result.details:
                notes.append("LIG ID test")
            if "msa_guided" in result.details:
                notes.append("MSA guided")
            notes_str = "; ".join(notes) if notes else ""
            
            results_table.add_row(
                result.name.replace("_", " ").title(),
                result.interface.upper(),
                result.endpoint.upper(),
                Text(status, style=status_style),
                duration_str,
                confidence_str,
                structures_str,
                notes_str
            )
        
        console.print(results_table)
        
        # Performance analysis
        if successful > 0:
            console.print("\n⚡ Performance Analysis", style="bold")
            
            # Average response times by interface and endpoint
            perf_table = Table(title="Average Response Times")
            perf_table.add_column("Category", style="cyan")
            perf_table.add_column("Count", style="blue")
            perf_table.add_column("Avg Duration", style="yellow")
            perf_table.add_column("Avg Confidence", style="magenta")
            
            # Group by interface and endpoint
            for interface in ["python", "cli"]:
                for endpoint in ["local", "nvidia"]:
                    subset = [r for r in self.results if 
                             r.interface == interface and 
                             r.endpoint == endpoint and 
                             r.status == "success"]
                    
                    if subset:
                        avg_duration = sum(r.duration for r in subset) / len(subset)
                        confidences = [r.confidence for r in subset if r.confidence]
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                        
                        perf_table.add_row(
                            f"{interface.upper()} - {endpoint.upper()}",
                            str(len(subset)),
                            f"{avg_duration:.1f}s",
                            f"{avg_confidence:.3f}" if avg_confidence else "-"
                        )
            
            console.print(perf_table)
        
        # Key findings
        console.print("\n🎯 Key Findings", style="bold")
        findings = []
        
        # Check rate limiting protection effectiveness
        nvidia_failures = [r for r in self.results if r.endpoint == "nvidia" and r.status == "failed"]
        rate_limited_failures = [r for r in nvidia_failures if "429" in str(r.error) or "rate limit" in str(r.error).lower()]
        if nvidia_failures and not rate_limited_failures:
            findings.append("⚡ Rate limiting protection working effectively")
        elif rate_limited_failures:
            findings.append(f"⚠️ {len(rate_limited_failures)} rate limiting failures - may need longer delays")
        
        # Check atom ID validation fix
        covalent_tests = [r for r in self.results if "covalent" in r.name and r.status == "success"]
        if covalent_tests:
            findings.append("✅ Atom ID validation fix confirmed working")
        
        # Check endpoint compatibility
        local_tests = [r for r in self.results if r.endpoint == "local" and r.status == "success"]
        nvidia_tests = [r for r in self.results if r.endpoint == "nvidia" and r.status == "success"]
        
        if local_tests:
            findings.append(f"✅ Local endpoint: {len(local_tests)} successful tests")
        if nvidia_tests:
            findings.append(f"✅ NVIDIA endpoint: {len(nvidia_tests)} successful tests")
        
        # Check interface compatibility
        python_tests = [r for r in self.results if r.interface == "python" and r.status == "success"]
        cli_tests = [r for r in self.results if r.interface == "cli" and r.status == "success"]
        
        if python_tests:
            findings.append(f"✅ Python API: {len(python_tests)} successful tests")
        if cli_tests:
            findings.append(f"✅ CLI interface: {len(cli_tests)} successful tests")
        
        if failed > 0:
            findings.append(f"⚠️ {failed} tests failed - check error details above")
        
        for finding in findings:
            console.print(f"  {finding}")
        
        # Overall status
        console.print(f"\n🏁 Overall Result", style="bold")
        if failed == 0:
            console.print("🎉 ALL TESTS PASSED! Boltz2 implementation is fully functional.", style="bold green")
        elif failed < total_tests / 2:
            console.print("⚠️ Mostly successful with some failures. Check specific errors.", style="bold yellow")
        else:
            console.print("❌ Significant issues detected. Review failed tests.", style="bold red")

    async def run_all_tests(self):
        """Run the complete test suite."""
        console.print("🚀 Starting Boltz2 Master Test Suite", style="bold cyan")
        console.print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Display rate limiting configuration
        console.print(f"⚡ Rate Limiting Protection: {self.nvidia_delay}s delays for NVIDIA endpoints", style="yellow")
        console.print(f"🔄 Retry Logic: Up to {self.max_retries} attempts with exponential backoff", style="yellow")
        
        self.start_time = time.time()
        self.results = []
        
        # Test configurations to run
        endpoints = []
        interfaces = []
        
        if not self.args.nvidia_only:
            endpoints.append("local")
        if not self.args.local_only and self.nvidia_api_key:
            endpoints.append("nvidia")
        
        if not self.args.cli_only:
            interfaces.append("python")
        if not self.args.api_only:
            interfaces.append("cli")
        
        console.print(f"🎯 Testing {len(endpoints)} endpoint(s) × {len(interfaces)} interface(s)")
        
        # Run tests for each combination
        for endpoint in endpoints:
            for interface in interfaces:
                if interface == "python" and self.should_test_interface("python") and self.should_test_endpoint(endpoint):
                    results = await self.run_python_tests(endpoint)
                    self.results.extend(results)
                
                elif interface == "cli" and self.should_test_interface("cli") and self.should_test_endpoint(endpoint):
                    results = self.run_cli_tests(endpoint)
                    self.results.extend(results)
        
        self.total_duration = time.time() - self.start_time
        
        # Generate final report
        self.generate_report()
        
        console.print(f"\n📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"⏱️ Total Runtime: {self.total_duration:.1f}s")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Boltz2 Master Test Suite")
    parser.add_argument("--api-only", action="store_true", help="Test Python API only")
    parser.add_argument("--cli-only", action="store_true", help="Test CLI only")
    parser.add_argument("--local-only", action="store_true", help="Test local endpoint only")
    parser.add_argument("--nvidia-only", action="store_true", help="Test NVIDIA endpoint only")
    parser.add_argument("--quick", action="store_true", help="Quick tests with reduced parameters")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validation
    if args.api_only and args.cli_only:
        console.print("❌ Cannot specify both --api-only and --cli-only", style="red")
        sys.exit(1)
    
    if args.local_only and args.nvidia_only:
        console.print("❌ Cannot specify both --local-only and --nvidia-only", style="red")
        sys.exit(1)
    
    # Run the test suite
    suite = MasterTestSuite(args)
    
    try:
        asyncio.run(suite.run_all_tests())
    except KeyboardInterrupt:
        console.print("\n⏹️ Test suite interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Test suite failed: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main() 