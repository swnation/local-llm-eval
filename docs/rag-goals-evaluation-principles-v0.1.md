---
id: rag-goals-evaluation-principles-v0.1
project: local-llm-eval
type: principles
status: R1 frozen (post R1 fix, GO for freeze)
version: 0.1
created: 2026-05-25
updated: 2026-05-25
scope: RAG goals and evaluation principles for EMR_AI_24clinic /explain
related:
  - AGENTS.md
  - PROJECT_CONTEXT.md
  - docs/rag_aware_eval_design_r0.md
  - prompts/rag_aware_eval_set_v0.1.json
  - docs/hpz2-lmstudio-phase2-stage-a-config-2026-05-24.md
  - docs/hpz2-lmstudio-phase2-stage-ar-model-aware-2026-05-24.md
---

# RAG Goals and Evaluation Principles v0.1

> This document defines how to judge RAG quality before running more model tests.
> It does not authorize heavy eval, Phase 2 `/explain`, EMR_AI_24clinic writes,
> commits, pushes, RA-03 changes, or Stage B/C expansion.

## 0. Current Status

There was no dedicated current document for the revised semantic-first RAG goals
and evaluation principles. Existing artifacts define a frozen Phase 2.1 design,
case set, LM Studio configs, and runner notes, but they still lean toward
strict endpoint/schema readiness as the visible score surface.

This file fills that gap. It is a policy layer over the frozen design, not a
replacement for `docs/rag_aware_eval_design_r0.md` or
`prompts/rag_aware_eval_set_v0.1.json`.

Current active execution baseline:

- HP Z2 is execution-only.
- Main PC is canonical for documentation, review, commit, and push.
- The active runner direction is LM Studio / llama.cpp Vulkan, not Ollama.
- Any existing Ollama-oriented host labels are legacy context unless explicitly
  revalidated for the current LM Studio lane.
- No heavy eval or real `/explain` run happens without explicit user GO.

## 1. Product Goal

The `/explain` RAG system should help a clinician or reviewer understand why a
deterministic rule/check fired, using only retrieved evidence and safe wording.
It is not a diagnosis engine, prescription recommender, or autonomous medical
decision maker.

Primary output goals:

- State the relevant issue in concise Korean.
- Ground every clinical, drug, diagnosis, code, and policy claim in retrieved
  context.
- Preserve important nuance when rule text and knowledge-base text differ.
- Cite exact source IDs that actually exist in the retrieved evidence set.
- Avoid unsupported alternative-drug recommendations.
- Avoid leaking PHI in summaries, citations, errors, logs, and artifacts.
- Say confirmation is needed when the retrieved context is insufficient or
  when a human clinical decision is required.

Role boundary carried from `PROJECT_CONTEXT.md` §2:

| LLM should do | LLM must not do |
|---|---|
| charting sentence cleanup | act as the OCR primary engine or canonical extractor |
| explain `NEEDS_REVIEW` reasons | make hard safety decisions |
| turn rule findings into report wording | auto-correct or auto-confirm records |
| emit JSON + PHI-safe summaries | instruct prescription changes or clinical confirmation |

Core rule: **LLM은 판단 엔진이 아닌 설명·정리·검토 보조 엔진**.

## 2. Evaluation Goal

The evaluation should answer four separate questions:

1. Did the model understand the evidence and reach the right conclusion?
2. Can an adapter/normalizer reliably convert the model output to the app
   contract?
3. Can the model natively satisfy the strict contract without help?
4. Does the real `/explain` endpoint behave correctly end to end?

These questions must not be collapsed into one strict JSON score. A strict
schema failure is operationally relevant, but it is not the same thing as a bad
RAG answer. Conversely, schema-valid JSON is not useful if the conclusion is
wrong, ungrounded, unsafe, or cites nonexistent evidence.

## 2.1 System Architecture and Failure Ownership

Evaluation should map failures to the pipeline stage that owns them:

```text
retrieved chunks
       |
       v
evidence pack --------------------> Semantic Lane judges here
       |
       v
model reasoning/answer -----------> Semantic Lane judges here
       |
       v
normalizer -----------------------> Normalizer Lane judges here
       |
       v
citation_verifier ----------------> citation integrity / verifier policy
       |
       v
/explain JSON response -----------> Native Contract Lane + Real Endpoint Lane
```

`failure_owner` should be one of: retrieval, evidence_pack, prompt, model,
normalizer, verifier, endpoint, infra, or manual_review_needed.

## 3. Evaluation Lanes

### 3.1 Semantic RAG Lane / Model Potential Lane

Purpose: judge the model's raw RAG reasoning quality.

Allowed output: freeform text, markdown, JSON, `answer` field, inline citations,
or other readable structure. The contract shape is not the primary score.

Judge:

- conclusion correctness
- groundedness against retrieved context
- citation exactness and source ID existence
- preservation of rule/KB nuance
- unsupported inference or hallucination
- safety wording compliance
- PHI safety
- Korean clinical readability

Interpretation:

- This lane decides whether a model is worth keeping as a RAG candidate.
- A model can pass this lane even if it fails native strict JSON.
- Citation extraction may be post-hoc if the cited source IDs are real and
  semantically attached to the claims they support.

### 3.2 Normalizer Lane

Purpose: judge whether outputs from promising models can be converted into the
final app contract.

Input examples:

- freeform answer with bracketed citations
- markdown with citations
- JSON using `answer` instead of `summary`
- citations as strings, arrays, or inline source mentions
- extra text around an otherwise recoverable JSON object

Target contract:

```json
{
  "summary": "string",
  "citations": ["source_id"]
}
```

Interpretation:

- Recoverable envelope differences are adapter issues, not model-quality
  failures.
- The normalizer must not invent citations, rewrite clinical meaning, or remove
  safety qualifiers.
- A normalizer pass does not excuse a semantic hard fail.

### 3.3 Native Contract Lane

Purpose: measure whether a model can directly emit the endpoint's preferred
strict JSON/schema shape.

This lane is useful for operational simplicity and low-latency integration.
It should not be the primary model-quality lane.

Interpretation:

- Native contract pass = convenient integration.
- Native contract fail = may need normalizer or prompt/profile adjustment.
- Native contract pass with wrong content remains a failed RAG answer.

### 3.4 Real Endpoint Lane

Purpose: measure the actual `/explain` pipeline.

This lane includes retrieval, prompt building, PHI stripping, LM Studio model
serving, timeout behavior, citation verification, endpoint response status, and
latency.

Interpretation:

- This is the only lane that can declare endpoint readiness.
- It is also the noisiest lane for model selection because failures may come
  from retrieval, prompt construction, verifier policy, model serving, or the
  model itself.
- Run only after explicit user GO.

### 3.5 Lane Priority and Gating

Working priority before calibration:

| Lane | Ranking role | Working weight / gate |
|---|---|---|
| Semantic RAG Lane | primary model-quality score | 60-70% |
| Normalizer Lane | adapter feasibility | 15-20% |
| Native Contract Lane | integration convenience | 5-10%, not a hard gate |
| Real Endpoint Lane | production readiness | gate after semantic + normalizer pass |

Gating rules:

- Semantic hard fail -> reject model for RAG promotion, regardless of speed or
  contract shape.
- Semantic pass + normalizer pass -> candidate can be compared against native
  contract behavior.
- Native contract pass is useful but should not outrank semantic quality.
- Real Endpoint Lane should be entered only by candidates that have already
  shown semantic viability and recoverable contract behavior.

## 4. Hard Fails

Any of the following should block promotion regardless of JSON shape or speed:

- nonexistent `source_id` citation presented as evidence
- citation-claim mismatch, where the source ID exists but does not support the
  specific claim attached to it
- conclusion contradicts retrieved context
- out-of-context retrieval drift, where the answer imports closed-domain facts
  or prior knowledge not present in the retrieved evidence pack
- unsupported drug, diagnosis, dose, code, restriction, or policy assertion
- direct alternative-drug recommendation when the task forbids it
- PHI output in summary, citations, error message, log, or exported artifact
- claiming certainty where retrieved evidence requires confirmation
- omitting a safety-critical constraint that changes clinical meaning

## 5. Soft Fails

These should be tracked, but should not by themselves eliminate a semantically
strong model:

- `answer` field instead of `summary`
- citations as a string instead of an array
- markdown code fence
- extra text around JSON
- bracket, bullet, or inline citation formatting variation
- citation order difference when all required source IDs are present
- verbose but safe wording

Soft fails become hard only if the normalizer cannot recover them without
changing meaning, inventing evidence, or dropping required safety language.

## 6. Normalizer Implementation Boundary

Normalizer work must stay separated from production app changes until the user
explicitly opens the production implementation track.

| Location | Scope | Entry condition |
|---|---|---|
| `local-llm-eval` runner-side normalizer | eval-only adapter and scoring support; EMR write 0 | allowed in this principles/eval track |
| `EMR_AI_24clinic` app/llm normalizer stage | production endpoint behavior | Phase 1d or later explicit GO only |

The runner-side normalizer may parse, map, and validate output envelopes for
evaluation. It must not mutate clinical meaning, invent source IDs, or create a
production dependency that bypasses the endpoint verifier.

## 7. Suggested Result Fields

Future result tables should separate these fields instead of publishing one
ambiguous strict score:

| Field | Meaning |
|---|---|
| `semantic_pass` | conclusion is clinically and contextually correct |
| `grounding_pass` | claims are supported by retrieved context |
| `citation_integrity` | citations exist and support the associated claims |
| `safety_pass` | no forbidden recommendation, unsafe certainty, or PHI leak |
| `normalizer_pass` | output can be converted to `{summary, citations}` |
| `native_contract_pass` | model emits strict contract without adapter help |
| `endpoint_pass` | real `/explain` response passes status/verifier/latency gates |
| `failure_owner` | retrieval, prompt, model, normalizer, verifier, endpoint, or infra |

Speed should be compared only after semantic and safety gates. A fast model with
unsafe or ungrounded output is not a viable RAG model.

## 8. Metric Framework Reference

The project should not import a metric toolkit blindly, but the local fields
should stay compatible with established RAG evaluation concepts.

| Local field / axis | External metric family | How to use here |
|---|---|---|
| `grounding_pass`, `context_only_compliance` | faithfulness / groundedness | claims must be supported by retrieved context |
| `semantic_pass`, `user_judgement_alignment` | answer relevance / response completeness | answer addresses the actual rule/check and user verdict |
| `retrieval_relevance` | context relevance / retrieval quality | retrieved chunks match the case semantics |
| `citation_integrity` | provenance / citation accuracy | source IDs exist and support the associated claims |
| `safety_pass`, `PHI_zero_hit` | clinical safety / privacy | no unsafe recommendation, over-certainty, or PHI leak |
| `latency_*`, `endpoint_pass` | operational endpoint quality | real endpoint behavior after model-quality gates |

Candidate references for later tooling review: RAGAS-style faithfulness and
context relevance, Microsoft RAG evaluator categories such as groundedness and
response completeness, and healthcare RAG safety checks focused on factual
alignment, clinical validity, privacy, and latency.

## 9. Mapping to Existing Phase 2 Axes

The existing frozen axes remain useful, but should be read through the lane
separation above:

| Existing axis | Primary lane |
|---|---|
| `citation_present` / `citation_valid_strict` / `citation_status_ok` | Semantic + Endpoint |
| `context_only_compliance` | Semantic |
| `safety_wording_compliance` | Semantic |
| `PHI_zero_hit` | Semantic + Endpoint hard gate |
| `latency_*` | Endpoint |
| `retrieval_relevance` | Endpoint / retrieval attribution |
| `user_judgement_alignment` | Semantic review |

