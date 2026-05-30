---
id: hpz2-phase2-ladder-progress-v0.1
project: local-llm-eval
type: progress-tracking
status: live
version: 0.1
created: 2026-05-25
updated: 2026-05-30
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
| Current level | L0/L1 complete / llama.cpp primary lane locked / L2 full matrix / shortlist locked / L5 shim implemented / Step 3 + shutdown / shim review PASS / H1 RA-03 PASS / schema probe PASS / json_schema mode committed / H2 A/B plan frozen / **H2 A/B 8-cell executed (8/8 PASS, no structural drift)** / **schema mode decided = json_object (Rule 2)** |
| Current repo HEAD | `08a94af` (`docs(rag): freeze H2 schema mode A/B plan`) committed+pushed+HP-pulled; **H2 A/B result-sync (R14) doc changes are working tree** until separate commit/push GO |
| Current tracker status | H2 A/B 8-cell complete (Qwen 35B A3B official + Granite 4.1 30B x `json_object` + `json_schema`); **Rule 2 -> H2 = `json_object` + strict-schema conformance metric/caveat**; discrimination null (RA-05 did not drift in either mode -> json_schema enforcement undemonstrated, not disproven); HP runtime shut down; broader L5 still blocked |
| Next recommended GO | this H2 result-sync `commit + push GO` + HP pull, then **H2 model-comparison planning** (`json_object` fixed, strict-schema conformance metric live as a tripwire) |
| L2 blocker | none for synthetic L2 evidence; current primary shortlist is locked |
| L3 blocker | user GO + runner-side normalizer feasibility prototype over locked primary shortlist |
| L5 hard blocker | H1 PASS + shutdown + schema probe + R12 + R13 plan + H2 A/B 8-cell + schema mode decided (`json_object`) do not authorize broader L5; remaining blockers are RA-03 user-owned final checks, sufficient L2-L4 evidence, and explicit `Phase 2 heavy run GO` |
| Disk hard floor | `C:` free space >= 100 GB |
| Runtime lane | llama.cpp primary / LM Studio secondary; L5 shim provides local Ollama-compatible adapter only |

## 2. Ladder Status Snapshot

| Level | Status | GO issued | Result reported | Artifact path | Reviewer verdict | Next |
|---|---|---|---|---|---|---|
| L0 inventory | complete | 2026-05-25 | 2026-05-25 | `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323` | accepted-for-design-R2 | complete |
| L1 source verification | complete | 2026-05-25 | 2026-05-25 | `C:\github\hpz2-run-artifacts\results\l0_l1_inventory_20260525_202323` | accepted-for-design-R2 | use source matrix for model-axis catalog |
| L2 semantic smoke | complete-shortlist-locked | 2026-05-26/27 | LM Studio L2 completed as secondary; llama.cpp full matrix and bonus probes completed; shortlist locked | `C:\Github\hpz2-run-artifacts\results\hpz2_llamacpp_l2_integrated_report_20260527.md` | accepted-for-shortlist-codify | repo review + commit/push; then L3 or L5 planning decision |
| L3 normalizer feasibility | blocked | - | - | - | - | requires L2 results + runner-side normalizer prototype |
| L4 native contract check | blocked | - | - | - | - | requires L2/L3 review and explicit L4 GO |
| L5 shim adapter | implemented-reviewed-h1-pass-schema-probe-jsonschema-committed-hp-pulled | 2026-05-28 | 2026-05-30 | `21c6379` original shim / `dd646db` R12 json_schema mode / `docs/hpz2-l5-ollama-shim-design-2026-05-28.md` | PASS for H1 plumbing; schema probe PASS; R12 unit tests PASS; HP pull/verify PASS | H2 A/B plan review and later execution GO |
| L5 real endpoint | h1-pass-shutdown-schema-probe-jsonschema-h2ab-8cell-pass-mode-json_object-broader-blocked | 2026-05-30/31 | 2026-05-31 | PHI-safe H1 + H2 A/B metadata packets; no raw response text; shutdown packets; schema probe packet; R12 commit; R13 plan doc; R14 result doc | H1 one-case PASS + probe PASS + H2 A/B 8/8 PASS (no structural drift) + **schema mode decided = json_object (Rule 2)** | no additional cases/matrix without separate GO; broader L5 requires RA-03 checks, sufficient L2-L4 evidence, and `Phase 2 heavy run GO` (schema mode now fixed) |

