# ---------------------------------------------------------------
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------

"""
Virtual Screening Module for Boltz-2

Provides high-level APIs for virtual screening campaigns with
automatic parallelization, result analysis, and visualization.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from .client import Boltz2Client, Boltz2SyncClient
from .models import Polymer, Ligand, PredictionRequest, PocketConstraint
from .exceptions import Boltz2ValidationError
from .multi_endpoint_client import MultiEndpointClient


class CompoundLibrary:
    """Represents a chemical library for virtual screening."""
    
    def __init__(self, compounds: List[Dict[str, Any]]):
        """
        Initialize compound library.
        
        Args:
            compounds: List of compound dictionaries with required fields:
                - name: Compound name
                - smiles: SMILES string OR ccd: CCD code
                - metadata: Optional dict with additional info
        """
        self.compounds = self._validate_compounds(compounds)
    
    @classmethod
    def from_csv(cls, csv_path: Union[str, Path], 
                 name_col: str = "name", 
                 smiles_col: str = "smiles",
                 ccd_col: Optional[str] = None) -> "CompoundLibrary":
        """Load compound library from CSV file."""
        df = pd.read_csv(csv_path)
        compounds = []
        
        for _, row in df.iterrows():
            compound = {"name": row[name_col]}
            
            if smiles_col in row and pd.notna(row[smiles_col]):
                compound["smiles"] = row[smiles_col]
            elif ccd_col and ccd_col in row and pd.notna(row[ccd_col]):
                compound["ccd"] = row[ccd_col]
            else:
                continue
            
            # Add all other columns as metadata
            metadata = {}
            for col in df.columns:
                if col not in [name_col, smiles_col, ccd_col]:
                    metadata[col] = row[col]
            
            if metadata:
                compound["metadata"] = metadata
            
            compounds.append(compound)
        
        return cls(compounds)
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> "CompoundLibrary":
        """Load compound library from JSON file."""
        with open(json_path, 'r') as f:
            compounds = json.load(f)
        return cls(compounds)
    
    def _validate_compounds(self, compounds: List[Dict]) -> List[Dict]:
        """Validate compound entries."""
        validated = []
        for i, compound in enumerate(compounds):
            if "name" not in compound:
                raise Boltz2ValidationError(f"Compound {i} missing 'name' field")
            
            if "smiles" not in compound and "ccd" not in compound:
                raise Boltz2ValidationError(
                    f"Compound '{compound['name']}' must have either 'smiles' or 'ccd'"
                )
            
            validated.append(compound)
        
        return validated
    
    def __len__(self) -> int:
        return len(self.compounds)
    
    def __iter__(self):
        return iter(self.compounds)


class VirtualScreeningResult:
    """Container for virtual screening results."""
    
    def __init__(self, 
                 target_name: str,
                 target_sequence: str,
                 results: List[Dict[str, Any]],
                 parameters: Dict[str, Any],
                 duration_seconds: float):
        self.target_name = target_name
        self.target_sequence = target_sequence
        self.results = results
        self.parameters = parameters
        self.duration_seconds = duration_seconds
        self.timestamp = datetime.now()
    
    @property
    def successful_results(self) -> List[Dict]:
        """Get only successful predictions."""
        return [r for r in self.results if "error" not in r]
    
    @property
    def failed_results(self) -> List[Dict]:
        """Get only failed predictions."""
        return [r for r in self.results if "error" in r]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.results:
            return 0.0
        return len(self.successful_results) / len(self.results)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame."""
        return pd.DataFrame(self.successful_results)
    
    def save_results(self, output_dir: Union[str, Path], 
                     save_structures: bool = True) -> Dict[str, Path]:
        """
        Save all results to files.
        
        Returns:
            Dictionary of saved file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # Save summary CSV
        df = self.to_dataframe()
        if not df.empty:
            csv_path = output_dir / "screening_results.csv"
            df.to_csv(csv_path, index=False)
            saved_files["results_csv"] = csv_path
        
        # Save structures
        if save_structures:
            structures_dir = output_dir / "structures"
            structures_dir.mkdir(exist_ok=True)
            
            for result in self.successful_results:
                if "structure_cif" in result:
                    cif_path = structures_dir / f"{result['compound_name'].replace(' ', '_')}.cif"
                    with open(cif_path, 'w') as f:
                        f.write(result["structure_cif"])
        
        # Save metadata
        metadata = {
            "target_name": self.target_name,
            "target_sequence_length": len(self.target_sequence),
            "compounds_screened": len(self.results),
            "successful_predictions": len(self.successful_results),
            "failed_predictions": len(self.failed_results),
            "success_rate": self.success_rate,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
            "parameters": self.parameters
        }
        
        metadata_path = output_dir / "screening_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        saved_files["metadata"] = metadata_path
        
        return saved_files
    
    def get_top_hits(self, n: int = 10, by: str = "predicted_pic50") -> pd.DataFrame:
        """Get top N compounds by specified metric."""
        df = self.to_dataframe()
        if df.empty or by not in df.columns:
            return pd.DataFrame()
        
        return df.nlargest(n, by)
    
    def get_statistics_by_group(self, group_by: str = "compound_type") -> pd.DataFrame:
        """Get statistics grouped by a metadata field."""
        df = self.to_dataframe()
        if df.empty or group_by not in df.columns:
            return pd.DataFrame()
        
        stats = df.groupby(group_by).agg({
            'predicted_pic50': ['mean', 'std', 'count'],
            'predicted_ic50_nm': 'mean',
            'binding_probability': 'mean'
        }).round(3)
        
        return stats


class VirtualScreening:
    """High-level API for virtual screening campaigns."""
    
    def __init__(self, 
                 client: Optional[Union[Boltz2Client, Boltz2SyncClient, MultiEndpointClient]] = None,
                 max_workers: int = 4):
        """
        Initialize virtual screening.
        
        Args:
            client: Boltz2 client instance (if None, creates default)
                   Can be a single client or MultiEndpointClient for load balancing
            max_workers: Maximum parallel workers for screening
        """
        self.client = client or Boltz2SyncClient()
        self.max_workers = max_workers
        self.is_async = isinstance(self.client, (Boltz2Client, MultiEndpointClient)) and (
            not hasattr(self.client, 'is_async') or self.client.is_async
        )
        self.is_multi_endpoint = isinstance(self.client, MultiEndpointClient)
    
    def screen(self,
               target_sequence: str,
               compound_library: Union[CompoundLibrary, List[Dict], str, Path],
               target_name: str = "Target",
               predict_affinity: bool = True,
               pocket_residues: Optional[List[int]] = None,
               pocket_radius: float = 10.0,
               recycling_steps: int = 2,
               sampling_steps: int = 30,
               diffusion_samples: int = 1,
               sampling_steps_affinity: int = 100,
               diffusion_samples_affinity: int = 3,
               affinity_mw_correction: bool = True,
               batch_size: Optional[int] = None,
               progress_callback: Optional[Callable] = None) -> VirtualScreeningResult:
        """
        Run virtual screening campaign.
        
        Args:
            target_sequence: Protein target sequence
            compound_library: Compounds to screen (CompoundLibrary, list, or path to file)
            target_name: Name of the target protein
            predict_affinity: Enable affinity prediction
            pocket_residues: List of residue indices defining binding pocket
            pocket_radius: Radius for pocket constraint in Angstroms
            recycling_steps: Number of recycling steps
            sampling_steps: Number of sampling steps
            diffusion_samples: Number of diffusion samples
            sampling_steps_affinity: Sampling steps for affinity prediction
            diffusion_samples_affinity: Diffusion samples for affinity
            affinity_mw_correction: Apply molecular weight correction
            batch_size: Process compounds in batches (None = all parallel)
            progress_callback: Function called with (completed, total) after each compound
            
        Returns:
            VirtualScreeningResult object with all results
        """
        # Prepare compound library
        if isinstance(compound_library, (str, Path)):
            path = Path(compound_library)
            if path.suffix == '.csv':
                compound_library = CompoundLibrary.from_csv(path)
            elif path.suffix == '.json':
                compound_library = CompoundLibrary.from_json(path)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        elif isinstance(compound_library, list):
            compound_library = CompoundLibrary(compound_library)
        
        # Store parameters
        parameters = {
            "target_name": target_name,
            "predict_affinity": predict_affinity,
            "pocket_residues": pocket_residues,
            "pocket_radius": pocket_radius,
            "recycling_steps": recycling_steps,
            "sampling_steps": sampling_steps,
            "diffusion_samples": diffusion_samples,
            "sampling_steps_affinity": sampling_steps_affinity if predict_affinity else None,
            "diffusion_samples_affinity": diffusion_samples_affinity if predict_affinity else None,
            "affinity_mw_correction": affinity_mw_correction if predict_affinity else None
        }
        
        # Run screening
        start_time = time.time()
        
        if self.is_async:
            # Use async screening
            results = asyncio.run(self._screen_async(
                target_sequence, compound_library, parameters, 
                pocket_residues, pocket_radius, progress_callback
            ))
        else:
            # Use sync screening with thread pool
            results = self._screen_sync(
                target_sequence, compound_library, parameters,
                pocket_residues, pocket_radius, progress_callback, batch_size
            )
        
        duration = time.time() - start_time
        
        return VirtualScreeningResult(
            target_name=target_name,
            target_sequence=target_sequence,
            results=results,
            parameters=parameters,
            duration_seconds=duration
        )
    
    def _screen_sync(self, target_sequence: str, compound_library: CompoundLibrary,
                     parameters: Dict, pocket_residues: Optional[List[int]],
                     pocket_radius: float, progress_callback: Optional[Callable],
                     batch_size: Optional[int]) -> List[Dict]:
        """Synchronous screening implementation."""
        results = []
        total = len(compound_library)
        
        # Create protein polymer once
        protein = Polymer(
            id="A",
            molecule_type="protein",
            sequence=target_sequence
        )
        
        # Prepare pocket constraint if specified
        constraints = []
        if pocket_residues:
            pocket_constraint = PocketConstraint(
                chain_id="A",
                residue_idxs=pocket_residues,
                radius=pocket_radius
            )
            constraints.append(pocket_constraint)
        
        # Process compounds
        if batch_size and batch_size < total:
            # Process in batches
            for i in range(0, total, batch_size):
                batch = list(compound_library.compounds[i:i+batch_size])
                batch_results = self._process_batch_sync(
                    protein, batch, parameters, constraints
                )
                results.extend(batch_results)
                
                if progress_callback:
                    progress_callback(len(results), total)
        else:
            # Process all in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                
                for compound in compound_library:
                    future = executor.submit(
                        self._screen_single_compound_sync,
                        protein, compound, parameters, constraints
                    )
                    futures.append(future)
                
                for i, future in enumerate(futures):
                    result = future.result()
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(i + 1, total)
        
        return results
    
    async def _screen_async(self, target_sequence: str, compound_library: CompoundLibrary,
                           parameters: Dict, pocket_residues: Optional[List[int]],
                           pocket_radius: float, progress_callback: Optional[Callable]) -> List[Dict]:
        """Asynchronous screening implementation."""
        # Create protein polymer
        protein = Polymer(
            id="A",
            molecule_type="protein",
            sequence=target_sequence
        )
        
        # Prepare pocket constraint
        constraints = []
        if pocket_residues:
            pocket_constraint = PocketConstraint(
                chain_id="A",
                residue_idxs=pocket_residues,
                radius=pocket_radius
            )
            constraints.append(pocket_constraint)
        
        # Create tasks
        tasks = []
        for compound in compound_library:
            task = self._screen_single_compound_async(
                protein, compound, parameters, constraints
            )
            tasks.append(task)
        
        # Run with progress updates
        results = []
        total = len(tasks)
        
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results
    
    def _screen_single_compound_sync(self, protein: Polymer, compound: Dict,
                                    parameters: Dict, constraints: List) -> Dict:
        """Screen a single compound synchronously."""
        try:
            # Create ligand
            if "smiles" in compound:
                ligand = Ligand(
                    id="LIG",
                    smiles=compound["smiles"],
                    predict_affinity=parameters["predict_affinity"]
                )
            else:
                ligand = Ligand(
                    id="LIG",
                    ccd=compound["ccd"],
                    predict_affinity=parameters["predict_affinity"]
                )
            
            # Create request
            request = PredictionRequest(
                polymers=[protein],
                ligands=[ligand],
                constraints=constraints if constraints else None,
                recycling_steps=parameters["recycling_steps"],
                sampling_steps=parameters["sampling_steps"],
                diffusion_samples=parameters["diffusion_samples"]
            )
            
            # Add affinity parameters if enabled
            if parameters["predict_affinity"]:
                request.sampling_steps_affinity = parameters["sampling_steps_affinity"]
                request.diffusion_samples_affinity = parameters["diffusion_samples_affinity"]
                request.affinity_mw_correction = parameters["affinity_mw_correction"]
            
            # Run prediction
            if self.is_multi_endpoint and not self.is_async:
                response = self.client.predict_sync(request)
            else:
                response = self.client.predict(request)
            
            # Extract results
            result = {
                "compound_name": compound["name"],
                "compound_smiles": compound.get("smiles", ""),
                "compound_ccd": compound.get("ccd", ""),
                "structure_confidence": response.confidence_scores[0] if response.confidence_scores else None,
                "structure_cif": response.structures[0].structure
            }
            
            # Add metadata
            if "metadata" in compound:
                for key, value in compound["metadata"].items():
                    result[f"compound_{key}"] = value
            
            # Add affinity results if available
            if response.affinities and "LIG" in response.affinities:
                affinity = response.affinities["LIG"]
                result.update({
                    "predicted_pic50": affinity.affinity_pic50[0],
                    "predicted_ic50_nm": 10 ** (-affinity.affinity_pic50[0]) * 1e9,
                    "binding_probability": affinity.affinity_probability_binary[0]
                })
            
            return result
            
        except Exception as e:
            return {
                "compound_name": compound["name"],
                "error": str(e)
            }
    
    async def _screen_single_compound_async(self, protein: Polymer, compound: Dict,
                                           parameters: Dict, constraints: List) -> Dict:
        """Screen a single compound asynchronously."""
        # Similar to sync version but uses await
        try:
            # Create ligand
            if "smiles" in compound:
                ligand = Ligand(
                    id="LIG",
                    smiles=compound["smiles"],
                    predict_affinity=parameters["predict_affinity"]
                )
            else:
                ligand = Ligand(
                    id="LIG",
                    ccd=compound["ccd"],
                    predict_affinity=parameters["predict_affinity"]
                )
            
            # Create request
            request = PredictionRequest(
                polymers=[protein],
                ligands=[ligand],
                constraints=constraints if constraints else None,
                recycling_steps=parameters["recycling_steps"],
                sampling_steps=parameters["sampling_steps"],
                diffusion_samples=parameters["diffusion_samples"]
            )
            
            # Add affinity parameters
            if parameters["predict_affinity"]:
                request.sampling_steps_affinity = parameters["sampling_steps_affinity"]
                request.diffusion_samples_affinity = parameters["diffusion_samples_affinity"]
                request.affinity_mw_correction = parameters["affinity_mw_correction"]
            
            # Run prediction
            response = await self.client.predict(request)
            
            # Extract results (same as sync)
            result = {
                "compound_name": compound["name"],
                "compound_smiles": compound.get("smiles", ""),
                "compound_ccd": compound.get("ccd", ""),
                "structure_confidence": response.confidence_scores[0] if response.confidence_scores else None,
                "structure_cif": response.structures[0].structure
            }
            
            # Add metadata
            if "metadata" in compound:
                for key, value in compound["metadata"].items():
                    result[f"compound_{key}"] = value
            
            # Add affinity results
            if response.affinities and "LIG" in response.affinities:
                affinity = response.affinities["LIG"]
                result.update({
                    "predicted_pic50": affinity.affinity_pic50[0],
                    "predicted_ic50_nm": 10 ** (-affinity.affinity_pic50[0]) * 1e9,
                    "binding_probability": affinity.affinity_probability_binary[0]
                })
            
            return result
            
        except Exception as e:
            return {
                "compound_name": compound["name"],
                "error": str(e)
            }
    
    def _process_batch_sync(self, protein: Polymer, batch: List[Dict],
                           parameters: Dict, constraints: List) -> List[Dict]:
        """Process a batch of compounds."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for compound in batch:
                future = executor.submit(
                    self._screen_single_compound_sync,
                    protein, compound, parameters, constraints
                )
                futures.append(future)
            
            results = [future.result() for future in futures]
        
        return results


# Convenience functions
def quick_screen(target_sequence: str, 
                 compounds: Union[List[Dict], str, Path],
                 target_name: str = "Target",
                 output_dir: Optional[Union[str, Path]] = None,
                 **kwargs) -> VirtualScreeningResult:
    """
    Quick virtual screening with minimal setup.
    
    Args:
        target_sequence: Protein sequence
        compounds: List of compounds or path to CSV/JSON file
        target_name: Name of target
        output_dir: Directory to save results (optional)
        **kwargs: Additional parameters passed to VirtualScreening.screen()
    
    Returns:
        VirtualScreeningResult
    """
    screener = VirtualScreening()
    result = screener.screen(
        target_sequence=target_sequence,
        compound_library=compounds,
        target_name=target_name,
        **kwargs
    )
    
    if output_dir:
        saved_files = result.save_results(output_dir)
        print(f"Results saved to: {output_dir}")
        for key, path in saved_files.items():
            print(f"  - {key}: {path}")
    
    return result 