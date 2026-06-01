---
id: h2-content-lane-supplement-result-2026-06-01
project: local-llm-eval
type: execution-result
status: completed-no-model-recommendation
created: 2026-06-01
scope: H2 content-lane supplement over Primary 4 x 17 endpoint matrix
related:
  - docs/h2-model-comparison-plan-2026-05-31.md
  - docs/hpz2-llamacpp-h2-endpoint-runner-2026-06-01.md
  - prompts/rag_aware_eval_set_v0.1.json
---

# H2 Content-Lane Supplement Result

## Artifacts

Successful supplement run:

```text
C:\Github\hpz2-run-artifacts\results\h2_content_lane_supplement_20260601_191928\
```

Preserved failed attempt:

```text
C:\Github\hpz2-run-artifacts\results\h2_content_lane_supplement_20260601_191749\
```

The failed attempt used global Python and stopped with
`ModuleNotFoundError: No module named 'fastapi'`. HP teardown was verified clean
after that attempt. The runner now preflights the local harness dependency
before HP runtime startup.

## Execution Pins

- Main PC `local-llm-eval`: `c97b163daab21886bef80400b44ac144d8b0d8e4`
  with the approved uncommitted runner/runbook hardening paths allowed.
- Main PC `EMR_AI_24clinic`: `dfe80b087151860dd466d65d34025e4c64af791d`,
  clean.
- HP `local-llm-eval`: `c97b163daab21886bef80400b44ac144d8b0d8e4`,
  clean.
- HP `EMR_AI_24clinic`: `543e1f9ef5a0e4fcb49c47e4a55b0e5e661a6944`,
  clean, not used for the Main PC endpoint harness.
- Local harness interpreter:
  `C:\Github\EMR_AI_24clinic\.venv\Scripts\python.exe`.

## Structural Result

- Run mode: `content_lane_supplement`.
- Raw model responses stored: no.
- Stopped early: no.
- Models completed: 4.
- Cases per model: 17.
- Model calls per model: 16. RA-04 did not call the model.
- HTTP non-200: 0.
- Invalid JSON: 0 / 64 model calls.
- Strict-schema failures: 0 / 64 model calls.
- Structural drift: 0.
- PHI hit count: 0.
- Final HP runtime: ports `18080` and `18081` closed; no llama/shim process.

## Content And Citation Summary

| model | content pass | content missing | not scored | citation expected-source missing | status mismatch |
|---|---:|---:|---:|---:|---:|
| `hpz2-l2-qwen36-35b-a3b` | 5 | 8 | 4 | 5 | 0 |
| `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4` | 6 | 7 | 4 | 5 | 1 |
| `hpz2-l2-qwen36-35b-a3b-mtp-q8` | 4 | 9 | 4 | 6 | 0 |
| `hpz2-l2-granite-41-30b-q4km` | 3 | 10 | 4 | 6 | 0 |

The `not scored` count is the same for all models:

- RA-01, RA-02, and RA-05 still have placeholder expected-summary keywords.
- RA-04 is a no-call PHI early-return lane.

The `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4` status mismatch repeats the H2 heavy-run
pattern: `smoke-09-bst` returned EMR `citation_failed` where `ok` was expected.

## Decision

Do not recommend a Primary model for `/explain` from this H2 evidence.

Interpretation caveat: this is not a direct model-quality verdict. The result is
confounded by endpoint prompt constraints, retrieval selection, citation
verifier policy, and literal keyword scoring. It is valid as endpoint
structure/PHI evidence and as a signal that the current evaluation setup is not
ready for model ranking.

Reason:

- Every candidate missed content keywords in more than half of the scored
  content-lane cases.
- Expected-source citation misses repeated across all candidates.
- The best content-pass count was `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`, but it
  also had the repeated `smoke-09-bst` status mismatch.

The structural lane is healthy, but the content/citation lane is not calibrated
enough for a model recommendation.

## Next Gate

Recommended next gate:

```text
H2 content/citation failure review GO
```

That review should inspect safe metadata and, only if separately approved,
perform a narrow raw-response or endpoint replay review for selected failing
cases. Do not infer authorization for more model runs, `/explain` calls, EMR
writes, cleanup, downloads, commit, or push from this result.
