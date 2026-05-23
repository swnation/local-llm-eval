# HP Z2 LM Studio Smoke Results

Status: R0 result capture
Date: 2026-05-24
Source: HP Z2 execution summary pasted into main PC session
Scope: Official HP Z2 + LM Studio/Vulkan light smoke only

## Verdict

The official HP Z2 LM Studio/Vulkan smoke baseline completed successfully.

- Official execution host: HP Z2 Mini G1a
- Canonical workspace: main PC `C:\Github\local-llm-eval`
- HP repo HEAD during run: `164491536c572b7b8f902235bcf2bad0caed76ac`
- HP repo status after run: `main...origin/main` clean
- Backend: LM Studio
- Runtime: llama.cpp Vulkan
- Server: `http://127.0.0.1:1234/v1`
- Load profile: `--gpu max --context-length 4096 --ttl 120`
- Prompt: `prompts/hpz2_lmstudio_smoke_v0.1.json`

No RAG Phase 2 heavy eval was run. No `EMR_AI_24clinic` write, commit, or push occurred. LM Studio ended with `No Models Loaded`.

## Result Artifacts

Primary HP artifacts:

- `results/hpz2_lmstudio_smoke_20260524_015214.md`
- `results/hpz2_lmstudio_smoke_20260524_015214.json`

Additional `gpt-oss-20b` successful retry artifact:

- `results/hpz2_lmstudio_smoke_gpt_oss_20b_retry_20260524_021058.md`
- `results/hpz2_lmstudio_smoke_gpt_oss_20b_retry_20260524_021058.json`

Excluded diagnostic artifact:

- `results/hpz2_lmstudio_smoke_gpt_oss_20b_retry_20260524_021017.*`
- Reason: exact variant key diagnostic failure only. Do not use for baseline reporting.

## Official Baseline Table

`gpt-oss-20b` uses the successful retry value from `021058`; all other rows use the primary matrix artifact from `015214`.

| Model | Status | Load s | API wall s | Raw tok/s | Tokens | Visible output | Source |
|---|---:|---:|---:|---:|---:|---|---|
| `hpz2-lms-qwen3-8b` | PASS | 4.452 | 3.035 | 39.866 | 121/169 | `OK, understood.` | primary matrix |
| `hpz2-lms-qwen3-14b` | PASS | 6.981 | 0.417 | 16.770 | 7/55 | `OK.` | primary matrix |
| `hpz2-lms-gpt-oss-20b` | PASS | 9.437 | 1.149 | 17.406 | 20/129 | `OK.` | retry `021058` |
| `hpz2-lms-granite-4.1-30b` | PASS | 12.246 | 0.419 | 4.772 | 2/50 | `OK` | primary matrix |
| `hpz2-lms-qwen3.6-35b-a3b` | PASS | 18.358 | 3.227 | 63.841 | 206/256 | `OK.` | primary matrix |
| `hpz2-lms-gemma-4-31b` | PASS | 16.184 | 13.105 | 10.530 | 138/189 | `OK.` | primary matrix |
| `hpz2-lms-gpt-oss-120b` | PASS | 100.666 | 1.697 | 11.197 | 19/128 | `OK.` | primary matrix |

Raw tok/s is `completion_tokens / API wall seconds`. It is not the same as user-visible speed when a model spends completion tokens on hidden or thinking output.

## Backend Interpretation

`gpt-oss-120b` is viable on the HP Z2 LM Studio/Vulkan lane. This is a backend-specific result and should not be conflated with the earlier Ollama/ROCm failure. The same model can fail in one backend and pass in another because memory allocation and GPU runtime paths differ.

`qwen3.6-35b-a3b` and `gemma-4-31b` both passed, but their token counts are larger than the visible response suggests. Treat these rows as possibly affected by hidden or thinking token overhead. For later clinical/RAG eval interpretation, visible output quality and raw completion throughput should be reviewed separately.

`qwen3-14b` remains the light practical baseline candidate. `gpt-oss-120b` is now a large-model comparison candidate for the LM Studio/Vulkan lane, subject to load-time tolerance.

## gpt-oss-20b Ambiguity

In the primary matrix, `hpz2-lms-gpt-oss-20b` failed before load/API because the estimate stage returned:

```text
Multiple models match the provided model key. Please select one.
```

This is not a model viability failure. The successful retry used:

```text
load key: openai/gpt-oss-20b
load profile: --gpu max --context-length 4096 --ttl 120 -y
```

The retry result is adopted as the official `gpt-oss-20b` smoke value for this baseline.

## Follow-Up Items

1. Patch `tools/hpz2_lmstudio_smoke_matrix.py` so `lms load` and `lms load --estimate-only` can run non-interactively when LM Studio reports multiple matching model keys. Status: resolved in local follow-up by adding configurable `lms_cli_args` and setting the HP Z2 smoke config default to `["-y"]`.
2. Add a Phase 2 LM Studio config only after the smoke runner ambiguity is fixed.
3. Keep RAG Phase 2 heavy run blocked until RA-03 input codes and expected citations are user-confirmed.
4. Keep HP Z2 as execution-only runner and main PC as canonical docs/commit/push workspace unless the user changes that rule.

## Stop Carry

- RAG Phase 2 heavy eval: not run
- `EMR_AI_24clinic` write: none
- commit/push from HP: none
- Phase 1d: not entered
- RA-03 placeholder inference: none
