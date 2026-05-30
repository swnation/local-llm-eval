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
- `prompts/rag_aware_eval_set_v0.1.json` = eval set spec v0.1, with R2 four-lane/P7/acceptable-citation additions
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
  matches. Carry notes: H1 must confirm valid JSON and model-name mapping; H2+
  quality comparisons must revisit schema fidelity because the shim currently
  sends llama.cpp `response_format: {"type":"json_object"}` rather than the
  stricter EMR `format` schema.

This shim status by itself does not authorize L5 or `/explain`; H1 execution
requires a separate explicit execution GO after the plan is accepted.

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
  downloads, or H2+ quality conclusions. H2+ quality comparisons must revisit
  schema fidelity because the shim still maps EMR strict `format` schema to
  llama.cpp `json_object`.
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
- Do not commit or push unless explicitly requested.
