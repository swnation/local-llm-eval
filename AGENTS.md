# local-llm-eval Agent Entry Rules

## Session Entry Order

For any new session in `C:\Github\local-llm-eval`, read these first:

1. `PROJECT_CONTEXT.md`
2. `docs/rag_aware_eval_design_r0.md`
3. `prompts/rag_aware_eval_set_v0.1.json`
4. `git status --branch --short`

Treat repo-local files as the source of truth. Memory is supporting context only.

## Current Project Goal

The active goal is RAG-aware Phase 2 evaluation planning for `EMR_AI_24clinic` `/explain`.

Current planning artifacts:

- `docs/rag_aware_eval_design_r0.md` = Phase 2.1 design R1 frozen baseline, with R2 pre-L2 semantic-first update
- `prompts/rag_aware_eval_set_v0.1.json` = eval set spec v0.2.1, 17 cases; RA-06/RA-07 added, RA-08 removed
- `docs/h2-schema-mode-ab-plan-2026-05-30.md` = R13/R14 schema-mode A/B plan/result; H2 schema mode fixed to `json_object` plus strict-schema conformance metric/caveat
- `docs/h2-model-comparison-plan-2026-05-31.md` = R15 H2 model-comparison plan freeze: Primary 4 x 17-case eval set, `json_object` fixed, 64 model-call cells, execution still gated
- `models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json` = Phase 2 Stage A LM Studio config R0.2 (includes all HP Z2 LM Studio smoke-pass models + execution pacing)
- `models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json` = L2 synthetic semantic smoke config over HP Z2 L0/L1 model catalog
- `models_config_hpz2_llamacpp_phase2_l2_v0.1.json` = primary HP Z2 llama.cpp L2 synthetic semantic config after backend lane decision lock (2026-05-26); LM Studio L2 remains secondary/historical

Phase 2 heavy run remains blocked until:

- HP Z2 setup is complete
- The user explicitly issues `Phase 2 heavy run GO`

RA-03 is resolved as `sme + trimesy + lacto2`, `dx=a090`, pediatric `age=1`; expected citations are verified in current RAG chunks. Do not change those values without explicit user instruction.

## Current Runner Baseline

Phase 2 model viability baselines should now be measured on the official HP Z2 runner. Backend lane lock (2026-05-26): llama.cpp is primary for HP Z2 L2/L3 candidate evaluation; LM Studio remains secondary for manual inspection, model management, and historical comparison.

- Execution host: HP Z2 Mini G1a
- Primary backend lane: llama.cpp `llama-server.exe`
- Primary runtime: llama.cpp Vulkan on `Vulkan0`
- Primary config: `models_config_hpz2_llamacpp_phase2_l2_v0.1.json`
- Primary runner: `tools/hpz2_llamacpp_phase2_l2_runner.py`
- Primary runbook: `docs/hpz2-llamacpp-phase2-l2-runner-2026-05-26.md`
- Backend decision note: `docs/hpz2-phase2-backend-lane-decision-2026-05-26.md`
- Primary load profile: `--no-mmap --no-host --kv-offload --op-offload -fa on -ctk q8_0 -ctv q8_0 -b 1024 -ub 256 --reasoning off`; add `--skip-chat-parsing` for GPT-OSS GGUF models.
- Secondary backend lane: LM Studio / llama.cpp Vulkan
- Secondary load profile: `--gpu max --context-length 4096 --ttl 120`
- Smoke config: `models_config_hpz2_lmstudio_smoke_v0.1.json`
- Smoke prompt: `prompts/hpz2_lmstudio_smoke_v0.1.json`
- Runbook: `docs/hpz2-lmstudio-official-smoke-baseline-2026-05-24.md`
- Phase 2 Stage A config: `models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json`
- Phase 2 Stage A runner: `tools/hpz2_lmstudio_phase2_stage_a_runner.py`
- Phase 2 Stage A config note: `docs/hpz2-lmstudio-phase2-stage-a-config-2026-05-24.md`
- Phase 2 Stage A-R model-aware config: `models_config_hpz2_lmstudio_phase2_stage_ar_v0.1.json`
- Phase 2 Stage A-R note: `docs/hpz2-lmstudio-phase2-stage-ar-model-aware-2026-05-24.md`
- Phase 2 L2 semantic config: `models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json`
- Phase 2 L2 semantic runner: `tools/hpz2_lmstudio_phase2_l2_semantic_runner.py`
- Phase 2 L2 semantic runbook: `docs/hpz2-lmstudio-phase2-l2-semantic-runner-2026-05-25.md`
- LM Studio L2 semantic lane: secondary/historical comparison only after the llama.cpp primary lane lock. Keep these files; do not delete or reinterpret them as failed.
- Phase 2 Stage A pacing: unload before/after each model, confirm `lms status` has no loaded models, wait 90s after unload, wait 180s after large models or failures.
- Phase 2 Stage A-R load profile: `--gpu max --context-length 32768 --ttl 3600 -y` on HP Z2. Stage A strict baseline remains `4096`.
- Stage A-R does not replace the Stage A strict endpoint baseline; use it only to test model-aware profiles such as Qwen `/no_think`, gpt-oss reasoning hints, Granite RAG/extraction settings, Gemma sampling, and LM Studio JSON schema output.
- L2 semantic smoke does not use the real endpoint. Its dry-run is config/spec validation only. Actual HP Z2 model execution requires a separate HP execution GO for the selected backend.

