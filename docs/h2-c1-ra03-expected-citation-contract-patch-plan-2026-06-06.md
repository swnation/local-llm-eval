---
id: h2-c1-ra03-expected-citation-contract-patch-plan-2026-06-06
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-06
scope: Main PC plan for RA-03 expected citation contract patch after source-index hygiene review
related:
  - docs/h2-c1-retrieval-query-policy-patch-plan-2026-06-06.md
  - prompts/rag_aware_eval_set_v0.1.json
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - tools/h2_c1_retrieval_only_probe.py
  - 'C:\Github\EMR_AI_24clinic\rag_index\chunks\rules.jsonl'
  - 'C:\Github\EMR_AI_24clinic\rag_index\chunks\knowledge.jsonl'
---

# H2 C1 RA-03 Expected Citation Contract Patch Plan

## Project Goal Check

- direct value: correct the RA-03 citation contract so C1 replay measures
  safety grounding rather than requiring an evidence source that does not
  contain the safety claim.
- classification: `direct progress` with safety and evaluation-validity value.
- narrower scope: document-only plan. No eval-set edit, endpoint-runner
  implementation, EMR write, RAG chunk/index mutation, HP command, model
  execution, `/explain`, commit, push, relay update, or librarian backup is
  authorized by this file.

## Scope

This is a Main PC planning gate.

The later patch target is the RA-03 block in:

```text
prompts/rag_aware_eval_set_v0.1.json
```

This plan does not change that JSON file.

Out of scope:

- changing RA-03 resolved values: `sme + trimesy + lacto2`, `dx=a090`,
  pediatric `age=1`.
- changing retrieval query policy or C1 top-k policy.
- changing endpoint citation verifier behavior.
- editing `C:\Github\EMR_AI_24clinic\**`.
- enriching `rule:drug:sme`, regenerating chunks, rebuilding vectors, or
  reindexing.
- HP Z2 pull/verify, retrieval replay, endpoint replay, model execution, or
  `/explain`.
- commit, push, relay update, or backup.

## Evidence Summary

Current RA-03 contract in `prompts/rag_aware_eval_set_v0.1.json` requires all
three source IDs through `expected_citations_includes_at_least`:

```text
rule:drug:sme
kb:소아_AGE_sme_2세미만
kb:소아_AGE_FGID:007
```

The eval schema says `expected_citations_includes_at_least` is the default
required-all pass surface unless an `acceptable_citation_set` overrides it. The
endpoint runner follows that contract: if a case has no
`acceptable_citation_set`, it copies `expected_citations_includes_at_least` into
`required_all`.

The source-index hygiene review found no chunk/vector alignment corruption:

```text
chunk_count 730
chunk_unique 730
vector_count 730
vector_unique 730
embedding_shape (730, 1024)
rule_drug_sme_chunk_count 1
rule_drug_sme_vector_count 1
vector_missing_in_chunks 0
chunks_missing_in_vectors 0
```

The problem is source-content mismatch:

- `rule:drug:sme` exists in chunks and vectors, but its chunk content only
  states drug code/name, ingredient, syrup formulation, 3 times/day, and
  `needs_review`. It does not state the `2세 미만` safety boundary, insurance
  restriction, or `hidra` alternative.
- `kb:소아_AGE_sme_2세미만` contains the direct safety claim: `sme` is restricted
  for patients under age 2 and `hidra` is the preferred antidiarrheal
  alternative in that context.
- `kb:소아_AGE_FGID:007` contains the AGE bundle context: `trimesy`, `lacto2`,
  `sme (2세 이상)`, and `hidra(2세 미만 지사제)`.

Therefore RA-03 should not require `rule:drug:sme` as a mandatory citation in
the current index state. Requiring it rewards citation to a weak source that
does not ground the safety meaning being evaluated.

## Contract Diagnosis

This is not a missing source-ID problem.

This is not primarily a vector-index corruption problem.

This is not responsibly fixed by query expansion alone. Even if
`rule:drug:sme` were retrieved, the rule chunk still would not support the
specific RA-03 safety claim.

The intended RA-03 clinical/evaluation question is:

```text
AGE diarrhea bundle, age 1, sme + trimesy + lacto2:
check under-two sme boundary, age confirmation, and hidra alternative.
```

The two current KB chunks are the sources that actually encode that meaning.
`rule:drug:sme` can still be useful as a diagnostic or optional drug-code hit,
but it should not be a pass/fail source for this RA-03 citation contract until
the EMR source itself is intentionally enriched and reindexed under a separate
GO.

## Proposed Patch

Preferred strict patch for the later implementation gate:

```json
"expected_citations_includes_at_least": [
  "kb:소아_AGE_sme_2세미만",
  "kb:소아_AGE_FGID:007"
],
"acceptable_citation_set": {
  "required_all": [
    "kb:소아_AGE_sme_2세미만",
    "kb:소아_AGE_FGID:007"
  ],
  "optional_hits": [
    "rule:drug:sme"
  ],
  "invalid_aliases": []
}
```

Recommended note field inside the RA-03 case:

```json
"_ra03_contract_note": "rule:drug:sme exists but currently does not encode the under-two sme safety boundary; keep it optional until EMR source enrichment/reindex is explicitly approved."
```

Keep unchanged:

- `id`
- `source`
- `expected_status`
- `citation_required`
- `model_call_expected`
- `phi_input_test_flag`
- `axis_focus`
- `explain_request`
- `expected_citations_pending`
- `expected_summary_keywords`
- `expected_summary_rubric`
- `user_verdict_carry`

This keeps RA-03 strict: both current safety-grounding KB sources are required.
The only removed hard requirement is the current rule chunk that does not carry
the safety claim.

## Success Criteria

The implementation patch is acceptable only if all of these are true:

- Only the RA-03 block in `prompts/rag_aware_eval_set_v0.1.json` changes.
- The file remains valid JSON.
- RA-03 `expected_citations_includes_at_least` no longer includes
  `rule:drug:sme`.
- RA-03 `acceptable_citation_set.required_all` requires the two KB source IDs.
- RA-03 `acceptable_citation_set.optional_hits` includes `rule:drug:sme`.
- RA-03 resolved values stay locked: `sme + trimesy + lacto2`, `dx=a090`,
  pediatric `age=1`.
- No EMR repo file, RAG chunk, vector index, or endpoint code is changed in
  this patch.
- Retrieval-only tooling no longer treats `rule:drug:sme` as a required RA-03
  source through `expected_citations_includes_at_least`.

## Validation Plan

Minimum Main PC validation after the later implementation patch:

```powershell
python -m json.tool C:\Github\local-llm-eval\prompts\rag_aware_eval_set_v0.1.json > $null
python -m unittest discover -s C:\Github\local-llm-eval\tests
git -C C:\Github\local-llm-eval diff --check
```

Focused checks to inspect manually:

- RA-03 JSON block contains exactly the proposed citation contract.
- No other case citation contracts changed.
- Any retrieval-only probe or endpoint-runner summary after the patch reports
  `rule:drug:sme` as optional/diagnostic only, not as a required missing source.

No HP Z2 run is required for the JSON contract patch itself. HP replay becomes
useful only after the eval-set patch is committed, pushed, pulled, and a
separate HP execution GO is issued.

## Deferred Separate Lane

If the project later wants `rule:drug:sme` to become a mandatory RA-03 citation,
that is an EMR source-enrichment lane, not this patch:

1. Add the under-two safety boundary to the authoritative EMR source for
   `sme`.
2. Regenerate chunks.
3. Rebuild vectors.
4. Verify chunk/vector alignment.
5. Rerun retrieval reachability.
6. Then consider promoting `rule:drug:sme` back into `required_all` or
   `strong_all`.

That lane requires a separate EMR write/reindex plan and explicit GO.

## Next Gates

If this plan is accepted:

```text
Main PC local-llm-eval RA-03 expected citation contract patch plan commit GO
```

Later implementation gate:

```text
Main PC local-llm-eval RA-03 expected citation contract patch implementation GO
```

Optional separate EMR source-enrichment lane:

```text
Main PC local-llm-eval RA-03 sme EMR source enrichment plan GO
```
