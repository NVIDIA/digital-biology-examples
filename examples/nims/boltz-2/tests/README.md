# Tests

## Running tests

```bash
pip install -e ".[dev]"

# Mock tests only (default, no real endpoints needed)
pytest

# Include live-endpoint tests (requires running NIM / SageMaker / NVIDIA hosted)
pytest -m real_endpoint

# Performance / concurrency tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

## Markers (defined in `pytest.ini`)

| Marker | Purpose |
|--------|---------|
| `unit` | Fast, no external dependencies |
| `integration` | Medium speed, may touch external deps |
| `slow` | Real API calls / long-running operations |
| `real_endpoint` | Requires a live Boltz-2 NIM (or SageMaker / NVIDIA hosted) |
| `performance` | Load / concurrency benchmarks |
| `api` | Python API tests |
| `cli` | CLI tests |

## Test files

| File | Scope |
|------|-------|
| `conftest.py` | Shared constants, fixtures, pytest config |
| `test_basic.py` | Client init, model imports |
| `test_multi_endpoint_functionality.py` | Per-method API coverage (protein, ligand, covalent, DNA, YAML, VS, health, metadata) through single + multi-endpoint mocks |
| `test_integration_scenarios.py` | Scenario-level workflows (e2e prediction, VS, LB strategies, failover, health monitoring, error recovery) |
| `test_cli_multi_endpoint.py` | CLI command parsing and option validation |
| `test_msa_search.py` | MSA search client, format converter, Boltz integration |
| `test_a3m_to_csv_converter.py` | A3M-to-multimer-CSV conversion logic |
| `test_examples_syntax.py` | Syntax + import validation for example scripts |
| `test_live_endpoints.py` | Live tests: NIM, SageMaker, NVIDIA hosted, multi-endpoint, perf, CLI smoke |
| `test_comprehensive_stress.py` | High-volume concurrent prediction stress tests |

## Environment variables for live tests

| Variable | Default | Description |
|----------|---------|-------------|
| `BOLTZ2_NIM_URL` | `http://localhost:8000` | Self-hosted NIM endpoint |
| `SAGEMAKER_ENDPOINT_NAME` | *(skip if unset)* | AWS SageMaker endpoint name |
| `SAGEMAKER_REGION` | `us-east-1` | AWS region |
| `NVIDIA_API_KEY` | *(skip if unset)* | NVIDIA hosted API key |
| `NVIDIA_HOSTED_URL` | `https://health.api.nvidia.com` | NVIDIA hosted base URL |

## Coverage

```bash
pytest --cov=boltz2_client --cov-report=term-missing
```