The main PC remains the canonical workspace for review, documentation, commit, and push. HP Z2 is execution-only unless the user explicitly changes that rule.

Earlier 5080, subpc, Ollama, or manual one-off results are exploratory only and must not be mixed into the official HP Z2 LM Studio/Vulkan speed baseline.

## Phase 2 L2 Shortlist Lock

Shortlist lock date: 2026-05-27. Evidence is captured in
`C:\Github\hpz2-run-artifacts\results\hpz2_llamacpp_l2_integrated_report_20260527.md`
at artifact repo commit `80907506d07686e84df2cf6e9448b5c632a7dffd`.

Primary candidates for the next Phase 2 decision surface:

- `hpz2-l2-qwen36-35b-a3b`
- `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`
- `hpz2-l2-qwen36-35b-a3b-mtp-q8`
- `hpz2-l2-granite-41-30b-q4km`

Reference/historical candidates remain useful for comparison, but are not the
first-pass default: Qwen 122B A10B variants, GPT-OSS 120B, Mistral Small 24B,
Llama 70B, and Gemma 31B.

Do not promote these to the current primary shortlist without a separate review
and user GO: EXAONE 4.5 33B under current llama.cpp `b9333`, Aya Expanse 32B,
K-EXAONE 236B official IQ4_XS, or K-EXAONE 236B Q2_K mradermacher community
fallback. The Q2_K K-EXAONE result is secondary viability evidence only.

After the 2026-05-27 cleanup, config `model_path` values are expected canonical
locations, not proof that files are still installed on HP. Future execution
requires a fresh file-existence, disk, and download preflight.

This shortlist lock does not authorize L3, L4, L5, `/explain`, EMR writes,
cleanup, downloads, model execution, commit, or push.

## Current L5 Shim Baseline

The HP Z2 Ollama-compatible llama.cpp shim is implemented and committed on the
main PC at `21c6379e0fbb8c54d6932de0ee22a1b7a86277c8`
(`feat(rag): add HP Z2 ollama llama.cpp shim`).

- Shim: `tools/hpz2_ollama_compat_llamacpp_shim.py`
- Tests: `tests/test_hpz2_ollama_compat_llamacpp_shim.py`
- Runbook: `docs/hpz2-l5-ollama-shim-design-2026-05-28.md`
- Purpose: keep `EMR_AI_24clinic` unchanged by translating local Ollama
  `POST /api/generate` calls to llama.cpp `POST /v1/chat/completions`.
- Safety posture: loopback-only bind/upstream, `stream=true` rejected, request
  size bounded, prompt/system/response bodies not logged.
- Step 3 loopback health preflight: DONE on HP Z2, then shutdown confirmed
  (`llama-server` and shim stopped; ports `18080` and `18081` not listening).
- Shim review: PASS / CONDITIONAL GO for H1. EMR sends Ollama
  `POST /api/generate` and reads only the `response` field; the shim contract
  matches. H1 later confirmed valid JSON and model-name mapping for one RA-03
  request. R12 adds committed `--schema-mode json-schema` support that forwards
  the EMR `format` schema to llama.cpp in the R11-verified nested OpenAI-style
  wrapper. H2+ quality comparisons still require one fixed documented schema
  mode before comparing models.

This shim status by itself does not authorize broader L5, additional
`/explain` calls, or H2/H3/H4 work; each later execution gate requires a
separate explicit GO.

