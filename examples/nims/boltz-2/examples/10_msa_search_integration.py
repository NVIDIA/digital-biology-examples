#!/usr/bin/env python3
"""
10_msa_search_integration.py

Demonstrates GPU-accelerated MSA Search NIM integration with Boltz-2.
This example shows how to use NVIDIA's MSA Search NIM to generate
high-quality multiple sequence alignments for improved structure predictions.

Key Features:
- MSA Search NIM configuration (NVIDIA-hosted or local)
- Automated MSA generation from protein sequences
- Multiple output format support (a3m, FASTA, CSV, Stockholm)
- Direct integration with Boltz-2 structure prediction
- Batch MSA search for multiple sequences
"""

import asyncio
from pathlib import Path
from boltz2_client import Boltz2Client

# Example protein sequences
PROTEIN_SEQUENCES = {
    # Human CDK2 kinase domain
    "CDK2": (
        "MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKISPEFLNKRFQQLRELIK"
        "LRHPNIVSLQKVILDTWQRAKDEGLPSTAIREISLLKELNHPNIVKLLDVIH"
        "TENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVL"
        "HRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCK"
        "YYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFRIFRTLGTPDEVVWPGVT"
        "SMPDYKPSFPKWARQDFSKVVPPLDEDGRSLLSQMLHYDPNKRISAKAALAHP"
        "FFQDVTKPVPHLRL"
    ),
    
    # Small ubiquitin
    "Ubiquitin": (
        "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDG"
        "RTLSDYNIQKESTLHLVLRLRGG"
    ),
    
    # Lysozyme
    "Lysozyme": (
        "KVFERCELARTLKRLGMDGYRGISLANWMCLAKWESGYNTRATNYNAGDRST"
        "DYGIFQINSRYWCNDGKTPGAVNACHLSCSALLQDNIADAVACAKRVVRDPQG"
        "IRAWVAWRNRCQNRDVRQYVQGCGV"
    )
}


async def configure_msa_search(client: Boltz2Client, endpoint_type: str = "local"):
    """Configure MSA Search NIM integration."""
    print("🔧 Configuring MSA Search NIM")
    print("-" * 50)
    
    if endpoint_type == "nvidia_hosted":
        # NVIDIA-hosted endpoint
        msa_endpoint = "https://health.api.nvidia.com/v1/biology/nvidia/msa-search"
        print("📡 Using NVIDIA-hosted MSA Search NIM")
        print("   (Requires NVIDIA_API_KEY environment variable)")
    else:
        # Local deployment
        msa_endpoint = "http://localhost:8001"
        print("💻 Using local MSA Search NIM deployment")
        print(f"   Endpoint: {msa_endpoint}")
    
    # Configure MSA search
    client.configure_msa_search(
        msa_endpoint_url=msa_endpoint,
        timeout=300,
        max_retries=3
    )
    
    # Check available databases
    try:
        databases = await client.get_msa_databases()
        print(f"📚 Available databases: {', '.join(databases)}")
    except Exception as e:
        print(f"⚠️  Could not fetch database list: {e}")
        print("   Using default: Uniref30_2302, colabfold_envdb_202108")


async def search_and_save_msa(
    client: Boltz2Client,
    protein_name: str,
    sequence: str,
    output_dir: Path
) -> Path:
    """Search MSA and save in multiple formats."""
    print(f"\n🔍 Searching MSA for {protein_name}")
    print(f"   Sequence length: {len(sequence)} residues")
    
    # Search and save in A3M format
    msa_path = await client.search_msa(
        sequence=sequence,
        databases=["Uniref30_2302", "colabfold_envdb_202108"],
        max_msa_sequences=500,
        e_value=10.0,
        output_format="a3m",
        save_path=output_dir / f"{protein_name}_msa.a3m"
    )
    
    print(f"✅ MSA saved to: {msa_path}")
    
    # Also save in FASTA format for visualization
    fasta_path = await client.search_msa(
        sequence=sequence,
        databases=["Uniref30_2302", "colabfold_envdb_202108"],
        max_msa_sequences=100,  # Fewer sequences for FASTA
        e_value=1.0,  # Stricter threshold
        output_format="fasta",
        save_path=output_dir / f"{protein_name}_msa.fasta"
    )
    
    print(f"📄 FASTA format: {fasta_path}")
    
    return msa_path


