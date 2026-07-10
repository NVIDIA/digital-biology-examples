# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Boltz-2 Python Client

A comprehensive Python client for NVIDIA's Boltz-2 molecular structure prediction service.
Supports local, NVIDIA hosted, and AWS SageMaker endpoints with full API coverage.

Example:
    >>> from boltz2_client import Boltz2Client, EndpointType
    >>> 
    >>> # Local endpoint
    >>> client = Boltz2Client("http://localhost:8000")
    >>> 
    >>> # NVIDIA hosted endpoint
    >>> client = Boltz2Client(
    ...     base_url="https://health.api.nvidia.com",
    ...     api_key="your_api_key",
    ...     endpoint_type=EndpointType.NVIDIA_HOSTED
    ... )
    >>> 
    >>> # Simple protein prediction
    >>> result = await client.predict_protein_structure("MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG")
    >>> print(f"Confidence: {result.confidence_scores[0]:.3f}")
"""

__version__ = "0.5.2.post1"
__author__ = "NVIDIA Corporation"
__email__ = "bionemo-support@nvidia.com"

from .client import Boltz2Client, Boltz2SyncClient, EndpointType
from .models import (
    PredictionRequest,
    PredictionResponse,
    Polymer,
    Ligand,
    Contact,
    PocketConstraint,
    BondConstraint,
    Atom,
    AlignmentFileRecord,
    AlignmentFormat,
    HealthStatus,
    ServiceMetadata,
    StructuralTemplate,
    Modification,
    AffinityPrediction,
)
from .exceptions import (
    Boltz2Error,
    Boltz2ClientError,
    Boltz2APIError,
    Boltz2TimeoutError,
    Boltz2ConnectionError,
    Boltz2ValidationError,
)
from .virtual_screening import (
    VirtualScreening,
    CompoundLibrary,
    VirtualScreeningResult,
    quick_screen,
)
from .multi_endpoint_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
)
from .msa_search import (
    MSASearchClient,
    MSASearchIntegration,
    MSASearchRequest,
    MSASearchResponse,
    MSAFormatConverter,
    PairedMSASearchRequest,
    PairedMSASearchResponse,
    StructuralTemplateRequest,
    StructuralTemplateResponse,
)
from .a3m import (
    A3MToCSVConverter,
    A3MParser,
    A3MMSA,
    A3MSequence,
    convert_a3m_to_multimer_csv,
    create_multimer_msa_request,
    create_paired_msa_per_chain,
    ConversionResult,
    GreedyPairingStrategy,
    CompletePairingStrategy,
    TaxonomyPairingStrategy,
    SpeciesMapper,
    SPECIES_TO_TAXID,
)
from .utils import (
    save_prediction_outputs,
    get_prediction_summary,
    save_pae_matrix,
    save_pde_matrix,
    get_pae_summary,
    convert_cif_to_pdb,
    convert_pdb_to_cif,
)

__all__ = [
    # Core client classes
    "Boltz2Client",
    "Boltz2SyncClient",
    "EndpointType",
    
    # Data models
    "PredictionRequest",
    "PredictionResponse", 
    "Polymer",
    "Ligand",
    "Contact",
    "PocketConstraint",
    "BondConstraint",
    "Atom",
    "AlignmentFileRecord",
    "AlignmentFormat",
    "HealthStatus",
    "ServiceMetadata",
    "AffinityPrediction",
    "StructuralTemplate",
    "Modification",
    
    # Exceptions
    "Boltz2Error",
    "Boltz2ClientError",
    "Boltz2APIError",
    "Boltz2TimeoutError",
    "Boltz2ConnectionError",
    "Boltz2ValidationError",
    
    # Virtual screening
    "VirtualScreening",
    "CompoundLibrary",
    "VirtualScreeningResult",
    "quick_screen",
    
    # Multi-endpoint support
    "MultiEndpointClient",
    "LoadBalanceStrategy",
    "EndpointConfig",
    
    # MSA Search NIM integration
    "MSASearchClient",
    "MSASearchIntegration",
    "MSASearchRequest",
    "MSASearchResponse",
    "MSAFormatConverter",
    "PairedMSASearchRequest",
    "PairedMSASearchResponse",
    "StructuralTemplateRequest",
    "StructuralTemplateResponse",
    
    # A3M to CSV Multimer Converter
    "A3MToCSVConverter",
    "A3MParser",
    "A3MMSA",
    "A3MSequence",
    "convert_a3m_to_multimer_csv",
    "create_multimer_msa_request",
    "create_paired_msa_per_chain",
    "save_prediction_outputs",
    "get_prediction_summary",
    "save_pae_matrix",
    "save_pde_matrix",
    "get_pae_summary",
    "convert_cif_to_pdb",
    "convert_pdb_to_cif",
    "ConversionResult",
    "GreedyPairingStrategy",
    "CompletePairingStrategy",
    "TaxonomyPairingStrategy",
    "SpeciesMapper",
    "SPECIES_TO_TAXID",
]


def get_version() -> str:
    """Get the current version of the package."""
    return __version__

def check_health(base_url: str = "http://localhost:8000", endpoint_type: str = "local") -> bool:
    """
    Quick health check for a Boltz-2 service.
    
    Args:
        base_url: Base URL of the Boltz-2 service
        endpoint_type: Type of endpoint ("local", "nvidia_hosted", or "sagemaker")
        
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        client = Boltz2SyncClient(base_url=base_url, endpoint_type=endpoint_type)
        health = client.health_check()
        return health.status == "healthy"
    except Exception:
        return False 