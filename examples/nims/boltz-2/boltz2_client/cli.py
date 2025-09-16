
# ---------------------------------------------------------------
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Command-line interface for Boltz-2 Python Client.

This module provides a comprehensive CLI for all Boltz-2 features including
protein structure prediction, protein-ligand complexes, covalent complexes,
DNA-protein complexes, and advanced parameter control.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
from rich.panel import Panel
from rich.text import Text
import yaml as pyyaml

from .client import Boltz2Client, Boltz2SyncClient, EndpointType
from .models import (
    PredictionRequest, Polymer, Ligand, PocketConstraint, BondConstraint, 
    Atom, AlignmentFileRecord, AlignmentFormat
)
from .exceptions import Boltz2ClientError


console = Console()


def print_success(message: str):
    """Print success message."""
    console.print(f"✅ {message}", style="green")


def print_error(message: str):
    """Print error message."""
    console.print(f"❌ {message}", style="red")


def print_info(message: str):
    """Print info message."""
    console.print(f"ℹ️ {message}", style="blue")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"⚠️ {message}", style="yellow")


@click.group()
@click.option('--base-url', default='http://localhost:8000', help='Service base URL (can be comma-separated for multiple endpoints)')
@click.option('--api-key', help='API key for NVIDIA hosted endpoints (or set NVIDIA_API_KEY env var)')
@click.option('--endpoint-type', 
              type=click.Choice(['local', 'nvidia_hosted']), 
              default='local',
              help='Type of endpoint: local or nvidia_hosted')
@click.option('--timeout', default=300.0, help='Request timeout in seconds')
@click.option('--poll-seconds', default=10, help='Polling interval for NVIDIA hosted endpoints')
@click.option('--multi-endpoint', is_flag=True, help='Enable multi-endpoint load balancing')
@click.option('--load-balance-strategy', 
              type=click.Choice(['round_robin', 'least_loaded', 'random']), 
              default='least_loaded',
              help='Load balancing strategy for multi-endpoint')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, base_url: str, api_key: Optional[str], endpoint_type: str, 
        timeout: float, poll_seconds: int, multi_endpoint: bool, 
        load_balance_strategy: str, verbose: bool):
    """
    Boltz-2 Python Client CLI
    
    Supports both local deployments and NVIDIA hosted endpoints.
    
    Examples:
    
    # Local endpoint
    boltz2 --base-url http://localhost:8000 protein "MKTVRQERLK..."
    
    # Multi-endpoint for parallel processing
    boltz2 --multi-endpoint --base-url "http://localhost:8000,http://localhost:8001,http://localhost:8002,http://localhost:8003" screen target.fasta compounds.csv
    
    # Multi-endpoint with custom strategy
    boltz2 --multi-endpoint --base-url "http://localhost:8000,http://localhost:8001" --load-balance-strategy round_robin protein "MKTVRQERLK..."
    
    # NVIDIA hosted endpoint  
    boltz2 --base-url https://health.api.nvidia.com --endpoint-type nvidia_hosted --api-key YOUR_KEY protein "MKTVRQERLK..."
    
    # Using environment variable for API key
    export NVIDIA_API_KEY=your_api_key
    boltz2 --base-url https://health.api.nvidia.com --endpoint-type nvidia_hosted protein "MKTVRQERLK..."
    """
    ctx.ensure_object(dict)
    ctx.obj['base_url'] = base_url
    ctx.obj['api_key'] = api_key
    ctx.obj['endpoint_type'] = endpoint_type
    ctx.obj['timeout'] = timeout
    ctx.obj['poll_seconds'] = poll_seconds
    ctx.obj['multi_endpoint'] = multi_endpoint
    ctx.obj['load_balance_strategy'] = load_balance_strategy
    ctx.obj['verbose'] = verbose
    
    if verbose:
        if multi_endpoint:
            endpoints = [url.strip() for url in base_url.split(',')]
            print_info(f"Using multi-endpoint mode with {len(endpoints)} endpoints")
            print_info(f"Load balance strategy: {load_balance_strategy}")
            for ep in endpoints:
                print_info(f"  - {ep}")
        else:
            print_info(f"Using {endpoint_type} endpoint: {base_url}")
            if endpoint_type == 'nvidia_hosted':
                if api_key:
                    print_info("API key provided via command line")
                else:
                    print_info("API key will be read from NVIDIA_API_KEY environment variable")


def create_client(ctx):
    """Create a Boltz2Client or MultiEndpointClient from context."""
    from .multi_endpoint_client import MultiEndpointClient, LoadBalanceStrategy
    
    if ctx.obj['multi_endpoint']:
        # Parse multiple endpoints from comma-separated list
        endpoints = [url.strip() for url in ctx.obj['base_url'].split(',')]
        
        # Map strategy string to enum
        strategy_map = {
            'round_robin': LoadBalanceStrategy.ROUND_ROBIN,
            'least_loaded': LoadBalanceStrategy.LEAST_LOADED,
            'random': LoadBalanceStrategy.RANDOM
        }
        strategy = strategy_map[ctx.obj['load_balance_strategy']]
        
        if ctx.obj['verbose']:
            print_info(f"Using multi-endpoint with {len(endpoints)} endpoints")
            print_info(f"Load balance strategy: {strategy.value}")
        
        return MultiEndpointClient(
            endpoints=endpoints,
            strategy=strategy,
            timeout=ctx.obj['timeout']
        )
    else:
        # Single endpoint
        return Boltz2Client(
            base_url=ctx.obj['base_url'],
            api_key=ctx.obj['api_key'],
            endpoint_type=ctx.obj['endpoint_type'],
            timeout=ctx.obj['timeout'],
            poll_seconds=ctx.obj['poll_seconds'],
            console=console
        )


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
            if ctx.obj['endpoint_type'] != 'nvidia_hosted':
                print_error(f"Health check failed: {e}")
                raise click.Abort()
    
    asyncio.run(check_health())


