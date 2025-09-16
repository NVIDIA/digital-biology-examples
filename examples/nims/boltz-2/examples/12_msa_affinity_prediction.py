#!/usr/bin/env python3
"""
Example 12: MSA-Guided Protein-Ligand Affinity Prediction

This example demonstrates how to combine MSA search with protein-ligand
complex prediction and affinity estimation.

Key features:
- MSA search for improved protein structure accuracy
- Protein-ligand complex prediction
- Affinity prediction (pIC50/IC50)
- Comparison with and without MSA
"""

import asyncio
from pathlib import Path
from boltz2_client import Boltz2Client, Polymer, Ligand, PredictionRequest, AlignmentFileRecord

# Example: Human Carbonic Anhydrase II (CA-II) - a well-studied drug target
PROTEIN_SEQUENCE = """
SHHWGYGKHNGPEHWHKDFPIAKGERQSPVDIDTHTAKYDPSLKPLSVSYDQATSLRILNNGHAFNVEFDDSQ
DKAVLKGGPLDGTYRLIQFHFHWGSLDGQGSEHTVDKKKYAAELHLVHWNTKYGDFGKAVQQPDGLAVLGIFL
KVGSAKPGLQKVVDVLDSIKTKGKSADFTNFDPRGLLPESLDYWTYPGSLTTPPLLECVTWIVLKEPISVSSEQ
VDKFRKLNFNGEGEPEELMVDNWRPAQPLKNRQIKASFK
""".strip().replace('\n', '')

# Ligand: Dorzolamide (a carbonic anhydrase inhibitor)
DORZOLAMIDE_SMILES = "CCNS(=O)(=O)c1sc(S(N)(=O)=O)c(C)c1C"

# Alternative ligand: Acetazolamide
ACETAZOLAMIDE_SMILES = "CC(=O)Nc1nnc(s1)S(=O)(=O)N"


async def predict_without_msa(client: Boltz2Client, output_dir: Path):
    """Predict protein-ligand complex without MSA."""
    print("\n=== Prediction WITHOUT MSA ===")
    
    result = await client.predict_protein_ligand_complex(
        protein_sequence=PROTEIN_SEQUENCE,
        ligand_smiles=DORZOLAMIDE_SMILES,
        ligand_id="DOR",
        recycling_steps=3,
        sampling_steps=50,
        predict_affinity=True,
        sampling_steps_affinity=200,
        diffusion_samples_affinity=5,
        save_structures=True,
        output_dir=output_dir / "without_msa"
    )
    
    print(f"✅ Structure confidence: {result.confidence_scores[0]:.3f}")
    
    if result.affinities and "DOR" in result.affinities:
        aff = result.affinities["DOR"]
        print(f"📊 Affinity predictions:")
        print(f"   - pIC50: {aff.affinity_pic50[0]:.3f}")
        print(f"   - IC50: {aff.affinity_ic50[0]:.3f} nM")
        print(f"   - Binding probability: {aff.affinity_probability_binary[0]:.3f}")
    
    return result


async def predict_with_msa_search(client: Boltz2Client, output_dir: Path):
    """Predict protein-ligand complex with MSA search."""
    print("\n=== Prediction WITH MSA Search ===")
    
    # Configure MSA Search
    client.configure_msa_search(
        msa_endpoint_url="http://your-msa-nim:8000",
        timeout=300
    )
    
    # Use the new integrated method
    result = await client.predict_ligand_with_msa_search(
        protein_sequence=PROTEIN_SEQUENCE,
        ligand_smiles=DORZOLAMIDE_SMILES,
        ligand_id="DOR",
        databases=["Uniref30_2302", "PDB70_220313"],
        max_msa_sequences=1000,
        e_value=0.0001,
        recycling_steps=5,  # Higher for better accuracy
        sampling_steps=100,
        predict_affinity=True,
        sampling_steps_affinity=300,  # Higher for affinity
        diffusion_samples_affinity=8,
        affinity_mw_correction=True,
        save_structures=True,
        output_dir=output_dir / "with_msa"
    )
    
    print(f"✅ Structure confidence: {result.confidence_scores[0]:.3f}")
    
    if result.affinities and "DOR" in result.affinities:
        aff = result.affinities["DOR"]
        print(f"📊 Affinity predictions:")
        print(f"   - pIC50: {aff.affinity_pic50[0]:.3f}")
        print(f"   - IC50: {aff.affinity_ic50[0]:.3f} nM")
        print(f"   - Binding probability: {aff.affinity_probability_binary[0]:.3f}")
    
    return result


