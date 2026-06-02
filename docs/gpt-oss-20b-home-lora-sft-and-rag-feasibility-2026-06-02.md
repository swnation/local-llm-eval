---
id: gpt-oss-20b-home-lora-sft-and-rag-feasibility-2026-06-02
project: local-llm-eval
type: feasibility-plan
status: draft-plan
created: 2026-06-02
scope: GPT-OSS 20B home RTX 5080 LoRA/SFT pilot, with RAG-first carry for Korean clinic rules, HIRA notices, and clinical guidelines
related:
  - docs/rag-goals-evaluation-principles-v0.1.md
  - docs/rag_aware_eval_design_r0.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - docs/hpz2-phase2-l2-shortlist-lock-2026-05-27.md
  - docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md
  - docs/medical-rag-corpus-schema-draft-2026-06-02.md
---

# GPT-OSS 20B Home LoRA/SFT and RAG Feasibility Plan

## Project Goal Check

- Direct value: create a safe first pilot for adapting GPT-OSS behavior for the
  `clinical-assist` `/explain` lane before any 120B or external training work.
- Classification: direct progress, planning only.
- Narrower scope: run a local GPT-OSS 20B LoRA/SFT smoke on the home RTX 5080
  using synthetic non-PHI examples. Keep mutable medical and reimbursement
  facts in a versioned RAG corpus.

This document does not authorize data scraping, PHI export, external training,
model execution, `/explain`, EMR writes, relay update, or backup.

## Source Snapshot

Verified on 2026-06-02:

- OpenAI describes GPT-OSS models as open-weight models that run on
  user-controlled infrastructure or hosting providers, not through ChatGPT or
  the OpenAI API.
- OpenAI describes `gpt-oss-20b` as a medium open-weight model for local or
  specialized use cases and lists it as fine-tunable.
- The Hugging Face `openai/gpt-oss-20b` card says GPT-OSS models should use the
  harmony response format, and that `gpt-oss-20b` can be fine-tuned on consumer
  hardware.
- The Hugging Face card states GPT-OSS 20B runs within 16 GB of memory in its
  MXFP4 form.
- NVIDIA lists the GeForce RTX 5080 with 16 GB GDDR7 memory.
- OpenAI's GPT-OSS fine-tuning cookbook demonstrates GPT-OSS 20B SFT with
  Transformers, TRL, and LoRA.

References:

- https://help.openai.com/en/articles/11870455-openai-open-weight-models-gpt-oss
- https://platform.openai.com/docs/models/gpt-oss-20b
- https://huggingface.co/openai/gpt-oss-20b
- https://cookbook.openai.com/articles/gpt-oss/fine-tune-transfomers
- https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5080/

## Short Verdict

The home RTX 5080 plan is reasonable as a local behavior-adaptation smoke test,
not as a knowledge-ingestion project.

Recommended first architecture:

```text
synthetic non-PHI C1 instruction examples
       |
       v
GPT-OSS 20B + LoRA/SFT adapter
       |
       v
offline C1 and citation-discipline eval
```

Recommended later architecture:

```text
versioned medical/reimbursement corpus
       |
       v
retrieval + citation verifier + deterministic rule metadata
       |
       v
GPT-OSS base or adapter
       |
       v
C1-style grounded explanation
```

Do not train hospital rules, HIRA notices, or guideline facts into the adapter
as the primary source of truth. Train behavior only.

## Why 20B First

Use GPT-OSS 20B first because:

- it is the GPT-OSS variant explicitly positioned for consumer-hardware
  fine-tuning;
- it fits the home RTX 5080 memory envelope better than 120B;
- small adapter experiments can expose formatting, Korean explanation, and
  grounding-discipline risks before spending money on external 120B jobs;
- failure is cheap and local.

Treat 120B as a later reference or external-job candidate only after the 20B
pilot shows a measurable benefit over prompt/RAG baseline.

## Hardware Reality Check

