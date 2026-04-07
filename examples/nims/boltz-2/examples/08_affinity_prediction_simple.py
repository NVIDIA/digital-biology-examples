#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Example 8: Affinity Prediction (Simplified)

A simplified example demonstrating affinity prediction with a smaller protein
and common drug molecule for faster execution.
"""

import asyncio
from boltz2_client import Boltz2Client, Polymer, Ligand, PredictionRequest

# Small test protein (50 residues)
TEST_SEQUENCE = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSL"

# Aspirin SMILES
ASPIRIN_SMILES = "CC(=O)OC1=CC=CC=C1C(=O)O"


async def predict_affinity_simple():
    """Simple affinity prediction example."""
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Create protein
    protein = Polymer(
        id="A",
        molecule_type="protein",
        sequence=TEST_SEQUENCE
    )
    
    # Create ligand with affinity prediction
    ligand = Ligand(
        id="LIG",
        smiles=ASPIRIN_SMILES,
        predict_affinity=True
    )
    
    print("🧪 Affinity Prediction Example (Simplified)")
    print("=" * 50)
    print(f"Protein: Test sequence ({len(TEST_SEQUENCE)} residues)")
    print(f"Ligand: Aspirin")
    print()
    
    # Create prediction request with minimal parameters
    request = PredictionRequest(
        polymers=[protein],
        ligands=[ligand],
        # Minimal parameters for faster execution
        recycling_steps=1,
        sampling_steps=10,
        diffusion_samples=1,
        # Affinity parameters
        sampling_steps_affinity=50,
        diffusion_samples_affinity=2,
        affinity_mw_correction=True
    )
    
    print("🚀 Running prediction...")
    
    try:
        # Predict
        result = await client.predict(request)
        
        print("✅ Prediction complete!")
        
        # Check affinity results
        if result.affinities and "LIG" in result.affinities:
            affinity = result.affinities["LIG"]
            
            print("\n📊 Affinity Results:")
            print("-" * 30)
            print(f"pIC50: {affinity.affinity_pic50[0]:.2f}")
            print(f"Binding probability: {affinity.affinity_probability_binary[0]:.1%}")
            
            # Correct IC50 calculation
            # pIC50 = -log10(IC50 in M), so IC50 in M = 10^(-pIC50)
            ic50_nm = 10 ** (-affinity.affinity_pic50[0]) * 1e9
            print(f"IC50: {ic50_nm:.1f} nM")
            
            # Interpretation
            print("\n💊 Interpretation:")
            if affinity.affinity_pic50[0] > 7.0:
                print("→ Strong binding predicted")
            elif affinity.affinity_pic50[0] > 5.0:
                print("→ Moderate binding predicted")
            else:
                print("→ Weak/no binding predicted")
                
        else:
            print("⚠️ No affinity data in response")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        

def main():
    """Run the example."""
    asyncio.run(predict_affinity_simple())


if __name__ == "__main__":
    main() 