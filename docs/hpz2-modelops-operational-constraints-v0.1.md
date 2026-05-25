---
id: hpz2-modelops-operational-constraints-v0.1
project: local-llm-eval
type: runbook
status: draft
version: 0.1
created: 2026-05-25
updated: 2026-05-25
scope: HP Z2 LM Studio/Vulkan model selection, disk guardrails, and pre-heavy ModelOps testing
related:
  - docs/rag-goals-evaluation-principles-v0.1.md
  - docs/hpz2-lmstudio-phase2-stage-a-config-2026-05-24.md
  - docs/hpz2-lmstudio-phase2-stage-ar-model-aware-2026-05-24.md
  - ../../hpz2-run-artifacts/scripts/modelops_profile_matrix.py
  - ../../hpz2-run-artifacts/scripts/modelops_select_and_cleanup.py
---

# HP Z2 ModelOps Operational Constraints v0.1

> This runbook covers model selection and disk-safe test operations before any
> Phase 2 heavy run. It does not authorize heavy eval, real `/explain`, EMR
> writes, RA-03 changes, Stage B/C expansion, commit, push, or destructive model
> cleanup without an explicit GO.

## 0. Scope

This document captures the operational rules that were intentionally kept out
of the RAG principles document:

- which model families to prioritize before heavy run
- how to treat very large downloads
- how to keep `C:` free space above the hard floor
- how to cycle through installed models, cleanup, download, and retest
- how to keep LM Studio/Vulkan results separate from legacy Ollama context

The canonical workspace for this document is the main PC repo. HP Z2 remains
execution-only.

## 1. Hard Guardrails

| Guardrail | Rule |
|---|---|
| Runtime lane | LM Studio / llama.cpp Vulkan only for this track |
| Heavy run | blocked until explicit user GO |
| Real endpoint | no Phase 2 `/explain` execution without explicit user GO |
| EMR repo | no `EMR_AI_24clinic` writes without explicit user GO |
| Commit/push | separate explicit GO only |
| Disk floor | keep `C:` free space >= 100 GB after each cleanup/download/test step |
| Large model size | models requiring more than about 71 GB on disk are low priority unless there is a strong reason and explicit user approval |
| Source trust | prefer official publisher models and high-trust GGUF distributors such as Unsloth |
| Result interpretation | semantic-first; strict JSON/native contract failure is not the whole model verdict |

If any step would violate the disk floor, stop before download or cleanup and
report the blocker.

## 2. Model Priority Policy

Prioritize models that are likely to provide useful RAG reasoning while staying
practical on HP Z2:

1. Already installed models first.
2. Official publisher LM Studio entries or official Hugging Face org releases.
3. Unsloth GGUF releases when official GGUF is unavailable or less practical.
4. Quantizations that keep model files comfortably below the disk and load
   limits while preserving useful reasoning quality.
5. Speed-favorable architectures: MoE, MTP, small active-parameter models, or
   models with strong draft-token/speculative behavior.
6. 70B+ models only when the selected quant is disk-practical and offers a
   clear semantic-quality reason over smaller candidates.

Deprioritize:

- 70B+ variants whose local footprint exceeds about 71 GB.
- duplicate families where a smaller or faster quant already gives comparable
  semantic results.
- models that are only strict-contract convenient but semantically weak.
- models with weak provenance, unclear quant lineage, or stale community
  repacks when official or Unsloth options exist.

Live model-card/source verification is required before any new download because
publisher, quant, file size, and compatibility details can change.

## 3. Installed Snapshot Reference

The following snapshot came from
`../../hpz2-run-artifacts/results/modelops/overnight_until_15_20260525_040708/final_lms_ls.json`.
It is useful for planning, but must be refreshed with `lms ls` before execution.

| Model key | Publisher | Params | Quant | Size GiB | Architecture | Initial treatment |
|---|---|---:|---|---:|---|---|
| `openai/gpt-oss-120b` | openai | 120B | MXFP4 | 59.03 | gpt-oss | high-priority large semantic candidate; below 71 GB |
| `qwen3.5-122b-a10b-mtp` | unsloth | 122B-A10B | Q3_K_M | 54.20 | qwen35moe | preserve for MTP/MoE comparison unless disk floor forces review |
| `qwen3.5-122b-a10b` | unsloth | 122B-A10B | Q3_K_M | 52.55 | qwen35moe | compare only if MTP sibling does not dominate |
| `llama-3.3-70b-instruct` | unsloth | 70B | Q4_K_M | 39.60 | llama | slow but useful 70B baseline |
| `qwen3.6-35b-a3b-mtp@q8_k_xl` | unsloth | 35B-A3B | Q8_K_XL | 38.08 | qwen35moe | high-priority MTP/MoE semantic candidate |
| `gemma-4-31b-it` | unsloth | 31B | Q8_K_XL | 34.76 | gemma4 | medium-large comparison; keep if semantic signal justifies |
| `google/gemma-4-26b-a4b` | google | 26B-A4B | Q8_0 | 26.13 | gemma4 | high-trust official candidate |
| `qwen3.6-35b-a3b-mtp@?` | unsloth | 35B-A3B | MXFP4/MoE | 22.32 | qwen35moe | investigate exact quant label before ranking |
| `qwen/qwen3.6-35b-a3b` | qwen | 35B-A3B | Q4_K_M | 20.55 | qwen35moe | official small-active candidate; high priority |
| `unsloth/gemma-4-26b-a4b-it` | unsloth | 26B-A4B | MXFP4/MoE | 17.55 | gemma4 | speed-favorable Gemma comparison |
| `mistral-small-3.2-24b-instruct-2506` | unsloth | 24B | Q4_K_XL | 13.55 | llama | practical mid-size comparator |
| `unsloth/gpt-oss-20b` | unsloth | 20B | F16 | 12.85 | gpt-oss | compare against official 20B only if output differs materially |
| `openai/gpt-oss-20b` | openai | 20B | MXFP4 | 11.28 | gpt-oss | speed baseline and known comparator |

