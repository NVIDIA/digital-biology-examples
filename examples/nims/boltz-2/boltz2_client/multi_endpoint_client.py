# ---------------------------------------------------------------
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Multi-Endpoint Client for Boltz-2

Provides load balancing across multiple Boltz-2 NIM endpoints
for improved throughput and parallelization in virtual screening.
"""

import asyncio
import random
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from rich.console import Console

from .client import Boltz2Client, Boltz2SyncClient, EndpointType
from .models import PredictionRequest, PredictionResponse, HealthStatus, ServiceMetadata, AlignmentFileRecord
from .exceptions import Boltz2APIError, Boltz2TimeoutError


class LoadBalanceStrategy(Enum):
    """Load balancing strategies for multi-endpoint client."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"


@dataclass
class EndpointConfig:
    """Configuration for a single endpoint."""
    base_url: str
    api_key: Optional[str] = None
    endpoint_type: str = EndpointType.LOCAL
    weight: float = 1.0  # For weighted load balancing
    max_concurrent_requests: int = 10
    

@dataclass
class EndpointStatus:
    """Runtime status of an endpoint."""
    endpoint_config: EndpointConfig
    client: Union[Boltz2Client, Boltz2SyncClient]
    is_healthy: bool = True
    last_health_check: float = 0
    current_requests: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0


