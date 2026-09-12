# Boltz-2 Python Client

Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.

[![PyPI](https://img.shields.io/pypi/v/boltz2-python-client)](https://pypi.org/project/boltz2-python-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Python and command-line interfaces for NVIDIA Boltz-2 NIM: protein, DNA/RNA,
ligand and covalent complexes, binding affinity, MSA integration, templates,
and multi-endpoint screening.

Version **0.6.0** targets **NIM 1.9.0**. Releases are validated on
[TestPyPI](https://test.pypi.org/project/boltz2-python-client/0.6.0/)
before production publication. Select the matching index when installing.
See [migration and compatibility](docs/migration-0.6.md).

The source archive (`.tar.gz`) under the release page's **Download files** includes
the current guides, scripts and notebooks. Relative links in this README refer
to files in that extracted archive or a matching repository checkout.

## Install

Python 3.10 or newer:

```bash
# PyPI, after production publication
python -m pip install boltz2-python-client==0.6.0

# TestPyPI release and dependencies from PyPI
python -m pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ boltz2-python-client==0.6.0

# From this checkout or the extracted source archive
python -m pip install -e '.[dev,notebooks]'
```

Optional extras: `notebooks` (Jupyter and visualization), `sagemaker` (boto3),
`analysis` (NumPy and structure conversion), and `screening` (pandas for CSV and
DataFrame helpers). The Python client itself needs no GPU;
a running NIM server performs inference.

## Quick start

Run against a ready local server. This sequence is an input-format example;
confidence scores do not establish a biological interaction.

```python
from pathlib import Path
from boltz2_client import Boltz2SyncClient

client = Boltz2SyncClient(base_url="http://localhost:8000", timeout=600)
result = client.predict_protein_structure(
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    output_dir=Path("results/protein"),
)
print(result.confidence_scores)
```

For notebooks and asynchronous programs, use `Boltz2Client` and `await`:

```python
from boltz2_client import Boltz2Client, Ligand, Polymer, PredictionRequest

client = Boltz2Client(timeout=600)
request = PredictionRequest(
    polymers=[Polymer(id="A", molecule_type="protein", sequence="MTEYKLVVVGACGVGKSALTIQLIQNHFVDEYDPT")],
    ligands=[Ligand(id="L1", smiles="CC(=O)Oc1ccccc1C(=O)O",
                    predict_affinity=True, output_affinity_embedding=True)],
    diffusion_samples=2,
    max_parallel_samples=1,  # NIM 1.9+: lower peak GPU memory
)
result = await client.predict(request, output_dir="results/complex")
print(result.affinities["L1"].affinity_pic50)
print(result.affinities["L1"].affinity_embedding)
```

The second example demonstrates request syntax using a short protein fragment
and aspirin; it is not a validated binding pair. Use full, appropriate target
sequences and assess predictions against experimental evidence.

## Endpoints

| Deployment | Configuration | Prediction path |
|---|---|---|
| Local/self-hosted | `Boltz2Client(base_url="http://localhost:8000")` | `/biology/mit/boltz2/predict` |
| NVIDIA hosted | `Boltz2Client(endpoint_type="nvidia_hosted")` | `/v1/biology/mit/boltz2/predict` |
| SageMaker | `Boltz2Client(endpoint_type="sagemaker", sagemaker_endpoint_name="my-endpoint")` | boto3 `invoke_endpoint` |

For hosted inference, supply the key through `NVIDIA_API_KEY` or `NGC_API_KEY`
in the process environment (or `api_key` in Python). The default hosted base
URL is `https://health.api.nvidia.com`. Local inference sends no authorization
header. Hosted deployments may lag the container release; enable version-specific
options only when that endpoint supports them.

SageMaker requires the `sagemaker` extra and configured AWS credentials/region.
See the [SageMaker connection example](docs/deployment.md#existing-sagemaker-endpoint).
Use asynchronous clients in Jupyter; the synchronous wrapper uses `asyncio.run()`.

## CLI

```bash
boltz2 health
boltz2 protein ACDEFGHIKLMNPQRSTVWY --output-dir results/protein
boltz2 protein ACDEFGHIKLMNPQRSTVWY --diffusion-samples 2 --max-parallel-samples 1
boltz2 ligand ACDEFGHIKLMNPQRSTVWY --smiles CC --predict-affinity --output-affinity-embedding
boltz2 advanced --config-file examples/data/nim_1_9_request.json --output-dir results/advanced
boltz2 --endpoint-type nvidia_hosted protein ACDEFGHIKLMNPQRSTVWY
boltz2 --multi-endpoint --base-url http://gpu1:8000,http://gpu2:8000 protein ACDEFGHIKLMNPQRSTVWY
```

These short sequences/ligands illustrate syntax. `boltz2 --help` lists all
commands, including covalent constraints, YAML, MSA conversion and screening.

## Results and matrices

`predict()` saves every structure as `structure_0.cif`, `structure_1.cif`, etc.,
plus `prediction_response.json` (complete response), `prediction_metadata.json`
(scores, affinities, embeddings and runtime metrics), and `affinities.json` when
present. Use `save_structures=False` or CLI `--no-save` to suppress client output.
Use separate output directories for separate predictions to avoid overwriting files.

**NIM 1.9 does not return full PAE/PDE matrices in JSON.** `write_full_pae=True`
and `write_full_pde=True` create NPZ files on the server under
`$NIM_OUTPUT_PATH/prediction_*/pae/` and `.../pde/`. `result.pae` and `result.pde`
remain `None`. Mount the server output directory to retrieve these artifacts.
Aggregate `complex_pde_scores` and `complex_ipde_scores` remain in the response.
See [outputs](docs/outputs.md) for loading matrices and retaining results.

## Deploy a local server

Follow [local deployment](docs/deployment.md), including GPU/driver prerequisites,
NGC login, cache and output mounts. The pinned image is
`nvcr.io/nim/mit/boltz2:1.9.0`. The deployment script checks GPU access before
starting a container:

```bash
# Set NGC_API_KEY (or NVIDIA_API_KEY) in the environment first.
export LOCAL_NIM_CACHE="$HOME/.cache/nim"
export LOCAL_NIM_OUTPUT="$HOME/boltz2-output"
bash scripts/start_local_nim.sh
```

## Guides and examples

Start with the [protein prediction notebook](examples/notebooks/01_protein_prediction.ipynb)
and [example index](examples/README.md). Guides:

- [Parameters](docs/parameters.md), [migration](docs/migration-0.6.md), [outputs](docs/outputs.md)
- [Affinity](docs/affinity_prediction.md), [covalent complexes](docs/covalent_complex.md)
- [MSA search](docs/msa_search.md), [A3M multimer pairing](docs/a3m_to_multimer_msa.md)
- [YAML subset](docs/yaml.md), [async usage](docs/async.md)
- [Multiple endpoints](docs/multi_endpoint.md), [virtual screening](docs/virtual_screening.md)
- [Validation and release procedure](docs/development.md), [changelog](CHANGELOG.md)

## License

[MIT](LICENSE). Third-party assets retain their [licenses](licenses/README.md).
NVIDIA NIM container and model terms are separate from the Python client license.