@cli.command()
@click.pass_context
def metadata(ctx):
    """Get service metadata and model information."""
    async def get_metadata():
        try:
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
                
        except Exception as e:
            print_error(f"Failed to get metadata: {e}")
            raise click.Abort()
    
    asyncio.run(get_metadata())


@cli.command()
@click.argument('sequence')
@click.option('--polymer-id', default='A', help='Polymer identifier (default: A)')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6), 
              help='Number of recycling steps (1-6, default: 3)')
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000),
              help='Number of sampling steps (10-1000, default: 50)')
@click.option('--diffusion-samples', default=1, type=click.IntRange(1, 5),
              help='Number of diffusion samples (1-5, default: 1)')
@click.option('--step-scale', default=1.638, type=click.FloatRange(0.5, 5.0),
              help='Step scale for diffusion sampling (0.5-5.0, default: 1.638)')
@click.option('--msa-file', multiple=True, type=(str, click.Choice(['sto', 'a3m', 'csv', 'fasta'])),
              help='MSA file and format (can be specified multiple times)')
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.pass_context
def protein(ctx, sequence: str, polymer_id: str, recycling_steps: int, sampling_steps: int,
           diffusion_samples: int, step_scale: float, msa_file: List[Tuple[str, str]], 
           output_dir: str, no_save: bool):
    """
    Predict protein structure with optional MSA guidance.
    
    SEQUENCE: Protein amino acid sequence
    
    Examples:
        boltz2 protein "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
        boltz2 protein "SEQUENCE" --msa-file alignment.a3m a3m --recycling-steps 5
        boltz2 protein "SEQUENCE" --output-dir ./results --sampling-steps 100
    """
    async def run_protein_prediction():
        try:
            client = create_client(ctx)
            
            # Prepare MSA files
            msa_files = []
            for file_path, format_type in msa_file:
                if not Path(file_path).exists():
                    print_error(f"MSA file not found: {file_path}")
                    raise click.Abort()
                msa_files.append((file_path, format_type))
            
            print_info(f"Predicting structure for protein sequence (length: {len(sequence)})")
            print_info(f"Parameters: recycling_steps={recycling_steps}, sampling_steps={sampling_steps}")
            print_info(f"            diffusion_samples={diffusion_samples}, step_scale={step_scale}")
            
            if msa_files:
                print_info(f"Using {len(msa_files)} MSA file(s)")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Making prediction...", total=None)
                
                def progress_callback(message: str):
                    progress.update(task, description=message)
                
                result = await client.predict_protein_structure(
                    sequence=sequence,
                    polymer_id=polymer_id,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    diffusion_samples=diffusion_samples,
                    step_scale=step_scale,
                    msa_files=msa_files if msa_files else None,
                    save_structures=not no_save,
                    output_dir=Path(output_dir),
                    progress_callback=progress_callback
                )
                
                progress.update(task, description="Prediction completed!")
            
            # Display results
            print_success(f"Prediction completed successfully!")
            print_info(f"Generated {len(result.structures)} structure(s)")
            
            if result.confidence_scores:
                avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
                print_info(f"Average confidence: {avg_confidence:.3f}")
            
            if not no_save:
                print_info(f"Structures saved to: {output_dir}")
            
        except Exception as e:
            print_error(f"Prediction failed: {e}")
            raise click.Abort()
    
    asyncio.run(run_protein_prediction())


