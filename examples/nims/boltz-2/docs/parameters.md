# NIM 1.9 request parameters

Use `PredictionRequest` for the complete NIM request. Unknown keys are errors.
All convenience prediction methods accept additional top-level request parameters
through keyword arguments. `save_structures`, `output_dir`, and `progress_callback`
are client options and are not sent to NIM.

| Parameter | Default | Range / meaning |
|---|---|---|
| `complex_id` | unset | NIM 1.9 artifact name, 1–64 letters/digits/underscore/hyphen |
| `polymers` | required | 1–12 protein, DNA or RNA chains |
| `ligands` | absent | Up to 20; exactly one of `ccd` or `smiles` each |
| `constraints` | absent | Bond or pocket constraints |
| `recycling_steps` | 3 | 1–10 |
| `sampling_steps` | 50 | 10–1000 |
| `diffusion_samples` | 1 | 1–25 |
| `max_parallel_samples` | unset | 1–25 concurrent diffusion samples; NIM 1.9+ |
| `step_scale` | 1.638 | 0.5–5.0 |
| `output_format` | `mmcif` | Only mmCIF; CLI PDB conversion is client-side |
| `without_potentials` | false | Disable potentials |
| `concatenate_msas` | false | Merge supplied MSAs |
| `sampling_steps_affinity` | 200 | 10–1000 |
| `diffusion_samples_affinity` | 5 | 1–10 |
| `affinity_mw_correction` | false | Molecular weight correction |
| `write_full_pae` / `write_full_pde` | false | Write server NPZ files; see [outputs](outputs.md) |

`max_parallel_samples` controls concurrency within a prediction, independently of
client multi-endpoint concurrency. A lower value reduces peak device memory and
may increase runtime. It does not change the number of requested structures.
More recycles/samples increase compute; no parameter setting guarantees accuracy.

## Polymers, MSAs and templates

Polymer IDs are 1–4 alphanumeric characters. Sequences must be nonempty; proteins
accept standard one-letter amino acid codes plus `X`, DNA accepts `ATCG`, RNA
accepts `AUCG`. The client normalizes sequence case. The default per-chain limit
is 4096 characters; supported total complex size also depends on GPU memory and
NIM administrator settings.

```python
from boltz2_client import AlignmentFileRecord, Polymer

sequence = "ACDEFGHIKLMNPQRSTVWY"
protein = Polymer(
    id="A", molecule_type="protein", sequence=sequence,
    msa={"custom": {"a3m": AlignmentFileRecord(
        alignment=f">query\n{sequence}\n", format="a3m", rank=0,
    )}},
)
```

The example is a query-only MSA for syntax demonstration. Real homolog alignments
provide evolutionary information. Use `alignment`, not `data`. At most three
MSA database entries are accepted; each format key must match the record's
lowercase `format`. The first alignment sequence must match the polymer sequence.
Only A3M and CSV are consumed by NIM inference; FASTA and Stockholm records are
accepted by the schema but discarded during server input preparation.

`structural_templates` accepts up to four `StructuralTemplate` objects on protein
polymers only. Supply actual `structure` content, `format="cif"` or `"pdb"`, and
optional `chain_id` and `name` (up to 64 alphanumeric/underscore/hyphen characters).
`modifications` contains `Modification(ccd="SEP", position=...)` with 1-based
positions and 1–5 uppercase alphanumeric CCD codes. Choose modifications that
match the target chemistry.

## Ligands and constraints

Only one ligand may enable `predict_affinity`. Duplicate CCD/SMILES entries are
not accepted when affinity is enabled. `output_affinity_embedding=True` requires
`predict_affinity=True` on the same ligand. Read [affinity](affinity_prediction.md)
for score interpretation.

A bond constraint has `constraint_type="bond"` and exactly two atoms, each with
`id`, positive 1-based `residue_index`, and `atom_name`. A pocket constraint has
`constraint_type="pocket"`, a ligand `binder` ID and polymer residue `contacts`.
The 1.9 container restricts atom/contact IDs to 1–4 uppercase letters or exactly
four alphanumeric characters (for example `LIG` or `LIG1`, not `L1`).
Use IDs that actually occur in the request and residue positions/atom names that
exist in the selected molecules. The service validates molecular chemistry.

Source: [NVIDIA inference reference](https://docs.nvidia.com/nim/bionemo/boltz2/latest/inference.html).
