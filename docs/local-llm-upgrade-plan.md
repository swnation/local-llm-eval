# Track 2 — Local LLM Upgrade Plan

> Purpose: separate forward-looking local LLM infrastructure plan from the completed v0.2 experiment track.
> Last updated: 2026-05-16.

---

## 1. Why This Track Exists

The v0.2 quick rerun answered one narrow question:

> Which currently available local models can safely assist clinical-assist with charting cleanup, NEEDS_REVIEW explanation, rule-finding prose, and JSON+PHI summaries?

The upgrade track answers a broader question:

> How should the local LLM environment evolve so future evaluation and production work is more reliable, cheaper to run, and easier to review?

This plan is intentionally separate from the v0.2 result ranking. A hardware/runtime change must not silently rewrite the interpretation of the existing f16/default-KV baseline.

---

## 2. Guiding Principles

1. Keep evaluation baselines comparable.
   - Record runtime, KV cache type, context length, template, reasoning mode, and model variant.
   - Do not mix q8 KV or larger-context results into the f16 quick rerun table without labels.

2. Favor measured role fit over social proof.
   - Reddit/LocalLLM threads can raise candidate priority, but this repo decides by the v0.2 eval set.

3. Prioritize production safety over average score.
   - JSON-only hard_fail and PHI safety are gating signals for automation.
   - High prose quality does not make a model safe for D.

4. Prefer simple operations unless role split wins clearly.
   - A single `gpt-oss-20b` with dynamic effort is easier to operate than multiple role-specific models.
   - Role split remains viable if formatter/reviewer gains are large enough.

---

## 3. Runtime Policy: KV Cache

### Current baseline

The 2026-05-16 quick rerun used Ollama defaults, effectively the baseline runtime for this report set.

### Candidate policy

For constrained-memory future rounds, test:

```text
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
```

Rationale:

- q8 KV can reduce KV memory roughly by half compared with f16.
- q8 KV is a reasonable first compromise before attempting q4 KV.
- q4 KV should be treated as experimental for quality-sensitive clinical text.

Operational cautions:

- Ollama KV cache type is a global server option.
- On Windows, environment variable changes require restarting Ollama.
- q8 KV results must be labeled separately from the default/f16 quick rerun.
- Some architectures or Ollama versions may not apply KV quantization as expected; verify through logs or memory behavior before trusting the result.

### Recommended naming

Use explicit suffixes:

- `quick_rerun_f16_default`
- `quick_rerun_q8kv_flash`
- `qwen35b_preview_32gb_q8kv`

---

## 4. Immediate Upgrade Track: Qwen3.6-35B-A3B Preview

Priority: high.

Reason:

- It is already planned for 64GB part 2.
- It is a plausible challenger to `gpt-oss-20b`.
- Its MoE active-parameter profile may make a 32GB preview possible even before RAM upgrade.

Run it as **exploratory preview**, not as a replacement for the finished v0.2 quick rerun.

Suggested sequence:

1. Try default/f16 runtime first if the model loads.
2. If memory fails, retry with q8 KV + flash attention.
3. Run D smoke first.
4. If D smoke produces usable output or informative failures, run all 13 prompts.
5. Score with the same `score_runner.py`.
6. Report separately as `part2_preflight`, not as baseline rank.

Required metadata:

```text
model_id:
quant:
provider: ollama
num_ctx:
kv_cache_type:
flash_attention:
reasoning/thinking mode:
load result:
OOM or partial offload:
```

Decision value:

- If Qwen preview is strong and automation-safe, it becomes part 2 priority 1.
- If it fails D by reasoning trace/fence/prose, it may still be a prose reviewer candidate.
- If it OOMs on 32GB, defer without penalty to 64GB part 2.

### Result snapshot (2026-05-16)

Status: completed as `part2_preflight_32gb_defaultkv_thinking_off`.

- Model: `qwen3.6:35b-a3b` via Ollama, Q4_K_M, 23GB local pull.
- Runtime: default KV / default flash setting / `reasoning_effort='none'`.
- D smoke: avg **4.67**, hard_fail **0**.
- Full v0.2 13 prompts: avg **3.31**, hard_fail **0**.
- v0.3 rescore of the same raw full run: avg **3.38**, hard_fail **0**; D_json_phi becomes **5.00** after the D_01 false-positive forbidden fix.
- Category scores: A 2.50 / B 3.33 / C 3.00 / D 4.67.
- Interpretation: strong automation-safety signal and better total avg than `gpt-oss-20b` dynamic effort (3.15 HF0), but A abbreviation preservation and B_01 exact/name mismatch wording still need review. Treat as **64GB part 2 priority 1 challenger**, not silent replacement for the completed baseline.

Tracked report: `reviews/qwen35b-preview-32gb-2026-05-16-report.md`.

---

## 5. gpt-oss-20b Upgrade Work

### Operational rule (R4.1 GO, 2026-05-16 — pinned)

> **medium improves C only; medium is unsafe for D JSON-only.**

Verified production path (after R4.1 sign-off):

