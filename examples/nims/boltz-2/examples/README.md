# Examples

Install this checkout with `pip install -e ".[notebooks,screening]"` and set
`BOLTZ2_NIM_URL` to a ready NIM 1.9.0 endpoint (default `http://localhost:8000`).
Run Python scripts from the client directory. Outputs go under `results/examples`.

| Script | Run | Purpose |
|---|---|---|
| [predict.py](predict.py) | `python examples/predict.py` | Protein prediction |
| [predict_yaml.py](predict_yaml.py) | `python examples/predict_yaml.py` | YAML request |
| [screen.py](screen.py) | `python examples/screen.py` | Two-compound affinity screen |
| [msa_search.py](msa_search.py) | `MSA_NIM_URL=http://localhost:8001 python examples/msa_search.py` | MSA search and prediction |
| [paired_msa.py](paired_msa.py) | `python examples/paired_msa.py chain_A.a3m chain_B.a3m` | Precomputed paired alignments |
| [nim_1_9.py](nim_1_9.py) | `python examples/nim_1_9.py` | Sampling, embeddings and matrix artifacts |
| [multi_endpoint.py](multi_endpoint.py) | `python examples/multi_endpoint.py` | Endpoint dispatch |

The small script inputs demonstrate API use, not experimental accuracy.
MSA Search is separate from Boltz2; select an installed database with `MSA_DATABASE`.

## Notebooks

From the repository root, install `python -m pip install -e ".[notebooks]"`, then
run `jupyter lab examples/notebooks` in that environment. Run each notebook's
cells in order. All five notebooks use the async Python API, show the connected
NIM version, and target **NIM 1.9.0 / client 0.6.0**. Outputs go under
`notebook_outputs` relative to the kernel directory; rerunning replaces files
in the same output folder. The inline py3Dmol viewers require JavaScript/CDN access.

| Notebook | Purpose |
|---|---|
| [01 · Protein prediction](notebooks/01_protein_prediction.ipynb) | Two samples, structural template and optional PAE/PDE files |
| [02 · Protein complexes](notebooks/02_protein_complexes.ipynb) | Barnase–barstar, optional precomputed A3M pairing, two-copy input |
| [03 · CDK4 affinity](notebooks/03_cdk4_affinity.ipynb) | Palbociclib, three embeddings, optional saved MSA or existing MSA service |
| [04 · Protein–DNA](notebooks/04_protein_dna_complex.ipynb) | Two protein chains and reverse-complementary DNA strands |
| [05 · Covalent ligand](notebooks/05_covalent_ligand.ipynb) | KRAS G12C–U4U bond constraint and inline viewer |

Optional settings, supplied before launching Jupyter:

| Setting | Used by |
|---|---|
| `BOLTZ2_NIM_URL` | All notebooks; defaults to `http://localhost:8000` |
| `BOLTZ2_SERVER_OUTPUT_DIR` | Notebook 01: accessible host directory mounted at `/opt/nim/output` |
| `MULTIMER_A3M_A`, `MULTIMER_A3M_B` | Notebook 02: both per-chain A3M files, matching the configured sequences |
| `CDK4_MSA_PATH` | Notebook 03: existing CDK4 A3M file; takes precedence over search |
| `MSA_NIM_URL`, `MSA_DATABASE` | Notebook 03: existing MSA Search NIM 2.3.0; default database `pdb70_220313` |

No MSA service or database download is required for the default notebook flows.
For SageMaker, use the [connection example](../docs/deployment.md#existing-sagemaker-endpoint).

See [validation](../docs/development.md) for actual notebook and Bash CLI checks,
and [outputs](../docs/outputs.md) for saved structures and PAE/PDE files.