RTX 5080 has 16 GB VRAM. That is enough to try GPT-OSS 20B in its intended
consumer-memory lane, but it does not guarantee comfortable full-precision
training.

First pilot constraints:

- use LoRA or QLoRA-style adapter training, not full fine-tuning;
- use tiny batches, gradient accumulation, gradient checkpointing if available,
  and short sequences first;
- start with a 10-example overfit smoke before any longer run;
- save adapter checkpoints only, not a merged production model;
- stop on repeated OOM rather than broadening into unstable offload tricks.

## Training Target

Good targets:

- emit the C1 shape reliably:

```json
{
  "summary": "grounded Korean explanation",
  "citations": ["source_id"]
}
```

- say evidence is insufficient instead of filling gaps;
- attach each clinical, drug, diagnosis, code, dose, and reimbursement claim to
  a supplied source ID;
- preserve distinctions between hospital rule, HIRA criterion, drug label, and
  clinical guideline;
- write concise Korean for a GP reviewer;
- refuse alternative-drug or treatment advice when unsupported.

Bad targets:

- memorizing HIRA notices;
- memorizing hospital rules;
- learning from raw EMR notes;
- replacing deterministic rule checks;
- answering patient-specific questions without retrieved evidence.

## Pilot Dataset

Use synthetic non-PHI examples only.

Stage 0 smoke:

- 10 examples;
- one or two source types;
- short context;
- train only long enough to prove the stack runs and the adapter saves.

Stage 1 behavior pilot:

- 100 to 300 instruction examples;
- 20% holdout by rule family/source type;
- include negative cases with insufficient evidence;
- include examples where hospital rule and reimbursement criterion differ.

Each training example should include:

- task instruction;
- synthetic case metadata;
- retrieved evidence snippets with source IDs;
- expected C1 output;
- forbidden claims.

## Baselines

Before judging the adapter, run the same holdout set against:

1. GPT-OSS 20B base + prompt only.
2. GPT-OSS 20B base + prompt + normalizer.
3. GPT-OSS 20B LoRA/SFT adapter + same prompt + same normalizer.

The adapter is useful only if it improves behavior without reducing grounding.

## Pass Criteria

For the first behavior pilot:

- PHI-like hits: 0.
- C1 shape pass: at least 95% after normalizer.
- Native C1 pass: measured separately, target at least 80% for the pilot.
- Source ID existence: 100%.
- Citation-claim pass: at least 90%.
- Unsupported clinical/reimbursement hard fail: 0.
- Insufficient-evidence cases: at least 90% correctly refuse or defer.
- User/manual Korean readability: adapter must improve over base or tie base
  without losing grounding.

Reject the adapter if it becomes more fluent but less grounded.

## Home Pilot Run Gates

Recommended gate sequence:

```text
GPT-OSS 20B home LoRA env preflight GO
GPT-OSS 20B 10-example LoRA smoke GO
GPT-OSS 20B LoRA holdout eval GO
GPT-OSS 20B adapter-vs-base review GO
```

Do not upload hospital internal rules or PHI to any external provider in this
track.

## Relationship to RAG Corpus

The LoRA pilot can proceed with synthetic evidence snippets, but any production
candidate must be evaluated with the versioned RAG corpus schema. The adapter
must learn to use supplied evidence, not to recall mutable facts from weights.

The next design document is:

```text
docs/medical-rag-corpus-schema-draft-2026-06-02.md
```

## 120B Carry

GPT-OSS 120B remains a later option:

- use it as a RAG baseline/reference model first;
- do not externally fine-tune it until the 20B adapter demonstrates that LoRA
  adds measurable behavior value;
- require provider due diligence before any external upload.

## STOP Carry

- No model execution in this document.
- No external upload.
- No external training job.
- No source scraping.
- No PHI or raw EMR use.
- No production `/explain`.
- No EMR_AI_24clinic write.
- No adapter merge or deployment.
- No commit/push without separate GO.