## 3. Parallel Track Status

| Track | Scope | Status | Ladder dependency | Owner |
|---|---|---|---|---|
| Phase 2.1 design R1 -> R2 update | 4-lane mapping, scorer P7 placeholder rejection fix, acceptable citation set, model-axis catalog, C1-C7 hooks | complete-committed | required before L2 | Main PC Codex |
| Stage A-R lane reinterpretation | Reclassify existing Stage A-R / ModelOps results under 4 lanes and L0-L5 ladder | pending | useful before L2 comparisons | Main PC Codex |
| Semantic-first runner build | Add or adapt local-llm-eval runner for semantic fields and v0.2 metric hooks | complete-committed | required before L2 | Main PC Codex |
| L2 LM Studio runner pacing enforcement | Enforce no-loaded-model, cooldown, failure recovery, and C: free-space gates from `_execution_pacing` | complete-committed | secondary lane carry | Main PC Codex |
| L2 llama.cpp primary backend runner | Direct `llama-server.exe` lifecycle, no-mmap/Vulkan/Q8KV profile, GPT-OSS parser override, LM Studio-compatible artifact surface | complete-committed | required before primary lane pilot and full matrix | Main PC Codex |
| L2 shortlist codification | Promote final primary/reference/exclusion decision into repo docs/config | complete-committed | required before L3/L5 planning handoff | Main PC Codex |
| Normalizer adapter prototype | Runner-side only, eval scope, no EMR production write | pending | required before L3 | Main PC Codex |
| L5 Ollama-compatible shim adapter | Translate local Ollama `/api/generate` to llama.cpp `/v1/chat/completions` without EMR code changes | complete-reviewed | required before H1 smoke | Main PC Codex |
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
| `HP Z2 shim Step 3 loopback health preflight GO` | Verify HP repo state, ensure no stale server process, start one loopback llama.cpp server, start loopback shim, and check shim `/health` | Step 3 health preflight packet | no `/explain`, no EMR write, no settings file write, no model matrix, no cleanup/download |
| `H1 minimal /explain smoke plan GO` | Plan a one-case H1 smoke with preflight, env override, JSON validity check, logging/PHI guard, and shutdown boundary | H1 plan packet | plan only; no `/explain`, no EMR write, no settings file write, no model matrix |
| `HP EMR baseline refresh GO` | Refresh HP `C:\Github\EMR_AI_24clinic` to known origin state and report clean HEAD | HP EMR baseline packet | no `/explain`, no llama-server, no shim, no file edits, no commit/push |
| `HP local-llm-eval R8 pull/verify GO` | Pull latest `local-llm-eval` docs after R8 commit/push and report clean HEAD | HP local-llm-eval sync packet | no model execution, no `/explain`, no EMR write |
| `HP local-llm-eval R9 pull/verify GO` | Pull repo doc R9 `304836e` or newer on HP after H1 shutdown and report clean HEAD | HP local-llm-eval sync packet | no model execution, no `/explain`, no EMR write, no commit/push |
| `H1 minimal /explain smoke execution GO (RA-03 only)` | Execute exactly one RA-03 `/explain` smoke through the reviewed H1 harness and then teardown | H1 one-case result packet | no second case, no `scripts/smoke_test_explain.py`, no settings file write, no EMR repo write, stop after first failure |
| `Main PC tunneled H1 RA-03 execution GO` | Execute the H1 harness from Main PC through an SSH tunnel to HP loopback shim | H1 one-case result packet | one request only; close tunnel after request; no EMR file write; no second case; no matrix |
| `schema fidelity capability probe GO` | Probe llama.cpp b9333 structured-output support with synthetic non-PHI direct `/v1/chat/completions` requests | schema capability packet | no `/explain`, no shim `/api/generate`, no EMR write, no matrix, shutdown after probe |
| `shim json_schema mode implementation GO` | Add/test/document a shim mode that forwards EMR strict `format` schema to llama.cpp OpenAI-style `json_schema` | repo diff + tests + docs | no `/explain`, no model execution, no EMR write; commit/push separate unless explicitly bundled |
| `H2 A/B execution plan freeze GO` | Freeze the limited schema-mode A/B plan and decision rules before any multi-call `/explain` work | plan doc + tracker/relay sync | docs only; no `/explain`, no HP runtime start, no EMR write, no model/matrix/cleanup/download; commit/push separate |
| `H2 A/B execution GO (4-cell minimal)` | Run RA-03 and RA-05 across `json_object` and `json_schema` on Qwen 35B A3B official | PHI-safe 4-cell A/B result packet | requires reviewed/committed plan and HP pull; no Granite expansion, raw response relay, EMR write, settings write, cleanup/download, or second model |
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
  - H1 minimal `/explain` smoke plan/result reviewed
  - RA-03 user-owned checks complete
  - sufficient L2-L4 evidence
  - explicit `Phase 2 heavy run GO`
  - EMR_AI_24clinic read-only constraints reconfirmed
