# HP Z2 LM Studio Official Smoke Baseline

Status: R0 runbook
Date: 2026-05-24
Scope: HP Z2 + LM Studio/Vulkan model viability baseline only.

## Baseline Rule

The official execution baseline for this smoke matrix is:

- Host: HP Z2 Mini G1a
- Backend: LM Studio
- Runtime: llama.cpp Vulkan
- Server: `http://127.0.0.1:1234/v1`
- Load profile: `--gpu max --context-length 4096 --ttl 120 -y`
- Prompt: `prompts/hpz2_lmstudio_smoke_v0.1.json`
- Config: `models_config_hpz2_lmstudio_smoke_v0.1.json`

Main PC remains the canonical workspace for documentation, review, commit, and push. HP Z2 is the execution-only runner. Earlier 5080, subpc, Ollama, or manual one-off results are exploratory only and are not speed baselines for this matrix.

This is not RAG Phase 2 heavy eval. It does not call `EMR_AI_24clinic` and does not resolve RA-03 placeholders.

## Equal Candidates

All listed models are equal candidates for this smoke pass:

| Label | LM Studio model key |
|---|---|
| `hpz2-lms-qwen3-8b` | `qwen/qwen3-8b` |
| `hpz2-lms-qwen3-14b` | `qwen/qwen3-14b` |
| `hpz2-lms-gpt-oss-20b` | `openai/gpt-oss-20b` |
| `hpz2-lms-granite-4.1-30b` | `ibm/granite-4.1-30b` |
| `hpz2-lms-qwen3.6-35b-a3b` | `qwen/qwen3.6-35b-a3b` |
| `hpz2-lms-gemma-4-31b` | `google/gemma-4-31b` |
| `hpz2-lms-gpt-oss-120b` | `openai/gpt-oss-120b` |

## Command

Run this on HP Z2 only:

```powershell
cd C:\Github\local-llm-eval
python tools\hpz2_lmstudio_smoke_matrix.py `
  --config models_config_hpz2_lmstudio_smoke_v0.1.json `
  --prompts prompts\hpz2_lmstudio_smoke_v0.1.json `
  --server-url http://127.0.0.1:1234/v1 `
  --confirm-hpz2
```

Dry-run validation without model execution:

```powershell
python tools\hpz2_lmstudio_smoke_matrix.py `
  --config models_config_hpz2_lmstudio_smoke_v0.1.json `
  --prompts prompts\hpz2_lmstudio_smoke_v0.1.json `
  --dry-run
```

Run a subset if needed:

```powershell
python tools\hpz2_lmstudio_smoke_matrix.py `
  --config models_config_hpz2_lmstudio_smoke_v0.1.json `
  --prompts prompts\hpz2_lmstudio_smoke_v0.1.json `
  --models hpz2-lms-gpt-oss-120b hpz2-lms-qwen3.6-35b-a3b `
  --confirm-hpz2
```

## Output

The script writes:

- `results/hpz2_lmstudio_smoke_<timestamp>.json`
- `results/hpz2_lmstudio_smoke_<timestamp>.md`

Record these fields per model:

- estimate output
- load time
- API wall time
- completion tokens
- total tokens
- raw completion tok/s
- visible output
- error, if any

Raw tok/s is calculated as `completion_tokens / api_wall_s`. Models that spend many tokens on hidden or thinking output can show high raw tok/s while visible output remains short. Interpret raw throughput separately from visible response quality.

The runner appends `-y` to `lms load` and `lms load --estimate-only` through the config default `lms_cli_args`. This keeps the run non-interactive when LM Studio reports multiple matching model keys, such as `openai/gpt-oss-20b` versus `openai/gpt-oss-120b`.

## Stop Conditions

Stop and report instead of continuing if any of these happen:

- LM Studio server is not reachable.
- `lms status` fails.
- A model load fails with memory or Vulkan allocation errors.
- Visible output is empty after a successful API response.
- Any command would touch `EMR_AI_24clinic`.
- Any workflow starts RAG Phase 2 heavy eval.

## Next Step After Run

Paste the generated markdown table or JSON summary back into the main PC session. The main PC session should then decide whether to document the result, patch a Phase 2 LM Studio config, or keep a model in HOLD.
