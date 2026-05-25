---
id: hpz2-phase2-ladder-progress-v0.1
project: local-llm-eval
type: progress-tracking
status: live
version: 0.1
created: 2026-05-25
updated: 2026-05-25
scope: Single source of truth for HP Z2 Phase 2 L0-L5 ladder progress
related:
  - docs/rag-goals-evaluation-principles-v0.1.md
  - docs/rag-cross-industry-patterns-v0.1.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - docs/rag_aware_eval_design_r0.md
  - prompts/rag_aware_eval_set_v0.1.json
  - models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json
  - models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json
---

# HP Z2 Phase 2 Ladder Progress v0.1

> This is the live single source of truth for L0-L5 progress. If context is
> lost, read this file plus the three frozen/planning docs listed in `related`
> before continuing. This tracker does not authorize heavy eval, real
> `/explain`, EMR writes, RA-03 changes, Stage B/C expansion, commit, push, or
> model cleanup/download without the matching explicit GO.

## 0. Scope

This tracker records:

- the current L0-L5 ladder status;
- the next exact GO phrase;
- parallel Main PC / HP Z2 / reviewer tracks;
- append-only result archives for each completed step;
- live STOP carry that must survive context loss.

Rules:

- §2 is the live snapshot and may be updated as statuses change.
- §5 is append-only; do not delete prior result entries. Add correction notes
  instead of rewriting history.
- Commit/push after updates is recommended only after explicit commit/push GO.
- HP Z2 remains execution-only. Main PC remains canonical for docs, commits,
  and pushes.

## 1. Quick Status

| Field | Value |
|---|---|
| Current level | L0 pending / L1 pending |
| Current repo HEAD | `c376052` (`docs(rag): add semantic-first planning docs`) |
| Current tracker status | live R0, initial pending snapshot |
| Next recommended GO | `HP Z2 L0 inventory + L1 source verification GO` |
| L2 blocker | Phase 2.1 design R2 update + semantic-first runner build |
| L3 blocker | runner-side normalizer feasibility prototype |
| L5 hard blocker | RA-03 user-owned final checks + explicit `Phase 2 heavy run GO` |
| Disk hard floor | `C:` free space >= 100 GB |
| Runtime lane | LM Studio / llama.cpp Vulkan, not Ollama |

## 2. Ladder Status Snapshot

| Level | Status | GO issued | Result reported | Artifact path | Reviewer verdict | Next |
|---|---|---|---|---|---|---|
| L0 inventory | pending | - | - | - | - | wait for `HP Z2 L0 inventory + L1 source verification GO` |
| L1 source verification | pending | - | - | - | - | run with L0, then report inventory/source matrix |
| L2 semantic smoke | blocked-by-design-R2 | - | - | - | - | requires L1 + design R2 + semantic-first runner build |
| L3 normalizer feasibility | blocked | - | - | - | - | requires L2 results + runner-side normalizer prototype |
| L4 native contract check | blocked | - | - | - | - | requires L2/L3 review and explicit L4 GO |
| L5 real endpoint | blocked-hard | - | - | - | - | requires RA-03 checks + sufficient L2-L4 evidence + `Phase 2 heavy run GO` |

## 3. Parallel Track Status

| Track | Scope | Status | Ladder dependency | Owner |
|---|---|---|---|---|
| Phase 2.1 design R1 -> R2 update | 4-lane mapping, scorer P7 placeholder rejection fix, acceptable citation set, model-axis catalog, C1-C7 hooks | pending | recommended before L2 | Main PC Codex |
| Stage A-R lane reinterpretation | Reclassify existing Stage A-R / ModelOps results under 4 lanes and L0-L5 ladder | pending | useful before L2 comparisons | Main PC Codex |
| Semantic-first runner build | Add or adapt local-llm-eval runner for semantic fields and v0.2 metric hooks | pending | required before L2 | Main PC Codex |
| Normalizer adapter prototype | Runner-side only, eval scope, no EMR production write | pending | required before L3 | Main PC Codex |
| L0 inventory + L1 source verification | Refresh `lms ls`, loaded state, C: free space, source/model-card trust matrix | pending | safe first execution step | HP Z2 Codex |
| RA-03 user-owned checks | Final input/citation/user-verdict checks required before real endpoint | pending | hard blocker before L5 | User |
| Claude/read-only review | Review tracker updates, design R2, L0-L5 result packets | standby | after each result report | HP Z2 Claude |

## 4. GO Carry

