---
id: h2-output-contract-primary4-expansion-review-2026-06-02
project: local-llm-eval
type: review
status: completed-primary4-c1-hypothesis
created: 2026-06-02
scope: H2 output-contract calibration Primary4 expansion artifact review
related:
  - docs/h2-output-contract-calibration-plan-2026-06-01.md
  - docs/hpz2-llamacpp-h2-output-contract-calibration-runner-2026-06-01.md
  - docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md
---

# H2 Output-Contract Primary4 Expansion Review

## Scope

This review covers the HP Z2 Primary4 expansion artifact:

```text
C:\github\hpz2-run-artifacts\results\h2_output_contract_calibration_20260602_022031\
```

The run used direct llama.cpp synthetic non-PHI prompts. It did not call
`/explain`, did not use the shim, and did not write `EMR_AI_24clinic`.

The artifact has not been path-limited committed or pushed in this review gate.

## Artifact Sanity

- Runner exit code: 0
- Mode: `h2_output_contract_calibration`
- Models: 4 Primary4 models
- Cells: 48
- API status: 48/48 `ok`
- Raw responses stored: 48/48
- Prompt files stored: 48/48
- Parse status: 36 `json_ok`, 12 `freeform_only`
- Native C1 contract pass: 12/12 C1 cells
- Normalizer pass: 48/48
- Citation exact pass: 48/48
- Required-source pass: 48/48
- Distractor-source pass: 48/48
- PHI-like hits: 0
- Final HP teardown: no `llama-server`; ports `18080` and `18081` free

The artifact-level `semantic_pass`, `grounding_pass`, `citation_claim_pass`,
and `safety_pass` fields remain unset by design. The table below is this
coordinator review's manual verdict.

## Manual Viability Verdict

Pass means semantic, grounding, citation-claim, and safety boundary are
acceptable for the synthetic case. A contract is viable for a model at 2/3 or
better, per the pre-registered plan.

| model | C1 | C2 | C3 | C4 | notes |
|---|---:|---:|---:|---:|---|
| `hpz2-l2-qwen36-35b-a3b` | 2/3 | 2/3 | 2/3 | 1/3 | OC-01 omits physician-judgment boundary across all contracts; C4 also omits the OC-03 final claim/judgment boundary. |
| `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4` | 2/3 | 2/3 | 2/3 | 3/3 | C1-C3 fail OC-01 boundary; C4 includes it but is not endpoint-native. |
| `hpz2-l2-qwen36-35b-a3b-mtp-q8` | 2/3 | 2/3 | 2/3 | 2/3 | OC-01 boundary omission persists across all contracts. |
| `hpz2-l2-granite-41-30b-q4km` | 3/3 | 3/3 | 3/3 | 3/3 | Preserves all three synthetic case boundaries. |

## Decision

C1 remains the preferred endpoint-contract hypothesis.

Reason:

- C1 is endpoint-native.
- All four Primary4 models meet C1 viability at 2/3 or better.
- C1 also has 12/12 native contract pass across Primary4.
- C2 and C3 remain viable normalizer-path backups, but they are not closer to
  the current endpoint contract than C1.
- C4 is not selected because it is not endpoint-native and the official Qwen
  model reaches only 1/3 under C4.

## Limits

This is not a final model recommendation.

Granite is strongest in this synthetic output-contract review, but the artifact
tests three synthetic cases only and intentionally excludes endpoint retrieval,
endpoint prompt construction, shim behavior, and verifier policy.

The main open issue is not JSON formatting. It is safety-boundary retention,
especially the physician-judgment boundary in OC-01 for Qwen-family outputs.

## Next Gate

Use the C1 hypothesis to design a narrow endpoint replay before another broad
model-quality claim:

```text
H2 C1 endpoint-hypothesis replay/design GO
```

The replay must preserve the gate boundary: C1 synthetic viability is evidence
for a contract hypothesis, not evidence that the real `/explain` endpoint is
ready.
