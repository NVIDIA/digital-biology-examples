# Development and validation

From this checkout, using Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,notebooks]"
pytest
```

Default pytest runs offline tests. The notebook unit checks use synthetic
responses; actual inference and browser validation are separate steps below.

## Run all tests against real services

```bash
export BOLTZ2_NIM_URL=http://localhost:8000
export MSA_NIM_URL=http://localhost:8001  # optional separate MSA Search NIM
pytest -o addopts="-v --tb=short --strict-markers" --junitxml=results/full-suite.xml
```

This includes 50 protein and 147 affinity stress requests. Every request must
succeed. `BOLTZ2_TEST_CONCURRENCY` defaults to 2. NVIDIA-hosted prediction tests
run when `NVIDIA_API_KEY` or `NGC_API_KEY` is set. SageMaker tests run only when
`SAGEMAKER_ENDPOINT_NAME` is set; specify `SAGEMAKER_REGION` too.

For the local subset, add `-k "not NVIDIAHosted and not SageMaker and not sagemaker"`.
The complete suite also invokes the installed console command through Bash,
checks nonzero error exits, and parses JSON, mmCIF, PDB and screening outputs.

## Execute notebooks and inspect artifacts

```bash
export BOLTZ2_SERVER_OUTPUT_DIR=/path/to/boltz2-output
python scripts/validate_notebooks.py
python scripts/validate_live_nim.py --server-output-dir "$BOLTZ2_SERVER_OUTPUT_DIR"
bash scripts/validate_cli.sh
```

Activate the virtual environment before the Bash check. Set `BOLTZ2_BIN` and
`PYTHON` to explicit executable paths if needed. Notebook execution creates a
private kernel using the current Python, saves executed copies, and validates
structure coordinates. Source notebook outputs remain cleared. All five retained
notebooks use the local endpoint. SageMaker's connection example is in the
[deployment guide](deployment.md#existing-sagemaker-endpoint); its live pytest
checks still require an explicitly configured endpoint.

Use `--notebook FILE.ipynb` to rerun one notebook. To exercise optional branches
without downloading databases:

```bash
MSA_NIM_URL=http://localhost:8001 MSA_DATABASE=pdb70_220313 \
  python scripts/validate_notebooks.py --notebook 03_cdk4_affinity.ipynb \
  --output-dir results/notebooks-msa
CDK4_MSA_PATH=/absolute/path/to/cdk4.a3m \
  python scripts/validate_notebooks.py --notebook 03_cdk4_affinity.ipynb \
  --output-dir results/notebooks-msa-file
MULTIMER_A3M_A=/absolute/path/to/barnase.a3m MULTIMER_A3M_B=/absolute/path/to/barstar.a3m \
  python scripts/validate_notebooks.py --notebook 02_protein_complexes.ipynb \
  --output-dir results/notebooks-paired
```

Use fresh output directories when comparing validation runs.

Results live under `results/` and are ignored by Git. A successful API test
establishes software behavior, not biological accuracy. MSA paired/template
searches need additional databases; a PDB70-only server does not cover them.

## Package and release

```bash
python -m build --outdir dist/testpypi-0.6.0
python -m twine check dist/testpypi-0.6.0/*
```

Install the wheel in a fresh environment and check imports, CLI and bundled data.
Validate version `0.6.0` on TestPyPI first. With TestPyPI credentials configured
outside the repository, the upload command is:

```bash
python -m twine upload --repository testpypi --non-interactive \
  dist/testpypi-0.6.0/boltz2_python_client-0.6.0-py3-none-any.whl \
  dist/testpypi-0.6.0/boltz2_python_client-0.6.0.tar.gz
```

Verify the uploaded files' SHA-256 digests against the local artifacts, then
install from TestPyPI in a clean environment and check imports and the CLI.
Publishing to production PyPI is a separate action; retain these exact artifacts
for promotion after TestPyPI validation rather than rebuilding them.

The NIM request-schema fixture records its source image digest. Regenerate it
from the pinned image when upgrading NIM. See the [validation report](refresh-review.md).
