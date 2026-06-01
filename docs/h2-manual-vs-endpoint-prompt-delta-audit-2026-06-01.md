---
id: h2-manual-vs-endpoint-prompt-delta-audit-2026-06-01
project: local-llm-eval
type: audit
status: completed-test-validity-warning
created: 2026-06-01
scope: Manual-prompt versus endpoint-prompt delta audit for H2 interpretation
related:
  - docs/h2-content-lane-supplement-result-2026-06-01.md
  - docs/h2-content-citation-failure-review-2026-06-01.md
  - docs/rag_aware_eval_design_r0.md
  - docs/rag-goals-evaluation-principles-v0.1.md
  - prompts/rag_aware_eval_set_v0.1.json
---

# H2 Manual-vs-Endpoint Prompt Delta Audit

## Scope

This audit responds to the user observation that direct manual prompts produce
substantially better answers than the H2 `/explain` endpoint test.

The exact manual prompt/output examples were not provided in this gate, so this
is not a sentence-by-sentence comparison. It is an audit of the endpoint prompt,
retrieval query, verifier, runner scoring, and H2 artifact interpretation.

No new `/explain` calls, model runs, llama-server starts, shim starts,
raw-response replay, EMR writes, cleanup/download, commit, or push were
performed.

## Corrected Interpretation

The H2 endpoint result should not be treated as a model-quality verdict.

Safe interpretation:

- The endpoint execution was structurally stable: 64 model-backed calls,
  invalid JSON 0, strict-schema failures 0, structural drift 0, PHI hit 0, and
  RA-04 no-call preserved.
- Current H2 evidence is not sufficient to recommend a Primary model.

Unsafe interpretation:

- Do not claim that the models are clinically poor from the H2 content/citation
  result alone.
- Do not rank model quality using content keyword pass counts.
- Do not treat expected-citation misses as model failures when the expected
  source was not retrieved.
- Do not treat manual-prompt versus endpoint-prompt quality delta as a model
  limitation before prompt/retrieval/rubric differences are controlled.

Better wording:

```text
Current H2 endpoint evidence is confounded by endpoint prompt, retrieval,
verifier, and keyword-rubric effects. It blocks a positive model recommendation
under the current test, but it does not prove that the models lack semantic
potential under better prompting or a calibrated evaluation lane.
```

## Prompt Delta Findings

### 1. Endpoint Prompt Forbids Some Strings The Rubric Later Requires

The endpoint prompt explicitly prefers generic wording and discourages repeating
input codes when generic wording is enough:

- "입력된 약/검사 코드는 현재 점검 대상 식별에 필요한 경우에만 언급한다."
- "generic 설명으로 충분한 경우 입력 코드를 반복하지 말고..."
- "특정 order code 대신 \"해당 IV 수액\"으로 표현한다."

The content rubric then checks exact substrings such as `umk`, `j209`,
`trimesy`, `lacto2`, `dexisy`, `BST`, and `tysy`.

This creates a prompt/rubric contradiction. A model can follow the endpoint
style instruction and be counted as content-missing because it omitted a literal
input code.

### 2. Endpoint Prompt Is A Contract/Production Prompt, Not A Model-Potential Prompt

The `/explain` prompt imposes all of these simultaneously:

- retrieved-context-only restriction
- JSON-only output
- `summary` capped at 150 Korean characters
- citations copied exactly as bracketed `[source_id]`
- no extra text, no Markdown, no explanation outside JSON
- generic safety wording and conservative prescribing style

A user-written manual prompt usually supplies the intended clinical task more
directly and is not forced through the same 150-character JSON/citation
contract. This can legitimately produce better semantic answers from the same
model.

Per project design, this endpoint lane is the noisiest lane for model selection
because failures may come from retrieval, prompt construction, verifier policy,
model serving, or the model itself.

### 3. Retrieval Query Omits Some Details That Manual Prompts Usually Include

The endpoint retrieval query is built mainly from:

- `check_result.message`
- `check_result.sub`
- `check_result.source`
- `context.dx`
- `context.orders`
- `order_details[].code`

It does not directly include `dose`, `_note`, `age`, or `weight_kg` in the
retrieval query. Those values are available later in the endpoint prompt, but
they may not help retrieval select the right chunks.

This matters for cases where the user's manual prompt naturally includes weight,
age band, dose, insurance nuance, or code interpretation in plain language.

### 4. Citation Failures Mix Multiple Owners

Some expected sources were not retrieved for all four models, so the model could
not cite them:

- RA-02 expected metformin matrix row
- RA-03 expected `rule:drug:sme`
- RA-06 expected `rule:drug:dexisy`

Other sources were retrieved but not selected or were replaced by adjacent
aliases. That may be a model-citation-selection issue, expected-source policy
issue, or alias-policy issue, not a pure clinical reasoning failure.

### 5. Raw Responses Were Not Stored

The runner parsed raw summaries transiently for keyword scoring and then wrote
only safe metadata. This is acceptable for PHI-safe structural evidence, but it
prevents retrospective semantic review.

Therefore content keyword misses cannot be audited into final user-verdict
labels after the fact.

## Claims To Soften Or Retract

Keep:

- H2 structure/PHI execution evidence is valid.
- Current H2 evidence does not support a positive Primary model recommendation.

Soften:

- "content/citation lane is insufficient" should be read as "insufficient under
  the current endpoint/rubric setup", not as a direct model-quality result.
- "content pass count" is a mechanical substring result, not a semantic score.

Retract or forbid:

- "The models are clinically mostly wrong."
- "The manual prompt delta is caused by model limitation."
- "Citation miss means model miss."
- "No model recommendation means no model has semantic potential."

## Required Next Step Before More Model Ranking

Do not run a larger model matrix to solve this. First calibrate the evaluation
lane.

Recommended next safe gate:

```text
H2 manual prompt artifact intake GO
```

Scope: collect 2-3 user-provided manual prompt/output examples for the same H2
cases and compare them against endpoint prompt, retrieved source IDs, expected
keywords, and verifier policy. No model execution is required if the examples
already exist.

Additional read-only gates:

```text
H2 expected_summary_keywords rubric review GO
H2 retrieval/expected-citation alignment GO
```

Execution gate, only after separate explicit approval:

```text
H2 narrow raw-response replay GO
```

Candidate cases: `smoke-09-bst`, `RA-03`, `RA-06`, and `RA-07`. This would run
`/explain`/models and must define raw-response capture, PHI policy, and teardown
evidence before execution.