@cli.command()
@click.argument('protein_sequence')
@click.option('--smiles', help='Ligand SMILES string')
@click.option('--ccd', help='Ligand CCD code (alternative to SMILES)')
@click.option('--protein-id', default='A', help='Protein identifier (default: A)')
@click.option('--ligand-id', default='LIG', help='Ligand identifier (default: LIG)')
@click.option('--pocket-residues', help='Comma-separated list of pocket residue indices')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6))
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000))
@click.option('--predict-affinity', is_flag=True, help='Enable affinity prediction for the ligand')
@click.option('--sampling-steps-affinity', default=200, type=click.IntRange(10, 1000), help='Sampling steps for affinity prediction (default: 200)')
@click.option('--diffusion-samples-affinity', default=5, type=click.IntRange(1, 10), help='Diffusion samples for affinity prediction (default: 5)')
@click.option('--affinity-mw-correction', is_flag=True, help='Apply molecular weight correction to affinity prediction')
@click.option('--msa-file', multiple=True, type=(str, click.Choice(['sto', 'a3m', 'csv', 'fasta'])),
              help='MSA file and format (can be specified multiple times)')
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.pass_context
def ligand(ctx, protein_sequence: str, smiles: Optional[str], ccd: Optional[str],
          protein_id: str, ligand_id: str, pocket_residues: Optional[str],
          recycling_steps: int, sampling_steps: int, predict_affinity: bool,
          sampling_steps_affinity: int, diffusion_samples_affinity: int, 
          affinity_mw_correction: bool, msa_file: List[Tuple[str, str]], 
          output_dir: str, no_save: bool):
    """
    Predict protein-ligand complex structure with optional MSA guidance.
    
    PROTEIN_SEQUENCE: Protein amino acid sequence
    
    Example:
        boltz2 ligand "PROTEIN_SEQ" --smiles "CC(=O)OC1=CC=CC=C1C(=O)O"
        boltz2 ligand "PROTEIN_SEQ" --ccd ASP --pocket-residues "10,15,20,25"
        boltz2 ligand "PROTEIN_SEQ" --smiles "CC(=O)O" --msa-file alignment.a3m a3m --predict-affinity
    """
    if not smiles and not ccd:
        print_error("Must provide either --smiles or --ccd")
        raise click.Abort()
    
    if smiles and ccd:
        print_error("Cannot specify both --smiles and --ccd")
        raise click.Abort()
    
    async def run_ligand_prediction():
        try:
            client = create_client(ctx)
            
            # Parse pocket residues
            pocket_residue_list = None
            if pocket_residues:
                pocket_residue_list = [int(x.strip()) for x in pocket_residues.split(',')]
            
            print_info(f"Predicting protein-ligand complex")
            print_info(f"Protein length: {len(protein_sequence)}")
            print_info(f"Ligand: {smiles or ccd}")
            
            if pocket_residue_list:
                print_info(f"Pocket residues: {pocket_residue_list}")
            
            if predict_affinity:
                print_info(f"Affinity prediction: ENABLED")
                print_info(f"  - Sampling steps: {sampling_steps_affinity}")
                print_info(f"  - Diffusion samples: {diffusion_samples_affinity}")
                print_info(f"  - MW correction: {affinity_mw_correction}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Making prediction...", total=None)
                
                def progress_callback(message: str):
                    progress.update(task, description=message)
                
                # Prepare MSA files
                msa_files = []
                for file_path, format_type in msa_file:
                    if not Path(file_path).exists():
                        print_error(f"MSA file not found: {file_path}")
                        raise click.Abort()
                    msa_files.append((file_path, format_type))
                
                if msa_files:
                    print_info(f"Using {len(msa_files)} MSA file(s)")
                
                # Use the convenience method that handles MSA
                result = await client.predict_protein_ligand_complex(
                    protein_sequence=protein_sequence,
                    ligand_smiles=smiles,
                    ligand_ccd=ccd,
                    protein_id=protein_id,
                    ligand_id=ligand_id,
                    pocket_residues=pocket_res_list if pocket_residues else None,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    predict_affinity=predict_affinity,
                    sampling_steps_affinity=sampling_steps_affinity,
                    diffusion_samples_affinity=diffusion_samples_affinity,
                    affinity_mw_correction=affinity_mw_correction,
                    msa_files=msa_files if msa_files else None,
                    save_structures=not no_save,
                    output_dir=Path(output_dir),
                    progress_callback=progress_callback
                )
                
                progress.update(task, description="Prediction completed!")
            
            print_success(f"Complex prediction completed successfully!")
            print_info(f"Generated {len(result.structures)} structure(s)")
            
            if result.confidence_scores:
                avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
                print_info(f"Average confidence: {avg_confidence:.3f}")
            
            # Display affinity results if available
            if predict_affinity and result.affinities and ligand_id in result.affinities:
                console.print("\n📊 Affinity Prediction Results:", style="bold cyan")
                affinity = result.affinities[ligand_id]
                
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Metric", style="cyan", no_wrap=True)
                table.add_column("Value", style="green")
                
                table.add_row("pIC50", f"{affinity.affinity_pic50[0]:.3f}")
                table.add_row("log(IC50)", f"{affinity.affinity_pred_value[0]:.3f}")
                table.add_row("Binding Probability", f"{affinity.affinity_probability_binary[0]:.3f}")
                
                # pIC50 = -log10(IC50 in M), so IC50 in M = 10^(-pIC50)
                ic50_nm = 10 ** (-affinity.affinity_pic50[0]) * 1e9
                table.add_row("Estimated IC50", f"{ic50_nm:.2f} nM")
                
                console.print(table)
                
                # Interpretation
                if affinity.affinity_probability_binary[0] > 0.7:
                    print_success("Strong binding predicted (>70% probability)")
                elif affinity.affinity_probability_binary[0] > 0.5:
                    print_info("Moderate binding predicted (>50% probability)")
                else:
                    print_info("Weak binding predicted (<50% probability)")
            
            # Save results
            if not no_save:
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)
                
                # Save structure
                structure_file = output_path / "structure_0.cif"
                with open(structure_file, 'w') as f:
                    f.write(result.structures[0].structure)
                print_info(f"Structure saved to: {structure_file}")
                
                # Save affinity results if available
                if predict_affinity and result.affinities and ligand_id in result.affinities:
                    affinity_file = output_path / "affinity_results.json"
                    affinity_data = {
                        "ligand_id": ligand_id,
                        "ligand": smiles or ccd,
                        "predictions": {
                            "log_ic50": affinity.affinity_pred_value[0],
                            "pic50": affinity.affinity_pic50[0],
                            "binding_probability": affinity.affinity_probability_binary[0],
                            "ic50_nm": ic50_nm
                        }
                    }
                    with open(affinity_file, 'w') as f:
                        json.dump(affinity_data, f, indent=2)
                    print_info(f"Affinity results saved to: {affinity_file}")
            
        except Exception as e:
            print_error(f"Prediction failed: {e}")
            raise click.Abort()
    
    asyncio.run(run_ligand_prediction())


@cli.command()
@click.argument('protein_sequence')
@click.option('--ccd', help='Ligand CCD code (required for covalent bonding)')
@click.option('--bond', 'bonds', multiple=True, 
              help='Bond constraint: POLYMER_ID:RESIDUE_INDEX:ATOM_NAME:LIGAND_ID:ATOM_NAME (can be specified multiple times)')
@click.option('--disulfide', 'disulfides', multiple=True,
              help='Disulfide bond: POLYMER_ID:RESIDUE1_INDEX:POLYMER_ID:RESIDUE2_INDEX (can be specified multiple times)')
