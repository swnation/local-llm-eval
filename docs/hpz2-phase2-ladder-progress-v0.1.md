---
id: hpz2-phase2-ladder-progress-v0.1
project: local-llm-eval
type: progress-tracking
status: live
version: 0.1
created: 2026-05-25
updated: 2026-05-27
scope: Single source of truth for HP Z2 Phase 2 L0-L5 ladder progress
related:
  - docs/rag-goals-evaluation-principles-v0.1.md
  - docs/rag-cross-industry-patterns-v0.1.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - docs/rag_aware_eval_design_r0.md
  - prompts/rag_aware_eval_set_v0.1.json
  - models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json
  - models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json
  - models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json
  - tools/hpz2_lmstudio_phase2_l2_semantic_runner.py
  - docs/hpz2-lmstudio-phase2-l2-semantic-runner-2026-05-25.md
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
  - tools/hpz2_llamacpp_phase2_l2_runner.py
  - docs/hpz2-llamacpp-phase2-l2-runner-2026-05-26.md
  - docs/hpz2-phase2-backend-lane-decision-2026-05-26.md
  - docs/hpz2-phase2-l2-shortlist-lock-2026-05-27.md
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
- §1 `Current repo HEAD` must be bumped in the same commit as any tracker
  content change.
- Commit/push after updates is recommended only after explicit commit/push GO.
- HP Z2 remains execution-only. Main PC remains canonical for docs, commits,
  and pushes.

## 1. Quick Status

| Field | Value |
|---|---|
| Current level | L0 complete / L1 complete / LM Studio L2 complete as secondary / llama.cpp primary lane locked / L2 full matrix complete / shortlist locked |
| Current repo HEAD | `b53fb7f` (`fix(rag): call semantic scorer with keywords`) before this shortlist codify update |
| Current tracker status | live R5 working tree, shortlist codification in progress |
| Next recommended GO | review + commit/push this shortlist codification; then decide L3 normalizer feasibility or L5 heavy-run planning |
| L2 blocker | none for synthetic L2 evidence; current primary shortlist is locked |
| L3 blocker | user GO + runner-side normalizer feasibility prototype over locked primary shortlist |
| L5 hard blocker | RA-03 user-owned final checks + explicit `Phase 2 heavy run GO` |
| Disk hard floor | `C:` free space >= 100 GB |
| Runtime lane | llama.cpp primary / LM Studio secondary, not Ollama |

## 2. Ladder Status Snapshot

| Level | Status | GO issued | Result reported | Artifact path | Reviewer verdict | Next |
|---|---|---|---|---|---|---|
| L0 inventory | complete | 2026-05-25 | 2026-05-25 | `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323` | accepted-for-design-R2 | complete |
| L1 source verification | complete | 2026-05-25 | 2026-05-25 | `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323` | accepted-for-design-R2 | use source matrix for model-axis catalog |
| L2 semantic smoke | complete-shortlist-locked | 2026-05-26/27 | LM Studio L2 completed as secondary; llama.cpp full matrix and bonus probes completed; shortlist locked | `C:\Github\hpz2-run-artifacts\results\hpz2_llamacpp_l2_integrated_report_20260527.md` | accepted-for-shortlist-codify | repo review + commit/push; then L3 or L5 planning decision |
| L3 normalizer feasibility | blocked | - | - | - | - | requires L2 results + runner-side normalizer prototype |
| L4 native contract check | blocked | - | - | - | - | requires L2/L3 review and explicit L4 GO |
| L5 real endpoint | blocked-hard | - | - | - | - | requires RA-03 checks + sufficient L2-L4 evidence + `Phase 2 heavy run GO` |

## 3. Parallel Track Status

| Track | Scope | Status | Ladder dependency | Owner |
|---|---|---|---|---|
| Phase 2.1 design R1 -> R2 update | 4-lane mapping, scorer P7 placeholder rejection fix, acceptable citation set, model-axis catalog, C1-C7 hooks | complete-committed | required before L2 | Main PC Codex |
| Stage A-R lane reinterpretation | Reclassify existing Stage A-R / ModelOps results under 4 lanes and L0-L5 ladder | pending | useful before L2 comparisons | Main PC Codex |
| Semantic-first runner build | Add or adapt local-llm-eval runner for semantic fields and v0.2 metric hooks | complete-committed | required before L2 | Main PC Codex |
| L2 LM Studio runner pacing enforcement | Enforce no-loaded-model, cooldown, failure recovery, and C: free-space gates from `_execution_pacing` | complete-committed | secondary lane carry | Main PC Codex |
| L2 llama.cpp primary backend runner | Direct `llama-server.exe` lifecycle, no-mmap/Vulkan/Q8KV profile, GPT-OSS parser override, LM Studio-compatible artifact surface | complete-committed | required before primary lane pilot and full matrix | Main PC Codex |
| L2 shortlist codification | Promote final primary/reference/exclusion decision into repo docs/config | in-working-tree | required before L3/L5 planning handoff | Main PC Codex |
| Normalizer adapter prototype | Runner-side only, eval scope, no EMR production write | pending | required before L3 | Main PC Codex |
| L0 inventory + L1 source verification | Refresh `lms ls`, loaded state, C: free space, source/model-card trust matrix | complete | safe first execution step | HP Z2 Codex |
| RA-03 user-owned checks | Final input/citation/user-verdict checks required before real endpoint | pending | hard blocker before L5 | User |
| Claude/read-only review | Review tracker updates, design R2, L0-L5 result packets | standby | after each result report | HP Z2 Claude |

