#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
CDK4 Protein-Ligand Affinity Prediction with MSA

This example demonstrates:
1. MSA search for CDK4 protein using GPU MSA NIM
2. Converting MSA from JSON to a3m format
3. Protein-ligand affinity prediction using Boltz2 NIM

Target: CDK4 (Cyclin-dependent kinase 4)
Ligand: Palbociclib (FDA-approved CDK4/6 inhibitor)
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from boltz2_client import Boltz2Client, Polymer, Ligand, PredictionRequest
from boltz2_client.models import AlignmentFileRecord
from boltz2_client.msa_search import MSASearchClient, MSASearchIntegration

# Endpoints
MSA_ENDPOINT = os.getenv("MSA_NIM_URL", "http://localhost:8000")
BOLTZ2_ENDPOINT = os.getenv("BOLTZ2_NIM_URL", "http://localhost:8000")

# CDK4 sequence (295 amino acids)
CDK4_SEQUENCE = "MATSRYEPVAEIGVGAYGTVYKARDPHSGHFVALKSVRVPNGGGGGGGLPISTVREVALLRRLEAFEHPNVVRLMDVCATSRTDREIKVTLVFEHVDQDLRTYLDKAPPPGLPAETIKDLMRQFLRGLDFLHANCIVHRDLKPENILVTSGGTVKLADFGLARIYSYQMALTPVVVTLWYRAPEVLLQSTYATPVDMWSVGCIFAEMFRRKPLFCGNSEADQLGKIFDLIGLPPEDDWPRDVSLPRGAFPPRGPRPVQSVVPEMEESGAQLLLEMLTFNPHKRISAFRALQHSYLHKDEGNPE"

# Palbociclib (Ibrance) - CDK4/6 inhibitor
# SMILES from PubChem CID: 5330286
PALBOCICLIB_SMILES = "CC1=C(C(=O)N(C2=NC(=NC=C12)NC3=NC=C(C=C3)N4CCNCC4)C5CCCC5)C(=O)C"


def convert_msa_to_a3m(msa_response, query_sequence, query_name="query"):
    """
    Convert MSA search response to A3M format.
    A3M format is like FASTA but allows lowercase letters for insertions.
    """
    a3m_lines = []
    
    # Add query sequence first
    a3m_lines.append(f">{query_name}")
    a3m_lines.append(query_sequence)
    
    # Process each database's alignments
    sequence_count = 0
    for db_name, alignments in msa_response.alignments.items():
        print(f"\nProcessing {db_name} alignments...")
        
        for i, alignment in enumerate(alignments):
            # Extract aligned sequence
            if hasattr(alignment, 'aligned_sequence'):
                aligned_seq = alignment.aligned_sequence
            elif hasattr(alignment, 'sequence'):
                aligned_seq = alignment.sequence
            else:
                continue
            
            # Skip if identical to query
            if aligned_seq.replace('-', '') == query_sequence:
                continue
            
            # Create header with metadata
            header = f">{db_name}_{i}"
            if hasattr(alignment, 'description'):
                header += f" {alignment.description[:50]}"
            if hasattr(alignment, 'e_value'):
                header += f" E={alignment.e_value:.2e}"
            
            a3m_lines.append(header)
            a3m_lines.append(aligned_seq)
            sequence_count += 1
    
    print(f"\n✅ Converted {sequence_count} sequences to A3M format")
    return "\n".join(a3m_lines)


