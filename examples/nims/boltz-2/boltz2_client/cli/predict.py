# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""Structure prediction commands (protein, ligand, covalent, dna_protein, advanced, yaml)."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import click
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
from rich.table import Table
import yaml as pyyaml

from ..client import Boltz2Client
from ..models import (
    PredictionRequest, Polymer, Ligand, BondConstraint,
    Atom, AlignmentFileRecord,
)
from . import cli, console, print_success, print_error, print_info, print_warning


def create_client(ctx):
    """Delegate to the package-level create_client (patchable by tests)."""
    return sys.modules[__package__].create_client(ctx)


@cli.command()
@click.argument('sequence')
@click.option('--polymer-id', default='A', help='Polymer identifier (default: A)')
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10), 
              help='Number of recycling steps (1-10, default: 3)')
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000),
              help='Number of sampling steps (10-1000, default: 50)')
@click.option('--diffusion-samples', default=1, type=click.IntRange(1, 25),
              help='Number of diffusion samples (1-25, default: 1)')
@click.option('--step-scale', default=1.638, type=click.FloatRange(0.5, 5.0),
              help='Step scale for diffusion sampling (0.5-5.0, default: 1.638)')
@click.option('--msa-file', multiple=True, type=(str, click.Choice(['a3m', 'csv', 'fasta'])),
              help='MSA file and format (can be specified multiple times)')
@click.option('--output-dir', type=click.Path(), default='.', help='Directory to save output files (structure_0.cif, prediction_metadata.json). Default: current directory')
@click.option('--no-save', is_flag=True, help='Do not save structure files')
@click.option('--write-full-pae', is_flag=True, default=False,
              help='Output full PAE (Predicted Aligned Error) matrix as JSON')
@click.option('--write-full-pde', is_flag=True, default=False,
              help='Output full PDE (Predicted Distance Error) matrix as JSON')
@click.option('--output-format', type=click.Choice(['cif', 'pdb']), default='cif',
              help='Output structure format: cif (default) or pdb')
@click.pass_context
def protein(ctx, sequence: str, polymer_id: str, recycling_steps: int, sampling_steps: int,
           diffusion_samples: int, step_scale: float, msa_file: List[Tuple[str, str]], 
           output_dir: str, no_save: bool, write_full_pae: bool, write_full_pde: bool,
           output_format: str):
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
            if write_full_pae:
                print_info(f"            write_full_pae=True")
            if write_full_pde:
                print_info(f"            write_full_pde=True")
            
            if msa_files:
                print_info(f"Using {len(msa_files)} MSA file(s)")
            
            # Build MSA if files provided
            msa_dict = None
            if msa_files:
                msa_dict = {}
                for i, (file_path, format_type) in enumerate(msa_files):
                    with open(file_path, "r") as fh:
                        content = fh.read()
                    msa_record = AlignmentFileRecord(
                        alignment=content,
                        format=format_type,
                        rank=i
                    )
                    db_name = f"msa_{i}" if len(msa_files) > 1 else "default"
                    if db_name not in msa_dict:
                        msa_dict[db_name] = {}
                    msa_dict[db_name][format_type] = msa_record
            
            # Create polymer and request
            polymer = Polymer(
                id=polymer_id,
                molecule_type="protein",
                sequence=sequence,
                msa=msa_dict
            )
            
            request = PredictionRequest(
                polymers=[polymer],
                recycling_steps=recycling_steps,
                sampling_steps=sampling_steps,
                diffusion_samples=diffusion_samples,
                step_scale=step_scale,
                write_full_pae=write_full_pae,
                write_full_pde=write_full_pde
            )
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Making prediction...", total=None)
                
                def progress_callback(message: str):
                    progress.update(task, description=message)
                
                result = await client.predict(
                    request,
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
                
                # Convert to PDB if requested
                if output_format == 'pdb':
                    from ..utils import convert_cif_to_pdb
                    for i in range(len(result.structures)):
                        cif_path = Path(output_dir) / f"structure_{i}.cif"
                        if cif_path.exists():
                            pdb_path = Path(output_dir) / f"structure_{i}.pdb"
                            convert_cif_to_pdb(cif_path, pdb_path)
                            print_info(f"Converted to PDB: {pdb_path}")
            
            # Save PAE matrix if requested and available
            if write_full_pae and result.pae:
                import json
                pae_path = Path(output_dir) / f"structure_{polymer_id}.pae.json"
                pae_path.write_text(json.dumps({'pae': result.pae}, indent=2))
                pae_shape = f"{len(result.pae)}x{len(result.pae[0])}x{len(result.pae[0][0])}"
                print_info(f"PAE matrix saved to: {pae_path} (shape: {pae_shape})")
            
            # Save PDE matrix if requested and available
            if write_full_pde and result.pde:
                import json
                pde_path = Path(output_dir) / f"structure_{polymer_id}.pde.json"
                pde_path.write_text(json.dumps({'pde': result.pde}, indent=2))
                pde_shape = f"{len(result.pde)}x{len(result.pde[0])}x{len(result.pde[0][0])}"
                print_info(f"PDE matrix saved to: {pde_path} (shape: {pde_shape})")
            
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
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10))
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000))
@click.option('--predict-affinity', is_flag=True, help='Enable affinity prediction for the ligand')
@click.option('--sampling-steps-affinity', default=200, type=click.IntRange(10, 1000), help='Sampling steps for affinity prediction (default: 200)')
@click.option('--diffusion-samples-affinity', default=5, type=click.IntRange(1, 10), help='Diffusion samples for affinity prediction (default: 5)')
@click.option('--affinity-mw-correction', is_flag=True, help='Apply molecular weight correction to affinity prediction')
@click.option('--msa-file', multiple=True, type=(str, click.Choice(['a3m', 'csv', 'fasta'])),
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
                    pocket_residues=pocket_residue_list if pocket_residues else None,
                    recycling_steps=recycling_steps,
                    sampling_steps=sampling_steps,
                    predict_affinity=predict_affinity,
                    sampling_steps_affinity=sampling_steps_affinity,
                    diffusion_samples_affinity=diffusion_samples_affinity,
                    affinity_mw_correction=affinity_mw_correction,
                    save_structures=False,
                    msa_files=msa_files if msa_files else None,
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
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10))
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
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10))
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
@click.option('--recycling-steps', default=3, type=click.IntRange(1, 10))
@click.option('--sampling-steps', default=50, type=click.IntRange(10, 1000))
@click.option('--diffusion-samples', default=1, type=click.IntRange(1, 25))
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
                
                from ..models import YAMLConfig
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
                                '.fasta': 'fasta',
                                '.csv': 'csv'
                            }
                            format_type = format_map.get(msa_path.suffix.lower(), 'a3m')
                            
                            from ..models import AlignmentFileRecord
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


