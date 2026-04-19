# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""MSA search and conversion commands."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import click
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
from rich.table import Table

from ..client import Boltz2Client
from ..models import (
    PredictionRequest, Polymer, Ligand, AlignmentFileRecord,
)
from . import cli, console, print_success, print_error, print_info, print_warning


def create_client(ctx):
    """Delegate to the package-level create_client (patchable by tests)."""
    return sys.modules[__package__].create_client(ctx)


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
              type=click.Choice(['a3m', 'fasta']), 
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
            raise
    
    try:
        asyncio.run(run_msa_search())
    except Exception:
        raise click.Abort()


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
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10),
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
            raise
    
    try:
        asyncio.run(run_msa_predict())
    except Exception:
        raise click.Abort()


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
@click.option('--sampling-steps-affinity', default=200, type=click.IntRange(10, 1000),
              help='Sampling steps for affinity (10-1000, default: 200)')
@click.option('--diffusion-samples-affinity', default=5, type=click.IntRange(1, 25),
              help='Diffusion samples for affinity (1-25, default: 5)')
@click.option('--affinity-mw-correction', is_flag=True,
              help='Apply MW correction to affinity')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10),
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
                    print(f"  Predicted value: {aff.affinity_pred_value[0]:.3f}")
                    print(f"  Binding probability: {aff.affinity_probability_binary[0]:.3f}")
            
        except Exception as e:
            print_error(f"MSA-ligand prediction failed: {e}")
            raise
    
    try:
        asyncio.run(run_msa_ligand())
    except Exception:
        raise click.Abort()


@cli.command(name='convert-msa')
@click.argument('a3m_files', nargs=-1, type=click.Path(exists=True))
@click.option('--chain-ids', '-c', type=str, required=True,
              help='Comma-separated chain IDs corresponding to A3M files (e.g., "A,B")')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output CSV file path')
@click.option('--max-pairs', type=int, default=None,
              help='Maximum number of paired sequences to include')
@click.option('--pairing-strategy', type=click.Choice(['greedy', 'complete', 'taxonomy']), 
              default='greedy',
              help='Strategy for pairing sequences (default: greedy, like ColabFold)')
@click.option('--pairing-mode', type=click.Choice(['auto', 'taxid', 'uniref']),
              default='auto',
              help='Pairing identifier mode: auto (default, like ColabFold), taxid, or uniref')
@click.option('--include-unpaired', is_flag=True, default=False,
              help='Include unpaired sequences with key=-1 (maximizes MSA depth)')
