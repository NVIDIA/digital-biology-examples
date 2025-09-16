# YAML Configuration Guide for Boltz-2 Python Client

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.

This guide explains how to use YAML configuration files with the Boltz-2 Python Client, following the official Boltz repository format.

## Overview

The Boltz-2 Python Client supports the official YAML configuration format used by the original Boltz implementation. This allows you to:

- Use existing Boltz YAML configurations without modification
- Define complex molecular systems in a structured format
- Predict binding affinities alongside structure prediction
- Include MSA files for enhanced protein predictions
- Easily share and reproduce prediction configurations

## YAML Format Specification

### Basic Structure

```yaml
version: 1  # Configuration version (required)
sequences:  # List of molecular sequences (required)
  - protein:
      id: A
      sequence: "PROTEIN_SEQUENCE"
      msa: "optional_msa_file.a3m"  # optional
  - ligand:
      id: B
      smiles: "LIGAND_SMILES"
properties:  # Optional properties to predict
  affinity:
    binder: B  # ID of the binding molecule
```

### Supported Molecule Types

#### Proteins
```yaml
- protein:
    id: A                    # Unique identifier (A-Z or 4 alphanumeric chars)
    sequence: "MKTVRQERLK..." # Amino acid sequence
    msa: "protein_A.a3m"     # Optional MSA file path or "empty"
```

#### Ligands
```yaml
- ligand:
    id: B                    # Unique identifier
    smiles: "CC(=O)O"        # SMILES string representation
```

#### Multiple Proteins
```yaml
- protein:
    id: A
    sequence: "SEQUENCE_1"
    msa: "empty"
- protein:
    id: B
    sequence: "SEQUENCE_2"
    msa: "empty"
```

### Properties

#### Binding Affinity Prediction
```yaml
properties:
  affinity:
    binder: B  # ID of the ligand that binds to the protein
```

## Example Configurations

### 1. Basic Protein-Ligand Complex

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
  - ligand:
      id: B
      smiles: "CC(=O)O"
```

### 2. Binding Affinity Prediction

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "SGFRKMAFPSGKVEGCMVQVTCGTTTLNGLWLDDVVYCPRHVICTSEDMLNPNYEDLLIRKSNHNFLVQAGNVQLRV..."
      msa: "protein_A.a3m"  # MSA file for better accuracy
  - ligand:
      id: B
      smiles: "N[C@@H](Cc1ccc(O)cc1)C(=O)O"
properties:
  affinity:
    binder: B
```

### 3. SARS-CoV-2 Mpro with Nirmatrelvir

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "SGFRKMAFPSGKVEGCMVQVTCGTTTLNGLWLDDVVYCPRHVICTSEDMLNPNYEDLLIRKSNHNFLVQAGNVQLRV..."
  - ligand:
      id: X
      smiles: "N#C[C@H](C[C@@H]1CCNC1=O)NC(=O)[C@H]1N(C[C@H]2[C@@H]1C2(C)C)C(=O)[C@H](C(C)(C)C)NC(=O)C(F)(F)F"
```

### 4. Multi-Protein Complex

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
      msa: "empty"
  - protein:
      id: B
      sequence: "MVTPEGNVSLVDESLLVGVTDEDRAVRSAHQFYERLIGLWAPAVMEAAHELGVFAALAEAPADSGELARRLDCDARAMRVLLDALYAYDVIDRIHDTNGFRYLLSAEARECLLPGTLFSLVGKFMHDINVAWPAWRNLAEVVRHGARDTSGAESPNGIAQEDYESLVGGINFWAPPIVTTLSRKLRASGRSGDATASVLDVGCGTGLYSQLLLREFPRWTATGLDVERIATLANAQALRLGVEERFATRAGDFWRGGWGTGYDLVLFANIFHLQTPASAVRLMRHAAACLAPDGLVAVVDQIVDADREPKTPQDRFALLFAASMTNTGGGDAYTFQEYEEWFTAAGLQRIETLDTPMHRILLARRATEPSAVPEGQASENLYFQ"
      msa: "empty"
```

## MSA File Support

### Supported Formats
- **A3M**: `.a3m` - HHsuite format
- **STO**: `.sto` - Stockholm format  
- **FASTA**: `.fasta` - Standard FASTA alignment
- **CSV**: `.csv` - Comma-separated values

### MSA File Specification
```yaml
- protein:
    id: A
    sequence: "PROTEIN_SEQUENCE"
    msa: "protein_A.a3m"  # Path relative to YAML file
```

### MSA Directory Structure
```
project/
├── config.yaml
├── msas/
│   ├── protein_A.a3m
│   └── protein_B.sto
└── outputs/
```

## Usage Methods

### 1. Command Line Interface

#### Basic Usage
```bash
# Run prediction from YAML file
boltz2 yaml protein_ligand.yaml

# With custom parameters
boltz2 yaml config.yaml --recycling-steps 5 --sampling-steps 100 --diffusion-samples 3

# With custom MSA directory
boltz2 yaml config.yaml --msa-dir /path/to/msa/files

# Save to specific directory
boltz2 yaml config.yaml --output-dir ./results
```

#### Available CLI Parameters
- `--recycling-steps` (1-6): Number of recycling steps (default: 3)
- `--sampling-steps` (10-1000): Number of sampling steps (default: 50)
- `--diffusion-samples` (1-5): Number of diffusion samples (default: 1)
- `--step-scale` (0.5-5.0): Step scale for diffusion sampling (default: 1.638)
- `--msa-dir`: Directory containing MSA files (default: same as YAML file)
- `--output-dir`: Output directory for results (default: current directory)
- `--no-save`: Don't save structure files (for testing)