- Reviewer verdict: -
- Next GO: pending

### H1 minimal `/explain` smoke plan

- Status: planned in R8; executed and passed in R9 as a one-case tunneled RA-03
  smoke
- Plan GO interpreted as: plan only, no `/explain`
- Reported HP read-only state before R8:
  - HP hostname: `hpcheck`
  - HP `local-llm-eval`: clean, `21c6379...`
  - HP `EMR_AI_24clinic`: clean, `ef6e40f...`
  - ports `127.0.0.1:18080` and `127.0.0.1:18081`: free
  - `218bf51f` was not resolvable on HP
- Main PC verification:
  - `EMR_AI_24clinic` has `218bf51f0af66907333aa9c619ac2a0f732eb6d1`
    and latest observed `543e1f9ef5a0e4fcb49c47e4a55b0e5e661a6944`.
  - `ef6e40f..543e1f9` has no changes under `app`, `scripts`, or
    `rag_index`.
  - Verdict: functionally low risk for `/explain`, but audit drift remains.
    Refresh HP EMR before H1 execution.
- R8 plan decisions:
  - Preferred topology: split execution through SSH tunnel. HP runs
    `llama-server` and shim; reviewed EMR harness calls `127.0.0.1:18081`.
  - All-on-HP is allowed only after HP refreshes repos and reports clean HEADs.
  - `scripts/smoke_test_explain.py` is not allowed for H1 minimal because it
    runs more than one case and writes markdown artifacts.
  - Use one in-memory `TestClient` or equivalent direct harness call for RA-03
    only, with env override and no `data/llm_settings.json` write.
- Completed before execution:
  - HP EMR baseline refreshed and reported clean at `543e1f9`.
  - HP `local-llm-eval` pulled R8 and reported clean at `0f2da81`.
  - HP runtime started loopback-only with `llama-server` health ok and shim
    `/health` status ok with `upstream.status=ok`.
  - Main PC EMR `.venv` was used because HP Python lacked `fastapi` and
    `pydantic`.
  - Explicit tunneled H1 execution GO was issued.

### H1 minimal `/explain` RA-03 smoke result

- Status: PASS, one-case endpoint-readiness signal only
- Execution topology:
  - Main PC EMR `.venv` harness
  - SSH tunnel on Main PC `127.0.0.1:18081`
  - HP Z2 loopback shim `127.0.0.1:18081`
  - HP Z2 loopback `llama-server` `127.0.0.1:18080`
- Successful SSH target: `test@192.168.68.50`; `hpcheck` alias had host-key
  verification drift and should not be assumed for the next run.
- Scope controls:
  - exactly one RA-03 `/explain` request
  - RA-03 values: `sme + trimesy + lacto2`, `dx=a090`, `age=1`
  - env override only; no `data/llm_settings.json` write
  - no EMR repo edits, no `scripts/smoke_test_explain.py`, no second request
- PHI-safe result metadata:
  - HTTP status `200`
  - EMR status `ok`
  - raw LLM text valid JSON: yes
  - JSON has `summary` and `citations`: yes
  - citation verifier: pass
  - PHI hit count: `0`
  - retrieved chunks: `5`
  - citation count: `2`
  - latency: `17554 ms`
  - wall time: `17565 ms`
  - `llm_generate_call_count`: `1`
  - `/api/generate` reached: yes
  - both repos remained clean
  - Main PC tunnel listener closed after request
