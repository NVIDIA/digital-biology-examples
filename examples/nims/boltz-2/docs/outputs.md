# Prediction outputs

`PredictionResponse` retains structures, per-sample scores, affinity results,
embeddings, metrics, and unknown response fields. Score arrays should be read in
the order returned by the service; do not assume the first sample is best.
`save_prediction_outputs(response, output_dir)` saves all structures and a scores
JSON including affinities. `client.predict(..., output_dir=...)` also saves a
complete `prediction_response.json`.

## Full PAE and PDE in NIM 1.9

Enable `write_full_pae` / `write_full_pde` in `PredictionRequest` and mount the
server output directory (see [deployment](deployment.md)). The JSON fields are
null, including when these flags are enabled. Files are created under:

```
NIM_OUTPUT_PATH/prediction_*/pae/pae_*_model_*.npz
NIM_OUTPUT_PATH/prediction_*/pde/pde_*_model_*.npz
```

The 1.9.0 container schema also supports `complex_id`, which is not yet listed
in the web inference reference. Set a unique value (1–64 letters, digits, hyphens
or underscores) to write artifacts under `$NIM_OUTPUT_PATH/<complex_id>/` instead.
Use a new ID per prediction to avoid collisions. The client has no matrix-download
API; access the mounted directory directly. When omitting `complex_id`, identify
the matching timestamp directory from deployment records rather than selecting
the newest directory blindly.

```python
import numpy as np

# Replace with the exact artifact path from your prediction directory.
with np.load("/path/to/pae_prediction_model_0.npz", allow_pickle=False) as archive:
    print(archive.files)
    for key in archive.files:
        matrix = archive[key]
        print(key, matrix.shape, matrix.dtype)
```

Matrices use Ångström units and have quadratic storage cost in the token count,
per sample. The service writes uncompressed NPZ archives. Lower error generally
means higher confidence, not experimentally verified correctness. Aggregate
`complex_pde_scores` and `complex_ipde_scores` remain available in JSON without
these flags. Aggregate PAE is not a separate NIM JSON field.

The existing `save_pae_matrix`, `save_pde_matrix`, and `get_pae_summary` functions
remain available for arrays obtained from legacy responses or other sources.
They cannot retrieve files from a NIM server.

## Affinity embeddings

Set both `predict_affinity=True` and `output_affinity_embedding=True` on one
ligand. Its affinity response includes `affinity_embedding`,
`model_1_affinity_embedding`, and `model_2_affinity_embedding`: two-dimensional
arrays with 384 components per vector, or null. Embeddings are numerical features,
not probabilities. Preserve all returned rows and ensemble outputs.

Source: [NVIDIA inference API](https://docs.nvidia.com/nim/bionemo/boltz2/latest/inference.html).
