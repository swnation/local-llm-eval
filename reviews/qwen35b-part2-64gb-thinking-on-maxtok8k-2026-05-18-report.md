# Qwen3.6-35B-A3B 64GB Part 2 — thinking-on maxtok8k Diagnostic Report

Date: 2026-05-18
Round label: `part2_64gb_diagnostic_maxtok8k_thinking_on`
Status: **D smoke PASS → Full 13 PASS — diagnostic round (not directly comparable to 2048-cap baselines)**

> Default 2048-cap thinking-on D smoke failed by output budget exhaustion, not JSON fence/reasoning trace leak.
> A separate maxtok8k diagnostic round was run to test whether Qwen thinking-on can complete D JSON under sufficient output budget.

## Setup

| Field | Spec | Actual observed |
|---|---|---|
| Model | `qwen3.6:35b-a3b` | `qwen3.6:35b-a3b` (Ollama list, 23 GB) |
| Provider | Ollama OpenAI-compatible API | confirmed via `base_url: http://localhost:11434/v1` in raw |
| Quant / size | Q4_K_M / 23 GB | same |
| Reasoning mode | `reasoning_effort='medium'` (thinking-on) | inference_options `{reasoning_effort: medium, max_tokens: 8192}` in raw |
| KV cache type | default / f16-equivalent (intended spec) | **not directly observed** — `OLLAMA_KV_CACHE_TYPE` env var unset (good) but Ollama log not captured this round |
| Flash attention | default | **not directly observed** — `OLLAMA_FLASH_ATTENTION` env var unset |
| num_ctx | default (no override in `inference_options`) | **not directly observed** |
| max output tokens | **8192** (override via `inference_options.max_tokens`) | confirmed via raw `inference_options`; per-prompt observed max was 4449 (A_02), no prompt hit the 8192 cap |
| Config | `models_config_qwen35b_thinking_on_64gb_maxtokens8k.json` | same |
| Prompt set (D smoke) | `prompts/test_suite_v0.3_d_only.json` | same |
| Prompt set (full 13) | `prompts/test_suite_v0.3.json` | same |
| Scorer | `score_runner.py` / `SCORING_CONTRACT.md` v0.3 | same |
| Pre-check env vars | both unset | confirmed both empty |
| Pre-check `ollama ps` | empty | confirmed empty |
| Pre-check `git log` | latest commit `71c9341` | confirmed |

## Commands

```powershell
# D smoke
python eval_runner_auto.py --config models_config_qwen35b_thinking_on_64gb_maxtokens8k.json --prompts prompts/test_suite_v0.3_d_only.json
python score_runner.py --prompts prompts/test_suite_v0.3_d_only.json --results-glob "results/qwen3.6-35b-a3b-64gb-thinking-on-maxtok8k_20260518_003642.json" --output results/_scored_part2_64gb_qwen35b_thinking_on_maxtok8k_dsmoke_20260518

# Full 13
python eval_runner_auto.py --config models_config_qwen35b_thinking_on_64gb_maxtokens8k.json --prompts prompts/test_suite_v0.3.json
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/qwen3.6-35b-a3b-64gb-thinking-on-maxtok8k_20260518_011459.json" --output results/_scored_part2_64gb_qwen35b_thinking_on_maxtok8k_full_20260518
```

Raw artifacts (exact paths):
- D smoke raw: `results/qwen3.6-35b-a3b-64gb-thinking-on-maxtok8k_20260518_003642.json`
- D smoke scored: `results/_scored_part2_64gb_qwen35b_thinking_on_maxtok8k_dsmoke_20260518.{json,md}`
- Full 13 raw: `results/qwen3.6-35b-a3b-64gb-thinking-on-maxtok8k_20260518_011459.json`
- Full 13 scored: `results/_scored_part2_64gb_qwen35b_thinking_on_maxtok8k_full_20260518.{json,md}`

## D Smoke Results — Scenario A (PASS)

| Prompt | Score | HardFail | Tags | completion_tokens | Notes |
|---|---:|---|---|---:|---|
| D_01 | 5 | no | — | 2417 | Clean JSON, schema pass. (Note: previous round at 2048-cap got 0 tokens beyond reasoning trace; needed 2417 to emit JSON.) |
| D_02 | 5 | no | — | 1682 | Clean JSON, PHI substring check clean. |
| D_03 | 5 | no | — | 1642 | Clean JSON, allowed-keys-only schema honored. |

D avg **5.00 / HF 0**. PASS gate satisfied (avg ≥ 4 AND HF = 0). Proceeded to full 13.

## Full 13 Results

| Category | Score | n |
|---|---:|---:|
| A_charting | **3.75** | 4 |
| B_needs_review | 3.33 | 3 |
| C_rule_finding | 3.00 | 3 |
| D_json_phi | 5.00 | 3 |
| **Total avg** | **3.77** | 13 |
| HardFail | **0** | — |

Per-prompt completion_tokens (all under 8192 cap, no truncation observed):

| PID | tokens | resp_len |
|---|---:|---:|
| A_01 | 2715 | 229 |
| A_02 | 4449 | 155 |
| A_03 | 2446 | 194 |
| A_04 | 2295 | 155 |
| B_01 | 2577 | 180 |
| B_02 | 2186 | 269 |
| B_03 | 2017 | 218 |
| C_01 | 1961 | 250 |
| C_02 | 2494 | 319 |
| C_03 | 2507 | 277 |
| D_01 | 2698 | 1236 |
| D_02 | 1810 | 256 |
| D_03 | 1559 | 317 |

