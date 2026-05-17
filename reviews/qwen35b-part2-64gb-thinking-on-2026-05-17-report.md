# Qwen3.6-35B-A3B 64GB Part 2 — thinking-on Report

Date: 2026-05-17
Round label: `part2_64gb_defaultkv_thinking_on`
Status: **D smoke FAIL — full 13 held**

## Setup

| Field | Spec | Actual observed |
|---|---|---|
| Model | `qwen3.6:35b-a3b` | `qwen3.6:35b-a3b` (Ollama list, 23 GB) |
| Provider | Ollama OpenAI-compatible API | confirmed via `base_url: http://localhost:11434/v1` in raw |
| Quant / size | Q4_K_M / 23 GB | same |
| Reasoning mode | `reasoning_effort='medium'` (thinking-on) | inference_options `{reasoning_effort: medium}` in raw |
| KV cache type | default / f16-equivalent (per config `_runtime_metadata.kv_cache_type`) | **not directly observed** — `OLLAMA_KV_CACHE_TYPE` env var unset (good) but Ollama log not captured this round |
| Flash attention | default (per config) | **not directly observed** — `OLLAMA_FLASH_ATTENTION` env var unset |
| num_ctx | default (per config — no override in `inference_options`) | **not directly observed** |
| max output tokens | not explicitly set in config | runtime cap appears to be 2048 (D_01/D_03 both stopped at exactly `completion_tokens: 2048`) |
| Config | `models_config_qwen35b_thinking_on_64gb.json` | same |
| Prompt set (D smoke) | `prompts/test_suite_v0.3_d_only.json` | same |
| Scorer | `score_runner.py` / `SCORING_CONTRACT.md` v0.3 | same |
| RAM context | post-64GB upgrade, first part-2 run | same |
| Pre-check env vars | both unset | confirmed both empty |
| Pre-check `ollama ps` | empty | confirmed empty |

## Commands

```powershell
python eval_runner_auto.py --config models_config_qwen35b_thinking_on_64gb.json --prompts prompts/test_suite_v0.3_d_only.json
python score_runner.py --prompts prompts/test_suite_v0.3_d_only.json --results-glob "results/qwen3.6-35b-a3b-64gb-thinking-on_20260517_235616.json" --output results/_scored_part2_64gb_qwen35b_thinking_on_dsmoke_20260517
```

Raw artifact used (exact paths):
- Raw: `results/qwen3.6-35b-a3b-64gb-thinking-on_20260517_235616.json`
- Markdown: `results/qwen3.6-35b-a3b-64gb-thinking-on_20260517_235616.md`
- Scored: `results/_scored_part2_64gb_qwen35b_thinking_on_dsmoke_20260517.{json,md}`

Full 13 was **not executed** (held per spec — D smoke failed PASS gate).

## D Smoke Results

| Prompt | Score | HardFail | Tags | completion_tokens | elapsed_s | tok/s | Notes |
|---|---:|---|---|---:|---:|---:|---|
| D_01 | 0 | **YES** | `EMPTY_RESPONSE` | 2048 | 158.5 | 12.9 | Hit output-token cap; visible response empty (reasoning trace consumed entire budget, no JSON emitted) |
| D_02 | 5 | no | — | 1797 | 127.7 | 14.1 | Clean JSON, schema pass, no PHI leak. Under token cap. |
| D_03 | 0 | **YES** | `EMPTY_RESPONSE` | 2048 | 143.1 | 14.3 | Hit output-token cap; visible response empty (same pattern as D_01) |

D_json_phi average: **1.67** (gate required ≥ 4.00). Hard-fails: **2 of 3**.

## Verdict

**D smoke FAIL.** PASS gate required all three D prompts hard_fail=false and D avg ≥ 4.00. The actual outcome violates both clauses: D_01 and D_03 returned empty visible bodies, tagged `EMPTY_RESPONSE`, and the D average is 1.67.

Per spec, full 13 round is held; thinking-on is recorded as carrying a D-category automation risk on the 64GB default-context runtime.

## Raw Spot Check

