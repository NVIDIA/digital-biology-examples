# ---------------------------------------------------------------
# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------


"""
Data models for Boltz-2 API requests and responses.

This module defines Pydantic models that represent the data structures
used by the Boltz-2 API, providing type safety and validation for all
available parameters and features.
"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re
from .models_affinity import AffinityPrediction


class Modification(BaseModel):
    """Represents a molecular modification."""
    type: str = Field(..., description="Type of modification")
    position: int = Field(..., description="Position of modification")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional modification details")


class AlignmentFileRecord(BaseModel):
    """Represents a single alignment file record."""
    alignment: str = Field(..., description="Raw alignment file content as string")
    format: Literal["sto", "a3m", "csv", "fasta"] = Field(..., description="Alignment file format")
    rank: int = Field(-1, description="Integer rank to define ordering of alignments")
    
    @validator('alignment')
    def validate_alignment_content(cls, v):
        """Validate alignment content is not empty."""
        if not v.strip():
            raise ValueError("Alignment content cannot be empty")
        return v


class Polymer(BaseModel):
    """Represents a polymer (protein, DNA, or RNA) in the prediction request."""
    
    id: str = Field(..., description="Unique identifier for the polymer (A-Z or 4 alphanumeric chars)")
    molecule_type: Literal["protein", "dna", "rna"] = Field(..., description="Type of molecule")
    sequence: str = Field(..., description="Sequence string")
    cyclic: bool = Field(False, description="Whether the polymer is cyclic")
    modifications: List[Modification] = Field(default_factory=list, description="List of modifications")
    msa: Optional[Dict[str, Dict[str, AlignmentFileRecord]]] = Field(None, description="A Dictionary [database_name -> [format -> AlignmentFileRecord]] containing alignments")
    
    @validator('sequence')
    def validate_sequence(cls, v, values):
        """Validate sequence based on molecule type."""
        if 'molecule_type' not in values:
            return v
            
        molecule_type = values['molecule_type']
        
        if molecule_type == "protein":
            # Standard amino acid codes
            valid_chars = set("ACDEFGHIKLMNPQRSTVWY")
            if not all(c.upper() in valid_chars for c in v):
                raise ValueError(f"Invalid amino acid characters in protein sequence: {v}")
        elif molecule_type == "dna":
            # Standard DNA bases
            valid_chars = set("ATCG")
            if not all(c.upper() in valid_chars for c in v):
                raise ValueError(f"Invalid DNA base characters in sequence: {v}")
        elif molecule_type == "rna":
            # Standard RNA bases
            valid_chars = set("AUCG")
            if not all(c.upper() in valid_chars for c in v):
                raise ValueError(f"Invalid RNA base characters in sequence: {v}")
        
        return v.upper()
    
    @validator('id')
    def validate_id(cls, v):
        """Validate polymer ID format (single letter A-Z or 4 alphanumeric chars)."""
        if re.match(r'^[A-Z]$', v):
            return v  # Single letter A-Z
        elif re.match(r'^[A-Za-z0-9]{4}$', v):
            return v  # 4 alphanumeric characters
        else:
            raise ValueError("Polymer ID must be either a single letter (A-Z) or 4 alphanumeric characters")


class Ligand(BaseModel):
    """Represents a ligand in the prediction request."""
    
    id: str = Field(..., description="Unique identifier for the ligand")
    smiles: Optional[str] = Field(None, description="SMILES string representation")
    ccd: Optional[str] = Field(None, description="Chemical Component Dictionary (CCD) code")
    predict_affinity: Optional[bool] = Field(False, description="Run affinity prediction for this ligand. Note: only one ligand per request can have this enabled")
    
    @validator('smiles')
    def validate_smiles(cls, v):
        """Basic SMILES validation."""
        if v is not None:
            if not v.strip():
                raise ValueError("SMILES string cannot be empty")
            # Basic character validation - could be enhanced with RDKit
            if any(char in v for char in [' ', '\t', '\n']):
                raise ValueError("SMILES string should not contain whitespace")
            return v.strip()
        return v
    
    @validator('ccd')
    def validate_ccd(cls, v):
        """Basic CCD code validation."""
        if v is not None:
            if not v.strip():
                raise ValueError("CCD code cannot be empty")
            # CCD codes are typically 3-4 character alphanumeric codes
            if not re.match(r'^[A-Za-z0-9]{2,4}$', v.strip()):
                raise ValueError("CCD code must be 2-4 alphanumeric characters")
            return v.strip().upper()
        return v
    
    @validator('ccd', always=True)
    def validate_smiles_or_ccd(cls, v, values):
        """Ensure either SMILES or CCD is provided, but not both."""
        smiles = values.get('smiles')
        if smiles and v:
            raise ValueError("Cannot specify both SMILES and CCD code")
        if not smiles and not v:
            raise ValueError("Must specify either SMILES or CCD code")
        return v
    
    @validator('id')
    def validate_id(cls, v):
        """Validate ligand ID format."""
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("Ligand ID must contain only alphanumeric characters, underscores, and hyphens")
        return v


class Atom(BaseModel):
    """Represents an atom in constraints."""
    id: Optional[str] = Field(None, description="Polymer/ligand ID (chain identifier)")
    residue_index: int = Field(..., description="Residue index (1-based)")
    atom_name: str = Field(..., description="Atom name (e.g., 'CA', 'SG', 'C22')")
    
    @validator('id')
    def validate_id(cls, v):
        """Validate atom ID format to match server-side validation."""
        if v is not None:
            # Server pattern: ^([A-Z]+|[A-Za-z0-9]{4})$
            # One or more letters (A-Z+) OR exactly 4 alphanumeric characters
            if re.match(r'^[A-Z]+$', v) or re.match(r'^[A-Za-z0-9]{4}$', v):
                return v
            else:
                raise ValueError("Atom ID must be either one or more letters (A-Z) or exactly 4 alphanumeric characters")
        return v


class PocketConstraint(BaseModel):
    """Represents a pocket constraint."""
    constraint_type: str = Field("pocket", description="Type of constraint")
    ligand_id: str = Field(..., description="ID of the ligand")
    polymer_id: str = Field(..., description="ID of the polymer")
    residue_ids: List[int] = Field(..., description="List of residue IDs defining the pocket")
    binder: str = Field(..., description="ID of the binding molecule")
    contacts: List[int] = Field(default_factory=list, description="Contact residue indices")


class BondConstraint(BaseModel):
    """Represents a bond constraint between atoms."""
    constraint_type: str = Field("bond", description="Type of constraint")
    atoms: List[Atom] = Field(..., description="List of atoms involved in the bond (exactly 2)")
    
    @validator('atoms')
    def validate_atoms_count(cls, v):
        """Validate that exactly 2 atoms are specified for a bond."""
        if len(v) != 2:
            raise ValueError("Bond constraint must specify exactly 2 atoms")
        return v


class PredictionRequest(BaseModel):
    """Complete prediction request model with all available Boltz-2 parameters."""
    
    # Required parameters
    polymers: List[Polymer] = Field(..., description="List of polymers (DNA, RNA, or Protein) - max 5, min 1")
    
    # Optional molecular components
    ligands: Optional[List[Ligand]] = Field(None, description="List of ligands - max 5, min 0")
    
    # Constraints
    constraints: Optional[List[Union[PocketConstraint, BondConstraint]]] = Field(
        None, description="Optional constraints for the prediction (pocket or bond constraints)"
    )
    
    # Diffusion and sampling parameters
    recycling_steps: Optional[int] = Field(
        3, ge=1, le=6, 
        description="The number of recycling steps to use for prediction (1-6, default: 3)"
    )
    sampling_steps: Optional[int] = Field(
        50, ge=10, le=1000,
        description="The number of sampling steps to use for prediction (10-1000, default: 50)"
    )
    diffusion_samples: Optional[int] = Field(
        1, ge=1, le=5,
        description="The number of diffusion samples to use for prediction (1-5, default: 1)"
    )
    step_scale: Optional[float] = Field(
        1.638, ge=0.5, le=5.0,
        description="Step size related to temperature of diffusion sampling. Lower = higher diversity (0.5-5.0, default: 1.638)"
    )
    
    # Advanced parameters
    without_potentials: Optional[bool] = Field(
        False, 
        description="Whether to run without potentials (default: False)"
    )
    output_format: Optional[Literal["mmcif"]] = Field(
        "mmcif", 
        description="Output format for structures (default: mmcif)"
    )
    concatenate_msas: Optional[bool] = Field(
        False,
        description="Concatenate Multiple Sequence Alignments for a polymer into one alignment (default: False)"
    )
    
    # Affinity prediction parameters
    sampling_steps_affinity: Optional[int] = Field(
        200, ge=10, le=1000,
        description="The number of sampling steps for affinity prediction. Higher values may improve accuracy but increase runtime (10-1000, default: 200)"
    )
    diffusion_samples_affinity: Optional[int] = Field(
        5, ge=1, le=10,
        description="The number of diffusion samples for affinity prediction. Higher values may improve reliability but increase runtime (1-10, default: 5)"
    )
    affinity_mw_correction: Optional[bool] = Field(
        False,
        description="Whether to add Molecular Weight correction to the affinity prediction (default: False)"
    )
    
    @validator('polymers')
    def validate_polymers_count(cls, v):
        """Validate polymer count."""
        if len(v) > 5:
            raise ValueError("Maximum 5 polymers allowed")
        if len(v) == 0:
            raise ValueError("At least 1 polymer required")
        return v
    
    @validator('ligands')
    def validate_ligands_count(cls, v):
        """Validate ligand count and affinity prediction constraints."""
        if v is not None:
            if len(v) > 5:
                raise ValueError("Maximum 5 ligands allowed")
            
            # Check that only one ligand has predict_affinity=True
            affinity_ligands = [lig for lig in v if getattr(lig, 'predict_affinity', False)]
            if len(affinity_ligands) > 1:
                raise ValueError("Only one ligand per request can have predict_affinity=True")
        return v
    
    @validator('constraints')
    def validate_constraints(cls, v):
        """Validate constraints format."""
        if v is not None:
            for constraint in v:
                if isinstance(constraint, dict):
                    constraint_type = constraint.get('constraint_type')
                    if constraint_type not in ['pocket', 'bond']:
                        raise ValueError(f"Invalid constraint type: {constraint_type}")
        return v


class StructureData(BaseModel):
    """Represents structure data in the response."""
    
    format: str = Field(..., description="Structure format (e.g., 'mmcif')")
    structure: str = Field(..., description="Structure data content")
    name: Optional[str] = Field(None, description="Structure name")
    source: Optional[str] = Field(None, description="Structure source file")


class PredictionResponse(BaseModel):
    """Complete prediction response model."""
    
    structures: List[StructureData] = Field(..., description="Predicted structures")
    confidence_scores: Optional[List[float]] = Field(None, description="Confidence scores for predictions")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Runtime metrics and statistics")
    
    # Affinity prediction results
    affinities: Optional[Dict[str, AffinityPrediction]] = Field(
        None, 
        description="Predicted affinity values for ligands (keyed by ligand ID)"
    )
    
    # Additional confidence metrics
    ptm_scores: Optional[List[float]] = Field(None, description="Predicted TM score for the complex")
    iptm_scores: Optional[List[float]] = Field(None, description="Predicted TM score when aggregating at interfaces")
    ligand_iptm_scores: Optional[List[float]] = Field(None, description="ipTM but only at protein-ligand interfaces")
    protein_iptm_scores: Optional[List[float]] = Field(None, description="ipTM but only at protein-protein interfaces")
    complex_plddt_scores: Optional[List[float]] = Field(None, description="Average pLDDT score for the complex")
    complex_iplddt_scores: Optional[List[float]] = Field(None, description="Average pLDDT score when upweighting interface tokens")
    complex_pde_scores: Optional[List[float]] = Field(None, description="Average PDE score for the complex")
    complex_ipde_scores: Optional[List[float]] = Field(None, description="Average PDE score when aggregating at interfaces")
    chains_ptm_scores: Optional[List[float]] = Field(None, description="Predicted TM score within each chain")
    pair_chains_iptm_scores: Optional[List[Dict[str, Any]]] = Field(None, description="Predicted TM score between each pair of chains")
    
    @validator('structures')
    def validate_structures(cls, v):
        """Validate structures list."""
        if len(v) == 0:
            raise ValueError("At least one structure must be returned")
        return v


class HealthStatus(BaseModel):
    """Health status response model."""
    
    status: str = Field(..., description="Health status")
    timestamp: Optional[datetime] = Field(None, description="Status timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")


class ModelInfo(BaseModel):
    """Model information."""
    
    modelUrl: str = Field(..., description="Model URL")
    shortName: str = Field(..., description="Model short name")


class LicenseInfo(BaseModel):
    """License information."""
    
    name: str = Field(..., description="License name")
    path: str = Field(..., description="License file path")
    sha: str = Field(..., description="License file SHA")
    size: int = Field(..., description="License file size")
    url: str = Field(..., description="License URL")
    type: str = Field(..., description="License type")
    content: str = Field(..., description="License content")


class ServiceMetadata(BaseModel):
    """Service metadata response model."""
    
    assetInfo: List[str] = Field(..., description="Asset information")
    licenseInfo: LicenseInfo = Field(..., description="License information")
    modelInfo: List[ModelInfo] = Field(..., description="Model information")
    repository_override: str = Field(..., description="Repository override")
    version: str = Field(..., description="Service version")


class PredictionJob(BaseModel):
    """Represents a prediction job for tracking."""
    
    job_id: str = Field(..., description="Unique job identifier")
    request: PredictionRequest = Field(..., description="Original request")
    status: Literal["pending", "running", "completed", "failed"] = Field(..., description="Job status")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    result: Optional[PredictionResponse] = Field(None, description="Job result")
    error: Optional[str] = Field(None, description="Error message if failed")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Job progress (0-1)")


# Convenience type aliases
PolymerType = Literal["protein", "dna", "rna"]
OutputFormat = Literal["mmcif"]
JobStatus = Literal["pending", "running", "completed", "failed"]
AlignmentFormat = Literal["sto", "a3m", "csv", "fasta"]
ConstraintType = Literal["pocket", "bond"]


# Add YAML configuration models at the end of the file

class YAMLProtein(BaseModel):
    """YAML protein configuration matching official Boltz format."""
    id: str = Field(..., description="Protein identifier")
    sequence: str = Field(..., description="Protein sequence")
    msa: Optional[str] = Field(None, description="Path to MSA file or 'empty'")


class YAMLLigand(BaseModel):
    """YAML ligand configuration matching official Boltz format."""
    id: str = Field(..., description="Ligand identifier")
    smiles: str = Field(..., description="SMILES string")


class YAMLSequence(BaseModel):
    """YAML sequence entry (protein or ligand)."""
    protein: Optional[YAMLProtein] = Field(None, description="Protein configuration")
    ligand: Optional[YAMLLigand] = Field(None, description="Ligand configuration")
    
    @validator('ligand', always=True)
    def validate_protein_or_ligand(cls, v, values):
        """Ensure either protein or ligand is specified, but not both."""
        protein = values.get('protein')
        if protein and v:
            raise ValueError("Cannot specify both protein and ligand in the same sequence entry")
        if not protein and not v:
            raise ValueError("Must specify either protein or ligand in sequence entry")
        return v


class YAMLAffinity(BaseModel):
    """YAML affinity property configuration."""
    binder: str = Field(..., description="ID of the binding molecule (ligand)")


class YAMLProperties(BaseModel):
    """YAML properties configuration."""
    affinity: Optional[YAMLAffinity] = Field(None, description="Affinity prediction configuration")


class YAMLConfig(BaseModel):
    """Complete YAML configuration matching official Boltz format."""
    version: int = Field(1, description="Configuration version")
    sequences: List[YAMLSequence] = Field(..., description="List of sequences (proteins and ligands)")
    properties: Optional[YAMLProperties] = Field(None, description="Properties to predict")
    
    @validator('sequences')
    def validate_sequences(cls, v):
        """Validate sequences list."""
        if len(v) == 0:
            raise ValueError("At least one sequence must be specified")
        return v
    
    def to_prediction_request(self) -> PredictionRequest:
        """Convert YAML config to PredictionRequest."""
        polymers = []
        ligands = []
        
        for seq in self.sequences:
            if seq.protein:
                # Handle MSA
                msa_records = None
                if seq.protein.msa and seq.protein.msa != "empty":
                    # For now, we'll handle MSA files separately
                    # This would need to be loaded from the file path
                    pass
                
                polymer = Polymer(
                    id=seq.protein.id,
                    molecule_type="protein",
                    sequence=seq.protein.sequence,
                    msa=msa_records
                )
                polymers.append(polymer)
            
            elif seq.ligand:
                ligand = Ligand(
                    id=seq.ligand.id,
                    smiles=seq.ligand.smiles
                )
                ligands.append(ligand)
        
        return PredictionRequest(
            polymers=polymers,
            ligands=ligands if ligands else None
        )


# Convenience type aliases
YAMLConfigType = YAMLConfig 