---
id: h2-output-contract-calibration-plan-2026-06-01
project: local-llm-eval
type: execution-plan
status: review-ready-design
created: 2026-06-01
scope: Output-contract calibration before further H2 model-quality ranking
related:
  - docs/h2-manual-vs-endpoint-prompt-delta-audit-2026-06-01.md
  - docs/h2-content-lane-supplement-result-2026-06-01.md
  - docs/hpz2-llamacpp-h2-output-contract-calibration-runner-2026-06-01.md
  - docs/rag-goals-evaluation-principles-v0.1.md
  - docs/rag_aware_eval_design_r0.md
  - prompts/rag_aware_eval_set_v0.1.json
---

# H2 Output-Contract Calibration Plan

## Status

Review-ready design. The runner build is present in
`tools/hpz2_llamacpp_h2_output_contract_calibration_runner.py`, with the
synthetic fixture in `prompts/h2_output_contract_calibration_v0.1.json`.

This document does not authorize model execution, `/explain`, llama-server
startup, shim startup, EMR writes, cleanup/download, commit, push, or backup.

## Why This Gate Exists

The H2 endpoint run mixed several questions:

1. Does the model understand the retrieved clinical evidence?
2. Can the model follow the exact output contract?
3. Can a normalizer recover a good answer into the app contract?
4. Does the real `/explain` endpoint pass retrieval, prompt, verifier, and PHI
   gates end to end?

The manual-vs-endpoint audit showed that the current endpoint prompt/rubric can
penalize good answers for format, citation, retrieval, or literal-keyword
reasons. Before more model ranking, we need a small output-contract calibration
lane.

## Goal

Find the least fragile output format that local models can follow while
preserving clinical meaning and exact source attribution.

This gate answers:

- Which output contracts do Primary 4 models follow reliably?
- Which failures are soft envelope failures that a normalizer can recover?
- Which failures are hard semantic/citation failures?
- Which contract should be promoted as a hypothesis for later endpoint or replay
  tests?

This gate does not decide final `/explain` model ranking by itself.

## Execution Topology

Plan phase:

- Host: Main PC.
- Scope: design/review only.
- No model execution.

Future run phase, only after explicit GO:

- Host: HP Z2.
- Backend: direct llama.cpp `/v1/chat/completions`, not `/explain`.
- Data: synthetic non-PHI evidence packs only.
- Raw responses: stored, because calibration requires exact envelope analysis.
- EMR repo: read-only and not called.
- Shim: not used.

Rationale: direct llama.cpp isolates output-format behavior from endpoint
retrieval, EMR prompt builder, shim translation, and citation verifier policy.

## Model Scope

Default run scope is Primary 4:

- `hpz2-l2-qwen36-35b-a3b`
- `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`
- `hpz2-l2-qwen36-35b-a3b-mtp-q8`
- `hpz2-l2-granite-41-30b-q4km`

Reference models are out of scope unless separately approved.

The first execution should be a pilot, not the full Primary 4 matrix:

- Pilot default: Qwen official + Granite only.
- Expansion to Primary 4 requires pilot artifacts, raw-output safety scan, and
  teardown evidence to pass.

## Prompt Inputs

Use 3 synthetic non-PHI evidence packs. They should be small enough for manual
review and broad enough to catch contract fragility.

| case | purpose | evidence shape |
|---|---|---|
| `OC-01-simple-one-source` | one conclusion, one required source | one rule chunk, one obvious source ID |
| `OC-02-two-source-nuance` | rule + KB nuance preservation | one rule chunk and one KB exception/threshold chunk |
| `OC-03-distractor-source` | citation selection under distractor | two relevant chunks plus one plausible but irrelevant chunk |

Synthetic source IDs should include realistic punctuation:

- `rule:drug:demo`
- `kb:소아_DEMO_용량:007`
- `kb:보험_DEMO_예외_2026-01`

Do not include patient names, chart numbers, real clinical notes, or production
PHI-like identifiers.

## Contract Variants

Test the same evidence and task under four output-contract variants.

### C1. Native Endpoint Contract

Purpose: measure direct compatibility with current `/explain` verifier.

Expected raw shape:

```json
{"summary":"한국어 설명","citations":["[source_id]"]}
```

Rules:

- JSON only.
- Top-level keys exactly `summary` and `citations`.
- `summary` is a string.
- `summary` should be no more than 150 Korean characters.
- `citations` is an array of bracketed strings.
- Every citation must exactly match one valid source ID after bracket stripping.

Use this as Native Contract Lane evidence only. Do not let C1 outrank semantic
quality by itself.

### C2. JSON Source-ID Contract

Purpose: test whether brackets are the fragile part.

Expected raw shape:

```json
{"summary":"한국어 설명","citations":["source_id"]}
```

Rules:

- JSON only.
- Top-level keys exactly `summary` and `citations`.
- Citations are bare source ID strings with no brackets.
- A runner-side normalizer may wrap source IDs for endpoint compatibility.

This is a Normalizer Lane candidate. It is a soft fail for current endpoint
native compatibility but not for model semantic ability.

### C3. Relaxed JSON Answer Contract

Purpose: test whether `summary` and strict key naming are fragile.

Expected raw shape:

```json
{"answer":"한국어 설명","sources":["source_id"]}
```

Rules:

- JSON only.
- Allowed top-level keys are exactly `answer` and `sources`.
- `sources` are bare source ID strings.
- Normalizer maps `answer -> summary` and `sources -> citations`.

This is useful if models reliably produce meaningful answers but resist the
current endpoint key names.

### C4. Freeform With Inline Citations

Purpose: measure semantic model potential with minimal envelope pressure.

Expected raw shape:

```text
한국어 설명 문장. [source_id]
```

Rules:

- No JSON requirement.
- Every clinical claim should be followed by one or more bracketed source IDs.
- A runner-side extractor may recover summary text and citations.

This is Semantic RAG Lane plus Normalizer Lane evidence, not native endpoint
evidence.

## Matrix Size

Default pilot matrix:

```text
2 models x 3 cases x 4 contract variants = 24 calls
```

Pilot pair: Qwen official + Granite, because they cover the main family split.

Expansion matrix, only after a clean pilot:

```text
4 models x 3 cases x 4 contract variants = 48 calls
```

Both are intentionally small compared with an endpoint matrix. The purpose is
gross contract calibration, not model ranking.

## Runtime Controls For Future Run

Keep runtime controls fixed so the run tests output contract behavior, not
sampling or endpoint drift:

| control | value |
|---|---|
| backend | direct llama.cpp `/v1/chat/completions` |
| endpoint path | no `/explain` |
| schema mode for C1-C3 | `response_format: {"type":"json_object"}` |
| schema mode for C4 | no `response_format`; freeform allowed |
| temperature | `0` or the project low-variance default |
| max tokens | enough for contract completion, default target `512` |
| raw response | store exact raw content for every cell |
| prompt/profile | same prompt template per contract across all models |

Do not mix `json_schema` into the first calibration run. The earlier H2 A/B
showed no practical endpoint difference between `json_object` and `json_schema`
for the tested cells, and adding it here would double the matrix before the
basic contract question is answered. Reopen it only if `json_object` is the
suspected failure source.

## Raw Response Safety Controls

Raw response storage is required for this calibration, but only because the
fixtures are synthetic and non-PHI.

Preflight:

- Write a synthetic fixture manifest listing every prompt, evidence chunk, and
  source ID.
- Run PHI/PHI-like pattern scan over the fixture manifest before execution.
- Abort before model startup if any prompt includes a name, chart number,
  registration number, phone number, resident-registration-like pattern, or
  production patient text.

Postflight:

- Run PHI/PHI-like scan over raw responses, summaries, logs, and aggregate JSON.
- Mark artifacts as internal calibration artifacts.
- If PHI-like output appears, stop summary generation, quarantine or delete the
  raw-output file according to the runbook, and report only PHI-safe metadata.

This run must not use real `/explain` payloads, production patient notes, or
manual prompt examples that contain PHI-like text.

## Scoring Fields

Each cell should store raw response plus structured scoring.