R8 H1 plan correction (2026-05-30):

- Current repo/doc baseline at R8 entry is `3000ceb`
  (`docs(rag): sync shim step3 review status`). Do not use `21c6379` as the
  current repo HEAD; `21c6379` is the shim implementation commit only.
- Preferred H1 topology is split execution: HP Z2 runs `llama-server` and the
  loopback shim; the reviewed EMR `/explain` harness reaches the shim through
  `127.0.0.1:18081` via SSH tunnel. All-on-HP is acceptable only after the HP
  EMR checkout is refreshed and pinned.
- Main PC verified `EMR_AI_24clinic` commits `218bf51f` and current
  `543e1f9`; HP reported `ef6e40f` and could not resolve `218bf51f`.
  Diff inspection showed no `/explain`-relevant path changes under `app`,
  `scripts`, or `rag_index` from `ef6e40f` to `543e1f9`, but this is still an
  audit drift. Refresh HP `EMR_AI_24clinic` before H1 execution unless the user
  explicitly accepts the older baseline.
- H1 minimal execution, if later approved, is RA-03 only, uses env override
  only, must not use `scripts/smoke_test_explain.py`, and must include JSON
  validity, citation verifier, PHI-zero, repo-dirty, and teardown checks.

R9 H1 RA-03 result sync (2026-05-30):

- H1 tunneled one-case smoke PASS was reported through the split topology:
  Main PC EMR `.venv` harness -> SSH tunnel `127.0.0.1:18081` ->
  HP Z2 loopback shim -> HP Z2 loopback `llama-server`.
- Audit pins at execution: Main PC `EMR_AI_24clinic` `543e1f9`, Main PC
  `local-llm-eval` `0f2da81`, HP `EMR_AI_24clinic` `543e1f9`, HP
  `local-llm-eval` `0f2da81`.
- Harness scope: exactly one RA-03 `/explain` request, env override only,
  no `data/llm_settings.json` write, no EMR repo edits, no
  `scripts/smoke_test_explain.py`.
- PHI-safe result metadata: HTTP 200, EMR status `ok`, raw LLM text valid JSON,
  JSON has `summary` and `citations`, citation verifier passed, PHI hit count
  `0`, retrieved chunks `5`, citation count `2`, latency `17554 ms`, wall time
  `17565 ms`, both repos remained clean.
- SSH tunnel note: `hpcheck` alias hit host-key verification drift; the
  successful path used `test@192.168.68.50`.
- Carry: this H1 PASS is a plumbing/readiness signal only. It does not authorize
  Phase 2 heavy run, additional cases, matrix execution, EMR writes, cleanup,
  downloads, or H2+ quality conclusions. R12 adds a `json_schema` forwarding
  mode, but H2+ quality comparisons must still select one fixed schema mode
  through a reviewed A/B gate.
- Runtime carry at R9 entry: shutdown was still awaiting separate HP report.

R10 H1 runtime shutdown sync (2026-05-30):

- HP confirmed tunneled H1 runtime shutdown: shim PID `24380` validated and
  stopped; `llama-server` PID `55796` validated and stopped; ports
  `127.0.0.1:18080` and `127.0.0.1:18081` have no listener.
- HP final repo status after shutdown: `EMR_AI_24clinic` clean at `543e1f9`;
  `local-llm-eval` clean at `0f2da81`.
- Carry: HP `local-llm-eval` has not yet pulled repo doc R9 commit `304836e`.
  Before the next HP work that depends on repo docs, pull/verify latest
  `origin/main`.

R11 schema fidelity capability probe sync (2026-05-30):

- HP ran a narrow direct `llama-server` `/v1/chat/completions` probe on
  `hpz2-l2-qwen36-35b-a3b` without shim or EMR `/explain`.
- llama.cpp `b9333` accepted `response_format: {"type":"json_object"}`:
  HTTP 200, valid JSON, strict `{summary: string, citations: string[]}` schema
  match, no server error, latency `483.7 ms`.
- llama.cpp `b9333` accepted OpenAI-style `response_format:
  {"type":"json_schema", "json_schema": ...}` with an EXPLAIN-like schema:
  HTTP 200, valid JSON, strict schema match, no server error, latency
  `434.2 ms`.
- Runtime shutdown confirmed after probe: `llama-server` PID `62200` stopped and
  `127.0.0.1:18080` had no listener.