async def predict_with_automatic_msa(
    client: Boltz2Client,
    protein_name: str,
    sequence: str,
    output_dir: Path
):
    """Predict structure with automatic MSA search."""
    print(f"\n🧬 Predicting structure with MSA search for {protein_name}")
    print("-" * 60)
    
    # One-step MSA search and structure prediction
    result = await client.predict_with_msa_search(
        sequence=sequence,
        polymer_id="A",
        databases=["Uniref30_2302"],
        max_msa_sequences=1000,
        e_value=10.0,
        recycling_steps=3,
        sampling_steps=50,
        diffusion_samples=1
    )
    
    # Save structure
    structure_path = output_dir / f"{protein_name}_with_msa.cif"
    structure_path.write_text(result.structures[0].structure)
    
    confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
    print(f"✅ Structure predicted with MSA")
    print(f"📊 Confidence score: {confidence:.3f}")
    print(f"💾 Structure saved to: {structure_path}")
    
    return result


async def compare_with_without_msa(
    client: Boltz2Client,
    protein_name: str,
    sequence: str,
    output_dir: Path
):
    """Compare predictions with and without MSA."""
    print(f"\n📊 Comparing predictions for {protein_name}")
    print("=" * 60)
    
    # Predict without MSA
    print("\n1️⃣ Prediction WITHOUT MSA:")
    result_no_msa = await client.predict_protein_structure(
        sequence=sequence,
        recycling_steps=3,
        sampling_steps=50
    )
    
    confidence_no_msa = result_no_msa.confidence_scores[0] if result_no_msa.confidence_scores else 0.0
    print(f"   Confidence: {confidence_no_msa:.3f}")
    
    # Save structure without MSA
    no_msa_path = output_dir / f"{protein_name}_no_msa.cif"
    no_msa_path.write_text(result_no_msa.structures[0].structure)
    
    # Predict with MSA
    print("\n2️⃣ Prediction WITH MSA search:")
    result_with_msa = await client.predict_with_msa_search(
        sequence=sequence,
        databases=["Uniref30_2302", "colabfold_envdb_202108"],
            max_msa_sequences=1000,
        recycling_steps=3,
        sampling_steps=50
    )
    
    confidence_with_msa = result_with_msa.confidence_scores[0] if result_with_msa.confidence_scores else 0.0
    print(f"   Confidence: {confidence_with_msa:.3f}")
    
    # Save structure with MSA
    with_msa_path = output_dir / f"{protein_name}_with_msa.cif"
    with_msa_path.write_text(result_with_msa.structures[0].structure)
    
    # Analysis
    print("\n📈 Analysis:")
    if confidence_with_msa > confidence_no_msa:
        improvement = ((confidence_with_msa - confidence_no_msa) / confidence_no_msa) * 100
        print(f"   🎉 MSA improved confidence by {improvement:.1f}%")
    else:
        print(f"   ℹ️  Similar confidence with and without MSA")
    
    print(f"\n💾 Structures saved:")
    print(f"   Without MSA: {no_msa_path}")
    print(f"   With MSA:    {with_msa_path}")


async def batch_msa_search_demo(
    client: Boltz2Client,
    sequences: dict,
    output_dir: Path
):
    """Demonstrate batch MSA search for multiple sequences."""
    print("\n🔄 Batch MSA Search")
    print("=" * 50)
    
    msa_dir = output_dir / "batch_msa"
    msa_dir.mkdir(exist_ok=True)
    
    # Perform batch search
    print(f"Searching MSA for {len(sequences)} sequences...")
    
    msa_paths = await client.batch_msa_search(
        sequences=sequences,
        output_dir=msa_dir,
        output_format="a3m",
        databases=["Uniref30_2302"],
        max_msa_sequences=500,
        e_value=10.0
    )
    
    print(f"\n✅ Batch search completed!")
    for seq_id, path in msa_paths.items():
        if path:
            # Count sequences in MSA
            msa_content = path.read_text()
            seq_count = sum(1 for line in msa_content.split('\n') if line.startswith('>'))
            print(f"   {seq_id}: {seq_count} sequences found → {path.name}")


