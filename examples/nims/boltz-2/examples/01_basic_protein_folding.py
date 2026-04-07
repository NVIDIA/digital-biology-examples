#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Example 1: Basic Protein Structure Prediction

This example demonstrates how to predict protein structure using just a sequence.
"""

import asyncio
from boltz2_client import Boltz2Client


async def basic_protein_folding():
    """Example of basic protein structure prediction."""
    print("🧬 Basic Protein Structure Prediction Example\n")
    
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Test sequence (small protein for quick testing)
    sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    print(f"Sequence: {sequence}")
    print(f"Length: {len(sequence)} residues\n")
    
    try:
        # Predict structure
        print("🔄 Predicting protein structure...")
        result = await client.predict_protein_structure(
            sequence=sequence,
            polymer_id="A",
            recycling_steps=3,
            sampling_steps=50
        )
        
        print(f"✅ Prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
        # Structure information
        for i, structure in enumerate(result.structures):
            print(f"   Structure {i+1}: {structure.format} format")
            print(f"   Size: {len(structure.structure)} characters")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(basic_protein_folding()) 