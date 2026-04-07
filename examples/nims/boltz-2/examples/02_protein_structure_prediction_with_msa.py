#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
02_protein_structure_prediction_with_msa.py

Demonstrates MSA-guided protein structure prediction using Boltz-2.
This example shows how to use Multiple Sequence Alignment (MSA) data 
to improve prediction accuracy by providing evolutionary context.

Key Features:
- Comparison between MSA-guided and basic predictions
- Proper MSA file handling and validation
- Client helper functions for automatic schema conversion
- Confidence score analysis and interpretation
"""

import asyncio
from pathlib import Path
from boltz2_client import Boltz2Client

# Example protein sequence (KRAS G12C - a well-studied oncogene)
PROTEIN_SEQUENCE = (
    "MTEYKLVVVGACGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEY"
    "SAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQ"
    "AQDLARSYGIPFIETSAKTRQGVDDAFYTLVREIRKHKE"
)

# Path to MSA file (A3M format with evolutionary sequences)
MSA_FILE_PATH = Path(__file__).parent / "data" / "msa-kras-g12c_combined.a3m"


async def predict_without_msa(client: Boltz2Client) -> dict:
    """Perform basic protein structure prediction without MSA."""
    print("🔬 Step 1: Basic prediction (no evolutionary data)")
    print("-" * 50)
    
    result = await client.predict_protein_structure(
        sequence=PROTEIN_SEQUENCE,
        recycling_steps=3,
        sampling_steps=50
    )
    
    confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
    print(f"✅ Basic prediction completed")
    print(f"📊 Confidence score: {confidence:.3f}")
    print(f"📄 Structure length: {len(result.structures[0].structure)} characters")
    
    return {
        "type": "basic",
        "confidence": confidence,
        "structure": result.structures[0].structure,
        "result": result
    }


async def predict_with_msa(client: Boltz2Client) -> dict:
    """Perform MSA-guided protein structure prediction."""
    print("\n🧬 Step 2: MSA-guided prediction (with evolutionary data)")
    print("-" * 55)
    
    # Validate MSA file exists
    if not MSA_FILE_PATH.exists():
        print(f"⚠️ Warning: MSA file not found at {MSA_FILE_PATH}")
        print("   Using basic prediction instead...")
        return await predict_without_msa(client)
    
    # Load and analyze MSA file
    msa_text = MSA_FILE_PATH.read_text()
    sequence_count = sum(1 for line in msa_text.split("\n") if line.startswith(">"))
    print(f"📁 Loaded MSA: {MSA_FILE_PATH.name}")
    print(f"🔢 Sequences in alignment: {sequence_count}")
    print(f"📏 MSA file size: {len(msa_text):,} characters")
    
    # Use client helper function for automatic schema conversion
    msa_files = [(str(MSA_FILE_PATH), "a3m")]
    
    result = await client.predict_protein_structure(
        sequence=PROTEIN_SEQUENCE,
        msa_files=msa_files,  # Helper automatically converts to nested dict schema
        recycling_steps=3,
        sampling_steps=50
    )
    
    confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
    print(f"✅ MSA-guided prediction completed")
    print(f"📊 Confidence score: {confidence:.3f}")
    print(f"📄 Structure length: {len(result.structures[0].structure)} characters")
    
    return {
        "type": "msa_guided",
        "confidence": confidence,
        "structure": result.structures[0].structure,
        "result": result,
        "msa_sequences": sequence_count
    }


def analyze_results(basic_result: dict, msa_result: dict) -> None:
    """Compare and analyze prediction results."""
    print("\n📈 Results Analysis")
    print("=" * 50)
    
    basic_conf = basic_result["confidence"]
    msa_conf = msa_result["confidence"]
    
    print(f"Basic prediction confidence:     {basic_conf:.3f}")
    print(f"MSA-guided prediction confidence: {msa_conf:.3f}")
    
    if msa_conf > basic_conf:
        improvement = ((msa_conf - basic_conf) / basic_conf) * 100
        print(f"🎉 MSA improved confidence by {improvement:.1f}%")
        print("✨ Evolutionary data enhanced prediction quality!")
    elif msa_conf < basic_conf:
        decrease = ((basic_conf - msa_conf) / basic_conf) * 100
        print(f"⚠️  MSA confidence lower by {decrease:.1f}%")
        print("ℹ️  This can happen with noisy or misaligned MSAs")
    else:
        print("➡️  Similar confidence scores")
    
    # Confidence interpretation
    print(f"\n🎯 Confidence Interpretation:")
    for result_type, conf in [("Basic", basic_conf), ("MSA-guided", msa_conf)]:
        if conf > 0.9:
            quality = "Excellent (very reliable)"
        elif conf > 0.7:
            quality = "Good (reliable)"
        elif conf > 0.5:
            quality = "Moderate (use with caution)"
        else:
            quality = "Poor (unreliable)"
        print(f"   {result_type}: {quality}")


async def save_structures(basic_result: dict, msa_result: dict) -> None:
    """Save prediction structures to CIF files."""
    print(f"\n💾 Saving Structures")
    print("-" * 20)
    
    # Save basic prediction
    basic_file = "protein_basic_prediction.cif"
    Path(basic_file).write_text(basic_result["structure"])
    print(f"📁 Basic structure: {basic_file}")
    
    # Save MSA-guided prediction
    msa_file = "protein_msa_guided_prediction.cif"
    Path(msa_file).write_text(msa_result["structure"])
    print(f"📁 MSA structure: {msa_file}")
    
    print(f"ℹ️  Load these files in PyMOL, ChimeraX, or any molecular viewer")


async def main():
    """Main execution function."""
    print("🧬 Protein Structure Prediction with MSA")
    print("=" * 60)
    print("This example demonstrates how Multiple Sequence Alignment (MSA)")
    print("data can improve protein structure prediction accuracy.\n")
    
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    try:
        # Test server connection
        health = await client.health_check()
        print(f"🌐 Server status: {health.status}")
        
        # Perform both types of predictions
        basic_result = await predict_without_msa(client)
        msa_result = await predict_with_msa(client)
        
        # Analyze and compare results
        analyze_results(basic_result, msa_result)
        
        # Save structures for visualization
        await save_structures(basic_result, msa_result)
        
        print(f"\n🎉 Analysis complete!")
        print(f"💡 Key takeaway: MSA data provides evolutionary context")
        print(f"   that often improves structure prediction accuracy.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"💡 Make sure Boltz-2 server is running at http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(main()) 