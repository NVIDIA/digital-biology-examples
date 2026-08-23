# ACS Fall 2026 GPU chemistry workshop

Explore a bounded chemistry-agent workflow with the NVIDIA nvMolKit library.
You can use an interactive notebook, a conversational OpenClaw experience, or
both. Each journey uses fixed inputs and validated operations so that you can
focus on the chemistry and the scientific limits of the results.

## Before you begin

- Use a current desktop browser.
- Brev GPU time is billable. Stop your environment when you finish.
- Keep API keys private. Enter a key only in the named Launchable field. Never
  paste it into a notebook, chat, or workshop result.
- Hosted inference can be rate-limited. If a request reports an error, take a
  screenshot and continue with another optional activity.

## Choose either journey

Both journeys are optional and independent. You can do either one, both, or
neither.

| Journey | Launchable | What you do |
| --- | --- | --- |
| Notebook | [nvMolKit + Nemotron Notebook](https://brev.nvidia.com/launchable/deploy/now?launchableID=env-3HJtJW3qHg4Dw1I3xt75BfpBmZW) | Run a guided notebook and approve bounded scientific stages. |
| OpenClaw | [Open Chemistry Agent](https://brev.nvidia.com/launchable/deploy/now?launchableID=env-3Hlp4pHBlTTlfDxfH41KkGhTeCV) | Send four science-first prompts in a chat. |

## Notebook journey

1. Open [NVIDIA inference](https://inference.nvidia.com), sign in, and create or
   copy an NVIDIA inference API key.
2. Open the Notebook Launchable. Enter the key in `NVIDIA_API_KEY`, only in this
   Launchable field, and deploy the default hardware.
3. Wait for setup to finish. Open JupyterLab from the port 8888 Secure Link.
4. Open `nvmolkit_nemotron_demo.ipynb` and run its cells from top to bottom.
5. In **Agent run**, select **Start Agent**. Review the bounded proposal, then
   select **Approve & Run** for each displayed stage.
6. After the MMFF94 stage, select **Run Objective Challenge**.
7. Review the evidence-backed conclusion and download any results you want.
8. Stop the Brev environment when you finish.

The notebook validates inputs with RDKit on the CPU. nvMolKit performs the
fingerprint, similarity, conformer-embedding, and MMFF94 operations on the GPU.
Python validates every bounded agent action and independently measures the
result.

## OpenClaw journey

1. Open the OpenClaw Launchable. Leave **Setup** empty and deploy the default
   hardware.
2. Wait for setup to finish, then open **Open Chemistry Agent**. The app should
   open directly. It should not request an API key, gateway token, or password.
3. Start one new chat.
4. Copy Prompt 1 below into the chat. Wait for the answer and image before you
   send the next prompt.
5. Send Prompts 2, 3, and 4 one at a time and in order.
6. After Prompt 4, select **Download Results** and download `results.zip`.
7. Stop the Brev environment when you finish.

Send each prompt only once. If OpenClaw is still working, wait. If you
accidentally send the same prompt twice, do not try to repair anything; the
workshop should return the existing completed result. If a request reports an
error, take a screenshot and continue with another optional activity.

## Four OpenClaw prompts

### Prompt 1 — Library and representation

<!-- ACS_PROMPT:01-data-and-representation:BEGIN -->
~~~text
Use the preinstalled ACS workshop workflow to inspect the fixed molecule library and explain how the molecules are represented for comparison. Run this workshop step once. Clearly distinguish RDKit work on the CPU from nvMolKit fingerprint generation on the GPU. Explain the measured result and its scientific limits, then show the result image and provide the workshop download. If this step has already completed in this chat, show the existing result without running it again.
~~~
<!-- ACS_PROMPT:01-data-and-representation:END -->

### Prompt 2 — Relationships and groups

<!-- ACS_PROMPT:02-relationships-and-groups:BEGIN -->
~~~text
Use the preinstalled ACS workshop workflow to find structurally similar molecules and group them using the fixed Butina rule. Run this workshop step once. Clearly distinguish GPU fingerprint and similarity calculations from CPU clustering. Explain what the groups mean, what they do not prove, and how the fingerprint and distance cutoff affect the result. Show the result image and provide the updated workshop download. If this step has already completed, show the existing result without running it again.
~~~
<!-- ACS_PROMPT:02-relationships-and-groups:END -->

### Prompt 3 — Sampled 3D geometry

<!-- ACS_PROMPT:03-sampled-3d-geometry:BEGIN -->
~~~text
Use the preinstalled ACS workshop workflow to generate and optimize the bounded set of sampled 3D conformers. Run this workshop step once. Explain which work ran on the GPU, what convergence and MMFF94 energy mean, and why these sampled conformers are not experimental structures. Show the result image and provide the updated workshop download. If this step has already completed, show the existing result without running it again.
~~~
<!-- ACS_PROMPT:03-sampled-3d-geometry:END -->

### Prompt 4 — Bounded panel objective

<!-- ACS_PROMPT:04-objective:BEGIN -->
~~~text
Use the preinstalled bounded workshop objective to improve the weakest-link structural diversity of the fixed four-molecule panel. Choose only permitted changes with the best predicted minimum pairwise Tanimoto distance, and stop when the objective finishes. Explain the starting panel, limiting pair, accepted changes, final result, and change in `D_min`. Make clear that this is a bounded descriptor exercise, not autonomous molecular design or evidence of biological performance. Show the final image and provide the complete workshop download. If the objective has already completed, show the existing result without running it again.
~~~
<!-- ACS_PROMPT:04-objective:END -->

## Results and downloads

Each OpenClaw prompt should show a visible result and update the workshop
download:

1. Prompt 1: a library preview image.
2. Prompt 2: a cluster-size image.
3. Prompt 3: an optimized-structure image.
4. Prompt 4: a final-panel image.

Select **Download Results** to download `results.zip`. The archive contains the
images, data tables, molecular files, summaries, and provenance produced by the
completed steps.

## Finish

Download any files you want to keep. Then stop or delete each Brev environment
that you started. A stopped environment retains its disk and can still incur
storage charges; deletion removes the environment and its disk.

## Scientific limits

This workshop produces computational descriptors and sampled force-field
geometries. It does not provide experimental evidence of molecular identity,
binding, activity, ADMET, efficacy, safety, synthesizability, clinical
relevance, or experimental structure.

Morgan-fingerprint and Tanimoto results depend on the fixed radius-2, 1024-bit
hashed representation. The Butina cutoff is a Tanimoto distance rule. Sampled
conformers are not experimental structures, and MMFF94 energies compare sampled
conformers only within the same molecule. The bounded panel objective searches
only the supplied candidates and does not demonstrate autonomous molecular
design.

## Official links

- [NVIDIA nvMolKit](https://github.com/NVIDIA-BioNeMo/nvMolKit)
- [NVIDIA inference](https://inference.nvidia.com)
- [Brev Launchables](https://docs.nvidia.com/brev/latest/launchables/index.html)
- [Brev GPU instance lifecycle](https://docs.nvidia.com/brev/latest/concepts/gpu-instances.html)