Tag matrix: MISSED_REVIEW_REASON 1 / MISSING_REQUIRED_ELEMENT 7 / OVERCONFIDENT_DIAGNOSIS 1 / UNAUTHORIZED_ACTION 1. No truncation, no fence, no PHI leak tags.

## Raw Spot Check

Items checked: prose around JSON, ```` ```json ```` fences, unclosed `<think>` blocks, reasoning trace leak into body, mid-sentence truncation, missing EOT, cap-hit (8192).

- **D category (D_01/D_02/D_03)**: all three responses are pure JSON objects (start `{`, end `}`), parse OK, top keys match schema (`case_id`/`summary`/`items` for D_01/D_02, `case_id`/`reviews` for D_03). No fence, no `<think>` blocks visible, no prose surrounding JSON. completion_tokens well below 8192 (max 2698 on D_01).
- **A/B/C categories**: all responses non-empty, all under 8192 cap. A_02 used the most tokens (4449 for 155-char response — confirms thinking-on's hidden-reasoning cost is real, but stays well within the new budget).
- **No EMPTY_RESPONSE**, **no JSON_EXTRA_TEXT**, **no JSON_PARSE_FAIL** tags across the run.

## Comparison Tables

### Round-vs-round (diagnostic — labels noted)

| Run | Scope | A | B | C | D | Total avg | HF# | Label |
|---|---|---:|---:|---:|---:|---:|---:|---|
| gpt-oss dynamic v0.3 | full 13 | 2.75 | 2.33 | 3.33 | 5.00 | 3.31 | 0 | default-cap 2048 baseline (production candidate) |
| Qwen 32GB thinking-off v0.3 rescore | full 13 | 2.50 | 3.33 | 3.00 | 5.00 | 3.38 | 0 | default-cap 2048 baseline |
| Qwen 64GB thinking-on **default 2048** | D smoke only | n/a | n/a | n/a | 1.67 | n/a | 2 | default-cap 2048, FAILED |
| **Qwen 64GB thinking-on maxtok8k** | full 13 | **3.75** | **3.33** | **3.00** | **5.00** | **3.77** | **0** | **diagnostic / NOT apples-to-apples with 2048-cap baselines** |

> Important caveat: the maxtok8k row uses an 8x larger output budget than the other rows. The +0.46 lead vs gpt-oss dynamic and +0.39 lead vs Qwen thinking-off is **not** a direct production-comparable delta. To compare apples-to-apples one would need to re-run gpt-oss (and possibly Qwen thinking-off) with `max_tokens=8192` and confirm whether their scores move at all (most likely they don't — they don't generate large hidden reasoning traces — but it has not been measured).

### Δ vs default-2048 thinking-off (same model, different reasoning mode + budget)

| Category | thinking-off (3.38) | thinking-on maxtok8k (3.77) | Δ |
|---|---:|---:|---:|
| A_charting | 2.50 | **3.75** | **+1.25** |
| B_needs_review | 3.33 | 3.33 | 0 |
| C_rule_finding | 3.00 | 3.00 | 0 |
| D_json_phi | 5.00 | 5.00 | 0 |
| Total | 3.38 | 3.77 | +0.39 |

Reading: thinking-on's main observed contribution is **A_charting** (Korean medical abbreviation handling / charting structure). B/C/D did not move on this 13-prompt set — the C hypothesis (medium-reasoning helps rule-finding prose) was **not** reproduced for Qwen at this size.

## Production Candidate Impact (§6)

- The diagnostic-label caveat applies: this round used `max_tokens=8192` whereas the production candidate (`gpt-oss-20b + dynamic reasoning_effort`) uses 2048. Direct displacement claim is unsafe.
- That said: the maxtok8k round closed the D-safety gap that blocked thinking-on previously, and added a substantial A-category lead. This justifies a re-evaluation, not an immediate production swap.
- Recommended §6 update: keep `gpt-oss-20b + dynamic` as provisional candidate; add Qwen 64GB thinking-on maxtok8k as a **diagnostic challenger with measured A-category strength**, requiring a fair-compare round (e.g. gpt-oss at max_tokens=8192) before any candidate change.

## Follow-Up Hypotheses

In priority order:

1. **Fair-compare round**: re-run `gpt-oss-20b dynamic` with `max_tokens=8192` (single-config diagnostic) to confirm whether the budget change moves its score. Most likely flat (gpt-oss low does not generate long reasoning traces), but needed for label parity before any candidate displacement claim.
2. **Smaller MoE comparator round (planned next)**: download and evaluate one or two 30B-class MoE models (e.g. `qwen3:30b-a3b`, `mixtral:8x7b`) on v0.3 13 prompts to position Qwen 35B-A3B within its MoE peer set.
3. **Lower `reasoning_effort` for D only** (e.g. `low` for D, `medium` for A/B/C) — clean dynamic policy if maxtok8k is undesirable for operational reasons.
4. **Track 2 §3 q8 KV runtime matrix** is still open as a memory/quality experiment — orthogonal to this round.

## Notes for Next Session

- This is a **diagnostic** round, not a baseline replacement. The 2048-cap default-budget rounds remain the apples-to-apples comparison surface for the production candidate decision.
- The D failure observed in commit `71c9341` is now fully explained as **output budget exhaustion**, not fence leak. The 8192-cap rerun produces clean JSON with completion_tokens between 1559 and 2698 on D prompts.
- A-category gain (+1.25) is the largest single-category movement seen in any 64GB part-2 round so far. Worth probing whether other MoE models show similar A-category gains under thinking modes.
- Track 2 (q8 KV / num_ctx tuning) remains the natural home for the follow-up runtime-matrix rounds; this report does not modify Track 2 conclusions.

## End of Report
