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

Phase 2 heavy run remains blocked until:

- HP Z2 setup is complete
- The user explicitly issues `Phase 2 heavy run GO`

RA-03 is resolved as `sme + trimesy + lacto2`, `dx=a090`, pediatric `age=1`; expected citations are verified in current RAG chunks. Do not change those values without explicit user instruction.

## Current Runner Baseline

Phase 2 model viability baselines should now be measured on the official HP Z2 runner:

- Execution host: HP Z2 Mini G1a
- Backend lane under test: LM Studio
- Runtime: llama.cpp Vulkan
- Load profile: `--gpu max --context-length 4096 --ttl 120`
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
- Phase 2 Stage A pacing: unload before/after each model, confirm `lms status` has no loaded models, wait 90s after unload, wait 180s after large models or failures.
- Phase 2 Stage A-R load profile: `--gpu max --context-length 32768 --ttl 3600 -y` on HP Z2. Stage A strict baseline remains `4096`.
- Stage A-R does not replace the Stage A strict endpoint baseline; use it only to test model-aware profiles such as Qwen `/no_think`, gpt-oss reasoning hints, Granite RAG/extraction settings, Gemma sampling, and LM Studio JSON schema output.
- L2 semantic smoke does not use the real endpoint. Its dry-run is config/spec validation only. Actual HP Z2 model execution requires a separate `HP Z2 L2 semantic smoke matrix GO`.

The main PC remains the canonical workspace for review, documentation, commit, and push. HP Z2 is execution-only unless the user explicitly changes that rule.

Earlier 5080, subpc, Ollama, or manual one-off results are exploratory only and must not be mixed into the official HP Z2 LM Studio/Vulkan speed baseline.

## Hard Stops

- Do not run models or heavy eval without explicit GO.
- Do not write to `C:\Github\EMR_AI_24clinic` without explicit GO.
- Do not enter Phase 1d implementation from this repo.
- Do not regenerate the 681 chunk baseline or touch chunk-variation work unless explicitly reopened.
- Do not revert app prompt files for Stage C; use runner-side fixtures only if that stage is approved.
- Do not change RA-03 resolved values or infer RA-01/RA-02/RA-05 expected wording; those are user-owned.
- Do not commit or push unless explicitly requested.
