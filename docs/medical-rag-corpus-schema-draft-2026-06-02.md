---
id: medical-rag-corpus-schema-draft-2026-06-02
project: local-llm-eval
type: schema-draft
status: draft
created: 2026-06-02
scope: versioned medical RAG corpus schema for clinic rules, HIRA notices, drug labels, and Korean clinical guidelines
related:
  - docs/gpt-oss-20b-home-lora-sft-and-rag-feasibility-2026-06-02.md
  - docs/rag-goals-evaluation-principles-v0.1.md
  - prompts/rag_aware_eval_set_v0.1.json
---

# Medical RAG Corpus Schema Draft

## Project Goal Check

- Direct value: define the source-of-truth data shape needed before any
  GPT-OSS LoRA/SFT or RAG production candidate can be judged safely.
- Classification: direct progress, schema planning only.
- Narrower scope: source metadata, chunk metadata, rule linkage, and eval linkage.
  This document does not ingest sources or authorize training.

## Design Principle

The corpus stores mutable medical and reimbursement facts outside the model.
Fine-tuning may teach behavior, but the RAG corpus owns the facts.

Every generated clinical, drug, diagnosis, dose, code, reimbursement, and
guideline claim must be traceable to:

- a source document;
- a version or effective date;
- a chunk ID;
- a source type;
- a use-rights status;
- a human review status.

## Source Types

Initial allowed source types:

| source_type | Meaning | Training upload default |
|---|---|---|
| `hospital_rule` | local clinic rule or deterministic rule metadata | blocked until owner approval |
| `hira_notice` | HIRA/MOHW reimbursement notice or criteria | retrieval only until use rights reviewed |
| `drug_label` | MFDS or approved label source | retrieval only until use rights reviewed |
| `clinical_guideline` | Korean guideline or society guideline | retrieval only until license reviewed |
| `synthetic_case` | generated non-PHI case/evidence example | allowed for local training after review |
| `eval_fixture` | synthetic eval-only case fixture | allowed for local training only if marked so |

## Source Document Record

```json
{
  "source_id": "hira_notice__2025_037__drug_x__v001",
  "source_type": "hira_notice",
  "publisher": "HIRA/MOHW",
  "title": "plain source title",
  "source_url": "https://example.invalid/source",
  "retrieved_date": "2026-06-02",
  "published_date": "2025-02-15",
  "effective_date": "2025-03-01",
  "expiry_date": null,
  "version_label": "notice-2025-037",
  "jurisdiction": "KR",
  "language": "ko",
  "scope_tags": ["drug_reimbursement", "pediatrics"],
  "status": "active",
  "supersedes": [],
  "superseded_by": [],
  "license_or_use_note": "needs review before external upload",
  "allowed_uses": {
    "retrieval": true,
    "local_training": false,
    "external_training": false,
    "redistribution": false
  },
  "phi_risk": "none_expected",
  "clinical_owner_review": "pending",
  "source_hash_sha256": "pending",
  "notes": ""
}
```

## Chunk Record

```json
{
  "chunk_id": "hira_notice__2025_037__drug_x__v001__chunk_0001",
  "source_id": "hira_notice__2025_037__drug_x__v001",
  "chunk_index": 1,
  "section_title": "coverage criteria",
  "text": "retrieval text excerpt",
  "char_start": 0,
  "char_end": 420,
  "token_estimate": 180,
  "claim_tags": ["dose", "coverage_condition"],
  "entity_tags": {
    "drug_codes": [],
    "drug_names": [],
    "dx_codes": [],
    "age_bands": []
  },
  "effective_date": "2025-03-01",
  "status": "active",
  "phi_scan": {
    "status": "pass",
    "scanner": "pending",
    "checked_at": "2026-06-02"
  },
  "embedding_status": "not_built",
  "notes": ""
}
```

## Rule Link Record

Use this to connect deterministic app rules to RAG evidence.

```json
{
  "rule_link_id": "rule_link__age_drug_001__hira_notice_2025_037",
  "rule_id": "age_drug_001",
  "rule_owner": "clinical-assist",
  "linked_source_ids": ["hira_notice__2025_037__drug_x__v001"],
  "linked_chunk_ids": ["hira_notice__2025_037__drug_x__v001__chunk_0001"],
  "relationship": "supports_explanation",
  "required_for_explain": true,
  "local_rule_vs_external_source": "local_rule_more_conservative",
  "review_status": "pending_clinician_review",
  "notes": ""
}
```

## Eval Link Record

Use this to build synthetic cases and judge RAG behavior.

```json
{
  "eval_case_id": "med_rag_synth_001",
  "case_type": "synthetic_non_phi",
  "task_type": "explain_rule_trigger",
  "source_ids": ["hospital_rule__age_drug_001__v001"],
  "chunk_ids": ["hospital_rule__age_drug_001__v001__chunk_0001"],
  "expected_claims": [
    {
      "claim_id": "claim_001",
      "text": "The explanation must state the age-related review reason.",
      "supporting_chunk_ids": ["hospital_rule__age_drug_001__v001__chunk_0001"]
    }
  ],
  "forbidden_claims": [
    "do not recommend an alternative medication",
    "do not claim reimbursement approval if retrieved evidence is insufficient"
  ],
  "expected_citations": ["hospital_rule__age_drug_001__v001__chunk_0001"],
  "negative_case": false,
  "holdout_group": "age_drug_rules",
  "manual_review_status": "pending"
}
```

## Corpus Build Stages

| Stage | Scope | Output |
|---|---|---|
| S0 | schema review only | this document |
| S1 | 10 synthetic source/chunk fixtures | no public source ingestion |
| S2 | hospital-rule metadata pilot | no raw patient text |
| S3 | HIRA/public-source retrieval pilot | license/use review required |
| S4 | guideline-source retrieval pilot | license/use review required |
| S5 | eval-set linkage | synthetic cases only |

## Validation Rules

Minimum validators:

- every `chunk_id` maps to an existing `source_id`;
- every `rule_link` chunk maps to an existing chunk;
- `effective_date` is present for `hira_notice`, `drug_label`, and
  `clinical_guideline`;
- `allowed_uses.external_training` defaults to false;
- `phi_scan.status` must be pass before local training use;
- no eval case can cite a source whose retrieval use is false;
- no external upload if any referenced source has unknown use rights.

## STOP Carry

- No source scraping.
- No public corpus ingestion.
- No hospital-rule export.
- No PHI or raw EMR.
- No external training.
- No model execution.
- No EMR_AI_24clinic write.
- No commit/push without separate GO.
