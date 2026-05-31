---
id: h2-model-comparison-plan-2026-05-31
project: local-llm-eval
type: execution-plan
status: frozen-plan-pending-phase2-heavy-run-go
created: 2026-05-31
scope: H2 model-comparison plan only
---

# H2 Model-Comparison Plan

## Purpose

Select the next `/explain` model candidate from the locked Primary shortlist by
running the same 17-case RAG-aware eval set under one fixed endpoint condition.

This is a plan freeze only. It does not authorize `/explain`, HP runtime
startup, model execution, matrix execution, EMR writes, cleanup, downloads,
commit, or push.

## Fixed Baseline

- Eval set: `prompts/rag_aware_eval_set_v0.1.json` v0.2.1.
- Case count: 17 total.
- Model-call cases: 16 per model. RA-04 is a PHI early-return case and must not
  call the model.
- Expected model-backed cells: 4 models x 16 cases = 64. RA-04 may be
  exercised as a PHI guard lane, but it is excluded from model-backed latency
  and model-quality denominators because it must not reach the model.
- Structured-output mode: `json_object`.
- Strict-schema conformance metric remains live as a tripwire.
- Retrieval settings: `top_k=5`, `min_similarity=0.45`,
  `lexical_rerank=false`.
- Prompt/tone/EMR behavior: unchanged.
- Variable under test: model only.

The `json_object` mode is chosen from the R14 H2 schema-mode A/B result. This
choice is not proof that `json_object` is generally safe. It means only that
the 2-case x 2-Primary-model A/B showed no meaningful structural difference
between `json_object` and `json_schema`. H2 must still record strict-schema
conformance for every output.

## Model Scope

Run Primary 4 only:

1. `hpz2-l2-qwen36-35b-a3b`
2. `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`
3. `hpz2-l2-qwen36-35b-a3b-mtp-q8`
4. `hpz2-l2-granite-41-30b-q4km`

Reference or historical models are out of scope unless separately approved.
Do not add Qwen 122B, GPT-OSS 120B, Mistral Small 24B, Llama 70B, Gemma 31B,
EXAONE, Aya, or K-EXAONE variants to this H2 comparison without a separate
review and user GO.

## Case Scope

Use all 17 eval cases.

- Smoke carry: 10 cases.
- RAG-aware RA-01 through RA-07: 7 cases.
- RA-03 values remain locked:
  - orders: `sme`, `trimesy`, `lacto2`
  - dx: `a090`
  - pediatric age: `1`
- RA-04 is the PHI early-return case and must not make a model call. If the
  harness exercises RA-04, record it as a PHI guard check, not as model-quality
  evidence for a specific model.
- RA-06 and RA-07 are included, but their content-quality verdict remains
  provisional until user-owned expected-summary keyword spot-check is closed.
- RA-06 is kept as a hard case and tripwire for multi-citation behavior,
  `json_object` structural conformance, and strict-schema conformance.

Do not use RA-06 or RA-07 for final content-quality conclusions until their
expected-summary wording has been reviewed by the user. If the user chooses to
run before that spot-check, label content lanes for those cases as provisional.

## Metrics

Per model and per case, collect PHI-safe metadata only:

- HTTP status.
- EMR status.
- Valid JSON: yes/no.
- Strict schema conformance:
  - `summary` is a string.
  - `citations` is an array of strings.
  - no extra top-level keys.
- Structural drift: yes/no.
- Citation verifier pass/fail.
- Retrieved chunk count.
- Citation count.
- PHI hit count.
- Latency and wall time.
- Failure owner: infra / retrieval / schema / citation / PHI / content /
  unknown.
- Content/user-verdict lane status, including `provisional` where applicable.

Do not write raw model responses into relay or handoff reports. Report only
metadata, case IDs, and safe aggregate summaries.

## Decision Output

The H2 result packet should support one of these outcomes:

1. Recommend a Primary model for `/explain`.
2. Recommend a Primary model conditionally, with named caveats.
3. Decline to recommend a model because evidence is insufficient.

Do not select a model by latency alone. Citation correctness, schema
conformance, PHI safety, and content/user-verdict lanes must be considered
together.

## Pre-Run Recommendation

Recommended before `Phase 2 heavy run GO`:

- User spot-check RA-06 and RA-07 expected-summary keyword drafts.

This spot-check is recommended but not a hard prerequisite for freezing this
plan. If it is skipped before execution, H2 may still run, but RA-06/RA-07
content-quality verdicts must remain provisional.

## Execution Safety Envelope

Actual execution requires explicit `Phase 2 heavy run GO`.

Preflight before any run:

- Main PC `local-llm-eval` clean at the committed plan baseline or newer.
- HP `local-llm-eval` clean at the committed plan baseline or newer.
- Main PC and HP `EMR_AI_24clinic` clean at `c6dc30c` or newer, or else report
  the exact HEAD and confirm `/explain` app/llm contract files are unchanged.
- HP hostname `hpcheck` / `HPCHECK`.
- Ports `18080` and `18081` free before each runtime pair.
- No stale `llama-server` or shim process.
- Required GGUF file exists for the selected model.
- `C:` free space at least 100 GiB.
- Memory load below 92%.
- Use loopback-only bindings.
- Use SSH tunnel from Main PC to HP shim; prefer `test@192.168.68.50` if the
  `hpcheck` alias still has host-key drift.
- Use env override only; do not write `data/llm_settings.json`.
- Do not edit `C:\Github\EMR_AI_24clinic`.
- Do not use `scripts/smoke_test_explain.py`.
- Do not regenerate chunks or rebuild the RAG baseline.
- PHI hit count greater than zero is a hard STOP.
- Tear down each runtime pair and confirm ports `18080` and `18081` have no
  listener before moving to the next model.
- Do not kill user-owned desktop processes or revert files that the agent did
  not modify; STOP and report if user-caused dirty state blocks the run.

## STOP Conditions

Stop immediately and report if any of these occur:

- User did not issue explicit `Phase 2 heavy run GO`.
- Any repo required for the run is dirty for unexplained reasons.
- HP model file missing.
- C: free space below 100 GiB.
- Memory load at or above 92%.
- Stale runtime process or port conflict cannot be resolved inside the approved
  scope.
- `llama-server` or shim health check fails.
- Tunnel cannot be established.
- Any PHI hit count is greater than zero.
- RA-03 locked values drift.
- An unapproved model, schema mode, case set, top_k, min_similarity, prompt, or
  tone change is introduced.

## Next GO

Recommended sequence:

1. `H2 model-comparison plan review GO`
2. `H2 model-comparison plan commit + push GO`
3. HP `local-llm-eval` pull/verify to the committed plan baseline
4. Optional: `RA-06/RA-07 expected_summary_keywords spot-check GO`
5. `Phase 2 heavy run GO`

This plan freeze itself does not perform any of the above steps.
