# MSA Search integration

MSA Search is a separate NIM. Boltz2 consumes supplied alignments; omitting an
MSA does not start a search. Set `MSA_NIM_URL` to a running MSA Search server.
The client targets the local MSA Search 2.3 API.

```python
import os
from boltz2_client import Boltz2Client

client = Boltz2Client(timeout=1200)
client.configure_msa_search(msa_endpoint_url=os.environ["MSA_NIM_URL"])
result = await client.predict_with_msa_search(
    sequence="ACDEFGHIKLMNPQRSTVWY",
    databases=["pdb70_220313"],
    max_msa_sequences=500,
    output_dir="results/msa",
)
```

Select databases installed on that server. PDB70 is useful for a small API test;
UniRef30 provides taxonomy for paired searches. With the GPU server enabled,
`max_msa_sequences` must match `NIM_GLOBAL_MAX_MSA_DEPTH` (default 500).
Database names are case-insensitive, but output keys preserve the requested case.

```bash
boltz2 msa-search "$SEQUENCE" --endpoint "$MSA_NIM_URL" \
  -d pdb70_220313 --output results/msa
boltz2 msa-predict "$SEQUENCE" --endpoint "$MSA_NIM_URL" \
  -d pdb70_220313 --output-dir results/msa_prediction
boltz2 msa-ligand "$SEQUENCE" --endpoint "$MSA_NIM_URL" \
  -d pdb70_220313 --smiles CCO --predict-affinity --output-dir results/msa_ligand
```

For search-only use, `MSASearchClient` exposes `search`, `paired_search`,
`template_search`, `get_databases`, and `health_check`. Paired searches need a
server database with taxonomy; template searches additionally need the structure
archive. Those capabilities cannot be validated using a PDB70-only deployment.
Use `MSAFormatConverter.extract_alignment(response, "a3m")` to obtain alignment
text. Preserve the query sequence and database provenance when saving it.

Precomputed A3M and CSV inputs are supported directly; see
[A3M pairing](a3m_to_multimer_msa.md). FASTA/Stockholm records are schema-valid but
are discarded by Boltz2 1.9 input preparation, so use A3M or CSV for inference.

[NVIDIA MSA API reference](https://docs.nvidia.com/nim/bionemo/msa-search/latest/api-reference.html).
