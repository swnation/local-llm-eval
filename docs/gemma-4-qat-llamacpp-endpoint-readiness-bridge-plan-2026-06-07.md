---
id: gemma-4-qat-llamacpp-endpoint-readiness-bridge-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: Main PC bridge plan after Gemma 4 26B A4B QAT direct llama.cpp output-contract pilot
related:
  - docs/gemma-4-qat-llamacpp-output-contract-runner-plan-2026-06-07.md
  - tools/hpz2_llamacpp_gemma_output_contract_pilot.py
  - tests/test_hpz2_llamacpp_gemma_output_contract_pilot.py
  - docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - prompts/rag_aware_eval_set_v0.1.json
  - hpz2-run-artifacts: results/gemma_llamacpp_output_contract_pilot_20260607_152418/
---

# Gemma llama.cpp Endpoint-Readiness Bridge Plan

## Project Goal Check

- direct value: convert the successful Gemma 4 26B A4B QAT native
  output-contract pilot into a bounded endpoint-readiness decision path without
  prematurely entering `/explain`, Primary4 replay, or model ranking.
- classification: `direct progress` with evaluation-safety value.
- narrower scope: document-only plan. No code patch, HP command, model load,
  prompt/API call, `/explain`, endpoint replay, EMR write/reindex, artifact
  mutation, relay update, backup, commit, or push is authorized by this file.

## Decision

The 26B A4B QAT direct llama.cpp pilot is sufficient to close the native
output-contract gate for this model.

It is not sufficient to declare endpoint readiness.

Bridge decision:

```text
Gemma 4 26B A4B QAT Q4_0 may enter a narrow endpoint-readiness bridge lane.
It must not enter Primary4 endpoint replay, model ranking, or production-like
`/explain` evaluation until the bridge lane passes.
```

## Evidence Consumed

Source repo:

```text
local-llm-eval@80d0201d4edc4039bd460c233b9850b1d30ecf8d
fix(rag): avoid Gemma runner shim self-match
```

Artifact repo:

```text
hpz2-run-artifacts@75ecfc32037ac53e07107dc1d5ac4717836e30ee
results/gemma_llamacpp_output_contract_pilot_20260607_152418/
```

Reviewed metadata:

- backend: direct llama.cpp `/v1/chat/completions`.
- model: `hpz2-gemma4-26b-a4b-qat-q4_0`.
- prompt/data: one synthetic non-PHI output-contract prompt.
- stopped early: false.
- raw model output stored: false.
- endpoint readiness assessed: false.
- G1 final-answer control: API ok, content channel, PASS, reasoning chars 0.
- G2 JSON schema native contract: API ok, content channel, parsed JSON, exact
  synthetic citation, PASS, reasoning chars 0.
- PHI-like hits: 0.
- preflight and final preflight: ports/processes clear, LM Studio had no model
  loaded, model file hash matched.

Important caveat:

- `server_exit_code=1` appears after shutdown, while final preflight is clean.
  Treat this as a runner lifecycle interpretation follow-up, not a blocker for
  this metadata-only pilot. Do not reuse it as proof of clean process semantics
  until the runner records expected shutdown exit behavior explicitly.

## User Scope Update

The HP-side larger-model experiments are a separate lane.

This bridge plan must not absorb, block, or reinterpret:

- 31B QAT reference testing.
- larger Gemma variants.
- Qwen/GPT-OSS/Granite/other large-model experiments.
- Step-3.7 or other large-MoE feasibility work.

If those runs produce useful evidence, they should enter through their own HP
artifact publish and review gates, not by widening this 26B endpoint-readiness
bridge.

## What This Plan Does Not Claim

This plan does not claim:

- endpoint readiness.
- `/explain` readiness.
- clinical semantic quality.
- final citation-grounding quality.
- model ranking.
- Primary4 promotion.
- H2/C1 replay acceptance.
- that 31B or larger models are worse or unnecessary.

The only positive claim is narrower:

```text
Gemma 4 26B A4B QAT can produce clean final content and strict native JSON
under direct llama.cpp for the synthetic output-contract prompt.
```

## Bridge Lane Shape

The bridge lane should answer one question:

```text
Can the 26B A4B QAT model keep the same output-contract behavior when the
prompt shape becomes closer to the C1 `/explain` harness, while still avoiding
real endpoint execution?
```

Recommended sequence:

1. **Bridge Plan Review**

   Review this document and decide the exact bridge surface.

2. **Bridge Runner Patch**

   Add a synthetic C1-shaped bridge runner or mode. It may reuse the existing
   output-contract runner if that keeps the code smaller.

   The runner should still call direct llama.cpp
   `/v1/chat/completions`, not LM Studio, not the shim, and not `/explain`.

3. **HP Bridge Pull/Verify**

   HP pulls the bridge patch and runs only static checks/dry-run first.

