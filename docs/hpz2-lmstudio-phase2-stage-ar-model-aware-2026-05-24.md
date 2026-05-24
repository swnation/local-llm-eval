# HP Z2 LM Studio Phase 2 Stage A-R Model-Aware Config

Status: R0.1 config + runner patch
Date: 2026-05-24
Scope: `local-llm-eval` only. No model execution.

## Purpose

Stage A-R is a model-aware rerun lane for the HP Z2 LM Studio Phase 2 RAG eval.
It keeps the original Stage A strict endpoint baseline intact, then tests
whether model-specific integration settings improve structured RAG citation
behavior.

- Baseline config: `models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json`
- Model-aware config: `models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json`
- Runner: `tools/hpz2_lmstudio_phase2_stage_a_runner.py`
- Eval set: `prompts/rag_aware_eval_set_v0.1.json`

## What Changed

The runner now supports per-model `inference_options`:

- LM Studio JSON schema structured output.
- Model-specific sampling values.
- Qwen `/no_think` prompt suffixes for concise JSON RAG answers.
- gpt-oss reasoning effort hints in the system prompt.
- Gemma channel/tag cleanup for diagnostic output parsing.
- Failure reason buckets such as `json_parse_failed`, `schema_failed`,
  `malformed_citation`, `dropped_citation`, and
  `retrieval_expected_missing`.
- Corrected citation validity counting so empty-citation failures do not count
  as valid citations.

## Model Profiles

| model | profile | key settings |
|---|---|---|
| qwen3-14b | `qwen3-nonthinking-json-rag` | `/no_think`, JSON schema, temp 0.7, top_p 0.8, top_k 20 |
| qwen3-8b | `qwen3-nonthinking-json-rag` | `/no_think`, JSON schema, temp 0.7, top_p 0.8, top_k 20 |
| gpt-oss-20b | `gpt-oss-low-reasoning-structured-rag` | `Reasoning: low`, JSON schema, temp 0.0 |
| qwen3.6-35b-a3b | `qwen3.6-nonthinking-json-rag` | `/no_think`, JSON schema, temp 0.7, top_p 0.8, top_k 20 |
| granite-4.1-30b | `granite-rag-extraction-json` | JSON schema, temp 0.2, top_p 0.9 |
| gemma-4-31b | `gemma4-standard-json-rag` | JSON schema, temp 1.0, top_p 0.95, top_k 64 |
| gpt-oss-120b | `gpt-oss-medium-reasoning-structured-rag` | `Reasoning: medium`, JSON schema, temp 0.0 |

## Interpretation

Stage A remains the strict endpoint-readiness result. Stage A-R should be used
to answer a narrower question: whether each model can become viable when its
documented operating mode is respected.

If Stage A-R improves Qwen or Gemma, the production decision still needs a
separate integration decision because model-specific prompt/postprocess handling
would need to be made explicit in the app or runtime lane.

## Commands

Dry-run validation only:

```powershell
python tools\hpz2_lmstudio_phase2_stage_a_runner.py `
  --config models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --dry-run
```

Actual Stage A-R execution, HP Z2 only, after explicit GO:

```powershell
C:\github\.venvs\hpz2-phase2-emr-rag\Scripts\python.exe `
  tools\hpz2_lmstudio_phase2_stage_a_runner.py `
  --config models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json `
  --eval-set prompts\rag_aware_eval_set_v0.1.json `
  --server-url http://127.0.0.1:1234/v1 `
  --confirm-hpz2 `
  --confirm-heavy-run
```

## Hard Stops

- No EMR source/code writes.
- No commit/push from HP Z2.
- Do not treat Stage A-R as replacing Stage A. Compare both.
- Do not run Stage B, Stage C, or chunk variation without separate GO.