| field | meaning |
|---|---|
| `raw_response_stored` | must be true for this calibration run |
| `parse_status` | `json_ok`, `json_recoverable`, `freeform_only`, `empty`, `invalid` |
| `contract_variant` | `C1`, `C2`, `C3`, or `C4` |
| `native_contract_pass` | raw output exactly satisfies C1 |
| `normalizer_pass` | output can be converted to `{summary, citations}` without changing meaning |
| `semantic_pass` | answer conclusion matches the evidence pack |
| `grounding_pass` | claims are supported by cited source text |
| `citation_exact_pass` | cited source IDs exist in evidence pack |
| `citation_claim_pass` | cited source supports the claim it is attached to |
| `extra_text` | text outside expected JSON when JSON was requested |
| `extra_keys` | schema keys not allowed by the selected contract |
| `missing_keys` | required keys omitted |
| `citation_format_error` | bracket/bare/object/other mismatch |
| `source_id_copy_error` | punctuation or Korean source ID altered |
| `summary_length_chars` | length after normalization |
| `failure_owner` | prompt, model, normalizer, citation, semantic, or manual_review_needed |
| `metric_risk_notes` | notes where automated scoring may mislead |

Semantic, grounding, and citation-claim fields require manual review for the
first run. Automated checks can assist but must not replace reviewer judgement.

## Decision Rules

Manual review sign-off is required for `semantic_pass`, `grounding_pass`, and
`citation_claim_pass` in the pilot.

Per-cell pass:

- Semantic cell pass = `semantic_pass`, `grounding_pass`,
  `citation_exact_pass`, `citation_claim_pass`, and `safety_pass` all true.
- Native C1 cell pass = semantic cell pass plus `native_contract_pass` true and
  `summary_length_chars <= 150`.
- Normalizer cell pass = semantic cell pass plus `normalizer_pass` true.

Per-model contract viability:

- A contract is viable for one model if at least 2/3 pilot cases pass for that
  model under that contract.
- A model has native endpoint-contract viability if C1 is viable.
- A model has normalizer-path viability if C2 or C3 is viable.
- A model has semantic-only potential if only C4 is viable.

Pilot-level contract selection:

- Prefer C1 only if both pilot models reach C1 viability.
- If C1 fails for either pilot model but C2 or C3 passes for both, promote the
  best passing normalizer-path contract as the expansion hypothesis.
- Prefer C2 over C3 when both pass, because C2 is closer to the current endpoint
  schema.
- Treat C4 as evidence of semantic potential only; it cannot be selected as the
  endpoint contract without a separate normalizer design.
- If no contract reaches 2/3 pass for both pilot models, stop and revise prompt
  templates before expanding to Primary 4.

Do not promote a contract solely because it is easy to parse. Semantic,
grounding, safety, and citation-claim correctness outrank format convenience.

## Prompt Design Requirements

Each contract prompt must include:

- the task
- the evidence pack
- the valid source ID list
- the exact requested output shape
- one positive example using a different source ID than the test evidence
- one negative example showing common failure, such as missing brackets or extra
  markdown

Avoid these in calibration prompts:

- production `/explain` style instructions that discourage literal codes unless
  the case is specifically measuring that behavior
- mixed requirements like "do not repeat codes" while the rubric requires code
  substrings
- broad clinical questions that can be answered from model prior knowledge
- real PHI or production patient text

## Artifacts

Future run should write:

```text
C:\Github\hpz2-run-artifacts\results\h2_output_contract_calibration_<timestamp>\
```

Required files:

- `output_contract_calibration_results.json`
- `output_contract_calibration_summary.md`
- per-cell raw response files
- prompt templates used for each contract variant
- HP runtime log and teardown evidence

The summary must separate:

- semantic model potential
- normalizer feasibility
- native contract convenience
- endpoint contract hypothesis for later replay

The summary must explicitly state that endpoint readiness is not assessed until
a later `/explain` lane.

## Hard Stops

- No `/explain`.
- No EMR repo write.
- No production prompt changes.
- No PHI or PHI-like identifiers.
- No cleanup/download.
- No reference-model expansion without separate GO.
- No raw response storage if any prompt accidentally contains PHI-like text.
- Stop if HP runtime fails teardown or ports remain open.

## Next Gates

Plan review gate:

```text
H2 output-contract calibration plan review GO
```

Implementation gate:

```text
H2 output-contract calibration runner build GO
```

Execution gate:

```text
HP Z2 H2 output-contract calibration run GO
```

Manual artifact gate, still recommended before execution if the user has strong
manual prompt examples:

```text
H2 manual prompt artifact intake GO
```
