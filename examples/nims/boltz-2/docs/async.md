# Async and synchronous Python

Use `Boltz2Client` with `await` in Jupyter or an async application. Use
`Boltz2SyncClient` in ordinary Python scripts. Both expose the same method names;
the synchronous wrapper does not add a `_sync` suffix.

```python
import asyncio
from boltz2_client import Boltz2Client

async def main():
    client = Boltz2Client(base_url="http://localhost:8000", timeout=1200)
    result = await client.predict_protein_structure(
        sequence="ACDEFGHIKLMNPQRSTVWY", output_dir="results/protein",
    )
    print(result.confidence_scores)

asyncio.run(main())  # In Jupyter, use: await main()
```

For a bounded batch, limit concurrent requests with `asyncio.Semaphore` and
collect the results with `asyncio.gather`. The server's GPU memory and request
queue determine useful concurrency. Save each prediction to its own directory.
`max_parallel_samples` controls samples within one prediction, not concurrent
client requests.

```python
from boltz2_client import Boltz2SyncClient
client = Boltz2SyncClient(timeout=1200)
result = client.predict_protein_structure(sequence="ACDEFGHIKLMNPQRSTVWY")
```

Synchronous methods use `asyncio.run()` and cannot run inside an active Jupyter
event loop. `VirtualScreening.screen()` is also synchronous; from an async
application, call it with `await asyncio.to_thread(screener.screen, ...)`.

See [multiple endpoints](multi_endpoint.md) and [outputs](outputs.md).
