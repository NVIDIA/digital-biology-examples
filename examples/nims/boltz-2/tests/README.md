# Tests

```bash
pip install -e ".[dev]"
pytest                                   # offline tests
pytest -m real_endpoint                  # live endpoint tests
pytest -m performance                    # concurrency and stress tests
pytest -o addopts="-v --tb=short"          # complete suite
```

| Coverage | Location |
|---|---|
| Models, request serialization, YAML, HTTP errors, saved outputs | `test_nim_19.py` |
| Client methods, endpoint dispatch/recovery, CLI parsing | `test_basic.py`, `test_*endpoint*.py`, `test_integration_scenarios.py` |
| MSA conversion and service adapters | `test_a3m_to_csv_converter.py`, `test_msa_search.py` |
| Notebook format and synthetic execution | `test_notebooks.py` |
| Actual async/sync Python methods and Bash CLI | `test_live_workflows.py` |
| Real local/hosted/SageMaker endpoints | `test_live_endpoints.py` |
| 50 protein and 147 affinity predictions, with assertions | `test_comprehensive_stress.py` |

`BOLTZ2_NIM_URL` defaults to localhost:8000. `MSA_NIM_URL` enables the separate MSA
CLI checks. Hosted tests use `NVIDIA_API_KEY` or `NGC_API_KEY`. SageMaker tests
require `SAGEMAKER_ENDPOINT_NAME` and its region; missing endpoints are skipped.

For actual notebook execution, output inspection and package checks, see
[development](../docs/development.md). [Recorded results](../docs/refresh-review.md)
distinguish verified behavior, service failures and skipped checks.
