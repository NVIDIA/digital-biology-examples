# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
MSA Search NIM Client for Boltz-2

Provides integration with NVIDIA's GPU-accelerated MSA Search NIM (v2.3.0+)
for monomer, paired (multimer), and structural-template searches.

Reference: https://docs.nvidia.com/nim/bionemo/msa-search/2.3.0/api-reference.html

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
"""

import asyncio
import warnings
import aiohttp
import os
from typing import Dict, List, Optional, Union, Literal, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


# ── Monomer search models ────────────────────────────────────────────────────


class MSASearchRequest(BaseModel):
    """Request model for monomer MSA Search NIM API."""

    sequence: str = Field(..., description="Query protein sequence", max_length=4096)
    databases: Optional[List[str]] = Field(
        default=["all"],
        description="Database names to search (case-insensitive). Default searches all.",
    )
    e_value: Optional[float] = Field(
        default=0.0001,
        description="E-value threshold for filtering hits",
        ge=0.0,
        le=1.0,
    )
    iterations: Optional[int] = Field(
        default=1,
        description="MSA iterations (ignored for colabfold search_type which uses 3)",
        ge=1,
        le=6,
    )
    max_msa_sequences: Optional[int] = Field(
        default=500,
        description="Max sequences per database (server default NIM_GLOBAL_MAX_MSA_DEPTH=500)",
        ge=1,
    )
    output_alignment_formats: Optional[List[str]] = Field(
        default=["a3m"],
        description='Output MSA formats: "a3m" and/or "fasta"',
    )
    search_type: Optional[Literal["colabfold", "alphafold2"]] = Field(
        default="colabfold",
        description="Search algorithm",
    )

    @field_validator("sequence")
    @classmethod
    def validate_sequence(cls, v):
        valid_chars = set("ACDEFGHIKLMNPQRSTVWYX")
        sequence = v.upper().strip()
        if not sequence:
            raise ValueError("Sequence cannot be empty")
        invalid_chars = set(sequence) - valid_chars
        if invalid_chars:
            raise ValueError(f"Invalid characters in sequence: {invalid_chars}")
        return sequence


# ── Paired search models (v2.1.0+) ──────────────────────────────────────────


class PairedMSASearchRequest(BaseModel):
    """Request model for the paired (multimer) MSA endpoint."""

    sequences: Union[List[str], Dict[str, str]] = Field(
        ..., description="Protein sequences (one per chain). List or {chain_id: seq}."
    )
    databases: Optional[List[str]] = Field(
        default=["all"],
        description="Databases with taxonomy info for species-based pairing",
    )
    e_value: Optional[float] = Field(default=0.0001, ge=0.0, le=1.0)
    max_msa_sequences: Optional[int] = Field(default=500, ge=1)
    pairing_strategy: Optional[Literal["greedy", "complete"]] = Field(
        default="greedy",
        description="'greedy' maximises rows; 'complete' requires all chains per species",
    )
    unpack: Optional[bool] = Field(
        default=True,
        description="True → per-chain output; False → raw concatenated output",
    )


class PairedMSASearchResponse(BaseModel):
    """Response from the paired MSA search endpoint."""

    alignments_by_chain: Dict[str, Dict[str, Dict[str, "AlignmentFileRecord"]]] = Field(
        ..., description="Paired MSA keyed by chain_id → database → format"
    )
    metrics: Optional[Dict[str, Any]] = None


# ── Structural template search models (v2.2.0+) ─────────────────────────────


class StructuralTemplateRequest(BaseModel):
    """Request model for structural template search endpoint."""

    sequence: str = Field(..., max_length=4096)
    structural_template_databases: Optional[List[str]] = Field(
        default=["pdb70_220313"],
        description="PDB databases to search for structural templates",
    )
    msa_databases: Optional[List[str]] = Field(
        default=["all"],
        description="Databases for MSA generation (first is used for profile)",
    )
    e_value: Optional[float] = Field(default=0.0001, ge=0.0, le=1.0)
    max_structures: Optional[int] = Field(
        default=20, description="Max PDB structures to return"
    )
    max_msa_sequences: Optional[int] = Field(default=500, ge=1)


class SearchHitRecord(BaseModel):
    hits: str = Field(..., description="Template hits in M8 (BLAST tabular) format")
    format: str = Field(default="m8")


class StructuralTemplate(BaseModel):
    structure: str = Field(..., description="mmCIF file content")
    format: str = Field(default="mmcif")


class StructuralTemplateResponse(BaseModel):
    """Response from the structural template search endpoint."""

    alignments: Dict[str, Dict[str, "AlignmentFileRecord"]] = Field(
        ..., description="MSA alignments [database][format]"
    )
    search_hits: Dict[str, Dict[str, SearchHitRecord]] = Field(
        ..., description="Template hits [database][format]"
    )
    structures: Dict[str, StructuralTemplate] = Field(
        ..., description="Retrieved PDB structures by PDB ID"
    )
    metrics: Optional[Dict[str, Any]] = None


# ── Shared models ────────────────────────────────────────────────────────────


class AlignmentFileRecord(BaseModel):
    """A single alignment file record returned by the MSA NIM."""
    alignment: str = Field(..., description="MSA content")
    format: str = Field(..., description='Format identifier ("a3m" or "fasta")')


class MSASearchResponse(BaseModel):
    """Response from the monomer MSA search endpoint."""

    alignments: Dict[str, Dict[str, AlignmentFileRecord]] = Field(
        ..., description="Alignments as nested dictionary [database][format]"
    )
    metrics: Optional[Dict[str, Any]] = Field(
        None, description="Search metrics / debugging info"
    )


# Rebuild models to resolve forward references
PairedMSASearchResponse.model_rebuild()
StructuralTemplateResponse.model_rebuild()
    

class MSASearchClient:
    """Client for NVIDIA MSA Search NIM (v2.3.0+).

    Supports monomer, paired (multimer), and structural-template endpoints.
    """

    # Endpoint paths
    _MONOMER_PATH = "/biology/colabfold/msa-search/predict"
    _PAIRED_PATH = "/biology/colabfold/msa-search/paired/predict"
    _TEMPLATE_PATH = "/biology/colabfold/msa-search/structure-templates/predict"
    _DB_CONFIG_PATH = "/biology/colabfold/msa-search/config/msa-database-configs"
    _METADATA_PATH = "/v1/metadata"
    _HEALTH_PATH = "/v1/health/ready"

    def __init__(
        self,
        endpoint_url: str,
        api_key: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
    ):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries

        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    # ── helpers ───────────────────────────────────────────────────────────

    async def _post(self, path: str, payload: dict) -> dict:
        """POST with retries + exponential backoff."""
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(
                        f"{self.endpoint_url}{path}",
                        headers=self.headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        error_text = await resp.text()
                        if attempt == self.max_retries - 1:
                            raise Exception(
                                f"MSA Search failed: {resp.status} - {error_text}"
                            )
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        raise Exception(
                            f"MSA Search timed out after {self.timeout}s"
                        )
                except Exception:
                    if attempt == self.max_retries - 1:
                        raise
                logger.warning("MSA Search attempt %d failed, retrying…", attempt + 1)
                await asyncio.sleep(2**attempt)

    async def _get(self, path: str, timeout: int = 30) -> Any:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.endpoint_url}{path}",
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                error_text = await resp.text()
                raise Exception(f"GET {path} failed: {resp.status} - {error_text}")

    # ── monomer search ────────────────────────────────────────────────────

    async def search(
        self,
        sequence: str,
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        iterations: int = 1,
        output_alignment_formats: Optional[List[str]] = None,
        search_type: str = "colabfold",
        **kwargs,
    ) -> MSASearchResponse:
        """Monomer MSA search against ``/biology/colabfold/msa-search/predict``."""
        request = MSASearchRequest(
            sequence=sequence,
            databases=databases or ["all"],
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            iterations=iterations,
            output_alignment_formats=output_alignment_formats or ["a3m"],
            search_type=search_type,
        )
        payload = request.model_dump(exclude_none=True)
        payload.update(kwargs)
        data = await self._post(self._MONOMER_PATH, payload)
        return MSASearchResponse(**data)

    # ── paired search (v2.1.0+) ───────────────────────────────────────────

    async def paired_search(
        self,
        sequences: Union[List[str], Dict[str, str]],
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        pairing_strategy: Literal["greedy", "complete"] = "greedy",
        unpack: bool = True,
        **kwargs,
    ) -> PairedMSASearchResponse:
        """Paired MSA search for multimers.

        Endpoint: ``/biology/colabfold/msa-search/paired/predict``

        Args:
            sequences: Protein sequences (list or {chain_id: seq}).
            pairing_strategy: "greedy" (max rows) or "complete" (all chains).
            unpack: True returns per-chain output; False returns raw combined.
        """
        request = PairedMSASearchRequest(
            sequences=sequences,
            databases=databases or ["all"],
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            pairing_strategy=pairing_strategy,
            unpack=unpack,
        )
        payload = request.model_dump(exclude_none=True)
        payload.update(kwargs)
        data = await self._post(self._PAIRED_PATH, payload)
        return PairedMSASearchResponse(**data)

    # ── structural template search (v2.2.0+) ─────────────────────────────

    async def template_search(
        self,
        sequence: str,
        structural_template_databases: Optional[List[str]] = None,
        msa_databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_structures: int = 20,
        max_msa_sequences: int = 500,
        **kwargs,
    ) -> StructuralTemplateResponse:
        """Structural template search for finding homologous PDB structures.

        Endpoint: ``/biology/colabfold/msa-search/structure-templates/predict``
        """
        request = StructuralTemplateRequest(
            sequence=sequence,
            structural_template_databases=structural_template_databases or ["pdb70_220313"],
            msa_databases=msa_databases or ["all"],
            e_value=e_value,
            max_structures=max_structures,
            max_msa_sequences=max_msa_sequences,
        )
        payload = request.model_dump(exclude_none=True)
        payload.update(kwargs)
        data = await self._post(self._TEMPLATE_PATH, payload)
        return StructuralTemplateResponse(**data)

    # ── metadata / config ─────────────────────────────────────────────────

    async def get_metadata(self) -> Dict[str, Any]:
        """Get NIM metadata from ``/v1/metadata`` (preferred over get_databases)."""
        return await self._get(self._METADATA_PATH)

    async def get_databases(self) -> Dict[str, Any]:
        """Get database configurations (deprecated in MSA NIM v2.2.0+).

        Prefer :meth:`get_metadata` which uses ``/v1/metadata``.
        """
        warnings.warn(
            "get_databases() uses the deprecated /config/msa-database-configs "
            "endpoint. Use get_metadata() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self._get(self._DB_CONFIG_PATH)

    async def health_check(self) -> bool:
        """Return True if the MSA NIM is ready."""
        try:
            await self._get(self._HEALTH_PATH, timeout=10)
            return True
        except Exception:
            return False


class MSAFormatConverter:
    """Utilities for converting MSA search results to various formats."""
    
    @staticmethod
    def extract_alignment(
        response: MSASearchResponse,
        format: str = "a3m"
    ) -> Optional[str]:
        """Extract alignment content from an MSA search response.

        Args:
            response: MSA search response (monomer or template).
            format: Requested format key (``"a3m"`` or ``"fasta"``).

        Returns:
            Alignment content string, or the first available format
            if the requested one is absent.  ``None`` only when there
            are no alignments at all.
        """
        # Search through all databases for the requested format
        for db_name, formats in response.alignments.items():
            if format in formats:
                return formats[format].alignment
        
        # If exact format not found, try to get any available format
        for db_name, formats in response.alignments.items():
            if formats:
                # Get first available format
                first_format = next(iter(formats))
                return formats[first_format].alignment
        
        return None
    
    @staticmethod
    def get_all_alignments(response: MSASearchResponse) -> Dict[str, Dict[str, str]]:
        """
        Get all alignments from the response.
        
        Args:
            response: MSA search response
            
        Returns:
            Dictionary mapping database -> format -> alignment content
        """
        result = {}
        for db_name, formats in response.alignments.items():
            result[db_name] = {}
            for fmt, record in formats.items():
                result[db_name][fmt] = record.alignment
        return result


class MSASearchIntegration:
    """Integration utilities for MSA Search with Boltz-2 client."""
    
    def __init__(self, msa_search_client: MSASearchClient):
        """
        Initialize MSA Search integration.
        
        Args:
            msa_search_client: Configured MSA Search client
        """
        self.client = msa_search_client
    
    async def search_and_save(
        self,
        sequence: str,
        output_path: Union[str, Path],
        output_format: Literal["a3m", "fasta"] = "a3m",
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        **kwargs
    ) -> Path:
        """
        Perform MSA search and save results to file.
        
        Args:
            sequence: Query protein sequence
            output_path: Path to save MSA file
            output_format: Output format (a3m, fasta, sto)
            databases: Databases to search
            e_value: E-value threshold
            max_msa_sequences: Maximum sequences
            **kwargs: Additional search parameters
            
        Returns:
            Path to saved file
        """
        # Perform search with requested output format
        response = await self.client.search(
            sequence=sequence,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            output_alignment_formats=[output_format],
            **kwargs
        )
        
        # Extract the alignment content
        content = MSAFormatConverter.extract_alignment(response, output_format)
        
        if not content:
            raise ValueError(f"No alignment found in format: {output_format}")
        
        # Save to file
        output_path = Path(output_path)
        output_path.write_text(content)
        
        # Count sequences in alignment
        seq_count = content.count('\n>')
        logger.info(f"Saved MSA with {seq_count} sequences to {output_path}")
        
        return output_path
    
    async def search_and_prepare_for_boltz(
        self,
        sequence: str,
        polymer_id: str,
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        **kwargs
    ) -> Dict[str, Dict[str, 'AlignmentFileRecord']]:
        """
        Perform MSA search and prepare results in Boltz-2 format.
        
        Args:
            sequence: Query protein sequence
            polymer_id: Polymer ID for Boltz-2
            databases: Databases to search
            e_value: E-value threshold
            max_msa_sequences: Maximum sequences
            **kwargs: Additional search parameters
            
        Returns:
            MSA data in Boltz-2 format (nested dict structure)
        """
        from .models import AlignmentFileRecord as Boltz2AlignmentFileRecord
        
        # Perform search
        response = await self.client.search(
            sequence=sequence,
            databases=databases,
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            output_alignment_formats=["a3m"],
            **kwargs
        )
        
        # Extract A3M content
        a3m_content = MSAFormatConverter.extract_alignment(response, "a3m")
        
        if not a3m_content:
            raise ValueError("No A3M alignment found in MSA search response")
        
        # Create Boltz2 AlignmentFileRecord
        msa_record = Boltz2AlignmentFileRecord(
            alignment=a3m_content,
            format="a3m",
            rank=0
        )
        
        # Return in Boltz-2 format
        return {"msa_search": {"a3m": msa_record}}
    
    async def batch_search(
        self,
        sequences: Dict[str, str],
        output_dir: Union[str, Path],
        output_format: Literal["a3m", "fasta"] = "a3m",
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
            output_format: Output format for all files
            databases: Databases to search
            e_value: E-value threshold
            max_msa_sequences: Maximum sequences per MSA
            **kwargs: Additional search parameters
            
        Returns:
            Dict mapping sequence IDs to output file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        # Process sequences concurrently with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent searches
        
        async def search_single(seq_id: str, sequence: str):
            async with semaphore:
                try:
                    output_path = output_dir / f"{seq_id}_msa.{output_format}"
                    path = await self.search_and_save(
                        sequence=sequence,
                        output_path=output_path,
                        output_format=output_format,
                        databases=databases,
                        e_value=e_value,
                        max_msa_sequences=max_msa_sequences,
                        **kwargs
                    )
                    return seq_id, path
                except Exception as e:
                    logger.error(f"Failed to search MSA for {seq_id}: {e}")
                    return seq_id, None
        
        # Run all searches
        tasks = [search_single(seq_id, seq) for seq_id, seq in sequences.items()]
        search_results = await asyncio.gather(*tasks)
        
        # Collect results
        for seq_id, path in search_results:
            if path:
                results[seq_id] = path
        
        logger.info(f"Completed batch MSA search for {len(results)}/{len(sequences)} sequences")
        
        return results
