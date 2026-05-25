---
id: rag-cross-industry-patterns-v0.1
project: local-llm-eval
type: research-carry
status: draft
version: 0.1
created: 2026-05-25
updated: 2026-05-25
scope: Cross-industry RAG evaluation patterns and v0.2 carry input
related:
  - docs/rag-goals-evaluation-principles-v0.1.md
  - docs/rag_aware_eval_design_r0.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
---

# Cross-Industry RAG Patterns v0.1

> This document records external RAG evaluation patterns for later v0.2 or
> runner-design work. It does not reopen the R1 frozen principles document, and
> it does not authorize heavy eval, real `/explain`, EMR writes, RA-03 changes,
> Stage B/C expansion, commit, or push.

## 0. Verdict

The R1 frozen principles document is consistent with the main patterns found
across clinical, legal, financial/regulatory, and enterprise RAG evaluation:

- separate retrieval, grounding, answer utility, citation, and endpoint metrics;
- treat high-risk domains as requiring domain-specific metrics and human review;
- penalize fabricated or claim-mismatched citations;
- keep strict output contract evaluation separate from answer quality;
- preserve provenance and auditability for regulated workflows.

The external review does not create a freeze blocker. It creates v0.2 carry
items for scorer design, runner output fields, and later production audit
planning.

## 1. Verified Source Set

| Source | Verified takeaway | Local mapping |
|---|---|---|
| RAGAS metrics docs | RAG evaluation metrics include context precision, context recall, response relevancy, and faithfulness. | Supports quantifying current `grounding_pass`, `semantic_pass`, and `retrieval_relevance` fields. |
| Microsoft RAG evaluators | Separates system evaluation (`Groundedness`, `Relevance`, `Response Completeness`) from process/retrieval evaluation. | Matches lane separation and `failure_owner`. |
| RAG-X medical QA | Medical RAG needs independent retriever/generator diagnosis and grounding-aware success, not only apparent answer accuracy. | Supports `failure_owner` and semantic-first gates. |
| Auditable clinical AI-CDSS framework | Clinical decision support should preserve source verification, provenance, transparency, and audit logging. | Future Phase 1d / production audit trail carry, not current eval-only scope. |
| LegalBench-RAG | Legal RAG benchmark emphasizes precise minimal snippets, expert annotation, and avoiding context bloat/hallucination. | Supports top_k/min_similarity tuning and user spot-check as expert annotation. |
| Walking a Tightrope | High-risk medical/legal evaluation needs refined domain-specific metrics and human-centric reliability. | Supports user verdict primary and high-risk hard fails. |
| Case-aware enterprise RAG judge | Enterprise RAG evaluation can be case-aware, severity-aware, and separated into retrieval, grounding, utility, and workflow alignment. | Supports case-aware RA-01/RA-03/RA-05 scoring later. |
| CCRS | Uses multi-metric LLM-as-judge dimensions such as relevance, correctness, density, coherence, and recall. | Supports optional LLM-judge layering if user approves. |
| RAGalyst | Domain-specific RAG evaluation should align automated judging with human annotations; no single model/config is universally optimal. | Supports model-by-case evaluation and user verdict primary. |
| Financial metric-failure paper | Financial-domain GenAI evaluation warns that generic metrics and SME review can still fail without a risk framework. | Supports metric-risk review; exact "Traceable Fusion Score" term remains unverified from primary source. |

## 2. Confirmed Alignment With R1 Frozen Principles

| R1 principle | Cross-industry support | Status |
|---|---|---|
| Four-lane split: Semantic / Normalizer / Native Contract / Endpoint | RAGAS, Microsoft, RAG-X, enterprise evaluators separate retrieval/process, grounding, answer utility, and output behavior. | keep |
| Semantic-first model quality | Medical/legal/high-risk sources emphasize factual grounding and domain-specific correctness over generic format success. | keep |
| Hard fail: nonexistent citation | Legal and clinical sources treat source attribution as reliability-critical. | keep |
| Hard fail: citation-claim mismatch | Legal precise snippet retrieval and clinical source verification both require claim-level support. | keep |
| Hard fail: out-of-context drift | Groundedness/faithfulness metrics directly target unsupported claims from model memory. | keep |
| User verdict primary | Legal expert annotation and high-risk human-centric evaluation support this. | keep |
| Normalizer lane as local contract adapter | External "normalization" often means retrieval score normalization, not output envelope normalization. The local definition remains correct for this app. | keep local definition |

## 3. v0.2 Carry Candidates

| ID | Candidate | Why it matters | Suggested entry point |
|---|---|---|---|
| C1 | Atomic claim decomposition | RAGAS faithfulness and clinical/legal citation practice benefit from claim-by-claim grounding rather than one boolean. | semantic-first runner build |
| C2 | Retrieval Precision@k / Recall@k / Context Recall | LegalBench-RAG and RAGAS-style retrieval metrics expose whether failures are retrieval or generation. | Phase 2 design R2 axis 6 update |
| C3 | Response completeness / missing-critical-info score | Microsoft distinguishes groundedness precision from completeness recall. | v0.2 result schema |
| C4 | Case-aware scoring | RA-01 pediatric retrieval, RA-03 safety boundary, and RA-05 rule/KB nuance should not share identical scoring emphasis. | scorer design |
| C5 | Multi-method metric layering | Combine boolean gates, 0-1 quantitative metrics, optional LLM-as-judge, and user verdict. | runner design after user decision |
| C6 | Provenance and audit trail | Clinical and regulated-domain sources support logging source version, retrieval set, prompt/profile, verifier result, and model ID. | Phase 1d / production implementation, not current EMR write scope |
| C7 | Metric-risk review | Financial-domain metric-failure framing suggests documenting where metrics can mislead. | v0.2 scoring notes |

## 4. Non-Carry Or Caution Items

| Item | Treatment |
|---|---|
| "Traceable Fusion Score" exact term | Not confirmed from primary source in this verification pass. Keep only the broader idea: trace how retrieved evidence is used, ignored, or contradicted. |
| Retrieval-score normalization | Not the same as this project's output normalizer lane. Do not conflate them. |
| Full LLM-as-judge automation | Keep behind user decision. High-risk workflow should not replace user verdict with judge output by default. |
| Production audit trail | Valuable, but it implies EMR app behavior and storage choices. Keep for Phase 1d or explicit production-design GO. |

## 5. Suggested v0.2 Result Schema Additions

These are candidate additions to the current eight result fields, not R1 frozen
requirements:

| Field | Type | Meaning |
|---|---|---|
| `claim_count` | integer | number of atomic claims extracted from answer |
| `claim_grounded_count` | integer | claims supported by retrieved evidence |
| `claim_grounding_score` | float 0-1 | `claim_grounded_count / claim_count` |
| `retrieval_precision_at_k` | float 0-1 | relevant retrieved chunks divided by retrieved chunks |
| `retrieval_recall_proxy` | float 0-1 or manual label | whether required evidence appears in retrieved set |
| `response_completeness` | pass/fail or 0-1 | whether critical expected information is missing |
| `case_metric_profile` | enum/string | RA-case-specific scoring profile |
| `metric_risk_notes` | string | known ways this score can overstate/understate quality |
| `audit_artifact_id` | string | future production artifact reference, if/when implemented |

## 6. Source URLs

- RAGAS metrics: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
- Microsoft RAG evaluators: https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators
- RAG-X medical QA: https://arxiv.org/abs/2603.03541
- Auditable clinical AI-CDSS: https://pmc.ncbi.nlm.nih.gov/articles/PMC12913532/
- LegalBench-RAG: https://arxiv.org/abs/2408.10343
- Walking a Tightrope: https://arxiv.org/abs/2311.14966
- Case-aware enterprise RAG judge: https://arxiv.org/abs/2602.20379
- CCRS: https://arxiv.org/abs/2506.20128
- RAGalyst: https://arxiv.org/abs/2511.04502
- Financial metric-failure paper: https://researchtrend.ai/papers/2510.13524

## 7. STOP Carry

- No heavy eval.
- No `/explain` execution.
- No EMR_AI_24clinic write.
- No RA-03 change.
- No Stage B/C expansion.
- No commit or push without separate GO.
- C6 provenance/audit trail is future production scope, not current eval-only scope.

## 8. Version Log

| Version | Date | Change |
|---|---|---|
| R0 draft | 2026-05-25 | Initial cross-industry RAG pattern carry. Verified the main Claude research direction against primary or high-trust sources and captured v0.2 carry candidates C1-C7. |
