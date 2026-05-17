# gpt-oss-20b Dynamic — maxtok8k Fair-Compare Diagnostic Report

Date: 2026-05-18
Round label: `fair_compare_gpt_oss_dynamic_maxtok8k`
Status: **Scenario A (gpt-oss flat at maxtok8k)** — composite 3.23 vs 2048 baseline 3.31, Δ -0.08 (noise)

> Purpose: Establish a maxtok8k-budget baseline for gpt-oss dynamic so that the Qwen 64GB thinking-on maxtok8k result (commit `7240eaa`, avg 3.77) can be compared apples-to-apples. Without this round, any production-candidate displacement claim would be confounded by the 2048 → 8192 cap change.

## Setup

| Field | Spec | Actual observed |
|---|---|---|
| Models | `gpt-oss:20b` ×2 (reasoning_effort low + medium) | confirmed via raw `inference_options` |
| Provider | Ollama OpenAI-compatible API | `base_url: http://localhost:11434/v1` in raw |
| Quant / size | Default Ollama gpt-oss:20b (17 GB) | same |
| max output tokens | **8192** (override via `inference_options.max_tokens`) | confirmed; per-prompt observed max was 1232 (medium B_01) — no cap pressure |
| KV cache type | default / f16-equivalent (intended spec) | **not directly observed** — `OLLAMA_KV_CACHE_TYPE` env var unset |
| Flash attention | default | **not directly observed** — `OLLAMA_FLASH_ATTENTION` env var unset |
| num_ctx | default | **not directly observed** |
| Config | `models_config_gpt_oss_dynamic_maxtok8k.json` | same |
| Prompt set | `prompts/test_suite_v0.3.json` (full 13) | same |
| Scorer | `score_runner.py` / `SCORING_CONTRACT.md` v0.3 | same |
| Pre-check env vars | both unset | confirmed |
| Pre-check `ollama ps` | empty | confirmed |
| Pre-check `git log` | latest commit `7240eaa` | confirmed |

## Commands

```powershell
python eval_runner_auto.py --config models_config_gpt_oss_dynamic_maxtok8k.json --prompts prompts/test_suite_v0.3.json
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/gpt-oss-20b-low-maxtok8k_20260518_041947.json" --output results/_scored_gpt_oss_low_maxtok8k_full_20260518
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/gpt-oss-20b-medium-maxtok8k_20260518_042427.json" --output results/_scored_gpt_oss_medium_maxtok8k_full_20260518
```

Raw artifacts:
- Low raw: `results/gpt-oss-20b-low-maxtok8k_20260518_041947.json`
- Low scored: `results/_scored_gpt_oss_low_maxtok8k_full_20260518.{json,md}`
- Medium raw: `results/gpt-oss-20b-medium-maxtok8k_20260518_042427.json`
- Medium scored: `results/_scored_gpt_oss_medium_maxtok8k_full_20260518.{json,md}`

## Runtime Health

Both models completed full 13 cleanly. No timeout, no partial. Total wall-clock for both runs ~6 minutes (low ~1.5 min, medium ~5 min). No `_partial.json` residual.

## Per-Prompt Results

### low (reasoning_effort = low, max_tokens = 8192)

| PID | Score | HF | Tags | tokens | resp_len |
|---|---:|---|---|---:|---:|
| A_01 | 3 | no | — | 102 | 112 |
| A_02 | 3 | no | TOO_VERBOSE | 485 | 131 |
| A_03 | 3 | no | — | 99 | 174 |
| A_04 | 3 | no | — | 135 | 106 |
| B_01 | 3 | no | MISSING_REQUIRED_ELEMENT | 96 | 135 |
| B_02 | 3 | no | — | 153 | 253 |
| B_03 | 2 | no | MISSING_REQUIRED_ELEMENT | 44 | 20 |
| C_01 | 2 | no | MISSING_REQUIRED_ELEMENT | 119 | 20 |
| C_02 | 2 | no | MISSING_REQUIRED_ELEMENT | 61 | 20 |
| C_03 | 2 | no | MISSING_REQUIRED_ELEMENT | 116 | 189 |
| D_01 | 5 | no | — | 372 | 844 |
| D_02 | 5 | no | — | 131 | 235 |
| D_03 | 5 | no | — | 216 | 233 |

Category averages: A 3.00 / B 2.67 / C 2.00 / D 5.00 — Total **3.15 / HF 0**

### medium (reasoning_effort = medium, max_tokens = 8192)

| PID | Score | HF | Tags | tokens | resp_len |
|---|---:|---|---|---:|---:|
| A_01 | 3 | no | — | 694 | 125 |
| A_02 | 4 | no | — | 1232 | 183 |
| A_03 | 3 | no | — | 617 | 160 |
| A_04 | 4 | no | — | 355 | 110 |
| B_01 | 2 | no | MISSING_REQUIRED_ELEMENT | 1219 | 143 |
| B_02 | 2 | no | — | 862 | 20 |
| B_03 | 2 | no | MISSING_REQUIRED_ELEMENT | 323 | 20 |
| C_01 | 3 | no | MISSING_REQUIRED_ELEMENT | 420 | 193 |
| C_02 | 2 | no | MISSING_REQUIRED_ELEMENT | 151 | 20 |
| C_03 | 2 | no | MISSING_REQUIRED_ELEMENT | 876 | 148 |
| D_01 | 5 | no | — | 495 | 869 |
| D_02 | 5 | no | — | 444 | 240 |
| D_03 | 5 | no | — | 329 | 340 |

Category averages: A 3.50 / B 2.00 / C 2.33 / D 5.00 — Total **3.23 / HF 0**

## Raw Spot Check

All 6 D responses (3 prompts × 2 reasoning modes) parse as valid JSON with the expected top-level keys (`case_id/summary/items` for D_01,D_02; `case_id/reviews` for D_03). No markdown fence, no `<think>` block leak, no prose around JSON, no EMPTY_RESPONSE.

Verbose/budget changes vs 2048 baseline:
- **low**: response length comparable to 2048 baseline. completion_tokens 44–485, all well under 8k cap. No verbose pressure.
- **medium**: completion_tokens 151–1232, all well under 8k cap. Hidden reasoning is real (medium uses 3–10× more tokens than low) but not anywhere near runaway.
- **No cap hit on any prompt across either run.** 8k budget is overkill for gpt-oss.

## Dynamic Composite (selected-set: A/B/D from low, C from medium)

Formula: `composite = (A_low*4 + B_low*3 + C_medium*3 + D_low*3) / 13`

| Field | Value |
|---|---:|
| A (low) | 3.00 × 4 = 12.00 |
| B (low) | 2.67 × 3 = 8.01 |
| C (medium) | 2.33 × 3 = 6.99 |
| D (low) | 5.00 × 3 = 15.00 |
| Sum | 42.00 |
| **Composite avg** | **42.00 / 13 = 3.23** |

**Composite HF (selected-set basis)**: 0
- Low A/B/D hard_fail: 0
- Medium C hard_fail: 0
- Total selected-set HF: 0

**Medium D diagnostic finding (NOT in composite per §5)**:
- Medium D at maxtok8k: 5.00 / HF 0, all 3 responses pure JSON, no fence
- Contrast: §5.7 verification at 2048 cap showed medium D_02 `JSON_EXTRA_TEXT` hard_fail (medium D = 3.00 with 1 HF)
- Interpretation: at higher output budget, medium's reasoning trace appears to fit without spilling into the response body as a fence. **This is a diagnostic observation only — §5 forbidden rule (medium for D) remains in force unless verified by a separate targeted round.** A standalone medium-D-at-8k re-run + temperature-sweep could be informative, but is not a part-2 priority.

## Comparison Tables

### 2048 baseline vs maxtok8k (same model, different budget)

| Field | 2048 v0.3 rescore | maxtok8k (this round) | Δ |
|---|---:|---:|---:|
| A_low | 2.75 | 3.00 | +0.25 |
| B_low | 2.33 | 2.67 | +0.34 |
| C_low | 2.00 | 2.00 | 0 |
| D_low | 5.00 | 5.00 | 0 |
| Total low | 3.00 | 3.15 | +0.15 |
| C_medium | 3.33 | 2.33 | **-1.00** |
| **Composite dynamic** | **3.31** | **3.23** | **-0.08** |
| HF | 0 | 0 | 0 |

Reading:
- Low at 8k vs low at 2048: small positive drift (+0.15 total). Within scoring noise.
- Medium C at 8k vs medium C at 2048: -1.00 drop. Notable but plausible from sampling at temp 0.3 (responses on C are stub-like at both budgets for some prompts).
- Composite net: -0.08, essentially flat. **Scenario A** confirmed: gpt-oss does not benefit from larger output budget on this 13-prompt set.

### Fair-compare table (maxtok8k apples-to-apples)

| Run | Scope | A | B | C | D | Total | HF# | Label |
|---|---|---:|---:|---:|---:|---:|---:|---|
| gpt-oss dynamic 2048 v0.3 (production candidate) | full 13 | 2.75 | 2.33 | 3.33 | 5.00 | 3.31 | 0 | baseline |
| **gpt-oss dynamic maxtok8k (this round)** | full 13 | **3.00** | **2.67** | **2.33** | **5.00** | **3.23** | **0** | diagnostic (8k cap) |
| Qwen 32GB thinking-off 2048 v0.3 rescore | full 13 | 2.50 | 3.33 | 3.00 | 5.00 | 3.38 | 0 | baseline |
| Qwen 64GB thinking-on maxtok8k | full 13 | **3.75** | 3.33 | 3.00 | 5.00 | **3.77** | 0 | diagnostic (8k cap) |
| **Δ (Qwen-maxtok8k - gpt-oss-maxtok8k)** | full 13 | **+0.75** | +0.66 | +0.67 | 0 | **+0.54** | 0 | apples-to-apples (both 8k) |

**Key conclusion**: at fair-compare (both at maxtok8k), Qwen leads by **+0.54** total avg with HF parity. The gap is real and not an artifact of budget mismatch. A-category gap is particularly large (+0.75) — Qwen thinking-on's main strength is Korean medical abbreviation handling / charting structure.

## Production Candidate Impact (§6)

- The maxtok8k fair-compare validates the +0.54 Qwen lead is **not** a budget-mismatch artifact.
- However, this does NOT immediately displace `gpt-oss-20b dynamic` as production candidate. Outstanding considerations:
  1. **Operational cost**: Qwen 35B-A3B MoE wall-clock per prompt is ~4–5× gpt-oss 20B (Qwen 35B run took ~38 min vs gpt-oss ~6 min for 2-model full 13 each). Production latency matters.
  2. **VRAM split**: Qwen 35B uses 61%/39% CPU/GPU split (model size 35GB exceeds 16GB VRAM). gpt-oss 20B fits with 20%/80% CPU/GPU. Throughput and concurrent-request behavior will differ.
  3. **maxtok8k cost in production**: 4× the per-request output budget compared to gpt-oss baseline of 2048.
  4. **Smaller-model comparators not yet measured**: round 9 (dense 12-14B + smaller MoE) might show that a 12B dense model approaches gpt-oss's 3.31 score, in which case **RAG-augmented smaller model** becomes the right production architecture (lower latency, updatable knowledge), not larger Qwen.

§6 update recommendation: keep `gpt-oss-20b dynamic` as provisional production candidate. Promote Qwen 64GB thinking-on maxtok8k to **measured challenger with +0.54 fair-compare lead**, decision deferred until round 9 (dense/MoE comparator) completes.

## Hypothesis Confirmation

User's three branch hypotheses, with this round's outcome:

| Hypothesis | Prediction | Observed | Verdict |
|---|---|---|---|
| A: 2048 was sufficient for gpt-oss; 8k flat | composite ≈ 3.31 | 3.23 (Δ -0.08) | **A confirmed** |
| B: cap policy needs Part 2 revisit (8k uplift) | large positive Δ | Δ -0.08 | rejected |
| C: 8k is risky for gpt-oss (verbose/fence/HF) | HF or fence increases | HF 0, no fence, no truncation | rejected |

→ Scenario A. The Qwen-vs-gpt-oss comparison at maxtok8k is honest (no cap-artifact confound). Qwen's +0.54 lead is the real signal.

## Follow-Up Hypotheses (logged, not actioned)

1. **Round 9 (next, planned)**: MoE + dense comparators (qwen3:8b, gemma3:12b, qwen3:14b, qwen3:30b-a3b, mixtral:8x7b) at default 2048 cap. Decide between "larger model" and "smaller-model-plus-RAG" architectures.
2. **Medium-D-at-8k targeted verification**: §5.7's medium-D failure didn't reproduce here. A targeted round with multiple seeds at 2048 vs 8192 could clarify whether the §5 forbidden rule needs a budget caveat. Not urgent.
3. **gpt-oss operational latency benchmark vs Qwen 35B**: end-to-end wall-clock + throughput under concurrent requests, to quantify the production trade-off for any candidate displacement decision.

## Notes for Next Session

- Both maxtok8k diagnostic rounds (Qwen `7240eaa` and this one) close out the "is the cap a confound?" question. Cap is not a confound for gpt-oss; it WAS a confound for Qwen thinking-on. With both quantified, §6 has clean numbers for the production decision.
- The medium D pass at 8k is **interesting but isolated** — do not relax §5 forbidden rule yet.
- A-category gap (+0.75 in favor of Qwen) is the single largest signal in part-2 so far. This category measures Korean medical abbreviation handling and charting structure adherence — a clinical-assist core competency.
- Round 9 will tell whether RAG-track investment dominates "bigger-model" investment for this project.

## End of Report
