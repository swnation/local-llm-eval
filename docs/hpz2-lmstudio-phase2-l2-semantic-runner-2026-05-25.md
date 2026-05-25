---
id: hpz2-lmstudio-phase2-l2-semantic-runner-2026-05-25
project: local-llm-eval
type: runbook
status: draft-built
created: 2026-05-25
scope: HP Z2 LM Studio Phase 2 L2 synthetic semantic smoke runner
related:
  - docs/rag_aware_eval_design_r0.md
  - docs/hpz2-phase2-ladder-progress-v0.1.md
  - prompts/rag_aware_eval_set_v0.1.json
  - models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json
  - tools/hpz2_lmstudio_phase2_l2_semantic_runner.py
---

# HP Z2 LM Studio Phase 2 L2 Semantic Runner

This runner is for L2 only: synthetic LM Studio prompts over fixed evidence
packs. It does not import `EMR_AI_24clinic`, does not call the production app,
and records the real endpoint lane as not run.

## Files

- Config: `models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json`
- Runner: `tools/hpz2_lmstudio_phase2_l2_semantic_runner.py`
- Eval set: `prompts/rag_aware_eval_set_v0.1.json`

## What It Validates

- R2 four-lane result fields:
  - `semantic_rag_lane`
  - `normalizer_lane`
  - `native_contract_lane`
  - `real_endpoint_lane`
- P7 placeholder rejection:
  - placeholder citations fail citation integrity;
  - placeholder summaries fail normalizer/native/semantic gates;
  - user-owned expected wording placeholders keep semantic verdict at
    `manual_review_needed`.
- Acceptable citation sets:
  - `required_all`
  - `core_any_of`
  - `strong_all`
  - `optional_hits`
  - `invalid_aliases`
- C1-C7 hook fields:
  - `claim_count`
  - `claim_grounded_count`
  - `claim_grounding_score`
  - `retrieval_precision_at_k`
  - `retrieval_recall_proxy`
  - `response_completeness`
  - `case_metric_profile`
  - `metric_risk_notes`

## Dry Run

Dry-run is allowed before HP Z2 execution because it only parses JSON and
validates config/spec consistency:

```powershell
python tools\hpz2_lmstudio_phase2_l2_semantic_runner.py `
  --config models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --dry-run
```

Expected dry-run behavior:

- no `lms` command;
- no model load;
- no LM Studio API request;
- no production app call;
- no EMR write.

## Execution Gate

Real L2 execution is still blocked until the user gives a separate HP Z2 GO.
The runner also refuses execution unless both confirmation flags are present:

```powershell
python tools\hpz2_lmstudio_phase2_l2_semantic_runner.py `
  --config models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --confirm-hpz2 `
  --confirm-l2-run
```

The recommended default tier is `l2_initial_6`. Other configured tiers are
`fast_daily`, `quality`, `reference`, `duplicate_review`, and `all`.

## Output

When executed on HP Z2 with a separate GO, artifacts are written under
`results/` with prefix `hpz2_lmstudio_phase2_l2_semantic`.

The HP Z2 artifact repo may then be used for transferring logs/results. The
Main PC remains canonical for documentation, commits, and pushes.
