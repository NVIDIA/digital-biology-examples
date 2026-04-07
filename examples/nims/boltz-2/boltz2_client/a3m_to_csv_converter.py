# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Backward-compatible re-export shim.

All functionality has moved to the ``boltz2_client.a3m`` subpackage.
This module preserves ``from boltz2_client.a3m_to_csv_converter import ...``
for existing code.
"""

from .a3m import (  # noqa: F401
    A3MParser,
    A3MMSA,
    A3MSequence,
    SpeciesMapper,
    SPECIES_TO_TAXID,
    PairingStrategy,
    GreedyPairingStrategy,
    CompletePairingStrategy,
    TaxonomyPairingStrategy,
    A3MToCSVConverter,
    ConversionResult,
    convert_a3m_to_multimer_csv,
    create_multimer_msa_request,
    create_paired_msa_per_chain,
)
