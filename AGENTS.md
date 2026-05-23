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

Current frozen planning artifacts:

- `docs/rag_aware_eval_design_r0.md` = Phase 2.1 design R1 frozen baseline
- `prompts/rag_aware_eval_set_v0.1.json` = eval set spec v0.1 R1 frozen baseline

Phase 2 heavy run remains blocked until:

- HP Z2 setup is complete
- RA-03 `{TBD-code-1}` / `{TBD-code-2}` / `{TBD-dx}` are user-confirmed
- RA-03 expected citation source IDs are verified against the RAG index
- The user explicitly issues `Phase 2 heavy run GO`

## Current Runner Baseline

Phase 2 model viability baselines should now be measured on the official HP Z2 runner:

- Execution host: HP Z2 Mini G1a
- Backend lane under test: LM Studio
- Runtime: llama.cpp Vulkan
- Load profile: `--gpu max --context-length 4096 --ttl 120`
- Smoke config: `models_config_hpz2_lmstudio_smoke_v0.1.json`
- Smoke prompt: `prompts/hpz2_lmstudio_smoke_v0.1.json`
- Runbook: `docs/hpz2-lmstudio-official-smoke-baseline-2026-05-24.md`

The main PC remains the canonical workspace for review, documentation, commit, and push. HP Z2 is execution-only unless the user explicitly changes that rule.

Earlier 5080, subpc, Ollama, or manual one-off results are exploratory only and must not be mixed into the official HP Z2 LM Studio/Vulkan speed baseline.

## Hard Stops

- Do not run models or heavy eval without explicit GO.
- Do not write to `C:\Github\EMR_AI_24clinic` without explicit GO.
- Do not enter Phase 1d implementation from this repo.
- Do not regenerate the 681 chunk baseline or touch chunk-variation work unless explicitly reopened.
- Do not revert app prompt files for Stage C; use runner-side fixtures only if that stage is approved.
- Do not infer RA-03 codes or RA-01~RA-05 expected wording; those are user-owned.
- Do not commit or push unless explicitly requested.
