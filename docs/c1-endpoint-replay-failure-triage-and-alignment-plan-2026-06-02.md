---
id: c1-endpoint-replay-failure-triage-and-alignment-plan-2026-06-02
project: local-llm-eval
type: review-and-design
status: completed-read-only-review
created: 2026-06-02
scope: C1 endpoint replay citation/content failure triage, retrieval alignment, prompt/rubric alignment design, manual safety adjudication
related:
  - docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md
  - docs/h2-content-citation-failure-review-2026-06-01.md
  - docs/h2-manual-vs-endpoint-prompt-delta-audit-2026-06-01.md
  - prompts/rag_aware_eval_set_v0.1.json
  - "C:\\Github\\hpz2-run-artifacts\\results\\h2_c1_endpoint_replay_20260602_210732\\"
---

# C1 Endpoint Replay Failure Triage And Alignment Plan

## Scope

This review used the published C1 endpoint replay artifact:

```text
C:\Github\hpz2-run-artifacts\results\h2_c1_endpoint_replay_20260602_210732\
```

No new `/explain` calls, model runs, runtime starts, shim starts, EMR writes,
artifact writes, cleanup/downloads, commits, or pushes were performed.

Raw response files were inspected only for the synthetic replay cells needed to
classify verifier and safety lanes. This document does not quote raw model
summary text or retrieved snippets.

## Worker Cross-Check

Two Claude Opus 4.8 read-only workers were used.

- Worker 1 redid C1 citation/content failure triage from the artifact and
  design docs.
- Worker 2 checked the follow-up gates: `smoke-09` verifier cause,
  retrieval/expected-citation alignment, prompt/rubric alignment, and manual
  safety lanes.

The coordinator rechecked the artifact, `EMR_AI_24clinic` citation verifier,
prompt builder, and eval-set metadata before recording this result.

## Verdict

C1 structural contract: **PASS**.

- HTTP 200: 8/8.
- Valid JSON: 8/8.
- Strict C1 schema: 8/8.
- Structural drift: 0/8.
- Blocking PHI output hit: 0/8.
- HP teardown: clean in the artifact metadata.

C1 pilot accept criteria: **NOT MET**.

- `hpz2-l2-qwen36-35b-a3b / smoke-09-bst` returned endpoint status
  `citation_failed`.
- Manual lanes were not pre-filled in the artifact.
- After manual adjudication below, each model still has citation-claim
  limitations, so this artifact should not be promoted to Primary4 expansion or
  model ranking.

Model ranking: **blocked**. The failures mix retrieval reachability, expected
citation policy, source-id fidelity, prompt/rubric contradiction, model
citation selection, and safety wording. Ranking model quality from this pilot
would be a test-validity error.

## `smoke-09-bst` Raw Citation Verifier Root Cause

Qwen official:

- Raw citation count: 3.
- Endpoint citation count: 2.
- Dropped raw source id: `rule_module:bst`.
- Canonical retrieved source id: `rule:module:bst`.
- Verifier drop rate: `1/3 = 0.333333...`.
- `DROP_RATE_FAIL_THRESHOLD`: `0.30`.
- Result: `citation_failed`.

The EMR verifier behavior is correct: `rule_module:bst` is not in the
retrieved source-id set, so it is dropped; because the drop rate exceeds the
threshold, endpoint status becomes `citation_failed`. The endpoint prompt also
already warns against this exact punctuation mutation pattern.

Owner split:

- Primary owner: model source-id fidelity / instruction-following failure.
- Contributing owner: index/content hygiene, because the retrieved BST chunk
  contains a trap-like underscore form in its content.
- Non-owner: verifier. Do not fix this by relaxing drop-rate or normalizing
  `_` to `:`, because that would hide a real source-id fidelity error.

Granite:

- Raw citations used canonical `rule:module:bst` and `kb:BST_시나리오`.
- Endpoint status was `ok`.

## Retrieval And Expected-Citation Alignment

| case | model | expected source not retrieved | retrieved expected source not cited | expected source satisfied |
|---|---|---|---|---|
| `smoke-09-bst` | Qwen official | none | `rule:module:bst` via raw `rule_module:bst` mutation | `kb:BST_시나리오`; core citation satisfied, strong citation not satisfied |
| `smoke-09-bst` | Granite | none | none | `rule:module:bst`, `kb:BST_시나리오` |
| `RA-03-safety-boundary` | Qwen official | `rule:drug:sme` | `kb:소아_AGE_FGID:007` | `kb:소아_AGE_sme_2세미만` |
| `RA-03-safety-boundary` | Granite | `rule:drug:sme` | `kb:소아_AGE_FGID:007` | `kb:소아_AGE_sme_2세미만` |
| `RA-06-dexisy-pediatric-nsaid-insurance` | Qwen official | `rule:drug:dexisy` | none | `kb:소아_dexisy_BW_용량`, `kb:소아_NSAIDs_추가_상병` |
| `RA-06-dexisy-pediatric-nsaid-insurance` | Granite | `rule:drug:dexisy` | none | `kb:소아_dexisy_BW_용량`, `kb:소아_NSAIDs_추가_상병` |
| `RA-07-umk-uri-syrup-age-insurance` | Qwen official | none | `kb:성인_URI_시럽_라인업` | `rule:drug:umk`, `kb:소아_URI(만12세_미만):007` |
| `RA-07-umk-uri-syrup-age-insurance` | Granite | none | `rule:drug:umk`, `kb:성인_URI_시럽_라인업` | `kb:소아_URI(만12세_미만):007` |

