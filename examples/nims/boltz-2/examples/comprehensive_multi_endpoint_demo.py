#!/usr/bin/env python3
"""
Comprehensive Multi-Endpoint Boltz2 NIM Demo

This example demonstrates ALL Boltz2 NIM functionalities with multi-endpoint support:
- Protein structure prediction
- Protein-ligand complex prediction
- Covalent complex prediction
- DNA-protein complex prediction
- YAML-based prediction
- Virtual screening
- Health monitoring
- Load balancing strategies

Run multiple Boltz-2 NIM instances on different ports to test:
bash
# Terminal 1
docker run --rm --gpus device=0 -p 8000:8000 nvcr.io/nim/mit/boltz-2:latest

# Terminal 2  
docker run --rm --gpus device=1 -p 8001:8000 nvcr.io/nim/mit/boltz-2:latest

# Terminal 3
docker run --rm --gpus device=2 -p 8002:8000 nvcr.io/nim/mit/boltz-2:latest
"""

import asyncio
import os
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

from boltz2_client import (
    MultiEndpointClient,
    LoadBalanceStrategy,
    EndpointConfig,
    VirtualScreening,
    CompoundLibrary,
    PredictionRequest,
    Polymer,
    Ligand,
    PocketConstraint
)

# Initialize console for pretty output
console = Console()

# Sample protein sequence (CDK2 kinase)
CDK2_SEQUENCE = """
MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG
KQDQQPQGDSGSSQFPTDAASSAFQGLMEGFAPDMKCGVCITWIYAAFQKVAAEFADSEPQLISG
YAFEHFHDERPGGVAPLPLGVGNVLSRSQNRVTVWDVKRESCVQEAYGVGVDDVKDICEELAEEL
AVEPVTDSDVDIDGVNHMFVRVQRQIEQNPAQDAGTYISRAKRKLGSRPFRSIEIEIERPVTTTI
""".replace('\n', '').replace(' ', '')

