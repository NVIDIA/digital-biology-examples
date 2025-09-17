# ---------------------------------------------------------------
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Boltz-2 Python Client

A comprehensive Python client for NVIDIA's Boltz-2 molecular structure prediction service.
Supports both local deployments and NVIDIA hosted endpoints with full API coverage.

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

__version__ = "0.3.0"
__author__ = "NVIDIA Corporation"
__email__ = "bionemo-support@nvidia.com"

from .client import Boltz2Client, Boltz2SyncClient, EndpointType
from .models import (
    PredictionRequest,
    PredictionResponse,
    Polymer,
    Ligand,
    PocketConstraint,
    BondConstraint,
    Atom,
    AlignmentFileRecord,
    AlignmentFormat,
    HealthStatus,
    ServiceMetadata,
)
from .models_affinity import AffinityPrediction
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
)

# Optional imports for visualization
try:
    from .visualization import (
        StructureVisualizer,
        visualize_structure,
        create_multi_view,
    )
    _HAS_VISUALIZATION = True
except ImportError:
    _HAS_VISUALIZATION = False

# Optional imports for analysis
try:
    from .analysis import (
        StructureAnalyzer,
        calculate_rmsd,
        analyze_contacts,
    )
    _HAS_ANALYSIS = True
except ImportError:
    _HAS_ANALYSIS = False

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
    "PocketConstraint",
    "BondConstraint",
    "Atom",
    "AlignmentFileRecord",
    "AlignmentFormat",
    "HealthStatus",
    "ServiceMetadata",
    "AffinityPrediction",
    
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
]

# Add visualization exports if available
if _HAS_VISUALIZATION:
    __all__.extend([
        "StructureVisualizer",
        "visualize_structure", 
        "create_multi_view",
    ])

# Add analysis exports if available
if _HAS_ANALYSIS:
    __all__.extend([
        "StructureAnalyzer",
        "calculate_rmsd",
        "analyze_contacts",
    ])

def get_version() -> str:
    """Get the current version of the package."""
    return __version__

def check_health(base_url: str = "http://localhost:8000", endpoint_type: str = "local") -> bool:
    """
    Quick health check for a Boltz-2 service.
    
    Args:
        base_url: Base URL of the Boltz-2 service
        endpoint_type: Type of endpoint ("local" or "nvidia_hosted")
        
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        client = Boltz2SyncClient(base_url=base_url, endpoint_type=endpoint_type)
        health = client.health_check()
        return health.status == "healthy"
    except Exception:
        return False 