@click.pass_context
def convert_msa_command(ctx, a3m_files: Tuple[str, ...], chain_ids: str, 
                        output: str, max_pairs: Optional[int], 
                        pairing_strategy: str, pairing_mode: str, include_unpaired: bool):
    """
    Convert ColabFold A3M monomer MSA files to Boltz2 multimer CSV format.
    
    This command pairs sequences from individual monomer A3M MSA files
    based on organism/species matching and outputs a CSV file suitable
    for Boltz2 multimer structure predictions.
    
    The CSV format has two columns: 'key' and 'sequence'.
    Key conventions (matching open-source Boltz-2):
      key=0    : Query sequence
      key=1..N : Paired sequences (same key across chains = co-evolved)
      key=-1   : Unpaired sequences (no cross-chain match)
    Multiple chain sequences are separated by ':' in the combined CSV.
    
    PAIRING MODE (ColabFold-compatible):
    
    \b
    - auto (default): Like ColabFold. Auto-detects if TaxIDs are present.
                      Uses TaxID pairing if >50% sequences have TaxIDs,
                      otherwise falls back to UniRef cluster ID pairing.
    - taxid: Force TaxID-based pairing (requires OX= fields or species codes)
    - uniref: Force UniRef cluster ID pairing (works with all ColabFold output)
    
    Examples:
    
    \b
    # Default ColabFold-style (auto-detect pairing mode)
    boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv
    
    \b
    # Force UniRef ID pairing (standard ColabFold output without TaxIDs)
    boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --pairing-mode uniref
    
    \b
    # Force TaxID pairing (requires taxonomy annotations)
    boltz2 convert-msa chain_A.a3m chain_B.a3m -c A,B -o paired.csv --pairing-mode taxid
    
    \b
    # Convert three chains with max pairs limit
    boltz2 convert-msa chainA.a3m chainB.a3m chainC.a3m -c A,B,C -o paired.csv --max-pairs 1000
    """
    from ..a3m import convert_a3m_to_multimer_csv
    
    # Parse chain IDs
    chain_id_list = [c.strip() for c in chain_ids.split(',')]
    
    if len(chain_id_list) != len(a3m_files):
        print_error(f"Number of chain IDs ({len(chain_id_list)}) must match number of A3M files ({len(a3m_files)})")
        raise click.Abort()
    
    if len(a3m_files) < 2:
        print_error("At least 2 A3M files are required for multimer pairing")
        raise click.Abort()
    
    # Create mapping of chain IDs to file paths
    a3m_file_dict = {chain_id: Path(filepath) for chain_id, filepath in zip(chain_id_list, a3m_files)}
    
    # Convert pairing_mode to use_tax_id
    use_tax_id = None  # auto-detect (default)
    if pairing_mode == 'taxid':
        use_tax_id = True
    elif pairing_mode == 'uniref':
        use_tax_id = False
    # else: pairing_mode == 'auto', use_tax_id = None (auto-detect)
    
    print_info("A3M to CSV Multimer Converter (ColabFold-compatible)")
    print_info(f"Input files:")
    for chain_id, filepath in a3m_file_dict.items():
        print(f"  Chain {chain_id}: {filepath}")
    print_info(f"Output: {output}")
    print_info(f"Pairing strategy: {pairing_strategy}")
    print_info(f"Pairing mode: {pairing_mode}")
    if include_unpaired:
        print_info("Include unpaired: Yes (key=-1, matching open-source Boltz-2)")
    if max_pairs:
        print_info(f"Max pairs: {max_pairs}")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Converting MSA files...", total=None)
            
            result = convert_a3m_to_multimer_csv(
                a3m_files=a3m_file_dict,
                output_path=Path(output),
                pairing_strategy=pairing_strategy,
                use_tax_id=use_tax_id,
                include_unpaired=include_unpaired,
                max_pairs=max_pairs
            )
            
            progress.update(task, description="Conversion completed!")
        
        print_success("MSA conversion completed successfully!")
        print_info(f"Paired sequences: {result.num_pairs}")
        print_info(f"Chain IDs: {', '.join(result.chain_ids)}")
        print_info(f"Output file: {output}")
        
        # Show query sequence lengths
        print_info("Query sequence lengths:")
        for chain_id, seq in result.query_sequences.items():
            print(f"  Chain {chain_id}: {len(seq)} residues")
        
        # Show preview of CSV
        lines = result.csv_content.split('\n')
        if len(lines) > 4:
            print_info("CSV preview (first 3 pairs):")
            for line in lines[:4]:
                print(f"  {line[:100]}{'...' if len(line) > 100 else ''}")
        
    except Exception as e:
        print_error(f"Conversion failed: {e}")
        raise click.Abort()


@cli.command(name='multimer-msa')
@click.argument('a3m_files', nargs=-1, type=click.Path(exists=True))
@click.option('--chain-ids', '-c', type=str, required=True,
              help='Comma-separated chain IDs corresponding to A3M files (e.g., "A,B")')
@click.option('--output', '-o', type=click.Path(), default=None,
              help='Output CIF file path (default: complex.cif)')
@click.option('--save-csv', is_flag=True, default=False,
              help='Save the generated paired CSV files alongside the CIF output')
@click.option('--save-all', is_flag=True, default=False,
              help='Save all outputs: CIF, confidence scores, metrics as JSON')
@click.option('--max-pairs', type=int, default=None,
              help='Maximum number of paired sequences to include')
