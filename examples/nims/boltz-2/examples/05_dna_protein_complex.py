#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Example 5: DNA-Protein Complex Prediction

This example demonstrates how to predict DNA-protein complexes,
including transcription factors, nucleases, and other DNA-binding proteins.
"""

import asyncio
from boltz2_client import Boltz2Client


async def simple_dna_protein():
    """Example of simple DNA-protein complex prediction."""
    print("🧬 DNA-Protein Complex Prediction Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # DNA-binding protein (example transcription factor domain)
    protein_sequences = [
        "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    ]
    
    # DNA sequences (example binding sites)
    dna_sequences = [
        "ATCGATCGATCGATCG",  # 16 bp DNA
        "GCTAGCTAGCTAGCTA"   # 16 bp DNA (complementary)
    ]
    
    print(f"Protein sequences: {len(protein_sequences)}")
    for i, seq in enumerate(protein_sequences):
        print(f"  Protein {i+1}: {seq} ({len(seq)} residues)")
    
    print(f"\nDNA sequences: {len(dna_sequences)}")
    for i, seq in enumerate(dna_sequences):
        print(f"  DNA {i+1}: {seq} ({len(seq)} bp)")
    
    try:
        print("\n🔄 Predicting DNA-protein complex...")
        result = await client.predict_dna_protein_complex(
            protein_sequences=protein_sequences,
            dna_sequences=dna_sequences,
            protein_ids=["A"],
            dna_ids=["B", "C"],
            recycling_steps=4,
            sampling_steps=75,
            concatenate_msas=False
        )
        
        print(f"✅ DNA-protein complex prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def multi_protein_dna():
    """Example of multi-protein DNA complex."""
    print("🧬 Multi-Protein DNA Complex Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Multiple proteins (e.g., transcription factor complex)
    protein_sequences = [
        "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",  # Protein 1
        "MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPAD"    # Protein 2
    ]
    
    # DNA double helix
    dna_sequences = [
        "ATCGATCGATCGATCGATCGATCG",  # 24 bp DNA strand 1
        "CGATCGATCGATCGATCGATCGAT"   # 24 bp DNA strand 2
    ]
    
    print(f"Multi-protein DNA complex:")
    print(f"Proteins: {len(protein_sequences)}")
    for i, seq in enumerate(protein_sequences):
        print(f"  Protein {i+1}: {len(seq)} residues")
    
    print(f"DNA strands: {len(dna_sequences)}")
    for i, seq in enumerate(dna_sequences):
        print(f"  DNA {i+1}: {seq} ({len(seq)} bp)")
    
    try:
        print("\n🔄 Predicting multi-protein DNA complex...")
        result = await client.predict_dna_protein_complex(
            protein_sequences=protein_sequences,
            dna_sequences=dna_sequences,
            protein_ids=["A", "B"],
            dna_ids=["C", "D"],
            recycling_steps=5,
            sampling_steps=100,
            concatenate_msas=True  # Concatenate MSAs for better complex prediction
        )
        
        print(f"✅ Multi-protein DNA complex prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def rna_protein_complex():
    """Example of RNA-protein complex prediction."""
    print("🧬 RNA-Protein Complex Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # RNA-binding protein
    protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    # RNA sequence (example ribosomal RNA fragment)
    rna_sequence = "AUCGAUCGAUCGAUCG"  # 16 nt RNA
    
    print(f"RNA-binding protein: {len(protein_sequence)} residues")
    print(f"RNA sequence: {rna_sequence} ({len(rna_sequence)} nt)")
    
    try:
        # Use the advanced method for RNA-protein complex
        from boltz2_client.models import Polymer, PredictionRequest
        
        # Create polymers
        polymers = [
            Polymer(
                id="A",
                molecule_type="protein",
                sequence=protein_sequence
            ),
            Polymer(
                id="B",
                molecule_type="rna",
                sequence=rna_sequence
            )
        ]
        
        # Create prediction request
        request = PredictionRequest(
            polymers=polymers,
            recycling_steps=4,
            sampling_steps=75,
            concatenate_msas=False
        )
        
        print("\n🔄 Predicting RNA-protein complex...")
        result = await client.predict(request)
        
        print(f"✅ RNA-protein complex prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def nuclease_dna_complex():
    """Example of nuclease-DNA complex with advanced parameters."""
    print("🧬 Nuclease-DNA Complex with Advanced Parameters\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Nuclease protein (example restriction enzyme)
    protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    # DNA substrate with recognition sequence
    dna_sequence = "ATCGATCGAATTCGATCGATCG"  # Contains EcoRI site (GAATTC)
    
    print(f"Nuclease protein: {len(protein_sequence)} residues")
    print(f"DNA substrate: {dna_sequence} ({len(dna_sequence)} bp)")
    print(f"Recognition site: GAATTC at position {dna_sequence.find('GAATTC')}")
    
    try:
        # Use advanced parameters for better accuracy
        result = await client.predict_dna_protein_complex(
            protein_sequences=[protein_sequence],
            dna_sequences=[dna_sequence],
            protein_ids=["A"],
            dna_ids=["B"],
            recycling_steps=6,      # Maximum recycling for accuracy
            sampling_steps=150,     # More sampling steps
            concatenate_msas=False
        )
        
        print(f"\n✅ Nuclease-DNA complex prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
        # Additional metrics if available
        if result.metrics:
            print(f"📈 Prediction metrics:")
            for key, value in result.metrics.items():
                print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all DNA-protein complex examples."""
    await simple_dna_protein()
    print("\n" + "="*60 + "\n")
    await multi_protein_dna()
    print("\n" + "="*60 + "\n")
    await rna_protein_complex()
    print("\n" + "="*60 + "\n")
    await nuclease_dna_complex()


if __name__ == "__main__":
    asyncio.run(main()) 