class MultiEndpointClient:
    """
    Client that manages multiple Boltz-2 endpoints with load balancing.
    
    Supports both synchronous and asynchronous operations with automatic
    failover and health checking.
    """
    
    def __init__(
        self,
        endpoints: List[Union[EndpointConfig, Dict[str, Any], str]],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        health_check_interval: float = 60.0,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        console: Optional[Console] = None,
        is_async: bool = True
    ):
        """
        Initialize multi-endpoint client.
        
        Args:
            endpoints: List of endpoint configurations. Can be:
                - EndpointConfig objects
                - Dict with EndpointConfig fields
                - String URLs (will use default settings)
            strategy: Load balancing strategy
            health_check_interval: Seconds between health checks
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts per endpoint
            retry_delay: Delay between retries
            console: Rich console for output
            is_async: Whether to use async or sync clients
        """
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.console = console or Console()
        self.is_async = is_async
        
        # Parse and initialize endpoints
        self.endpoints: List[EndpointStatus] = []
        self._round_robin_index = 0
        
        for endpoint in endpoints:
            config = self._parse_endpoint_config(endpoint)
            client = self._create_client(config)
            status = EndpointStatus(
                endpoint_config=config,
                client=client
            )
            self.endpoints.append(status)
        
        if not self.endpoints:
            raise ValueError("At least one endpoint must be provided")
        
        # Start health check task if async
        self._health_check_task = None
        if is_async:
            try:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            except RuntimeError:
                # No event loop running, skip async health checks
                pass
    
    def _parse_endpoint_config(self, endpoint: Union[EndpointConfig, Dict, str]) -> EndpointConfig:
        """Parse various endpoint configuration formats."""
        if isinstance(endpoint, EndpointConfig):
            return endpoint
        elif isinstance(endpoint, dict):
            return EndpointConfig(**endpoint)
        elif isinstance(endpoint, str):
            # Simple URL string
            return EndpointConfig(base_url=endpoint)
        else:
            raise ValueError(f"Invalid endpoint configuration: {endpoint}")
    
    def _create_client(self, config: EndpointConfig) -> Union[Boltz2Client, Boltz2SyncClient]:
        """Create a client instance for an endpoint."""
        ClientClass = Boltz2Client if self.is_async else Boltz2SyncClient
        return ClientClass(
            base_url=config.base_url,
            api_key=config.api_key,
            endpoint_type=config.endpoint_type,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            console=self.console
        )
    
    async def _health_check_loop(self):
        """Background task to periodically check endpoint health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_endpoints_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.console.print(f"[red]Health check error: {e}[/red]")
    
    async def _check_all_endpoints_health(self):
        """Check health of all endpoints."""
        tasks = []
        for endpoint in self.endpoints:
            if time.time() - endpoint.last_health_check > self.health_check_interval:
                tasks.append(self._check_endpoint_health(endpoint))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_endpoint_health(self, endpoint: EndpointStatus):
        """Check health of a single endpoint."""
        try:
            if self.is_async:
                health = await endpoint.client.health_check()
            else:
                health = endpoint.client.health_check()
            
            # Normalize to boolean
            status_value = getattr(health, "status", health)
            endpoint.is_healthy = (status_value == "healthy") if isinstance(status_value, str) else bool(health)
            endpoint.last_health_check = time.time()
            
            if endpoint.is_healthy and endpoint.failed_requests > 0:
                # Reset failed requests on recovery
                endpoint.failed_requests = 0
                self.console.print(f"[green]Endpoint {endpoint.endpoint_config.base_url} recovered[/green]")
        except Exception:
            endpoint.is_healthy = False
            endpoint.last_health_check = time.time()
    
    def _get_healthy_endpoints(self) -> List[EndpointStatus]:
        """Get list of currently healthy endpoints."""
        return [ep for ep in self.endpoints if ep.is_healthy]
    
    
    def get_healthy_endpoints(self) -> List[str]:
        """
        Get list of URLs for currently healthy endpoints.
        
        Returns:
            List of healthy endpoint URLs
        """
        healthy = self._get_healthy_endpoints()
        return [ep.endpoint_config.base_url for ep in healthy]
    
    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status of all endpoints.
        
        Returns:
            Dictionary mapping endpoint URLs to their status
        """
        status = {}
        for ep in self.endpoints:
            status[ep.endpoint_config.base_url] = {
                "status": "healthy" if ep.is_healthy else "unhealthy",
                "last_check": ep.last_health_check,
                "current_requests": ep.current_requests,
                "total_requests": ep.total_requests,
                "failed_requests": ep.failed_requests,
                "avg_response_time": ep.average_response_time
            }
        return status

    def _select_endpoint(self) -> Optional[EndpointStatus]:
        """Select an endpoint based on the configured strategy."""
        healthy_endpoints = self._get_healthy_endpoints()
        
        if not healthy_endpoints:
            # Try all endpoints if none are marked healthy
            healthy_endpoints = self.endpoints
        
        if not healthy_endpoints:
            return None
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            endpoint = healthy_endpoints[self._round_robin_index % len(healthy_endpoints)]
            self._round_robin_index += 1
            return endpoint
        
        elif self.strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(healthy_endpoints)
        
        elif self.strategy == LoadBalanceStrategy.LEAST_LOADED:
            # Select endpoint with fewest current requests
            return min(healthy_endpoints, key=lambda ep: ep.current_requests)
        
        elif self.strategy == LoadBalanceStrategy.WEIGHTED:
            # Weighted random selection
            weights = [ep.endpoint_config.weight for ep in healthy_endpoints]
            return random.choices(healthy_endpoints, weights=weights)[0]
        
        return healthy_endpoints[0]
    
    async def predict(self, request: PredictionRequest) -> PredictionResponse:
        """
        Make a prediction using load balancing across endpoints.
        
        Args:
            request: Prediction request
            
        Returns:
            PredictionResponse from the successful endpoint
            
        Raises:
            Boltz2APIError: If all endpoints fail
        """
        errors = []
        attempted_endpoints = set()
        
        # Try each endpoint until success
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            # Use endpoint URL as key since EndpointStatus is not hashable
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                # Already tried this endpoint
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                # Track request
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                # Make the request
                if self.is_async:
                    response = await endpoint.client.predict(request)
                else:
                    response = endpoint.client.predict(request)
                
                # Update statistics
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint.endpoint_config.base_url}: {str(e)}")
                
                # Mark unhealthy if too many failures
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint.endpoint_config.base_url} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        # All endpoints failed
        raise Boltz2APIError(
            f"All endpoints failed. Errors: {'; '.join(errors)}"
        )
    
    def predict_sync(self, request: PredictionRequest) -> PredictionResponse:
        """Synchronous version of predict."""
        if self.is_async:
            raise RuntimeError("Use predict() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        # Try each endpoint until success
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            # Use endpoint URL as key since EndpointStatus is not hashable
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                # Already tried this endpoint
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                # Track request
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                # Make the synchronous request
                response = endpoint.client.predict(request)
                
                # Update statistics
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint.endpoint_config.base_url}: {str(e)}")
                
                # Mark unhealthy if too many failures
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint.endpoint_config.base_url} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        # All endpoints failed
        raise Boltz2APIError(
            f"All endpoints failed. Errors: {'; '.join(errors)}"
        )
    
    async def predict_protein_structure(
        self,
        sequence: str,
        polymer_id: str = "A",
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        diffusion_samples: int = 1,
        step_scale: float = 1.638,
        msa_files: Optional[List[Tuple[str, str]]] = None,
        msa: Optional[Dict[str, Dict[str, AlignmentFileRecord]]] = None,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict protein structure using load balancing across endpoints.
        
        Args:
            sequence: Protein amino acid sequence
            polymer_id: Polymer identifier (default: A)
            recycling_steps: Number of recycling steps (1-6)
            sampling_steps: Number of sampling steps (10-1000)
            diffusion_samples: Number of diffusion samples (1-5)
            step_scale: Step scale for diffusion sampling (0.5-5.0)
            msa_files: List of (file_path, format) tuples for MSA guidance
            save_structures: Whether to save structure files
            output_dir: Directory to save output files
            progress_callback: Progress callback function
            
        Returns:
            PredictionResponse from the successful endpoint
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_protein_structure(
                        sequence=sequence,
                        polymer_id=polymer_id,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        diffusion_samples=diffusion_samples,
                        step_scale=step_scale,
                        msa_files=msa_files,
                        msa=msa,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_protein_structure(
                        sequence=sequence,
                        polymer_id=polymer_id,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        diffusion_samples=diffusion_samples,
                        step_scale=step_scale,
                        msa_files=msa_files,
                        msa=msa,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for protein structure prediction. Errors: {'; '.join(errors)}"
        )
    
    async def predict_protein_ligand_complex(
        self,
        protein_sequence: str,
        ligand_smiles: Optional[str] = None,
        ligand_ccd: Optional[str] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        pocket_residues: Optional[List[int]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        predict_affinity: bool = False,
        sampling_steps_affinity: Optional[int] = None,
        diffusion_samples_affinity: Optional[int] = None,
        affinity_mw_correction: Optional[bool] = None,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict protein-ligand complex using load balancing across endpoints.
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_protein_ligand_complex(
                        protein_sequence=protein_sequence,
                        ligand_smiles=ligand_smiles,
                        ligand_ccd=ligand_ccd,
                        protein_id=protein_id,
                        ligand_id=ligand_id,
                        pocket_residues=pocket_residues,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        predict_affinity=predict_affinity,
                        sampling_steps_affinity=sampling_steps_affinity,
                        diffusion_samples_affinity=diffusion_samples_affinity,
                        affinity_mw_correction=affinity_mw_correction,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_protein_ligand_complex(
                        protein_sequence=protein_sequence,
                        ligand_smiles=ligand_smiles,
                        ligand_ccd=ligand_ccd,
                        protein_id=protein_id,
                        ligand_id=ligand_id,
                        pocket_residues=pocket_residues,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        predict_affinity=predict_affinity,
                        sampling_steps_affinity=sampling_steps_affinity,
                        diffusion_samples_affinity=diffusion_samples_affinity,
                        affinity_mw_correction=affinity_mw_correction,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for protein-ligand complex prediction. Errors: {'; '.join(errors)}"
        )
    
    async def predict_covalent_complex(
        self,
        protein_sequence: str,
        ligand_ccd: str,
        covalent_bonds: Optional[List[Tuple[int, str, str]]] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict covalent complex using load balancing across endpoints.
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_covalent_complex(
                        protein_sequence=protein_sequence,
                        ligand_ccd=ligand_ccd,
                        covalent_bonds=covalent_bonds,
                        protein_id=protein_id,
                        ligand_id=ligand_id,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_covalent_complex(
                        protein_sequence=protein_sequence,
                        ligand_ccd=ligand_ccd,
                        covalent_bonds=covalent_bonds,
                        protein_id=protein_id,
                        ligand_id=ligand_id,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for covalent complex prediction. Errors: {'; '.join(errors)}"
        )
    
    async def predict_dna_protein_complex(
        self,
        protein_sequences: List[str],
        dna_sequences: List[str],
        protein_ids: Optional[List[str]] = None,
        dna_ids: Optional[List[str]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        concatenate_msas: bool = False,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict DNA-protein complex using load balancing across endpoints.
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_dna_protein_complex(
                        protein_sequences=protein_sequences,
                        dna_sequences=dna_sequences,
                        protein_ids=protein_ids,
                        dna_ids=dna_ids,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        concatenate_msas=concatenate_msas,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_dna_protein_complex(
                        protein_sequences=protein_sequences,
                        dna_sequences=dna_sequences,
                        protein_ids=protein_ids,
                        dna_ids=dna_ids,
                        recycling_steps=recycling_steps,
                        sampling_steps=sampling_steps,
                        concatenate_msas=concatenate_msas,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for DNA-protein complex prediction. Errors: {'; '.join(errors)}"
        )
    
    async def predict_with_advanced_parameters(
        self,
        request: PredictionRequest,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict with advanced parameters using load balancing across endpoints.
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_with_advanced_parameters(
                        request=request,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_with_advanced_parameters(
                        request=request,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for advanced parameter prediction. Errors: {'; '.join(errors)}"
        )
    
    async def predict_from_yaml_config(
        self,
        config: Any,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict from YAML config using load balancing across endpoints.
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_from_yaml_config(
                        config=config,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_from_yaml_config(
                        config=config,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for YAML config prediction. Errors: {'; '.join(errors)}"
        )
    
    async def predict_from_yaml_file(
        self,
        yaml_file: Union[str, Path],
        msa_dir: Optional[Union[str, Path]] = None,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """
        Predict from YAML file using load balancing across endpoints.
        """
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                if self.is_async:
                    response = await endpoint.client.predict_from_yaml_file(
                        yaml_file=yaml_file,
                        msa_dir=msa_dir,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                else:
                    response = endpoint.client.predict_from_yaml_file(
                        yaml_file=yaml_file,
                        msa_dir=msa_dir,
                        save_structures=save_structures,
                        output_dir=output_dir,
                        progress_callback=progress_callback
                    )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for YAML file prediction. Errors: {'; '.join(errors)}"
        )
    
    async def health_check(self) -> HealthStatus:
        """
        Check health of all endpoints and return aggregate status.
        """
        healthy_count = 0
        total_endpoints = len(self.endpoints)
        
        for endpoint in self.endpoints:
            try:
                if self.is_async:
                    health = await endpoint.client.health_check()
                else:
                    health = endpoint.client.health_check()
                
                status_value = getattr(health, "status", health)
                endpoint.is_healthy = (status_value == "healthy") if isinstance(status_value, str) else bool(health)
                endpoint.last_health_check = time.time()
                
                if endpoint.is_healthy:
                    healthy_count += 1
                    if endpoint.failed_requests > 0:
                        endpoint.failed_requests = 0
                        self.console.print(f"[green]Endpoint {endpoint.endpoint_config.base_url} recovered[/green]")
                else:
                    endpoint.is_healthy = False
                    
            except Exception:
                endpoint.is_healthy = False
                endpoint.last_health_check = time.time()
        
        # Return aggregate health status
        if healthy_count == total_endpoints:
            return HealthStatus(status="healthy", details={"healthy_endpoints": healthy_count, "total_endpoints": total_endpoints})
        elif healthy_count > 0:
            return HealthStatus(status="degraded", details={"healthy_endpoints": healthy_count, "total_endpoints": total_endpoints})
        else:
            return HealthStatus(status="unhealthy", details={"healthy_endpoints": healthy_count, "total_endpoints": total_endpoints})
    
    async def get_service_metadata(self) -> ServiceMetadata:
        """
        Get service metadata from the first healthy endpoint.
        """
        healthy_endpoints = self._get_healthy_endpoints()
        
        if not healthy_endpoints:
            # Try all endpoints if none are marked healthy
            healthy_endpoints = self.endpoints
        
        if not healthy_endpoints:
            raise Boltz2APIError("No endpoints available for metadata retrieval")
        
        # Use the first healthy endpoint
        endpoint = healthy_endpoints[0]
        
        try:
            if self.is_async:
                return await endpoint.client.get_service_metadata()
            else:
                return endpoint.client.get_service_metadata()
        except Exception as e:
            raise Boltz2APIError(f"Failed to get service metadata from {endpoint.endpoint_config.base_url}: {str(e)}")

    # Synchronous versions for sync client
    def predict_protein_structure_sync(
        self,
        sequence: str,
        polymer_id: str = "A",
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        diffusion_samples: int = 1,
        step_scale: float = 1.638,
        msa_files: Optional[List[Tuple[str, str]]] = None,
        msa: Optional[Dict[str, Dict[str, AlignmentFileRecord]]] = None,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_protein_structure."""
        if self.is_async:
            raise RuntimeError("Use predict_protein_structure() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_protein_structure(
                    sequence=sequence,
                    polymer_id=polymer_id,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    diffusion_samples=diffusion_samples,
                    step_scale=step_scale,
                    msa_files=msa_files,
                    msa=msa,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for protein structure prediction. Errors: {'; '.join(errors)}"
        )
    
    def predict_protein_ligand_complex_sync(
        self,
        protein_sequence: str,
        ligand_smiles: Optional[str] = None,
        ligand_ccd: Optional[str] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        pocket_residues: Optional[List[int]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_protein_ligand_complex."""
        if self.is_async:
            raise RuntimeError("Use predict_protein_ligand_complex() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_protein_ligand_complex(
                    protein_sequence=protein_sequence,
                    ligand_smiles=ligand_smiles,
                    ligand_ccd=ligand_ccd,
                    protein_id=protein_id,
                    ligand_id=ligand_id,
                    pocket_residues=pocket_residues,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for protein-ligand complex prediction. Errors: {'; '.join(errors)}"
        )
    
    def predict_covalent_complex_sync(
        self,
        protein_sequence: str,
        ligand_ccd: str,
        covalent_bonds: Optional[List[Tuple[int, str, str]]] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_covalent_complex."""
        if self.is_async:
            raise RuntimeError("Use predict_covalent_complex() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_covalent_complex(
                    protein_sequence=protein_sequence,
                    ligand_ccd=ligand_ccd,
                    covalent_bonds=covalent_bonds,
                    protein_id=protein_id,
                    ligand_id=ligand_id,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for covalent complex prediction. Errors: {'; '.join(errors)}"
        )
    
    def predict_dna_protein_complex_sync(
        self,
        protein_sequences: List[str],
        dna_sequences: List[str],
        protein_ids: Optional[List[str]] = None,
        dna_ids: Optional[List[str]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        concatenate_msas: bool = False,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_dna_protein_complex."""
        if self.is_async:
            raise RuntimeError("Use predict_dna_protein_complex() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_dna_protein_complex(
                    protein_sequences=protein_sequences,
                    dna_sequences=dna_sequences,
                    protein_ids=protein_ids,
                    dna_ids=dna_ids,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    concatenate_msas=concatenate_msas,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for DNA-protein complex prediction. Errors: {'; '.join(errors)}"
        )
    
    def predict_with_advanced_parameters_sync(
        self,
        request: PredictionRequest,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_with_advanced_parameters."""
        if self.is_async:
            raise RuntimeError("Use predict_with_advanced_parameters() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_with_advanced_parameters(
                    request=request,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for advanced parameter prediction. Errors: {'; '.join(errors)}"
        )
    
    def predict_from_yaml_config_sync(
        self,
        config: Any,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_from_yaml_config."""
        if self.is_async:
            raise RuntimeError("Use predict_from_yaml_config() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_from_yaml_config(
                    config=config,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for YAML config prediction. Errors: {'; '.join(errors)}"
        )
    
    def predict_from_yaml_file_sync(
        self,
        yaml_file: Union[str, Path],
        msa_dir: Optional[Union[str, Path]] = None,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> PredictionResponse:
        """Synchronous version of predict_from_yaml_file."""
        if self.is_async:
            raise RuntimeError("Use predict_from_yaml_file() for async client")
        
        errors = []
        attempted_endpoints = set()
        
        while len(attempted_endpoints) < len(self.endpoints):
            endpoint = self._select_endpoint()
            
            if not endpoint:
                break
                
            endpoint_key = endpoint.endpoint_config.base_url
            if endpoint_key in attempted_endpoints:
                continue
            
            attempted_endpoints.add(endpoint_key)
            
            try:
                endpoint.current_requests += 1
                endpoint.total_requests += 1
                
                start_time = time.time()
                
                response = endpoint.client.predict_from_yaml_file(
                    yaml_file=yaml_file,
                    msa_dir=msa_dir,
                    save_structures=save_structures,
                    output_dir=output_dir,
                    progress_callback=progress_callback
                )
                
                elapsed = time.time() - start_time
                endpoint.average_response_time = (
                    (endpoint.average_response_time * (endpoint.total_requests - 1) + elapsed)
                    / endpoint.total_requests
                )
                
                return response
                
            except Exception as e:
                endpoint.failed_requests += 1
                errors.append(f"{endpoint_key}: {str(e)}")
                
                if endpoint.failed_requests >= 3:
                    endpoint.is_healthy = False
                    self.console.print(
                        f"[red]Endpoint {endpoint_key} marked unhealthy[/red]"
                    )
                
            finally:
                endpoint.current_requests -= 1
        
        raise Boltz2APIError(
            f"All endpoints failed for YAML file prediction. Errors: {'; '.join(errors)}"
        )
    
    def health_check_sync(self) -> HealthStatus:
        """Synchronous version of health_check."""
        if self.is_async:
            raise RuntimeError("Use health_check() for async client")
        
        healthy_count = 0
        total_endpoints = len(self.endpoints)
        
        for endpoint in self.endpoints:
            try:
                is_healthy = endpoint.client.health_check()
                endpoint.is_healthy = is_healthy
                endpoint.last_health_check = time.time()
                
                if is_healthy:
                    healthy_count += 1
                    if endpoint.failed_requests > 0:
                        endpoint.failed_requests = 0
                        self.console.print(f"[green]Endpoint {endpoint.endpoint_config.base_url} recovered[/green]")
                else:
                    endpoint.is_healthy = False
                    
            except Exception:
                endpoint.is_healthy = False
                endpoint.last_health_check = time.time()
        
        # Return aggregate health status
        if healthy_count == total_endpoints:
            return HealthStatus(status="healthy", details={"healthy_endpoints": healthy_count, "total_endpoints": total_endpoints})
        elif healthy_count > 0:
            return HealthStatus(status="degraded", details={"healthy_endpoints": healthy_count, "total_endpoints": total_endpoints})
        else:
            return HealthStatus(status="unhealthy", details={"healthy_endpoints": healthy_count, "total_endpoints": total_endpoints})
    
    def get_service_metadata_sync(self) -> ServiceMetadata:
        """Synchronous version of get_service_metadata."""
        if self.is_async:
            raise RuntimeError("Use get_service_metadata() for async client")
        
        healthy_endpoints = self._get_healthy_endpoints()
        
        if not healthy_endpoints:
            # Try all endpoints if none are marked healthy
            healthy_endpoints = self.endpoints
        
        if not healthy_endpoints:
            raise Boltz2APIError("No endpoints available for metadata retrieval")
        
        # Use the first healthy endpoint
        endpoint = healthy_endpoints[0]
        
        try:
            return endpoint.client.get_service_metadata()
        except Exception as e:
            raise Boltz2APIError(f"Failed to get service metadata from {endpoint.endpoint_config.base_url}: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all endpoints."""
        return {
            "strategy": self.strategy.value,
            "endpoints": [
                {
                    "url": ep.endpoint_config.base_url,
                    "healthy": ep.is_healthy,
                    "current_requests": ep.current_requests,
                    "total_requests": ep.total_requests,
                    "failed_requests": ep.failed_requests,
                    "avg_response_time": round(ep.average_response_time, 2)
                }
                for ep in self.endpoints
            ]
        }
    
    def print_status(self):
        """Print formatted status to console."""
        from rich.table import Table
        
        table = Table(title="Multi-Endpoint Status")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Current", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Avg Time (s)", justify="right")
        
        for ep in self.endpoints:
            status = "✓ Healthy" if ep.is_healthy else "✗ Unhealthy"
            status_style = "green" if ep.is_healthy else "red"
            
            table.add_row(
                ep.endpoint_config.base_url,
                f"[{status_style}]{status}[/{status_style}]",
                str(ep.current_requests),
                str(ep.total_requests),
                str(ep.failed_requests),
                f"{ep.average_response_time:.2f}"
            )
        
        self.console.print(table)
    
    async def close(self):
        """Clean up resources."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_async:
            asyncio.create_task(self.close())
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()