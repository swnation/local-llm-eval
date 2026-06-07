---
id: gemma-4-qat-llamacpp-c1-endpoint-replay-candidate-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: Main PC plan for deciding whether Gemma 4 26B A4B QAT may enter a tiny C1 endpoint-replay candidate lane
related:
  - docs/gemma-4-qat-llamacpp-endpoint-readiness-bridge-plan-2026-06-07.md
  - docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md
  - docs/c1-endpoint-replay-failure-triage-and-alignment-plan-2026-06-02.md
  - docs/hpz2-llamacpp-h2-endpoint-runner-2026-06-01.md
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
  - hpz2-run-artifacts: results/gemma_llamacpp_endpoint_readiness_bridge_20260607_173638/
---

# Gemma llama.cpp C1 Endpoint-Replay Candidate Plan

## Project Goal Check

- direct value: decide the next safe step after the Gemma 26B A4B QAT bridge
  artifact, without overstating endpoint readiness or entering model ranking.
- classification: `direct progress` with evaluation-safety value.
- narrower scope: Main PC plan draft only. No code patch, HP command, model
  load, prompt/API call, `/explain`, endpoint replay, EMR write/reindex,
  artifact mutation, relay update, librarian backup, commit, or push is
  authorized by this file.

## Decision

Gemma 4 26B A4B QAT Q4_0 may be treated as a candidate for a tiny C1
endpoint-replay lane.

It is not endpoint-ready yet.

It must not be added to the default Primary4 C1 replay, broad H2 matrix,
model-ranking lane, or HP larger-model lane. It should enter through a
dedicated Gemma candidate patch and a later explicit HP execution GO.

## Evidence Consumed

Source repo:

```text
local-llm-eval@6a529f8443b2b48c69768df9ca6182144a50b546
feat(rag): add Gemma endpoint bridge mode
```

Published artifact:

```text
hpz2-run-artifacts@40e2a0e41793f1c9112ddd4bf587856e7778c5b4
results/gemma_llamacpp_endpoint_readiness_bridge_20260607_173638/
```

Evidence access note:

- Main PC `hpz2-run-artifacts` main worktree is known dirty/diverged and may
  not contain this path at worktree `HEAD`.
- The reviewed evidence is the published remote-tracking tree:
  `git -C C:\Github\hpz2-run-artifacts show origin/main:<artifact-path>` at
  commit `40e2a0e41793f1c9112ddd4bf587856e7778c5b4`.
- For durable reproduction, `git show
  40e2a0e41793f1c9112ddd4bf587856e7778c5b4:<artifact-path>` is equivalent
  after fetching that commit.
- Do not treat absence from the dirty local worktree as absence from the
  published artifact unless `origin/main` at the pinned commit is also missing
  the artifact path.

Reviewed bridge metadata:

- mode: `gemma_llamacpp_endpoint_readiness_bridge`.
- backend: direct llama.cpp `/v1/chat/completions`.
- bridge shape: synthetic C1-shaped metadata-only lane.
- model: `hpz2-gemma4-26b-a4b-qat-q4_0`.
- stopped early: false.
- raw model output stored: false.
- endpoint readiness assessed: false.
- no `/explain` call.
- GB1 final-answer C1-shape: PASS, API ok, content channel, reasoning chars 0,
  exact `[kb:DEMO_GEMMA_BRIDGE:001]` citation, PHI-like hits 0.
- GB2 JSON C1-shape: PASS, API ok, parsed JSON, content channel, reasoning
  chars 0, exact `[kb:DEMO_GEMMA_BRIDGE:001]` citation, PHI-like hits 0.
- final preflight: ports 0, shim processes 0.

Notes:

- `server_exit_code=1` remains a controlled-termination lifecycle caveat. It is
  not a bridge artifact blocker because model status completed, health was OK,
  `stopped_early=false`, and final preflight was clean.
- Generated `server_stderr.txt` trailing whitespace is preserved as runtime-log
  fidelity, not source-code style.

## What The Bridge Proves

The bridge proves only this:

```text
Gemma 4 26B A4B QAT can preserve clean final-answer and JSON-contract behavior
under a synthetic C1-shaped direct llama.cpp prompt.
```

It does not prove:

- `/explain` readiness.
- retrieval behavior.
- shim behavior with the endpoint prompt.
- citation verifier behavior.
- clinical semantic quality.
- model ranking.
- Primary4 promotion.
- 31B or larger-model behavior.

## Current Runner/Config Gap

Gemma QAT cannot be run through the existing C1 endpoint replay as-is.

Current endpoint runner defaults:

- `C1_REPLAY_PILOT_MODELS` includes only Qwen official and Granite.
- `PRIMARY_MODELS` includes the Primary4 set, not Gemma QAT.
- `--primary4-c1-replay` expands to Primary4, not Gemma.

Current llama.cpp config has Gemma entries, but they are not the QAT Q4_0 model
that passed the bridge:

- `hpz2-l2-google-gemma-4-26b-a4b` points to Q8_0.
- `hpz2-l2-unsloth-gemma-4-26b-a4b-it` points to MXFP4_MOE.
- `hpz2-l2-gemma-4-31b-it` points to non-QAT 31B.

The later patch must add an explicit QAT label or a dedicated runner-local
descriptor for:

```text
label: hpz2-gemma4-26b-a4b-qat-q4_0
path: C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf
sha256: 9B96AA267521008235F8792590CB8E2DC47A8A236C6FF1767964CBBE32510873
```

Do not reuse the existing non-QAT Gemma labels as if they were the reviewed QAT
model.

## Recommended Candidate Lane

After a separate Main PC runner/config patch and HP pull/verify, run only:

```text
1 model x 4 C1 replay cases = 4 /explain calls
```

Model:

- `hpz2-gemma4-26b-a4b-qat-q4_0`

Cases:

- `smoke-09-bst`
- `RA-03-safety-boundary`
- `RA-06-dexisy-pediatric-nsaid-insurance`
- `RA-07-umk-uri-syrup-age-insurance`

Retrieval policy:

- Prefer `h2_c1_current_aug_top10_v0` for the first Gemma candidate replay,
  because the latest reviewed C1 top-10 artifact is the relevant comparator
  and reduces known reachability confounds.
- Treat top-10 retrieval as a diagnostic condition, not a pass criterion.

Do not include RA-04. It is a PHI early-return lane and must not call the model.

Do not run the full 17-case H2 matrix.

## Patch Shape

Preferred patch:

1. Add an explicit Gemma QAT C1 replay selector, for example:

   ```text
   --gemma26-c1-replay
   ```

2. The selector must require `--confirm-h2-c1-endpoint-replay`.

3. The selector must be mutually exclusive with `--primary4-c1-replay`.

4. Add the QAT model descriptor without promoting it into `PRIMARY_MODELS`.

5. Keep existing default C1 replay behavior unchanged.

6. Record QAT file length and SHA256 match in preflight, or add an equivalent
   explicit hash-check guard for this candidate lane.

7. Keep endpoint runner response storage policy unchanged: selected synthetic
   C1 replay response bodies and raw LLM JSON text may be stored only after PHI
   scan. Do not relay or quote raw response text in memory.

Alternative patch:

- Add a generic bounded `--c1-replay-model` selector only if it remains
  allowlist-based and cannot select arbitrary models outside the reviewed
  labels. A fully free-form model selector is too wide for this gate.

## Pass Criteria

The Gemma candidate replay is structurally acceptable only if all are true:

- HP `local-llm-eval` is clean/synced at the expected patch commit.
- Main PC `EMR_AI_24clinic` is clean at the expected endpoint baseline.
- HP ports `18080/18081` are free before run.
- No stale `llama-server` or shim process exists before run.
- QAT GGUF exists and SHA256 matches.
- llama.cpp health check passes.
- all 4 cells return HTTP 200.
- endpoint status is `ok` for all model-called cells.
- all model-called cells return valid C1 JSON.
- strict C1 schema passes.
- structural drift count is 0.
- PHI-like hit count is 0.
- final HP teardown proves no stale listener/process on `18080/18081`.

Manual lanes remain separate:

- `semantic`
- `grounding`
- `citation_claim`
- `safety`

Gemma may be considered for a later comparison only if there is no safety fail
and citation failures are classified by owner: retrieval reachability,
retrieved-but-not-cited, source-id fidelity, prompt/rubric, verifier, or model.

Do not call the result a model-ranking win from one 4-cell candidate replay.

## Stop Criteria

Stop before execution if:

- the pinned published bridge artifact cannot be read from
  `hpz2-run-artifacts` `origin/main` at
  `40e2a0e41793f1c9112ddd4bf587856e7778c5b4`.
- the patch reuses the wrong Gemma label or non-QAT model path.
- the runner would add Gemma to Primary4/default replay instead of a dedicated
  candidate selector.
- HP or Main PC worktrees are dirty outside approved paths.
- QAT hash/size cannot be verified.
- endpoint runner would store raw output for non-synthetic or PHI-like content.
- `--gemma26-c1-replay` can be combined with `--primary4-c1-replay`.
- any preflight finds stale runtime processes or occupied ports.

Stop after artifact review if:

- any PHI-like hit appears.
- any cell is reasoning-only, invalid JSON, strict-schema fail, or structural
  drift.
- safety manual lane fails.
- failures are aggregated as model quality without owner separation.

## Relationship To Existing C1 Evidence

The existing Qwen/Granite C1 evidence stays the comparator:

- C1 structural contract has been viable.
- Prior accept/promotion criteria were not met because citation-claim and
  evaluation-lane ownership remained unresolved.
- The top-10 retrieval-policy replay improved RA-03 reachability but did not
  close all RA-06/RA-07 citation-selection/manual-lane issues.

Therefore Gemma should be measured against the same C1 candidate lane, not used
to bypass the unresolved evaluation-lane work.

## Next Gates

If this plan is accepted, the next source gate is:

```text
Main PC local-llm-eval Gemma llama.cpp C1 endpoint-replay candidate plan review/commit GO
```

Then the implementation gate:

```text
Main PC local-llm-eval Gemma llama.cpp C1 endpoint-replay candidate runner patch GO
```

After commit/push and HP pull/verify, the execution gate:

```text
HP Z2 local-llm-eval Gemma llama.cpp C1 endpoint-replay candidate pilot GO
```

Librarian backup remains a separate batched maintenance gate.
