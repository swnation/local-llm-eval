# Track 1 — v0.2 Local LLM Eval Experiments

> Purpose: durable summary of the completed v0.2 evaluation track.
> Source of truth for raw details: `reviews/quick-rerun-2026-05-16-report.md`.
> Last updated: 2026-05-16.

---

## 1. Scope

This track covers the **local-llm-eval v0.2 experiment line**:

- prompt set validation after GPT R1 GO
- harness conversion from legacy v1 to v0.2
- D-category smoke test
- automatic scoring implementation
- 32GB quick rerun
- follow-up experiments needed to interpret the quick rerun
- R4 result-interpretation review packet

This track does **not** decide final production adoption. Production adoption remains provisional until 64GB part 2 evaluates larger candidates such as Qwen3.6-35B-A3B.

---

## 2. Fixed Evaluation Contract

The local LLM role is fixed:

- It explains, cleans up, summarizes, and reviews deterministic pipeline output.
- It does not perform OCR, canonical extraction, hard safety judgment, automatic correction, prescription change, or final clinical confirmation.

The v0.2 prompt set has 13 prompts:

| Category | Count | Purpose |
|---|---:|---|
| A_charting | 4 | raw chart memo cleanup |
| B_needs_review | 3 | explain matcher `NEEDS_REVIEW` reasons |
| C_rule_finding | 3 | convert deterministic rule findings into report prose |
| D_json_phi | 3 | JSON-only schema compliance and PHI-safe summaries |

Scoring contract:

- `hard_fail -> forbidden -> required -> format -> score`
- D prompts use `required_layer = "json_schema"` with strict exact keys.
- A prompts use `ko_with_medical_en_allowed`; `MIXED_LANGUAGE` must not become an automatic hard fail there.
- D prompts require `response.strip()` to be a JSON object. Markdown fences or prose around JSON are hard fail.

Primary specs:

- `prompts/test_suite_v0.2.json`
- `SCORING_CONTRACT.md`
- `score_runner.py`

---

## 3. Completed Rounds

| Round | Scope | Verdict | Result |
|---|---|---|---|
| R1 | v0.2 prompt set | GO | quick rerun allowed |
| R2 | Step 1 harness/scoring schema | CONDITIONAL GO -> closed | D required-layer and schema exactness fixed |
| R3 | `compute_score` order | CONDITIONAL GO -> closed | forbidden/required major failures now score 2 before score 3 |
| R4 | quick rerun interpretation | packet ready | waiting for result-interpretation sign-off |

R4 packet:

- `reviews/review-packet-v0.2-r4-quick-rerun.md`
- required attachment: `reviews/quick-rerun-2026-05-16-report.md`

---

## 4. Execution Timeline

| Step | Result |
|---|---|
| Environment check | 32GB RAM, RTX 5080 16GB VRAM, Ollama 0.24.0 |
| Ollama import | `hari-8b`, `hari-14b`, `ministral` imported; `ministral` needed `num_ctx 8192` |
| D smoke | `gpt-oss` passed D JSON-only; `gemma4` failed exactly by JSON fence |
| scorer fixture validation | `gpt-oss` D scores `4/5/5`, `gemma4` D scores `0/0/0` |
| full quick rerun | 7 models x 13 prompts completed in about 8.5 minutes |
| exaone4 retry | failed due to 16GB VRAM limit for a 17GB model |
| follow-up experiments | ChatML variants, gpt-oss medium C, D_02 retries, clinical-hari A_02 retries |

---

## 5. Current Ranking Interpretation

The quick rerun produced a useful but provisional ranking:

| Candidate | Current interpretation |
|---|---|
| `clinical-hari-q5-current` | score leader; strong B/C/D; A_02 one-off empty-response quirk and JSON-style charting output require operational guidance |
| `gpt-oss-20b-low` | hard_fail 0; strong D; weak C at low effort |
| `gpt-oss-20b-medium` | C improves from 2.00 to 3.33; A/B/D medium still needs one full check |
| `hari-14b-i1-chatml` | best A/formatter candidate; D is not automation-safe because reasoning trace leaks around JSON |
| `hari-8b-i1-chatml` | similar but weaker than 14b; ChatML fixes template echo problems |
| `gemma4-latest` | readable Korean prose; D fails through consistent JSON fence |
| `ministral-3-14b-reasoning` | usable A/B/C; D_02 repeats 1-token EOT failure |
| `exaone4-32b-iq4-4k` | not evaluated on 16GB VRAM; retry in part 2 with split/offload or smaller quant |

