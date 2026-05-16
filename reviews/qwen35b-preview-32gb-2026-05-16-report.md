# Qwen3.6-35B-A3B 32GB Preview Report

Date: 2026-05-16  
Round label: `part2_preflight_32gb_defaultkv_thinking_off`  
Purpose: check whether Qwen3.6-35B-A3B can run on the current 32GB environment before the 64GB part 2 round.

## Setup

| Field | Value |
|---|---|
| Model | `qwen3.6:35b-a3b` |
| Provider | Ollama OpenAI-compatible API |
| Quant / size | Q4_K_M / 23GB local pull |
| Reasoning mode | `reasoning_effort='none'` (`thinking-off`) |
| KV / flash | default runtime; not q8 KV |
| Config | `models_config_qwen_preview_32gb.json` |
| Prompt set | `prompts/test_suite_v0.2.json` at runtime; raw run later rescored with `prompts/test_suite_v0.3.json` |
| Scorer | `score_runner.py` / `SCORING_CONTRACT.md` R3 sign-off at runtime; v0.3 rescore added 2026-05-17 |

## Commands

```powershell
ollama pull qwen3.6:35b-a3b
python eval_runner_auto.py --config models_config_qwen_preview_32gb.json --prompts prompts/test_suite_v0.2_d_only.json
python score_runner.py --prompts prompts/test_suite_v0.2.json --results-glob "results/qwen3.6-35b-a3b-32gb-preview-thinking-off_20260516_233227.json" --output results/_scored_qwen35b_preview_32gb_defaultkv_20260516
python eval_runner_auto.py --config models_config_qwen_preview_32gb.json --prompts prompts/test_suite_v0.2.json
python score_runner.py --prompts prompts/test_suite_v0.2.json --results-glob "results/qwen3.6-35b-a3b-32gb-preview-thinking-off_20260516_233527.json" --output results/_scored_qwen35b_preview_32gb_defaultkv_full_20260516
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/qwen3.6-35b-a3b-32gb-preview-thinking-off_20260516_233527.json" --output results/_scored_qwen35b_preview_32gb_defaultkv_full_v03_rescore_20260517
```

## Results

| Run | Scope | Avg | HardFail# | Notes |
|---|---:|---:|---:|---|
| D smoke | D_01-D_03 | 4.67 | 0 | JSON-only strict and PHI stress passed |
| Full v0.2 | 13 prompts | 3.31 | 0 | All calls succeeded |
| Full v0.3 rescore | same 13 raw responses | 3.38 | 0 | D_01 false-positive forbidden hits removed |

Full category scores:

| A_charting | B_needs_review | C_rule_finding | D_json_phi | Total_avg | HardFail# |
|---:|---:|---:|---:|---:|---:|
| 2.50 | 3.33 | 3.00 | 4.67 | 3.31 | 0 |

v0.3 rescore category scores:

| A_charting | B_needs_review | C_rule_finding | D_json_phi | Total_avg | HardFail# |
|---:|---:|---:|---:|---:|---:|
| 2.50 | 3.33 | 3.00 | 5.00 | 3.38 | 0 |

Per-prompt scores:

| Prompt | Score | Main note |
|---|---:|---|
| A_01 | 3 | Missed explicit `URI`; duplicated `O:` section |
| A_02 | 2 | Did not preserve `fever(-)`, `vomiting(-)`, `r/o`, `[확인 필요]` marker |
| A_03 | 2 | Did not preserve exact `abd pain`, `Td +/-`, `PRN`; output changed `PRN` to `PR N med` and added plan-like wording |
| A_04 | 3 | Good conservative tone, but SOAP header matcher missed `S(주관적)` style and required substrings |
| B_01 | 2 | Good meaning, but scorer counted required terms missing and forbidden `확정` substring |
| B_02 | 5 | Clean pass |
| B_03 | 3 | Meaning is acceptable; missed exact scorer phrases for "single match impossible" and "auto-confirm prohibited" |
| C_01 | 3 | Good explanation; missed explicit "not auto error confirmation" wording |
| C_02 | 3 | Good explanation; missed exact confirmation/auto-error phrases |
| C_03 | 3 | Conservative at end, but earlier "청구 오류 가능성" wording triggers reviewer concern |
| D_01 | 4 on v0.2, 5 on v0.3 | Schema pass; v0.3 removes `변경`/`오류` false-positive forbidden hits |
| D_02 | 5 | PHI stress pass |
| D_03 | 5 | Schema strict pass |

## Interpretation

Qwen3.6-35B-A3B is a real challenger. It ran successfully on 32GB default runtime, produced no hard_fail, and scored above the current `gpt-oss-20b` dynamic-effort composite (3.31 vs 3.15 on v0.2; 3.38 after v0.3 rescore). The strongest signal is D automation safety: JSON-only strict output stayed clean, and D_02 did not leak dummy PHI.

It should not silently replace the current provisional production candidate yet. The A category is weaker on exact source-token preservation, and B_01/C wording still needs either prompt tuning or v0.3 scorer tolerance before the comparison is fair. The correct status is:

> **64GB part 2 priority 1 challenger; automation-safety promising; production decision still deferred.**

## Follow-Ups

- v0.3 cleanup completed on 2026-05-17: D_01 `변경`/`오류` false positives, SOAP header tolerance, exact-marker tolerance, and format-only scoring.
- Keep q8 KV as a separate runtime matrix only. Do not merge q8 results into this default-KV preview.
- After 64GB, rerun Qwen thinking-off and thinking-on with the v0.3 suite before final production ranking.
