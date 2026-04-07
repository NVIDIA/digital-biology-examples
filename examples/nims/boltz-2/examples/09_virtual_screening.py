#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Example 9: Virtual Screening

This example demonstrates how to run virtual screening campaigns using
the high-level VirtualScreening API with minimal code.
"""

import asyncio
from pathlib import Path
from boltz2_client import VirtualScreening, CompoundLibrary, quick_screen

# BTK kinase domain sequence (example target)
BTK_SEQUENCE = """VVALYDYMPMNANDLQLRKGDEYFILEESNLPWWRARDKNGQEGYIPSNYVTEAEDSIEMYEWY
SKHMNGSDDVVALAHGKRSPTFQELVQAAERETGRHGSEWLKEKLNQMRFIFDLRA""".replace("\n", "")

# Example compound library
COMPOUNDS = [
    {
        "name": "Ibrutinib",
        "smiles": "CC#CC(=O)N1CCCC(C1)n2c3c(c(n2)C4CC4)c(ncn3)Nc5ccc(c(c5)F)Oc6ccccn6",
        "metadata": {"type": "BTK inhibitor", "known_pic50": 8.7}
    },
    {
        "name": "Zanubrutinib",
        "smiles": "CC(C)(O)C#CC(=O)n1cc(c2c1cccc2)C3CCN(CC3)c4nc5c(c(n4)c6ccccc6)n(cn5)C7CC7",
        "metadata": {"type": "BTK inhibitor", "known_pic50": 8.9}
    },
    {
        "name": "Aspirin",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        "metadata": {"type": "Control", "known_pic50": 3.5}
    }
]


def example_minimal():
    """Minimal virtual screening example."""
    print("=== Example 1: Minimal Virtual Screening ===\n")
    
    # Quick screen with minimal code
    result = quick_screen(
        target_sequence=BTK_SEQUENCE,
        compounds=COMPOUNDS,
        target_name="BTK Kinase",
        output_dir="screening_results_minimal"
    )
    
    print(f"\nScreened {len(result.results)} compounds")
    print(f"Success rate: {result.success_rate:.1%}")
    
    # Show top hits
    top_hits = result.get_top_hits(n=3)
    print("\nTop hits:")
    for _, hit in top_hits.iterrows():
        print(f"  {hit['compound_name']}: pIC50={hit['predicted_pic50']:.2f}")


def example_advanced():
    """Advanced virtual screening with pocket constraints."""
    print("\n=== Example 2: Advanced Virtual Screening ===\n")
    
    # Create screener with custom client
    screener = VirtualScreening(max_workers=2)
    
    # Define binding pocket (example residues near ATP site)
    pocket_residues = [10, 15, 20, 25, 30, 35, 40]
    
    # Run screening with pocket constraints
    result = screener.screen(
        target_sequence=BTK_SEQUENCE,
        compound_library=COMPOUNDS,
        target_name="BTK Kinase",
        predict_affinity=True,
        pocket_residues=pocket_residues,
        recycling_steps=2,
        sampling_steps=40,
        sampling_steps_affinity=100,
        diffusion_samples_affinity=3
    )
    
    print(f"Screening completed in {result.duration_seconds:.1f} seconds")
    
    # Analyze by compound type
    stats = result.get_statistics_by_group(group_by="compound_type")
    if not stats.empty:
        print("\nStatistics by compound type:")
        print(stats)


def example_csv_library():
    """Example using CSV compound library."""
    print("\n=== Example 3: CSV Compound Library ===\n")
    
    # Create example CSV file
    csv_path = Path("example_compounds.csv")
    with open(csv_path, 'w') as f:
        f.write("name,smiles,type,source\n")
        f.write("Ibrutinib,CC#CC(=O)N1CCCC(C1)n2c3c(c(n2)C4CC4)c(ncn3)Nc5ccc(c(c5)F)Oc6ccccn6,BTK inhibitor,FDA\n")
        f.write("Aspirin,CC(=O)OC1=CC=CC=C1C(=O)O,Control,OTC\n")
    
    print(f"Created example CSV: {csv_path}")
    
    # Load and screen
    library = CompoundLibrary.from_csv(csv_path)
    print(f"Loaded {len(library)} compounds from CSV")
    
    # Run screening
    screener = VirtualScreening()
    result = screener.screen(
        target_sequence=BTK_SEQUENCE,
        compound_library=library,
        target_name="BTK Kinase"
    )
    
    # Save full results
    saved = result.save_results("screening_results_csv")
    print(f"\nResults saved to:")
    for key, path in saved.items():
        print(f"  - {key}: {path}")
    
    # Clean up
    csv_path.unlink()


async def example_async():
    """Example using async client for better performance."""
    print("\n=== Example 4: Async Virtual Screening ===\n")
    
    from boltz2_client import Boltz2Client
    
    # Create async client
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Create screener with async client
    screener = VirtualScreening(client=client, max_workers=4)
    
    # Large compound library for parallel processing
    large_library = COMPOUNDS * 3  # Duplicate for demo
    
    # Progress tracking
    def progress_callback(completed, total):
        print(f"\rProgress: {completed}/{total} ({completed/total:.1%})", end="")
    
    # Run async screening
    result = screener.screen(
        target_sequence=BTK_SEQUENCE,
        compound_library=large_library,
        target_name="BTK Kinase",
        progress_callback=progress_callback
    )
    
    print(f"\n\nAsync screening completed!")
    print(f"Total time: {result.duration_seconds:.1f} seconds")
    print(f"Time per compound: {result.duration_seconds/len(large_library):.1f} seconds")


def example_batch_processing():
    """Example with batch processing for large libraries."""
    print("\n=== Example 5: Batch Processing ===\n")
    
    # Create larger library
    large_library = []
    for i in range(20):
        large_library.append({
            "name": f"Compound_{i}",
            "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",  # Using aspirin as placeholder
            "metadata": {"batch": i // 5}
        })
    
    # Screen in batches
    screener = VirtualScreening(max_workers=2)
    result = screener.screen(
        target_sequence=BTK_SEQUENCE,
        compound_library=large_library,
        target_name="BTK Kinase",
        predict_affinity=False,  # Faster without affinity
        batch_size=5,  # Process 5 at a time
        sampling_steps=20  # Faster predictions
    )
    
    print(f"Screened {len(result.results)} compounds in batches")
    print(f"Success rate: {result.success_rate:.1%}")
    
    # Group results by batch
    df = result.to_dataframe()
    if not df.empty:
        batch_stats = df.groupby('compound_batch')['structure_confidence'].agg(['mean', 'count'])
        print("\nResults by batch:")
        print(batch_stats)


def main():
    """Run all examples."""
    print("🧬 Boltz-2 Virtual Screening Examples\n")
    
    # Check service health first
    from boltz2_client import Boltz2SyncClient
    client = Boltz2SyncClient()
    try:
        health = client.health_check()
        print(f"✅ Service status: {health.status}\n")
    except Exception as e:
        print(f"❌ Service health check failed: {e}")
        print("Make sure Boltz-2 service is running at http://localhost:8000")
        return
    
    # Run examples
    example_minimal()
    example_advanced()
    example_csv_library()
    
    # Run async example
    asyncio.run(example_async())
    
    example_batch_processing()
    
    print("\n✨ All examples completed!")


if __name__ == "__main__":
    main() 