- Limitation: this was a minimal synthetic non-PHI capability probe, not proof
  across longer clinical prompts.
- Next recommended gate: `shim json_schema mode implementation GO` before H2+
  quality conclusions.

R12 shim json_schema mode implementation (2026-05-30):

- Committed implementation `dd646db596aa4a44b3272223973961181d5a4dbc`
  (`feat(rag): add shim json_schema response mode`) adds
  `--schema-mode json-schema`; it was pushed to `origin/main` and pulled on HP.
- In `json-schema` mode, the shim wraps the Ollama/EMR `format` object in the
  R11-verified nested OpenAI-style shape:
  `response_format: {"type":"json_schema","json_schema":{"name":"explain_response","strict":true,"schema":...}}`.
- Default remains `--schema-mode json-object` for backward compatibility.
- `json-schema` mode fails closed with HTTP 400 if the request has no JSON
  object `format` schema, and does not call upstream in that case.
- Validation before commit/push: `py_compile` passed,
  `python -m unittest tests.test_hpz2_ollama_compat_llamacpp_shim` ran 9 tests
  successfully, and `git diff --check` passed with CRLF warnings only.
- Shape review found the first flat working-tree draft did not match the R11 HP
  probe artifact; the implementation was corrected to the nested shape before
  commit/push.
- This implementation still does not authorize `/explain`, model execution,
  matrix runs, EMR writes, cleanup, download, commit, or push without separate
  GO.

R13 H2 schema-mode A/B plan freeze (2026-05-30):

- Plan doc: `docs/h2-schema-mode-ab-plan-2026-05-30.md`.
- Purpose: resolve the R12 carry note that R11/R12 prove accepted shape and
  forwarding, but not hard schema enforcement across longer clinical prompts.
- Frozen minimal matrix is 4 cells:
  `RA-03-safety-boundary` + `RA-05-rule-kb-nuance-conflict` crossed with
  `json_object` + `json_schema` on `hpz2-l2-qwen36-35b-a3b`.
- RA-03 values remain locked: `sme + trimesy + lacto2`, `dx=a090`, pediatric
  `age=1`.
- RA-05 values for this A/B: `dx=a09`, `orders=tamiiv`, pediatric `age=11`.
  RA-05 is structure/schema-enforcement evidence only; do not use it for final
  content-quality verdicts because expected summary wording and clinical input
  review are user-owned pending.
- Optional expansion to `hpz2-l2-granite-41-30b-q4km` is an 8-cell run and
  requires separate explicit approval.
- Decision rules are pre-registered in the plan: RA-05 `json_schema` conforming
  while `json_object` drifts selects `json_schema`; no meaningful structural
  difference selects `json_object` plus strict-schema conformance metric/caveat.
- Safety envelope: SSH tunnel/loopback only, env override only, no
  `data/llm_settings.json` write, PHI hit count `0` hard gate,
  shutdown/ports-closed verification, and PHI-safe metadata only.
- This plan freeze does not authorize `/explain`, HP runtime startup, model
  execution, matrix execution, EMR writes, cleanup, downloads, commit, or push.

R14 H2 schema-mode A/B execution result (2026-05-30/31):

- Executed the A/B; the frozen 4-cell matrix was expanded to 8 cells with
  explicit approval (added `hpz2-l2-granite-41-30b-q4km`).
- 8/8 cells PASS: HTTP 200, EMR `ok`, valid JSON, strict schema conformant,
  structural drift NO, citation verifier pass, PHI hit `0`, for both Qwen 35B
  A3B official and Granite 4.1 30B across `json_object` and `json_schema`.
- Decision: pre-registered Rule 2 (no meaningful structural difference) ->
  H2 uses `json_object` plus a strict-schema conformance metric and caveat.
- Honest caveat: the discriminating case RA-05 did not drift under `json_object`
  either, so enforcement was not demonstrated and `json_object` was not observed
  failing. The result is mode-invariance for 2 cases x 2 Primary-tier models
  only, not general `json_object` safety. Keep the conformance metric live as a
  tripwire for weaker models / harder cases.
- HP runtime torn down (pair 4: shim PID `63764`, `llama-server` PID `42084`
  stopped; ports `18080`/`18081` no listener). HP repos clean at
  `local-llm-eval 08a94af` / `EMR_AI_24clinic 543e1f9`.
