# Multiple endpoints

`MultiEndpointClient` distributes requests among configured NIM servers. It
supports `ROUND_ROBIN`, `LEAST_LOADED`, and `RANDOM` selection, tracks endpoint
health, and tries another endpoint when a request fails.

```python
from boltz2_client import MultiEndpointClient, LoadBalanceStrategy

async with MultiEndpointClient(
    endpoints=["http://gpu1:8000", "http://gpu2:8000"],
    strategy=LoadBalanceStrategy.LEAST_LOADED,
    timeout=1200,
) as client:
    result = await client.predict_protein_structure(
        sequence="ACDEFGHIKLMNPQRSTVWY",
        diffusion_samples=2, max_parallel_samples=1,
        output_dir="results/multi",
    )
```

For synchronous use, set `is_async=False` and call methods such as
`predict_protein_structure_sync()` or `predict_sync(request, output_dir=...)`.
Unlike `Boltz2SyncClient`, this class uses explicit `_sync` method names.
All prediction wrappers forward additional NIM request and output parameters.

```bash
boltz2 --multi-endpoint --base-url http://gpu1:8000,http://gpu2:8000 \
  --load-balance-strategy least_loaded protein ACDEFGHIKLMNPQRSTVWY \
  --output-dir results/multi
```

Use an async context manager to stop background health checks when finished.
A one-server test checks dispatch and concurrency; it does not establish
multi-GPU throughput or redundancy. Hosted services do not expose the local
readiness API, so use this workflow with self-hosted NIMs.

See [async usage](async.md), [screening](virtual_screening.md), and [tests](development.md).