@click.option('--protein-id', default='A', help='Protein identifier (default: A)')
@click.option('--ligand-id', default='LIG', help='Ligand identifier (default: LIG)')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6))
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000))
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.pass_context
def covalent(ctx, protein_sequence: str, ccd: Optional[str],
            bonds: List[str], disulfides: List[str], protein_id: str, ligand_id: str, 
            recycling_steps: int, sampling_steps: int, output_dir: str, no_save: bool):
    """
    Predict covalent complex structure with flexible bond constraints.
    
    Note: Covalent bonding only supports CCD codes for ligands, not SMILES.
    
    This command supports various types of covalent bonds:
    
    \b
    1. Protein-Ligand bonds (requires --ccd):
       --bond A:12:SG:LIG:C22  (Cys12 SG to ligand C22)
       --bond A:45:NE2:LIG:C1  (His45 NE2 to ligand C1)
    
    \b
    2. Disulfide bonds (protein-only, no ligand needed):
       --disulfide A:12:A:45   (Cys12 to Cys45 in same chain)
       --disulfide A:12:B:23   (Cys12 in chain A to Cys23 in chain B)
    
    \b
    3. Multiple bonds:
       --bond A:12:SG:LIG:C22 --bond A:45:NE2:LIG:C1
    
    Examples:
    
    \b
    # Covalent protein-ligand complex (CCD required)
    boltz2 covalent "MKTVRQERLKCSIVRIL..." --ccd U4U --bond A:12:SG:LIG:C22
    
    \b
    # Disulfide bond in protein (no ligand needed)
    boltz2 covalent "MKTVRQERLKCSIVRILCSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG" --disulfide A:12:A:25
    
    \b
    # Multiple covalent bonds with ligand
    boltz2 covalent "SEQUENCE..." --ccd ATP --bond A:12:SG:LIG:C22 --bond A:45:NE2:LIG:C1
    """
    async def run_covalent_prediction():
        try:
            client = create_client(ctx)
            
            # Validate inputs
            if not bonds and not disulfides:
                print_error("At least one bond constraint (--bond or --disulfide) must be specified")
                raise click.Abort()
            
            if bonds and not ccd:
                print_error("CCD code (--ccd) is required when using --bond constraints")
                print_error("Note: Covalent bonding only supports CCD codes, not SMILES")
                raise click.Abort()
            
            # Parse bond constraints
            bond_constraints = []
            
            # Parse protein-ligand bonds
            for bond_spec in bonds:
                try:
                    parts = bond_spec.split(':')
                    if len(parts) != 5:
                        raise ValueError("Bond format: POLYMER_ID:RESIDUE_INDEX:ATOM_NAME:LIGAND_ID:ATOM_NAME")
                    
                    polymer_id, residue_idx, protein_atom, lig_id, ligand_atom = parts
                    residue_idx = int(residue_idx)
                    
                    bond_constraint = BondConstraint(
                        constraint_type="bond",
                        atoms=[
                            Atom(id=polymer_id, residue_index=residue_idx, atom_name=protein_atom),
                            Atom(id=lig_id, residue_index=1, atom_name=ligand_atom)
                        ]
                    )
                    bond_constraints.append(bond_constraint)
                    
                except (ValueError, IndexError) as e:
                    print_error(f"Invalid bond specification '{bond_spec}': {e}")
                    raise click.Abort()
            
            # Parse disulfide bonds
            for disulfide_spec in disulfides:
                try:
                    parts = disulfide_spec.split(':')
                    if len(parts) != 4:
                        raise ValueError("Disulfide format: POLYMER_ID1:RESIDUE1_INDEX:POLYMER_ID2:RESIDUE2_INDEX")
                    
                    polymer1_id, residue1_idx, polymer2_id, residue2_idx = parts
                    residue1_idx = int(residue1_idx)
                    residue2_idx = int(residue2_idx)
                    
                    bond_constraint = BondConstraint(
                        constraint_type="bond",
                        atoms=[
                            Atom(id=polymer1_id, residue_index=residue1_idx, atom_name="SG"),
                            Atom(id=polymer2_id, residue_index=residue2_idx, atom_name="SG")
                        ]
                    )
                    bond_constraints.append(bond_constraint)
                    
                except (ValueError, IndexError) as e:
                    print_error(f"Invalid disulfide specification '{disulfide_spec}': {e}")
                    raise click.Abort()
            
            # Create polymers
            polymers = [Polymer(
                id=protein_id,
                molecule_type="protein",
                sequence=protein_sequence
            )]
            
            # Create ligands if specified
            ligands = []
            if ccd:
                ligand = Ligand(
                    id=ligand_id,
                    ccd=ccd
                )
                ligands.append(ligand)
            
            # Display prediction info
            print_info("Predicting covalent complex structure")
            print_info(f"Protein length: {len(protein_sequence)}")
            if ccd:
                print_info(f"Ligand CCD: {ccd}")
            
            print_info(f"Bond constraints: {len(bond_constraints)}")
            for i, constraint in enumerate(bond_constraints, 1):
                atom1, atom2 = constraint.atoms
                print_info(f"  {i}. {atom1.id}:{atom1.residue_index}:{atom1.atom_name} ↔ {atom2.id}:{atom2.residue_index}:{atom2.atom_name}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Predicting covalent complex...", total=None)
                
                def progress_callback(message: str):
                    progress.update(task, description=message)
                
                response = await client.predict_with_advanced_parameters(
                    polymers=polymers,
                    ligands=ligands if ligands else None,
                    constraints=bond_constraints,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    save_structures=not no_save,
                    output_dir=Path(output_dir),
                    progress_callback=progress_callback
                )
                
                progress.update(task, description="Prediction completed!")
            
            print_success("Covalent complex prediction completed successfully!")
            print_info(f"Generated {len(response.structures)} structure(s)")
            
            if response.confidence_scores:
                avg_confidence = sum(response.confidence_scores) / len(response.confidence_scores)
                print_info(f"Average confidence: {avg_confidence:.3f}")
            
            if not no_save:
                print_info(f"Structures saved to: {output_dir}")
                
        except Exception as e:
            print_error(f"Covalent prediction failed: {e}")
            raise click.Abort()
    
    asyncio.run(run_covalent_prediction())


