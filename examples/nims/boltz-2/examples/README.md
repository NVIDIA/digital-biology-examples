# Boltz-2 Python Client Examples

This directory contains comprehensive examples demonstrating the Boltz-2 Python client for biomolecular structure prediction.

## Directory Layout

```
examples/
├── 01-13           Numbered tutorial scripts (progression)
├── barnase_barstar_with_msa.py        Case study demo
├── cdk4_msa_affinity_example.py       Case study demo
├── comprehensive_multi_endpoint_demo.py   Multi-endpoint demo
├── msa_search_simple_demo.py          Minimal MSA demo
├── multi_endpoint_screening.py        Production screening demo
├── data/           YAML configs, A3M files, JSON, support files
└── notebooks/      Jupyter notebooks (tutorials + visualizations)
```

## Tutorial Scripts

| # | File | Topic |
|---|------|-------|
| 01 | `01_basic_protein_folding.py` | Simple protein structure prediction from sequence |
| 02 | `02_protein_structure_prediction_with_msa.py` | MSA integration and comparison |
| 03 | `03_protein_ligand_complex.py` | SMILES/CCD ligand binding, pocket constraints |
| 04 | `04_covalent_bonding.py` | Covalent bonds and disulfide bridges |
| 05 | `05_dna_protein_complex.py` | DNA/RNA-protein complexes |
| 06 | `06_yaml_configurations.py` | YAML config creation and parameter overrides |
| 07 | `07_advanced_parameters.py` | Diffusion parameters, quality vs speed |
| 08 | `08_affinity_prediction_simple.py` | Binding affinity (pIC50) prediction |
| 09 | `09_virtual_screening.py` | High-throughput compound screening |
| 10 | `10_msa_search_integration.py` | GPU-accelerated MSA search + prediction |
| 11 | `11_msa_search_large_protein.py` | Large protein MSA optimization |
| 12 | `12_msa_affinity_prediction.py` | MSA-guided affinity prediction |
| 13 | `13_a3m_to_multimer_csv.py` | ColabFold A3M to Boltz-2 multimer CSV |

## Notebooks

Located in `notebooks/`:

| File | Topic |
|------|-------|
| `01_multimer_prediction.ipynb` | Heterodimer/homodimer prediction |
| `02_cdk4_msa_affinity_prediction.ipynb` | CDK4-Palbociclib MSA + affinity workflow |
| `03_colabfold_a3m_to_multimer.ipynb` | ColabFold A3M multimer pairing (notebook) |
| `boltz2_demo.ipynb` | Client overview demo |
| `boltz2_comprehensive_demo.ipynb` | All-features comprehensive demo |
| `boltz2_nim_DNA_Protein_Complex_example_py3Dmol.ipynb` | DNA-protein with py3Dmol visualization |
| `boltz2_nim_protein_ligand_covalent_complex_molstar_visualization.ipynb` | Covalent complex with Molstar visualization |

## Standalone Demos

| File | Topic |
|------|-------|
| `barnase_barstar_with_msa.py` | Barnase-barstar complex with MSA for both chains |
| `cdk4_msa_affinity_example.py` | CDK4 MSA + affinity (script version of notebook 02) |
| `comprehensive_multi_endpoint_demo.py` | All features with multi-endpoint orchestration |
| `msa_search_simple_demo.py` | Minimal MSA NIM demo (search only) |
| `multi_endpoint_screening.py` | Multi-endpoint virtual screening with load balancing |

## Data Files

Located in `data/`:

| File | Used By |
|------|---------|
| `protein_ligand.yaml` | `06_yaml_configurations.py` |
| `multi_protein_complex.yaml` | `06_yaml_configurations.py` |
| `sars_cov2_mpro_nirmatrelvir.yaml` | `06_yaml_configurations.py` |
| `msa-kras-g12c_combined.a3m` | `02_protein_structure_prediction_with_msa.py` |
| `kinase_y7w_affinity.json` | `08_affinity_prediction_simple.py` |
| `cdk2_target.txt` | Reference sequence |
| `cdk4_msa_affinity/` | CDK4 workflow results |

## Quick Start

```bash
pip install -e .

# Ensure Boltz-2 NIM is running locally, or set API key
export NVIDIA_API_KEY=your_api_key_here

python examples/01_basic_protein_folding.py
```

## Example Selection Guide

| Goal | Recommended |
|------|-------------|
| Learn basics | `01`, `03`, `06` |
| Improve accuracy | `02`, `07`, `10` |
| Drug discovery | `03`, `04`, `08`, `09` |
| Virtual screening | `09`, `multi_endpoint_screening.py` |
| MSA-enhanced | `02`, `10`, `11`, `12` |
| Multimer MSA | `13`, notebook `03` |
| Production setup | `06`, `multi_endpoint_screening.py` |

## Additional Resources

- **Main Documentation**: `../README.md`
- **Guides**: `../docs/` (parameters, YAML, async, MSA search, multi-endpoint, etc.)
- **CLI Help**: `boltz2 --help`
