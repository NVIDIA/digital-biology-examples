# Boltz-2 API Parameters Reference

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

This document provides a comprehensive reference for all available Boltz-2 API parameters, their ranges, effects, and usage examples.

## Table of Contents

1. [Core Parameters](#core-parameters)
2. [Diffusion Parameters](#diffusion-parameters)
3. [Molecular Components](#molecular-components)
4. [Constraints](#constraints)
5. [Advanced Parameters](#advanced-parameters)
6. [MSA Parameters](#msa-parameters)
7. [Affinity Prediction Parameters](#affinity-prediction-parameters)
8. [Parameter Combinations](#parameter-combinations)
9. [Usage Examples](#usage-examples)

## Core Parameters

### Required Parameters

#### `polymers` (List[Polymer])
- **Description**: List of polymers (DNA, RNA, or Protein) to predict
- **Range**: 1-5 polymers
- **Required**: Yes
- **Example**:
```python
polymers = [
    Polymer(
        id="A",
        molecule_type="protein",
        sequence="MKTVRQERLK..."
    )
]
```

### Optional Parameters

#### `ligands` (List[Ligand])
- **Description**: List of ligands for complex prediction
- **Range**: 0-5 ligands
- **Required**: No
- **Default**: None
- **Example**:
```python
ligands = [
    Ligand(
        id="LIG",
        smiles="CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
    )
]
```

## Diffusion Parameters

### `recycling_steps` (int)
- **Description**: Number of recycling steps for iterative refinement
- **Range**: 1-6
- **Default**: 3
- **Effect**: Higher values improve accuracy but increase computation time
- **Recommendations**:
  - 1-2: Fast, lower accuracy
  - 3-4: Balanced (recommended)
  - 5-6: High accuracy, slower

### `sampling_steps` (int)
- **Description**: Number of diffusion sampling steps
- **Range**: 10-1000
- **Default**: 50
- **Effect**: More steps generally improve quality but increase time
- **Recommendations**:
  - 10-30: Fast prototyping
  - 50-100: Standard quality
  - 200-1000: High quality, research use

### `diffusion_samples` (int)
- **Description**: Number of independent diffusion samples
- **Range**: 1-5
- **Default**: 1
- **Effect**: Multiple samples provide diversity and ensemble predictions
- **Usage**: Use >1 for uncertainty estimation or best-of-N selection

### `step_scale` (float)
- **Description**: Controls the temperature of diffusion sampling
- **Range**: 0.5-5.0
- **Default**: 1.638
- **Effect**: 
  - Lower values (0.5-1.0): More conservative, less diversity
  - Higher values (2.0-5.0): More diverse, potentially less accurate
- **Recommendations**:
  - 0.5-1.0: High confidence predictions
  - 1.2-2.0: Balanced exploration
  - 2.5-5.0: Maximum diversity

## Molecular Components

### Polymer Types

#### Protein
```python
Polymer(
    id="A",
    molecule_type="protein",
    sequence="MKTVRQERLK...",  # Standard amino acids
    cyclic=False,
    modifications=[]
)
```

#### DNA
```python
Polymer(
    id="C",
    molecule_type="dna",
    sequence="ATCGATCG",  # A, T, C, G only
    cyclic=False,
    modifications=[]
)
```

#### RNA
```python
Polymer(
    id="R",
    molecule_type="rna",
    sequence="AUCGAUCG",  # A, U, C, G only
    cyclic=False,
    modifications=[]
)
```

### Ligand Types

#### SMILES-based Ligands
```python
Ligand(
    id="LIG1",
    smiles="CC(=O)OC1=CC=CC=C1C(=O)O"  # Aspirin
)
```

#### CCD-based Ligands
```python
Ligand(
    id="LIG2",
    ccd="ATP"  # Standard CCD code
)
```

## Constraints

### Pocket Constraints
Define binding pockets for ligand placement:

```python
PocketConstraint(
    constraint_type="pocket",
    ligand_id="LIG",
    polymer_id="A",
    residue_ids=[10, 15, 20, 25, 30]  # 1-based indexing
)
```

### Bond Constraints
Define covalent bonds between atoms:

```python
BondConstraint(
    constraint_type="bond",
    atoms=[
        Atom(id="A", residue_index=12, atom_name="SG"),  # Cys12 sulfur
        Atom(id="LIG", residue_index=1, atom_name="C22")  # Ligand carbon
    ]
)
```

## Advanced Parameters

### `without_potentials` (bool)
- **Description**: Run prediction without physics-based potentials
- **Default**: False
- **Effect**: Faster but potentially less accurate
- **Usage**: Experimental feature for speed optimization

### `output_format` (str)
- **Description**: Output structure format
- **Options**: "mmcif"
- **Default**: "mmcif"
- **Note**: Currently only mmCIF format is supported

### `concatenate_msas` (bool)
- **Description**: Concatenate Multiple Sequence Alignments for polymers
- **Default**: False
- **Effect**: Combines MSAs into single alignment
- **Usage**: For related polymer sequences

## MSA Parameters

### MSA File Formats
Supported formats for Multiple Sequence Alignments:

- **sto**: Stockholm format
- **a3m**: A3M format (HHsuite)
- **csv**: Comma-separated values
- **fasta**: FASTA format

### MSA Usage Example

#### Method 1: Using Helper Function (Recommended)
```python
# Using the msa_files helper (automatically converts to server schema)
result = await client.predict_protein_structure(
    sequence="MKTVRQERLK...",
    msa_files=[("alignment.a3m", "a3m")],  # List of (file_path, format) tuples
    recycling_steps=3,
    sampling_steps=50
)
```

#### Method 2: Manual MSA Record Creation (Advanced)
```python
# Create MSA record manually
msa_record = AlignmentFileRecord(
    alignment=msa_content,  # File content as string
    format="a3m",
    rank=0  # Ordering rank
)

# Add to polymer
polymer = Polymer(
    id="A",
    molecule_type="protein",
    sequence="MKTVRQERLK...",
    msa=[msa_record]
)
```

## Affinity Prediction Parameters

### Ligand-Specific Parameters

#### `predict_affinity` (bool)
- **Description**: Enable affinity prediction for a specific ligand
- **Default**: False
- **Required**: No
- **Note**: Only ONE ligand per request can have this enabled
- **Example**:
```python
ligand = Ligand(
    id="LIG",
    smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
    predict_affinity=True  # Enable affinity prediction
)
```

### Global Affinity Parameters

#### `sampling_steps_affinity` (int)
- **Description**: Number of sampling steps for affinity prediction
- **Range**: 10-1000
- **Default**: 200
- **Effect**: Higher values may improve accuracy but increase runtime
- **Recommendations**:
  - 50-100: Fast testing
  - 200-300: Production use
  - 500-1000: High accuracy research

#### `diffusion_samples_affinity` (int)
- **Description**: Number of diffusion samples for affinity prediction
- **Range**: 1-10
- **Default**: 5
- **Effect**: Higher values provide ensemble predictions and reliability
- **Recommendations**:
  - 1-3: Fast predictions
  - 5-8: Balanced accuracy
  - 10: Maximum ensemble diversity

#### `affinity_mw_correction` (bool)
- **Description**: Apply molecular weight correction to affinity predictions
- **Default**: False
- **Effect**: Adjusts predictions based on ligand molecular weight
- **Usage**: Recommended for diverse ligand libraries

### Affinity Response Fields

The response includes an `affinities` dictionary with the following fields for each ligand:

- `affinity_pred_value`: Raw affinity predictions (log scale)
- `affinity_pic50`: pIC50 values (-log10 of IC50 in M)
- `affinity_probability_binary`: Binary binding probability (0-1)
- `model_*_affinity_*`: Individual model predictions for ensemble analysis

### Affinity Usage Example

```python
from boltz2_client import Boltz2Client, Polymer, Ligand

client = Boltz2Client()

# Define protein and ligand
protein = Polymer(id="A", molecule_type="protein", sequence="YOUR_SEQUENCE")
ligand = Ligand(id="LIG", smiles="YOUR_SMILES", predict_affinity=True)

# Predict with affinity
result = await client.predict_structure(
    polymers=[protein],
    ligands=[ligand],
    sampling_steps_affinity=300,
    diffusion_samples_affinity=8,
    affinity_mw_correction=True
)

# Access results
if result.affinities and "LIG" in result.affinities:
    affinity = result.affinities["LIG"]
    ic50_nm = 10**(-affinity.affinity_pic50[0]) * 1e9
    print(f"pIC50: {affinity.affinity_pic50[0]:.2f}")
    print(f"IC50: {ic50_nm:.1f} nM")
    print(f"Binding probability: {affinity.affinity_probability_binary[0]:.1%}")
```

## Parameter Combinations

### High-Quality Prediction
```python
request = PredictionRequest(
    polymers=polymers,
    recycling_steps=5,
    sampling_steps=200,
    diffusion_samples=3,
    step_scale=1.2
)
```

### Fast Prediction
```python
request = PredictionRequest(
    polymers=polymers,
    recycling_steps=2,
    sampling_steps=20,
    diffusion_samples=1,
    step_scale=1.638
)
```

### Diverse Sampling
```python
request = PredictionRequest(
    polymers=polymers,
    recycling_steps=3,
    sampling_steps=100,
    diffusion_samples=5,
    step_scale=2.5
)
```

### Conservative Prediction
```python
request = PredictionRequest(
    polymers=polymers,
    recycling_steps=4,
    sampling_steps=100,
    diffusion_samples=1,
    step_scale=0.8
)
```

## Usage Examples

### 1. Basic Protein Prediction
```python
from boltz2_client import Boltz2Client
from boltz2_client.models import Polymer, PredictionRequest

client = Boltz2Client()

polymer = Polymer(
    id="A",
    molecule_type="protein",
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
)

request = PredictionRequest(polymers=[polymer])
result = await client.predict(request)
```

### 2. Protein-Ligand Complex
```python
protein = Polymer(
    id="A",
    molecule_type="protein",
    sequence="PROTEIN_SEQUENCE"
)

ligand = Ligand(
    id="LIG",
    smiles="CC(=O)OC1=CC=CC=C1C(=O)O"
)

# Define binding pocket
pocket = PocketConstraint(
    ligand_id="LIG",
    polymer_id="A",
    residue_ids=[10, 15, 20, 25]
)

request = PredictionRequest(
    polymers=[protein],
    ligands=[ligand],
    constraints=[pocket],
    recycling_steps=4,
    sampling_steps=100
)
```

### 3. Covalent Complex
```python
protein = Polymer(
    id="A",
    molecule_type="protein",
    sequence="PROTEIN_WITH_CYSTEINE"
)

ligand = Ligand(
    id="LIG",
    ccd="U4U"
)

# Define covalent bond
bond = BondConstraint(
    constraint_type="bond",
    atoms=[
        Atom(id="A", residue_index=12, atom_name="SG"),
        Atom(id="LIG", residue_index=1, atom_name="C22")
    ]
)

request = PredictionRequest(
    polymers=[protein],
    ligands=[ligand],
    constraints=[bond]
)
```

### 4. DNA-Protein Complex
```python
proteins = [
    Polymer(id="A", molecule_type="protein", sequence="PROTEIN1"),
    Polymer(id="B", molecule_type="protein", sequence="PROTEIN2")
]

dna = [
    Polymer(id="C", molecule_type="dna", sequence="ATCGATCG"),
    Polymer(id="D", molecule_type="dna", sequence="CGATCGAT")
]

request = PredictionRequest(
    polymers=proteins + dna,
    recycling_steps=3,
    sampling_steps=50,
    concatenate_msas=True
)
```

### 5. MSA-Guided Prediction

#### Method 1: Using Helper Function (Recommended)
```python
# Using the msa_files helper for automatic schema conversion
result = await client.predict_protein_structure(
    sequence="PROTEIN_SEQUENCE",
    msa_files=[("alignment.a3m", "a3m")],  # Helper automatically converts to nested dict
    recycling_steps=4,
    sampling_steps=100
)
```

#### Method 2: Manual Request Creation (Advanced)
```python
# Load MSA content manually
with open("alignment.a3m", "r") as f:
    msa_content = f.read()

msa_record = AlignmentFileRecord(
    alignment=msa_content,
    format="a3m",
    rank=0
)

protein = Polymer(
    id="A",
    molecule_type="protein",
    sequence="PROTEIN_SEQUENCE",
    msa=[msa_record]
)

request = PredictionRequest(
    polymers=[protein],
    recycling_steps=4,
    sampling_steps=100
)
```

### 6. Multi-Ligand System
```python
protein = Polymer(
    id="A",
    molecule_type="protein",
    sequence="PROTEIN_SEQUENCE"
)

ligands = [
    Ligand(id="LIG1", smiles="SMILES1"),
    Ligand(id="LIG2", smiles="SMILES2"),
    Ligand(id="LIG3", ccd="ATP"),
    Ligand(id="LIG4", ccd="GTP")
]

request = PredictionRequest(
    polymers=[protein],
    ligands=ligands,
    recycling_steps=5,
    sampling_steps=150,
    diffusion_samples=2
)
```

## Performance Considerations

### Speed vs Quality Trade-offs

| Parameter | Fast | Balanced | High Quality |
|-----------|------|----------|--------------|
| recycling_steps | 1-2 | 3-4 | 5-6 |
| sampling_steps | 10-30 | 50-100 | 200-1000 |
| diffusion_samples | 1 | 1-2 | 3-5 |
| step_scale | 1.638 | 1.2-2.0 | 0.8-1.5 |

### Memory Usage
- More polymers and ligands increase memory usage
- Higher sampling_steps and diffusion_samples require more memory
- Complex constraints may increase computational overhead

### Recommended Workflows

#### Development/Testing
```python
recycling_steps=2
sampling_steps=20
diffusion_samples=1
step_scale=1.638
```

#### Production/Research
```python
recycling_steps=4
sampling_steps=100
diffusion_samples=2
step_scale=1.2
```

#### High-Accuracy Research
```python
recycling_steps=6
sampling_steps=500
diffusion_samples=5
step_scale=1.0
```

## Error Handling

### Common Parameter Errors

1. **Invalid ranges**: Parameters outside allowed ranges
2. **Missing required fields**: Polymers list cannot be empty
3. **Constraint validation**: Invalid atom references in constraints
4. **Sequence validation**: Invalid characters for molecule type
5. **Ligand validation**: Must specify either SMILES or CCD, not both

### Validation Examples
```python
# This will raise validation error
try:
    request = PredictionRequest(
        polymers=[],  # Empty list not allowed
        recycling_steps=10  # Outside range 1-6
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Best Practices

1. **Start with default parameters** for initial testing
2. **Use MSAs when available** for better accuracy
3. **Define constraints carefully** with correct atom names and indices
4. **Monitor confidence scores** to assess prediction quality
5. **Use multiple diffusion_samples** for uncertainty estimation
6. **Adjust step_scale** based on desired diversity
7. **Save intermediate results** for long-running predictions
8. **Validate sequences** before submission

## CLI Usage

All parameters can be used via the command-line interface:

```bash
# Basic protein prediction
boltz2 protein "SEQUENCE" --recycling-steps 4 --sampling-steps 100

# Protein prediction with MSA
boltz2 protein "SEQUENCE" --msa-file alignment.a3m a3m --recycling-steps 4

# Protein-ligand complex
boltz2 ligand "PROTEIN_SEQ" --smiles "SMILES" --pocket-residues "10,15,20"

# Covalent protein-ligand complex
boltz2 covalent "PROTEIN_SEQ" --ccd U4U --bond A:12:SG:LIG:C22

# Disulfide bond formation
boltz2 covalent "PROTEIN_SEQ" --disulfide A:12:A:45

# DNA-protein complex
boltz2 dna-protein --protein-sequences "PROT1,PROT2" --dna-sequences "ATCG,CGTA"

# YAML configuration
boltz2 yaml config.yaml --recycling-steps 5

# Advanced configuration
boltz2 advanced --config-file config.json
```

For complete CLI documentation, run:
```bash
boltz2 --help
boltz2 covalent --help
boltz2 examples
```
---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
