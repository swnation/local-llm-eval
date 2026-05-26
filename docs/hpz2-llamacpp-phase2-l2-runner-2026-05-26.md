---
id: hpz2-llamacpp-phase2-l2-runner-2026-05-26
project: local-llm-eval
type: runbook
status: draft-built
created: 2026-05-26
scope: HP Z2 llama.cpp Phase 2 L2 synthetic semantic runner
related:
  - docs/hpz2-phase2-backend-lane-decision-2026-05-26.md
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
  - tools/hpz2_llamacpp_phase2_l2_runner.py
  - prompts/rag_aware_eval_set_v0.1.json
---

# HP Z2 llama.cpp Phase 2 L2 Runner

This runner is for L2 only: synthetic prompts over fixed evidence packs through
directly launched llama.cpp `llama-server.exe`. It does not call `/explain`,
does not import or write `EMR_AI_24clinic`, and records the real endpoint lane as
not run.

## Files

- Config: `models_config_hpz2_llamacpp_phase2_l2_v0.1.json`
- Runner: `tools/hpz2_llamacpp_phase2_l2_runner.py`
- Eval set: `prompts/rag_aware_eval_set_v0.1.json`
- Backend decision: `docs/hpz2-phase2-backend-lane-decision-2026-05-26.md`

## Dry Run

Dry-run validates config and eval-set consistency only:

```powershell
python tools\hpz2_llamacpp_phase2_l2_runner.py `
  --config models_config_hpz2_llamacpp_phase2_l2_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --dry-run
```

Expected dry-run behavior:

- no `llama-server` process;
- no model load;
- no LM Studio API request;
- no production app call;
- no `/explain`;
- no EMR write.

## Execution Gate

Real L2 execution is refused unless both confirmation flags are present:

```powershell
python tools\hpz2_llamacpp_phase2_l2_runner.py `
  --config models_config_hpz2_llamacpp_phase2_l2_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --tier primary_fast `
  --confirm-hpz2 `
  --confirm-l2-run
```

Default tier is `primary_fast`:

- `hpz2-l2-qwen36-35b-a3b`
- `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`

Other tiers are `primary_plus_reference`, `secondary_comparison`,
`family_baseline_optional`, and `all`.

## Runtime Policy

The primary HP Z2 llama.cpp profile is:

```powershell
-c 16384 -n 8192 `
-dev Vulkan0 -ngl all -sm none -mg 0 `
--no-mmap --no-host --kv-offload --op-offload -fa on `
-ctk q8_0 -ctv q8_0 `
--cache-ram 0 --no-cache-prompt --ctx-checkpoints 0 `
-b 1024 -ub 256 -np 1 --reasoning off
```

GPT-OSS models add `--skip-chat-parsing`. Conservative fallback is
`-b 256 -ub 64`.

## Pacing And STOP

Before real execution:

- verify hostname is the approved HP Z2 runner (`HPCHECK`);
- verify no stale `llama-server` process;
- verify LM Studio is Server ON / No Models Loaded if available;
- verify C: free space is at least 100 GiB;
- verify memory load is below the abort threshold.

Stop and report on:

- llama-server load failure;
- repeated non-2xx API errors;
- GPT-OSS parser error despite `--skip-chat-parsing`;
- memory load at or above 92%;
- free physical memory below 3 GiB;
- C: free below 100 GiB;
- stale server process after termination;
- RA-03 value drift;
- any `/explain` or EMR write path;
- invalid unknown or placeholder citations above the expected manual-review baseline.

## Output

By default, artifacts are written under:

```text
C:\github\hpz2-run-artifacts\results\llamacpp_phase2_l2_<timestamp>\
```

The artifact shape mirrors the LM Studio L2 summary enough for Main PC review:

- `full_matrix_results.json`
- `full_matrix_summary.md`
- per-model server stdout/stderr logs
- lane pass/fail fields
- citation integrity counts
- failure owner and manual-review fields
- memory and final state evidence