This table is not a deletion plan. Deletion requires a fresh inventory, disk
check, result review, and explicit cleanup GO.

## 4. Pre-Heavy Test Ladder

Use the lightest useful test before moving toward heavier work:

| Level | Purpose | Endpoint? | Allowed without heavy-run GO? |
|---|---|---:|---:|
| L0 inventory | `lms ls`, model sizes, disk free, loaded model state | no | yes |
| L1 source verification | official/Unsloth model card, quant, file size, license, compatibility | no | yes |
| L2 synthetic semantic smoke | short RAG-like prompts through LM Studio only | no `/explain` | requires explicit ModelOps test GO |
| L3 normalizer feasibility | runner-side parsing to `{summary, citations}` | no `/explain` | requires explicit normalizer/test GO |
| L4 native contract check | strict JSON/schema behavior in LM Studio | no `/explain` | requires explicit ModelOps test GO |
| L5 real endpoint | actual `/explain` Phase 2 cell | yes | blocked until Phase 2 heavy run GO |

L2-L4 can make a model eligible for heavy-run consideration, but cannot declare
production readiness. Only L5 can do that.

## 5. Disk-Safe Pull / Test / Cleanup Loop

Each iteration should follow this order:

1. Refresh inventory: `lms ls` and current `C:` free space.
2. Confirm no model is loaded before cleanup or large download.
3. Test already installed candidates first.
4. Rank candidates with semantic-first fields from
   `docs/rag-goals-evaluation-principles-v0.1.md`.
5. Mark cleanup candidates only when they are clearly lower priority, redundant,
   or failed in a way that is not a prompt/normalizer artifact.
6. Dry-review cleanup paths and sizes. Refuse any path outside
   `C:\Users\test\.lmstudio\models`.
7. Delete only after explicit cleanup GO.
8. Re-check `C:` free space. It must remain >= 100 GB.
9. Download the next highest-priority verified model only if the post-download
   estimate remains above the disk floor.
10. Retest, unload, and record final loaded models as `[]`.

Cleanup should be conservative. For example, the existing
`modelops_select_and_cleanup.py` only lists `qwen3.6-27b-mtp` as a safe-delete
directory. Broader cleanup rules require review before use.

## 6. Selection Fields

Future ModelOps summaries should include these fields:

| Field | Meaning |
|---|---|
| `model_key` | LM Studio key or exact local model identifier |
| `publisher` | official org, Unsloth, or other distributor |
| `source_trust` | official, high-trust GGUF, community, unknown |
| `params_active` | total params and active params for MoE/MTP when known |
| `quant` | exact quantization label |
| `size_gib` | local footprint |
| `fits_disk_policy` | whether it stays below the current disk threshold |
| `speed_signal` | tok/s, load time, and draft-token/speculative signal if available |
| `semantic_signal` | semantic RAG lane quality |
| `normalizer_signal` | recoverability to `{summary, citations}` |
| `native_contract_signal` | strict JSON/schema behavior |
| `cleanup_priority` | keep, review, delete-candidate, preserve-by-user-rule |
| `reason` | one-line objective rationale |

## 7. Current Objective Position

The next useful work is not to run more models blindly. It is to convert the
frozen RAG principles into a disk-safe candidate-management plan, then run only
the smallest tests that can distinguish semantic potential, normalizer
recoverability, native contract convenience, and endpoint readiness.

Given the current direction:

- treat `gpt-oss-120b` as a serious semantic candidate because its MXFP4
  footprint is under the user's approximate 71 GB practicality limit;
- keep MTP/MoE candidates in scope because their active-parameter and speed
  profiles may be materially better than dense 70B+ baselines;
- do not keep a model solely because it emits strict JSON;
- do not delete large or unusual candidates just because one strict-contract run
  failed;
- make official/Unsloth provenance and disk safety explicit before every new
  download.

## 8. STOP Carry

- No heavy eval in this document.
- No Phase 2 `/explain` call in this document.
- No EMR_AI_24clinic write.
- No RA-03 changes.
- No Stage B/C expansion.
- No cleanup or download without a fresh inventory, disk check, and explicit GO.
- No commit or push without separate GO.

## 9. Version Log

| Version | Date | Change |
|---|---|---|
| R0 draft | 2026-05-25 | Initial HP Z2 ModelOps operational constraints runbook. Captures disk floor, model priority policy, installed snapshot, pre-heavy test ladder, cleanup loop, and STOP carry. |
