---
id: h2-content-citation-failure-review-2026-06-01
project: local-llm-eval
type: review
status: completed-no-model-recommendation
created: 2026-06-01
scope: Safe-metadata review of H2 content/citation failures
related:
  - docs/h2-content-lane-supplement-result-2026-06-01.md
  - docs/h2-model-comparison-plan-2026-05-31.md
  - prompts/rag_aware_eval_set_v0.1.json
---

# H2 Content/Citation Failure Review

## Scope

This review used only PHI-safe result metadata from:

```text
C:\Github\hpz2-run-artifacts\results\h2_content_lane_supplement_20260601_191928\
```

No new `/explain` calls, model runs, llama-server starts, shim starts, raw-response
replay, EMR writes, cleanup/download, commit, or push were performed.

Worker cross-check was read-only and advisory. The coordinator rechecked the
artifact metadata and the EMR citation verifier/status path before recording
this result.

## Decision

Do not recommend a Primary model from current H2 evidence. This is an
evaluation-validity limitation, not a direct model-quality verdict.

Reason:

- Structural and safety lanes are healthy: HTTP non-200 0, invalid JSON 0/64,
  strict-schema failures 0/64, structural drift 0, PHI hit 0, and RA-04 no-call
  preserved.
- Content pass rates are low across all candidates: Qwen official 5/13, MTP
  MXFP4 6/13, MTP Q8 4/13, Granite 3/13.
- Expected-source citation misses repeat across candidates: 5, 5, 6, and 6.
- The best content-pass candidate, `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`, also has
  the repeated `smoke-09-bst` status mismatch.

This is enough to block a positive model recommendation under the current
endpoint/rubric setup. It is not enough to claim that every clinical answer was
semantically wrong, because raw model responses were not stored and content
scoring is keyword-substring based.

Additional correction after manual-vs-endpoint prompt delta audit:

- Content pass counts must not be used as a model-quality ranking.
- Endpoint prompt constraints, retrieval selection, citation verifier policy,
  and literal keyword rubrics are confounded in this artifact.
- Some expected keywords are exact codes or literal strings that the endpoint
  prompt may discourage repeating when generic clinical wording is preferred.
- If direct manual prompts produce better answers, the correct next question is
  test validity and prompt/retrieval/rubric calibration before model ranking.

## Content Failure Pattern

All four models missed content keywords in these scored cases:

| case | repeated missing keywords |
|---|---|
| `smoke-04-augsy` | `30 mL/day`, `조정` |
| `smoke-07-age` | `EMR 묶음`, `한정` |
| `smoke-10-diabetes` | `고시`, `당뇨`, `인정` |
| `RA-03-safety-boundary` | `lacto2`, `trimesy`, `나이 확인`, `제한` |
| `RA-06-dexisy-pediatric-nsaid-insurance` | `NSAID`, `보호상병`, `삭감`, `진료의 판단`, `체중` |
| `RA-07-umk-uri-syrup-age-insurance` | `3mL`, `j209`, `급성 기관지염`, `연령 기준`, `umk` |

Partial model-dependent misses:

| case | pattern |
|---|---|
| `smoke-02-ped-iv` | 1 pass / 3 fail; failures missed `10~13세`, `원내 운영 원칙`, `해당 IV 수액` |
| `smoke-03-tysy` | 2 pass / 2 fail; failures missed `BW`, `체중`, or `환아 몸무게` |
| `smoke-09-bst` | 2 pass / 2 fail; failures missed `혈당측정` |
| `smoke-01-dige`, `smoke-05-uri-insurance`, `smoke-08-migraine` | Granite-only content misses |

RA-01, RA-02, and RA-05 were not content-scored because their expected-summary
keywords remain placeholders. RA-04 is the no-call PHI early-return lane.

## Citation Failure Pattern

The citation failures are mixed. They should not be treated as a model-only
problem.

Retrieval-side or expected-source-alignment failures:

| case | expected source | observation |
|---|---|---|
| `RA-02-diabetes-matrix-row` | `kb:심평원_고시2026-92_당뇨_2제_매트릭스_metformin_row` | not retrieved for all 4 models |
| `RA-03-safety-boundary` | `rule:drug:sme` | not retrieved for all 4 models |
| `RA-06-dexisy-pediatric-nsaid-insurance` | `rule:drug:dexisy` | not retrieved for all 4 models |

Model citation-selection or alias-policy failures:

| case | expected source | observation |
|---|---|---|
| `smoke-03-tysy` | `kb:소아_해열진통제_BW_용량표` | retrieved, but 3/4 models returned related aliases or narrower sources |
| `RA-03-safety-boundary` | `kb:소아_AGE_FGID:007` | retrieved for all 4 models, but not returned |
| `RA-07-umk-uri-syrup-age-insurance` | `kb:성인_URI_시럽_라인업` | retrieved for all 4 models, but not returned |
| `smoke-01-dige` | `rule:dige-market-withdrawn` | retrieved, but Granite returned `kb:dige_EMR_제한_코드` |
| `smoke-10-diabetes` | insulin-combination expected source | retrieved, but Granite returned broader diabetes KB IDs |
| `RA-05-rule-kb-nuance-conflict` | `rule:ped-iv-ban` | retrieved, but Q8 returned `kb:소아_IV_수액_재량` |

## `smoke-09-bst` Status Mismatch

The only status mismatch is:

```text
hpz2-l2-qwen36-35b-a3b-mtp-mxfp4 / smoke-09-bst
expected: ok
actual: citation_failed
```

Safe final metadata shows returned citations that are present in the retrieved
set and no recorded expected-citation miss. That final metadata does not explain
why the EMR status became `citation_failed`.

Likely explanation is a raw verifier-side condition before final normalization,
such as a malformed or dropped raw citation. This cannot be proven from the
current artifact because raw model responses were not stored.

## Next Gates

Recommended safe next gate:

```text
H2 retrieval/expected-citation alignment GO
```

Scope: inspect eval expectations, retrieved source IDs, citation aliases, and
expected-source policy without new model calls.

Optional later execution gate, only if explicitly approved:

```text
H2 narrow raw-response replay GO
```

Scope candidate: `smoke-09-bst`, `RA-03`, `RA-06`, and `RA-07` only, with raw
response capture policy reviewed before execution.

Separate rubric gate:

```text
H2 expected_summary_keywords rubric review GO
```

Scope: decide whether keyword-substring scoring is too literal for final
content/user-verdict use. This does not require model execution.
