# Boltz-2 Python Client

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.

[![PyPI version](https://badge.fury.io/py/boltz2-python-client.svg)](https://badge.fury.io/py/boltz2-python-client)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python client for NVIDIA's Boltz-2 biomolecular structure prediction service. This package provides both synchronous and asynchronous interfaces, a rich CLI, and built-in 3D visualization capabilities.

## Features

- **Boltz2 NIM v1.6 Support** — Compatible with the latest NVIDIA Boltz2 NIM
- **Full API Coverage** — Protein folding, protein-ligand, covalent, DNA-protein, YAML configs
- **Async & Sync Clients** — Choose your preferred programming style
- **Rich CLI Interface** — Beautiful command-line tools with progress bars
- **Flexible Endpoints** — Local deployments, NVIDIA hosted API, or AWS SageMaker
- **Affinity Prediction** — Predict binding affinity (pIC50) for protein-ligand complexes
- **Virtual Screening** — High-level API for drug discovery campaigns
- **MSA Search Integration** — GPU-accelerated MSA generation with NVIDIA MSA Search NIM
- **A3M to Multimer MSA** — Convert ColabFold A3M files to paired multimer format
- **Multi-Endpoint Load Balancing** — Distribute predictions across multiple NIMs
- **PAE/PDE Matrix Output** — Full Predicted Aligned Error and Distance Error matrices
- **Structural Templates** — Template-guided structure prediction

## Installation

```bash
# From PyPI
pip install boltz2-python-client

# With SageMaker support
pip install "boltz2-python-client[sagemaker]"

# From source
git clone https://github.com/NVIDIA/digital-biology-examples.git
cd digital-biology-examples/examples/nims/boltz-2
pip install -e ".[dev]"
```

## Quick Start

### Python API

```python
import asyncio
from boltz2_client import Boltz2Client

async def main():
    client = Boltz2Client(base_url="http://localhost:8000")

    # Simple protein prediction
    result = await client.predict_protein_structure(
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    )
    print(f"Confidence: {result.confidence_scores[0]:.3f}")

    # MSA-guided prediction
    result = await client.predict_protein_structure(
        sequence="MKTVRQERLK...",
        msa_files=[("alignment.a3m", "a3m")],
        recycling_steps=3,
        sampling_steps=200,
    )

asyncio.run(main())
```

### Synchronous API

```python
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(base_url="http://localhost:8000")
result = client.predict_protein_structure(sequence="MKTVRQ...")
```

### CLI

```bash
# Health check
boltz2 health

# Protein structure
boltz2 protein "SEQUENCE" --recycling-steps 3 --sampling-steps 200

# Protein-ligand with affinity
boltz2 ligand "SEQUENCE" --smiles "CC(=O)OC1=CC=CC=C1C(=O)O" --predict-affinity

# Covalent complex
boltz2 covalent "SEQUENCE" --ccd U4U --bond A:11:SG:L:C22

# Virtual screening
boltz2 screen "SEQUENCE" compounds.csv -o results/

# Multimer from A3M files
boltz2 multimer-msa chain_A.a3m chain_B.a3m -c A,B -o complex.cif --save-all

# Multi-endpoint load balancing
boltz2 --multi-endpoint --base-url "http://gpu1:8000,http://gpu2:8000" protein "SEQUENCE"
```

## Configuration

### Local Endpoint (Default)

```python
client = Boltz2Client(base_url="http://localhost:8000")
```

### NVIDIA Hosted Endpoint

```python
client = Boltz2Client(
    base_url="https://health.api.nvidia.com",
    api_key="your_api_key",  # or set NVIDIA_API_KEY env var
    endpoint_type="nvidia_hosted",
)
```

### AWS SageMaker Endpoint

```python
from boltz2_client import Boltz2SyncClient

# Requires: pip install "boltz2-python-client[sagemaker]"
# AWS credentials must be configured (e.g. via AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
# environment variables, ~/.aws/credentials, or an IAM role)

client = Boltz2SyncClient(
    endpoint_type="sagemaker",
    sagemaker_endpoint_name="my-boltz2-endpoint",
    sagemaker_region="us-east-1",
)

# Health check (calls describe_endpoint under the hood)
health = client.health_check()
print(f"Endpoint status: {health.status}")

# Predict protein structure — same API as local/hosted endpoints
result = client.predict_protein_structure(
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    recycling_steps=3,
    sampling_steps=200,
)
print(f"Confidence: {result.confidence_scores[0]:.3f}")

# Protein-ligand with affinity prediction
result = client.predict_protein_ligand_complex(
    protein_sequence="MKTVRQERLK...",
    ligand_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
    predict_affinity=True,
)
```

```bash
# CLI — all commands work with SageMaker by adding the endpoint flags
boltz2 --endpoint-type sagemaker --sagemaker-endpoint-name my-boltz2-endpoint health
boltz2 --endpoint-type sagemaker --sagemaker-endpoint-name my-boltz2-endpoint \
    protein "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
```

## Supported Prediction Types

| Type | CLI Command | Python Method |
|------|-------------|---------------|
| Protein folding | `protein` | `predict_protein_structure()` |
| Protein-ligand | `ligand` | `predict_protein_ligand_complex()` |
| Covalent complex | `covalent` | `predict_covalent_complex()` |
| DNA-protein | `dna-protein` | `predict_dna_protein_complex()` |
| Advanced | `advanced` | `predict_with_advanced_parameters()` |
| YAML config | `yaml` | `predict_from_yaml_config()` |
| Virtual screening | `screen` | `VirtualScreening.screen()` |
| MSA search | `msa-search` | `client.search_msa()` |
| Multimer MSA | `multimer-msa` | A3M conversion + `predict()` |

## Boltz-2 NIM v1.6 Parameter Limits

| Parameter | Range |
|-----------|-------|
| `recycling_steps` | 1–10 |
| `diffusion_samples` | 1–25 |
| `sampling_steps` | 10–1000 |
| `polymers` | up to 12 |
| `ligands` | up to 20 |

## Local Deployment

```bash
export NGC_API_KEY=<your_key>
export LOCAL_NIM_CACHE=~/.cache/nim
mkdir -p $LOCAL_NIM_CACHE && chmod -R 777 $LOCAL_NIM_CACHE

docker run -it --runtime=nvidia --shm-size=16G \
    -p 8000:8000 -e NGC_API_KEY \
    -v "$LOCAL_NIM_CACHE":/opt/nim/.cache \
    nvcr.io/nim/mit/boltz2:1.6.0
```

## Examples

The [`examples/`](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2/examples) directory contains tutorial scripts, notebooks, and standalone demos:

**Tutorial Scripts** ([`examples/`](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2/examples)):

| File | Description |
|------|-------------|
| `01_basic_protein_folding.py` | Simple protein structure prediction |
| `02_protein_structure_prediction_with_msa.py` | MSA-guided predictions |
| `03_protein_ligand_complex.py` | Protein-ligand complexes |
| `04_covalent_bonding.py` | Covalent bond constraints |
| `05_dna_protein_complex.py` | DNA-protein interactions |
| `06_yaml_configurations.py` | YAML config files |
| `07_advanced_parameters.py` | Advanced API parameters |
| `08_affinity_prediction_simple.py` | Binding affinity prediction |
| `09_virtual_screening.py` | Virtual screening |
| `10_msa_search_integration.py` | GPU-accelerated MSA search + prediction |
| `11_msa_search_large_protein.py` | Large protein MSA optimization |
| `12_msa_affinity_prediction.py` | MSA-guided affinity prediction |
| `13_a3m_to_multimer_csv.py` | A3M to multimer MSA conversion |

**Notebooks** ([`examples/notebooks/`](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2/examples/notebooks)):

| File | Description |
|------|-------------|
| `01_multimer_prediction.ipynb` | Heterodimer/homodimer prediction |
| `02_cdk4_msa_affinity_prediction.ipynb` | CDK4-Palbociclib MSA + affinity workflow |
| `03_colabfold_a3m_to_multimer.ipynb` | ColabFold A3M multimer pairing |

## Documentation

| Guide | Description |
|-------|-------------|
| [Parameters](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/parameters.md) | Detailed parameter documentation |
| [YAML Configuration](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/yaml.md) | Working with YAML config files |
| [Affinity Prediction](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/affinity_prediction.md) | Binding affinity (pIC50) guide |
| [Virtual Screening](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/virtual_screening.md) | Drug discovery campaigns |
| [MSA Search](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/msa_search.md) | GPU-accelerated MSA generation |
| [A3M Multimer MSA](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/a3m_to_multimer_msa.md) | ColabFold A3M conversion |
| [Multi-Endpoint](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/multi_endpoint.md) | Load balancing across NIMs |
| [Covalent Complex](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/covalent_complex.md) | Covalent bond predictions |
| [Async Guide](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/docs/async.md) | Async programming best practices |
| [Changelog](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/CHANGELOG.md) | Release history |

## Development

```bash
pip install -e ".[dev]"
pytest tests/                                           # mock tests only
pytest tests/ -m real_endpoint                          # live endpoint tests
BOLTZ2_NIM_URL=http://your-nim:8000 pytest tests/ -v   # all tests
```

## Requirements

- **Python** 3.8+
- **Core**: httpx, pydantic, rich, click, PyYAML, aiofiles, aiohttp, py3Dmol
- **Optional**: boto3 (SageMaker), pandas (dev)

## License

MIT License — see [LICENSE](https://github.com/NVIDIA/digital-biology-examples/blob/main/examples/nims/boltz-2/LICENSE). Third-party licenses in [licenses/](https://github.com/NVIDIA/digital-biology-examples/tree/main/examples/nims/boltz-2/licenses/).

## Links

- [NVIDIA BioNeMo](https://www.nvidia.com/en-us/clara/bionemo/)
- [Boltz-2 Paper](https://cdn.prod.website-files.com/68404fd075dba49e58331ad9/6842ee1285b9af247ac5a122_boltz2.pdf)
- [TestPyPI](https://test.pypi.org/project/boltz2-python-client/)

---

## Disclaimer

This software is provided as-is without warranties of any kind. No guarantees are made regarding the accuracy, reliability, or fitness for any particular purpose. The underlying models and APIs are experimental and subject to change without notice. Users are responsible for validating all results and assessing suitability for their specific use cases.

---

**Made with care for the computational biology community**