async def search_msa_and_convert(sequence, output_dir):
    """Search MSA and convert to A3M format."""
    print("🔍 Searching for CDK4 MSA...")
    
    # Initialize MSA client
    msa_client = MSASearchClient(endpoint_url=MSA_ENDPOINT)
    
    # Perform MSA search with correct parameters
    msa_response = await msa_client.search(
        sequence=sequence,
        databases=["Uniref30_2302", "colabfold_envdb_202108"],
        max_msa_sequences=500,  # Correct parameter name
        e_value=0.1,  # More permissive than default
        output_alignment_formats=["a3m"]
    )
    
    print(f"\n✅ MSA search complete!")
    print(f"Found alignments in {len(msa_response.alignments)} databases:")
    for db_name, alignments in msa_response.alignments.items():
        print(f"   - {db_name}: {len(alignments)} sequences")
    
    # Convert to A3M
    cdk4_a3m = convert_msa_to_a3m(msa_response, sequence, "CDK4_HUMAN")
    
    # Save A3M file
    a3m_path = output_dir / "cdk4_msa.a3m"
    with open(a3m_path, "w") as f:
        f.write(cdk4_a3m)
    
    print(f"\n📄 A3M file saved to: {a3m_path}")
    print(f"File size: {len(cdk4_a3m):,} bytes")
    
    # Show preview
    lines = cdk4_a3m.split("\n")
    print(f"\nFirst few lines of A3M:")
    for line in lines[:6]:
        print(line[:80] + "..." if len(line) > 80 else line)
    print("...")
    
    return a3m_path, cdk4_a3m


async def predict_with_affinity(cdk4_a3m_content, output_dir):
    """Perform protein-ligand affinity prediction."""
    print("\n🧬 Preparing CDK4-Palbociclib affinity prediction...")
    
    # Initialize Boltz2 client
    client = Boltz2Client(base_url=BOLTZ2_ENDPOINT)
    
    # Create CDK4 polymer with MSA
    cdk4_with_msa = Polymer(
        id="A",
        molecule_type="protein",
        sequence=CDK4_SEQUENCE,
        msa={
            "default": {
                "a3m": AlignmentFileRecord(
                    alignment=cdk4_a3m_content,
                    format="a3m",
                    rank=0
                )
            }
        }
    )
    
    # Create Palbociclib ligand with affinity prediction enabled
    palbociclib = Ligand(
        id="LIG",
        smiles=PALBOCICLIB_SMILES,
        predict_affinity=True  # Enable affinity prediction
    )
    
    # Create prediction request
    request = PredictionRequest(
        polymers=[cdk4_with_msa],
        ligands=[palbociclib],
        recycling_steps=5,
        sampling_steps=100,
        # Affinity prediction parameters
        sampling_steps_affinity=200,
        diffusion_samples_affinity=5,
        affinity_mw_correction=True
    )
    
    print("🔄 Predicting CDK4-Palbociclib complex with affinity...")
    print("   This may take several minutes...")
    
    # Predict
    result = await client.predict(request)
    
    # Save structure
    structure_path = output_dir / "cdk4_palbociclib_complex.cif"
    with open(structure_path, "w") as f:
        f.write(result.structures[0].structure)
    
    print(f"\n✅ Prediction complete!")
    print(f"📁 Structure saved to: {structure_path}")
    
    return result, structure_path