Provisional production recommendation from the report:

> `gpt-oss-20b` single-model operation with dynamic reasoning effort:
> D = low, A/B/C = medium.

Reason:

- no hard_fail observed in the baseline
- D JSON-only automation is stable at low
- C recovers at medium
- single-model operation avoids model-swap overhead
- license/operation story is simpler than model-splitting

This is provisional. It needs `gpt-oss medium` A/B/D validation before being treated as a serious production candidate.

---

## 6. Known Experiment Findings

### D JSON-only

- `clinical-hari-q5-current` and `gpt-oss-20b-low` are the only D-automation-safe candidates in the 32GB quick rerun.
- `gemma4` D content can be good but fenced JSON makes it hard fail under v0.2 strict rules.
- reasoning models that emit `<think>` or prose before JSON should not be wired directly into a JSON-only pipeline without a separate post-processing and safety decision.

### A charting

- `hari-14b-i1-chatml` is the best current formatter-only candidate.
- ChatML Modelfiles should replace the default imported HARI Modelfiles for any future HARI evaluation.
- `clinical-hari-q5-current` A_02 retry produced normal responses but in JSON form, so it needs a stronger prose overlay if used for charting cleanup.

### B/C review prose

- `clinical-hari-q5-current` is strongest on B/C among baseline models.
- `gpt-oss-20b-low` under-produces in C; `reasoning_effort = "medium"` fixes much of this.

---

## 7. v0.3 Candidate Fixes

Must candidates from the report:

1. Narrow D_01 forbidden `"변경"` so legitimate findings such as "당뇨 약제 변경" are not false positives.
2. Strengthen or broaden A_04 `[확인 필요]` marker handling.
3. Revisit sentence-count tolerance for verbose reasoning models.

Should candidates:

1. Decide whether reasoning traces should be ignored, stripped, or treated as true JSON-only hard failures for D.
2. Improve `MIXED_LANGUAGE` handling for very short, under-produced responses.
3. Document operational guidance for `gpt-oss` reasoning effort.
4. Document HARI ChatML Modelfiles as the only recommended HARI import mode.

Backlog:

- D_02 PHI substring generalization with input-derived `forbidden_phi_values`
- C rule IDs aligned with actual production `rules.json`
- optional A handoff prompt
- category weights
- format-only-fail score policy

---

## 8. Next Actions

Immediate:

1. Send R4 packet + report for result-interpretation sign-off.
2. If R4 GO, run `gpt-oss-20b medium` on A/B/D, because only C has been checked at medium.
3. Update this track document with R4 verdict and the medium A/B/D result.

Then:

1. Decide v0.3 minimal prompt/scorer fixes.
2. Prepare 64GB part 2 configs and run order.
3. Keep 32GB and 64GB results separate in reports.

---

## 9. Retrieval Index

`results/findings_index.jsonl` is the fast lookup surface for this track.

Useful questions it can answer:

- Which model/prompt combinations failed D because of `JSON_EXTRA_TEXT`?
- Which A prompt produced `PHI_LEAK`?
- Which prompt/model pairs scored 5?
- What is each model's D average?

Regenerate with:

```powershell
python tools/build_findings_index.py
```

---

## 10. Files

Core files:

- `reviews/quick-rerun-2026-05-16-report.md`
- `reviews/review-packet-v0.2-r4-quick-rerun.md`
- `results/_scored_quick_rerun_20260516.json`
- `results/_scored_gpt_oss_medium_20260516.json`
- `results/_scored_hari14b_chatml_20260516.json`
- `results/findings_index.jsonl`
- `results/findings_index.README.md`

Implementation:

- `eval_runner_auto.py`
- `score_runner.py`
- `SCORING_CONTRACT.md`
- `tools/build_findings_index.py`