@click.option('--pairing-mode', type=click.Choice(['auto', 'taxid', 'uniref']),
              default='auto',
              help='Pairing identifier mode: auto (default), taxid, or uniref')
@click.option('--include-unpaired', is_flag=True, default=False,
              help='Include unpaired sequences with key=-1 (maximizes MSA depth)')
@click.option('--recycling-steps', type=click.IntRange(1, 10), default=3,
              help='Number of recycling steps (1-10, default: 3)')
@click.option('--sampling-steps', type=click.IntRange(10, 1000), default=200,
              help='Number of diffusion sampling steps (10-1000, default: 200)')
@click.option('--diffusion-samples', type=click.IntRange(1, 25), default=1,
              help='Number of diffusion samples/structures (1-25, default: 1)')
@click.option('--write-full-pae', is_flag=True, default=False,
              help='Output full PAE (Predicted Aligned Error) matrix')
@click.option('--write-full-pde', is_flag=True, default=False,
              help='Output full PDE (Predicted Distance Error) matrix')
@click.option('--output-format', type=click.Choice(['cif', 'pdb']), default='cif',
              help='Output structure format: cif (default) or pdb')
@click.pass_context
def multimer_msa_command(ctx, a3m_files: Tuple[str, ...], chain_ids: str, 
                         output: Optional[str], save_csv: bool, save_all: bool,
                         max_pairs: Optional[int], pairing_mode: str, include_unpaired: bool,
                         recycling_steps: int, sampling_steps: int, 
                         diffusion_samples: int, write_full_pae: bool, write_full_pde: bool,
                         output_format: str):
    """
    Predict multimer structure from ColabFold A3M monomer MSA files.
    
    This command performs the complete workflow:
    1. Converts A3M files to paired MSA format (ColabFold-style)
    2. Submits prediction to Boltz2 NIM
    3. Saves the predicted structure as CIF file
    
    PAIRING MODE (ColabFold-compatible):
    
    \b
    - auto (default): Auto-detects if TaxIDs are present in headers
    - taxid: Force TaxID-based pairing (requires OX= or species codes)
    - uniref: Force UniRef cluster ID pairing (all ColabFold output)
    
    Examples:
    
    \b
    # Predict heterodimer from two A3M files (auto-detect pairing)
    boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B
    
    \b
    # Predict with specific output file
    boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B -o my_complex.cif
    
    \b
    # Use UniRef pairing for standard ColabFold output
    boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B --pairing-mode uniref
    
    \b
    # Predict trimer with higher quality settings
    boltz2 multimer-msa a.a3m b.a3m c.a3m -c A,B,C --sampling-steps 400
    
    \b
    # Limit paired sequences for faster prediction
    boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B --max-pairs 100
    """
    import asyncio
    from ..a3m import convert_a3m_to_multimer_csv, create_paired_msa_per_chain
    from ..models import Polymer, PredictionRequest
    
    # Parse chain IDs
    chain_id_list = [c.strip() for c in chain_ids.split(',')]
    
    if len(chain_id_list) != len(a3m_files):
        print_error(f"Number of chain IDs ({len(chain_id_list)}) must match number of A3M files ({len(a3m_files)})")
        raise click.Abort()
    
    if len(a3m_files) < 2:
        print_error("At least 2 A3M files are required for multimer prediction")
        raise click.Abort()
    
    # Set default output path
    if output is None:
        output = "complex.cif"
    
    # Create mapping of chain IDs to file paths
    a3m_file_dict = {chain_id: Path(filepath) for chain_id, filepath in zip(chain_id_list, a3m_files)}
    
    # Convert pairing_mode to use_tax_id
    use_tax_id = None  # auto-detect (default)
    if pairing_mode == 'taxid':
        use_tax_id = True
    elif pairing_mode == 'uniref':
        use_tax_id = False
    
    console.print("\n[bold cyan]Boltz2 Multimer Prediction from A3M Files[/bold cyan]\n")
    
    # Show multi-endpoint info if enabled
    if ctx.obj and ctx.obj.get('multi_endpoint'):
        endpoints = [url.strip() for url in ctx.obj['base_url'].split(',')]
        print_info(f"Multi-endpoint mode: {len(endpoints)} endpoints")
        print_info(f"Load balance strategy: {ctx.obj.get('load_balance_strategy', 'least_loaded')}")
    
    print_info("Input A3M files:")
    for chain_id, filepath in a3m_file_dict.items():
        print(f"  Chain {chain_id}: {filepath}")
    print_info(f"Output: {output}")
    print_info(f"Pairing mode: {pairing_mode}")
    print_info(f"Recycling steps: {recycling_steps}")
    print_info(f"Sampling steps: {sampling_steps}")
    print_info(f"Diffusion samples: {diffusion_samples}")
    
    async def run_prediction():
        # Step 1: Convert A3M files to paired MSA
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Converting A3M files to paired MSA...", total=None)
            
            result = convert_a3m_to_multimer_csv(
                a3m_files=a3m_file_dict,
                pairing_strategy='greedy',
                use_tax_id=use_tax_id,
                include_unpaired=include_unpaired,
                max_pairs=max_pairs
            )
            
            unpaired_msg = " (+ unpaired)" if include_unpaired else ""
            progress.update(task, description=f"✓ Paired {result.num_pairs} sequences{unpaired_msg}")
        
        print_info(f"Paired sequences: {result.num_pairs}")
        
        # Save CSV files if requested
        if save_csv:
            output_path = Path(output)
            csv_dir = output_path.parent
            csv_dir.mkdir(parents=True, exist_ok=True)
            base_name = output_path.stem
            
            for chain_id, csv_content in result.csv_per_chain.items():
                csv_path = csv_dir / f"{base_name}_chain_{chain_id}.csv"
                csv_path.write_text(csv_content)
                print_info(f"CSV saved: {csv_path}")
        
        # Step 2: Create per-chain MSA structures
        msa_per_chain = create_paired_msa_per_chain(result)
        
        # Step 3: Create polymers
        polymers = []
        for chain_id in chain_id_list:
            polymer = Polymer(
                id=chain_id,
                molecule_type="protein",
                sequence=result.query_sequences[chain_id],
                msa=msa_per_chain[chain_id]
            )
            polymers.append(polymer)
            print_info(f"Chain {chain_id}: {len(polymer.sequence)} residues")
        
        # Step 4: Create prediction request
        request = PredictionRequest(
            polymers=polymers,
            recycling_steps=recycling_steps,
            sampling_steps=sampling_steps,
            diffusion_samples=diffusion_samples,
            write_full_pae=write_full_pae,
            write_full_pde=write_full_pde
        )
        
        # Step 5: Get client (supports multi-endpoint mode)
        client = create_client(ctx)
        
        # Check health (multi-endpoint checks all endpoints)
        print_info("Checking server health...")
        health = await client.health_check()
        if hasattr(health, 'status'):
            print_info(f"Server status: {health.status}")
        else:
            # Multi-endpoint returns list of health results
            print_info(f"All endpoints healthy")
        
        # Submit prediction
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Running prediction...", total=None)
            
            response = await client.predict(request, save_structures=False)
            
            progress.update(task, description="✓ Prediction complete")
        
        # Step 6: Save structure and outputs
        if response.structures:
            structure = response.structures[0]
            cif_content = structure.structure if hasattr(structure, 'structure') else str(structure)
            
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle output format
            if output_format == 'pdb':
                # Save as CIF first, then convert
                cif_temp_path = output_path.with_suffix('.cif')
                cif_temp_path.write_text(cif_content)
                
                # Convert to PDB
                from ..utils import convert_cif_to_pdb
                pdb_path = output_path.with_suffix('.pdb')
                convert_cif_to_pdb(cif_temp_path, pdb_path)
                print_success(f"Structure saved to: {pdb_path}")
                
                # Also keep the CIF if save_all is enabled, otherwise remove
                if not save_all:
                    cif_temp_path.unlink()
                else:
                    print_info(f"CIF also saved: {cif_temp_path}")
            else:
                output_path.write_text(cif_content)
                print_success(f"Structure saved to: {output_path}")
            
            atom_count = cif_content.count('ATOM ')
            print_info(f"Total atoms: {atom_count}")
            
            # Save additional structures if multiple samples
            if len(response.structures) > 1:
                from ..utils import convert_cif_to_pdb
                for i, struct in enumerate(response.structures[1:], start=2):
                    cif = struct.structure if hasattr(struct, 'structure') else str(struct)
                    if output_format == 'pdb':
                        extra_cif = output_path.with_stem(f"{output_path.stem}_{i}").with_suffix('.cif')
                        extra_cif.write_text(cif)
                        extra_pdb = output_path.with_stem(f"{output_path.stem}_{i}").with_suffix('.pdb')
                        convert_cif_to_pdb(extra_cif, extra_pdb)
                        print_info(f"Additional structure: {extra_pdb}")
                        if not save_all:
                            extra_cif.unlink()
                    else:
                        extra_path = output_path.with_stem(f"{output_path.stem}_{i}")
                        extra_path.write_text(cif)
                        print_info(f"Additional structure: {extra_path}")
            
            # Save all outputs if requested
            if save_all:
                # Collect all scores and metrics
                scores = {
                    'confidence_scores': response.confidence_scores,
                    'ptm_scores': response.ptm_scores,
                    'iptm_scores': response.iptm_scores,
                    'complex_plddt_scores': response.complex_plddt_scores,
                    'complex_iplddt_scores': response.complex_iplddt_scores,
                    'complex_pde_scores': response.complex_pde_scores,
                    'complex_ipde_scores': response.complex_ipde_scores,
                    'chains_ptm_scores': response.chains_ptm_scores,
                    'pair_chains_iptm_scores': response.pair_chains_iptm_scores,
                    'ligand_iptm_scores': response.ligand_iptm_scores,
                    'protein_iptm_scores': response.protein_iptm_scores,
                    'metrics': response.metrics,
                }
                
                # Remove None values
                scores = {k: v for k, v in scores.items() if v is not None}
                
                # Save scores as JSON
                scores_path = output_path.with_suffix('.scores.json')
                scores_path.write_text(json.dumps(scores, indent=2))
                print_info(f"Scores saved to: {scores_path}")
                
                # Print key scores
                if response.confidence_scores:
                    print_info(f"Confidence: {response.confidence_scores[0]:.4f}")
                if response.complex_plddt_scores:
                    print_info(f"Complex pLDDT: {response.complex_plddt_scores[0]:.4f}")
                if response.iptm_scores:
                    print_info(f"Interface pTM: {response.iptm_scores[0]:.4f}")
                if response.ptm_scores:
                    print_info(f"pTM: {response.ptm_scores[0]:.4f}")
            
            # Save PAE matrix if available
            if write_full_pae and response.pae:
                pae_path = output_path.with_suffix('.pae.json')
                pae_path.write_text(json.dumps({'pae': response.pae}, indent=2))
                pae_shape = f"{len(response.pae)}x{len(response.pae[0])}x{len(response.pae[0][0])}"
                print_info(f"PAE matrix saved to: {pae_path} (shape: {pae_shape})")
            
            # Save PDE matrix if available
            if write_full_pde and response.pde:
                pde_path = output_path.with_suffix('.pde.json')
                pde_path.write_text(json.dumps({'pde': response.pde}, indent=2))
                pde_shape = f"{len(response.pde)}x{len(response.pde[0])}x{len(response.pde[0][0])}"
                print_info(f"PDE matrix saved to: {pde_path} (shape: {pde_shape})")
        else:
            print_error("No structures returned from prediction")
            raise click.Abort()
        
        return response
    
    try:
        asyncio.run(run_prediction())
        print_success("\n✓ Multimer prediction complete!")
    except Exception as e:
        print_error(f"Prediction failed: {e}")
        raise click.Abort()