```text
A/B prose:     reasoning_effort = low      # medium ties low on score, low is faster
C prose:       reasoning_effort = medium   # medium fixes case_id-only short replies (avg 2.00 -> 3.33)
D JSON-only:   reasoning_effort = low      # medium produces ```json fence on D_02 (hard_fail)
```

R4 MF-1 verification (`reviews/quick-rerun-2026-05-16-report.md §5.7`) collapsed the original "A/B/C=medium / D=low" recommendation into "C=medium only / D/A/B=low". Do not widen medium to A/B/D without re-running the same comparison.

### Result snapshot

| Category | low (baseline) | medium (§5.7) | Δ |
|---|---|---|---|
| A_charting | 2.50 | 2.50 | 0 |
| B_needs_review | 2.33 | 2.33 | 0 |
| C_rule_finding | 2.00 | 3.33 | +1.33 |
| D_json_phi | 4.67 | 3.00 (D_02 hard_fail) | -1.67 |
| HF# | 0 | 1 | +1 |

Scenario C composite under the pinned policy:
`(A:2.50x4 + B:2.33x3 + C:3.33x3 + D:4.67x3) / 13 = 3.15`, hard_fail 0.

### Open follow-ups (selective, post-64GB OK)

- gpt-oss `reasoning_effort = "high"` for 1~2 prompts to measure medium-vs-high trade-off.
- ministral with explicit Mistral V7 template to diagnose the D_02 1-token EOT pattern.
- Re-run the full 13-prompt grid only if Ollama/runtime defaults change in a way that could affect baseline comparability.

---

## 6. HARI ChatML Track

Current finding:

- Default HARI imported Modelfiles appear to suffer from template issues.
- ChatML variants improve A and C and remove input-echo artifacts.
- D remains unsafe because reasoning traces or PHI echoes can appear around JSON.

Policy:

- Future HARI evaluation should use ChatML Modelfiles by default.
- Keep default HARI results only as historical evidence.
- Do not use HARI for direct JSON-only automation unless a separate trace-stripping policy is explicitly approved.

Best fit:

- `hari-14b-i1-chatml` as Formatter-only candidate.

Low priority upgrade:

- Try Q4_K_M variants only after template and reasoning-trace behavior are stable.
- Quant change is unlikely to fix D hard_fail behavior.

---

## 7. Part 2 Hardware Plan: 64GB vs 128GB

Current recommendation:

- 64GB is the next practical milestone.
- 128GB is useful later for very long context and heavier parallel experiments, but it is not the immediate blocker for the current production decision.

Before RAM upgrade:

1. Complete R4 result-interpretation sign-off.
2. Run gpt-oss medium A/B/D.
3. Optionally run Qwen3.6-35B-A3B 32GB preview.

After 64GB:

1. Run Qwen3.6-35B-A3B thinking on/off.
2. Run Gemma 4 26B/31B.
3. Retry EXAONE 32B with GPU+CPU split or smaller quant.
4. Retry magistral/ministral with explicit template if still relevant.

When to consider 128GB:

- repeated 64GB OOM for priority models
- long-context RAG experiments beyond 32K/64K
- multiple loaded models for role split
- local agent memory experiments with large retained context

---

## 8. Retrieval / Memory Track

Immediate completed step:

- `tools/build_findings_index.py`
- `results/findings_index.jsonl`
- `results/findings_index.README.md`

This is not a full RAG system, but it is the first practical memory layer:

- one line per scored prompt/model result
- model, variant, prompt, category, score, tags, hard_fail, excerpt
- fast filtering for review questions

Next increments:

1. Add a small query helper:
   - `tools/query_findings_index.py`
   - filters by category, model, tag, hard_fail, min/max score
2. Add a packet builder:
   - generate R4/R5 review excerpts from findings index
3. Add document section index:
   - split README/report/contract into heading-based chunks
   - store `doc_id`, `heading`, `path`, `text_excerpt`
4. Consider MCP/Serena-style integration only after local files prove useful.

Production clinical-assist RAG remains a separate design track. It should not be mixed into local-llm-eval scoring.

---

## 9. RAG and Agent Tooling: What to Borrow

Useful ideas:

- Keep a compact project memory document (`PROJECT_CONTEXT.md`).
- Index results into retrieval-friendly lines.
- Generate review packets instead of dumping entire raw outputs.
- Separate current baseline from exploratory runtime experiments.

Not adopted yet:

- Serena MCP
- OpenCode replacement
- Redis/SQLite in-memory production RAG
- patient-specific production memory

Reason:

- local-llm-eval is still an evaluation harness.
- production memory raises additional privacy, lifecycle, and PHI containment questions.

---

## 10. Decision Matrix

| Track | Priority | Status | Next action |
|---|---:|---|---|
| R4 sign-off | high | completed | R4.1 GO, Track 1 closed |
| gpt-oss medium A/B/D | high | completed | dynamic effort pinned: A/B/D low, C medium |
| Qwen3.6-35B-A3B 32GB preview | high | completed | avg 3.31 / hard_fail 0 on v0.2; v0.3 rescore avg 3.38 / hard_fail 0 |
| q8 KV policy | medium | documented here | test in separate round, do not mix with f16 baseline |
| v0.3 scoring cleanup | high | completed | use `prompts/test_suite_v0.3.json` for new runs |
| HARI ChatML | medium | proven useful for A | make ChatML the default HARI path |
| findings index | medium | implemented | add query helper if useful |
| Serena/MCP-style memory | low for eval, medium for production | concept only | separate design doc |
| Q4_K_M HARI quant | low | not run | defer |

---

## 11. Repo Hygiene

Every future experiment should record:

- model label
- source model / quant
- provider
- Modelfile/template
- context length
- KV cache type
- flash attention
- reasoning mode
- prompt subset
- scorer contract version
- score output path
- whether it is baseline, preview, or part2

Suggested result labels:

```text
_scored_quick_rerun_20260516.json
_scored_gpt_oss_medium_abd_20260516.json
_scored_qwen35b_preview_32gb_q8kv_20260516.json
_scored_part2_64gb_qwen35b_thinking_off_2026xxxx.json
```

---

## 12. Immediate Next Step

Recommended two-track execution:

1. Keep q8 KV as an explicit runtime-matrix experiment, not a silent default change.
2. Optionally run gpt-oss `reasoning_effort='high'` on 1~2 prompts.
3. After 64GB, rerun Qwen3.6-35B-A3B thinking-off/on and then Gemma 4 26B/31B using v0.3 prompts.
