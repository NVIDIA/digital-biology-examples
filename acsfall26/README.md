# ACS Fall 2026 GPU chemistry workshop

This workshop demonstrates a bounded BioNeMo Agent Toolkit workflow pattern for
chemistry, not an unrestricted or fully autonomous AI scientist. It follows the
pattern supported by the
[NVIDIA BioNeMo Agent Toolkit](https://github.com/NVIDIA-BioNeMo/bionemo-agent-toolkit),
without claiming direct toolkit runtime integration.

There are two required, complementary agentic chemistry environments. The
nvMolKit + Nemotron Notebook teaches direct nvMolKit and bounded Nemotron
through three guided modules. Conversational OpenClaw provides a separate
sandboxed OpenClaw experience with four tested prompts.

Nemotron plans and selects within validated choices. Python validates and
executes deterministic chemistry. nvMolKit performs the configured GPU
molecular operations. RDKit supports input handling, descriptors, CPU reference
work, and visualization. See the
[NVIDIA nvMolKit library](https://github.com/NVIDIA-BioNeMo/nvMolKit). No local
coding setup is required.

## Before the workshop

Complete these steps before you arrive:

1. Create [one NVIDIA account](https://account.nvidia.com/), verify your email,
   and complete an NVIDIA Cloud Account if prompted.
2. Sign in to [NVIDIA Brev](https://brev.nvidia.com/). Complete its onboarding
   and make sure your organization has Brev credits or a payment method.
3. Open the [NVIDIA API-key page](https://build.nvidia.com/settings/api-keys).
   Generate and copy one API key. Complete phone verification if requested. The
   conversational lab uses
   [NVIDIA Nemotron 3 Super 120B-A12B](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b?nim=hosted).

Hosted prototype access can be rate-limited. Brev GPU compute is separate and billable.
Never paste the key into chat, a screenshot, or a file. Paste it only into the
correct Launchable setup field:

| Required environment | Launchable ID | API-key field | Model use |
| --- | --- | --- | --- |
| nvMolKit + Nemotron Notebook | `env-3HJtJW3qHg4Dw1I3xt75BfpBmZW` | `NVIDIA_API_KEY` | Module 1: no LLM; hosted Modules 2–3 and companion: `nvidia/nemotron-3-nano-30b-a3b` |
| Conversational OpenClaw | `env-3Hlp4pHBlTTlfDxfH41KkGhTeCV` | `NVIDIA_INFERENCE_API_KEY` | [NVIDIA Nemotron 3 Super 120B-A12B](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b?nim=hosted) |

Use the same private API-key value in both fields.

## Complete both required labs

1. Deploy and open **nvMolKit + Nemotron Notebook**.
2. Complete numbered notebook Modules 1–3 in order.
3. Optionally run the integrated companion demo in the same Notebook Launchable.
4. Deploy and open the **Conversational OpenClaw Launchable**.
5. Complete the four existing conversational prompts in order.
6. Stop both Brev environments after the workshop.

Both Launchables are required. Complete the nvMolKit + Nemotron notebook first,
then complete the conversational OpenClaw lab.

For each deployment, use the signed-in Launchable page and confirm that the
required setup field is present, setup completes, and the expected app opens.
Repeat these checks for each new deployment. This guide makes no live-readiness claim.

## Required Lab 1 — nvMolKit + Nemotron Notebook

Open the
[nvMolKit + Nemotron Notebook Launchable](https://brev.nvidia.com/launchable/deploy/now?launchableID=env-3HJtJW3qHg4Dw1I3xt75BfpBmZW)
(Launchable ID `env-3HJtJW3qHg4Dw1I3xt75BfpBmZW`). Module 1 uses no LLM.
Hosted Modules 2–3 and the optional companion use
`nvidia/nemotron-3-nano-30b-a3b`.

1. Enter the API key in `NVIDIA_API_KEY`, then deploy.
2. Wait until setup is ready.
3. Open JupyterLab through the port 8888 Secure Link.
4. Run the Module 1 initialization. Confirm that it reports the installed nvMolKit version and one CUDA device. If it reports CPU fallback, stop and ask the facilitator.

Complete Modules 1–3 in order. Hosted mode is required for Modules 2–3.
Reference mode is instructor-directed recovery, makes zero hosted model calls,
and is not evidence that Nemotron ran.

### Module 1 — Direct nvMolKit ReFRAME analysis

Open `notebooks/01_direct_nvmolkit_reframe.ipynb`. Module 1 uses no LLM. It runs
Direct GPU Morgan fingerprints, Tanimoto similarity, fused Butina clustering,
and labeled RDKit CPU reference work. Compare bounded fingerprint radius, bit length, sample size, and Butina cutoff. Compare the GPU results with clearly labeled RDKit CPU reference work. Any Module 1 timing or throughput is an observation from the exact Notebook hardware, inputs, parameters, and the attendee run. It is not a general acceleration or speedup claim.

**Optional advanced run:** Run the 10,000-row exercise only when instructed.

### Module 2 — Agent-assisted ReFRAME neighborhoods

Open `notebooks/02_agent_assisted_reframe_neighborhoods.ipynb`. Nemotron selects two bounded failure policies and does not write executable code. Python renders, validates, binds, and executes the allow-listed implementation. Review the 60-row atlas and representation sensitivity.

### Agent-guided workflow

#### Module 3 — Agent-guided panel design

Open `notebooks/03_full_agent_reframe_panel_design.ipynb`. Nemotron gives a bounded plan and audit. The attendee reviews both bounded, allow-listed strategies, selects one, and clicks **Approve Plan & Run Agent** to approve execution. Python executes the selected strategy and independently validates the resulting 24-of-96 panel and its artifacts from the fixed 96-row ReFRAME snapshot. The attendee then reruns Steps 5 and 6 for the receipt and gallery.

#### Optional integrated companion demo

Open `notebooks/nvmolkit_nemotron_demo.ipynb` only within the required notebook environment. This optional companion shows six approved stages, a bounded objective challenge, and an evidence-backed conclusion. It is not required completion.

## Required Lab 2 — Conversational OpenClaw

Open the
[Conversational OpenClaw Launchable](https://brev.nvidia.com/launchable/deploy/now?launchableID=env-3Hlp4pHBlTTlfDxfH41KkGhTeCV)
(Launchable ID `env-3Hlp4pHBlTTlfDxfH41KkGhTeCV`). This required lab uses
[NVIDIA Nemotron 3 Super 120B-A12B](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b?nim=hosted)
in a sandboxed conversational workspace to explore the configured agentic
chemistry analyses. The four preset prompts below are tested starting points.
You can change the questions and the requested interpretation about these
analyses, while the sandbox keeps execution within the approved tools, fixed
data, and configured
[nvMolKit](https://github.com/NVIDIA-BioNeMo/nvMolKit) capabilities.

1. Use the default hardware. Confirm that the visible row shows one NVIDIA L4,
   x86-64, 4 CPUs, 16 GiB RAM, and 128 GiB disk. The row does not need to show `g6.xlarge`.
2. Enter the API key in `NVIDIA_INFERENCE_API_KEY`, then deploy.
3. Wait until setup is ready. Open **Open Chemistry Agent** and create one new session.
4. For the tested workshop path, paste the four prompts below unchanged and in order into that same session. Wait for each answer before sending the next prompt.

The installed `nvmolkit-usage` skill remains available for optional exploration
after the tested exercise. It describes the supported
[nvMolKit](https://github.com/NVIDIA-BioNeMo/nvMolKit) functions in this
environment. The four tested prompts do not read it.

If an LLM request times out, start a new session and retry the whole prompt once. Do not retry individual commands. After a second timeout, ask the facilitator.

## Four prompts

<!-- ACS_PROMPT:01-data-and-representation:BEGIN -->
~~~text
Question: What is in the fixed molecule library, and how is it represented for comparison?

Work only in `/sandbox/.openclaw/workspace`.
Do not read or edit files.
Do not install software or use the network.
Do not run an alternate command.

Run only this exact command, once:
env PYTHONPATH=/tmp/.local/lib/python3.13/site-packages python3 /sandbox/.openclaw/workspace/acs_workshop_runner.py run-lesson data-and-representation

If the command fails, report the error and stop. Do not repair or retry.
Use only the returned results. Answer with these six headings in this order:
Question
What ran
Measured result
Meaning
Scientific limit
Image and download location

Use at most three measured facts. State that the data are a deterministic 256-record ChEMBL convenience sample, not representative chemical space. State that Morgan/Tanimoto conclusions depend on the radius-2, 1024-bit hashed fingerprint. Report real GPU execution, not acceleration or speedup. Say that the current bundle is in **Download Results** at `workshop/results.zip`.

End with this exact line:
MEDIA:/sandbox/.openclaw/workspace/outputs/workshop/01-inspection/library_preview.png
~~~
<!-- ACS_PROMPT:01-data-and-representation:END -->

<!-- ACS_PROMPT:02-relationships-and-groups:BEGIN -->
~~~text
Question: Which molecules are similar, and how does Butina group them from the GPU-computed Tanimoto distances?

Work only in `/sandbox/.openclaw/workspace`.
Do not read or edit files.
Do not install software or use the network.
Do not run an alternate command.

Run only this exact command, once:
env PYTHONPATH=/tmp/.local/lib/python3.13/site-packages python3 /sandbox/.openclaw/workspace/acs_workshop_runner.py run-lesson relationships-and-groups

If the command fails, report the error and stop. Do not repair or retry.
Use only the returned results. Answer with these six headings in this order:
Question
What ran
Measured result
Meaning
Scientific limit
Image and download location

Use at most three measured facts. State that cutoff `0.40` is Tanimoto distance. State that the result depends on the radius-2, 1024-bit hashed fingerprint and that similarity `1.0` does not prove molecular identity. Report real GPU fingerprint and similarity execution followed by CPU RDKit clustering; do not claim acceleration or speedup. Say that the current bundle is in **Download Results** at `workshop/results.zip`.

End with this exact line:
MEDIA:/sandbox/.openclaw/workspace/outputs/workshop/04-clusters/cluster_sizes.png
~~~
<!-- ACS_PROMPT:02-relationships-and-groups:END -->

<!-- ACS_PROMPT:03-sampled-3d-geometry:BEGIN -->
~~~text
Question: What sampled 3D geometries were generated and optimized?

Work only in `/sandbox/.openclaw/workspace`.
Do not read or edit files.
Do not install software or use the network.
Do not run an alternate command.

Run only this exact command, once:
env PYTHONPATH=/tmp/.local/lib/python3.13/site-packages python3 /sandbox/.openclaw/workspace/acs_workshop_runner.py run-lesson sampled-3d-geometry

If the command fails, report the error and stop. Do not repair or retry.
Use only the returned results. Answer with these six headings in this order:
Question
What ran
Measured result
Meaning
Scientific limit
Image and download location

Use at most three measured facts. State that the deterministic selected molecules are not centroids, medoids, or globally optimal representatives. State that sampled conformers are not experimental structures and MMFF94 energies compare sampled conformers within one molecule only. Report real GPU execution, not acceleration or speedup. Say that the current bundle is in **Download Results** at `workshop/results.zip`.

End with this exact line:
MEDIA:/sandbox/.openclaw/workspace/outputs/workshop/06-mmff94/optimized_structures.png
~~~
<!-- ACS_PROMPT:03-sampled-3d-geometry:END -->

<!-- ACS_PROMPT:04-objective:BEGIN -->
~~~text
Question: Can a bounded agent improve the weakest-link diversity of a four-molecule panel?

Work only in `/sandbox/.openclaw/workspace`.
Do not read or edit files.
Do not install software or use the network.
Do not run an alternate command.

Run only the exact commands below.

Run `objective-start` exactly once with this command:
env PYTHONPATH=/tmp/.local/lib/python3.13/site-packages python3 /sandbox/.openclaw/workspace/acs_workshop_runner.py objective-start

If `terminal` is `true`, run zero objective-step commands. If the result is pending, find the maximum numeric `predicted_score` in the displayed actions. Select one displayed action tied at that maximum; this is the best predicted `D_min`. Substitute the exact returned `state_id` and `swap_id` in this template. Keep both substituted values single-quoted; a swap ID can contain `->`.

env PYTHONPATH=/tmp/.local/lib/python3.13/site-packages python3 /sandbox/.openclaw/workspace/acs_workshop_runner.py objective-step --state-id 'STATE_ID_FROM_MENU' --swap-id 'SWAP_ID_FROM_MENU'

After each result, stop immediately when `terminal` is `true`. Otherwise, repeat with the new displayed menu. Run at most three objective-step commands in total.

If a command fails, report the error and stop. Do not repair or retry.
Use only the returned results. Answer with these six headings in this order:
Question
What ran
Measured result
Meaning
Scientific limit
Image and download location

Use at most three measured facts: baseline `D_min`, final `D_min`, and their change. Put the baseline panel, limiting pair, accepted swap or swaps, and final panel under **What ran**. State that `D_min` is the weakest-link diversity score within eight fixed candidates. It is a structural-descriptor objective and does not demonstrate unrestricted autonomous design or biological performance. Report real GPU execution, not acceleration or speedup. Say that the full bundle is in **Download Results** at `workshop/results.zip`.

End with this exact line:
MEDIA:/sandbox/.openclaw/workspace/outputs/workshop/07-objective/final_panel.png
~~~
<!-- ACS_PROMPT:04-objective:END -->

## Download

The four key PNG images appear in chat. Open **Download Results** for the complete files.
Then open `workshop/` and download `results.zip`. A path that starts with `/sandbox/` is
an agent filesystem path, not a browser URL.

The ZIP contains the fixed input and provenance plus the generated README,
CSV, SDF, JSON, and PNG files available at that point in the workflow.

## Finish

Stop both workshop environments as soon as the exercise ends.
After downloading your files, **Delete each environment when you are finished**.
Stopped storage can still incur a charge. Deletion is permanent, so download your results first.

## Scientific limits

- The notebook uses a deterministic 96-row ReFRAME snapshot and validates only a bounded 24-compound panel.
- The 60-row fingerprint-dependent atlas depends on the selected representation.
- Reported values are run-specific timings and throughput, not general speedup evidence.
- The data are a deterministic 256-record ChEMBL convenience sample, not representative chemical space.
- The clustering cutoff `0.40` is Tanimoto distance.
- The deterministic selected molecules are not centroids, medoids, or globally optimal representatives.
- Morgan/Tanimoto conclusions depend on the radius-2, 1024-bit hashed fingerprint, and similarity `1.0` does not prove molecular identity.
- MMFF94 energies compare sampled conformers within one molecule only.
- `D_min` is the weakest-link diversity score within eight fixed candidates.
- The run demonstrates real GPU execution, not acceleration or speedup.

The results do not prove identity, binding, activity, ADMET, efficacy, safety, synthesizability, clinical value, or experimental structure.

## Official links

- [Workshop repository](https://github.com/ktretina/nvmolkit-brev-notebook)
- [NVIDIA BioNeMo Agent Toolkit](https://github.com/NVIDIA-BioNeMo/bionemo-agent-toolkit)
- [NVIDIA nvMolKit library](https://github.com/NVIDIA-BioNeMo/nvMolKit)
- [NVIDIA Brev quickstart](https://docs.nvidia.com/brev/getting-started/quickstart)
- [Official NVIDIA account and API-key instructions](https://docs.nvidia.com/ai-workbench/user-guide/latest/how-to/integrations/nvidia-integrations.html)
- [Brev stop, storage, and deletion guidance](https://docs.nvidia.com/brev/concepts/gpu-instances)
