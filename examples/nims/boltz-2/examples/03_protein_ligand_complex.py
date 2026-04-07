#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Example 3: Protein-Ligand Complex Prediction

This example demonstrates how to predict protein-ligand binding complexes
using both SMILES and CCD codes for ligands, including pocket constraints
to guide binding to specific regions.
"""

import asyncio
from boltz2_client import Boltz2Client
from boltz2_client.models import Polymer, Ligand, Contact, PocketConstraint


async def protein_ligand_complex():
    """Example of protein-ligand complex prediction."""
    print("🧬 Protein-Ligand Complex Prediction Example\n")
    
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Protein sequence (example binding protein)
    protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    # Example ligands
    examples = [
        {
            "name": "Aspirin",
            "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "ccd": None
        },
        {
            "name": "Acetate",
            "smiles": "CC(=O)O",
            "ccd": None
        },
        {
            "name": "ATP (CCD)",
            "smiles": None,
            "ccd": "ATP"
        }
    ]
    
    print(f"Protein sequence: {protein_sequence}")
    print(f"Length: {len(protein_sequence)} residues\n")
    
    for i, ligand in enumerate(examples, 1):
        print(f"--- Example {i}: {ligand['name']} ---")
        
        try:
            if ligand['smiles']:
                print(f"SMILES: {ligand['smiles']}")
                result = await client.predict_protein_ligand_complex(
                    protein_sequence=protein_sequence,
                    ligand_smiles=ligand['smiles'],
                    protein_id="A",
                    ligand_id="LIG",
                    recycling_steps=3,
                    sampling_steps=50
                )
            else:
                print(f"CCD Code: {ligand['ccd']}")
                result = await client.predict_protein_ligand_complex(
                    protein_sequence=protein_sequence,
                    ligand_ccd=ligand['ccd'],
                    protein_id="A",
                    ligand_id="LIG",
                    recycling_steps=3,
                    sampling_steps=50
                )
            
            print(f"✅ Prediction completed!")
            print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
            print(f"📁 Generated {len(result.structures)} structure(s)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()


async def pocket_constrained_binding():
    """Example of pocket-constrained protein-ligand binding."""
    print("🎯 Pocket-Constrained Binding Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Protein with known binding site
    protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    ligand_smiles = "CC(=O)O"  # Simple acetate
    
    print(f"Protein sequence: {protein_sequence}")
    print(f"Ligand SMILES: {ligand_smiles}")
    print("Note: Pocket constraints require specific API format alignment\n")
    
    try:
        # For now, demonstrate enhanced prediction parameters
        print("🔄 Predicting with enhanced parameters...")
        result_enhanced = await client.predict_protein_ligand_complex(
            protein_sequence=protein_sequence,
            ligand_smiles=ligand_smiles,
            protein_id="A",
            ligand_id="LIG",
            recycling_steps=5,
            sampling_steps=100
        )
        
        print(f"✅ Enhanced prediction completed!")
        print(f"📊 Enhanced confidence: {result_enhanced.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result_enhanced.structures)} structure(s)")
        
        # Compare with standard prediction
        print("\n🔄 Comparing with standard binding...")
        result_standard = await client.predict_protein_ligand_complex(
            protein_sequence=protein_sequence,
            ligand_smiles=ligand_smiles,
            protein_id="A",
            ligand_id="LIG",
            recycling_steps=3,
            sampling_steps=50
        )
        
        print(f"📊 Standard confidence: {result_standard.confidence_scores[0]:.3f}")
        print(f"📊 Enhanced confidence: {result_enhanced.confidence_scores[0]:.3f}")
        
        improvement = result_enhanced.confidence_scores[0] - result_standard.confidence_scores[0]
        if improvement > 0:
            print(f"✅ Enhanced parameters improved confidence by {improvement:.3f}")
        else:
            print(f"ℹ️ Enhanced parameters confidence difference: {improvement:.3f}")
        
        print(f"\n💡 Note: Pocket constraints can be used to guide ligand binding")
        print(f"   to specific regions of the protein when the API format is aligned.")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def pocket_constraint_example():
    """Example of using actual pocket constraints to guide ligand binding."""
    print("🎯 Pocket Constraint Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Protein sequence
    protein_sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    ligand_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
    
    print(f"Protein sequence: {protein_sequence}")
    print(f"Ligand SMILES: {ligand_smiles}")
    print(f"Protein length: {len(protein_sequence)} residues\n")
    
    # Define binding pocket residues (example residues that might form a binding site)
    pocket_residues = [10, 15, 20, 25, 30]  # Residues 10, 15, 20, 25, 30
    
    print(f"🔍 Defining pocket constraint:")
    print(f"   Pocket residues: {pocket_residues}")
    print(f"   These residues will be encouraged to interact with the ligand\n")
    
    try:
        # Create polymer and ligand objects
        polymer = Polymer(
            id="A",
            molecule_type="protein",
            sequence=protein_sequence
        )
        
        ligand = Ligand(
            id="LIG",
            smiles=ligand_smiles
        )
        
        # Create pocket constraint
        pocket_constraint = PocketConstraint(
            binder="LIG",
            contacts=[Contact(id="A", residue_index=r) for r in pocket_residues]
        )
        
        print("🔄 Running prediction with pocket constraint...")
        
        # Use advanced parameters method with constraints
        result = await client.predict_with_advanced_parameters(
            polymers=[polymer],
            ligands=[ligand],
            constraints=[pocket_constraint],
            recycling_steps=3,
            sampling_steps=50
        )
        
        print(f"✅ Pocket-constrained prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
        # Compare with unconstrained prediction
        print(f"\n🔄 Running unconstrained prediction for comparison...")
        
        result_unconstrained = await client.predict_with_advanced_parameters(
            polymers=[polymer],
            ligands=[ligand],
            constraints=None,  # No constraints
            recycling_steps=3,
            sampling_steps=50
        )
        
        print(f"📊 Unconstrained confidence: {result_unconstrained.confidence_scores[0]:.3f}")
        print(f"📊 Pocket-constrained confidence: {result.confidence_scores[0]:.3f}")
        
        difference = result.confidence_scores[0] - result_unconstrained.confidence_scores[0]
        if difference > 0:
            print(f"✅ Pocket constraint improved confidence by {difference:.3f}")
        else:
            print(f"ℹ️ Pocket constraint confidence difference: {difference:.3f}")
        
        print(f"\n💡 Pocket constraints guide the ligand to bind near specific residues")
        print(f"   This can be useful when you know the binding site from experiments")
        print(f"   or want to test binding at a particular location.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"💡 Make sure the residue indices are valid (1-based, ≤ sequence length)")


async def main():
    """Run all protein-ligand examples."""
    await protein_ligand_complex()
    print("\n" + "="*60 + "\n")
    await pocket_constrained_binding()
    print("\n" + "="*60 + "\n")
    await pocket_constraint_example()


if __name__ == "__main__":
    asyncio.run(main()) 