async def predict_with_existing_msa(client: Boltz2Client, output_dir: Path):
    """Predict using pre-computed MSA file."""
    print("\n=== Prediction with Pre-computed MSA ===")
    
    # Assume we have a pre-computed MSA file
    msa_path = output_dir / "ca2_alignment.a3m"
    
    if msa_path.exists():
        result = await client.predict_protein_ligand_complex(
            protein_sequence=PROTEIN_SEQUENCE,
            ligand_smiles=ACETAZOLAMIDE_SMILES,
            ligand_id="ACZ",
            msa_files=[(str(msa_path), "a3m")],
            recycling_steps=5,
            sampling_steps=100,
            predict_affinity=True,
            sampling_steps_affinity=300,
            diffusion_samples_affinity=8,
            save_structures=True,
            output_dir=output_dir / "with_existing_msa"
        )
        
        print(f"✅ Structure confidence: {result.confidence_scores[0]:.3f}")
        
        if result.affinities and "ACZ" in result.affinities:
            aff = result.affinities["ACZ"]
            print(f"📊 Affinity predictions for Acetazolamide:")
            print(f"   - pIC50: {aff.affinity_pic50[0]:.3f}")
            print(f"   - IC50: {aff.affinity_ic50[0]:.3f} nM")
            print(f"   - Binding probability: {aff.affinity_probability_binary[0]:.3f}")
    else:
        print("⚠️  MSA file not found. Run MSA search first.")


async def manual_msa_then_affinity(client: Boltz2Client, output_dir: Path):
    """Demonstrate manual MSA search followed by affinity prediction."""
    print("\n=== Manual MSA Search + Affinity Prediction ===")
    
    # Step 1: Configure MSA Search
    client.configure_msa_search("http://your-msa-nim:8000")
    
    # Step 2: Search and save MSA
    print("🔍 Searching for MSA...")
    msa_path = await client.search_msa(
        sequence=PROTEIN_SEQUENCE,
        databases=["Uniref30_2302", "PDB70_220313"],
        max_msa_sequences=1000,
        output_format="a3m",
        save_path=output_dir / "ca2_alignment.a3m"
    )
    print(f"✅ MSA saved to: {msa_path}")
    
    # Step 3: Load MSA content
    with open(msa_path, "r") as f:
        msa_content = f.read()
    
    # Step 4: Create custom prediction request
    msa_record = AlignmentFileRecord(
        alignment=msa_content,
        format="a3m",
        rank=0
    )
    
    protein = Polymer(
        id="A",
        molecule_type="protein",
        sequence=PROTEIN_SEQUENCE,
        msa={"colabfold": {"a3m": msa_record}}
    )
    
    ligand = Ligand(
        id="DOR",
        smiles=DORZOLAMIDE_SMILES,
        predict_affinity=True
    )
    
    request = PredictionRequest(
        polymers=[protein],
        ligands=[ligand],
        recycling_steps=5,
        sampling_steps=100,
        sampling_steps_affinity=300,
        diffusion_samples_affinity=8,
        affinity_mw_correction=True
    )
    
    print("🔮 Predicting structure and affinity...")
    result = await client.predict(
        request,
        save_structures=True,
        output_dir=output_dir / "manual_workflow"
    )
    
    print(f"✅ Structure confidence: {result.confidence_scores[0]:.3f}")
    
    if result.affinities and "DOR" in result.affinities:
        aff = result.affinities["DOR"]
        print(f"📊 Affinity predictions:")
        print(f"   - pIC50: {aff.affinity_pic50[0]:.3f}")
        print(f"   - IC50: {aff.affinity_ic50[0]:.3f} nM")
        print(f"   - Binding probability: {aff.affinity_probability_binary[0]:.3f}")


async def main():
    """Run all examples."""
    print("🧬 MSA-Guided Protein-Ligand Affinity Prediction")
    print("=" * 60)
    print(f"Protein: Human Carbonic Anhydrase II ({len(PROTEIN_SEQUENCE)} residues)")
    print(f"Ligands: Dorzolamide and Acetazolamide")
    
    # Create output directory
    output_dir = Path("msa_affinity_results")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    try:
        # Run examples
        await predict_without_msa(client, output_dir)
        await predict_with_msa_search(client, output_dir)
        await manual_msa_then_affinity(client, output_dir)
        await predict_with_existing_msa(client, output_dir)
        
        print("\n✅ All predictions completed!")
        print(f"📁 Results saved to: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