- Carry:
  - H1 confirms plumbing, model-name mapping, JSON validity, citation verifier,
    and PHI-zero behavior for one RA-03 request.
  - H1 does not prove model quality and does not authorize additional cases,
    matrix execution, EMR writes, cleanup/download, or `Phase 2 heavy run GO`.
  - H2+ quality conclusions require a fixed structured-output mode. R12 added
    committed `json_schema` forwarding support, but the selected H2 mode must
    still be decided from a limited A/B rather than inferred from H1.
  - R9 result sync still needed a separate HP runtime shutdown report.

### H1 tunneled runtime shutdown

- Status: DONE
- Reported: 2026-05-30
- Shutdown evidence:
  - shim PID `24380`: validated and stopped
  - `llama-server` PID `55796`: validated and stopped
  - `127.0.0.1:18080`: no listener
  - `127.0.0.1:18081`: no listener
- Final HP repo status:
  - `EMR_AI_24clinic`: clean at `543e1f9 feat(case-review): add core6 rule engine`
  - `local-llm-eval`: clean at `0f2da81 docs(rag): pin H1 smoke plan baselines`
- Boundaries confirmed: no `/explain`, no `/api/generate`, no edits, no matrix,
  no cleanup/download, no commit, and no push.
- Carry:
  - H1 runtime shutdown is closed.
  - HP `local-llm-eval` remains at R8 (`0f2da81`); before the next HP task that
    depends on repo docs, pull/verify R9 (`304836e`) or newer.

### Schema fidelity capability probe

- Status: PASS for minimal capability, not full clinical prompt proof
- Reported: 2026-05-30
- Runtime scope:
  - HP Z2 narrow runtime probe
  - model `hpz2-l2-qwen36-35b-a3b`
  - direct `llama-server` `/v1/chat/completions` only
  - no shim, no EMR `/explain`, no `/api/generate`, no matrix
  - synthetic non-PHI prompt
- Results:
  - `response_format {"type":"json_object"}`: HTTP `200`, accepted, valid JSON,
    strict `{summary: string, citations: string[]}` schema match, no server
    error, latency `483.7 ms`.
  - OpenAI-style `response_format {"type":"json_schema","json_schema":...}`:
    HTTP `200`, accepted, valid JSON, strict schema match, no server error,
    latency `434.2 ms`.
- Shutdown:
  - `llama-server` PID `62200` stopped successfully.
  - `127.0.0.1:18080`: no listener after shutdown.
  - HP `local-llm-eval`: clean at `66733a8`.
- Interpretation:
  - llama.cpp `b9333` can accept both tested structured-output request shapes in
    a minimal case.
  - This supports implementing a shim mode that forwards EMR strict `format`
    schema as llama.cpp OpenAI-style `json_schema`.
  - It does not prove behavior across longer clinical prompts or H2+ model
    comparisons.
- Next GO: R12 implementation is committed/pushed/HP-pulled; H2 A/B plan review
  is next before any multi-case execution.

### Shim json_schema mode implementation

- Status: implemented, reviewed, committed, pushed, and HP-pulled.
- GO issued: `shim json_schema mode implementation GO`
- Reported: 2026-05-30
- Commit: `dd646db596aa4a44b3272223973961181d5a4dbc`
  (`feat(rag): add shim json_schema response mode`)
- Files changed:
  - `tools/hpz2_ollama_compat_llamacpp_shim.py`
  - `tests/test_hpz2_ollama_compat_llamacpp_shim.py`
  - `docs/hpz2-l5-ollama-shim-design-2026-05-28.md`
  - `docs/hpz2-phase2-ladder-progress-v0.1.md`
  - `AGENTS.md`
- Behavior:
  - CLI now accepts `--schema-mode json-schema`.
  - Default remains `--schema-mode json-object`.
  - In `json-schema` mode, incoming EMR/Ollama `format` is wrapped as the
    R11-verified nested OpenAI-style shape:
    `response_format: {"type":"json_schema","json_schema":{"name":"explain_response","strict":true,"schema":...}}`.
  - Missing, empty, or non-object `format` in `json-schema` mode returns HTTP
    400 before upstream.
  - `--schema-mode none` omits `response_format`.