## 4. GO Carry

| GO phrase | Scope | Expected artifact | STOP boundaries |
|---|---|---|---|
| `HP Z2 L0 inventory + L1 source verification GO` | Refresh HP Z2 model inventory, C: free space, loaded model state, and source trust/quant/size verification | L0/L1 result packet + §5 archive entry | no model performance matrix, no cleanup, no download unless separately approved |
| `Phase 2.1 design R1 -> R2 update GO` | Update design/eval docs with 4-lane mapping, scorer fix, acceptable citation set, model catalog, and C1-C7 hooks | design R2 diff/report | no heavy eval, no EMR write |
| `HP Z2 semantic-first runner build GO` | Implement eval-only runner support for semantic fields and v0.2 metric hooks | tools/config docs + dry-run evidence | no `/explain`, no EMR write |
| `Phase 2 L2 semantic runner commit/push GO` | Commit and push L2 semantic runner/config/docs/tracker updates | synced Main PC `origin/main` | no model execution, no `/explain`, no EMR write |
| `Phase 2 L2 runner pacing enforcement patch GO` | Enforce L2 runner `_execution_pacing`, free-space, no-loaded-model, and recovery gates | runner/config/runbook/tracker diff + validation | no model execution, no LM Studio API calls, no `/explain`, no EMR write |
| `HP Z2 L2 semantic smoke matrix GO` | Synthetic LM Studio-only semantic smoke over approved Tier models | L2 result packet + §5 archive entry | no real `/explain`; maintain C: >= 100 GB |
| `Codex handoff packet: repo-side llama.cpp 갱신 GO` | Add primary llama.cpp config/runner/docs and update tracker/AGENTS/ModelOps docs | repo diff + dry-run validation | no model execution, no `/explain`, no EMR write, no commit/push |
| `HP Z2 llama.cpp L2 primary_fast dry-run/pilot GO` | Pull reviewed runner on HP and run selected llama.cpp primary tier only | llama.cpp L2 result packet | no `/explain`; maintain C: >= 100 GB; stop on memory/process/API/citation gates |
| `shortlist codify GO` | Codify final L2 shortlist into AGENTS, llama.cpp config, tracker, runbook, and shortlist decision doc | repo diff + config dry-run validation | no model execution, no `/explain`, no EMR write, no cleanup/download; commit/push separate GO |
| `HP Z2 L3 normalizer feasibility GO` | Runner-side conversion of model output to `{summary, citations}` | L3 result packet + normalizer notes | no production normalizer change |
| `HP Z2 L4 native contract check GO` | Strict JSON/schema convenience check | L4 result packet | native contract does not override semantic gate |
| `Phase 2 heavy run GO` | L5 real `/explain` endpoint cells | Phase 2 result packet | requires separate explicit GO, RA-03 checks, and EMR read-only constraints |
| `Phase 2 ladder tracker commit + push GO` | Commit tracker changes | git commit/push | docs only unless explicitly broadened |

## 5. Result Archive

Append new result entries below. Keep old entries intact.

### L0 inventory

- Status: complete
- GO issued: `HP Z2 L0 inventory + L1 source verification GO`
- Reported: 2026-05-25
- Artifact: `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323`
- Key fields captured:
  - `lms ls` output path: `lms_ls.json`
  - loaded model state before/after: No Models Loaded / No Models Loaded
  - C: free space: 230.28 GiB, 100 GiB floor PASS
  - installed LLM count: 13
  - embedding count: 1
  - model root path: `C:\Users\test\.lmstudio\models`
  - final loaded models: No Models Loaded
- Reviewer verdict: accepted-for-design-R2
- Next GO: `HP Z2 semantic-first runner build GO`

### L1 source verification

