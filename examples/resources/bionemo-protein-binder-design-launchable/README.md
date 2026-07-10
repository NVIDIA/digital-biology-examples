<!--
Copyright (c) 2026, NVIDIA CORPORATION. Licensed under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with the License. You may
obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required
by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
express or implied. See the License for the specific language governing permissions and
limitations under the License.
-->

# De Novo Protein Binder Design — Brev Launchable (Proteina-Complexa + Boltz-2)

A self-contained **Brev Launchable** that runs an end-to-end de novo **protein binder design**
campaign on a single **A100 / H100 / L40S** GPU in **well under an hour**:

- **Generation — [NVIDIA Proteina-Complexa](https://github.com/NVIDIA-Digital-Bio/Proteina-Complexa):**
  co-designs the binder **sequence + full-atom structure together**. The default generates a broad
  pool quickly (no AF2); reward-guided search (best-of-n / beam / MCTS with an AF2 reward) is optional.
- **Assessment — Boltz-2 (local NIM):** an *independent* model **co-folds** each binder–target complex
  and the designs are **ranked by co-folding confidence** (ipTM), with a best-of-N diffusion pass to
  tame Boltz-2's sampling noise. The top-K binders are reported with plots and an embedded **Mol\***
  3D view.

## Files

| File | Purpose |
|------|---------|
| `brev_startup.sh` | Launchable **startup script** (paste into the wizard): clones this repo and runs `setup.sh`. Reads `NGC_API_KEY` (and optional `GITHUB_TOKEN`). |
| `setup.sh` | Idempotent provisioning: builds Proteina-Complexa (`uv` env + public weights), fetches the agent-toolkit skill + ipSAE, sets up AF2-Multimer params, starts a **local Boltz-2 NIM** on `:8000`, registers a widget-capable JupyterLab kernel, and serves it on `:8888`. Writes `~/.complexa_env`. |
| `Complexa_Binder_Design.ipynb` | The workflow notebook: target → generate (broad pool) → Boltz-2 co-fold → rank top-K → plots + Mol\* views. |

Everything else is fetched at deploy time by `setup.sh` (Proteina-Complexa + weights, the
[bionemo-agent-toolkit](https://github.com/NVIDIA-BioNeMo/bionemo-agent-toolkit) skill, ipSAE,
AF2-Multimer params, the Boltz-2 NIM image, and Python deps).

## Target: PD-L1 (cancer immunotherapy)

Binders are designed against **PD-L1** (Programmed death-ligand 1 / CD274; registered Complexa target
**`32_PDL1_ALPHA`**, PDB `5O45`, span `A17-132`, hotspots `A56/A115/A123`, binder length 50–120 aa).
Tumors display PD-L1, which engages **PD-1** on T cells to switch them off (an immune *checkpoint*); a
binder covering PD-L1's PD-1-binding face blocks that checkpoint and re-activates anti-tumor T cells —
the mechanism of approved checkpoint inhibitors (atezolizumab, durvalumab, avelumab). PD-L1 is a
well-behaved, highly *designable* target. Swap `PBD_TARGET` for any of the ~44 registered targets
(`complexa target list`: IL-7Rα, TrkA, VEGF-A, TNFα, HER2, or the SARS-CoV-2 RBD `30_SC2RBD`, …).

## Deploy on Brev (Console wizard)

You need an **A100 / H100 (80 GB) or L40S (48 GB)** GPU and an **`NGC_API_KEY`** (`nvapi-…`) for the local Boltz-2 NIM
(Proteina-Complexa + AF2 weights are public). The Brev **Console wizard** is the way to create a
shareable Launchable (the CLI manages instances, not Launchables).

1. **Files and runtime:** *"I have code files in a git repository"* → this repo's URL; select
   **VM Mode** (required — the local Boltz-2 NIM needs Docker + `sudo`; VM Mode ships Ubuntu 22.04 +
   Docker + CUDA).
2. **Setup script:** paste **`brev_startup.sh`** (it clones the repo and runs `setup.sh`). The Brev
   wizard has **no separate secret field** — provide `NGC_API_KEY` *inside this script*:
   - **Embed (attendees need no key):** uncomment the `export NGC_API_KEY='nvapi-...'` line at the top
     of the pasted script and paste a **short-lived, scoped** event key.
   - **Bring-your-own-key:** leave it commented; each user exports `NGC_API_KEY` in the Brev terminal
     (then re-runs the script) or enters it in the notebook's first cell.
3. **Jupyter / networking:** choose **No** to Brev's built-in Jupyter, then add a **secure link named
   `jupyter` on port `8888`** — `setup.sh` serves the widget-capable JupyterLab there (Brev's stock
   Jupyter can't render the Mol\* widgets). Optionally expose `8000` to reach Boltz-2 directly.
4. **Compute:** 1× **A100 / H100 (80 GB) or L40S (48 GB)**, **~1 TB disk**.
5. **Review:** name it, set access (link / org / community), **Create Launchable** → shareable link + badge.

See the [Brev Launchables docs](https://docs.nvidia.com/brev/concepts/launchables).

> **Event key tip.** An embedded key is readable on each VM while valid, so use a **short-lived,
> scoped** NGC key (TTL as low as 1 hour; scope to NGC Catalog / NIM) and **deactivate/delete it
> right after the event**. Expect a first-boot image+weights pull per instance — stagger starts to
> avoid NGC pull-rate throttling.

## Run the notebook

Open **`Complexa_Binder_Design.ipynb`** and **select the `Python (Complexa)` kernel** (top-right
kernel picker or *Kernel → Change Kernel*), then run top to bottom. The setup cell reads its
configuration from environment variables (with sensible defaults):

| Env var | Default (DEMO) | Meaning |
|---------|----------------|---------|
| `OPENHACKATHON_DEMO_MODE` | `1` | `1` = 48/24/5/75 (pool/assess/diffusion/steps); `0` = 96/64/8/100 |
| `PBD_TARGET` | `32_PDL1_ALPHA` | any registered Complexa target (PD-L1 default) |
| `PBD_ALGORITHM` | `single-pass` | broad sampling; or `best-of-n` / `beam` for reward-guided search |
| `PBD_AF2_REWARD` | `0` | `1` turns on the AF2-Multimer reward (only with `best-of-n`; slower) |
| `PBD_NUM_SAMPLES` | `48` | size of the generated pool |
| `PBD_N_ASSESS` | `24` | how many to co-fold + score with Boltz-2 |
| `PBD_DIFFUSION_SAMPLES` | `5` | Boltz-2 structures sampled per design; the best-ipTM one is kept |
| `PBD_SAMPLING_STEPS` | `75` | Boltz-2 refinement steps per prediction |
| `PBD_APO` | `0` | `1` adds the apo (binder-alone) refold → apo↔holo stability RMSD |
| `PBD_TOP_K` | `5` | how many top-ranked binders to surface |

> Co-fold cost scales with `N_ASSESS × DIFFUSION_SAMPLES × SAMPLING_STEPS` — dial down for speed, up
> for quality (demo config runs ~20–40 min; longer on smaller GPUs like L40S).
>
> **L40S (48 GB) note:** vs A100/H100 (80 GB), very large co-folding jobs — big complexes, high
> `PBD_DIFFUSION_SAMPLES`, or the AF2-reward path — may hit **CUDA OOM**; reduce `PBD_N_ASSESS` /
> `PBD_DIFFUSION_SAMPLES` (or binder/target size) if so.

**Strategy — generate broad, rank by Boltz-2.** The default generates a large pool fast (no AF2) and
ranks it by **Boltz-2 co-folding ipTM**, surfacing the **top-K**. Boltz-2's co-folding is stochastic,
so for a more reliably gate-passing top binder, raise the pool (`PBD_NUM_SAMPLES=32`+ /
`PBD_N_ASSESS`) and the per-design diffusion samples (`PBD_DIFFUSION_SAMPLES=5`, best kept), or set
`OPENHACKATHON_DEMO_MODE=0` (64 / 48 / 5).

**Co-folding gate (ipSAE-excluded):** ipTM ≥ 0.65, complex & binder pLDDT ≥ 0.70, ≥ 20% hotspot
contact (plus apo-binder pLDDT ≥ 0.70 and apo↔holo RMSD ≤ 2.5 Å when `PBD_APO=1`). **ipSAE is
excluded** because it's unavailable on Boltz-2's PAE and reads 0. The notebook ranks by ipTM and
reports the **top-K**. PD-L1 is designable, so designs should clear the gate; on a harder target
(e.g. the SARS-CoV-2 RBD) clearing every bar generally needs scale.

**Seeing the 3D Mol\* widgets.** The embedded Mol\* views need the JupyterLab **front-end** to have
the `anywidget` / `ipywidgets` extensions. `setup.sh` serves a widget-capable JupyterLab on `:8888`;
if you use a stock JupyterLab instead, the viewer prints `<...PDBeMolstar object>` rather than
rendering, so serve from the Complexa `.venv` (see `setup.sh` Phase 6).

## Responsible use

De novo binder design is dual-use. Use it only for legitimate research and therapeutic intent, and
verify any epitope/target claims against the primary literature before acting on them.
