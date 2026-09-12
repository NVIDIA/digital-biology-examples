# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------


"""
Data models for Boltz-2 API requests and responses.

This module defines Pydantic models that represent the data structures
used by the Boltz-2 API, providing type safety and validation for all
available parameters and features.
"""

from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, ValidationInfo
from datetime import datetime
import re


class RequestModel(BaseModel):
    """Reject misspelled or unsupported request fields instead of dropping them."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AffinityPrediction(BaseModel):
    """Affinity prediction results for a ligand."""
    model_config = ConfigDict(extra="allow")

    affinity_embedding: Optional[List[List[float]]] = None
    model_1_affinity_embedding: Optional[List[List[float]]] = None
    model_2_affinity_embedding: Optional[List[List[float]]] = None
    
    affinity_pred_value: List[float] = Field(
        ..., description="The predicted log(IC50) values"
    )
    affinity_probability_binary: List[float] = Field(
        ..., description="The binary affinity prediction probability (0-1)"
    )
    model_1_affinity_pred_value: List[float] = Field(
        ..., description="The predicted log(IC50) from Model 1"
    )
    model_1_affinity_probability_binary: List[float] = Field(
        ..., description="The binary affinity prediction probability from Model 1"
    )
    model_2_affinity_pred_value: List[float] = Field(
        ..., description="The predicted log(IC50) from Model 2"
    )
    model_2_affinity_probability_binary: List[float] = Field(
        ..., description="The binary affinity prediction probability from Model 2"
    )
    affinity_pic50: List[float] = Field(
        ..., description="Predicted pIC50 binding affinity (-log10 of IC50 in molar)"
    )


class Modification(RequestModel):
    """Represents a chemical modification to a polymer chain."""
    ccd: str = Field(..., description="The Chemical Component Dictionary (CCD) ID of the modification (1-5 uppercase letters/numbers)")
    position: int = Field(..., gt=0, description="The 1-based index of the residue to modify")
    
    @field_validator('ccd')
    @classmethod
    def validate_ccd(cls, v):
        """Validate CCD code format."""
        if not re.match(r'^[A-Z0-9]{1,5}$', v):
            raise ValueError("CCD code must be 1-5 uppercase letters/numbers")
        return v


class AlignmentFileRecord(RequestModel):
    """Represents a single alignment file record."""
    alignment: str = Field(..., description="Raw alignment file content as string")
    format: Literal["sto", "a3m", "csv", "fasta"] = Field(..., description="Alignment file format")
    rank: Optional[int] = Field(-1, description="Integer rank to define ordering of alignments")
    
    @field_validator('alignment')
    @classmethod
    def validate_alignment_content(cls, v):
        """Validate alignment content is not empty."""
        if not v.strip():
            raise ValueError("Alignment content cannot be empty")
        return v


class StructuralTemplate(RequestModel):
    """A structural template to guide protein structure prediction."""
    structure: str = Field(..., min_length=1, description="The template structure content in CIF or PDB format")
    format: Literal["cif", "pdb"] = Field("cif", description="Format of the structure (cif or pdb)")
    name: Optional[str] = Field(None, description="Optional name for the template (max 64 chars, alphanumeric with -_)")
    chain_id: Optional[str] = Field(None, description="Optional chain ID to use from the template structure (1-4 alphanumeric)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate template name format."""
        if v is not None:
            if len(v) > 64:
                raise ValueError("Template name must be 64 characters or less")
            if not re.match(r'^[A-Za-z0-9_-]+$', v):
                raise ValueError("Template name must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    @field_validator('chain_id')
    @classmethod
    def validate_chain_id(cls, v):
        """Validate chain ID format."""
        if v is not None:
            if not re.match(r'^[A-Za-z0-9]{1,4}$', v):
                raise ValueError("Chain ID must be 1-4 alphanumeric characters")
        return v


class Polymer(RequestModel):
    """Represents a polymer (protein, DNA, or RNA) in the prediction request."""
    
    id: Optional[str] = Field(None, description="Unique identifier for the polymer (1-4 alphanumeric chars)")
    molecule_type: Literal["protein", "dna", "rna"] = Field(..., description="Type of molecule")
    sequence: str = Field(..., min_length=1, max_length=4096, description="Sequence string (default NIM limit: 4096 characters)")
    cyclic: Optional[bool] = Field(False, description="Whether the polymer is cyclic")
    modifications: Optional[List[Modification]] = Field(default_factory=list, description="List of modifications")
    msa: Optional[Dict[str, Dict[str, AlignmentFileRecord]]] = Field(None, description="A Dictionary [database_name -> [format -> AlignmentFileRecord]] containing alignments")
    structural_templates: Optional[List[StructuralTemplate]] = Field(None, description="Structural templates to guide prediction (max 4, protein only)")
    
    @field_validator('sequence')
    @classmethod
    def validate_sequence(cls, v, info: ValidationInfo):
        """Validate sequence based on molecule type."""
        molecule_type = info.data.get('molecule_type')
        if molecule_type is None:
            return v
        
        if molecule_type == "protein":
            valid_chars = set("ACDEFGHIKLMNPQRSTVWYX")
            if not all(c.upper() in valid_chars for c in v):
                raise ValueError(f"Invalid amino acid characters in protein sequence: {v}")
        elif molecule_type == "dna":
            valid_chars = set("ATCG")
            if not all(c.upper() in valid_chars for c in v):
                raise ValueError(f"Invalid DNA base characters in sequence: {v}")
        elif molecule_type == "rna":
            valid_chars = set("AUCG")
            if not all(c.upper() in valid_chars for c in v):
                raise ValueError(f"Invalid RNA base characters in sequence: {v}")
        
        return v.upper()
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate polymer ID format (1-4 alphanumeric characters)."""
        if v is not None:
            if not re.match(r'^[A-Za-z0-9]{1,4}$', v):
                raise ValueError("Polymer ID must be 1-4 alphanumeric characters")
        return v
    
    @field_validator('structural_templates')
    @classmethod
    def validate_structural_templates(cls, v, info: ValidationInfo):
        """Validate structural templates."""
        if v is not None:
            if len(v) > 4:
                raise ValueError("Maximum 4 structural templates allowed")
            molecule_type = info.data.get('molecule_type')
            if molecule_type and molecule_type != "protein":
                raise ValueError("Structural templates are only allowed for protein molecules")
        return v

    @model_validator(mode='after')
    def validate_polymer_features(self):
        if self.msa is not None:
            if self.molecule_type != 'protein':
                raise ValueError("MSAs are only allowed for protein molecules")
            if len(self.msa) > 3:
                raise ValueError("Maximum 3 MSA database entries allowed")
            for records in self.msa.values():
                for fmt, record in records.items():
                    if fmt != record.format:
                        raise ValueError("MSA format key must match the alignment record format")
        for modification in self.modifications or []:
            if modification.position > len(self.sequence):
                raise ValueError("Modification position exceeds the polymer length")
        return self


class Ligand(RequestModel):
    """Represents a ligand in the prediction request."""
    
    id: Optional[str] = Field(None, description="Chain ID for the ligand")
    smiles: Optional[str] = Field(None, description="SMILES string representation")
    ccd: Optional[str] = Field(None, description="Chemical Component Dictionary (CCD) code (1-5 uppercase letters/numbers)")
    predict_affinity: Optional[bool] = Field(False, description="Run affinity prediction for this ligand. Note: only one ligand per request can have this enabled")
    output_affinity_embedding: bool = Field(False, description="Return affinity embeddings (NIM 1.8+; requires predict_affinity)")
    
    @field_validator('smiles')
    @classmethod
    def validate_smiles(cls, v):
        """Basic SMILES validation."""
        if v is not None:
            if not v.strip():
                raise ValueError("SMILES string cannot be empty")
            if any(char in v for char in [' ', '\t', '\n']):
                raise ValueError("SMILES string should not contain whitespace")
            return v.strip()
        return v
    
    @field_validator('ccd')
    @classmethod
    def validate_ccd(cls, v):
        """Basic CCD code validation."""
        if v is not None:
            if not v.strip():
                raise ValueError("CCD code cannot be empty")
            if not re.match(r'^[A-Z0-9]{1,5}$', v.strip().upper()):
                raise ValueError("CCD code must be 1-5 uppercase letters/numbers")
            return v.strip().upper()
        return v
    
    @model_validator(mode='after')
    def validate_smiles_or_ccd(self):
        """Ensure either SMILES or CCD is provided, but not both."""
        if self.smiles and self.ccd:
            raise ValueError("Cannot specify both SMILES and CCD code")
        if not self.smiles and not self.ccd:
            raise ValueError("Must specify either SMILES or CCD code")
        if self.output_affinity_embedding and not self.predict_affinity:
            raise ValueError("output_affinity_embedding requires predict_affinity=True")
        return self
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate ligand ID format."""
        if v is not None:
            if not re.match(r'^[A-Za-z0-9_-]+$', v):
                raise ValueError("Ligand ID must contain only alphanumeric characters, underscores, and hyphens")
        return v


class Atom(RequestModel):
    """Represents an atom in constraints."""
    id: str = Field(..., description="Polymer/ligand ID (chain identifier)")
    residue_index: int = Field(..., gt=0, description="Residue index (1-based)")
    atom_name: str = Field(..., description="Atom name (e.g., 'CA', 'SG', 'C22')")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate atom ID format to match server-side validation."""
        if v is not None:
            if re.fullmatch(r'(?:[A-Z]{1,4}|[A-Za-z0-9]{4})', v):
                return v
            else:
                raise ValueError("Atom ID must be 1-4 uppercase letters or exactly 4 alphanumeric characters")
        return v


class Contact(RequestModel):
    """Represents a contact residue in a pocket constraint."""
    id: str = Field(..., pattern=r'^([A-Z]{1,4}|[A-Za-z0-9]{4})$', description="Chain identifier for the contact")
    residue_index: int = Field(..., gt=0, description="1-based index of the residue in the binding site")


class PocketConstraint(RequestModel):
    """Represents a pocket constraint defining a binding site."""
    constraint_type: Literal["pocket"] = Field("pocket", description="Type of constraint")
    binder: str = Field(..., description="ID of the binding molecule (e.g. ligand chain ID)")
    contacts: List[Contact] = Field(..., description="List of contacts defining the pocket")


class BondConstraint(RequestModel):
    """Represents a bond constraint between atoms."""
    constraint_type: Literal["bond"] = Field("bond", description="Type of constraint")
    atoms: List[Atom] = Field(..., description="List of atoms involved in the bond (exactly 2)")
    
    @field_validator('atoms')
    @classmethod
    def validate_atoms_count(cls, v):
        """Validate that exactly 2 atoms are specified for a bond."""
        if len(v) != 2:
            raise ValueError("Bond constraint must specify exactly 2 atoms")
        return v


class PredictionRequest(RequestModel):
    """Complete prediction request model with all available Boltz-2 parameters."""
    
    complex_id: Optional[str] = Field(
        None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$",
        description="NIM 1.9 artifact directory identifier; omitted uses prediction_timestamp"
    )

    # Required parameters
    polymers: List[Polymer] = Field(..., description="List of polymers (DNA, RNA, or Protein) - max 12, min 1")
    
    # Optional molecular components
    ligands: Optional[List[Ligand]] = Field(None, description="List of ligands - max 20, min 0")
    
    # Constraints
    constraints: Optional[List[Union[PocketConstraint, BondConstraint]]] = Field(
        None, description="Optional constraints for the prediction (pocket or bond constraints)"
    )
    
    # Diffusion and sampling parameters
    recycling_steps: Optional[int] = Field(
        3, ge=1, le=10, 
        description="The number of recycling steps to use for prediction (1-10, default: 3)"
    )
    sampling_steps: Optional[int] = Field(
        50, ge=10, le=1000,
        description="The number of sampling steps to use for prediction (10-1000, default: 50)"
    )
    diffusion_samples: Optional[int] = Field(
        1, ge=1, le=25,
        description="The number of diffusion samples to use for prediction (1-25, default: 1)"
    )
    step_scale: Optional[float] = Field(
        1.638, ge=0.5, le=5.0,
        description="Step size related to temperature of diffusion sampling. Lower = higher diversity (0.5-5.0, default: 1.638)"
    )
    
    # Advanced parameters
    max_parallel_samples: Optional[int] = Field(
        None, ge=1, le=25,
        description="Concurrent diffusion samples (NIM 1.9+); unset uses the server default"
    )
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
    
    # PAE/PDE output parameters (v1.5+)
    write_full_pae: Optional[bool] = Field(
        False,
        description="Write PAE matrices on the NIM server as NPZ files (JSON field is null in 1.9+)"
    )
    write_full_pde: Optional[bool] = Field(
        False,
        description="Write PDE matrices on the NIM server as NPZ files (JSON field is null in 1.9+)"
    )
    
    @field_validator('polymers')
    @classmethod
    def validate_polymers_count(cls, v):
        """Validate polymer count."""
        if len(v) > 12:
            raise ValueError("Maximum 12 polymers allowed")
        if len(v) == 0:
            raise ValueError("At least 1 polymer required")
        return v
    
    @field_validator('ligands')
    @classmethod
    def validate_ligands_count(cls, v):
        """Validate ligand count and affinity prediction constraints."""
        if v is not None:
            if len(v) > 20:
                raise ValueError("Maximum 20 ligands allowed")
            affinity_ligands = [lig for lig in v if getattr(lig, 'predict_affinity', False)]
            if len(affinity_ligands) > 1:
                raise ValueError("Only one ligand per request can have predict_affinity=True")
            if affinity_ligands:
                identities = [(lig.ccd, lig.smiles) for lig in v]
                if len(set(identities)) != len(identities):
                    raise ValueError("Duplicate CCD or SMILES values are not allowed with affinity prediction")
        return v
    
    @field_validator('constraints')
    @classmethod
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
    model_config = ConfigDict(extra="allow")
    
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
    
    # Full error matrices (v1.5+)
    pae: Optional[List[List[List[float]]]] = Field(
        None, 
        description="Legacy inline PAE matrices; deprecated and null in NIM 1.9+"
    )
    pde: Optional[List[List[List[float]]]] = Field(
        None, 
        description="Legacy inline PDE matrices; deprecated and null in NIM 1.9+"
    )
    
    @field_validator('structures')
    @classmethod
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

class YAMLProtein(RequestModel):
    """YAML protein configuration matching official Boltz format."""
    id: str = Field(..., description="Protein identifier")
    sequence: str = Field(..., description="Protein sequence")
    msa: Optional[str] = Field(None, description="Path to MSA file or 'empty'")


class YAMLLigand(RequestModel):
    """YAML ligand configuration matching official Boltz format."""
    id: str = Field(..., description="Ligand identifier")
    smiles: str = Field(..., description="SMILES string")


class YAMLSequence(RequestModel):
    """YAML sequence entry (protein or ligand)."""
    protein: Optional[YAMLProtein] = Field(None, description="Protein configuration")
    ligand: Optional[YAMLLigand] = Field(None, description="Ligand configuration")
    
    @model_validator(mode='after')
    def validate_protein_or_ligand(self):
        """Ensure either protein or ligand is specified, but not both."""
        if self.protein and self.ligand:
            raise ValueError("Cannot specify both protein and ligand in the same sequence entry")
        if not self.protein and not self.ligand:
            raise ValueError("Must specify either protein or ligand in sequence entry")
        return self


class YAMLAffinity(RequestModel):
    """YAML affinity property configuration."""
    binder: str = Field(..., description="ID of the binding molecule (ligand)")


class YAMLProperties(RequestModel):
    """YAML properties configuration."""
    affinity: Optional[YAMLAffinity] = Field(None, description="Affinity prediction configuration")


class YAMLConfig(RequestModel):
    """Complete YAML configuration matching official Boltz format."""
    version: Literal[1] = Field(1, description="Configuration version")
    sequences: List[YAMLSequence] = Field(..., description="List of sequences (proteins and ligands)")
    properties: Optional[Union[YAMLProperties, List[YAMLProperties]]] = Field(None, description="Properties to predict; Boltz list or legacy client mapping")
    
    @field_validator('sequences')
    @classmethod
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
        
        properties = self.properties if isinstance(self.properties, list) else [self.properties]
        for prop in properties:
            if prop and prop.affinity:
                matching = [lig for lig in ligands if lig.id == prop.affinity.binder]
                if len(matching) != 1:
                    raise ValueError("Affinity binder must identify exactly one ligand")
                matching[0].predict_affinity = True

        return PredictionRequest(
            polymers=polymers,
            ligands=ligands if ligands else None
        )


# Convenience type aliases
YAMLConfigType = YAMLConfig
