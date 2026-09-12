# Validation report — 2026-09-11

Validation of the `0.6.0` client, performed during its development cycle. Tested against local
Boltz2 NIM **1.9.0** on an RTX PRO 6000 Blackwell, driver **595.71.05**.

## Current notebook review

Five numbered notebooks cover protein prediction, protein complexes, CDK4
affinity, protein–DNA, and covalent ligands. The separate A3M notebook is merged
into protein complexes; the short SageMaker connection example moved to the
deployment guide. All current links and notebook version details were updated.

- **169 offline tests passed**, including format, execution and request-schema
  checks for every retained notebook. The count decreased by three parametrized
  cases when the two redundant notebooks were removed.
- **All five notebooks passed actual NIM inference** and saved valid mmCIF files.
- All five inline viewers rendered in headless Chrome without JavaScript errors.
  The covalent viewer also passed after its binding-site zoom/opacity adjustment.
- Protein prediction passed with and without matrix output. Four finite 65×65
  PAE/PDE arrays were inspected from the server output mount.
- CDK4 passed without an MSA, with a real PDB70 search, and with that saved A3M
  file. All three affinity embeddings were finite arrays of shape 1×384.
- Protein complexes passed with precomputed paired A3M input. The validation
  alignments were labeled synthetic fixtures; this verifies conversion and
  inference, not homolog quality. No databases were downloaded.
- Missing, incomplete and mismatched MSA inputs failed before prediction in
  four negative checks. The validator rejects unknown notebook filenames.
- Barstar was restored to UniProt's mature 89-residue sequence, and the DNA
  reverse complement is calculated in code. Both were checked in saved structures.
- SageMaker live testing remains skipped as requested.

Current evidence is under `results/notebook-refresh*`, including the offline
JUnit report, executed notebooks, viewer screenshots, artifact checks, and
optional-input runs. The broader client results below predate this notebook-only
review; the 197-request stress workload was not repeated for documentation edits.

## Changes

- Reduced 19 overlapping Python examples to seven focused, runnable scripts.
  Removed obsolete development harnesses, unused data and embedded prediction results.
- Simplified all seven notebooks and six long guides. Notebook imports and output
  saving are minimal; SageMaker uses an existing endpoint.
- Fixed parameter forwarding in async/sync multi-endpoint methods, an unawaited
  health-check coroutine, and successful CLI exit statuses after failed screens.
- Hosted readiness/metadata calls now report unsupported operations explicitly.
  They do not assume an endpoint is healthy without making a prediction.
- Added real-kernel notebook execution and Bash CLI validation with saved-output
  checks. Stress tests now fail if any request fails.

## Earlier full client validation

| Check | Result |
|---|---|
| Complete pytest suite, including real endpoints and stress | **222 passed, 3 skipped**, 445.45 seconds |
| Offline subset within that run | 172 passed |
| SageMaker live tests | Three skipped at the user's request |
| Six local notebooks in real Jupyter kernels | All passed; saved structures parsed with finite coordinates |
| CDK4 notebook MSA branches | No MSA, real PDB70 search, and saved A3M file all passed |
| Six notebook viewers in headless Chrome | All rendered canvases, no JavaScript errors; screenshots retained |
| Seven retained Python example scripts | All passed against the real local services |
| Async/sync Python workflows | Protein, ligand/CCD, pocket/covalent/disulfide constraints, DNA/RNA, MSA, templates, modifications, cyclic input, YAML, multiple samples and multi-endpoint screening passed |
| Bash CLI | 19 workflows, raw curl prediction, and three expected error exits passed |
| Stress predictions | 50/50 protein and 147/147 affinity requests passed; JSON scores and mmCIF coordinates checked |
| NIM 1.9 outputs | Two samples, three affinity embedding fields, complete JSON/CIF files, and four finite square PAE/PDE matrices verified |
| Wheel/sdist and Twine | Passed |
| Clean wheel installation | Imports, CLI, dependency check and bundled species data passed without pandas or py3Dmol |

Bash checks cover health/metadata, protein/MSA, mmCIF/PDB, SMILES/CCD ligands,
affinity embeddings, pocket/covalent/DNA complexes, JSON/YAML, A3M conversion,
multimers, multi-endpoint dispatch, screening and MSA Search commands. Empty URL,
invalid sequence and failed compound screening correctly return nonzero status.

## Services and limits

- Boltz2: `http://localhost:8000`, container `boltz2-nim-1-9`.
- MSA Search: `http://localhost:8001`, container `boltz2-msa-validation`, image
  `nvcr.io/nim/colabfold/msa-search:2.3.0`, PDB70 profile
  `3087b7ea46d601200c1f90c9246a7aa344e487056286497515900b0924d7853a`.
  Its validation cache occupies 108 MB.
- NVIDIA-hosted prediction passed in the final complete suite. Other probes
  encountered intermittent HTTP 504 and 429 responses; availability/rate limits
  are not established by a successful sample request.
- Live paired-MSA search and MSA template retrieval were not run: they require
  UniRef30 taxonomy and PDB structure databases beyond the PDB70 profile. Additional
  database downloads were skipped at the user's request. Precomputed A3M pairing
  and Boltz2 template inference were tested successfully.
- These checks verify software behavior and output integrity, not biological
  accuracy, multi-GPU scaling or performance guarantees.

## Reproduce and inspect

See [development instructions](development.md). Local evidence is ignored by Git:

- `results/full-suite.xml`: complete pytest results.
- `results/notebooks/`: executed notebooks, per-notebook report, viewer HTML/screenshots.
- `results/notebooks-with-msa/` and `results/notebooks-with-msa-file/`: MSA branch runs.
- `results/cli/validation.log`: actual Bash commands and artifact checks.
- `results/stress/{proteins,affinity}/`: all prediction outputs and per-request results.
- `results/examples/validation.json`: all seven Python examples.
- `results/nim-1.9-artifacts/validation.json`: full matrix/embedding validation.
- `results/hosted/`: additional hosted probe results.

Publication is separate from this validation report. Use the package indexes
to check release availability; TestPyPI validation precedes production promotion.