@cli.command()
@click.option('--protein-sequences', required=True, help='Comma-separated protein sequences')
@click.option('--dna-sequences', required=True, help='Comma-separated DNA sequences')
@click.option('--protein-ids', help='Comma-separated protein IDs (default: A,B,...)')
@click.option('--dna-ids', help='Comma-separated DNA IDs (default: C,D,...)')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6))
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000))
@click.option('--concatenate-msas', is_flag=True, help='Concatenate MSAs for polymers')
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.pass_context
def dna_protein(ctx, protein_sequences: str, dna_sequences: str, protein_ids: Optional[str],
               dna_ids: Optional[str], recycling_steps: int, sampling_steps: int,
               concatenate_msas: bool, output_dir: str, no_save: bool):
    """
    Predict DNA-protein complex structure.
    
    Example:
        boltz2 dna-protein --protein-sequences "PROT1,PROT2" --dna-sequences "ATCG,CGTA"
    """
    async def run_dna_protein_prediction():
        try:
            client = create_client(ctx)
            
            # Parse sequences
            protein_seq_list = [seq.strip() for seq in protein_sequences.split(',')]
            dna_seq_list = [seq.strip() for seq in dna_sequences.split(',')]
            
            # Parse IDs
            protein_id_list = None
            if protein_ids:
                protein_id_list = [id.strip() for id in protein_ids.split(',')]
            
            dna_id_list = None
            if dna_ids:
                dna_id_list = [id.strip() for id in dna_ids.split(',')]
            
            print_info(f"Predicting DNA-protein complex")
            print_info(f"Proteins: {len(protein_seq_list)} sequences")
            print_info(f"DNA: {len(dna_seq_list)} sequences")
            print_info(f"Concatenate MSAs: {concatenate_msas}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Making prediction...", total=None)
                
                def progress_callback(message: str):
                    progress.update(task, description=message)
                
                result = await client.predict_dna_protein_complex(
                    protein_sequences=protein_seq_list,
                    dna_sequences=dna_seq_list,
                    protein_ids=protein_id_list,
                    dna_ids=dna_id_list,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    concatenate_msas=concatenate_msas,
                    save_structures=not no_save,
                    output_dir=Path(output_dir),
                    progress_callback=progress_callback
                )
                
                progress.update(task, description="Prediction completed!")
            
            print_success(f"DNA-protein complex prediction completed successfully!")
            print_info(f"Generated {len(result.structures)} structure(s)")
            
            if result.confidence_scores:
                avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
                print_info(f"Average confidence: {avg_confidence:.3f}")
            
        except Exception as e:
            print_error(f"Prediction failed: {e}")
            raise click.Abort()
    
    asyncio.run(run_dna_protein_prediction())


