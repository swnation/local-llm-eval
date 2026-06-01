---
id: h2-c1-endpoint-hypothesis-replay-design-2026-06-02
project: local-llm-eval
type: design
status: design-and-runner-patch-ready
created: 2026-06-02
scope: H2 C1 endpoint-hypothesis replay design
related:
  - docs/h2-output-contract-primary4-expansion-review-2026-06-02.md
  - docs/h2-manual-vs-endpoint-prompt-delta-audit-2026-06-01.md
  - docs/h2-content-citation-failure-review-2026-06-01.md
  - docs/hpz2-llamacpp-h2-endpoint-runner-2026-06-01.md
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
---

# H2 C1 Endpoint-Hypothesis Replay Design

## Purpose

The output-contract calibration now supports C1 as the endpoint-native contract
hypothesis across Primary4. The next question is narrower:

```text
Can the current /explain endpoint preserve C1 structure and semantic safety
boundaries when the model is run through retrieval, endpoint prompt, shim, and
verifier policy?
```

This is an endpoint-hypothesis replay design. It is not an execution result.

## Inputs

- Pilot artifact: `h2_output_contract_calibration_20260602_012006`
- Primary4 expansion artifact: `h2_output_contract_calibration_20260602_022031`
- Endpoint failure review: `docs/h2-content-citation-failure-review-2026-06-01.md`
- Prompt delta audit:
  `docs/h2-manual-vs-endpoint-prompt-delta-audit-2026-06-01.md`
- Existing endpoint runner:
  `tools/hpz2_llamacpp_h2_endpoint_runner.py`

## Design Decision

Use C1 as the only output-contract hypothesis for endpoint replay.

Do not re-test C2, C3, or C4 in the endpoint lane yet. C2/C3 are backup
normalizer-path contracts, and C4 is not endpoint-native.

## Replay Matrix

Start with a narrow 8-call pilot:

```text
2 models x 4 cases = 8 /explain calls
```

Pilot models:

- `hpz2-l2-qwen36-35b-a3b`
- `hpz2-l2-granite-41-30b-q4km`

Pilot cases:

- `smoke-09-bst`
- `RA-03-safety-boundary`
- `RA-06`
- `RA-07`

Expansion, only after the 8-call pilot is reviewed:

```text
4 Primary4 models x 4 cases = 16 /explain calls
```

Do not run the full 17-case H2 matrix in this gate. The goal is to test the C1
endpoint hypothesis and prompt/retrieval confounds, not to rank models broadly.

## Fixed Runtime Controls

- Schema mode: existing H2 `json_object`
- Output contract: current endpoint C1 shape only:
  - top-level keys exactly `summary` and `citations`
  - `summary` is a Korean string
  - `citations` is an array of bracketed source IDs
- Retrieval settings: keep the same H2 settings unless a separate retrieval
  design gate changes them.
- Endpoint path: `/explain`
- Runtime topology: HP Z2 llama.cpp + shim, Main PC endpoint harness.
- No EMR writes.
- No `data/llm_settings.json` writes.
- No production prompt change in the replay gate.

## Runner Patch

The endpoint runner now has a separate replay mode:

```text
--confirm-h2-c1-endpoint-replay
```

Implemented behavior:

- default replay models are Qwen official + Granite;
- optional `--primary4-c1-replay` expands to all Primary4 models;
- replay cases are restricted to the four-case list above;
- output is written under `h2_c1_endpoint_replay_<timestamp>`;
- endpoint response bodies and raw LLM texts are stored only after PHI scan;
- response artifact paths are recorded per cell;
- retrieved source IDs and expected source misses are retained;
- final HP teardown evidence remains part of the normal runner output.

The patch must not change `EMR_AI_24clinic` production code.

## Manual Review Lanes

For each cell, fill these lanes after artifact generation:

- `semantic_pass`
- `grounding_pass`
- `citation_claim_pass`
- `safety_pass`

Do not use literal keyword matching as the only semantic verdict. Keyword hits
can be supporting evidence, but the manual verdict must account for prompt
delta, retrieved-source availability, and safety-boundary preservation.

## Pass Criteria

Endpoint C1 replay is acceptable for the narrow pilot if all are true:

- HTTP 200 and endpoint `ok` for all model-called cells.
- Valid C1 JSON shape for all model-called cells.
- No PHI-like hits in stored synthetic responses.
- No stale HP runtime processes or occupied ports after teardown.
- At least 3/4 pilot cases pass manual semantic, grounding, citation-claim, and
  safety lanes for each pilot model.
- Any safety-boundary case failure is explained by retrieved-source absence,
  prompt contradiction, or model wording, not left as an undiagnosed aggregate
  failure.

If C1 shape passes but semantic/safety lanes fail, do not return to larger
model ranking. Fix endpoint prompt/retrieval/rubric first.

## Stop Conditions

Stop before model execution if any of these are true:

- dirty `EMR_AI_24clinic`;
- unapproved dirty `local-llm-eval`;
- missing HP model file;
- stale HP `llama-server` or shim process;
- occupied HP `18080` or `18081`;
- HP C: free space below 100 GiB;
- HP memory load at or above 92%;
- raw-response storage is enabled for non-synthetic or PHI-like content;
- runner cannot prove teardown after a model pair.

## Next GO

Next execution-prep gate:

```text
local-llm-eval C1 replay runner review/pull GO
```

After commit/push, HP pull/verify, and an explicit HP execution GO, run the
8-call endpoint replay pilot.
