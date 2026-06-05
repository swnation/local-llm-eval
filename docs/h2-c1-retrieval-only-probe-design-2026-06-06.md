---
id: h2-c1-retrieval-only-probe-design-2026-06-06
project: local-llm-eval
type: design
status: draft-design
created: 2026-06-06
scope: Main PC retrieval-only probe design for H2 C1 RA-03/RA-06/RA-07 follow-up
related:
  - docs/h2-c1-retrieval-citation-follow-up-plan-2026-06-06.md
  - docs/h2-c1-evaluation-and-citation-criteria-2026-06-03.md
  - docs/c1-endpoint-replay-failure-triage-and-alignment-plan-2026-06-02.md
  - prompts/rag_aware_eval_set_v0.1.json
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - C:\Github\hpz2-run-artifacts\results\h2_c1_endpoint_replay_20260605_234311\
  - C:\Github\_review_hpz2_run_artifacts_origin_main\results\h2_c1_endpoint_replay_20260605_014010\
---

# H2 C1 Retrieval-Only Probe Design

## Scope

This is a design-only Main PC gate.

No HP Z2 command, LLM call, llama-server start, shim start, LM Studio API call,
`/explain` request, EMR write, artifact repo normalization, commit, push, relay
update, or librarian backup is authorized by this document.

The follow-up implementation, if approved later, should add a retrieval-only
probe runner that calls the existing EMR retriever directly. It should not use
`TestClient`, should not call `generate_llm`, and should not ask the model to
produce any text.

## Problem To Separate

The current local replay artifact
`h2_c1_endpoint_replay_20260605_234311` remains pilot NO-GO. The retrieval and
citation issues split as follows:

| case | observed current state | probe question |
| --- | --- | --- |
| RA-03 | `rule:drug:sme` is not retrieved; AGE pediatric KB sources are retrieved. | Is `rule:drug:sme` absent/unreachable, below current top-k, or suppressed by query wording? |
| RA-06 | `rule:drug:dexisy` was retrieved in the previous reviewed artifact but is missing in the current artifact. | Did the post-`f4869d6` query augmentation duplicate/broaden order-code terms enough to push the rule source out of top-k? |
| RA-07 | `kb:성인_URI_시럽_라인업` is retrieved but not cited. | Confirm this stays a citation-selection problem rather than a retrieval problem. |

`smoke-09-bst` is not the primary target of this retrieval probe. It remains a
source-id fidelity / BST hygiene lane because `rule:module:bst` is retrieved,
while Qwen emits `rule_module:bst`.

## Current Query Facts

`EMR_AI_24clinic.app.llm.prompt_builder.build_retrieval_query()` already includes
these fields:

- `check_result.message`
- `check_result.sub`
- `check_result.source`
- `context.dx[]`
- `context.orders[]`
- `context.order_details[].code`

`local-llm-eval.tools.hpz2_llamacpp_h2_endpoint_runner.augment_h2_retrieval_query()`
then adds H2-only fields:

- `context.age`
- `context.weight_kg`
- `context.orders[]`
- `context.order_details[].code`
- `context.order_details[].dose`
- `context.order_details[]._note`

Therefore the RA-06 regression hypothesis is not merely "orders/code were first
added." The better hypothesis is:

```text
orders/code were already in the EMR base query, and the H2 augmentation now
duplicates or over-weights broad multi-order context enough to change top-k
ranking.
```

The probe must compare old and current query policies with that fact visible.

## Proposed Implementation Surface

Add a new Main PC runner in a later implementation gate:

```text
tools/h2_c1_retrieval_only_probe.py
```

The runner should:

1. Load `prompts/rag_aware_eval_set_v0.1.json`.
2. Select default cases:
   - `RA-03-safety-boundary`
   - `RA-06-dexisy-pediatric-nsaid-insurance`
   - `RA-07-umk-uri-syrup-age-insurance`
3. Build each request through the existing
   `hpz2_lmstudio_phase2_stage_a_runner.case_payload()`.
4. Import EMR read-only helpers from `C:\Github\EMR_AI_24clinic`:
   - `app.llm.prompt_builder.build_retrieval_query`
   - `app.rag.retriever.Retriever`
5. Run retrieval directly for each query variant.
6. Store only source IDs and retrieval metadata, not retrieved snippets.

Do not monkeypatch the endpoint for this probe. Direct function calls are
smaller and avoid accidental `/explain` or LLM execution.

## Offline And Safety Guard

The runner should fail closed if the local embedding/index cache is missing.
It must not download models or refresh external resources unless a separate
download/cache GO is given.

Recommended environment posture for the runner:

