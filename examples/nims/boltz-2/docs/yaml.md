# YAML configuration subset

The client supports a subset of the Boltz YAML format: protein sequences with
optional MSA paths, SMILES ligands, and affinity properties. It does not implement
the complete OSS Boltz configuration language. For DNA/RNA, CCD ligands, templates,
modifications and constraints, use `PredictionRequest` or `boltz2 advanced` with
NIM JSON. Unsupported YAML fields are rejected rather than silently ignored.

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: ACDEFGHIKLMNPQRSTVWY
      msa: empty
  - ligand:
      id: LIG
      smiles: CC
properties:
  - affinity:
      binder: LIG
```

This is a syntax example, not a biologically validated target/ligand pair.
The legacy `properties: {affinity: {binder: LIG}}` mapping also works.
The binder must identify exactly one ligand. Each sequence entry must define
exactly one protein or ligand, and at least one protein is needed for NIM.

```python
from boltz2_client import Boltz2Client

client = Boltz2Client(timeout=600)
result = await client.predict_from_yaml_file(
    "complex.yaml", sampling_steps=100,
    max_parallel_samples=1, output_dir="results/yaml",
)
```

MSA paths are resolved relative to the YAML file, or `msa_dir` when supplied.
Use `.a3m` or `.csv` files for NIM-consumed alignments. `msa: empty` omits MSA;
it does not trigger an external search. A referenced file that does not exist
raises an error. `YAMLConfig.to_prediction_request()` converts molecular entries
and affinity properties only; the client methods load referenced MSA files.

```bash
boltz2 yaml complex.yaml --output-dir results/yaml
```

To create a configuration in Python, use `client.create_yaml_config()` and
`client.save_yaml_config()`. Unknown keys and conflicting sequence entries raise
Pydantic validation errors. See [migration](migration-0.6.md) for fixes relative
to 0.5.2.post1.
