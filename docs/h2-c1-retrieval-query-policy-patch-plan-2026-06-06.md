---
id: h2-c1-retrieval-query-policy-patch-plan-2026-06-06
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-06
scope: Main PC plan for H2 C1 retrieval query/top-k policy patch after retrieval-only probe
related:
  - docs/h2-c1-retrieval-only-probe-design-2026-06-06.md
  - docs/h2-c1-retrieval-citation-follow-up-plan-2026-06-06.md
  - tools/h2_c1_retrieval_only_probe.py
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - prompts/rag_aware_eval_set_v0.1.json
  - 'HP Z2: C:\Github\local-llm-eval\results\h2_c1_retrieval_probe_20260606_054108\'
---

# H2 C1 Retrieval Query Policy Patch Plan

## Project Goal Check

- direct value: turn the H2 C1 retrieval-only probe evidence into a narrow
  endpoint replay patch plan before any model ranking or Primary4 expansion.
- classification: `direct progress` with evaluation-safety value.
- narrower scope: document-only plan. No endpoint-runner implementation, eval
  set mutation, HP command, model execution, `/explain`, EMR write, commit,
  push, relay update, or librarian backup is authorized by this file.

## Scope

This is a Main PC planning gate.

The patch target is the C1 endpoint replay retrieval policy in
`tools/hpz2_llamacpp_h2_endpoint_runner.py`, but this document does not change
code.

Out of scope:

- changing `prompts/rag_aware_eval_set_v0.1.json` global defaults.
- changing EMR_AI_24clinic source code, RAG chunks, or index files.
- relaxing citation verifier behavior.
- using expected source IDs as live replay query terms.
- running HP Z2, llama-server, the shim, LM Studio, or `/explain`.
- committing, pushing, relay update, or backup.

## Evidence Boundary

This plan consumes the reviewed retrieval-only probe result produced on HP Z2:

```text
C:\Github\local-llm-eval\results\h2_c1_retrieval_probe_20260606_054108\
```

The artifact is not copied into this repo by this planning gate. The plan uses
the prior reviewed metadata and case findings to choose the next patch surface.

Repo-side facts verified for this plan:

- Current endpoint runner augmentation adds age, weight, `orders[]`,
  `order_details[].code`, dose, and note fields through
  `augment_h2_retrieval_query()`.
- The endpoint wrapper currently calls only that augmentation policy after
  `EMR_AI_24clinic.app.llm.prompt_builder.build_retrieval_query()`.
- Eval set default retrieval options remain `top_k=5`,
  `min_similarity=0.45`, and `lexical_rerank=false`.
- RA-03, RA-06, and RA-07 case-level options also use `top_k=5` and
  `min_similarity=0.45`.

## Probe Findings

### RA-03

Expected:

- `rule:drug:sme`
- `kb:소아_AGE_sme_2세미만`
- `kb:소아_AGE_FGID:007`

Finding:

- `kb:소아_AGE_sme_2세미만` reaches rank 1 under current H2 augmentation.
- `kb:소아_AGE_FGID:007` reaches rank 3 under current H2 augmentation.
- `rule:drug:sme` is not retrieved by `emr_base`, `h2_old_aug`,
  `h2_current_aug`, `primary_order_aug`,
  `oracle_expected_source_diag`, `wide_topk_diag`, or `minsim_zero_diag`.
- The source ID exists in HP chunks, so this is not a missing literal source ID
  in the chunk files.

Decision:

RA-03 is a separate source/index/searchability hygiene blocker. It should not
drive the C1 endpoint replay query/top-k patch.

### RA-06

Expected:

- `rule:drug:dexisy`
- `kb:소아_dexisy_BW_용량`
- `kb:소아_NSAIDs_추가_상병`

Finding:

- `emr_base` and `h2_current_aug` retrieve the two KB sources at top-5 but miss
  `rule:drug:dexisy`.
- `h2_old_aug` retrieves all expected sources at top-5.
- `primary_order_aug` retrieves all expected sources at top-5.
- `wide_topk_diag:h2_current_aug:k10/k20` retrieves `rule:drug:dexisy` at rank
  6.
- The source ID exists in HP chunks.

Decision:

RA-06 is a query/top-k policy problem. Current broad augmentation can push the
drug rule source just outside the C1 top-5 retrieval set.

### RA-07

Expected:

- `rule:drug:umk`
- `kb:성인_URI_시럽_라인업`
- `kb:소아_URI(만12세_미만):007`

Finding:

- `emr_base` retrieves all expected sources at top-5.
- `h2_current_aug` retrieves `rule:drug:umk` and
  `kb:소아_URI(만12세_미만):007` at top-5, but misses
  `kb:성인_URI_시럽_라인업`.
- `wide_topk_diag:h2_current_aug:k10/k20` retrieves the adult syrup lineup at
  rank 6.
- The source ID exists in HP chunks.

Decision:

The previous "pure citation-selection" classification for RA-07 must be
corrected. RA-07 has a retrieval/top-k component under the current H2 query
policy, because the expected adult lineup source is outside top-5 but inside
top-10.