- Status: complete
- GO issued: `HP Z2 L0 inventory + L1 source verification GO`
- Reported: 2026-05-25
- Artifact: `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323`
- Key fields captured:
  - source API status: all installed LLM/embedding repos OK
  - official LLM count: 4
  - high-trust Unsloth LLM count: 9
  - all resolved LLM folders <= 71 GiB: true
  - largest resolved folder: `openai/gpt-oss-120b` at 59.03 GiB
  - shared `qwen3.6-35b-a3b-mtp` repo folder: 58.74 GiB
  - cleanup/download/test: none
- Reviewer verdict: accepted-for-design-R2; not a cleanup approval
- Next GO: use model-axis catalog for semantic-first runner build and L2 candidate selection

### L2 semantic smoke matrix

- Status: blocked-by-pacing-enforcement-patch
- GO issued: `HP Z2 L2 semantic smoke matrix GO` reached preflight only; execution STOP before model load
- Artifact: -
- Required before entry:
  - L0/L1 reviewed: complete
  - design R2 updated: complete committed at `f3d0a9e`
  - semantic-first runner built or selected: complete committed at `56f772e`
  - Main PC dry-run validation: complete, no lms/model/API/app calls
  - HP Z2 pull/dry-run validation: complete
  - HP Z2 pre-execution review continuation: GO
  - HP Z2 execution attempt: STOP before model execution because pinned runner did not enforce `_execution_pacing`
- Reviewer verdict: pacing patch required before execution
- Next GO: `Phase 2 L2 runner pacing enforcement review GO`

### L2 llama.cpp primary full matrix and shortlist lock

- Status: complete-shortlist-locked
- GO issued: HP Z2 conditional overnight llama.cpp execution sequence
- Reported: 2026-05-27
- Integrated report: `C:\Github\hpz2-run-artifacts\results\hpz2_llamacpp_l2_integrated_report_20260527.md`
- Artifact repo commit: `80907506d07686e84df2cf6e9448b5c632a7dffd`
- Primary full matrix:
  - artifact: `C:\Github\hpz2-run-artifacts\results\llamacpp_phase2_l2_20260527_043835\`
  - 13 models x 4 cases
  - API ok: 52/52
  - citation core/strong: 52/52
  - semantic: 39/52
  - manual review: 13/52, all RA-05 expected wording baseline
- Bonus probes:
  - Granite 4.1 30B official IBM GGUF passed L2 probe and entered primary shortlist.
  - EXAONE 4.5 33B failed current llama.cpp `b9333` load probes; wait for upstream runtime support.
  - Aya Expanse 32B ran but failed practical citation/semantic usefulness.
  - K-EXAONE official IQ4_XS failed load; K-EXAONE Q2_K mradermacher is secondary-hold only.
- Shortlist lock:
  - primary: `hpz2-l2-qwen36-35b-a3b`, `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`, `hpz2-l2-qwen36-35b-a3b-mtp-q8`, `hpz2-l2-granite-41-30b-q4km`
  - reference: Qwen 122B variants, GPT-OSS 120B, Mistral Small 24B, Llama 70B, Gemma 31B
  - current primary exclusions: EXAONE 4.5, Aya Expanse, K-EXAONE official IQ4_XS, K-EXAONE Q2_K community fallback
- Availability carry: 2026-05-27 cleanup removed many previously tested local model folders, so config `model_path` entries require fresh file-existence and download preflight before future execution.
- Reviewer verdict: accepted-for-shortlist-codify
- Next GO: review + commit/push this codification, then decide L3 normalizer feasibility or L5 heavy-run planning.

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
| R1 | 2026-05-25 | Incorporated HP Z2 L0/L1 inventory and source verification results from `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323`; marked L0/L1 complete, corrected current HEAD snapshot, and set next GO to semantic-first runner build before L2. |
| R2 | 2026-05-25 | Added L2 synthetic semantic runner/config/runbook tracking. Main PC dry-run validation passed without lms commands, model loads, LM Studio API calls, production app calls, or EMR writes. L2 execution remains blocked until commit/push, HP Z2 pull/dry-run, and separate L2 semantic smoke matrix GO. |
| R3 | 2026-05-26 | Recorded HP Z2 pre-execution STOP before model load because pinned L2 runner did not enforce `_execution_pacing`; added working-tree pacing enforcement patch tracking. |
| R4 | 2026-05-26 | Locked llama.cpp as the primary HP Z2 backend lane with LM Studio as secondary evidence; added repo-side primary runner/config/docs tracking and next HP Z2 dry-run/pilot GO. |
| R5 | 2026-05-27 | Codified overnight llama.cpp L2 full matrix, Granite bonus probe, current primary shortlist, reference set, and current primary exclusions. |