Items checked: prose around JSON, ```` ```json ```` fences, unclosed `<think>` blocks, reasoning trace leak into body, mid-sentence truncation, missing EOT.

| Prompt | Finding |
|---|---|
| D_01 | `response` field is empty string. `completion_tokens` == 2048 (round value strongly suggests hitting the output cap, not natural EOT). No `<think>` block visible in the body — the harness/transport stripped reasoning, but the model never emitted any user-facing JSON before being cut off. |
| D_02 | Body is a clean JSON object. No markdown fence, no prose, no reasoning leak. JSON parse succeeds. One nit: spec asks for `items` covering all input findings; model emitted only 1 item (covering the most severe finding) — scorer's D_02 schema accepted this and gave 5, with PHI substring check clean. |
| D_03 | Same pattern as D_01: empty body, `completion_tokens` == 2048. |

Pattern interpretation:
- D_01 input has the largest schema (3 items × 5 required keys including `recommended_check`) and D_03 has the strictest schema (allowed-keys-only with 2 reviews × 3 keys). Both demand more reasoning content before the JSON can be assembled.
- D_02 has a smaller schema and finished under the cap.
- Thinking-on at `medium` is generating long Korean reasoning traces that exhaust the implicit ~2048-token output budget before the visible JSON is written.
- This mirrors the §5.7 lesson on gpt-oss medium (D_02 `JSON_EXTRA_TEXT` from fence leakage) but here the failure mode is **truncation**, not fence leak.

## Comparison Tables

### Qwen 64GB thinking-on (D smoke only) vs prior v0.3 baselines

| Run | Scope | A | B | C | D | Total avg | HardFail# | Source |
|---|---|---:|---:|---:|---:|---:|---:|---|
| gpt-oss dynamic v0.3 (production candidate) | full 13 | 2.75 | 2.33 | 3.33 | 5.00 | 3.31 | 0 | §6 |
| Qwen 32GB thinking-off v0.3 rescore | full 13 | 2.50 | 3.33 | 3.00 | 5.00 | 3.38 | 0 | preview report 2026-05-16 |
| **Qwen 64GB thinking-on (this round)** | **D smoke only** | n/a | n/a | n/a | **1.67** | n/a | **2** | this report |

A/B/C are unevaluated in this round (full 13 held). C improvement vs thinking-off (the core hypothesis) is **not measurable** because the D gate blocked the full run. **D safety is broken**, which is the dispositive result.

## Production Candidate Impact (§6)

- `gpt-oss-20b + dynamic reasoning_effort` (scenario C) remains the provisional production candidate. Qwen thinking-on does not displace it.
- Qwen 32GB thinking-off (3.38 HF0) remains the credible challenger; this round adds **no new evidence** in its favor and **subtracts** confidence in any "thinking-on by default" variant.
- §6 update recommendation: keep current candidate; add a note that thinking-on at default num_ctx/output-cap fails the D gate via truncation.

## Follow-Up Hypotheses (not actioned this round)

In priority order, for the next part-2 round:

1. **Dynamic policy for Qwen** (mirrors gpt-oss §5.7 pattern): `C/A/B = thinking-on`, `D = thinking-off`. Cleanest fix because D is exactly where thinking-on is unsafe.
2. **num_ctx + max output tokens uplift** for thinking-on D: try `num_ctx=8192` and an explicit larger output cap (e.g. 4096) in a separate labeled round. Keeps thinking-on as a single-policy candidate but spends VRAM/latency. Hold for after option 1, since option 1 already solves the gate.
3. **Lower `reasoning_effort`** (e.g. `low` instead of `medium`) for D only, if option 1 is undesirable for harness-simplicity reasons.

This round itself does **not** retry — fair-compare protocol holds default-ctx for the planned baseline.

## Notes for Next Session

- Holding `num_ctx` at default for this round preserved the apples-to-apples comparison surface with the 32GB thinking-off preview; that decision is intact.
- The D failure is a **truncation** signal, not a content/safety signal. The model is not leaking PHI, not emitting prose-around-JSON, not opening unclosed think blocks in the visible body — it simply never emits the JSON because its budget runs out inside the hidden trace.
- Track 2 (q8 KV / num_ctx tuning) is the natural home for the follow-up rounds.

## End of Report