@cli.command()
@click.option('--config-file', type=click.Path(exists=True), required=True,
              help='JSON configuration file with complete prediction parameters')
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.pass_context
def advanced(ctx, config_file: str, output_dir: str, no_save: bool):
    """
    Run prediction with advanced parameters from JSON configuration file.
    
    The JSON file should contain a complete prediction request with all parameters.
    
    Example JSON structure:
    {
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
        "diffusion_samples": 3
    }
    """
    async def run_advanced_prediction():
        try:
            client = create_client(ctx)
            
            # Load configuration
            config_path = Path(config_file)
            config_data = json.loads(config_path.read_text())
            
            print_info(f"Loading configuration from {config_path}")
            
            # Create prediction request
            request = PredictionRequest(**config_data)
            
            print_info("Running advanced prediction with custom parameters")
            print_info(f"Polymers: {len(request.polymers)}")
            if request.ligands:
                print_info(f"Ligands: {len(request.ligands)}")
            if request.constraints:
                print_info(f"Constraints: {len(request.constraints)}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                def progress_callback(message: str):
                    progress.console.print(f"🧬 {message}")
                
                task = progress.add_task("Making prediction...", total=None)
                
                result = await client.predict(
                    request,
                    save_structures=not no_save,
                    output_dir=Path(output_dir),
                    progress_callback=progress_callback
                )
                
                progress.update(task, description="Prediction completed!")
            
            print_success("Advanced prediction completed successfully!")
            print_info(f"Generated {len(result.structures)} structure(s)")
            
            if result.confidence_scores:
                avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
                print_info(f"Average confidence: {avg_confidence:.3f}")
            
        except Exception as e:
            print_error(f"Advanced prediction failed: {e}")
            raise click.Abort()
    
    asyncio.run(run_advanced_prediction())


@cli.command(name='yaml')
@click.argument('yaml_file', type=click.Path(exists=True))
@click.option('--msa-dir', type=click.Path(), help='Directory containing MSA files (default: same as YAML file)')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6))
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000))
@click.option('--diffusion-samples', default=1, type=click.IntRange(1, 5))
@click.option('--step-scale', default=1.638, type=click.FloatRange(0.5, 5.0))
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.pass_context
def yaml_config(ctx, yaml_file: str, msa_dir: Optional[str], recycling_steps: int, 
         sampling_steps: int, diffusion_samples: int, step_scale: float,
         output_dir: str, no_save: bool):
    """
    Run prediction from YAML configuration file (official Boltz format).
    
    This command supports the official Boltz YAML configuration format as used
    in the original Boltz repository examples.
    
    YAML_FILE: Path to YAML configuration file
    
    Example YAML format:
    
    \b
    version: 1
    sequences:
      - protein:
          id: A
          sequence: "MKTVRQERLK..."
          msa: "protein_A.a3m"  # optional
      - ligand:
          id: B
          smiles: "CC(=O)O"
    properties:  # optional
      affinity:
        binder: B
    
    Examples:
    
    \b
    # Basic protein-ligand complex
    boltz2 yaml protein_ligand.yaml
    
    \b
    # With custom parameters
    boltz2 yaml complex.yaml --recycling-steps 5 --sampling-steps 100
    
    \b
    # With custom MSA directory
    boltz2 yaml config.yaml --msa-dir /path/to/msa/files
    
    \b
    # Affinity prediction
    boltz2 yaml my_affinity_config.yaml --diffusion-samples 3
    """
    async def run_yaml_prediction():
        try:
            client = create_client(ctx)
            
            yaml_path = Path(yaml_file)
            print_info(f"Loading YAML configuration from {yaml_path}")
            
            # Determine MSA directory
            if msa_dir:
                msa_directory = Path(msa_dir)
            else:
                msa_directory = yaml_path.parent
            
            print_info(f"MSA directory: {msa_directory}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                def progress_callback(message: str):
                    progress.console.print(f"🧬 {message}")
                
                task = progress.add_task("Loading configuration...", total=None)
                
                # Load and validate YAML config
                yaml_content = yaml_path.read_text()
                yaml_data = pyyaml.safe_load(yaml_content)
                
                from .models import YAMLConfig
                config = YAMLConfig(**yaml_data)
                
                # Display configuration info
                protein_count = sum(1 for seq in config.sequences if seq.protein)
                ligand_count = sum(1 for seq in config.sequences if seq.ligand)
                
                print_info(f"Configuration loaded successfully")
                print_info(f"Proteins: {protein_count}, Ligands: {ligand_count}")
                
                if config.properties and config.properties.affinity:
                    print_info(f"Affinity prediction enabled for binder: {config.properties.affinity.binder}")
                
                progress.update(task, description="Making prediction...")
                
                # Convert config to request
                request = config.to_prediction_request()
                
                # Handle MSA files for proteins that reference them
                for i, seq in enumerate(config.sequences):
                    if seq.protein and seq.protein.msa and seq.protein.msa != "empty":
                        msa_path = msa_directory / seq.protein.msa
                        if msa_path.exists():
                            msa_content = msa_path.read_text()
                            # Determine format from extension
                            format_map = {
                                '.a3m': 'a3m',
                                '.sto': 'sto',
                                '.fasta': 'fasta',
                                '.csv': 'csv'
                            }
                            format_type = format_map.get(msa_path.suffix.lower(), 'a3m')
                            
                            from .models import AlignmentFileRecord
                            msa_record = AlignmentFileRecord(
                                alignment=msa_content,
                                format=format_type,
                                rank=0
                            )
                            
                            # Update the corresponding polymer with MSA
                            polymer_idx = sum(1 for s in config.sequences[:i] if s.protein)
                            if polymer_idx < len(request.polymers):
                                request.polymers[polymer_idx].msa = {"default": {format_type: msa_record}}
                        else:
                            print_warning(f"MSA file not found: {msa_path}")
                
                # Override with CLI parameters
                request.recycling_steps = recycling_steps
                request.sampling_steps = sampling_steps
                request.diffusion_samples = diffusion_samples
                request.step_scale = step_scale
                
                result = await client.predict(
                    request,
                    save_structures=not no_save,
                    output_dir=Path(output_dir),
                    progress_callback=progress_callback
                )
                
                progress.update(task, description="Prediction completed!")
            
            print_success("YAML prediction completed successfully!")
            print_info(f"Generated {len(result.structures)} structure(s)")
            
            if result.confidence_scores:
                avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
                print_info(f"Average confidence: {avg_confidence:.3f}")
            
            if not no_save:
                print_info(f"Structures saved to: {output_dir}")
            
        except Exception as e:
            print_error(f"YAML prediction failed: {e}")
            raise click.Abort()
    
    asyncio.run(run_yaml_prediction())


@cli.command(name='msa-search')
@click.argument('sequence')
@click.option('--endpoint', default='http://your-msa-nim:8000', 
              help='MSA Search NIM endpoint URL')
@click.option('--databases', '-d', multiple=True, default=['all'],
              help='Databases to search (default: all)')
@click.option('--max-sequences', default=500, type=int,
              help='Maximum sequences to return (default: 500)')
@click.option('--e-value', default=0.0001, type=float,
              help='E-value threshold (default: 0.0001)')
@click.option('--output-format', '-f', 
              type=click.Choice(['a3m', 'fasta', 'sto']), 
              default='a3m',
              help='Output format (default: a3m)')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file path')
@click.pass_context
def msa_search_command(ctx, sequence: str, endpoint: str, databases: List[str],
                       max_sequences: int, e_value: float, 
                       output_format: str, output: str):
    """
    Search for MSA using GPU-accelerated MSA Search NIM.
    
    Examples:
    
    # Basic MSA search
    boltz2 msa-search "MKTVRQERLKS..." -o output.a3m
    
    # Search specific databases with custom parameters
    boltz2 msa-search "SEQUENCE" -d uniref90 -d pdb70 --max-sequences 1000 -o output.a3m
    
    # Export in different format
    boltz2 msa-search "SEQUENCE" -f fasta -o output.fasta
    """
    async def run_msa_search():
        try:
            # Get client configuration
            config = ctx.obj
            client = Boltz2Client(
                base_url=config['base_url'],
                api_key=config.get('api_key'),
                endpoint_type=config['endpoint_type']
            )
            
            # Configure MSA Search
            print_info(f"Configuring MSA Search NIM: {endpoint}")
            client.configure_msa_search(
                msa_endpoint_url=endpoint,
                api_key=config.get('api_key')
            )
            
            # Show search parameters
            print_info("Search Parameters:")
            print(f"  Databases: {', '.join(databases)}")
            print(f"  Max sequences: {max_sequences}")
            print(f"  E-value: {e_value}")
            print(f"  Output format: {output_format}")
            
            # Perform search
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn()
            ) as progress:
                task = progress.add_task("Searching MSA...", total=None)
                
                result_path = await client.search_msa(
                    sequence=sequence,
                    databases=list(databases),
                    max_msa_sequences=max_sequences,
                    e_value=e_value,
                    output_format=output_format,
                    save_path=output
                )
                
                progress.update(task, completed=100)
            
            # Show results
            file_size = Path(result_path).stat().st_size
            seq_count = Path(result_path).read_text().count('\n>')
            
            print_success(f"MSA search completed!")
            print(f"  Sequences found: {seq_count}")
            print(f"  File size: {file_size:,} bytes")
            print(f"  Saved to: {result_path}")
            
        except Exception as e:
            print_error(f"MSA search failed: {e}")
    
    asyncio.run(run_msa_search())