async def main():
    """Main workflow."""
    print("=" * 60)
    print("CDK4-Palbociclib Affinity Prediction with MSA")
    print("=" * 60)
    
    print(f"\n🧬 CDK4 Protein:")
    print(f"   Length: {len(CDK4_SEQUENCE)} residues")
    print(f"   Function: Cell cycle regulation (G1/S transition)")
    print(f"\n💊 Palbociclib (Ibrance):")
    print(f"   Type: CDK4/6 selective inhibitor")
    print(f"   FDA approved: 2015 (breast cancer treatment)")
    print(f"   Known IC50: ~11 nM for CDK4")
    
    # Create output directory
    output_dir = Path("cdk4_msa_affinity")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: MSA Search and Conversion
        a3m_path, a3m_content = await search_msa_and_convert(CDK4_SEQUENCE, output_dir)
        
        # Alternative: Using MSASearchIntegration (direct save)
        print("\n📝 Alternative method: Direct MSA save using MSASearchIntegration")
        msa_client_for_integration = MSASearchClient(endpoint_url=MSA_ENDPOINT)
        msa_integration = MSASearchIntegration(msa_client_for_integration)
        direct_msa_path = await msa_integration.search_and_save(
            sequence=CDK4_SEQUENCE,
            output_path=output_dir / "cdk4_direct.a3m",
            output_format="a3m",
            databases=["Uniref30_2302", "colabfold_envdb_202108"],
            max_msa_sequences=500
        )
        print(f"✅ Direct MSA saved to: {direct_msa_path}")
        
        # Step 2: Affinity Prediction
        result, structure_path = await predict_with_affinity(a3m_content, output_dir)
        
        # Step 3: Analyze Results
        print("\n📊 Structure Confidence Metrics:")
        print(f"├─ Overall confidence: {result.confidence_scores[0]:.1%}")
        print(f"├─ pTM: {result.ptm_scores[0]:.3f}")
        print(f"└─ Complex pLDDT: {result.complex_plddt_scores[0]:.1f}")
        
        # Affinity predictions
        if result.affinities and "LIG" in result.affinities:
            affinity = result.affinities["LIG"]
            
            print("\n💊 Affinity Predictions:")
            print(f"├─ pIC50: {affinity.affinity_pic50[0]:.2f}")
            
            # Convert pIC50 to IC50 in nM
            ic50_molar = 10 ** (-affinity.affinity_pic50[0])
            ic50_nm = ic50_molar * 1e9
            print(f"├─ IC50: {ic50_nm:.1f} nM")
            print(f"├─ Binding probability: {affinity.affinity_binding_prob[0]:.1%}")
            
            # Compare with known value
            known_ic50 = 11  # nM
            print(f"\n📈 Comparison with experimental data:")
            print(f"├─ Predicted IC50: {ic50_nm:.1f} nM")
            print(f"├─ Known IC50: {known_ic50} nM")
            print(f"└─ Fold difference: {ic50_nm/known_ic50:.1f}x")
            
            if 0.2 <= ic50_nm/known_ic50 <= 5:
                print("\n✅ Excellent prediction! Within 5-fold of experimental value.")
            elif 0.1 <= ic50_nm/known_ic50 <= 10:
                print("\n✅ Good prediction! Within 10-fold of experimental value.")
            else:
                print("\n⚠️  Prediction differs significantly from experimental value.")
            
            # Save results
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "protein": {
                    "name": "CDK4",
                    "sequence_length": len(CDK4_SEQUENCE),
                    "msa_sequences": len(a3m_content.split('>')) - 1
                },
                "ligand": {
                    "name": "Palbociclib",
                    "smiles": PALBOCICLIB_SMILES,
                    "known_ic50_nm": known_ic50
                },
                "structure_confidence": {
                    "overall": result.confidence_scores[0],
                    "ptm": result.ptm_scores[0],
                    "plddt": result.complex_plddt_scores[0]
                },
                "affinity_predictions": {
                    "pic50": affinity.affinity_pic50[0],
                    "ic50_nm": ic50_nm,
                    "binding_probability": affinity.affinity_binding_prob[0]
                }
            }
            
            # Save JSON
            json_path = output_dir / "cdk4_palbociclib_results.json"
            with open(json_path, "w") as f:
                json.dump(results_data, f, indent=2)
            
            print(f"\n📄 Complete results saved to: {json_path}")
        else:
            print("\n❌ No affinity predictions found")
        
        # Summary
        print("\n📁 All output files:")
        print(f"├─ {a3m_path.name} - MSA in A3M format")
        print(f"├─ {direct_msa_path.name} - MSA (direct save)")
        print(f"├─ {structure_path.name} - Complex structure")
        print(f"└─ cdk4_palbociclib_results.json - Complete results")
        
        print("\n💡 Visualization in PyMOL:")
        print(f"pymol {structure_path}")
        print("# Then in PyMOL:")
        print("spectrum b, red_yellow_green_blue, minimum=50, maximum=90")
        print("show sticks, resn LIG")
        print("color magenta, resn LIG")
        print("show sticks, byres resn LIG around 5")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
