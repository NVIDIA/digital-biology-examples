# Natural Scientific Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the four ACS Fall 2026 OpenClaw prompt bodies as natural scientific requests without changing their execution or safety controls.

**Architecture:** Make one documentation-only edit in the public attendee page. Preserve the four prompt markers and every bounded execution, interpretation, artifact, and repeat-safety instruction; verify the marked blocks directly and do not change the Launchable or runtime.

**Tech Stack:** Markdown, Python standard library, Git

---

### Task 1: Rewrite and verify the four published prompts

**Files:**
- Modify: `acsfall26/README.md:68-96`
- Reference: `docs/superpowers/specs/2026-08-23-natural-scientific-prompts-design.md`

- [ ] **Step 1: Confirm the current wording is the expected RED state**

Run:

```bash
rg -n "preinstalled|workshop (workflow|step|download|objective)" acsfall26/README.md
```

Expected: four prompt lines are reported. Stop if the four marked prompt bodies
do not match the approved starting text.

- [ ] **Step 2: Replace only the four marked prompt bodies**

Use these exact prompt bodies:

```text
Inspect the fixed molecule library and explain how the molecules are represented for comparison. Run this analysis once. Clearly distinguish RDKit work on the CPU from nvMolKit fingerprint generation on the GPU. Explain the measured result and its scientific limits, then show the result image and provide the results download. If this analysis has already completed in this chat, show the existing result without running it again.
```

```text
Find structurally similar molecules and group them using the fixed Butina rule. Run this analysis once. Clearly distinguish GPU fingerprint and similarity calculations from CPU clustering. Explain what the groups mean, what they do not prove, and how the fingerprint and distance cutoff affect the result. Show the result image and provide the updated results download. If this analysis has already completed, show the existing result without running it again.
```

```text
Generate and optimize the defined set of sampled 3D conformers. Run this analysis once. Explain which work ran on the GPU, what convergence and MMFF94 energy mean, and why these sampled conformers are not experimental structures. Show the result image and provide the updated results download. If this analysis has already completed, show the existing result without running it again.
```

```text
Within the permitted candidate set, improve the weakest-link structural diversity of the fixed four-molecule panel. Run this analysis once. Choose only permitted changes with the best predicted minimum pairwise Tanimoto distance, and stop when the objective finishes. Explain the starting panel, limiting pair, accepted changes, final result, and change in `D_min`. Make clear that this is a bounded descriptor exercise, not autonomous molecular design or evidence of biological performance. Show the final image and provide the complete results download. If this analysis has already completed, show the existing result without running it again.
```

Do not change headings, markers, fences, or surrounding instructions.

- [ ] **Step 3: Run the marked-prompt verifier once**

Run:

```bash
python3 -c 'import re; from pathlib import Path; s=Path("acsfall26/README.md").read_text(); b=re.findall(r"<!-- ACS_PROMPT:[^:]+:BEGIN -->\n~~~text\n(.*?)\n~~~\n<!-- ACS_PROMPT:[^:]+:END -->", s, re.S); assert len(b)==4; joined="\n".join(b).lower(); assert "workshop" not in joined; assert "preinstalled" not in joined; assert all("without running it again" in p for p in b); assert all("download" in p and "image" in p for p in b); assert all("run this analysis once" in p.lower() for p in b); print("4 prompt blocks passed")'
```

Expected:

```text
4 prompt blocks passed
```

- [ ] **Step 4: Inspect the exact diff**

Run:

```bash
git diff --check
git diff -- acsfall26/README.md
```

Expected: no whitespace errors; only the four prompt-body lines change.

- [ ] **Step 5: Commit the verified prompt edit**

Run:

```bash
git add acsfall26/README.md
git commit -m "docs: make ACS prompts natural scientific requests"
```

Expected: one commit containing only `acsfall26/README.md`.

- [ ] **Step 6: Report the publication boundary**

Report the commit and verification result. Do not push, publish, change the
Launchable, rerun the live chemistry trajectory, or stop the live instance as
part of this wording-only task.