@cli.command(name='msa-predict')
@click.argument('sequence')
@click.option('--endpoint', default='http://your-msa-nim:8000',
              help='MSA Search NIM endpoint URL')
@click.option('--databases', '-d', multiple=True, default=['all'],
              help='Databases to search (default: all)')
@click.option('--max-sequences', default=500, type=int,
              help='Maximum sequences for MSA (default: 500)')
@click.option('--e-value', default=0.0001, type=float,
              help='E-value threshold (default: 0.0001)')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6),
              help='Number of recycling steps (default: 3)')
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000),
              help='Number of sampling steps (default: 50)')
@click.option('--output-dir', type=click.Path(), default='.',
              help='Directory to save output files')
@click.option('--no-save-msa', is_flag=True,
              help="Don't save the MSA file separately")
@click.pass_context
def msa_predict_command(ctx, sequence: str, endpoint: str, databases: List[str],
                        max_sequences: int, e_value: float,
                        recycling_steps: int, sampling_steps: int,
                        output_dir: str, no_save_msa: bool):
    """
    Perform MSA search and structure prediction in one step.
    
    This command combines MSA search with structure prediction for enhanced results.
    
    Examples:
    
    # Basic MSA-guided prediction
    boltz2 msa-predict "MKTVRQERLKS..."
    
    # Custom parameters
    boltz2 msa-predict "SEQUENCE" --max-sequences 1000 --recycling-steps 5
    
    # Save to specific directory
    boltz2 msa-predict "SEQUENCE" --output-dir results/
    """
    async def run_msa_predict():
        try:
            # Get client configuration
            config = ctx.obj
            client = Boltz2Client(
                base_url=config['base_url'],
                api_key=config.get('api_key'),
                endpoint_type=config['endpoint_type']
            )
            
            # Configure MSA Search
            print_info(f"Configuring MSA Search NIM: {endpoint}")
            client.configure_msa_search(
                msa_endpoint_url=endpoint,
                api_key=config.get('api_key')
            )
            
            # Show parameters
            print_info("MSA Search Parameters:")
            print(f"  Databases: {', '.join(databases)}")
            print(f"  Max sequences: {max_sequences}")
            print(f"  E-value: {e_value}")
            
            print_info("Prediction Parameters:")
            print(f"  Recycling steps: {recycling_steps}")
            print(f"  Sampling steps: {sampling_steps}")
            
            # Perform MSA search + prediction
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn()
            ) as progress:
                task = progress.add_task("MSA search + structure prediction...", total=None)
                
                result = await client.predict_with_msa_search(
                    sequence=sequence,
                    databases=list(databases),
                    max_msa_sequences=max_sequences,
                    e_value=e_value,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps
                )
                
                progress.update(task, completed=100)
            
            # Save results
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            structure_file = output_path / "structure_with_msa.cif"
            structure_file.write_text(result.structures[0].structure)
            
            confidence = result.confidence_scores[0] if result.confidence_scores else 0.0
            
            print_success("Prediction completed!")
            print(f"  Confidence score: {confidence:.3f}")
            print(f"  Structure saved to: {structure_file}")
            
            # Optionally save MSA separately
            if not no_save_msa:
                msa_file = output_path / "msa_alignment.a3m"
                await client.search_msa(
                    sequence=sequence,
                    databases=list(databases),
                    max_msa_sequences=max_sequences,
                    e_value=e_value,
                    output_format='a3m',
                    save_path=msa_file
                )
                print(f"  MSA saved to: {msa_file}")
            
        except Exception as e:
            print_error(f"MSA prediction failed: {e}")
    
    asyncio.run(run_msa_predict())


@cli.command(name='msa-ligand')
@click.argument('protein_sequence')
@click.option('--smiles', help='Ligand SMILES string')
@click.option('--ccd', help='Ligand CCD code (alternative to SMILES)')
@click.option('--endpoint', default='http://your-msa-nim:8000',
              help='MSA Search NIM endpoint URL')
@click.option('--databases', '-d', multiple=True, default=['all'],
              help='Databases to search (default: all)')
@click.option('--max-sequences', default=500, type=int,
              help='Maximum sequences for MSA (default: 500)')
@click.option('--e-value', default=0.0001, type=float,
              help='E-value threshold (default: 0.0001)')
@click.option('--predict-affinity', is_flag=True,
              help='Enable affinity prediction')
@click.option('--sampling-steps-affinity', default=200, type=int,
              help='Sampling steps for affinity (default: 200)')
@click.option('--diffusion-samples-affinity', default=5, type=int,
              help='Diffusion samples for affinity (default: 5)')
@click.option('--affinity-mw-correction', is_flag=True,
              help='Apply MW correction to affinity')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 6),
              help='Number of recycling steps (default: 3)')
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000),
              help='Number of sampling steps (default: 50)')
@click.option('--output-dir', type=click.Path(), default='.',
              help='Directory to save output files')