| GO phrase | Scope | Expected artifact | STOP boundaries |
|---|---|---|---|
| `HP Z2 L0 inventory + L1 source verification GO` | Refresh HP Z2 model inventory, C: free space, loaded model state, and source trust/quant/size verification | L0/L1 result packet + §5 archive entry | no model performance matrix, no cleanup, no download unless separately approved |
| `Phase 2.1 design R1 -> R2 update GO` | Update design/eval docs with 4-lane mapping, scorer fix, acceptable citation set, model catalog, and C1-C7 hooks | design R2 diff/report | no heavy eval, no EMR write |
| `HP Z2 semantic-first runner build GO` | Implement eval-only runner support for semantic fields and v0.2 metric hooks | tools/config docs + dry-run evidence | no `/explain`, no EMR write |
| `HP Z2 L2 semantic smoke matrix GO` | Synthetic LM Studio-only semantic smoke over approved Tier models | L2 result packet + §5 archive entry | no real `/explain`; maintain C: >= 100 GB |
| `HP Z2 L3 normalizer feasibility GO` | Runner-side conversion of model output to `{summary, citations}` | L3 result packet + normalizer notes | no production normalizer change |
| `HP Z2 L4 native contract check GO` | Strict JSON/schema convenience check | L4 result packet | native contract does not override semantic gate |
| `Phase 2 heavy run GO` | L5 real `/explain` endpoint cells | Phase 2 result packet | requires separate explicit GO, RA-03 checks, and EMR read-only constraints |
| `Phase 2 ladder tracker commit + push GO` | Commit tracker changes | git commit/push | docs only unless explicitly broadened |

## 5. Result Archive

Append new result entries below. Keep old entries intact.

### L0 inventory

- Status: pending
- GO issued: -
- Artifact: -
- Key fields to capture:
  - `lms ls` output path
  - loaded model state before/after
  - C: free space
  - installed LLM count
  - model root path
  - final loaded models should be `[]`
- Reviewer verdict: -
- Next GO: `HP Z2 L0 inventory + L1 source verification GO`

### L1 source verification

- Status: pending
- GO issued: -
- Artifact: -
- Key fields to capture:
  - model key
  - publisher/distributor
  - source URL
  - quant
  - local size GiB
  - source trust
  - license/access notes
  - keep/review/delete-candidate recommendation
- Reviewer verdict: -
- Next GO: wait for L0/L1 result review

### L2 semantic smoke matrix

- Status: blocked
- GO issued: -
- Artifact: -
- Required before entry:
  - L0/L1 reviewed
  - design R2 updated or accepted as not needed for this L2 slice
  - semantic-first runner built or selected
- Reviewer verdict: -
- Next GO: pending

### L3 normalizer feasibility

- Status: blocked
- GO issued: -
- Artifact: -
- Required before entry:
  - L2 semantic candidates selected
  - runner-side normalizer scope approved
- Reviewer verdict: -
- Next GO: pending

### L4 native contract check

- Status: blocked
- GO issued: -
- Artifact: -
- Required before entry:
  - L2/L3 reviewed
  - strict contract check targets selected
- Reviewer verdict: -
- Next GO: pending

### L5 real endpoint

- Status: blocked-hard
- GO issued: -
- Artifact: -
- Required before entry:
  - RA-03 user-owned checks complete
  - sufficient L2-L4 evidence
  - explicit `Phase 2 heavy run GO`
  - EMR_AI_24clinic read-only constraints reconfirmed
- Reviewer verdict: -
- Next GO: pending

## 6. STOP Carry

- No heavy eval without explicit GO.
- No real `/explain` without explicit `Phase 2 heavy run GO`.
- No EMR_AI_24clinic write without explicit GO.
- No RA-03 changes or inferred replacement values without explicit user instruction.
- No Stage B/C expansion without explicit GO.
- No chunk regeneration or 681 baseline rebuild unless explicitly reopened.
- No model cleanup or download without fresh inventory, disk check, and explicit GO.
- Keep `C:` free space >= 100 GB.
- Refuse cleanup paths outside `C:\Users\test\.lmstudio\models`.
- Keep synthetic PHI fixtures internal/redacted when shared outside repo context.
- Preserve Qwen3.5 122B candidates unless cleanup is explicitly approved after review.
- Treat audit trail / provenance implementation as Phase 1d or production scope.
- No commit or push without separate GO.

## 7. Version Log

| Version | Date | Change |
|---|---|---|
| R0 | 2026-05-25 | Initial L0-L5 progress tracker. Snapshot all levels pending/blocked, added parallel tracks, GO carry, result archive placeholders, and STOP carry. |