### 2. Python API

#### Load from File
```python
import asyncio
from boltz2_client import Boltz2Client

async def predict_from_yaml():
    client = Boltz2Client(base_url="http://localhost:8000")
    
    # Load and run prediction from YAML file
    result = await client.predict_from_yaml_file("config.yaml")
    
    print(f"Confidence: {result.confidence_scores[0]:.3f}")

asyncio.run(predict_from_yaml())
```

#### Load from String
```python
yaml_content = """
version: 1
sequences:
  - protein:
      id: A
      sequence: "MKTVRQERLK..."
  - ligand:
      id: B
      smiles: "CC(=O)O"
"""

result = await client.predict_from_yaml_config(yaml_content)
```

#### Create Programmatically
```python
# Create YAML config programmatically
config = client.create_yaml_config(
    proteins=[("A", "MKTVRQERLK...", "protein_A.a3m")],
    ligands=[("B", "CC(=O)O")],
    predict_affinity=True,
    binder_id="B"
)

# Save to file
client.save_yaml_config(config, "my_config.yaml")

# Run prediction
result = await client.predict_from_yaml_config(config)
```

### 3. Endpoint Configuration

#### Local Deployment
```bash
boltz2 --base-url http://localhost:8000 yaml config.yaml
```

#### NVIDIA Hosted Endpoint
```bash
export NVIDIA_API_KEY=your_api_key
boltz2 --base-url https://health.api.nvidia.com --endpoint-type nvidia_hosted yaml config.yaml
```

## Advanced Features

### Parameter Override
CLI parameters override YAML defaults:
```bash
# YAML file has default parameters, but CLI overrides them
boltz2 yaml config.yaml --recycling-steps 6 --step-scale 2.0
```

### Batch Processing
Process multiple YAML files:
```bash
# Process all YAML files in a directory
for yaml_file in configs/*.yaml; do
    boltz2 yaml "$yaml_file" --output-dir "results/$(basename "$yaml_file" .yaml)"
done
```

### Custom MSA Handling
```python
# Load YAML with custom MSA directory
result = await client.predict_from_yaml_config(
    "config.yaml",
    msa_dir=Path("/custom/msa/directory")
)
```

## Validation and Error Handling

### YAML Validation
The client validates YAML configurations:
- Required fields: `version`, `sequences`
- Sequence validation: protein/ligand mutual exclusion
- ID format validation: A-Z or 4 alphanumeric characters
- SMILES/CCD validation for ligands

### Common Errors
1. **Missing MSA files**: Warning displayed, prediction continues
2. **Invalid SMILES**: Validation error before prediction
3. **Malformed YAML**: Parsing error with helpful message
4. **Missing required fields**: Clear validation error

### Error Example
```bash
❌ YAML prediction failed: Must specify either protein or ligand in sequence entry
```

## Best Practices

### 1. File Organization
```
project/
├── configs/
│   ├── protein_ligand.yaml
│   ├── sars_cov2_mpro_nirmatrelvir.yaml
│   └── multi_protein.yaml
├── msas/
│   ├── protein_A.a3m
│   └── protein_B.sto
├── results/
│   ├── protein_ligand/
│   ├── sars_cov2_mpro_nirmatrelvir/
│   └── multi_protein/
└── scripts/
    └── run_predictions.sh
```

### 2. MSA File Management
- Use relative paths in YAML files
- Keep MSA files in a dedicated directory
- Use descriptive filenames matching protein IDs

### 3. Configuration Naming
- Use descriptive YAML filenames
- Include target information: `sars_cov2_mpro_nirmatrelvir.yaml`
- Version configurations: `config_v1.yaml`, `config_v2.yaml`

### 4. Parameter Tuning
- Start with default parameters
- Increase `recycling_steps` for better accuracy (slower)
- Use multiple `diffusion_samples` for ensemble predictions
- Adjust `step_scale` for diversity vs accuracy trade-off

## Compatibility

### Official Boltz Repository
The YAML format is fully compatible with the official Boltz format. You can:
- Use existing Boltz YAML files without modification
- Share configurations between different Boltz implementations
- Follow official Boltz documentation and examples

### Version Support
- **Version 1**: Current supported version
- Future versions will maintain backward compatibility

## Troubleshooting

### Common Issues

1. **YAML parsing errors**
   ```bash
   # Check YAML syntax
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

2. **MSA file not found**
   ```bash
   # Check MSA file paths
   boltz2 yaml config.yaml --msa-dir /correct/path/to/msas
   ```

3. **Service connection issues**
   ```bash
   # Check service health
   boltz2 health
   ```

### Debug Mode
```bash
# Enable verbose output
boltz2 --verbose yaml config.yaml
```

## Examples Repository

The `examples/` directory contains sample YAML files:
- `protein_ligand.yaml` - Basic protein-ligand complex
- `sars_cov2_mpro_nirmatrelvir.yaml` - SARS-CoV-2 Mpro example
- `multi_protein_complex.yaml` - Multi-protein complex

## Further Reading

- [Boltz-2 Python Client](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2)
- [Boltz-2 Technical Report](https://cdn.prod.website-files.com/68404fd075dba49e58331ad9/6842ee1285b9af247ac5a122_boltz2.pdf)
- [NVIDIA BioNeMo Documentation](https://docs.nvidia.com/bionemo/)

## Support

For issues with YAML configuration:
1. Check the examples in this repository
2. Validate YAML syntax
3. Verify MSA file paths
4. Test with simple configurations first
5. Check service health and connectivity
---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.