@click.pass_context
def msa_ligand_command(ctx, protein_sequence: str, smiles: Optional[str], ccd: Optional[str],
                       endpoint: str, databases: List[str], max_sequences: int, e_value: float,
                       predict_affinity: bool, sampling_steps_affinity: int,
                       diffusion_samples_affinity: int, affinity_mw_correction: bool,
                       recycling_steps: int, sampling_steps: int, output_dir: str):
    """
    MSA search + protein-ligand prediction with optional affinity.
    
    Combines MSA search with ligand complex prediction for enhanced accuracy.
    
    Examples:
    
    # Basic MSA-guided ligand prediction
    boltz2 msa-ligand "MKTVRQERLKS..." --smiles "CC(=O)O"
    
    # With affinity prediction
    boltz2 msa-ligand "SEQUENCE" --smiles "CC(=O)O" --predict-affinity
    
    # Custom parameters
    boltz2 msa-ligand "SEQUENCE" --ccd ATP --max-sequences 1000 \\
        --predict-affinity --sampling-steps-affinity 300
    """
    if not smiles and not ccd:
        print_error("Must provide either --smiles or --ccd")
        raise click.Abort()
    
    if smiles and ccd:
        print_error("Provide either --smiles or --ccd, not both")
        raise click.Abort()
    
    async def run_msa_ligand():
        try:
            # Get client configuration
            config = ctx.obj
            client = Boltz2Client(
                base_url=config['base_url'],
                api_key=config.get('api_key'),
                endpoint_type=config['endpoint_type']
            )
            
            # Configure MSA Search
            print_info(f"Configuring MSA Search NIM: {endpoint}")
            client.configure_msa_search(
                msa_endpoint_url=endpoint,
                api_key=config.get('api_key')
            )
            
            # Show parameters
            print_info("MSA Search Parameters:")
            print(f"  Databases: {', '.join(databases)}")
            print(f"  Max sequences: {max_sequences}")
            print(f"  E-value: {e_value}")
            
            print_info("Prediction Parameters:")
            print(f"  Recycling steps: {recycling_steps}")
            print(f"  Sampling steps: {sampling_steps}")
            
            if predict_affinity:
                print_info("Affinity Parameters:")
                print(f"  Sampling steps: {sampling_steps_affinity}")
                print(f"  Diffusion samples: {diffusion_samples_affinity}")
                print(f"  MW correction: {affinity_mw_correction}")
            
            # Perform MSA search + ligand prediction
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn()
            ) as progress:
                task = progress.add_task("MSA search + ligand prediction...", total=None)
                
                result = await client.predict_ligand_with_msa_search(
                    protein_sequence=protein_sequence,
                    ligand_smiles=smiles,
                    ligand_ccd=ccd,
                    databases=list(databases),
                    e_value=e_value,
                    max_msa_sequences=max_sequences,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    predict_affinity=predict_affinity,
                    sampling_steps_affinity=sampling_steps_affinity if predict_affinity else None,
                    diffusion_samples_affinity=diffusion_samples_affinity if predict_affinity else None,
                    affinity_mw_correction=affinity_mw_correction if predict_affinity else None,
                    save_structures=True,
                    output_dir=Path(output_dir)
                )
                
                progress.update(task, completed=100)
            
            # Save results
            output_path = Path(output_dir)
            
            print_success("Prediction completed!")
            
            if result.confidence_scores:
                confidence = result.confidence_scores[0]
                print(f"  Confidence score: {confidence:.3f}")
            
            if result.structures:
                structure_file = output_path / "structure_0.cif"
                print(f"  Structure saved to: {structure_file}")
            
            # Display affinity results if available
            if predict_affinity and result.affinities:
                ligand_id = "LIG"  # Default ligand ID
                if ligand_id in result.affinities:
                    aff = result.affinities[ligand_id]
                    print_info("Affinity Predictions:")
                    print(f"  pIC50: {aff.affinity_pic50[0]:.3f}")
                    print(f"  IC50: {aff.affinity_ic50[0]:.3f} nM")
                    print(f"  Binding probability: {aff.affinity_probability_binary[0]:.3f}")
            
        except Exception as e:
            print_error(f"MSA-ligand prediction failed: {e}")
    
    asyncio.run(run_msa_ligand())


@cli.command(name='screen')
@click.argument('target_sequence', type=str)
@click.argument('compounds_file', type=click.Path(exists=True))
@click.option('--target-name', default='Target', help='Name of the target protein')
@click.option('--output-dir', '-o', type=click.Path(), help='Output directory for results')
@click.option('--no-affinity', is_flag=True, help='Disable affinity prediction')
@click.option('--pocket-residues', type=str, help='Comma-separated list of pocket residue indices')
@click.option('--pocket-radius', type=float, default=10.0, help='Pocket constraint radius in Angstroms')
@click.option('--recycling-steps', type=int, default=2, help='Number of recycling steps')
@click.option('--sampling-steps', type=int, default=30, help='Number of sampling steps')
@click.option('--max-workers', type=int, default=4, help='Maximum parallel workers')
@click.option('--batch-size', type=int, help='Process compounds in batches')
@click.option('--save-structures/--no-save-structures', default=True, help='Save structure files')
@click.pass_context
def screen(ctx, target_sequence, compounds_file, target_name, output_dir, no_affinity,
           pocket_residues, pocket_radius, recycling_steps, sampling_steps, 
           max_workers, batch_size, save_structures):
    """Run virtual screening campaign against a protein target.
    
    Examples:
        boltz2 screen "MKTVRQERLK..." compounds.csv -o results/
        boltz2 screen target.fasta library.json --pocket-residues "10,15,20,25"
    """
    client = create_client(ctx)
    
    # Import here to avoid circular imports
    from .virtual_screening import VirtualScreening, CompoundLibrary
    
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
        console.print(f"Pocket constraint: {len(pocket_residues_list)} residues, radius={pocket_radius}Å")
    
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
                pocket_radius=pocket_radius,
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


if __name__ == "__main__":
    cli() 