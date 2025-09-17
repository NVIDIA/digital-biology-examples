#!/usr/bin/env python3
"""
Comprehensive Multi-Endpoint Stress Test for Boltz2 NIM

This test validates the multi-endpoint client under high load:
- 50 protein structure predictions
- 3 protein sequences × ~50 ligands for complex prediction
- Comprehensive timing and result analysis
- Result saving and summary tables
"""

import asyncio
import time
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pytest
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from boltz2_client import MultiEndpointClient, LoadBalanceStrategy, PredictionRequest, PredictionResponse

# Test data
PROTEIN_SEQUENCES = [
    # Short sequences for quick testing
    "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG",  # CDK2
    "MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRCALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL",  # P53
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT",  # Insulin
    "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVDDGTLLDNYKVPRLQLLKYV",  # Ubiquitin
    "MKLFDSLTVIGAVGNKIGLLYCFLHTSRGKPAIGIDMDRLETKLTLKGCQK",  # Myoglobin
    "MKLFDSLTVIGAVGNKIGLLYCFLHTSRGKPAIGIDMDRLETKLTLKGCQK",  # Myoglobin variant
    "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVDDGTLLDNYKVPRLQLLKYV",  # Ubiquitin variant
    "MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRCALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL",  # P53 variant
    "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG",  # CDK2 variant
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT",  # Insulin variant
]

# Generate 50 sequences by varying the base sequences
def generate_50_sequences():
    sequences = []
    base_seqs = PROTEIN_SEQUENCES * 5  # 5 × 10 = 50
    
    for i, seq in enumerate(base_seqs):
        # Add some variation to make them unique
        if i % 2 == 0:
            seq = seq + "A"  # Add alanine
        if i % 3 == 0:
            seq = seq[:-1] if len(seq) > 1 else seq  # Remove last amino acid
        sequences.append(seq)
    
    return sequences[:50]  # Ensure exactly 50

LIGANDS = [
    "CC(C)(C)OC(=O)N[C@@H](CC1=CC=CC=C1)C(=O)O",  # Boc-phenylalanine
    "CC(C)CC[C@H](NC(=O)OCc1ccccc1)C(=O)O",  # Z-Leucine
    "O=C(O)[C@@H]1CCCN1C(=O)OC(C)(C)C",  # Boc-Proline
    "CC(=O)Nc1ccc(O)cc1",  # Acetaminophen
    "CC(C)Cc1ccc(C(C)C(=O)O)cc1",  # Ibuprofen
    "O=C(O)Cc1ccccc1",  # Phenylacetic acid
    "CC(=O)OC1C(Sc2ccccc2)=C(C(=O)O)N2C(=O)CC2C1(C)C",  # Penicillin G
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
    "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
    "CN(C)c1ccc(C(=C2C=CC(=[N+](C)C)C=C2)c2ccccc2)cc1",  # Crystal violet
    "Cc1ccc(C(C)C)cc1",  # p-Cymene
    "COc1ccc(CC(C)=O)cc1",  # Anisylacetone
    "O=C1CC(c2ccccc2)Oc2ccccc21",  # Flavanone
    "O=C(Cc1ccccc1)Nc1ccccc1",  # N-Phenylphenylacetamide
    "Cc1ccccc1C(=O)O",  # o-Toluic acid
    "O=C(O)c1ccc(O)c(O)c1",  # Protocatechuic acid
    "CC(C)(C)c1ccc(O)cc1",  # 4-tert-Butylphenol
    "O=C(O)C=Cc1ccccc1",  # Cinnamic acid
    "c1ccc2c(c1)OCO2",  # 1,3-Benzodioxole
    "O=C(O)c1cccnc1",  # Nicotinic acid
    "COc1ccccc1",  # Anisole
    "CC(C)=O",  # Acetone
    "CCO",  # Ethanol
    "CC(C)O",  # Isopropanol
    "c1ccccc1",  # Benzene
    "Cc1ccccc1",  # Toluene
    "CC(=O)O",  # Acetic acid
    "O=C=O",  # Carbon dioxide
    "O",  # Water
    "CCCCCl",  # 1-Chlorobutane
    "O=C(O)CCc1ccccc1",  # Hydrocinnamic acid
    "COc1ccc(C=O)cc1",  # p-Anisaldehyde
    "Cc1ccc(C)cc1",  # p-Xylene
    "O=Cc1ccccc1",  # Benzaldehyde
    "O=C(c1ccccc1)c1ccccc1",  # Benzophenone
    "CC(=O)c1ccccc1",  # Acetophenone
    "COC(=O)c1ccccc1",  # Methyl benzoate
    "CCOc1ccccc1",  # Phenetole
    "c1ccc(Cl)cc1",  # Chlorobenzene
    "CC(C)(C)O",  # tert-Butanol
    "CCN(CC)CC",  # Triethylamine
    "C1CCCCC1",  # Cyclohexane
    "C1CCOC1",  # Tetrahydrofuran
    "CN(C)C=O",  # N,N-Dimethylformamide
    "CC#N",  # Acetonitrile
    "CS(C)=O",  # Dimethyl sulfoxide
    "ClCCl",  # Dichloromethane
    "ClC(Cl)Cl",  # Chloroform
    "ClC(Cl)(Cl)Cl",  # Carbon tetrachloride
]