```text
HF_HOME=C:\Github\EMR_AI_24clinic\rag_index\_build\hf_cache
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

Preflight checks:

- `C:\Github\EMR_AI_24clinic\rag_index\_build\vectors.npz` exists.
- `C:\Github\EMR_AI_24clinic\rag_index\chunks\*.jsonl` exists.
- `C:\Github\EMR_AI_24clinic` is not modified by the run.
- `local-llm-eval` target is explicit.
- No ports, HP process cleanup, or llama/LM Studio process checks are needed
  because this is not a runtime gate.

## Query Variants

Run every selected case through the same top-k/min-similarity settings unless a
variant explicitly states otherwise.

Default retrieval options come from each eval case:

```text
top_k=5
min_similarity=0.45
lexical_rerank=false
```

Minimum variants:

| variant id | query construction | purpose |
| --- | --- | --- |
| `emr_base` | EMR `build_retrieval_query()` only | Establish the existing endpoint baseline query. |
| `h2_old_aug` | `emr_base` + age/weight/dose/note only | Approximate the pre-`f4869d6` augmentation that did not re-add orders/code. |
| `h2_current_aug` | Existing `augment_h2_retrieval_query()` | Reproduce current runner behavior. |
| `primary_order_aug` | `emr_base` + age/weight + first/primary order detail dose/note | Test whether focused drug context restores rule sources without broad multi-order noise. |
| `oracle_expected_source_diag` | `emr_base` + expected rule source ID and expected drug code terms | Diagnostic only: prove whether the expected source is index-reachable when explicitly named. Not a production policy. |
| `wide_topk_diag` | run `h2_current_aug` and `primary_order_aug` at top-k 10 and top-k 20 | Separate "below top-5" from "not reachable under current similarity threshold." |
| `minsim_zero_diag` | run selected variants at `min_similarity=0.0`, top-k 20 | Diagnostic only: inspect rank/score when 0.45 threshold may hide a source. |

`oracle_expected_source_diag` must be labeled as non-production evidence. It
may use `expected_citations_includes_at_least` to diagnose index reachability,
but it must not become the endpoint query policy.

## Output Artifact

Recommended output location for the later implementation run:

```text
results/h2_c1_retrieval_probe_<YYYYMMDD_HHMMSS>/
  h2_c1_retrieval_probe_results.json
  h2_c1_retrieval_probe_summary.md
```

This is a Main PC/local harness artifact, not an HP Z2 runtime artifact.

The JSON should include:

```text
generated_at
local_llm_eval_head
emr_ai_24clinic_head
eval_set_path
emr_repo_path
index_paths
offline_mode
cases[]
```

Each `cases[]` item should include:

```text
case_id
expected_source_ids
expected_rule_source_ids
variants[]
```

Each `variants[]` item should include:

```text
variant_id
query
top_k
min_similarity
lexical_rerank
retrieved[]
expected_source_retrieved
expected_source_not_retrieved
expected_source_rank
hit_at_5
hit_at_10
hit_at_20
owner_hint
```

Each `retrieved[]` item should include only:

```text
rank
source_id
similarity
lexical_overlap
is_expected
```

Do not store:

- retrieved snippet/content
- model output
- raw `/explain` response
- PHI-like free text
- prompt bodies

## Interpretation Rules

### RA-03

If `rule:drug:sme` appears only in `oracle_expected_source_diag`, the index can
serve the source, but production query terms are not reaching it.

If it appears at top-k 10 or 20 under `h2_current_aug` or `primary_order_aug`,
the problem is ranking/top-k, not source absence.

If it does not appear even in `minsim_zero_diag` top-k 20, the next gate should
be index/source hygiene review, not endpoint replay.

### RA-06

If `h2_old_aug` retrieves `rule:drug:dexisy` and `h2_current_aug` misses it,
the likely patch is to remove broad duplicate `orders[]`/`order_details[].code`
boosting from the H2 augmentation and keep age/weight/dose/note.

If `primary_order_aug` restores `rule:drug:dexisy` while preserving
`kb:소아_dexisy_BW_용량` and `kb:소아_NSAIDs_추가_상병`, the next query policy patch
should prefer focused primary-order terms over appending every order equally.

If no non-oracle variant retrieves `rule:drug:dexisy`, but oracle does, treat it
as query design gap. If oracle also misses, inspect the index/source text.

### RA-07

If `kb:성인_URI_시럽_라인업` remains retrieved under base/current/focused variants,
RA-07 should stay in the citation-selection lane. Do not patch retrieval just to
force citation behavior.

If a query variant loses this source, that variant should not be promoted even
if it improves RA-03 or RA-06.

## Success Criteria For The Probe Runner

The implementation gate should be considered successful when:

- It runs without HP Z2, llama-server, shim, LM Studio API, `/explain`, or LLM
  calls.
- It produces deterministic JSON/Markdown artifacts with source IDs, ranks,
  similarities, and expected-source hit/miss tables.
- It clearly classifies RA-03 and RA-06 as one of:
  - index/source absent or unreachable;
  - below current top-k;
  - current query wording/ranking problem;
  - expected source reachable only through oracle diagnostic terms.
- It confirms whether RA-07 remains retrieved-not-cited.
- It leaves `EMR_AI_24clinic` unchanged.

The probe must not by itself unblock:

- model ranking
- Primary4 endpoint replay expansion
- final `/explain` recommendation
- verifier relaxation
- eval expected-citation edits

## Test Plan For Implementation Gate

Add focused unit tests around pure helper functions before any live retrieval
run:

- query variant builder includes the intended fields and labels.
- `h2_old_aug` does not re-add broad order/code terms beyond the EMR base query.
- `h2_current_aug` matches current `augment_h2_retrieval_query()` behavior.
- expected-source rank and hit-at-k calculations are correct.
- artifact serialization excludes snippet/content fields.
- offline/cache preflight fails closed when required index files are missing.

Live retrieval probe execution remains a separate gate after implementation.

## Recommended Next GO

```text
Main PC local-llm-eval H2 C1 retrieval-only probe implementation GO
```