async def explore_msa_formats(
    client: Boltz2Client,
    protein_name: str,
    sequence: str,
    output_dir: Path
):
    """Export MSA in different formats for various use cases."""
    print(f"\n📁 Exporting MSA in multiple formats for {protein_name}")
    print("-" * 50)
    
    formats_dir = output_dir / "formats"
    formats_dir.mkdir(exist_ok=True)
    
    # Export in different formats
    formats = {
        "a3m": "A3M format (for structure prediction)",
        "fasta": "FASTA format (for alignment viewers)",
        "csv": "CSV format (for data analysis)",
        "sto": "Stockholm format (for conservation analysis)"
    }
    
    for fmt, description in formats.items():
        print(f"\n📄 {description}:")
        
        path = await client.search_msa(
            sequence=sequence,
            databases=["Uniref30_2302"],
            max_msa_sequences=100,
            e_value=1.0,
            output_format=fmt,
            save_path=formats_dir / f"{protein_name}_msa.{fmt}"
        )
        
        print(f"   Saved to: {path}")


async def main():
    """Main execution function."""
    print("🚀 MSA Search NIM Integration Demo")
    print("=" * 60)
    print("This demo shows how to use GPU-accelerated MSA Search")
    print("with Boltz-2 for enhanced protein structure prediction.\n")
    
    # Create output directory
    output_dir = Path("msa_search_results")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize Boltz-2 client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    try:
        # Test Boltz-2 connection
        health = await client.health_check()
        print(f"✅ Boltz-2 server status: {health.status}")
        
        # Configure MSA Search
        # Change to "nvidia_hosted" to use NVIDIA's endpoint
        await configure_msa_search(client, endpoint_type="local")
        
        # Demo 1: Search and save MSA
        print("\n" + "="*60)
        print("Demo 1: MSA Search and Export")
        print("="*60)
        
        msa_path = await search_and_save_msa(
            client,
            "CDK2",
            PROTEIN_SEQUENCES["CDK2"],
            output_dir
        )
        
        # Demo 2: Direct MSA search + structure prediction
        print("\n" + "="*60)
        print("Demo 2: Automated MSA Search + Structure Prediction")
        print("="*60)
        
        await predict_with_automatic_msa(
            client,
            "Ubiquitin",
            PROTEIN_SEQUENCES["Ubiquitin"],
            output_dir
        )
        
        # Demo 3: Compare with/without MSA
        print("\n" + "="*60)
        print("Demo 3: Impact of MSA on Prediction Quality")
        print("="*60)
        
        await compare_with_without_msa(
            client,
            "Lysozyme",
            PROTEIN_SEQUENCES["Lysozyme"],
            output_dir
        )
        
        # Demo 4: Batch MSA search
        print("\n" + "="*60)
        print("Demo 4: Batch MSA Search")
        print("="*60)
        
        await batch_msa_search_demo(
            client,
            PROTEIN_SEQUENCES,
            output_dir
        )
        
        # Demo 5: Multiple formats
        print("\n" + "="*60)
        print("Demo 5: MSA Export Formats")
        print("="*60)
        
        await explore_msa_formats(
            client,
            "CDK2",
            PROTEIN_SEQUENCES["CDK2"],
            output_dir
        )
        
        print("\n" + "="*60)
        print("🎉 MSA Search Integration Demo Complete!")
        print("="*60)
        print(f"\n📁 Results saved in: {output_dir}")
        print("\n💡 Tips:")
        print("   - Use NVIDIA-hosted endpoint for production")
        print("   - Adjust max_msa_sequences based on protein size")
        print("   - Try different databases for specific proteins")
        print("   - Monitor MSA quality with e_value thresholds")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure Boltz-2 server is running")
        print("   2. Ensure MSA Search NIM is deployed")
        print("   3. Check NVIDIA_API_KEY for hosted endpoints")
        print("   4. Verify network connectivity")


if __name__ == "__main__":
    asyncio.run(main())