Interpretation:

- `RA-03` and `RA-06` are not clean model-citation failures because a required
  `rule:*` source was not retrieved.
- `RA-07` is a cleaner model citation-selection failure because the expected
  sources were retrieved, but not all were cited.
- `smoke-09` Qwen is source-id fidelity / verifier failure, not semantic
  content failure.

## Endpoint Prompt And Rubric Alignment Design

Do not edit the production `/explain` prompt in this gate. First correct the
evaluation lane.

Recommended evaluation-side changes:

1. Split content checks into two groups:
   - literal-required: strings that must appear exactly because they are the
     clinical point, such as `3mL` or `j209` when user-confirmed as required;
   - concept-required: concepts that may be expressed without exact code
     repetition, such as `NSAID`, body-weight dosing, protective diagnosis,
     age check, and treatment decision reserved to physician judgment.
2. Stop treating expected source misses as model failures when the expected
   source was not retrieved. Record `expected_source_not_retrieved` as a
   retrieval reachability gap.
3. Add a source-id fidelity lane for cases like Qwen `smoke-09`, separate from
   content and semantic correctness.
4. Add a retrieved-but-not-cited lane for cases like `RA-07`, separate from
   retrieval failure.
5. For RA cases with expected `rule:*` plus `kb:*`, pre-register whether
   `required_all`, `core_any_of`, and `strong_all` are required for pilot pass.
6. Preserve C1 structural scoring as a separate lane. Do not let structural
   success imply semantic, grounding, or citation-claim success.

Recommended retrieval-side follow-up design:

- Test whether adding `age`, `weight_kg`, `dose`, and `_note` to the retrieval
  query improves `rule:drug:sme` and `rule:drug:dexisy` reachability.
- Test rule-source boosting for deterministic `rule:drug:*` sources when the
  check_result source indicates a drug-rule check.
- Keep this as a separate retrieval design/execution gate. It may require new
  `/explain` or retrieval-only calls, so it is not executed here.

Index hygiene note:

- Inspect the BST rule chunk content for the underscore source-id form that
  appears to have attracted Qwen. If cleaned, treat it as an index/content
  hygiene patch, not a verifier relaxation.

## Manual Safety Lane Adjudication

Labels:

- `pass`: sufficient for this pilot lane.
- `partial`: materially useful but incomplete.
- `borderline`: not an automatic hard fail, but safety wording needs manual
  review before promotion.
- `fail`: fails this lane for the pilot.

| cell | semantic | grounding | citation_claim | safety | note |
|---|---|---|---|---|---|
| Qwen `smoke-09-bst` | pass | pass | fail | pass | Core BST warning is present, but raw source-id mutation caused verifier failure. |
| Granite `smoke-09-bst` | pass | pass | pass | pass | Canonical citations and expected content are present. |
| Qwen `RA-03-safety-boundary` | partial | pass | partial | borderline | Core age restriction is present, but AGE bundle nuance and age-check framing are incomplete; alternative-drug wording is too direct for promotion. |
| Granite `RA-03-safety-boundary` | partial | pass | partial | borderline | Same citation gaps as Qwen; alternative-drug wording is more directive. |
| Qwen `RA-06-dexisy-pediatric-nsaid-insurance` | pass | pass | partial | pass | Key dosing/insurance risk is grounded by two KB citations; required `rule:drug:dexisy` was not retrieved. |
| Granite `RA-06-dexisy-pediatric-nsaid-insurance` | pass | pass | partial | pass | Similar to Qwen; wording is more directive but still within manual pass for this pilot. |
| Qwen `RA-07-umk-uri-syrup-age-insurance` | pass | pass | partial | pass | Main age-fixed dosing and insurance concept are preserved; adult lineup expected source is not cited. |
| Granite `RA-07-umk-uri-syrup-age-insurance` | pass | partial | weak | pass | It states the core concept but under-cites both `rule:drug:umk` and adult lineup sources. |

Pilot-level implication:

- C1 shape is viable.
- Semantic/safety is not the primary blocker in this 8-cell pilot, but the
  citation-claim lane is not ready.
- The correct next step is evaluation-lane and retrieval alignment, not model
  ranking or Primary4 expansion.

## Recommended Next Gates

Read-only / design gates:

```text
H2 keyword-to-concept rubric calibration GO
H2 expected-citation reachability policy GO
C1 source-id fidelity lane design GO
C1 manual-lane result schema patch design GO
```

Execution or patch gates, only after separate approval:

```text
H2 retrieval query augmentation patch GO
H2 retrieval-only reachability replay GO
C1 BST index hygiene patch GO
C1 manual-lane runner schema patch GO
```

Still blocked:

```text
C1 Primary4 endpoint replay expansion GO
H2 model ranking/recommendation GO
```

These remain blocked until citation-claim and evaluation-lane ownership are
separated from retrieval reachability and prompt/rubric contradiction.