This means a result can be interpreted as:

- semantically good but contract-fragile
- contract-good but semantically weak
- endpoint-failing due to retrieval or verifier behavior
- endpoint-ready

Only the last category should be treated as production-ready.

## 10. Current Objective Position

The prior strict JSON-heavy scoring was useful for finding integration risk,
but it is too narrow as the main RAG model-quality metric. It can over-penalize
models that produce correct, grounded, well-cited answers in a different
envelope, and it can understate risk when a model emits valid JSON containing
weak or unsupported content.

The better default is semantic-first evaluation, followed by normalizer
feasibility, then native strict-contract convenience, and finally real endpoint
readiness after explicit GO.

For the current LM Studio/Vulkan track, this particularly means:

- `gpt-oss-120b-mxfp4` should not be dismissed solely for strict JSON failure if
  raw semantic answers are strong and citations are exact.
- `qwen3.6-35b-a3b-mtp@q8_k_xl` should be treated as a semantic-potential
  candidate if its `answer` field is correct and grounded, even if the strict
  contract expected `summary`.
- Stage A strict results remain valuable, but they should be labeled as native
  contract / endpoint readiness evidence, not as the whole model-quality verdict.

## 11. Open Ambiguities

These remain explicit after R1 freeze as user-owned or implementation-stage
decisions, not blockers to freezing this principles document:

- exact lane weights after calibration; current values are working defaults
- R1 fix -> frozen entry condition and reviewer sign-off owner
- whether `failure_owner` is manual-only, automated, or hybrid
- whether metric tooling should use RAGAS-style libraries directly or a custom
  local scorer with compatible field names
- whether semantic/grounding auto-judging may use LLM-as-judge, and if so
  whether user verdict remains the primary authority for disputed cases
- whether endpoint-lane speed should influence model ranking or only production
  readiness after semantic gates

### 11.1 Remaining User-Owned At R1 Freeze

| Item | R1 freeze treatment |
|---|---|
| Exact lane weights | Working defaults are sufficient for R1; calibrate after Phase 2 data. |
| Reviewer sign-off owner | User issued `Phase 2 RAG principles v0.1 R1 frozen mark GO` on 2026-05-25. |
| `failure_owner` automation level | Decide during runner implementation. |
| Metric tooling | Decide during semantic-first runner design; custom local fields remain canonical. |
| LLM-as-judge use | User verdict remains primary until explicitly changed. |
| Endpoint speed in model ranking | Decide after semantic gates and endpoint calibration. |

## 12. Next Safe Actions

Allowed without additional GO:

- Review and edit this principles document.
- Update local-llm-eval documentation to reference this principles document.
- Design a result table schema that separates the four lanes.
- Prototype runner-side normalizer evaluation inside `local-llm-eval` only.

Still blocked without explicit GO:

- heavy model eval
- Phase 2 `/explain` execution
- EMR_AI_24clinic writes
- production normalizer changes inside `EMR_AI_24clinic`
- RA-03 changes
- Phase 2 Stage B/C expansion
- commit or push

## 13. Version Log

| Version | Date | Change |
|---|---|---|
| R0 draft | 2026-05-25 | Initial semantic-first principles draft. Four lanes: semantic, normalizer, native contract, real endpoint. |
| R1 fix candidate | 2026-05-25 | Added LLM role boundary, pipeline/failure-owner map, lane weights and gates, hard-fail additions, normalizer implementation boundary, metric framework reference, and open ambiguities. |
| R1 frozen | 2026-05-25 | User issued R1 frozen mark GO. Status marked frozen and remaining open ambiguities carried as user-owned or implementation-stage decisions. No heavy eval, `/explain`, EMR write, RA-03 change, Stage B/C, commit, or push. |
