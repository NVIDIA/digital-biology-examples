# Affinity prediction

Enable `predict_affinity=True` on exactly one ligand, specified by SMILES or CCD.
Results are keyed by ligand ID under `result.affinities`. They are computational
predictions, not experimentally measured binding or inhibitory concentrations.

```python
from pathlib import Path
from boltz2_client import Boltz2Client

# Supply the complete target sequence as a plain-text file.
sequence = Path("target_sequence.txt").read_text().strip()
client = Boltz2Client(timeout=600)
result = await client.predict_protein_ligand_complex(
    protein_sequence=sequence,
    ligand_smiles="CC(=O)Oc1ccccc1C(=O)O",
    ligand_id="LIG",
    predict_affinity=True,
    output_affinity_embedding=True,  # NIM 1.8+
    diffusion_samples_affinity=1,
    output_dir="results/affinity",
)
affinity = result.affinities["LIG"]
print(affinity.affinity_pic50)
print(affinity.affinity_probability_binary)
```

The ligand above is aspirin; replace it with a molecule appropriate for your target.
For a complete worked pair, use the [CDK4 notebook](../examples/notebooks/03_cdk4_affinity.ipynb).

| Output | Interpretation |
|---|---|
| `affinity_pic50` | Predicted pIC50-like values; higher implies greater predicted affinity |
| `affinity_pred_value` | Model affinity on a log concentration scale; retain the raw values |
| `affinity_probability_binary` | Predicted binder likelihood, between 0 and 1 |
| `model_1_*`, `model_2_*` | Per-ensemble-model outputs |
| `affinity_embedding` | Optional 384-dimensional vectors; not an affinity score |
| `model_1_affinity_embedding`, `model_2_affinity_embedding` | Optional ensemble embeddings |

All numerical outputs are arrays. Preserve all returned entries rather than
assuming the first row is the best or an experimental consensus. Binding
probability and affinity strength answer different questions; do not label a
high binding probability as strong binding.

An IC50-like estimate in nM can be calculated from a returned pIC50 with
`10 ** (9 - pic50)`. Report it as a prediction. The model's training data include
mixed assay types, so these estimates should not be interpreted as a specific
assay measurement without calibration.

Affinity uses `sampling_steps_affinity` (10–1000, default 200),
`diffusion_samples_affinity` (1–10, default 5), and optional
`affinity_mw_correction` (default false). More samples cost additional compute.
Do not repeat the affinity ligand's CCD/SMILES elsewhere in the same request.

Embedding outputs require both flags on the same ligand. The client retains them
in `prediction_response.json`, metadata, and `affinities.json`. See [outputs](outputs.md).

Sources: [NVIDIA inference API](https://docs.nvidia.com/nim/bionemo/boltz2/latest/inference.html),
[NVIDIA model card](https://docs.api.nvidia.com/nim/reference/mit-boltz2).
