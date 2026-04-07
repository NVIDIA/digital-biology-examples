# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""Virtual screening CLI command."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
from rich.table import Table

from . import cli, console, print_success, print_error, print_info, print_warning


def create_client(ctx):
    """Delegate to the package-level create_client (patchable by tests)."""
    return sys.modules[__package__].create_client(ctx)


@cli.command(name='screen')
@click.argument('target_sequence', type=str)
@click.argument('compounds_file', type=click.Path(exists=True))
@click.option('--target-name', default='Target', help='Name of the target protein')
@click.option('--output-dir', '-o', type=click.Path(), help='Output directory for results')
@click.option('--no-affinity', is_flag=True, help='Disable affinity prediction')
@click.option('--pocket-residues', type=str, help='Comma-separated list of pocket residue indices')
@click.option('--recycling-steps', type=click.IntRange(1, 10), default=2, help='Number of recycling steps (1-10)')
@click.option('--sampling-steps', type=click.IntRange(10, 1000), default=30, help='Number of sampling steps (10-1000)')
@click.option('--max-workers', type=int, default=4, help='Maximum parallel workers')
@click.option('--batch-size', type=int, help='Process compounds in batches')
@click.option('--save-structures/--no-save-structures', default=True, help='Save structure files')
@click.pass_context
def screen(ctx, target_sequence, compounds_file, target_name, output_dir, no_affinity,
           pocket_residues, recycling_steps, sampling_steps, 
           max_workers, batch_size, save_structures):
    """Run virtual screening campaign against a protein target.
    
    Examples:
        boltz2 screen "MKTVRQERLK..." compounds.csv -o results/
        boltz2 screen target.fasta library.json --pocket-residues "10,15,20,25"
    """
    client = create_client(ctx)
    
    # Import here to avoid circular imports
    from ..virtual_screening import VirtualScreening, CompoundLibrary
    
    console.print(f"\n[bold cyan]🧬 Virtual Screening Campaign[/bold cyan]")
    console.print(f"Target: {target_name}")
    console.print(f"Compounds: {compounds_file}")
    
    # Load target sequence if file
    if Path(target_sequence).exists():
        with open(target_sequence, 'r') as f:
            lines = f.readlines()
            target_sequence = ''.join(line.strip() for line in lines if not line.startswith('>'))
    
    console.print(f"Target length: {len(target_sequence)} residues")
    
    # Parse pocket residues
    pocket_residues_list = None
    if pocket_residues:
        pocket_residues_list = [int(x.strip()) for x in pocket_residues.split(',')]
        console.print(f"Pocket constraint: {len(pocket_residues_list)} residues")
    
    # Create screener
    screener = VirtualScreening(client=client, max_workers=max_workers)
    
    # Progress callback
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task_id = None
        def update_progress(completed, total):
            nonlocal task_id
            if task_id is None:
                task_id = progress.add_task("Screening compounds", total=total)
            progress.update(task_id, completed=completed)
        
        try:
            # Run screening
            result = screener.screen(
                target_sequence=target_sequence,
                compound_library=compounds_file,
                target_name=target_name,
                predict_affinity=not no_affinity,
                pocket_residues=pocket_residues_list,
                recycling_steps=recycling_steps,
                sampling_steps=sampling_steps,
                batch_size=batch_size,
                progress_callback=update_progress
            )
            
            # Display results
            console.print(f"\n[bold green]✅ Screening completed![/bold green]")
            console.print(f"Total compounds: {len(result.results)}")
            console.print(f"Successful: {len(result.successful_results)} ({result.success_rate:.1%})")
            console.print(f"Duration: {result.duration_seconds:.1f} seconds")
            
            # Show top hits
            if result.successful_results and not no_affinity:
                top_hits = result.get_top_hits(n=5)
                if not top_hits.empty:
                    console.print("\n[bold]Top 5 Hits by pIC50:[/bold]")
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Compound", style="cyan")
                    table.add_column("pIC50", justify="right")
                    table.add_column("IC50 (nM)", justify="right")
                    table.add_column("Binding Prob", justify="right")
                    
                    for _, hit in top_hits.iterrows():
                        table.add_row(
                            hit['compound_name'],
                            f"{hit['predicted_pic50']:.2f}",
                            f"{hit['predicted_ic50_nm']:.1f}",
                            f"{hit['binding_probability']:.1%}"
                        )
                    
                    console.print(table)
            
            # Save results
            if output_dir:
                saved = result.save_results(output_dir, save_structures=save_structures)
                console.print(f"\n[bold]Results saved to {output_dir}:[/bold]")
                for key, path in saved.items():
                    console.print(f"  - {key}: {path}")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()