## Policy Decision

There is no single non-oracle top-5 query variant that cleanly fixes both RA-06
and RA-07:

- `h2_old_aug` fixes RA-06 but does not bring the RA-07 adult lineup into
  top-5.
- `primary_order_aug` fixes RA-06 but does not bring the RA-07 adult lineup
  into top-5.
- `h2_current_aug` misses both at top-5, but both become reachable at top-10.
- `oracle_expected_source_diag` is diagnostic only and must not be copied into
  endpoint replay policy.

Therefore the next patch should be a scoped C1 retrieval policy experiment, not
a silent global eval-set change.

Recommended patch policy:

```text
policy_id = h2_c1_current_aug_top10_v0
query = current H2 augmentation policy
top_k = 10 for C1 endpoint replay only
min_similarity = 0.45
lexical_rerank = false
```

This does not make top-10 a final pass criterion by itself. It creates a
traceable replay policy so C1 can separate:

- expected source not reachable.
- expected source reachable but outside top-5.
- expected source retrieved but not cited.
- source-id fidelity failure.
- manual-lane pending/fail/pass.

## Proposed Patch Surface

Primary file:

```text
tools/hpz2_llamacpp_h2_endpoint_runner.py
```

Patch plan:

1. Add explicit retrieval policy metadata.

   Suggested fields:

   ```text
   retrieval_policy_id
   retrieval_query_policy
   retrieval_top_k_policy
   retrieval_min_similarity
   retrieval_lexical_rerank
   retrieval_augmented_fields
   ```

2. Add a C1-scoped top-k override.

   Acceptable implementation shapes:

   - a CLI flag such as `--c1-retrieval-top-k 10`; or
   - a named policy flag such as
     `--retrieval-policy h2_c1_current_aug_top10_v0`.

   The implementation must not change the eval-set default `top_k=5`.

3. Preserve current query augmentation as the first endpoint replay policy.

   Do not copy `primary_order_aug` directly into endpoint replay yet. It was a
   diagnostic variant and may still miss RA-07 at top-5.

4. Record retrieval diagnostics in every C1 replay case result.

   Minimum fields:

   ```text
   retrieval_policy_id
   retrieval_options_effective
   expected_source_rank
   retrieved_expected_hit_at_5
   retrieved_expected_hit_at_10
   expected_source_not_retrieved
   retrieved_expected_but_not_cited
   ```

5. Preserve the expected-source leakage guard.

   Endpoint replay must not use `expected_citations_includes_at_least` or
   expected source IDs to construct the live retrieval query. Those values may
   only be used for scoring and diagnostics after retrieval.

6. Keep RA-03 separate.

   The query policy patch should report RA-03 `rule:drug:sme` as unresolved
   source/index/searchability hygiene unless a separate RA-03 gate fixes it.

## Non-Goals

- No verifier relaxation.
- No alias normalization that hides malformed source IDs.
- No model ranking.
- No Primary4 expansion.
- No final `/explain` recommendation.
- No EMR_AI_24clinic source or index mutation.
- No global eval-set `top_k` mutation.
- No RA-03 source/index hygiene fix in this patch.

## Implementation Criteria

A later implementation patch should be accepted only if it includes focused
tests for these behaviors:

- default eval-set `top_k=5` remains unchanged when no C1 policy flag is used.
- C1 policy can set effective retrieval `top_k=10` without changing the eval
  JSON.
- policy metadata is serialized into replay JSON and summary output.
- retrieval diagnostics include hit-at-5 and hit-at-10 separately.
- endpoint replay query construction does not read expected source IDs.
- RA-03 unresolved source/index hygiene is reported separately from C1 top-k
  policy behavior.
- dry-run does not start HP runtime, llama-server, shim, LM Studio, or
  `/explain`.

## Validation Plan

Main PC validation:

1. Run focused endpoint-runner unit tests.
2. Run focused retrieval-only probe tests if touched.
3. Run `py_compile` for the changed runner.
4. Run endpoint-runner dry-run.
5. Run `git diff --check`.

HP Z2 validation after commit/push and pull/verify:

1. Pull and verify `local-llm-eval` clean/synced.
2. Run the C1 retrieval policy replay verify gate with the named policy.
3. Confirm no EMR repo writes.
4. Confirm runtime teardown and ports clear.
5. Review artifact for RA-06/RA-07 reachability and citation behavior before
   any Primary4/model-ranking decision.

## Next Gates

Recommended immediate gate if this plan is accepted:

```text
Main PC local-llm-eval H2 C1 retrieval query policy patch plan commit GO
```

Then implementation:

```text
Main PC local-llm-eval H2 C1 retrieval query policy patch implementation GO
```

Later runtime verification:

```text
HP Z2 local-llm-eval H2 C1 retrieval query policy replay verify GO
```

Separate blocker lane:

```text
Main PC local-llm-eval RA-03 sme source-index hygiene review GO
```
