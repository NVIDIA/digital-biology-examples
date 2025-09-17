#!/usr/bin/env python3
"""
Multi-Endpoint Virtual Screening Example

This example demonstrates how to use multiple Boltz-2 NIM endpoints
for parallel virtual screening with load balancing.
"""

import asyncio
import os
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    VirtualScreening,
    CompoundLibrary
)

# Initialize console for pretty output
console = Console()


async def run_multi_endpoint_screening():
    """Run virtual screening using multiple endpoints."""
    
    # Define your target protein sequence
    TARGET_SEQUENCE = """
    MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
    KQDQQPQGDSGSSQFPTDAASSAFQGLMEGFAPDMKCGVCITWIYAAFQKVAAEFADSEPQLISG
    YAFEHFHDERPGGVAPLPLGVGNVLSRSQNRVTVWDVKRESCVQEAYGVGVDDVKDICEELAEEL
    AVEPVTDSDVDIDGVNHMFVRVQRQIEQNPAQDAGTYISRAKRKLGSRPFRSIEIEIERPVTTTI
    """.replace('\n', '').replace(' ', '')
    
    # Define your compound library
    compounds = [
        {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
        {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
        {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1"},
        {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"},
        {"name": "Naproxen", "smiles": "COC1=CC=C2C=C(C=CC2=C1)C(C)C(=O)O"},
    ]
    
    # Configure multiple endpoints
    # Replace these with your actual Boltz-2 NIM endpoints
    endpoints = [
        # Local endpoints on different ports
        EndpointConfig(base_url="http://localhost:8000", weight=1.0),
        EndpointConfig(base_url="http://localhost:8001", weight=1.0),
        EndpointConfig(base_url="http://localhost:8002", weight=1.0),
        
        # You can also mix local and remote endpoints
        # EndpointConfig(
        #     base_url="http://gpu-server-1:8000",
        #     weight=2.0  # Give this server more weight if it's more powerful
        # ),
        # EndpointConfig(
        #     base_url="http://gpu-server-2:8000", 
        #     weight=1.5
        # ),
        
        # Or use NVIDIA hosted endpoints
        # EndpointConfig(
        #     base_url="https://health.api.nvidia.com",
        #     api_key=os.getenv("NVIDIA_API_KEY"),
        #     endpoint_type="nvidia_hosted",
        #     weight=1.0
        # ),
    ]
    
    # Create multi-endpoint client with load balancing
    console.print("[bold blue]Initializing multi-endpoint client...[/bold blue]")
    
    multi_client = MultiEndpointClient(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.LEAST_LOADED,  # Use least-loaded balancing
        health_check_interval=30.0,  # Check health every 30 seconds
        timeout=300.0
    )
    
    # Print initial status
    console.print("\n[bold]Endpoint Status:[/bold]")
    multi_client.print_status()
    
    # Create virtual screening instance with multi-endpoint client
    vs = VirtualScreening(client=multi_client)
    
    # Create compound library
    library = CompoundLibrary(compounds)
    
    # Define progress callback
    def progress_callback(completed: int, total: int):
        console.print(f"Progress: {completed}/{total} compounds screened")
    
    # Run screening with progress tracking
    console.print(f"\n[bold green]Starting virtual screening of {len(compounds)} compounds...[/bold green]")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Screening compounds...", total=len(compounds))
        
        def update_progress(completed: int, total: int):
            progress.update(task, completed=completed)
        
        result = await vs.screen(
            target_sequence=TARGET_SEQUENCE,
            compound_library=library,
            target_name="Example Target",
            predict_affinity=True,
            recycling_steps=2,
            sampling_steps=30,
            diffusion_samples=1,
            sampling_steps_affinity=100,
            diffusion_samples_affinity=3,
            progress_callback=update_progress
        )
    
    # Print results
    console.print(f"\n[bold]Screening completed in {result.duration_seconds:.1f} seconds[/bold]")
    console.print(f"Success rate: {result.success_rate:.1%}")
    
    # Show endpoint statistics after screening
    console.print("\n[bold]Final Endpoint Statistics:[/bold]")
    multi_client.print_status()
    
    # Display top hits
    console.print("\n[bold]Top Hits by Predicted pIC50:[/bold]")
    top_hits = result.get_top_hits(n=3)
    for _, hit in top_hits.iterrows():
        console.print(
            f"  {hit['compound_name']}: "
            f"pIC50={hit['predicted_pic50']:.2f}, "
            f"IC50={hit['predicted_ic50_nm']:.1f} nM, "
            f"Binding Probability={hit['binding_probability']:.1%}"
        )
    
    # Save results
    output_dir = Path("multi_endpoint_results")
    saved_files = result.save_results(output_dir, save_structures=True)
    console.print(f"\n[green]Results saved to {output_dir}[/green]")
    
    # Clean up
    await multi_client.close()


def run_sync_example():
    """Synchronous example using multiple endpoints."""
    from boltz2_client import Boltz2SyncClient
    
    # Configure endpoints
    endpoints = [
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
    ]
    
    # Create synchronous multi-endpoint client
    multi_client = MultiEndpointClient(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.ROUND_ROBIN,
        is_async=False  # Use synchronous mode
    )
    
    # Create virtual screening with sync client
    vs = VirtualScreening(client=multi_client)
    
    # Define small test library
    compounds = [
        {"name": "Test1", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
        {"name": "Test2", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
    ]
    
    # Run screening
    result = vs.screen(
        target_sequence="MKTVRQERLKSIVRILERSKEPVSGAQ",
        compound_library=compounds,
        predict_affinity=False,  # Faster without affinity
        recycling_steps=1,
        sampling_steps=10,
    )
    
    console.print(f"Screened {len(compounds)} compounds in {result.duration_seconds:.1f}s")
    multi_client.print_status()


if __name__ == "__main__":
    # Choose between async and sync examples
    console.print("[bold]Multi-Endpoint Virtual Screening Example[/bold]\n")
    
    try:
        # Run async example (recommended for better performance)
        asyncio.run(run_multi_endpoint_screening())
        
        # Or run sync example
        # run_sync_example()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Screening interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise