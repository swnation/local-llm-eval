# Round 9 — MoE + 16GB-VRAM Dense Comparators Report

Date: 2026-05-18
Round label: `round9_moe_dense_64gb_2048cap`
Status: **RAG-augmented small-model architecture justified** — qwen3:14b dense matches gpt-oss baseline exactly (3.31 HF0); qwen3:8b floor sits +0.07 above. Both MoE candidates and gemma3:12b disqualified by D hard_fail.

> Purpose: at default 2048 cap (apples-to-apples with `gpt-oss dynamic 2048` baseline of 3.31 HF0), measure five candidates to answer two questions: (1) is a smaller MoE (qwen3:30b-a3b) or other-architecture MoE (mixtral:8x7b) sufficient versus the 35B Qwen MoE? (2) does a dense 12-14B model land within ±0.3 of the gpt-oss baseline — which would unlock the "RAG-augmented small dense model" production architecture instead of "larger Qwen MoE"?

## Setup

| Field | Spec | Actual observed |
|---|---|---|
| Models | qwen3:8b / gemma3:12b / qwen3:14b / qwen3:30b-a3b / mixtral:8x7b | confirmed via raw `inference_options` / `model_id` |
| Provider | Ollama OpenAI-compatible API | `base_url: http://localhost:11434/v1` in raw |
| Quant / disk sizes | Q4 defaults (5.2 / 8.1 / 9.3 / 18 / 26 GB on disk) | observed at `ollama pull` time |
| max output tokens | default 2048 (no override) | confirmed; cap-hit observed only on qwen3:30b-a3b (4 prompts at exactly 2048) |
| KV cache type | default / f16-equivalent (intended spec) | **not directly observed** — `OLLAMA_KV_CACHE_TYPE` env unset (verified precheck) |
| Flash attention | default (intended spec) | **not directly observed** — `OLLAMA_FLASH_ATTENTION` env unset |
| num_ctx | default per model (intended spec) | **not directly observed** in eval output; `ollama ps` reported runtime context-window allocations of 131072 (gemma3:12b), 40960 (qwen3:14b), 262144 (qwen3:30b-a3b), 32768 (mixtral:8x7b) — these are model defaults, not eval-set num_ctx |
| Reasoning control | `reasoning_effort="none"` for qwen3 family, omitted for gemma3 / mixtral | confirmed in raw `inference_options`. **Effective behavior**: qwen3:8b and qwen3:14b respect `none` (clean output, no reasoning leak). **qwen3:30b-a3b does NOT** — visible reasoning prose ("Okay, let's tackle this...") leaks into response body in every prompt. This is an Ollama / model-template gap, NOT an eval bug. |
| Config | `models_config_round9_moe_dense_64gb.json` | same |
| Prompt set | `prompts/test_suite_v0.3.json` (full 13) | same |
| Scorer | `score_runner.py` / `SCORING_CONTRACT.md` v0.3 | same |
| Pre-check env vars | both unset | confirmed (exit-code-1 from `Get-ChildItem` is "no matching var" — correct) |
| Pre-check `ollama ps` | empty | confirmed |
| Pre-check `git log` | latest commit `f00e9b6` | confirmed |

### `ollama ps` runtime observations (CPU/GPU split)

| Model | `ollama ps` SIZE | CPU/GPU split | Context |
|---|---|---|---|
| qwen3:8b | (passed in <1 min, no `ps` capture window) | — | — |
| gemma3:12b | 19 GB | 33% / 67% | 131072 |
| qwen3:14b | 16 GB | 14% / 86% | 40960 |
| qwen3:30b-a3b | 45 GB | 71% / 29% | 262144 |
| mixtral:8x7b | 32 GB | 61% / 39% | 32768 |

Larger MoEs (qwen3:30b-a3b 71% CPU, mixtral 61% CPU) spill heavily to CPU on the 16GB VRAM. qwen3:14b dense fits comfortably (86% GPU). qwen3:8b runs the fastest (sub-second to ~4 s per prompt).

## Commands

```powershell
ollama pull qwen3:8b ; ollama pull gemma3:12b ; ollama pull qwen3:14b ; ollama pull qwen3:30b-a3b ; ollama pull mixtral:8x7b
python eval_runner_auto.py --config models_config_round9_moe_dense_64gb.json --prompts prompts/test_suite_v0.3.json
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/qwen3-8b_20260518_044416.json" --output results/_scored_round9_qwen3-8b_20260518
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/gemma3-12b_20260518_044704.json" --output results/_scored_round9_gemma3-12b_20260518
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/qwen3-14b_20260518_044820.json" --output results/_scored_round9_qwen3-14b_20260518
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/qwen3-30b-a3b_20260518_050204.json" --output results/_scored_round9_qwen3-30b-a3b_20260518
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/mixtral-8x7b_20260518_050702.json" --output results/_scored_round9_mixtral-8x7b_20260518
```

### Raw + scored artifacts (exact paths)

| Model | Raw | Scored |
|---|---|---|
| qwen3-8b | `results/qwen3-8b_20260518_044416.json` | `results/_scored_round9_qwen3-8b_20260518.{json,md}` |
| gemma3-12b | `results/gemma3-12b_20260518_044704.json` | `results/_scored_round9_gemma3-12b_20260518.{json,md}` |
| qwen3-14b | `results/qwen3-14b_20260518_044820.json` | `results/_scored_round9_qwen3-14b_20260518.{json,md}` |
| qwen3-30b-a3b | `results/qwen3-30b-a3b_20260518_050204.json` | `results/_scored_round9_qwen3-30b-a3b_20260518.{json,md}` |
| mixtral-8x7b | `results/mixtral-8x7b_20260518_050702.json` | `results/_scored_round9_mixtral-8x7b_20260518.{json,md}` |

## Runtime Health

All 5 models completed full 13 cleanly. No timeout, no connection failure, no `_partial.json` residual. Background eval task exit code 0. Per-model wall-clock (per `eval_runner_auto.py` per-model start→save):

| Model | Approx wall-clock | Notes |
|---|---:|---|
| qwen3:8b | ~3 min | fastest |
| gemma3:12b | ~3 min | dense 12B, default ctx (131k) but unused |
| qwen3:14b | ~2 min | fast despite 14B (86% GPU) |
| qwen3:30b-a3b | ~20 min | heavy CPU offload + per-prompt reasoning-trace bloat |
| mixtral:8x7b | ~5 min | 32 GB MoE, dense-feeling output |

## Per-Model Results

### qwen3-8b (`reasoning_effort=none`)

| PID | Score | HF | Tags | tokens |
|---|---:|---|---|---:|
| A_01 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT | 76 |
| A_02 | 2 | no | MISSING_REQUIRED_ELEMENT | 91 |
| A_03 | 2 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 273 |
| A_04 | 4 | no | FORMAT_FAIL, TOO_VERBOSE | 169 |
| B_01 | 2 | no | MISSED_REVIEW_REASON, MISSING_REQUIRED_ELEMENT, OVERCONFIDENT_DIAGNOSIS, UNAUTHORIZED_ACTION | 175 |
| B_02 | 5 | no | — | 130 |
| B_03 | 3 | no | MISSING_REQUIRED_ELEMENT | 122 |
| C_01 | 3 | no | MISSING_REQUIRED_ELEMENT | 211 |
| C_02 | 5 | no | — | 142 |
| C_03 | 2 | no | MISSING_REQUIRED_ELEMENT | 256 |
| D_01 | 3 | no | MISSING_REQUIRED_ELEMENT, SCHEMA_EXTRA_KEY | 417 |
| D_02 | 5 | no | — | 114 |
| D_03 | 5 | no | — | 145 |

Category avgs: A 2.75 / B 3.33 / C 3.33 / D 4.33 — Total **3.38 / HF 0** — tokens 76–417 (no cap pressure)

### gemma3-12b (no `reasoning_effort`)

| PID | Score | HF | Tags | tokens |
|---|---:|---|---|---:|
| A_01 | 2 | no | MISSING_REQUIRED_ELEMENT | 172 |
| A_02 | 2 | no | MISSING_REQUIRED_ELEMENT | 129 |
| A_03 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 278 |
| A_04 | 3 | no | MISSING_REQUIRED_ELEMENT | 148 |
| B_01 | 2 | no | MISSING_REQUIRED_ELEMENT | 89 |
| B_02 | 5 | no | — | 112 |
| B_03 | 3 | no | MISSING_REQUIRED_ELEMENT | 116 |
| C_01 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 193 |
| C_02 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 189 |
| C_03 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 170 |
| D_01 | **0** | **HF** | JSON_EXTRA_TEXT (markdown ```json fence) | 615 |
| D_02 | **0** | **HF** | JSON_EXTRA_TEXT (markdown ```json fence) | 137 |
| D_03 | **0** | **HF** | JSON_EXTRA_TEXT (markdown ```json fence) | 170 |

Category avgs: A 2.50 / B 3.33 / C 3.00 / D **0.00** — Total **2.23 / HF 3** — tokens 89–615 (no cap)

### qwen3-14b (`reasoning_effort=none`)

| PID | Score | HF | Tags | tokens |
|---|---:|---|---|---:|
| A_01 | 3 | no | MISSING_REQUIRED_ELEMENT | 114 |
| A_02 | 2 | no | MISSING_REQUIRED_ELEMENT | 104 |
| A_03 | 4 | no | FORMAT_FAIL, TOO_VERBOSE | 95 |
| A_04 | 3 | no | MISSING_REQUIRED_ELEMENT | 107 |
| B_01 | 2 | no | MISSED_REVIEW_REASON, MISSING_REQUIRED_ELEMENT, OVERCONFIDENT_DIAGNOSIS, UNAUTHORIZED_ACTION | 98 |
| B_02 | 3 | no | MISSING_REQUIRED_ELEMENT | 124 |
| B_03 | 3 | no | MISSING_REQUIRED_ELEMENT | 108 |
| C_01 | 3 | no | MISSING_REQUIRED_ELEMENT | 152 |
| C_02 | 3 | no | MISSING_REQUIRED_ELEMENT | 144 |
| C_03 | 2 | no | MISSING_REQUIRED_ELEMENT | 154 |
| D_01 | 5 | no | — | 401 |
| D_02 | 5 | no | — | 114 |
| D_03 | 5 | no | — | 162 |

Category avgs: A 3.00 / B 2.67 / C 2.67 / D 5.00 — Total **3.31 / HF 0** — tokens 95–401 (no cap)

### qwen3-30b-a3b (`reasoning_effort=none` — but **not honored by model**)

| PID | Score | HF | Tags | tokens |
|---|---:|---|---|---:|
| A_01 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 2048 (CAP) |
| A_02 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 2048 (CAP) |
| A_03 | 4 | no | FORMAT_FAIL, TOO_VERBOSE | 2048 (CAP) |
| A_04 | 4 | no | FORMAT_FAIL, TOO_VERBOSE | 1506 |
| B_01 | 2 | no | FORMAT_FAIL, MISSED_REVIEW_REASON, MIXED_LANGUAGE, OVERCONFIDENT_DIAGNOSIS, TOO_VERBOSE, UNAUTHORIZED_ACTION | 1024 |
| B_02 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, MIXED_LANGUAGE, TOO_VERBOSE | 1024 |
| B_03 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, MIXED_LANGUAGE, TOO_VERBOSE | 561 |
| C_01 | 3 | no | FORMAT_FAIL, HALLUCINATED_FINDING, MISSING_REQUIRED_ELEMENT, MIXED_LANGUAGE, TOO_VERBOSE, UNAUTHORIZED_ACTION | 1024 |
| C_02 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, MIXED_LANGUAGE, TOO_VERBOSE | 1024 |
| C_03 | 3 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, MIXED_LANGUAGE, TOO_VERBOSE | 1024 |
| D_01 | **0** | **HF** | JSON_EXTRA_TEXT (prose prefix "Okay, let's tackle this...") | 2048 (CAP) |
| D_02 | **0** | **HF** | JSON_EXTRA_TEXT, PHI_LEAK | 1856 |
| D_03 | **0** | **HF** | JSON_EXTRA_TEXT, UNAUTHORIZED_ACTION | 1870 |

Category avgs: A 3.50 / B 2.67 / C 3.00 / D **0.00** — Total **2.38 / HF 3** — tokens 561–2048 (4 cap hits)

### mixtral-8x7b (no `reasoning_effort`)

| PID | Score | HF | Tags | tokens |
|---|---:|---|---|---:|
| A_01 | 2 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT | 219 |
| A_02 | 2 | no | MISSING_REQUIRED_ELEMENT | 125 |
| A_03 | 2 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, TOO_VERBOSE | 257 |
| A_04 | 2 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT | 198 |
| B_01 | 2 | no | FORMAT_FAIL, MISSING_REQUIRED_ELEMENT, MIXED_LANGUAGE | 43 |
| B_02 | 3 | no | MISSING_REQUIRED_ELEMENT | 187 |
| B_03 | 3 | no | MISSING_REQUIRED_ELEMENT | 194 |
| C_01 | 3 | no | MISSING_REQUIRED_ELEMENT | 250 |
| C_02 | 3 | no | MISSING_REQUIRED_ELEMENT | 214 |
| C_03 | 3 | no | MISSING_REQUIRED_ELEMENT | 271 |
| D_01 | **0** | **HF** | JSON_EXTRA_TEXT (```json fence) | 542 |
| D_02 | **0** | **HF** | JSON_EXTRA_TEXT (English prose prefix + fence + post-JSON prose) | 210 |
| D_03 | **0** | **HF** | JSON_EXTRA_TEXT (response truncated at 19 tokens — early-EOT) | 19 |

Category avgs: A 2.00 / B 2.67 / C 3.00 / D **0.00** — Total **1.92 / HF 3** — tokens 19–542 (no cap, but D_03 stopped early)

## Combined Comparison Table

| Model | Class | A | B | C | D | Total | HF | Δ vs gpt-oss baseline (3.31) | Within ±0.3? |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| **gpt-oss dynamic 2048 (production candidate baseline)** | dense 20B | 2.75 | 2.33 | 3.33 | 5.00 | **3.31** | 0 | — (baseline) | — |
| qwen3-8b | dense 8B | 2.75 | 3.33 | 3.33 | 4.33 | **3.38** | 0 | **+0.07** | YES |
| gemma3-12b | dense 12B | 2.50 | 3.33 | 3.00 | **0.00** | 2.23 | 3 | -1.08 | no (D HF) |
| qwen3-14b | dense 14B | 3.00 | 2.67 | 2.67 | 5.00 | **3.31** | 0 | **0.00** | YES |
| qwen3-30b-a3b | MoE 30B (3B active) | 3.50 | 2.67 | 3.00 | **0.00** | 2.38 | 3 | -0.93 | no (D HF) |
| mixtral-8x7b | MoE 8×7B | 2.00 | 2.67 | 3.00 | **0.00** | 1.92 | 3 | -1.39 | no (D HF) |
| (ref) Qwen 32GB thinking-off v0.3 | MoE 35B (3B active) | 2.50 | 3.33 | 3.00 | 5.00 | 3.38 | 0 | +0.07 | — |
| (ref) Qwen 64GB thinking-on maxtok8k | MoE 35B (3B active) | 3.75 | 3.33 | 3.00 | 5.00 | 3.77 | 0 | +0.46 (but diff cap) | — |

## Dense vs MoE Classification Analysis

**Dense models** (in this round): qwen3:8b, gemma3:12b, qwen3:14b
- 2 of 3 pass ±0.3 (qwen3:8b and qwen3:14b) — strong signal
- gemma3:12b failure is a JSON-fence formatting issue, NOT a content/reasoning issue; A/B/C category scores are competitive

**MoE models** (in this round): qwen3:30b-a3b, mixtral:8x7b
- 0 of 2 pass ±0.3
- Both fail on D HF (JSON purity)
- qwen3:30b-a3b's failure is rooted in `reasoning_effort=none` not being honored — reasoning prose contaminates every D response
- mixtral's failures are mixed: ```json fence (D_01), English-prose-prefix + fence + commentary (D_02), early-EOT truncation (D_03)

**Reference**: Qwen 35B-A3B (the only MoE that has passed cleanly) requires either thinking-off at default cap (3.38) or thinking-on at maxtok8k (3.77). The 30B sibling does not inherit that behavior with `reasoning_effort=none` under Ollama.

## Decision Tree — Trigger Met?

The round was designed to fire one of three branches:

1. **Dense 12-14B within ±0.3 of gpt-oss baseline** → RAG-augmented small dense model is the right production architecture
2. **Dense 12-14B more than 0.3 below baseline** → larger model (Qwen 35B class) is the right answer
3. **Dense within ±0.3 but MoE comparable also passes** → either architecture acceptable; pick on other criteria

**Verdict: Branch 1 FIRED.**

- **qwen3-14b dense: 3.31 (Δ 0.00)** — exactly matches gpt-oss baseline at less than half the disk size (9.3 GB vs 17 GB) and fits comfortably in 16GB VRAM (86% GPU). D 5.00/HF 0 — JSON discipline as good as gpt-oss.
- **qwen3-8b dense floor: 3.38 (Δ +0.07)** — even smaller (5.2 GB) and still within ±0.3. D 4.33/HF 0 — one D_01 score=3 from `SCHEMA_EXTRA_KEY` but no HF. Surprisingly the highest total score in the round.
- **MoE candidates fail HF**: neither qwen3:30b-a3b nor mixtral:8x7b clears the D safety bar. They are not direct substitutes for the Qwen 35B-A3B in §6.
- **gemma3:12b is rehabilitatable**: A/B/C all reasonable (2.50 / 3.33 / 3.00 — slightly above gpt-oss baseline on B), failures are pure formatting (markdown fence). A prompt-level "no fences, raw JSON only" reinforcement or a fence-strip post-processor would likely restore D to 4.00–5.00.

→ **Recommendation: RAG-augmented small dense model (qwen3:14b primary, qwen3:8b fallback) is now a credible production architecture candidate.** Promote to next round of comparison alongside `gpt-oss dynamic` and `Qwen 35B thinking-on maxtok8k`.

## D Spot Check Summary

| Model | D_01 | D_02 | D_03 |
|---|---|---|---|
| qwen3-8b | pure JSON, parses, no fence, no leak | pure JSON, parses, no fence | pure JSON, parses, no fence |
| gemma3-12b | ```json fence wrap | ```json fence wrap | ```json fence wrap |
| qwen3-14b | pure JSON, parses, no fence, no leak | pure JSON, parses, no fence | pure JSON, parses, no fence |
| qwen3-30b-a3b | "Okay, let's tackle this..." prose prefix (no `<think>` tag, just visible reasoning); cap-hit @ 2048 | reasoning prose + JSON (PHI_LEAK detected) | reasoning prose + JSON |
| mixtral-8x7b | ```json fence wrap | English prose "Based on the input..." + ```json fence + post-JSON commentary | early-EOT — output truncated at 19 tokens, partial JSON `{"case_id":"case_2026-0` |

C spot check: qwen3:30b-a3b's C_01–C_03 all show `Okay, let's...` prose prefix consuming 1024 tokens before any real content. A_01–A_03 hit the 2048 cap, all consumed by reasoning trace. This confirms `reasoning_effort=none` is silently ignored by Ollama for the `qwen3:30b-a3b` template.

## Production Candidate Impact (§6 update)

Current §6 production candidate: `gpt-oss-20b dynamic` (3.31 HF0). Round 9 outcome:

- **gpt-oss-20b dynamic retained as provisional candidate.** No model in this round HF-clean-displaced it.
- **qwen3:14b is now a co-equal candidate at this score** (3.31 / HF 0). Selection between gpt-oss and qwen3:14b should be made on: (a) operational latency (qwen3:14b in this round was actually faster wall-clock than gpt-oss at default cap due to 86% GPU utilization), (b) cost-of-RAG-integration (smaller model has more headroom for retrieved context), (c) license/portability.
- **qwen3:8b becomes a low-resource fallback** for environments with limited VRAM/RAM — 5.2 GB on disk, total 3.38 / HF 0.
- **Qwen 35B-A3B thinking-on maxtok8k (3.77, +0.46 vs baseline)** retains its "measured challenger" status from §6, but the **RAG-augmented small-model** path now has empirical backing.

### Architecture decision now pending two-way comparison

Two production architectures are now viable based on this evidence:

| Architecture | Best model | Score | Disk | VRAM behavior | Latency / 13 prompts | Operational notes |
|---|---|---:|---:|---|---:|---|
| **Large MoE + thinking** | Qwen 35B-A3B thinking-on maxtok8k | 3.77 HF0 | 24 GB | 61%/39% CPU/GPU split (35B exceeds 16GB) | ~38 min | high output budget (8k cap), heavy CPU offload, but highest score |
| **RAG-augmented small dense** | qwen3:14b @ default 2048 | 3.31 HF0 | 9.3 GB | 14%/86% CPU/GPU (fits 16GB) | ~2 min | fast, leaves headroom for retrieval, lower per-token cost |
| **Current production** | gpt-oss-20b dynamic @ default 2048 | 3.31 HF0 | 17 GB | 20%/80% CPU/GPU | ~6 min | proven, dynamic reasoning_effort, requires §5 D=low rule |

§6 update recommendation: keep `gpt-oss-20b dynamic` as **provisional** production candidate. Add `qwen3:14b @ default 2048` as **co-equal RAG-track candidate**. Defer final decision until a dedicated RAG eval set is constructed (see Follow-Up).

## Hypothesis Confirmation

| Hypothesis | Prediction | Observed | Verdict |
|---|---|---|---|
| H1: Smaller Qwen MoE (qwen3:30b-a3b) sufficient versus 35B-A3B | similar or modestly lower score | 2.38 with 3 D HF — **fails D safety bar** | **rejected** — 30B-A3B with `reasoning_effort=none` not honored by Ollama; not a drop-in substitute |
| H2: Mixtral 8x7B comparable to other 26GB-class models | within noise of gpt-oss baseline | 1.92 with 3 D HF — far below | **rejected** — D JSON discipline poor (fence + truncation) |
| H3: Dense 12-14B within ±0.3 of gpt-oss baseline (→ RAG architecture) | qwen3:14b or gemma3:12b within ±0.3 | qwen3:14b Δ 0.00, qwen3:8b Δ +0.07 (both HF 0) | **confirmed** — RAG-augmented small dense path empirically supported |

## Follow-Up Actions (logged, priority order)

1. **(P1) RAG eval set design**. The current 13-prompt suite measures explanation/cleanup/review on already-extracted findings — it does NOT measure retrieval-augmented Q&A. To complete the RAG-track decision we need 5–10 prompts that require the model to consume retrieved context (clinical-assist findings index, master DB excerpts) and produce safe, grounded output. Without this, we cannot prove "qwen3:14b + RAG ≥ gpt-oss dynamic standalone" on the actual production task shape.
2. **(P2) qwen3:30b-a3b retry with explicit Modelfile thinking-off template**. Today's failure is Ollama-template-driven, not model capability. If we craft a Modelfile that strips the reasoning trace at the system-prompt level (or use a quantized variant with reasoning disabled in the GGUF), 30B-A3B becomes a fair comparison point against 35B-A3B.
3. **(P3) gemma3:12b D-fence prompt-reinforcement experiment**. Add `"do NOT wrap JSON in markdown fences"` to D system prompts and re-run only gemma3 D smoke. If HF drops to 0, gemma3:12b becomes a third RAG candidate (8.1 GB, Korean-strong, dense).
4. **(P4) Part 2 remaining models** (Gemma 4 26B/31B, magistral, exaone4 split) — unchanged from previous backlog, but priority lowered given strong RAG-track evidence here.
5. **(P5) Operational latency benchmark** of the three top candidates (gpt-oss-20b dynamic, qwen3:14b, Qwen 35B-A3B thinking-on maxtok8k) under concurrent-request load. Wall-clock per-prompt in eval mode is single-request — production behavior will differ.

## Notes for Next Session

- Round 9 closes the "is a smaller model viable?" question with a clear YES (qwen3:14b at 3.31, qwen3:8b at 3.38 — both HF 0). The next milestone is RAG eval design.
- The qwen3:30b-a3b finding is the single most important operational caveat from this round: **the `reasoning_effort=none` OpenAI-compatible parameter is silently ignored by Ollama for this specific model.** Output-buffer cap hits + visible reasoning trace + PHI leak in D_02 confirmed. Do not include qwen3:30b-a3b in production without a Modelfile workaround.
- mixtral-8x7b D_03 early-EOT (19 tokens, partial JSON) is a separate weirdness. Could be a prompt-tokenization quirk with the system prompt's medical content + JSON schema instructions. Not investigated further.
- All 5 raw + scored artifacts preserved with exact timestamps. Reproducibility maintained.

## End of Report