# Sample compounds for screening
SAMPLE_COMPOUNDS = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
    {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1"},
    {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"},
    {"name": "Naproxen", "smiles": "COC1=CC=C2C=C(C=CC2=C1)C(C)C(=O)O"},
]

async def demo_multi_endpoint_protein_structure(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint protein structure prediction."""
    console.print(Panel.fit("🔬 Multi-Endpoint Protein Structure Prediction", style="bold blue"))
    
    try:
        result = await multi_client.predict_protein_structure(
            sequence=CDK2_SEQUENCE,
            polymer_id="A",
            recycling_steps=2,
            sampling_steps=30,
            diffusion_samples=1,
            step_scale=1.638
        )
        
        console.print(f"✅ Protein structure prediction completed!")
        console.print(f"   Generated {len(result.structures)} structure(s)")
        if result.confidence_scores:
            avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
            console.print(f"   Average confidence: {avg_confidence:.3f}")
            
    except Exception as e:
        console.print(f"❌ Protein structure prediction failed: {e}", style="red")

async def demo_multi_endpoint_protein_ligand(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint protein-ligand complex prediction."""
    console.print(Panel.fit("💊 Multi-Endpoint Protein-Ligand Complex Prediction", style="bold green"))
    
    try:
        result = await multi_client.predict_protein_ligand_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
            protein_id="A",
            ligand_id="LIG",
            recycling_steps=2,
            sampling_steps=30,
            pocket_residues=[10, 11, 12, 13, 14]
        )
        
        console.print(f"✅ Protein-ligand complex prediction completed!")
        console.print(f"   Generated {len(result.structures)} structure(s)")
        if result.confidence_scores:
            avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
            console.print(f"   Average confidence: {avg_confidence:.3f}")
            
    except Exception as e:
        console.print(f"❌ Protein-ligand complex prediction failed: {e}", style="red")

async def demo_multi_endpoint_covalent_complex(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint covalent complex prediction."""
    console.print(Panel.fit("🔗 Multi-Endpoint Covalent Complex Prediction", style="bold magenta"))
    
    try:
        result = await multi_client.predict_covalent_complex(
            protein_sequence=CDK2_SEQUENCE,
            ligand_ccd="ASP",  # Example CCD code
            covalent_bonds=[(12, "SG", "C22")],
            protein_id="A",
            ligand_id="LIG",
            recycling_steps=2,
            sampling_steps=30
        )
        
        console.print(f"✅ Covalent complex prediction completed!")
        console.print(f"   Generated {len(result.structures)} structure(s)")
        if result.confidence_scores:
            avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
            console.print(f"   Average confidence: {avg_confidence:.3f}")
            
    except Exception as e:
        console.print(f"❌ Covalent complex prediction failed: {e}", style="red")

async def demo_multi_endpoint_dna_protein(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint DNA-protein complex prediction."""
    console.print(Panel.fit("🧬 Multi-Endpoint DNA-Protein Complex Prediction", style="bold cyan"))
    
    try:
        # Sample DNA sequence
        dna_sequence = "ATCGATCGATCGATCG"
        
        result = await multi_client.predict_dna_protein_complex(
            protein_sequences=[CDK2_SEQUENCE],
            dna_sequences=[dna_sequence],
            protein_ids=["A"],
            dna_ids=["D"],
            recycling_steps=2,
            sampling_steps=30
        )
        
        console.print(f"✅ DNA-protein complex prediction completed!")
        console.print(f"   Generated {len(result.structures)} structure(s)")
        if result.confidence_scores:
            avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
            console.print(f"   Average confidence: {avg_confidence:.3f}")
            
    except Exception as e:
        console.print(f"❌ DNA-protein complex prediction failed: {e}", style="red")

async def demo_multi_endpoint_yaml_prediction(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint YAML-based prediction."""
    console.print(Panel.fit("📄 Multi-Endpoint YAML-Based Prediction", style="bold yellow"))
    
    try:
        # Create a YAML config equivalent
        config = {
            "polymers": [
                {
                    "id": "A",
                    "molecule_type": "protein",
                    "sequence": CDK2_SEQUENCE
                }
            ],
            "recycling_steps": 2,
            "sampling_steps": 30,
            "diffusion_samples": 1
        }
        
        result = await multi_client.predict_from_yaml_config(
            config=config,
            save_structures=True
        )
        
        console.print(f"✅ YAML-based prediction completed!")
        console.print(f"   Generated {len(result.structures)} structure(s)")
        if result.confidence_scores:
            avg_confidence = sum(result.confidence_scores) / len(result.confidence_scores)
            console.print(f"   Average confidence: {avg_confidence:.3f}")
            
    except Exception as e:
        console.print(f"❌ YAML-based prediction failed: {e}", style="red")

async def demo_multi_endpoint_virtual_screening(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint virtual screening."""
    console.print(Panel.fit("🔍 Multi-Endpoint Virtual Screening", style="bold red"))
    
    try:
        # Create virtual screening instance with multi-endpoint client
        vs = VirtualScreening(client=multi_client)
        
        # Create compound library
        library = CompoundLibrary(SAMPLE_COMPOUNDS)
        
        # Run screening
        result = vs.screen(
            target_sequence=CDK2_SEQUENCE,
            compound_library=library,
            target_name="CDK2",
            predict_affinity=True,
            recycling_steps=2,
            sampling_steps=30,
            diffusion_samples=1,
            pocket_residues=[10, 11, 12, 13, 14],
            pocket_radius=8.0
        )
        
        console.print(f"✅ Virtual screening completed!")
        console.print(f"   Screened {len(result.results)} compounds")
        console.print(f"   Duration: {result.duration_seconds:.1f} seconds")
        
        # Show top results
        if result.results:
            top_result = result.results[0]
            console.print(f"   Top compound: {top_result.get('name', 'Unknown')}")
            if 'predicted_pic50' in top_result:
                console.print(f"   Predicted pIC50: {top_result['predicted_pic50']:.3f}")
            
    except Exception as e:
        console.print(f"❌ Virtual screening failed: {e}", style="red")

async def demo_multi_endpoint_health_monitoring(multi_client: MultiEndpointClient):
    """Demonstrate multi-endpoint health monitoring."""
    console.print(Panel.fit("🏥 Multi-Endpoint Health Monitoring", style="bold white"))
    
    try:
        # Check health of all endpoints
        health_status = await multi_client.health_check()
        console.print(f"Overall Health Status: {health_status.status}")
        console.print(f"Details: {health_status.details}")
        
        # Get detailed status
        status = multi_client.get_status()
        console.print(f"Load Balancing Strategy: {status['strategy']}")
        
        # Print endpoint status table
        multi_client.print_status()
        
    except Exception as e:
        console.print(f"❌ Health monitoring failed: {e}", style="red")

async def demo_load_balancing_strategies():
    """Demonstrate different load balancing strategies."""
    console.print(Panel.fit("⚖️ Load Balancing Strategy Comparison", style="bold blue"))
    
    strategies = [
        LoadBalanceStrategy.ROUND_ROBIN,
        LoadBalanceStrategy.RANDOM,
        LoadBalanceStrategy.LEAST_LOADED,
        LoadBalanceStrategy.WEIGHTED
    ]
    
    for strategy in strategies:
        console.print(f"\n🔧 Testing {strategy.value.replace('_', ' ').title()} Strategy:")
        
        try:
            # Create client with specific strategy
            test_client = MultiEndpointClient(
                endpoints=[
                    "http://localhost:8000",
                    "http://localhost:8001", 
                    "http://localhost:8002"
                ],
                strategy=strategy
            )
            
            # Test health check
            health = await test_client.health_check()
            console.print(f"   Health Status: {health.status}")
            
            await test_client.close()
            
        except Exception as e:
            console.print(f"   ❌ Failed: {e}", style="red")

async def main():
    """Main demo function."""
    console.print(Panel.fit("🚀 Comprehensive Multi-Endpoint Boltz2 NIM Demo", style="bold green"))
    console.print("This demo showcases ALL Boltz2 NIM functionalities with multi-endpoint support!\n")
    
    # Configure multiple endpoints
    console.print("🔧 Setting up multi-endpoint client...")
    endpoints = [
        EndpointConfig(base_url="http://localhost:8000", weight=1.0),
        EndpointConfig(base_url="http://localhost:8001", weight=1.0),
        EndpointConfig(base_url="http://localhost:8002", weight=1.0),
    ]
    
    # Create multi-endpoint client
    multi_client = MultiEndpointClient(
        endpoints=endpoints,
        strategy=LoadBalanceStrategy.LEAST_LOADED,
        health_check_interval=30.0,
        timeout=300.0
    )
    
    try:
        # Run all demos
        await demo_multi_endpoint_health_monitoring(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_multi_endpoint_protein_structure(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_multi_endpoint_protein_ligand(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_multi_endpoint_covalent_complex(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_multi_endpoint_dna_protein(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_multi_endpoint_yaml_prediction(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_multi_endpoint_virtual_screening(multi_client)
        console.print("\n" + "="*80 + "\n")
        
        await demo_load_balancing_strategies()
        
    finally:
        # Clean up
        await multi_client.close()
    
    console.print("\n🎉 Demo completed! All Boltz2 NIM functionalities now support multi-endpoint load balancing!")

if __name__ == "__main__":
    # Check if endpoints are available
    console.print("⚠️  Make sure you have multiple Boltz-2 NIM instances running:")
    console.print("   docker run --rm --gpus device=0 -p 8000:8000 nvcr.io/nim/mit/boltz-2:latest")
    console.print("   docker run --rm --gpus device=1 -p 8001:8000 nvcr.io/nim/mit/boltz-2:latest")
    console.print("   docker run --rm --gpus device=2 -p 8002:8000 nvcr.io/nim/mit/boltz-2:latest\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        console.print(f"\n❌ Demo failed: {e}", style="red")