- Validation:
  - `python -m py_compile tools\hpz2_ollama_compat_llamacpp_shim.py tests\test_hpz2_ollama_compat_llamacpp_shim.py`
    passed.
  - `python -m unittest tests.test_hpz2_ollama_compat_llamacpp_shim` passed:
    9 tests.
  - HP artifact shape comparison found the first flat working-tree draft did
    not match R11; R12 was corrected to the nested wrapper before commit/push.
  - Claude re-review PASS after nested wrapper correction.
  - HP pull/verify completed: `66733a8..dd646db` fast-forward, clean, HEAD
    equals `origin/main`.
- Boundary:
  - No `/explain`, no HP runtime start, no shim call against HP runtime, no
    model matrix, no EMR write, no cleanup/download were performed during the
    R12 implementation/review/commit/pull chain.
- Next GO: R13 plan freeze is in working tree; plan review and commit/push are
  next before any multi-case `/explain` work.

### H2 schema-mode A/B execution plan freeze

- Status: frozen plan in working tree; commit/push not authorized by this GO.
- GO issued: `H2 A/B execution plan freeze GO`
- Reported: 2026-05-30
- Plan doc: `docs/h2-schema-mode-ab-plan-2026-05-30.md`
- Minimal matrix:
  - `RA-03-safety-boundary` x `json_object` x `hpz2-l2-qwen36-35b-a3b`
  - `RA-03-safety-boundary` x `json_schema` x `hpz2-l2-qwen36-35b-a3b`
  - `RA-05-rule-kb-nuance-conflict` x `json_object` x
    `hpz2-l2-qwen36-35b-a3b`
  - `RA-05-rule-kb-nuance-conflict` x `json_schema` x
    `hpz2-l2-qwen36-35b-a3b`
- Case locks:
  - RA-03 remains `sme + trimesy + lacto2`, `dx=a090`, pediatric `age=1`.
  - RA-05 is `dx=a09`, `orders=tamiiv`, pediatric `age=11`; use it only for
    structure/schema-enforcement measurement, not final content-quality verdict.
- Optional expansion:
  - Add `hpz2-l2-granite-41-30b-q4km` only with separate explicit approval.
- Pre-registered decision rules:
  - RA-05 `json_schema` conforming while `json_object` drifts selects
    `json_schema` for H2.
  - No meaningful structural difference selects `json_object` for H2 plus a
    strict-schema conformance metric/caveat.
- Safety envelope:
  - SSH tunnel/loopback only, env override only, no `data/llm_settings.json`
    write, PHI hit count `0` hard gate, shutdown/ports-closed verification,
    and PHI-safe metadata only.
- Boundary:
  - No `/explain`, no llama-server/shim start, no model execution, no matrix,
    no EMR write, no cleanup/download, no commit, and no push were authorized or
    performed by this plan freeze.
- Next GO: `H2 A/B execution plan review GO`, then commit/push + HP
  pull/verify, then `H2 A/B execution GO (4-cell minimal)`.

### L5 Ollama-compatible shim adapter

- Status: implemented-reviewed-r12-jsonschema-committed-hp-pulled
- GO issued: shim implementation gate
- Reported: 2026-05-28; Step 3/review updated 2026-05-30
- Commit: `21c6379e0fbb8c54d6932de0ee22a1b7a86277c8`
- Files:
  - `tools/hpz2_ollama_compat_llamacpp_shim.py`
  - `tests/test_hpz2_ollama_compat_llamacpp_shim.py`
  - `docs/hpz2-l5-ollama-shim-design-2026-05-28.md`
- Scope:
  - local loopback adapter from Ollama `/api/generate` to llama.cpp `/v1/chat/completions`
  - no EMR code changes
  - no `/explain`
  - no model execution authorized by the commit
- Step 3 health preflight:
  - HP hostname `HPCHECK`
  - local-llm-eval `21c6379` clean on HP
  - selected model file exists
  - llama-server `127.0.0.1:18080` health ok
  - shim `127.0.0.1:18081` health ok and upstream ok
  - stopped at `/health`
  - shutdown confirmed no shim/llama-server process and no `18080`/`18081` listeners
