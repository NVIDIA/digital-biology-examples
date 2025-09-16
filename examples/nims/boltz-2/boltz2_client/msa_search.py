"""
MSA Search NIM Client for Boltz-2

This module provides integration with NVIDIA's GPU-accelerated MSA Search NIM
to generate Multiple Sequence Alignments for enhanced protein structure predictions.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import asyncio
import aiohttp
import os
from typing import Dict, List, Optional, Union, Literal, Tuple, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MSASearchRequest(BaseModel):
    """Request model for MSA Search NIM API."""
    
    sequence: str = Field(..., description="Query protein sequence", max_length=4096)
    databases: Optional[List[str]] = Field(
        default=["all"],
        description="List of database names to search against",
        max_items=3
    )
    e_value: Optional[float] = Field(
        default=0.0001,
        description="E-value for filtering hits when building MSA",
        ge=0.0,
        le=1.0
    )
    iterations: Optional[int] = Field(
        default=1,
        description="Number of MSA iterations to perform",
        ge=1,
        le=6
    )
    max_msa_sequences: Optional[int] = Field(
        default=500,
        description="Maximum sequences taken from MSA",
        ge=1,
        le=10001
    )
    output_alignment_formats: Optional[List[str]] = Field(
        default=["a3m"],
        description="Output format of the MSA"
    )
    override_database_order: Optional[bool] = Field(
        default=False,
        description="Override database rank order"
    )
    search_type: Optional[Literal["colabfold", "alphafold2"]] = Field(
        default="colabfold",
        description="Which type of MSA Search to run"
    )
    
    @validator('sequence')
    def validate_sequence(cls, v):
        """Validate protein sequence contains only valid amino acids."""
        valid_chars = set("ACDEFGHIKLMNPQRSTVWYX")
        sequence = v.upper().strip()
        
        if not sequence:
            raise ValueError("Sequence cannot be empty")
            
        invalid_chars = set(sequence) - valid_chars
        if invalid_chars:
            raise ValueError(f"Invalid amino acid characters in sequence: {invalid_chars}")
            
        return sequence


class AlignmentFileRecord(BaseModel):
    """Represents a single alignment file record."""
    alignment: str = Field(..., description="The contents of a single MSA")
    format: str = Field(..., description="The format of the alignment (a3m, fasta, or sto)")


class MSASearchResponse(BaseModel):
    """Response model from MSA Search NIM API."""
    
    alignments: Dict[str, Dict[str, AlignmentFileRecord]] = Field(
        ..., 
        description="Alignments as nested dictionary [database][format]"
    )
    templates: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        description="Template hits if requested"
    )
    metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Metrics for the MSA search"
    )
    

class MSASearchClient:
    """Client for interacting with MSA Search NIM endpoints."""
    
    def __init__(
        self,
        endpoint_url: str,
        api_key: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3
    ):
        """
        Initialize MSA Search client.
        
        Args:
            endpoint_url: MSA Search NIM endpoint URL
            api_key: Optional API key for NVIDIA-hosted endpoints
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.endpoint_url = endpoint_url.rstrip('/')
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Set up headers
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    async def search(
        self,
        sequence: str,
        databases: Optional[List[str]] = None,
        e_value: float = 0.0001,
        max_msa_sequences: int = 500,
        iterations: int = 1,
        output_alignment_formats: Optional[List[str]] = None,
        search_type: str = "colabfold",
        **kwargs
    ) -> MSASearchResponse:
        """
        Perform MSA search for a protein sequence.
        
        Args:
            sequence: Query protein sequence
            databases: List of databases to search (default: ["all"])
            e_value: E-value for filtering hits
            max_msa_sequences: Maximum sequences taken from MSA
            iterations: Number of MSA iterations
            output_alignment_formats: Output formats (default: ["a3m"])
            search_type: Search type ("colabfold" or "alphafold2")
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            MSASearchResponse with search results
        """
        # Create request
        request = MSASearchRequest(
            sequence=sequence,
            databases=databases or ["all"],
            e_value=e_value,
            max_msa_sequences=max_msa_sequences,
            iterations=iterations,
            output_alignment_formats=output_alignment_formats or ["a3m"],
            search_type=search_type
        )
        
        # Prepare request payload
        payload = request.dict(exclude_none=True)
        payload.update(kwargs)  # Add any additional parameters
        
        # Make API request with retries
        async with aiohttp.ClientSession() as session:
            for attempt in range(self.max_retries):
                try:
                    async with session.post(
                        f"{self.endpoint_url}/biology/colabfold/msa-search/predict",
                        headers=self.headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return MSASearchResponse(**data)
                        else:
                            error_text = await response.text()
                            if attempt == self.max_retries - 1:
                                raise Exception(f"MSA Search failed: {response.status} - {error_text}")
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        raise Exception(f"MSA Search timed out after {self.timeout} seconds")
                    await asyncio.sleep(2 ** attempt)
                    
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise
                    logger.warning(f"MSA Search attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(2 ** attempt)
    
    async def get_databases(self) -> Dict[str, Any]:
        """
        Get MSA database configurations from the MSA Search NIM.
        
        Returns:
            Dictionary of database configurations
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.endpoint_url}/biology/colabfold/msa-search/config/msa-database-configs",
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get database configs: {response.status} - {error_text}")
    
    async def get_databases_status(self) -> Dict[str, Any]:
        """
        Get status of MSA databases.
        
        Returns:
            Dictionary of database status information
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.endpoint_url}/biology/colabfold/msa-search/databases/status",
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get database status: {response.status} - {error_text}")
    
    async def health_check(self) -> bool:
        """
        Check if the MSA Search NIM endpoint is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint_url}/v1/health/ready",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except:
            return False


class MSAFormatConverter:
    """Utilities for converting MSA search results to various formats."""
    
    @staticmethod
    def extract_alignment(
        response: MSASearchResponse,
        format: str = "a3m"
    ) -> Optional[str]:
        """
        Extract alignment content from MSA search response.
        
        Args:
            response: MSA search response
            format: Format to extract (a3m, fasta, sto)
            
        Returns:
            Alignment content string or None if not found
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
        output_format: Literal["a3m", "fasta", "sto"] = "a3m",
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
        output_format: Literal["a3m", "fasta", "sto"] = "a3m",
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
