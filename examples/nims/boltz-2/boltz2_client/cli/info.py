# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""Health, metadata, and examples commands."""

import asyncio
import sys

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import cli, console, print_success, print_error, print_info, print_warning


def create_client(ctx):
    """Delegate to the package-level create_client (patchable by tests)."""
    return sys.modules[__package__].create_client(ctx)



@cli.command()
@click.pass_context
def health(ctx):
    """Check the health status of the Boltz-2 service."""
    async def check_health():
        try:
            # Handle NVIDIA hosted endpoints specially
            if ctx.obj['endpoint_type'] == 'nvidia_hosted':
                print_warning("Health checks are not supported on NVIDIA hosted endpoints")
                print_info("NVIDIA hosted endpoints use managed infrastructure with built-in health monitoring")
                print_success("NVIDIA endpoint is considered healthy if you can make predictions")
                
                if ctx.obj['verbose']:
                    console.print("\nService Info:", style="bold")
                    console.print(f"  Base URL: {ctx.obj['base_url']}")
                    console.print(f"  Endpoint Type: {ctx.obj['endpoint_type']}")
                    console.print(f"  API Key: {'✅ Set via environment' if ctx.obj.get('api_key') is None else '✅ Provided via CLI'}")
                    console.print(f"  Note: To verify connectivity, try running a prediction command")
                    
                print_info("To test connectivity, try: boltz2 --endpoint-type nvidia_hosted protein \"SEQUENCE\" --no-save")
            else:
                # Local endpoint - use normal health check
                client = create_client(ctx)
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Checking service health...", total=None)
                    
                    health_status = await client.health_check()
                    progress.remove_task(task)
                    
                    if health_status.status == "healthy":
                        print_success(f"Service is healthy (Status: {health_status.status})")
                    else:
                        print_warning(f"Service status: {health_status.status}")
                    
                    if ctx.obj['verbose'] and health_status.details:
                        console.print("\nDetails:", style="bold")
                        for key, value in health_status.details.items():
                            console.print(f"  {key}: {value}")
                        
        except Exception as e:
            if ctx.obj['endpoint_type'] not in ('nvidia_hosted',):
                print_error(f"Health check failed: {e}")
                raise click.Abort()
    
    asyncio.run(check_health())


@cli.command()
@click.pass_context
def metadata(ctx):
    """Get service metadata and model information."""
    async def get_metadata():
        try:
            if ctx.obj.get('endpoint_type') == 'sagemaker':
                print_error("Metadata endpoint is not available for SageMaker endpoints.")
                print_error("Use 'boltz2 ... health' to check SageMaker endpoint status.")
                raise click.Abort()

            client = create_client(ctx)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Fetching service metadata...", total=None)
                
                metadata = await client.get_service_metadata()
                progress.remove_task(task)
                
                print_success("Service metadata retrieved successfully")
                
                # Display metadata in a nice table
                table = Table(title="Service Metadata")
                table.add_column("Property", style="cyan", no_wrap=True)
                table.add_column("Value", style="magenta")
                
                table.add_row("Version", metadata.version)
                table.add_row("Repository Override", metadata.repository_override)
                table.add_row("Asset Info", ", ".join(metadata.assetInfo))
                
                if metadata.modelInfo:
                    for i, model in enumerate(metadata.modelInfo):
                        table.add_row(f"Model {i+1} URL", model.modelUrl)
                        table.add_row(f"Model {i+1} Name", model.shortName)
                
                console.print(table)
                
        except click.Abort:
            raise
        except Exception as e:
            print_error(f"Failed to get metadata: {e}")
            raise click.Abort()
    
    asyncio.run(get_metadata())


@cli.command()
@click.pass_context
def examples(ctx):
    """Show example configurations and usage patterns."""
    console.print("\n[bold cyan]Boltz-2 Python Client Examples[/bold cyan]\n")
    
    # Basic protein folding
    console.print("[bold]1. Basic Protein Folding[/bold]")
    console.print("boltz2 protein \"MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG\"")
    console.print()
    
    # Protein-ligand complex
    console.print("[bold]2. Protein-Ligand Complex[/bold]")
    console.print("boltz2 ligand \"PROTEIN_SEQUENCE\" --smiles \"CC(=O)OC1=CC=CC=C1C(=O)O\"")
    console.print()
    
    # Covalent complex
    console.print("[bold]3. Covalent Complex[/bold]")
    console.print("boltz2 covalent \"PROTEIN_SEQUENCE\" --ccd U4U --bond A:12:SG:LIG:C22")
    console.print()
    
    # DNA-protein complex
    console.print("[bold]4. DNA-Protein Complex[/bold]")
    console.print("boltz2 dna-protein --protein-sequences \"SEQ1,SEQ2\" --dna-sequences \"ATCG,GCTA\"")
    console.print()
    
    # YAML configuration examples
    console.print("[bold]5. YAML Configuration Examples[/bold]")
    
    # Basic YAML
    console.print("\n[bold yellow]Basic Protein-Ligand YAML:[/bold yellow]")
    yaml_example = """version: 1
sequences:
  - protein:
      id: A
      sequence: "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
  - ligand:
      id: B
      smiles: "CC(=O)O"
"""
    console.print(f"[dim]{yaml_example}[/dim]")
    
    # Affinity prediction YAML
    console.print("[bold yellow]Affinity Prediction YAML:[/bold yellow]")
    affinity_example = """version: 1
sequences:
  - protein:
      id: A
      sequence: "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
      msa: "protein_A.a3m"  # optional MSA file
  - ligand:
      id: B
      smiles: "N[C@@H](Cc1ccc(O)cc1)C(=O)O"
properties:
  affinity:
    binder: B
"""
    console.print(f"[dim]{affinity_example}[/dim]")
    
    # YAML usage
    console.print("[bold]YAML Usage:[/bold]")
    console.print("boltz2 yaml protein_ligand.yaml")
    console.print("boltz2 yaml my_affinity_config.yaml --recycling-steps 5 --diffusion-samples 3")
    console.print()
    
    # Advanced JSON config
    console.print("[bold]6. Advanced JSON Configuration[/bold]")
    json_example = """{
  "polymers": [
    {
      "id": "A",
      "molecule_type": "protein",
      "sequence": "MKTVRQERLK..."
    }
  ],
  "ligands": [
    {
      "id": "LIG", 
      "smiles": "CC(=O)O"
    }
  ],
  "recycling_steps": 5,
  "sampling_steps": 100,
  "diffusion_samples": 3,
  "step_scale": 2.0
}"""
    console.print(f"[dim]{json_example}[/dim]")
    console.print("boltz2 advanced --config-file advanced_config.json")
    console.print()
    
    # Endpoint configuration
    console.print("[bold]7. Endpoint Configuration[/bold]")
    console.print("# Local endpoint (default)")
    console.print("boltz2 --base-url http://localhost:8000 protein \"SEQUENCE\"")
    console.print()
    console.print("# NVIDIA hosted endpoint")
    console.print("export NVIDIA_API_KEY=your_api_key")
    console.print("boltz2 --base-url https://health.api.nvidia.com --endpoint-type nvidia_hosted protein \"SEQUENCE\"")
    console.print()

