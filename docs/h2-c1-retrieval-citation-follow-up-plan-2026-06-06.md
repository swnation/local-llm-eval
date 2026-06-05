---
id: h2-c1-retrieval-citation-follow-up-plan-2026-06-06
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-06
scope: H2 C1 retrieval and citation follow-up after f4869d6 replay artifact review
related:
  - docs/h2-c1-evaluation-and-citation-criteria-2026-06-03.md
  - docs/c1-endpoint-replay-failure-triage-and-alignment-plan-2026-06-02.md
  - docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md
  - prompts/rag_aware_eval_set_v0.1.json
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - C:\Github\hpz2-run-artifacts\results\h2_c1_endpoint_replay_20260605_234311\
---

# H2 C1 Retrieval/Citation Follow-Up Plan

## Scope

This is a Main PC planning gate only.

Do not run HP Z2 model/runtime commands, llama-server, LM Studio API, `/explain`,
EMR writes, artifact repo normalization, relay update, commit, push, or
librarian backup in this gate.

## Current Verdict

The `h2_c1_endpoint_replay_20260605_234311` artifact shows that C1 JSON
structure and safety metadata instrumentation are usable, but pilot acceptance
and model ranking remain blocked.

The remaining blockers are not one class of model-quality failure. They split
into retrieval reachability, retrieval ranking regression, citation selection,
source-id fidelity, and manual-lane persistence.

## Evidence Snapshot

Evidence source:

- `C:\Github\hpz2-run-artifacts\results\h2_c1_endpoint_replay_20260605_234311\h2_c1_endpoint_replay_results.json`
- comparison baseline:
  `C:\Github\_review_hpz2_run_artifacts_origin_main\results\h2_c1_endpoint_replay_20260605_014010\h2_c1_endpoint_replay_results.json`

| case | current evidence | blocker owner |
| --- | --- | --- |
| smoke-09 | Granite returns canonical `rule:module:bst` and `kb:BST_시나리오`; Qwen still emits `rule_module:bst`, producing a near-miss against `rule:module:bst`. | source-id fidelity / index hygiene, not verifier relaxation |
| RA-03 | Both models retrieve AGE pediatric KB sources, including `kb:소아_AGE_sme_2세미만`; expected `rule:drug:sme` is not retrieved. | retrieval reachability |
| RA-06 | Current replay retrieves `kb:소아_NSAIDs_추가_상병` and `kb:소아_dexisy_BW_용량`, but expected `rule:drug:dexisy` is no longer in retrieved top-k. The previous reviewed artifact did retrieve and cite `rule:drug:dexisy`. | retrieval ranking regression after query augmentation |
| RA-07 | Both models retrieve `rule:drug:umk`, `kb:소아_URI(만12세_미만):007`, and `kb:성인_URI_시럽_라인업`, but omit `kb:성인_URI_시럽_라인업` from final citations. | citation selection |

## Criteria Alignment

Use the separation from
`docs/h2-c1-evaluation-and-citation-criteria-2026-06-03.md`:

- Expected source not retrieved: retrieval reachability or retrieval ranking
  problem.
- Expected source retrieved but not cited: citation-selection or
  citation-claim problem.
- Source ID mutation, for example `rule_module:bst` versus `rule:module:bst`:
  source-id fidelity problem. Do not hide it by normalization.
- Manual lanes missing or pending: artifact is not promotion-ready even if
  structural checks pass.

## Failure Owner Split

1. `smoke-09` Qwen citation failure remains a source-id fidelity issue.
   The verifier should continue to report the near miss instead of accepting
   mutated IDs.

2. `RA-03` remains a retrieval reachability issue for `rule:drug:sme`.
   The endpoint runner now augments age, weight, orders, and order details, but
   the drug rule still does not reach the retrieved set.

3. `RA-06` is a regression relative to the previous reviewed artifact.
   Adding broad order-code terms appears to change ranking enough to push
   `rule:drug:dexisy` out of the retrieved top-k while retaining related KB
   sources.

4. `RA-07` is not primarily a retrieval issue.
   The expected adult syrup lineup source is retrieved, but the model does not
   include it in output citations.

5. Manual-lane results are still pending at artifact level.
   Manual semantic, grounding, citation-claim, and safety adjudication should be
   persisted separately from structural endpoint status.

