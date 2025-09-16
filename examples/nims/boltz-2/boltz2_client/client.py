# ---------------------------------------------------------------
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------


"""
Boltz-2 Python Client

This module provides both synchronous and asynchronous clients for interacting
with the Boltz-2 NIM API, with comprehensive support for all available parameters
and advanced features.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from urllib.parse import urljoin
import os

import httpx
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from .models import (
    PredictionRequest, PredictionResponse, HealthStatus, ServiceMetadata,
    Polymer, Ligand, PocketConstraint, BondConstraint, Atom, AlignmentFileRecord,
    StructureData, PredictionJob, PolymerType, AlignmentFormat, ConstraintType,
    YAMLConfig, YAMLConfigType
)
from .exceptions import (
    Boltz2ClientError, Boltz2APIError, Boltz2ValidationError, 
    Boltz2TimeoutError, Boltz2ConnectionError
)
from .msa_search import (
    MSASearchClient, MSASearchIntegration, MSASearchRequest,
    MSASearchResponse, MSAFormatConverter
)


class EndpointType:
    """Endpoint type constants."""
    LOCAL = "local"
    NVIDIA_HOSTED = "nvidia_hosted"


class Boltz2Client:
    """
    Asynchronous client for Boltz-2 NIM service.
    
    Supports both local deployments and NVIDIA hosted endpoints with API key authentication.
    Provides comprehensive structure prediction capabilities with all available parameters.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        endpoint_type: str = EndpointType.LOCAL,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        poll_seconds: int = 10,
        console: Optional[Console] = None
    ):
        """
        Initialize the Boltz-2 client.
        
        Args:
            base_url: Base URL of the service
                - Local: "http://localhost:8000" 
                - NVIDIA Hosted: "https://health.api.nvidia.com"
            api_key: API key for NVIDIA hosted endpoints (can also be set via NVIDIA_API_KEY env var)
            endpoint_type: Type of endpoint ("local" or "nvidia_hosted")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            poll_seconds: Polling interval for NVIDIA hosted endpoints (NVCF-POLL-SECONDS)
            console: Rich console for output (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint_type = endpoint_type
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.poll_seconds = poll_seconds
        self.console = console or Console()
        
        # Handle API key for NVIDIA hosted endpoints
        if endpoint_type == EndpointType.NVIDIA_HOSTED:
            self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
            if not self.api_key:
                raise Boltz2ValidationError(
                    "API key is required for NVIDIA hosted endpoints. "
                    "Provide it via api_key parameter or NVIDIA_API_KEY environment variable."
                )
        else:
            self.api_key = None
        
        # Set up URLs based on endpoint type
        if endpoint_type == EndpointType.NVIDIA_HOSTED:
            self.predict_url = f"{self.base_url}/v1/biology/mit/boltz2/predict"
            self.health_url = f"{self.base_url}/v1/health/ready"
            self.ready_url = f"{self.base_url}/v1/health/ready"
            self.metadata_url = f"{self.base_url}/v1/metadata"
            self.status_url = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{task_id}"
        else:
            # Local endpoints
            self.predict_url = f"{self.base_url}/biology/mit/boltz2/predict"
            self.health_url = f"{self.base_url}/v1/health/ready"
            self.ready_url = f"{self.base_url}/v1/health/ready"
            self.metadata_url = f"{self.base_url}/v1/metadata"
            self.status_url = None
        
        # Initialize MSA search client (optional)
        self._msa_search_client = None
        self._msa_search_integration = None

    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get headers for requests based on endpoint type."""
        headers = {"Content-Type": "application/json"}
        
        if self.endpoint_type == EndpointType.NVIDIA_HOSTED:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["NVCF-POLL-SECONDS"] = str(self.poll_seconds)
        
        if additional_headers:
            headers.update(additional_headers)
            
        return headers

    async def _handle_nvidia_polling(
        self, 
        client: httpx.AsyncClient, 
        response: httpx.Response,
        progress_callback: Optional[Callable] = None
    ) -> httpx.Response:
        """Handle NVIDIA hosted endpoint polling for 202 responses."""
        if response.status_code != 202:
            return response
            
        task_id = response.headers.get("nvcf-reqid")
        if not task_id:
            raise Boltz2APIError("No task ID found in 202 response headers")
            
        if progress_callback:
            progress_callback(f"Request queued, polling task {task_id}...")
            
        headers = self._get_headers()
        
        while True:
            await asyncio.sleep(self.poll_seconds)
            
            status_response = await client.get(
                self.status_url.format(task_id=task_id),
                headers=headers,
                timeout=self.timeout
            )
            
            if status_response.status_code == 200:
                if progress_callback:
                    progress_callback("Task completed successfully")
                return status_response
            elif status_response.status_code in [400, 401, 404, 422, 500]:
                error_detail = status_response.text
                raise Boltz2APIError(f"Task failed with status {status_response.status_code}: {error_detail}")
            
            if progress_callback:
                progress_callback(f"Task still processing... (status: {status_response.status_code})")

    async def health_check(self) -> HealthStatus:
        """Check the health status of the Boltz-2 service."""
        try:
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.health_url, headers=headers)
                response.raise_for_status()
                
                return HealthStatus(
                    status="healthy" if response.status_code == 200 else "unhealthy",
                    timestamp=datetime.now(),
                    details={"status_code": response.status_code}
                )
        except Exception as e:
            raise Boltz2ConnectionError(f"Health check failed: {e}")

    async def get_service_metadata(self) -> ServiceMetadata:
        """Get service metadata and model information."""
        try:
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.metadata_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return ServiceMetadata(**data)
        except Exception as e:
            raise Boltz2APIError(f"Failed to get service metadata: {e}")

    async def predict(
        self,
        request: PredictionRequest,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[callable] = None
    ) -> PredictionResponse:
        """
        Make a structure prediction request with comprehensive parameter support.
        
        Args:
            request: Complete prediction request with all parameters
            save_structures: Whether to save structures to files
            output_dir: Directory to save structures (default: current directory)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Prediction response with structures and metadata
        """
        if output_dir is None:
            output_dir = Path.cwd()
        
        try:
            # Validate request
            request_dict = request.dict(exclude_none=True)
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if progress_callback:
                    progress_callback("Sending prediction request...")
                
                start_time = time.time()
                response = await client.post(
                    self.predict_url,
                    json=request_dict,
                    headers=headers
                )
                
                # Handle NVIDIA hosted endpoint polling
                if self.endpoint_type == EndpointType.NVIDIA_HOSTED:
                    response = await self._handle_nvidia_polling(client, response, progress_callback)
                
                if response.status_code != 200:
                    error_detail = response.text
                    raise Boltz2APIError(f"Prediction failed: {response.status_code} - {error_detail}")
                
                end_time = time.time()
                prediction_time = end_time - start_time
                
                if progress_callback:
                    progress_callback(f"Prediction completed in {prediction_time:.2f}s")
                
                # Parse response
                response_data = response.json()
                prediction_response = PredictionResponse(**response_data)
                
                # Save structures if requested
                if save_structures:
                    await self._save_structures(prediction_response, output_dir, progress_callback)
                
                return prediction_response
                
        except httpx.TimeoutException:
            raise Boltz2TimeoutError(f"Request timed out after {self.timeout} seconds")
        except httpx.RequestError as e:
            raise Boltz2ConnectionError(f"Connection error: {e}")
        except Exception as e:
            if isinstance(e, (Boltz2ClientError, Boltz2APIError, Boltz2TimeoutError)):
                raise
            raise Boltz2ClientError(f"Unexpected error: {e}")

    async def predict_protein_structure(
        self,
        sequence: str,
        polymer_id: str = "A",
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        diffusion_samples: int = 1,
        step_scale: float = 1.638,
        msa_files: Optional[List[Tuple[str, AlignmentFormat]]] = None,
        msa: Optional[Dict[str, Dict[str, AlignmentFileRecord]]] = None,
        **kwargs
    ) -> PredictionResponse:
        """
        Predict protein structure with optional MSA guidance.
        
        Args:
            sequence: Protein sequence
            polymer_id: Polymer identifier
            recycling_steps: Number of recycling steps (1-6)
            sampling_steps: Number of sampling steps (10-1000)
            diffusion_samples: Number of diffusion samples (1-5)
            step_scale: Step scale for diffusion (0.5-5.0)
            msa_files: List of (file_path, format) tuples for MSA files
            msa: Pre-constructed MSA dictionary {database_name: {format: AlignmentFileRecord}}
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response
        """


        # Create a proper PredictionRequest and use the main predict method
        # which handles file saving, progress callbacks, and all other functionality
        
        # Build MSA records for proper integration
        msa_dict = None
        
        # If msa is provided directly, use it
        if msa:
            msa_dict = msa
        # Otherwise, if msa_files are provided, load from files
        elif msa_files:
            msa_dict = {}
            for i, (file_path, format_type) in enumerate(msa_files):
                with open(file_path, "r") as fh:
                    content = fh.read()
                msa_record = AlignmentFileRecord(
                    alignment=content,
                    format=format_type,
                    rank=i
                )
                # Use database name as "default" or "msa_{i}"
                db_name = f"msa_{i}" if len(msa_files) > 1 else "default"
                if db_name not in msa_dict:
                    msa_dict[db_name] = {}
                msa_dict[db_name][format_type] = msa_record
        
        polymer = Polymer(
            id=polymer_id,
            molecule_type="protein",
            sequence=sequence,
            msa=msa_dict
        )
        
        request = PredictionRequest(
            polymers=[polymer],
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            diffusion_samples=diffusion_samples,
            step_scale=step_scale
        )
        
        return await self.predict(request, **kwargs)

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
        msa_files: Optional[List[Tuple[str, AlignmentFormat]]] = None,
        msa: Optional[Dict[str, Dict[str, AlignmentFileRecord]]] = None,
        **kwargs
    ) -> PredictionResponse:
        """
        Predict protein-ligand complex structure with optional MSA guidance.
        
        Args:
            protein_sequence: Protein sequence
            ligand_smiles: SMILES string for ligand (mutually exclusive with ligand_ccd)
            ligand_ccd: CCD code for ligand (mutually exclusive with ligand_smiles)
            protein_id: Protein polymer identifier
            ligand_id: Ligand identifier
            pocket_residues: List of residue indices defining binding pocket
            recycling_steps: Number of recycling steps
            sampling_steps: Number of sampling steps
            predict_affinity: Enable affinity prediction for this ligand
            sampling_steps_affinity: Sampling steps for affinity prediction
            diffusion_samples_affinity: Diffusion samples for affinity prediction
            affinity_mw_correction: Apply molecular weight correction to affinity
            msa_files: List of (file_path, format) tuples for MSA files
            msa: Pre-constructed MSA dictionary {database_name: {format: AlignmentFileRecord}}
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response with structure and optionally affinity predictions
        """
        if not ligand_smiles and not ligand_ccd:
            raise Boltz2ValidationError("Must provide either ligand_smiles or ligand_ccd")
        
        # Build MSA records if provided
        msa_dict = None
        
        # If msa is provided directly, use it
        if msa:
            msa_dict = msa
        # Otherwise, if msa_files are provided, load from files
        elif msa_files:
            msa_dict = {}
            for i, (file_path, format_type) in enumerate(msa_files):
                with open(file_path, "r") as fh:
                    content = fh.read()
                msa_record = AlignmentFileRecord(
                    alignment=content,
                    format=format_type,
                    rank=i
                )
                # Use database name as "default" or "msa_{i}"
                db_name = f"msa_{i}" if len(msa_files) > 1 else "default"
                if db_name not in msa_dict:
                    msa_dict[db_name] = {}
                msa_dict[db_name][format_type] = msa_record
        
        polymer = Polymer(
            id=protein_id,
            molecule_type="protein",
            sequence=protein_sequence,
            msa=msa_dict
        )
        
        ligand = Ligand(
            id=ligand_id,
            smiles=ligand_smiles,
            ccd=ligand_ccd,
            predict_affinity=predict_affinity
        )
        
        constraints = []
        if pocket_residues:
            pocket_constraint = PocketConstraint(
                ligand_id=ligand_id,
                polymer_id=protein_id,
                residue_ids=pocket_residues,
                binder=ligand_id,
                contacts=[]  # Leave empty to avoid server validation issues
            )
            constraints.append(pocket_constraint)
        
        request = PredictionRequest(
            polymers=[polymer],
            ligands=[ligand],
            constraints=constraints if constraints else None,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps
        )
        if sampling_steps_affinity is not None:
            request.sampling_steps_affinity = sampling_steps_affinity
        if diffusion_samples_affinity is not None:
            request.diffusion_samples_affinity = diffusion_samples_affinity
        if affinity_mw_correction is not None:
            request.affinity_mw_correction = affinity_mw_correction
        
        return await self.predict(request, **kwargs)

    async def predict_covalent_complex(
        self,
        protein_sequence: str,
        ligand_ccd: str,  # Only CCD codes supported for covalent bonding
        covalent_bonds: List[Tuple[int, str, str]] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        **kwargs
    ) -> PredictionResponse:
        """
        Predict covalent protein-ligand complex with bond constraints.
        
        Note: Covalent bonding only supports CCD codes for ligands, not SMILES.
        
        Args:
            protein_sequence: Protein sequence
            ligand_ccd: CCD code for ligand (SMILES not supported for covalent bonding)
            covalent_bonds: List of (residue_index, protein_atom, ligand_atom) tuples
            protein_id: Protein polymer identifier
            ligand_id: Ligand identifier
            recycling_steps: Number of recycling steps
            sampling_steps: Number of sampling steps
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response
        """
        if not ligand_ccd:
            raise Boltz2ValidationError("CCD code is required for covalent bonding (SMILES not supported)")
        
        if not covalent_bonds:
            raise Boltz2ValidationError("Must provide at least one covalent bond")
        
        polymer = Polymer(
            id=protein_id,
            molecule_type="protein",
            sequence=protein_sequence
        )
        
        ligand = Ligand(
            id=ligand_id,
            ccd=ligand_ccd  # Only CCD supported for covalent bonding
        )
        
        # Create bond constraints
        constraints = []
        for residue_idx, protein_atom, ligand_atom in covalent_bonds:
            bond_constraint = BondConstraint(
                constraint_type="bond",
                atoms=[
                    Atom(id=protein_id, residue_index=residue_idx, atom_name=protein_atom),
                    Atom(id=ligand_id, residue_index=1, atom_name=ligand_atom)
                ]
            )
            constraints.append(bond_constraint)
        
        request = PredictionRequest(
            polymers=[polymer],
            ligands=[ligand],
            constraints=constraints,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps
        )
        
        return await self.predict(request, **kwargs)

    async def predict_dna_protein_complex(
        self,
        protein_sequences: List[str],
        dna_sequences: List[str],
        protein_ids: Optional[List[str]] = None,
        dna_ids: Optional[List[str]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        concatenate_msas: bool = False,
        **kwargs
    ) -> PredictionResponse:
        """
        Predict DNA-protein complex structure.
        
        Args:
            protein_sequences: List of protein sequences
            dna_sequences: List of DNA sequences
            protein_ids: List of protein identifiers (default: A, B, ...)
            dna_ids: List of DNA identifiers (default: C, D, ...)
            recycling_steps: Number of recycling steps
            sampling_steps: Number of sampling steps
            concatenate_msas: Whether to concatenate MSAs
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response
        """
        if not protein_ids:
            protein_ids = [chr(65 + i) for i in range(len(protein_sequences))]  # A, B, C...
        
        if not dna_ids:
            start_idx = len(protein_sequences)
            dna_ids = [chr(65 + start_idx + i) for i in range(len(dna_sequences))]
        
        polymers = []
        
        # Add proteins
        for seq, pid in zip(protein_sequences, protein_ids):
            polymers.append(Polymer(
                id=pid,
                molecule_type="protein",
                sequence=seq
            ))
        
        # Add DNA
        for seq, did in zip(dna_sequences, dna_ids):
            polymers.append(Polymer(
                id=did,
                molecule_type="dna",
                sequence=seq
            ))
        
        request = PredictionRequest(
            polymers=polymers,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            concatenate_msas=concatenate_msas
        )
        
        return await self.predict(request, **kwargs)

    async def predict_with_advanced_parameters(
        self,
        polymers: List[Polymer],
        ligands: Optional[List[Ligand]] = None,
        constraints: Optional[List[Union[PocketConstraint, BondConstraint]]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        diffusion_samples: int = 1,
        step_scale: float = 1.638,
        without_potentials: bool = False,
        concatenate_msas: bool = False,
        **kwargs
    ) -> PredictionResponse:
        """
        Predict structure with full control over all advanced parameters.
        
        Args:
            polymers: List of polymers (proteins, DNA, RNA)
            ligands: Optional list of ligands
            constraints: Optional list of constraints
            recycling_steps: Number of recycling steps (1-6)
            sampling_steps: Number of sampling steps (10-1000)
            diffusion_samples: Number of diffusion samples (1-5)
            step_scale: Step scale for diffusion sampling (0.5-5.0)
            without_potentials: Whether to run without potentials
            concatenate_msas: Whether to concatenate MSAs
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response
        """
        request = PredictionRequest(
            polymers=polymers,
            ligands=ligands,
            constraints=constraints,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            diffusion_samples=diffusion_samples,
            step_scale=step_scale,
            without_potentials=without_potentials,
            concatenate_msas=concatenate_msas
        )
        
        return await self.predict(request, **kwargs)

    async def predict_from_yaml_config(
        self,
        yaml_config: Union[str, Path, YAMLConfig],
        msa_dir: Optional[Path] = None,
        save_structures: bool = True,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[callable] = None,
        recycling_steps: Optional[int] = None,
        sampling_steps: Optional[int] = None,
        diffusion_samples: Optional[int] = None,
        step_scale: Optional[float] = None,
        without_potentials: Optional[bool] = None,
        concatenate_msas: Optional[bool] = None,
        **kwargs
    ) -> PredictionResponse:
        """
        Predict structure from YAML configuration file (official Boltz format).
        
        This method supports the official Boltz YAML configuration format as used
        in the original Boltz repository examples.
        
        Args:
            yaml_config: YAML configuration (file path, string content, or YAMLConfig object)
            msa_dir: Directory containing MSA files referenced in YAML
            save_structures: Whether to save structures to files
            output_dir: Directory to save structures
            progress_callback: Optional callback for progress updates
            recycling_steps: Override recycling steps parameter
            sampling_steps: Override sampling steps parameter
            diffusion_samples: Override diffusion samples parameter
            step_scale: Override step scale parameter
            without_potentials: Override without potentials parameter
            concatenate_msas: Override concatenate MSAs parameter
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response
            
        Example YAML format:
            version: 1
            sequences:
              - protein:
                  id: A
                  sequence: "MKTVRQERLK..."
                  msa: "protein_A.a3m"  # optional
              - ligand:
                  id: B
                  smiles: "CC(=O)O"
            properties:  # optional
              affinity:
                binder: B
        """
        # Parse YAML config
        if isinstance(yaml_config, YAMLConfig):
            config = yaml_config
        else:
            if isinstance(yaml_config, (str, Path)):
                yaml_path = Path(yaml_config)
                if yaml_path.exists():
                    # Load from file
                    yaml_content = yaml_path.read_text()
                    yaml_data = yaml.safe_load(yaml_content)
                    config_dir = yaml_path.parent
                else:
                    # Treat as YAML string content
                    yaml_data = yaml.safe_load(yaml_config)
                    config_dir = Path.cwd()
            else:
                raise ValueError("yaml_config must be a file path, YAML string, or YAMLConfig object")
            
            config = YAMLConfig(**yaml_data)
        
        # Convert to PredictionRequest
        request = config.to_prediction_request()
        
        # Override parameters if provided
        if recycling_steps is not None:
            request.recycling_steps = recycling_steps
        if sampling_steps is not None:
            request.sampling_steps = sampling_steps
        if diffusion_samples is not None:
            request.diffusion_samples = diffusion_samples
        if step_scale is not None:
            request.step_scale = step_scale
        if without_potentials is not None:
            request.without_potentials = without_potentials
        if concatenate_msas is not None:
            request.concatenate_msas = concatenate_msas
        
        # Handle MSA files
        if msa_dir is None:
            msa_dir = config_dir if 'config_dir' in locals() else Path.cwd()
        
        # Load MSA files for proteins that reference them
        for i, seq in enumerate(config.sequences):
            if seq.protein and seq.protein.msa and seq.protein.msa != "empty":
                msa_path = msa_dir / seq.protein.msa
                if msa_path.exists():
                    msa_content = msa_path.read_text()
                    # Determine format from extension
                    format_map = {
                        '.a3m': 'a3m',
                        '.sto': 'sto',
                        '.fasta': 'fasta',
                        '.csv': 'csv'
                    }
                    format_type = format_map.get(msa_path.suffix.lower(), 'a3m')
                    
                    msa_record = AlignmentFileRecord(
                        alignment=msa_content,
                        format=format_type,
                        rank=0
                    )
                    
                    # Update the corresponding polymer with MSA
                    polymer_idx = sum(1 for s in config.sequences[:i] if s.protein)
                    if polymer_idx < len(request.polymers):
                        request.polymers[polymer_idx].msa = {"default": {format_type: msa_record}}
                else:
                    self.console.print(f"⚠️ MSA file not found: {msa_path}", style="yellow")
        
        return await self.predict(
            request, 
            save_structures=save_structures, 
            output_dir=output_dir, 
            progress_callback=progress_callback,
            **kwargs
        )

    async def predict_from_yaml_file(
        self,
        yaml_file: Union[str, Path],
        **kwargs
    ) -> PredictionResponse:
        """
        Predict structure from YAML configuration file.
        
        Args:
            yaml_file: Path to YAML configuration file
            **kwargs: Additional parameters for predict()
            
        Returns:
            Prediction response
        """
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
        # Set msa_dir to yaml parent directory only if not already provided
        if 'msa_dir' not in kwargs:
            kwargs['msa_dir'] = yaml_path.parent
        
        return await self.predict_from_yaml_config(
            yaml_path,
            **kwargs
        )
    
    def configure_msa_search(
        self,
        msa_endpoint_url: str,
        api_key: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3
    ) -> None:
        """
        Configure MSA Search NIM integration.
        
        Args:
            msa_endpoint_url: MSA Search NIM endpoint URL
                - NVIDIA hosted: "https://health.api.nvidia.com/v1/biology/nvidia/msa-search"
                - Local deployment: "http://localhost:8001"
            api_key: API key for NVIDIA-hosted endpoints
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self._msa_search_client = MSASearchClient(
            endpoint_url=msa_endpoint_url,
            api_key=api_key or self.api_key,
            timeout=timeout,
            max_retries=max_retries
        )
        self._msa_search_integration = MSASearchIntegration(self._msa_search_client)
        
        self.console.print(f"✅ MSA Search configured: {msa_endpoint_url}", style="green")
    
    async def search_msa(
        self,
        sequence: str,
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        output_format: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Union[MSASearchResponse, Path]:
        """
        Search for MSA using GPU-accelerated MSA Search NIM.
        
        Args:
            sequence: Protein sequence to search
            databases: List of databases to search (default: ["all"])
            e_value: E-value threshold for hits
            max_msa_sequences: Maximum sequences in MSA
            output_format: Output format if saving ("a3m", "fasta", "sto")
            save_path: Path to save MSA file
            **kwargs: Additional search parameters
            
        Returns:
            MSASearchResponse if not saving, Path to saved file if save_path provided
        """
        if not self._msa_search_client:
            raise Boltz2ClientError(
                "MSA Search not configured. Call configure_msa_search() first."
            )
        
        if save_path and output_format:
            # Search and save
            return await self._msa_search_integration.search_and_save(
                sequence=sequence,
                output_path=save_path,
                output_format=output_format,
                databases=databases,
                e_value=e_value,
                max_msa_sequences=max_msa_sequences,
                **kwargs
            )
        else:
            # Just search
            return await self._msa_search_client.search(
                sequence=sequence,
                databases=databases,
                e_value=e_value,
                max_msa_sequences=max_msa_sequences,
                **kwargs
            )
    
    async def predict_with_msa_search(
        self,
        sequence: str,
        polymer_id: str = "A",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        diffusion_samples: int = 1,
        step_scale: float = 1.638,
        **kwargs
    ) -> PredictionResponse:
        """
        Perform MSA search and use results for structure prediction in one step.
        
        Args:
            sequence: Protein sequence
            polymer_id: ID for the polymer (default: "A")
            databases: Databases to search for MSA
            e_value: E-value threshold for MSA
            max_msa_sequences: Maximum sequences in MSA
            recycling_steps: Number of recycling steps (1-6)
            sampling_steps: Number of sampling steps (10-1000)
            diffusion_samples: Number of diffusion samples (1-5)
            step_scale: Step scale factor (0.5-5.0)
            **kwargs: Additional parameters
            
        Returns:
            PredictionResponse with structure
        """
        if not self._msa_search_client:
            raise Boltz2ClientError(
                "MSA Search not configured. Call configure_msa_search() first."
            )
        
        # Perform MSA search
        self.console.print(f"🔍 Searching MSA for sequence ({len(sequence)} residues)...", style="blue")
        
        msa_data = await self._msa_search_integration.search_and_prepare_for_boltz(
            sequence=sequence,
            polymer_id=polymer_id,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            **kwargs
        )
        
        # Count sequences in alignment
        alignment_text = msa_data['msa_search']['a3m'].alignment
        seq_count = alignment_text.count('\n>')
        self.console.print(f"✅ MSA search completed with {seq_count} sequences", style="green")
        
        # Create polymer with MSA
        polymer = Polymer(
            id=polymer_id,
            molecule_type="protein",
            sequence=sequence,
            msa=msa_data
        )
        
        # Create request
        request = PredictionRequest(
            polymers=[polymer],
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            diffusion_samples=diffusion_samples,
            step_scale=step_scale
        )
        
        # Predict structure
        return await self.predict(request, **kwargs)
    
    async def batch_msa_search(
        self,
        sequences: Dict[str, str],
        output_dir: Union[str, Path],
        output_format: str = "a3m",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        **kwargs
    ) -> Dict[str, Path]:
        """
        Perform batch MSA search for multiple sequences.
        
        Args:
            sequences: Dict mapping sequence IDs to sequences
            output_dir: Directory to save MSA files
            output_format: Output format ("a3m", "fasta", "sto")
            databases: Databases to search
            e_value: E-value threshold
            max_msa_sequences: Maximum sequences per MSA
            **kwargs: Additional search parameters
            
        Returns:
            Dict mapping sequence IDs to output file paths
        """
        if not self._msa_search_client:
            raise Boltz2ClientError(
                "MSA Search not configured. Call configure_msa_search() first."
            )
        
        return await self._msa_search_integration.batch_search(
            sequences=sequences,
            output_dir=output_dir,
            output_format=output_format,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            **kwargs
        )
    
    async def predict_ligand_with_msa_search(
        self,
        protein_sequence: str,
        ligand_smiles: Optional[str] = None,
        ligand_ccd: Optional[str] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        pocket_residues: Optional[List[int]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        predict_affinity: bool = False,
        sampling_steps_affinity: Optional[int] = None,
        diffusion_samples_affinity: Optional[int] = None,
        affinity_mw_correction: Optional[bool] = None,
        **kwargs
    ) -> PredictionResponse:
        """
        Perform MSA search and predict protein-ligand complex with optional affinity.
        
        This method combines MSA search with protein-ligand complex prediction,
        including optional affinity prediction, in a single streamlined workflow.
        
        Args:
            protein_sequence: Protein sequence
            ligand_smiles: SMILES string for ligand (mutually exclusive with ligand_ccd)
            ligand_ccd: CCD code for ligand (mutually exclusive with ligand_smiles)
            protein_id: Protein polymer identifier
            ligand_id: Ligand identifier
            databases: Databases to search for MSA (default: ["all"])
            e_value: E-value threshold for MSA search
            max_msa_sequences: Maximum sequences in MSA
            pocket_residues: List of residue indices defining binding pocket
            recycling_steps: Number of recycling steps (1-6)
            sampling_steps: Number of sampling steps (10-1000)
            predict_affinity: Enable affinity prediction for this ligand
            sampling_steps_affinity: Sampling steps for affinity prediction
            diffusion_samples_affinity: Diffusion samples for affinity prediction
            affinity_mw_correction: Apply molecular weight correction to affinity
            **kwargs: Additional parameters
            
        Returns:
            PredictionResponse with structure and optionally affinity predictions
            
        Example:
            >>> result = await client.predict_ligand_with_msa_search(
            ...     protein_sequence="MKTVRQERLKS...",
            ...     ligand_smiles="CC(=O)Oc1ccccc1C(=O)O",
            ...     predict_affinity=True,
            ...     sampling_steps_affinity=300
            ... )
            >>> print(f"pIC50: {result.affinities['LIG'].affinity_pic50[0]:.3f}")
        """
        if not self._msa_search_client:
            raise Boltz2ClientError(
                "MSA Search not configured. Call configure_msa_search() first."
            )
        
        if not ligand_smiles and not ligand_ccd:
            raise Boltz2ValidationError("Must provide either ligand_smiles or ligand_ccd")
        
        # Perform MSA search
        self.console.print(f"🔍 Searching MSA for protein ({len(protein_sequence)} residues)...", style="blue")
        
        msa_data = await self._msa_search_integration.search_and_prepare_for_boltz(
            sequence=protein_sequence,
            polymer_id=protein_id,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            **kwargs
        )
        
        # Count sequences in alignment
        alignment_text = list(msa_data.values())[0]['a3m'].alignment
        seq_count = alignment_text.count('\n>')
        self.console.print(f"✅ MSA search completed with {seq_count} sequences", style="green")
        
        # Use the predict_protein_ligand_complex method with MSA
        return await self.predict_protein_ligand_complex(
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
            msa=msa_data,  # Pass the MSA data
            **kwargs
        )
    
    async def get_msa_databases(self) -> Dict[str, Any]:
        """
        Get MSA database configurations.
        
        Returns:
            Dictionary of database configurations
        """
        if not self._msa_search_client:
            raise Boltz2ClientError(
                "MSA Search not configured. Call configure_msa_search() first."
            )
        
        return await self._msa_search_client.get_databases()
    
    async def get_msa_databases_status(self) -> Dict[str, Any]:
        """
        Get MSA databases status.
        
        Returns:
            Dictionary of database status information
        """
        if not self._msa_search_client:
            raise Boltz2ClientError(
                "MSA Search not configured. Call configure_msa_search() first."
            )
        
        return await self._msa_search_client.get_databases_status()

    def create_yaml_config(
        self,
        proteins: Optional[List[Tuple[str, str, Optional[str]]]] = None,
        ligands: Optional[List[Tuple[str, str]]] = None,
        predict_affinity: bool = False,
        binder_id: Optional[str] = None
    ) -> YAMLConfig:
        """
        Create a YAML configuration object programmatically.
        
        Args:
            proteins: List of (id, sequence, msa_file) tuples
            ligands: List of (id, smiles) tuples  
            predict_affinity: Whether to predict binding affinity
            binder_id: ID of the binding molecule for affinity prediction
            
        Returns:
            YAMLConfig object
            
        Example:
            config = client.create_yaml_config(
                proteins=[("A", "MKTVRQERLK...", None)],
                ligands=[("B", "CC(=O)O")],
                predict_affinity=True,
                binder_id="B"
            )
        """
        from .models import YAMLProtein, YAMLLigand, YAMLSequence, YAMLAffinity, YAMLProperties
        
        sequences = []
        
        # Add proteins
        if proteins:
            for protein_id, sequence, msa_file in proteins:
                protein = YAMLProtein(
                    id=protein_id,
                    sequence=sequence,
                    msa=msa_file
                )
                sequences.append(YAMLSequence(protein=protein))
        
        # Add ligands
        if ligands:
            for ligand_id, smiles in ligands:
                ligand = YAMLLigand(
                    id=ligand_id,
                    smiles=smiles
                )
                sequences.append(YAMLSequence(ligand=ligand))
        
        # Add properties
        properties = None
        if predict_affinity:
            if not binder_id:
                raise ValueError("binder_id must be specified when predict_affinity=True")
            properties = YAMLProperties(
                affinity=YAMLAffinity(binder=binder_id)
            )
        
        return YAMLConfig(
            version=1,
            sequences=sequences,
            properties=properties
        )

    def save_yaml_config(
        self,
        config: YAMLConfig,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Save YAML configuration to file.
        
        Args:
            config: YAMLConfig object
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        
        # Convert to dict and save as YAML
        config_dict = config.dict(exclude_none=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        return output_path

    async def _save_structures(
        self,
        response: PredictionResponse,
        output_dir: Path,
        progress_callback: Optional[callable] = None
    ) -> List[Path]:
        """Save prediction structures to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        for i, structure in enumerate(response.structures):
            # Save structure file
            if structure.format.lower() == 'mmcif':
                structure_file = output_dir / f"structure_{i}.cif"
            else:
                structure_file = output_dir / f"structure_{i}.pdb"
            
            structure_file.write_text(structure.structure)
            saved_files.append(structure_file)
            
            if progress_callback:
                progress_callback(f"Saved structure to {structure_file}")
        
        # Save metadata
        metadata = {
            "confidence_scores": response.confidence_scores,
            "metrics": response.metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        metadata_file = output_dir / "prediction_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        saved_files.append(metadata_file)
        
        # Save affinities if present
        if getattr(response, "affinities", None):
            affinities_file = output_dir / "affinities.json"
            try:
                affinities_file.write_text(json.dumps(response.affinities, default=lambda o: o.dict() if hasattr(o, 'dict') else o, indent=2))
                saved_files.append(affinities_file)
                if progress_callback:
                    progress_callback(f"Saved affinities to {affinities_file}")
            except Exception:
                # Best-effort write; do not fail the whole save
                pass
        
        if progress_callback:
            progress_callback(f"Saved metadata to {metadata_file}")
        
        return saved_files


class Boltz2SyncClient:
    """
    Synchronous wrapper for the Boltz-2 client.
    
    Provides the same functionality as Boltz2Client but with synchronous methods.
    Supports both local deployments and NVIDIA hosted endpoints.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        endpoint_type: str = EndpointType.LOCAL,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        poll_seconds: int = 10,
        console: Optional[Console] = None
    ):
        """Initialize the synchronous client."""
        self._async_client = Boltz2Client(
            base_url=base_url,
            api_key=api_key,
            endpoint_type=endpoint_type,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            poll_seconds=poll_seconds,
            console=console
        )
    
    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._async_client.base_url
    
    @property
    def timeout(self) -> float:
        """Get the timeout value."""
        return self._async_client.timeout
    
    def health_check(self) -> HealthStatus:
        """Check the health status of the Boltz-2 service."""
        return asyncio.run(self._async_client.health_check())
    
    def get_service_metadata(self) -> ServiceMetadata:
        """Get service metadata and model information."""
        return asyncio.run(self._async_client.get_service_metadata())
    
    def predict(self, request: PredictionRequest, **kwargs) -> PredictionResponse:
        """Make a structure prediction request."""
        return asyncio.run(self._async_client.predict(request, **kwargs))
    
    def predict_protein_structure(self, **kwargs) -> PredictionResponse:
        """Predict protein structure."""
        return asyncio.run(self._async_client.predict_protein_structure(**kwargs))
    
    def predict_protein_ligand_complex(self, **kwargs) -> PredictionResponse:
        """Predict protein-ligand complex structure."""
        return asyncio.run(self._async_client.predict_protein_ligand_complex(**kwargs))
    
    def predict_covalent_complex(self, **kwargs) -> PredictionResponse:
        """Predict covalent protein-ligand complex."""
        return asyncio.run(self._async_client.predict_covalent_complex(**kwargs))
    
    def predict_dna_protein_complex(self, **kwargs) -> PredictionResponse:
        """Predict DNA-protein complex structure."""
        return asyncio.run(self._async_client.predict_dna_protein_complex(**kwargs))
    
    def predict_with_advanced_parameters(self, **kwargs) -> PredictionResponse:
        """Make prediction with full parameter control."""
        return asyncio.run(self._async_client.predict_with_advanced_parameters(**kwargs))
    
    def configure_msa_search(
        self,
        msa_endpoint_url: str,
        api_key: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3
    ) -> None:
        """Configure MSA Search NIM integration."""
        return self._async_client.configure_msa_search(
            msa_endpoint_url=msa_endpoint_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )
    
    def search_msa(
        self,
        sequence: str,
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        output_format: Optional[str] = None,
        save_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Union[MSASearchResponse, Path]:
        """Search for MSA using GPU-accelerated MSA Search NIM."""
        return asyncio.run(self._async_client.search_msa(
            sequence=sequence,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            output_format=output_format,
            save_path=save_path,
            **kwargs
        ))
    
    def predict_with_msa_search(
        self,
        sequence: str,
        polymer_id: str = "A",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        diffusion_samples: int = 1,
        step_scale: float = 1.638,
        **kwargs
    ) -> PredictionResponse:
        """Perform MSA search and use results for structure prediction."""
        return asyncio.run(self._async_client.predict_with_msa_search(
            sequence=sequence,
            polymer_id=polymer_id,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            diffusion_samples=diffusion_samples,
            step_scale=step_scale,
            **kwargs
        ))
    
    def batch_msa_search(
        self,
        sequences: Dict[str, str],
        output_dir: Union[str, Path],
        output_format: str = "a3m",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        **kwargs
    ) -> Dict[str, Path]:
        """Perform batch MSA search for multiple sequences."""
        return asyncio.run(self._async_client.batch_msa_search(
            sequences=sequences,
            output_dir=output_dir,
            output_format=output_format,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            **kwargs
        ))
    
    def predict_ligand_with_msa_search(
        self,
        protein_sequence: str,
        ligand_smiles: Optional[str] = None,
        ligand_ccd: Optional[str] = None,
        protein_id: str = "A",
        ligand_id: str = "LIG",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        pocket_residues: Optional[List[int]] = None,
        recycling_steps: int = 3,
        sampling_steps: int = 50,
        predict_affinity: bool = False,
        sampling_steps_affinity: Optional[int] = None,
        diffusion_samples_affinity: Optional[int] = None,
        affinity_mw_correction: Optional[bool] = None,
        **kwargs
    ) -> PredictionResponse:
        """Perform MSA search and predict protein-ligand complex with optional affinity."""
        return asyncio.run(self._async_client.predict_ligand_with_msa_search(
            protein_sequence=protein_sequence,
            ligand_smiles=ligand_smiles,
            ligand_ccd=ligand_ccd,
            protein_id=protein_id,
            ligand_id=ligand_id,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            pocket_residues=pocket_residues,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            predict_affinity=predict_affinity,
            sampling_steps_affinity=sampling_steps_affinity,
            diffusion_samples_affinity=diffusion_samples_affinity,
            affinity_mw_correction=affinity_mw_correction,
            **kwargs
        ))
    
    def get_msa_databases(self) -> Dict[str, Any]:
        """Get MSA database configurations."""
        return asyncio.run(self._async_client.get_msa_databases())
    
    def get_msa_databases_status(self) -> Dict[str, Any]:
        """Get MSA databases status."""
        return asyncio.run(self._async_client.get_msa_databases_status())


# Convenience functions for quick predictions
async def predict_protein(
    sequence: str,
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    endpoint_type: str = EndpointType.LOCAL,
    **kwargs
) -> PredictionResponse:
    """Quick protein structure prediction."""
    client = Boltz2Client(
        base_url=base_url, 
        api_key=api_key, 
        endpoint_type=endpoint_type
    )
    return await client.predict_protein_structure(sequence=sequence, **kwargs)


async def predict_protein_ligand(
    protein_sequence: str,
    ligand_smiles: str,
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    endpoint_type: str = EndpointType.LOCAL,
    **kwargs
) -> PredictionResponse:
    """Quick protein-ligand complex prediction."""
    client = Boltz2Client(
        base_url=base_url, 
        api_key=api_key, 
        endpoint_type=endpoint_type
    )
    return await client.predict_protein_ligand_complex(
        protein_sequence=protein_sequence,
        ligand_smiles=ligand_smiles,
        **kwargs
    )


async def predict_covalent(
    protein_sequence: str,
    ligand_ccd: str,
    covalent_bonds: List[Tuple[int, str, str]],
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    endpoint_type: str = EndpointType.LOCAL,
    **kwargs
) -> PredictionResponse:
    """Quick covalent complex prediction."""
    client = Boltz2Client(
        base_url=base_url, 
        api_key=api_key, 
        endpoint_type=endpoint_type
    )
    return await client.predict_covalent_complex(
        protein_sequence=protein_sequence,
        ligand_ccd=ligand_ccd,
        covalent_bonds=covalent_bonds,
        **kwargs
    ) 