4. **HP Bridge Pilot**

   One model, one or two C1-shaped synthetic cases, metadata-only artifact.

5. **Artifact Publish And Review**

   Publish only the bridge artifact directory from a clean temp worktree, then
   Main PC reviews lanes separately.

Only after all bridge checks pass should the project consider a later
C1 endpoint-replay candidate plan.

## Proposed Bridge Cases

Use synthetic/non-PHI data only.

Case `GB1-final-answer-c1-shape`:

- Uses a C1-like instruction structure: short clinical-explanation style,
  explicit "do not infer beyond evidence", exact source ID requirement.
- Expected output: final assistant content only.
- No JSON schema required.
- Pass requires content channel, no reasoning channel, PHI-like hits 0, and no
  raw output storage.

Case `GB2-json-schema-c1-shape`:

- Uses the same synthetic evidence but requests the current explain-style JSON
  object shape.
- Response format should use llama.cpp `json_schema` if the bridge runner keeps
  native schema mode.
- Expected fields should mirror endpoint contract shape only as far as needed
  for structure, not clinical meaning.

Minimum expected object:

```json
{
  "summary": "string",
  "citations": ["[kb:DEMO_GEMMA_BRIDGE:001]"]
}
```

Optional extension, only if it matches existing endpoint replay diagnostics
without adding complexity:

```json
{
  "summary": "string",
  "citations": ["[kb:DEMO_GEMMA_BRIDGE:001]"],
  "safety_notes": ["string"]
}
```

Do not use real RA-03, RA-06, RA-07, patient-like identifiers, or production
RAG chunks in this bridge gate.

## Pass Criteria

Bridge pilot passes only if all are true:

- preflight finds HP repo clean/synced at expected commit.
- preflight finds ports 18080/18081 free.
- preflight finds no stale `llama-server`, shim, or loaded LM Studio model.
- QAT GGUF file exists and SHA256 matches.
- llama.cpp accepts the required runtime args.
- health check is ok before calls.
- every bridge call returns API ok.
- final content channel is non-empty.
- reasoning chars are 0 or absent.
- JSON case parses as a single JSON object without markdown-fence stripping.
- expected synthetic citation is exact.
- PHI-like hits are 0.
- raw model output body is not stored.
- final preflight shows ports/processes clear.

## Stop Criteria

Stop and report `NO-GO` before any endpoint replay if:

- any bridge call is reasoning-only.
- reasoning appears together with final content.
- JSON output requires markdown-fence stripping or embedded JSON extraction.
- exact synthetic citation is missing.
- any PHI-like hit appears.
- token-loop or whitespace-only output appears.
- llama.cpp rejects runtime args or fails health.
- final preflight finds stale process or occupied 18080/18081.
- runner lifecycle cannot distinguish expected shutdown from failure after a
  successful call.

## Runner Follow-Up

Before HP bridge pilot, consider a small runner hardening patch:

- record whether `server_exit_code=1` is expected after controlled termination
  on Windows llama.cpp.
- separate `server_exit_code` from `teardown_status`.
- make final preflight the decisive process-cleanliness signal, but surface
  unexpected exit codes as `WARN`, not silent metadata.

This is useful but should stay scoped to lifecycle reporting. It should not
change the output-contract scoring result.

## Artifact Policy

The bridge artifact should store metadata only:

- model label and source commit.
- GGUF path, size, SHA256 match.
- runtime args.
- response-format lane.
- HTTP/API status.
- content char count.
- reasoning char count.
- JSON parse status.
- exact citation match status.
- PHI-like hit count.
- pass/fail and failure owner.
- preflight/final preflight process and port summary.

Do not store raw model output bodies by default.

## Review Decision Surface

After a bridge pilot, review lanes separately:

| Lane | Possible verdict |
|---|---|
| Native output contract | PASS / WARN / FAIL |
| C1-shaped prompt compatibility | PASS / WARN / FAIL |
| Runtime lifecycle | PASS / WARN / FAIL |
| Endpoint readiness | NOT ASSESSED unless `/explain` is actually called |
| Model ranking | NOT ASSESSED |

If the bridge passes, the next plan may be:

```text
Main PC local-llm-eval Gemma llama.cpp C1 endpoint-replay candidate plan GO
```

That later plan should decide whether Gemma 26B enters a tiny C1 replay next to
existing C1 candidates, and it should keep `/explain` execution as a separate
HP GO.

## Recommended Next GO

Recommended next gate:

```text
Main PC local-llm-eval Gemma llama.cpp endpoint-readiness bridge plan review/commit GO
```

Then, only if the plan is accepted:

```text
Main PC local-llm-eval Gemma llama.cpp endpoint-readiness bridge runner patch GO
```

HP larger-model runs remain separate and should use their own GO phrases.