- EMR pin note: Main PC `EMR_AI_24clinic` advanced `543e1f9 -> c6dc30c`
  (`feat(case-review): add core6 r3 rule context`, clinical-assist track);
  `app/llm/` unchanged, so the A/B contract basis is intact.
- Process-safety incident (low severity, no data loss): a user-opened Excel view
  of `knowledge/master_data/처방자료-모두.xls` was flagged modified; run recovery
  killed the user `EXCEL.EXE` and reverted the file. User confirmed view-only, so
  no data was lost. Corrective rule: do not auto-revert files the agent did not
  modify and do not kill user processes; on a shared workstation, STOP and
  surface user-caused dirty state instead.
- This result does not authorize Phase 2 heavy run, more `/explain` cases,
  matrix, EMR writes, cleanup, downloads, commit, or push.

R15 H2 model-comparison plan freeze (2026-05-31):

- Plan doc: `docs/h2-model-comparison-plan-2026-05-31.md`.
- Purpose: compare the locked Primary shortlist under one fixed `/explain`
  endpoint condition to recommend a model or decline if evidence is
  insufficient.
- Fixed condition: schema mode `json_object` from R14, strict-schema
  conformance metric live as a tripwire, `top_k=5`, `min_similarity=0.45`,
  `lexical_rerank=false`, prompt/tone unchanged. Model is the only variable.
- Model scope: Primary 4 only:
  `hpz2-l2-qwen36-35b-a3b`,
  `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4`,
  `hpz2-l2-qwen36-35b-a3b-mtp-q8`,
  `hpz2-l2-granite-41-30b-q4km`.
- Reference/historical models are out of scope unless separately approved.
- Case scope: 17 total eval cases. RA-04 is PHI early-return and must not call
  the model, so the expected model-call cells are 4 models x 16 cases = 64.
- RA-06/RA-07 are included, but their content-quality verdict remains
  provisional until user-owned expected-summary keyword spot-check is closed.
  RA-06 is retained as a hard-case tripwire for multi-citation behavior and
  structural/schema conformance.
- Recommended next sequence: plan review, plan commit/push, HP pull/verify,
  optional RA-06/RA-07 keyword spot-check, then explicit `Phase 2 heavy run GO`.
- This plan freeze does not authorize `/explain`, HP runtime startup, model
  execution, matrix execution, EMR writes, cleanup, downloads, commit, or push.

## Hard Stops

- Do not run models or heavy eval without explicit GO.
- Do not write to `C:\Github\EMR_AI_24clinic` without explicit GO.
- Do not enter Phase 1d implementation from this repo.
- Do not regenerate the 681 chunk baseline or touch chunk-variation work unless explicitly reopened.
- Do not revert app prompt files for Stage C; use runner-side fixtures only if that stage is approved.
- Do not change RA-03 resolved values or infer RA-01/RA-02/RA-05 expected wording; those are user-owned.
- Do not treat shim health preflight as permission to call `/explain`.
- Do not treat shim review PASS as permission to call `/explain`; H1 still needs
  a plan GO and a separate execution GO.
- Do not run H1 minimal through `scripts/smoke_test_explain.py` without a
  broader explicit GO; it runs more than one case and writes report artifacts.
- Do not treat H1 RA-03 PASS as permission for more `/explain` cases, Phase 2
  heavy run, matrix execution, EMR writes, cleanup, or downloads.
- Do not treat H2 A/B plan freeze as permission to execute H2 A/B, start HP
  runtime, or call `/explain`; execution requires a separate explicit GO.
- Do not use RA-05 for final content-quality verdicts until the user-owned
  expected-summary and clinical-input checks are complete.
- Do not expand H2 A/B beyond the executed 8-cell (Qwen + Granite) set without
  separate explicit approval.
- Do not treat the H2 A/B Rule-2 result (`json_object` chosen) as proof of
  general `json_object` safety; the discriminating case did not drift, so keep
  the strict-schema conformance metric live in H2 and do not drop `json_schema`.
- Do not treat H2 model-comparison plan freeze as permission to execute H2,
  start HP runtime, call `/explain`, or run model matrices; execution still
  requires explicit `Phase 2 heavy run GO`.
- Do not use RA-06/RA-07 for final content-quality verdicts until the
  user-owned expected-summary keyword spot-check is closed; if run earlier,
  label their content lanes provisional.
- Do not add reference/historical models to H2 model comparison without a
  separate review and explicit user GO.
- Do not commit or push unless explicitly requested.
