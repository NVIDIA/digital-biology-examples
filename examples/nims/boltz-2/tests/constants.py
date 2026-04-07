# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""Shared test constants. Import from here rather than redefining in each file."""

import os

CDK2_SEQUENCE = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
SAMPLE_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
SAMPLE_CCD = "ASP"
SAMPLE_DNA = "ATCGATCGATCGATCG"
SAMPLE_COMPOUNDS = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
    {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1"},
]
BOLTZ2_NIM_URL = os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000")