# Test proteins for ligand complex prediction
TEST_PROTEINS = [
    "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLG",  # CDK2
    "MNIFEMLRIDEGLRLKIYKDTEGYYTIGIGHLLTKSPSLNAAKSELDKAIGRNTNGVITKDEAEKLFNQDVDAAVRGILRNAKLKPVYDSLDAVRRCALINMVFQMGETGVAGFTNSLRMLQQKRWDEAAVNLAKSRWYNQTPNRAKRVITTFRTGTWDAYKNL",  # P53
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKT",  # Insulin
]

# Results storage
class ResultsStorage:
    def __init__(self):
        self.protein_predictions = []
        self.ligand_complex_predictions = []
        self.timing_data = {}
        self.endpoint_usage = {}
        self.errors = []
    
    def add_protein_prediction(self, sequence: str, result: Any, timing: float, endpoint: str):
        self.protein_predictions.append({
            'sequence': sequence[:50] + "..." if len(sequence) > 50 else sequence,
            'sequence_length': len(sequence),
            'result_type': type(result).__name__,
            'success': result is not None,
            'timing': timing,
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_ligand_complex_prediction(self, protein: str, ligand: str, result: Any, timing: float, endpoint: str):
        self.ligand_complex_predictions.append({
            'protein': protein[:50] + "..." if len(protein) > 50 else protein,
            'ligand': ligand[:30] + "..." if len(ligand) > 30 else ligand,
            'result_type': type(result).__name__,
            'success': result is not None,
            'timing': timing,
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat()
        })
    
    def save_results(self, output_dir: Path):
        """Save all results to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed results as JSON
        with open(output_dir / "comprehensive_test_results.json", "w") as f:
            json.dump({
                'protein_predictions': self.protein_predictions,
                'ligand_complex_predictions': self.ligand_complex_predictions,
                'timing_data': self.timing_data,
                'endpoint_usage': self.endpoint_usage,
                'errors': self.errors,
                'summary': self.generate_summary()
            }, f, indent=2)
        
        # Save protein predictions as CSV
        with open(output_dir / "protein_predictions.csv", "w", newline='') as f:
            if self.protein_predictions:
                writer = csv.DictWriter(f, fieldnames=self.protein_predictions[0].keys())
                writer.writeheader()
                writer.writerows(self.protein_predictions)
        
        # Save ligand complex predictions as CSV
        with open(output_dir / "ligand_complex_predictions.csv", "w", newline='') as f:
            if self.ligand_complex_predictions:
                writer = csv.DictWriter(f, fieldnames=self.ligand_complex_predictions[0].keys())
                writer.writeheader()
                writer.writerows(self.ligand_complex_predictions)
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        total_protein = len(self.protein_predictions)
        successful_protein = sum(1 for p in self.protein_predictions if p['success'])
        
        total_ligand = len(self.ligand_complex_predictions)
        successful_ligand = sum(1 for l in self.ligand_complex_predictions if l['success'])
        
        protein_timings = [p['timing'] for p in self.protein_predictions if p['success']]
        ligand_timings = [l['timing'] for l in self.ligand_complex_predictions if l['success']]
        
        return {
            'total_predictions': total_protein + total_ligand,
            'protein_predictions': {
                'total': total_protein,
                'successful': successful_protein,
                'success_rate': f"{(successful_protein/total_protein*100):.1f}%" if total_protein > 0 else "0%",
                'avg_timing': f"{sum(protein_timings)/len(protein_timings):.2f}s" if protein_timings else "N/A",
                'min_timing': f"{min(protein_timings):.2f}s" if protein_timings else "N/A",
                'max_timing': f"{max(protein_timings):.2f}s" if protein_timings else "N/A"
            },
            'ligand_complex_predictions': {
                'total': total_ligand,
                'successful': successful_ligand,
                'success_rate': f"{(successful_ligand/total_ligand*100):.1f}%" if total_ligand > 0 else "0%",
                'avg_timing': f"{sum(ligand_timings)/len(ligand_timings):.2f}s" if ligand_timings else "N/A",
                'min_timing': f"{min(ligand_timings):.2f}s" if ligand_timings else "N/A",
                'max_timing': f"{max(ligand_timings):.2f}s" if ligand_timings else "N/A"
            },
            'endpoint_distribution': self.endpoint_usage,
            'error_count': len(self.errors)
        }

@pytest.mark.asyncio
class TestComprehensiveStress:
    """Comprehensive stress test for multi-endpoint processing."""
    
    @pytest.fixture(scope="class")
    def stress_client(self):
        """Create a multi-endpoint client for stress testing."""
        return MultiEndpointClient(
            endpoints=[
                "http://localhost:8000",
                "http://localhost:8001", 
                "http://localhost:8002",
                "http://localhost:8003"
            ],
            strategy=LoadBalanceStrategy.LEAST_LOADED,  # Changed back to LEAST_LOADED for max resource utilization
            timeout=600.0,  # 10 minutes timeout
            max_retries=3,
            is_async=True
        )
    
    @pytest.fixture(scope="class")
    def test_results(self):
        """Create test results storage."""
        return ResultsStorage()
    
    @pytest.fixture(scope="class")
    def run_dir(self):
        """Base directory to save all artifacts for this test run."""
        base = Path("test_results") / datetime.now().strftime("%Y%m%d_%H%M%S")
        base.mkdir(parents=True, exist_ok=True)
        return base
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_50_protein_sequences(self, stress_client, test_results, run_dir):
        """Test 50 protein structure predictions across multiple endpoints CONCURRENTLY."""
        console = Console()
        sequences = generate_50_sequences()
        proteins_dir = run_dir / "proteins"
        
        console.print(f"\n[bold blue]🧬 Testing 50 Protein Structure Predictions CONCURRENTLY[/bold blue]")
        console.print(f"Sequences: {len(sequences)}")
        console.print(f"Endpoints: {len(stress_client.endpoints)}")
        console.print(f"Strategy: {stress_client.strategy.value}")
        console.print(f"Processing: CONCURRENT (all endpoints working simultaneously)")
        
        start_time = time.time()
        
        # Create concurrent tasks for all sequences
        async def process_single_sequence(sequence, sequence_index):
            """Process a single sequence and return results."""
            try:
                # For LEAST_LOADED strategy, we need to track which endpoint gets selected
                # The strategy will automatically pick the least loaded endpoint
                endpoint = stress_client._select_endpoint()
                endpoint_url = endpoint.endpoint_config.base_url if endpoint else "unknown"
                seq_output_dir = proteins_dir / f"seq_{sequence_index:03d}"
                
                # Make prediction
                pred_start = time.time()
                result = await stress_client.predict_protein_structure(
                    sequence=sequence,
                    recycling_steps=1,
                    sampling_steps=10,  # Minimum required
                    diffusion_samples=1,
                    save_structures=True,
                    output_dir=seq_output_dir
                )
                pred_time = time.time() - pred_start
                
                return {
                    'sequence_index': sequence_index,
                    'sequence': sequence,
                    'result': result,
                    'timing': pred_time,
                    'endpoint': endpoint_url,
                    'success': True,
                    'error': None
                }
                
            except Exception as e:
                return {
                    'sequence_index': sequence_index,
                    'sequence': sequence,
                    'result': None,
                    'timing': 0,
                    'endpoint': 'unknown',
                    'success': False,
                    'error': str(e)
                }
        
        # Process sequences in batches for better control
        # For LEAST_LOADED strategy, larger batches ensure endpoints stay occupied
        batch_size = 16  # Process 16 sequences concurrently (4 per endpoint for maximum occupation)
        all_results = []
        
        console.print(f"[yellow]Batch size: {batch_size} (4 per endpoint for maximum resource occupation)[/yellow]")
        console.print(f"[yellow]Strategy: LEAST_LOADED - will automatically distribute load across all endpoints[/yellow]")
        console.print(f"[yellow]Goal: Keep all endpoints fully occupied for maximum throughput[/yellow]")
        
        # Show initial endpoint status
        console.print(f"\n[bold cyan]Initial Endpoint Status:[/bold cyan]")
        for ep in stress_client.endpoints:
            console.print(f"  {ep.endpoint_config.base_url}: healthy={ep.is_healthy}, current_requests={ep.current_requests}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing protein sequences concurrently...", total=len(sequences))
            
            for batch_start in range(0, len(sequences), batch_size):
                batch_end = min(batch_start + batch_size, len(sequences))
                batch_sequences = sequences[batch_start:batch_end]
                
                # Create concurrent tasks for this batch
                tasks = [
                    process_single_sequence(seq, batch_start + i) 
                    for i, seq in enumerate(batch_sequences)
                ]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process batch results
                for result in batch_results:
                    if isinstance(result, dict) and result['success']:
                        test_results.add_protein_prediction(
                            result['sequence'], 
                            result['result'], 
                            result['timing'], 
                            result['endpoint']
                        )
                        
                        # Update endpoint usage tracking
                        endpoint_url = result['endpoint']
                        if endpoint_url not in test_results.endpoint_usage:
                            test_results.endpoint_usage[endpoint_url] = 0
                        test_results.endpoint_usage[endpoint_url] += 1
                    else:
                        # Handle errors
                        error_msg = str(result) if not isinstance(result, dict) else result.get('error', 'Unknown error')
                        test_results.errors.append(f"Sequence {batch_start}: {error_msg}")
                
                # Update progress
                progress.update(task, advance=len(batch_sequences))
                
                # Show batch completion
                console.print(f"✅ Completed batch {batch_start//batch_size + 1}: {len(batch_sequences)} sequences")
                
                # Show current endpoint load distribution
                current_loads = {}
                for ep in stress_client.endpoints:
                    current_loads[ep.endpoint_config.base_url] = ep.current_requests
                
                console.print(f"[cyan]Current endpoint loads: {current_loads}[/cyan]")
                
                # Minimal delay to keep endpoints occupied but prevent overwhelming
                await asyncio.sleep(0.1)  # Reduced from 0.5s to 0.1s for maximum throughput
        
        total_time = time.time() - start_time
        test_results.timing_data['protein_predictions'] = {
            'total_time': total_time,
            'sequences_processed': len(sequences),
            'avg_time_per_sequence': total_time / len(sequences),
            'concurrent_batches': (len(sequences) + batch_size - 1) // batch_size,
            'batch_size': batch_size
        }
        
        # Display results
        console.print(f"\n[bold green]✅ CONCURRENT Protein Structure Predictions Completed![/bold green]")
        console.print(f"Total time: {total_time:.2f}s")
        console.print(f"Average time per sequence: {total_time/len(sequences):.2f}s")
        console.print(f"Concurrent processing: {batch_size} sequences simultaneously")
        
        # Show endpoint distribution
        table = Table(title="Endpoint Usage Distribution (Concurrent Processing)")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Requests", style="magenta")
        table.add_column("Percentage", style="green")
        table.add_column("Load Balance", style="yellow")
        
        total_requests = sum(test_results.endpoint_usage.values())
        for endpoint, count in test_results.endpoint_usage.items():
            percentage = (count / total_requests) * 100 if total_requests > 0 else 0
            expected_percentage = 25.0  # 4 endpoints = 25% each
            balance_status = "✅ Balanced" if abs(percentage - expected_percentage) < 10 else "⚠️ Unbalanced"
            table.add_row(endpoint, str(count), f"{percentage:.1f}%", balance_status)
        
        console.print(table)
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_protein_ligand_complexes(self, stress_client, test_results, run_dir):
        """Test protein-ligand complex predictions with 3 proteins × ~50 ligands CONCURRENTLY."""
        console = Console()
        complexes_dir = run_dir / "complexes"
        
        console.print(f"\n[bold blue]🔬 Testing Protein-Ligand Complex Predictions CONCURRENTLY[/bold blue]")
        console.print(f"Proteins: {len(TEST_PROTEINS)}")
        console.print(f"Ligands: {len(LIGANDS)}")
        console.print(f"Total combinations: {len(TEST_PROTEINS) * len(LIGANDS)}")
        console.print(f"Processing: CONCURRENT (all endpoints working simultaneously)")
        
        start_time = time.time()
        total_combinations = len(TEST_PROTEINS) * len(LIGANDS)
        
        # Create concurrent tasks for all combinations
        async def process_single_complex(protein, ligand, combo_index):
            """Process a single protein-ligand combination."""
            try:
                # Track which endpoint will be used
                endpoint = stress_client._select_endpoint()
                endpoint_url = endpoint.endpoint_config.base_url if endpoint else "unknown"
                combo_output_dir = complexes_dir / f"combo_{combo_index:04d}"
                
                # Make prediction
                pred_start = time.time()
                result = await stress_client.predict_protein_ligand_complex(
                    protein_sequence=protein,
                    ligand_smiles=ligand,
                    recycling_steps=1,
                    sampling_steps=10,  # Minimum required
                    predict_affinity=True,
                    sampling_steps_affinity=50,
                    diffusion_samples_affinity=3,
                    affinity_mw_correction=False,
                    save_structures=True,
                    output_dir=combo_output_dir
                )
                pred_time = time.time() - pred_start
                
                return {
                    'combo_index': combo_index,
                    'protein': protein,
                    'ligand': ligand,
                    'result': result,
                    'timing': pred_time,
                    'endpoint': endpoint_url,
                    'success': True,
                    'error': None
                }
                
            except Exception as e:
                return {
                    'combo_index': combo_index,
                    'protein': protein,
                    'ligand': ligand,
                    'result': None,
                    'timing': 0,
                    'endpoint': 'unknown',
                    'success': False,
                    'error': str(e)
                }
        
        # Process combinations in batches for better control
        batch_size = 16  # Process 16 combinations concurrently (4 per endpoint for maximum occupation)
        all_results = []
        combo_index = 0
        
        console.print(f"[yellow]Batch size: {batch_size} (4 per endpoint for maximum resource occupation)[/yellow]")
        console.print(f"[yellow]Strategy: LEAST_LOADED - will automatically distribute load across all endpoints[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Processing protein-ligand complexes concurrently...", total=total_combinations)
            
            for protein in TEST_PROTEINS:
                for ligand in LIGANDS:
                    # Add to current batch
                    all_results.append((protein, ligand, combo_index))
                    combo_index += 1
                    
                    # Process batch when it reaches batch size
                    if len(all_results) >= batch_size:
                        # Create concurrent tasks for this batch
                        tasks = [
                            process_single_complex(prot, lig, idx) 
                            for prot, lig, idx in all_results
                        ]
                        
                        # Execute batch concurrently
                        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Process batch results
                        for result in batch_results:
                            if isinstance(result, dict) and result['success']:
                                test_results.add_ligand_complex_prediction(
                                    result['protein'], 
                                    result['ligand'], 
                                    result['result'], 
                                    result['timing'], 
                                    result['endpoint']
                                )
                                
                                # Update endpoint usage tracking
                                endpoint_url = result['endpoint']
                                if endpoint_url not in test_results.endpoint_usage:
                                    test_results.endpoint_usage[endpoint_url] = 0
                                test_results.endpoint_usage[endpoint_url] += 1
                            else:
                                # Handle errors
                                error_msg = str(result) if not isinstance(result, dict) else result.get('error', 'Unknown error')
                                test_results.errors.append(f"Complex {result.get('combo_index', 'unknown')}: {error_msg}")
                        
                        # Update progress
                        progress.update(task, advance=len(all_results))
                        
                        # Show batch completion
                        console.print(f"✅ Completed batch: {len(all_results)} complexes")
                        
                        # Clear batch
                        all_results = []
                        
                        # Minimal delay to keep endpoints occupied
                        await asyncio.sleep(0.1)  # Reduced for maximum throughput
            
            # Process remaining combinations in final batch
            if all_results:
                tasks = [
                    process_single_complex(prot, lig, idx) 
                    for prot, lig, idx in all_results
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, dict) and result['success']:
                        test_results.add_ligand_complex_prediction(
                            result['protein'], 
                            result['ligand'], 
                            result['result'], 
                            result['timing'], 
                            result['endpoint']
                        )
                        
                        endpoint_url = result['endpoint']
                        if endpoint_url not in test_results.endpoint_usage:
                            test_results.endpoint_usage[endpoint_url] = 0
                        test_results.endpoint_usage[endpoint_url] += 1
                    else:
                        error_msg = str(result) if not isinstance(result, dict) else result.get('error', 'Unknown error')
                        test_results.errors.append(f"Complex {result.get('combo_index', 'unknown')}: {error_msg}")
                
                progress.update(task, advance=len(all_results))
                console.print(f"✅ Completed final batch: {len(all_results)} complexes")
        
        total_time = time.time() - start_time
        test_results.timing_data['ligand_complex_predictions'] = {
            'total_time': total_time,
            'combinations_processed': total_combinations,
            'avg_time_per_combination': total_time / total_combinations,
            'concurrent_batches': (total_combinations + batch_size - 1) // batch_size,
            'batch_size': batch_size
        }
        
        # Display results
        console.print(f"\n[bold green]✅ CONCURRENT Protein-Ligand Complex Predictions Completed![/bold green]")
        console.print(f"Total time: {total_time:.2f}s")
        console.print(f"Average time per combination: {total_time/total_combinations:.2f}s")
        console.print(f"Concurrent processing: {batch_size} combinations simultaneously")
    
    @pytest.mark.slow
    @pytest.mark.real_endpoint
    async def test_comprehensive_analysis(self, stress_client, test_results, run_dir):
        """Run comprehensive analysis and save all results."""
        console = Console()
        
        console.print(f"\n[bold blue]📊 Comprehensive Analysis and Results Saving[/bold blue]")
        
        # Generate summary
        summary = test_results.generate_summary()
        
        # Display summary table
        table = Table(title="Comprehensive Test Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Predictions", str(summary['total_predictions']))
        table.add_row("Protein Predictions", f"{summary['protein_predictions']['total']} ({summary['protein_predictions']['success_rate']})")
        table.add_row("Ligand Complex Predictions", f"{summary['ligand_complex_predictions']['total']} ({summary['ligand_complex_predictions']['success_rate']})")
        table.add_row("Errors", str(summary['error_count']))
        
        if summary['protein_predictions']['avg_timing'] != "N/A":
            table.add_row("Avg Protein Time", summary['protein_predictions']['avg_timing'])
        if summary['ligand_complex_predictions']['avg_timing'] != "N/A":
            table.add_row("Avg Ligand Time", summary['ligand_complex_predictions']['avg_timing'])
        
        console.print(table)
        
        # Save results to the shared run directory
        output_dir = run_dir
        test_results.save_results(output_dir)
        
        console.print(f"\n[bold green]💾 Results saved to: {output_dir}[/bold green]")
        console.print(f"Files created:")
        console.print(f"  - comprehensive_test_results.json (complete data)")
        console.print(f"  - protein_predictions.csv (protein results)")
        console.print(f"  - ligand_complex_predictions.csv (ligand results)")
        
        # Final endpoint status
        final_status = stress_client.get_status()
        console.print(f"\n[bold blue]Final Endpoint Status:[/bold blue]")
        console.print(f"{final_status}")
        
        return summary

# Main execution function
async def run_comprehensive_stress_test():
    """Run the comprehensive stress test."""
    console = Console()
    
    console.print("[bold red]🚀 COMPREHENSIVE MULTI-ENDPOINT STRESS TEST[/bold red]")
    console.print("=" * 60)
    
    # Create client
    client = MultiEndpointClient(
        endpoints=[
            "http://localhost:8000",
            "http://localhost:8001", 
            "http://localhost:8002",
            "http://localhost:8003"
        ],
        strategy=LoadBalanceStrategy.LEAST_LOADED,
        timeout=600.0,
        max_retries=3,
        is_async=True
    )
    
    # Create results storage
    results = ResultsStorage()
    
    try:
        # Test 1: 50 protein sequences
        console.print("\n[bold blue]Phase 1: Protein Structure Predictions[/bold blue]")
        await test_50_protein_sequences(client, results)
        
        # Test 2: Protein-ligand complexes
        console.print("\n[bold blue]Phase 2: Protein-Ligand Complex Predictions[/bold blue]")
        await test_protein_ligand_complexes(client, results)
        
        # Test 3: Analysis and saving
        console.print("\n[bold blue]Phase 3: Analysis and Results Saving[/bold blue]")
        summary = await test_comprehensive_analysis(client, results)
        
        console.print(f"\n[bold green]🎉 COMPREHENSIVE STRESS TEST COMPLETED SUCCESSFULLY![/bold green]")
        return summary
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {str(e)}[/bold red]")
        results.errors.append(f"Test execution failed: {str(e)}")
        return None

if __name__ == "__main__":
    # Run the test
    asyncio.run(run_comprehensive_stress_test())
