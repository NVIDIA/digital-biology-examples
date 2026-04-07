# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
A3M subpackage for parsing, pairing, and converting MSA files.

Public API re-exports for backward compatibility with
``from boltz2_client.a3m_to_csv_converter import ...``.
"""

from .parser import (
    A3MParser,
    A3MMSA,
    A3MSequence,
    SpeciesMapper,
    SPECIES_TO_TAXID,
)
from .pairing import (
    PairingStrategy,
    GreedyPairingStrategy,
    CompletePairingStrategy,
    TaxonomyPairingStrategy,
)
from .converter import (
    A3MToCSVConverter,
    ConversionResult,
    convert_a3m_to_multimer_csv,
    create_multimer_msa_request,
    create_paired_msa_per_chain,
)

__all__ = [
    "A3MParser",
    "A3MMSA",
    "A3MSequence",
    "SpeciesMapper",
    "SPECIES_TO_TAXID",
    "PairingStrategy",
    "GreedyPairingStrategy",
    "CompletePairingStrategy",
    "TaxonomyPairingStrategy",
    "A3MToCSVConverter",
    "ConversionResult",
    "convert_a3m_to_multimer_csv",
    "create_multimer_msa_request",
    "create_paired_msa_per_chain",
]
