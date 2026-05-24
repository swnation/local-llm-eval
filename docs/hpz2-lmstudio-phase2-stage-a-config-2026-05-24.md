# HP Z2 LM Studio Phase 2 Stage A Config

Status: R0.3 config + runner patch
Date: 2026-05-24
Scope: Config, runner, and runbook notes only. No model execution.

## Purpose

This patch adds the Phase 2 Stage A LM Studio configuration:

- Config: `models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json`
- Runner: `tools/hpz2_lmstudio_phase2_stage_a_runner.py`
- Eval set: `prompts/rag_aware_eval_set_v0.1.json`
- Execution host: HP Z2 Mini G1a
- Backend: LM Studio
- Runtime: llama.cpp Vulkan
- LM Studio server: `http://127.0.0.1:1234/v1`
- Load profile: `--gpu max --context-length 4096 --ttl 120 -y`

Related follow-up: `models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json`
adds a model-aware Stage A-R rerun lane. Stage A remains the strict endpoint
baseline; Stage A-R diagnoses whether model-specific structured output and
reasoning/no-thinking settings improve viability. Stage A-R uses the HP Z2
optimized `--context-length 32768` load policy; Stage A keeps `4096`.

Main PC remains the canonical workspace for review, documentation, commit, and push. HP Z2 remains execution-only.

## Stage A Cells

Stage A is model-axis only. It keeps:

- `top_k=5`
- `min_similarity=0.45`
- `lexical_rerank=false`
- Fix v3 prompt tone
- current Phase 1c RAG index

| Cell | Model label | LM Studio key | Role |
|---|---|---|---|
| `stageA-qwen3-14b-rag` | `hpz2-lms-qwen3-14b-rag` | `qwen/qwen3-14b` | primary small-dense RAG candidate |
| `stageA-qwen3-8b-rag` | `hpz2-lms-qwen3-8b-rag` | `qwen/qwen3-8b` | fallback / low-resource RAG candidate |
| `stageA-gpt-oss-20b-rag` | `hpz2-lms-gpt-oss-20b-rag` | `openai/gpt-oss-20b` | direct RAG endpoint comparison candidate |
| `stageA-qwen3.6-35b-a3b-rag` | `hpz2-lms-qwen3.6-35b-a3b-rag` | `qwen/qwen3.6-35b-a3b` | large challenger |
| `stageA-granite-4.1-30b-rag` | `hpz2-lms-granite-4.1-30b-rag` | `ibm/granite-4.1-30b` | secondary 30B comparison candidate added by user request |
| `stageA-gemma-4-31b-rag` | `hpz2-lms-gemma-4-31b-rag` | `google/gemma-4-31b` | secondary dense quality/safety wording comparison candidate added by user request |
| `stageA-gpt-oss-120b-rag` | `hpz2-lms-gpt-oss-120b-rag` | `openai/gpt-oss-120b` | large gpt-oss comparison candidate added by user request |

## Holds

No HP Z2 LM Studio smoke-pass model is currently held out of Stage A. `ibm/granite-4.1-30b`, `google/gemma-4-31b`, and `openai/gpt-oss-120b` were all moved into Stage A by user request on 2026-05-24.

Interpret the large-model results with load time tracked separately. The HP Z2 smoke baseline load time for `openai/gpt-oss-120b` was about 100.666s.

## Model Pacing

The future heavy-run runner should avoid rapid model switching:

- unload all models before each model
- unload all models after each model
- require `lms status` to show no loaded models before the next load
- wait at least 90 seconds after a successful unload before the next model
- wait at least 180 seconds after large models or any load/API failure
- wait at least 10 seconds after a successful load before the first `/explain` call

Large-model cooldown applies to:

- `hpz2-lms-qwen3.6-35b-a3b-rag`
- `hpz2-lms-gemma-4-31b-rag`
- `hpz2-lms-gpt-oss-120b-rag`

## Execution Gate

This config must not be used to run heavy eval until the user explicitly issues:

```text
Phase 2 heavy run GO
```

This config patch did not:

- run models
- call `/explain`
- write to `EMR_AI_24clinic`
- commit
- push
- enter Stage B, Stage C, chunk variation, or Phase 1d

## Commands

Dry-run validation only:

```powershell
python tools\hpz2_lmstudio_phase2_stage_a_runner.py `
  --config models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --dry-run
```

Actual Stage A execution, HP Z2 only, after explicit `Phase 2 heavy run GO`:

```powershell
python tools\hpz2_lmstudio_phase2_stage_a_runner.py `
  --config models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --server-url http://127.0.0.1:1234/v1 `
  --confirm-hpz2 `
  --confirm-heavy-run
```

The runner imports `EMR_AI_24clinic` read-only and patches only the in-process `generate_llm` callable so `/explain` uses LM Studio chat completions. It does not save LLM settings and does not modify the EMR repo.

## Runner Notes

The future heavy-run runner must load each LM Studio model with the `served_model_id` from the config so the `/explain` app calls the same identifier. The runner must also point the app's LLM backend to LM Studio `http://127.0.0.1:1234/v1`.

The runner writes ignored local artifacts under `results/`:

- `results/hpz2_lmstudio_phase2_stage_a_<timestamp>.json`
- `results/hpz2_lmstudio_phase2_stage_a_<timestamp>.md`
