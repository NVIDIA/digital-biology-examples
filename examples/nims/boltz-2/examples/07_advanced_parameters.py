#!/usr/bin/env python3
# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Example 7: Advanced Parameter Control

This example demonstrates how to use advanced parameters for fine-tuning
Boltz-2 predictions, including diffusion parameters, sampling control,
and specialized options.
"""

import asyncio
import json
from pathlib import Path
from boltz2_client import Boltz2Client
from boltz2_client.models import PredictionRequest, Polymer, Ligand, Contact, PocketConstraint


async def diffusion_parameter_exploration():
    """Example of exploring different diffusion parameters."""
    print("⚙️ Diffusion Parameter Exploration Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Test sequence
    sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    # Different parameter combinations to test
    parameter_sets = [
        {
            "name": "Fast (Low Quality)",
            "recycling_steps": 1,
            "sampling_steps": 10,
            "diffusion_samples": 1,
            "step_scale": 1.0
        },
        {
            "name": "Standard",
            "recycling_steps": 3,
            "sampling_steps": 50,
            "diffusion_samples": 1,
            "step_scale": 1.638
        },
        {
            "name": "High Quality",
            "recycling_steps": 5,
            "sampling_steps": 100,
            "diffusion_samples": 2,
            "step_scale": 1.638
        },
        {
            "name": "Maximum Quality",
            "recycling_steps": 6,
            "sampling_steps": 200,
            "diffusion_samples": 3,
            "step_scale": 1.2
        },
        {
            "name": "High Diversity",
            "recycling_steps": 4,
            "sampling_steps": 75,
            "diffusion_samples": 5,
            "step_scale": 0.8  # Lower step scale for more diversity
        }
    ]
    
    print(f"Testing sequence: {sequence}")
    print(f"Length: {len(sequence)} residues\n")
    
    results = []
    
    for i, params in enumerate(parameter_sets, 1):
        print(f"--- Test {i}: {params['name']} ---")
        print(f"Parameters: recycling={params['recycling_steps']}, "
              f"sampling={params['sampling_steps']}, "
              f"diffusion={params['diffusion_samples']}, "
              f"step_scale={params['step_scale']}")
        
        try:
            import time
            start_time = time.time()
            
            result = await client.predict_protein_structure(
                sequence=sequence,
                polymer_id="A",
                recycling_steps=params['recycling_steps'],
                sampling_steps=params['sampling_steps'],
                diffusion_samples=params['diffusion_samples'],
                step_scale=params['step_scale']
            )
            
            end_time = time.time()
            prediction_time = end_time - start_time
            
            results.append({
                "name": params['name'],
                "params": params,
                "confidence": result.confidence_scores[0],
                "time": prediction_time,
                "structures": len(result.structures)
            })
            
            print(f"✅ Completed in {prediction_time:.1f}s")
            print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
            print(f"📁 Structures: {len(result.structures)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "name": params['name'],
                "params": params,
                "error": str(e)
            })
        
        print()
    
    # Summary comparison
    print("📊 Parameter Comparison Summary:")
    print(f"{'Test':<20} {'Time (s)':<10} {'Confidence':<12} {'Structures':<12}")
    print("-" * 60)
    
    for result in results:
        if 'error' not in result:
            print(f"{result['name']:<20} {result['time']:<10.1f} "
                  f"{result['confidence']:<12.3f} {result['structures']:<12}")
        else:
            print(f"{result['name']:<20} {'Error':<10} {'N/A':<12} {'N/A':<12}")


async def advanced_molecular_systems():
    """Example of advanced molecular system configurations."""
    print("⚙️ Advanced Molecular Systems Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Complex system: Multi-polymer with ligands and constraints
    print("--- Complex Multi-Component System ---")
    
    try:
        # Create complex system
        polymers = [
            Polymer(
                id="A",
                molecule_type="protein",
                sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
            ),
            Polymer(
                id="B",
                molecule_type="dna",
                sequence="ATCGATCGATCGATCG"
            )
        ]
        
        ligands = [
            Ligand(id="L1", smiles="CC(=O)O"),
            Ligand(id="L2", smiles="CCO")
        ]
        
        # Pocket constraint for ligand binding
        constraints = [
            PocketConstraint(
                binder="L1",
                contacts=[Contact(id="A", residue_index=r) for r in [10, 15, 20, 25]]
            )
        ]
        
        print(f"System components:")
        print(f"  - Protein A: {len(polymers[0].sequence)} residues")
        print(f"  - DNA B: {len(polymers[1].sequence)} bp")
        print(f"  - Ligand L1: {ligands[0].smiles}")
        print(f"  - Ligand L2: {ligands[1].smiles}")
        print(f"  - Pocket constraint: L1 → A residues {[c.residue for c in constraints[0].contacts]}")
        
        result = await client.predict_with_advanced_parameters(
            polymers=polymers,
            ligands=ligands,
            constraints=constraints,
            recycling_steps=5,
            sampling_steps=100,
            diffusion_samples=2,
            step_scale=1.5,
            without_potentials=False,
            concatenate_msas=True
        )
        
        print(f"\n✅ Complex system prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def json_configuration_advanced():
    """Example of using JSON configuration files for advanced setups."""
    print("⚙️ JSON Configuration for Advanced Setups Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Create advanced JSON configuration
    config = {
        "polymers": [
            {
                "id": "A",
                "molecule_type": "protein",
                "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "cyclic": False,
                "modifications": []
            }
        ],
        "ligands": [
            {
                "id": "LIG",
                "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
            }
        ],
        "constraints": [
            {
                "binder": "LIG",
                "contacts": [
                    {"id": "A", "residue_index": 10},
                    {"id": "A", "residue_index": 15},
                    {"id": "A", "residue_index": 20},
                    {"id": "A", "residue_index": 25},
                    {"id": "A", "residue_index": 30}
                ]
            }
        ],
        "recycling_steps": 5,
        "sampling_steps": 150,
        "diffusion_samples": 3,
        "step_scale": 1.2,
        "without_potentials": False,
        "concatenate_msas": False,
        "output_format": "mmcif"
    }
    
    # Save configuration to file
    config_path = Path("advanced_config.json")
    config_path.write_text(json.dumps(config, indent=2))
    
    print(f"Created advanced JSON configuration: {config_path}")
    print(f"Configuration includes:")
    print(f"  - 1 protein ({len(config['polymers'][0]['sequence'])} residues)")
    print(f"  - 1 ligand (aspirin)")
    print(f"  - Pocket constraint ({len(config['constraints'][0]['contacts'])} residues)")
    print(f"  - High-quality parameters (recycling=5, sampling=150, diffusion=3)")
    
    try:
        # Load and use the configuration
        request = PredictionRequest(**config)
        
        print(f"\n🔄 Running prediction from JSON config...")
        result = await client.predict(request, save_structures=False)
        
        print(f"✅ JSON configuration prediction completed!")
        print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
        print(f"📁 Generated {len(result.structures)} structure(s)")
        
        # Show configuration details
        print(f"\n📋 Configuration Summary:")
        print(f"   Polymers: {len(request.polymers)}")
        print(f"   Ligands: {len(request.ligands) if request.ligands else 0}")
        print(f"   Constraints: {len(request.constraints) if request.constraints else 0}")
        print(f"   Recycling steps: {request.recycling_steps}")
        print(f"   Sampling steps: {request.sampling_steps}")
        print(f"   Diffusion samples: {request.diffusion_samples}")
        print(f"   Step scale: {request.step_scale}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        if config_path.exists():
            config_path.unlink()


async def specialized_options():
    """Example of specialized prediction options."""
    print("⚙️ Specialized Prediction Options Example\n")
    
    client = Boltz2Client(base_url="http://localhost:8000")
    
    sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    
    # Test different specialized options
    options = [
        {
            "name": "Without Potentials",
            "without_potentials": True,
            "recycling_steps": 3,
            "sampling_steps": 50
        },
        {
            "name": "High Temperature (More Diversity)",
            "without_potentials": False,
            "step_scale": 0.5,  # Lower = higher diversity
            "recycling_steps": 4,
            "sampling_steps": 75
        },
        {
            "name": "Low Temperature (More Focused)",
            "without_potentials": False,
            "step_scale": 3.0,  # Higher = more focused
            "recycling_steps": 4,
            "sampling_steps": 75
        }
    ]
    
    for option in options:
        print(f"--- {option['name']} ---")
        
        try:
            result = await client.predict_protein_structure(
                sequence=sequence,
                polymer_id="A",
                without_potentials=option.get('without_potentials', False),
                step_scale=option.get('step_scale', 1.638),
                recycling_steps=option['recycling_steps'],
                sampling_steps=option['sampling_steps']
            )
            
            print(f"✅ Prediction completed!")
            print(f"📊 Confidence: {result.confidence_scores[0]:.3f}")
            print(f"📁 Generated {len(result.structures)} structure(s)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()


async def main():
    """Run all advanced parameter examples."""
    await diffusion_parameter_exploration()
    print("\n" + "="*60 + "\n")
    await advanced_molecular_systems()
    print("\n" + "="*60 + "\n")
    await json_configuration_advanced()
    print("\n" + "="*60 + "\n")
    await specialized_options()


if __name__ == "__main__":
    asyncio.run(main()) 