## Follow-Up Design

### 1. Add a retrieval-only probe gate

Create a Main PC retrieval-only diagnostic path before another HP endpoint
replay. The probe should not call the model. It should compare retrieval output
for RA-03, RA-06, and RA-07 under controlled query variants.

Minimum variants:

| variant | purpose |
| --- | --- |
| base case query | current raw prompt/eval query without H2 context augmentation |
| old augmentation | age, weight, dose, and note fields only |
| current augmentation | age, weight, `orders[]`, `order_details[].code`, dose, and note |
| focused drug-rule terms | primary expected drug rule/code terms without appending every order code |
| wider diagnostic top-k | inspect whether expected rule sources appear at top-k 7 or 10 without changing pass criteria |

Success criterion:

- RA-03 shows whether `rule:drug:sme` is absent from the index/retriever or
  merely ranked below current top-k.
- RA-06 identifies the smallest query policy that restores `rule:drug:dexisy`
  without losing `kb:소아_dexisy_BW_용량` and `kb:소아_NSAIDs_추가_상병`.
- RA-07 confirms that `kb:성인_URI_시럽_라인업` remains retrieved, keeping this
  case in the citation-selection lane.

### 2. Patch query augmentation policy only after probe evidence

Do not keep broad order-code concatenation as the only policy if it causes
RA-06 ranking regression.

Preferred patch direction after probe:

- Separate `rule_drug_boost_terms` from the free-text retrieval query.
- Prefer primary/current order terms over appending every context order equally.
- Keep `dose`, `_note`, `age`, and `weight_kg` because they carry pediatric
  dosing and insurance-rule context.
- Record retrieval query metadata in artifacts so future regressions can be
  traced to field policy, not guessed from output.

Non-goal:

- Do not solve `rule:drug:dexisy` by relaxing citation verification.
- Do not mark expected citations as pass when the expected source was not
  retrieved.

### 3. Add citation-selection handling for retrieved-not-cited cases

For RA-07, retrieval already reaches the adult syrup lineup source. The next
patch should make citation expectations visible to the model without requiring
the model to cite every retrieved source in all cases.

Preferred policy:

- Preserve strict source-ID checking.
- Distinguish required/core expected citations from supporting optional
  citations if the eval set later needs that distinction.
- Add artifact diagnostics for `retrieved_expected_but_not_cited`.
- Keep RA-07 as citation-selection failure until the model cites
  `kb:성인_URI_시럽_라인업` or the expected-citation contract is explicitly
  revised.

### 4. Persist manual-lane adjudication separately

Manual review results should not be inferred from endpoint pass/fail status.

Follow-up patch options:

- Add a manual-lane overlay file keyed by `artifact_id`, `case_id`, and model.
- Or extend the replay summary schema with explicit manual lane fields:
  `manual_semantic`, `manual_grounding`, `manual_citation_claim`,
  `manual_safety`, and `manual_overall`.

Success criterion:

- A future artifact can show "structure pass but manual lane pending/fail/pass"
  without forcing the coordinator to reconstruct the decision from prose.

### 5. Keep BST source-id hygiene separate

The `rule_module:bst` near miss should remain visible. If this is an index or
prompt source-ID formatting issue, fix it under a separate BST source-id hygiene
gate.

Do not broaden verifier normalization in a way that would hide malformed source
IDs.

## Proposed Gate Order

1. `Main PC local-llm-eval H2 C1 retrieval-only probe design GO`
2. `Main PC local-llm-eval H2 C1 retrieval-only probe implementation GO`
3. `Main PC local-llm-eval H2 C1 retrieval query policy patch plan GO`
4. `Main PC local-llm-eval H2 C1 retrieval query policy patch implementation GO`
5. `HP Z2 local-llm-eval H2 C1 retrieval query policy replay verify GO`
6. `Main PC local-llm-eval C1 manual-lane persistence patch plan GO`

Blocked until those gates produce evidence:

- Primary4/model-ranking expansion
- final `/explain` recommendation
- promotion of the current replay as pilot-ready

## Immediate Next GO

Recommended next command:

```text
Main PC local-llm-eval H2 C1 retrieval-only probe design GO
```