- Reviewer verdict: PASS / CONDITIONAL GO for H1
- Review carry:
  - EMR `ollama_client.py` sends `/api/generate` and reads only `response`; shim contract matches.
  - H1 confirmed valid JSON and model-name mapping for one RA-03 request.
  - R12 adds an optional `json_schema` forwarding mode, but default remains
    `json_object`; H2+ must still use one fixed documented mode.
- H1 result: one-case tunneled RA-03 `/explain` PASS recorded in R9.
- H1 runtime shutdown: confirmed in R10.
- Schema fidelity capability probe: PASS in R11 for minimal direct
  `json_object` and `json_schema` support.
- Next GO: `H2 A/B execution plan review GO`, then commit/push and HP
  pull/verify before small A/B execution.

## 6. STOP Carry

- No heavy eval without explicit GO.
- No real `/explain` without explicit `Phase 2 heavy run GO`.
- No shim Step 3 health preflight without explicit Step 3 GO.
- No H1 `/explain` smoke from shim health success alone.
- No H1 `/explain` smoke from shim review PASS alone; H1 needs a plan GO and a
  separate execution GO.
- No H1 minimal smoke through `scripts/smoke_test_explain.py` without broader
  explicit GO; H1 is one RA-03 request only.
- No additional `/explain` cases, Phase 2 heavy run, matrix execution, EMR
  writes, cleanup, or downloads from H1 RA-03 PASS alone.
- No H2+ quality conclusion from schema capability probe or R12 implementation
  alone; one fixed structured-output mode must be selected from a reviewed plan
  and explicit execution/result gate.
- No H2 A/B execution, HP runtime start, or `/explain` call from the R13 plan
  freeze alone.
- No RA-05 final content-quality verdict until user-owned expected-summary and
  clinical-input checks are complete; RA-05 is structure/schema-enforcement
  evidence only in the frozen A/B plan.
- No Granite / 8-cell H2 A/B expansion without separate explicit approval.
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
| R6 | 2026-05-30 | Synced tracker to shim implementation commit `21c6379`, marked shortlist codification complete-committed, added L5 shim adapter status, and set next narrow runtime gate to `HP Z2 shim Step 3 loopback health preflight GO`. |
| R7 | 2026-05-30 | Synced tracker after HP Step 3 health preflight/shutdown and Claude shim review PASS. Next gate is H1 minimal `/explain` smoke planning, not execution. |
| R8 | 2026-05-30 | Corrected H1 audit pins, separated current repo/doc baseline from shim implementation commit, recorded HP EMR baseline drift, narrowed H1 to one RA-03 harness call, and added HP repo refresh gates before execution. |
| R9 | 2026-05-30 | Recorded tunneled H1 RA-03 one-case `/explain` PASS: HTTP 200, EMR `ok`, valid JSON, citation verifier pass, PHI hits `0`, one request only, repos clean, and broader L5 still blocked without separate GO. |
| R10 | 2026-05-30 | Recorded HP H1 runtime shutdown: shim PID `24380` and `llama-server` PID `55796` stopped, ports `18080`/`18081` no listener, HP repos clean, and HP `local-llm-eval` still needs R9 pull before next doc-dependent work. |
| R11 | 2026-05-30 | Recorded schema fidelity capability probe: llama.cpp `b9333` accepted both `json_object` and OpenAI-style `json_schema` response formats in a minimal direct synthetic probe; next gate is shim `json_schema` forwarding implementation, not H2/heavy run. |
| R12 | 2026-05-30 | Implemented optional shim `--schema-mode json-schema` forwarding mode, added fail-closed validation and unit coverage, and kept default `json-object`; initially working tree until later R12 closeout. |
| R12-correction | 2026-05-30 | Corrected the initial flat `json_schema` draft to the R11-verified nested OpenAI-style wrapper after HP shape comparison reported MISMATCH. |
| R12-closeout | 2026-05-30 | Recorded R12 commit/push/HP pull completion at `dd646db`; nested `json_schema` mode is available but still requires a fixed H2 mode decision before broader comparisons. |
| R13 | 2026-05-30 | Froze H2 schema-mode A/B execution plan: RA-03 + RA-05 crossed with `json_object` + `json_schema` on Qwen 35B A3B official, with RA-05 limited to structure/schema-enforcement measurement and Granite expansion requiring separate approval. |
