# Natural Scientific Prompt Wording Design

## Goal

Make the four ACS Fall 2026 OpenClaw prompts read like natural scientific
requests. Remove wording that describes the environment as a preinstalled ACS
workshop workflow.

## Scope

Change only the four marked prompt bodies in `acsfall26/README.md`. Do not
change the surrounding attendee instructions, prompt markers, OpenClaw
configuration, workspace routing, runner, scientific workflow, or artifacts.

## Wording

Each prompt will begin with its scientific objective:

1. Inspect the fixed molecule library and explain its representation.
2. Find structurally similar molecules and group them with the fixed Butina
   rule.
3. Generate and optimize the defined set of sampled 3D conformers.
4. Improve the weakest-link structural diversity of the fixed four-molecule
   panel within the permitted candidate set.

Remove all workshop framing from the four prompt bodies. Use `analysis` and
`results download` instead of `workshop step` and `workshop download`.

## Reliability Contract

Preserve these controls without changing their meaning:

- run each analysis once;
- reuse an existing completed result after an accidental repeat;
- distinguish CPU and GPU work correctly;
- explain the measured result and its scientific limits;
- retain the fixed Butina rule and permitted panel changes;
- request the expected image and results download;
- preserve the objective stop condition; and
- keep all limitations on molecular similarity, sampled conformers, and
  biological interpretation.

The prompt wording is not the runtime-routing mechanism. OpenClaw workspace
instructions and the bounded runner continue to provide that routing.

## Verification

Run the existing published-prompt verifier once. Confirm that:

- all four prompt markers remain unchanged;
- no prompt body contains `workshop`, `preinstalled`, or `pre-installed`;
- every reliability control listed above remains present; and
- the source diff changes only the four prompt bodies and this design record.

Do not repeat the four-prompt live scientific workflow solely for this wording
change. The completed live journey already demonstrated the same retained
objectives and controls. If the existing verifier exposes an operational
dependency on the removed wording, stop and report it instead of expanding the
change.
