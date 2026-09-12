# Virtual screening

`VirtualScreening` predicts a protein complex for each compound and summarizes
confidence and optional affinity. Install `pip install -e ".[screening]"` for
CSV loading and DataFrame helpers.

```python
from boltz2_client import Boltz2SyncClient, VirtualScreening

screener = VirtualScreening(client=Boltz2SyncClient(timeout=1200), max_workers=2)
result = screener.screen(
    target_sequence="ACDEFGHIKLMNPQRSTVWY",
    compound_library=[{"name": "ethanol", "smiles": "CCO"}],
    predict_affinity=True,
)
assert not result.failed_results
print(result.get_top_hits(n=5))
result.save_results("results/screening")
```

This short input checks API usage. Use appropriate targets and compounds for
scientific work; predicted scores need independent evaluation.

A CSV library needs `name` and `smiles` columns. JSON libraries and
`CompoundLibrary` objects are also supported. Every compound result records
success or an error; inspect failures before ranking the successful subset.

```bash
boltz2 screen "$SEQUENCE" compounds.csv --max-workers 2 \
  --output-dir results/screening
```

Outputs include `screening_results.csv`, `screening_metadata.json`, and saved
structures. `--no-affinity` runs structure-only screening. Pocket residues are
1-based and must exist in the protein. More workers may increase queueing rather
than throughput; size concurrency for the actual server.

`screen()` is synchronous. In Jupyter, call it through `asyncio.to_thread`.
For multiple servers, pass a [MultiEndpointClient](multi_endpoint.md).
