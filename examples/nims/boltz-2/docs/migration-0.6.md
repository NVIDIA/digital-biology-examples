# Migrating from 0.5.2.post1

Version `0.6.0` updates the client for NIM 1.9.0. Compatibility was reviewed
against NVIDIA's documentation on 2026-09-11. Hosted and SageMaker model packages
can run different NIM versions.

| Feature | NIM | Client behavior |
|---|---|---|
| Protein, DNA/RNA, ligand, MSA, templates, affinity | Existing APIs | Public client entry points retained |
| Affinity embeddings | 1.8+ | Set `output_affinity_embedding=True` on the affinity ligand |
| Diffusion concurrency | 1.9+ | `max_parallel_samples=1..25`; omitted by default |
| Full PAE/PDE | 1.9+ | Server NPZ artifacts; JSON `pae`/`pde` stay null |
| Aggregate PDE scores | Existing APIs | Preserved in saved metadata |

Embedding flags are omitted from the wire request when false, and unset
`max_parallel_samples` is omitted. This avoids sending these new fields to older
endpoints during ordinary predictions. Unsupported enabled fields produce a
server error; the client does not silently downgrade requests.

## Validation and behavior changes

- Unknown request fields now raise validation errors. Previously Pydantic silently
  discarded misspelled parameters. Responses preserve unknown fields for forward compatibility.
- A ligand must define exactly one of CCD or SMILES. Embeddings require affinity
  on that same ligand. Duplicate ligand chemistry is rejected when affinity is enabled.
- Protein `X` is accepted. Empty sequences, nonpositive residue indices, invalid
  constraint types and out-of-range parameter assignments are rejected.
- The default request limit remains 4,096 residues per chain, 12 polymers and 20
  ligands. GPU capacity and administrator-configured NIM limits are separate.
- YAML affinity properties now enable affinity instead of being discarded. Both
  the Boltz list form and the client's legacy mapping are accepted. Missing
  referenced MSA files fail visibly rather than running without the requested MSA.
- Hosted mode selects the hosted URL when `base_url` is omitted and accepts both
  key environment variable names. Polling has a finite timeout and terminal
  HTTP errors preserve `status_code` and `response_data`.
- All scores and embeddings survive saving; `prediction_response.json` is new.
- The published 0.5.2.post1 lazy-pandas import fix is retained; use the `screening`
  extra for CSV/DataFrame helpers. This fix was absent from GitHub main.
- Python 3.10+ is required. Notebook visualization dependencies are optional.
- Multi-endpoint wrappers forward additional request and output parameters.
- Failed compound screens return a nonzero CLI exit code. Hosted readiness and
  metadata calls raise `NotImplementedError`; use prediction to check availability.
- Numbered tutorials and duplicate scripts are consolidated into the
  [example index](../examples/README.md). Five focused notebooks replace the seven
  overlapping notebooks; SageMaker's connection example moved to the
  [deployment guide](deployment.md#existing-sagemaker-endpoint).

The client remains a NIM wrapper, not a replacement for the Boltz OSS CLI.
[Supported YAML](yaml.md) is a subset; use `PredictionRequest` for all NIM fields.

## Deployment changes

NIM 1.9 uses one optimized backend. Remove old TensorRT profile hashes and
`NIM_REQUIRE_TRT`, `NIM_FAIL_ON_NO_TRT`, `NIM_BUILD_TRT_ENGINES`,
`NIM_BOLTZ_USE_TRT_ENGINES`, `NIM_BOLTZ_ENABLE_DIFFUSION_TF32`,
`NIM_BOLTZ_STRUCTURE_OPTIMIZED_BACKEND` and `NIM_BOLTZ_AFFINITY_OPTIMIZED_BACKEND`.
Leave `NIM_MODEL_PROFILE` unset unless explicitly selecting a supported profile.
Mount `/opt/nim/output` separately from `/opt/nim/.cache` for matrix artifacts.

References: [release notes](https://docs.nvidia.com/nim/bionemo/boltz2/latest/release-notes.html),
[inference API](https://docs.nvidia.com/nim/bionemo/boltz2/latest/inference.html),
[configuration](https://docs.nvidia.com/nim/bionemo/boltz2/latest/configure.html).
