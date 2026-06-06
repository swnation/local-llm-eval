---
id: hpz2-llamacpp-h2-endpoint-runner-2026-06-01
project: local-llm-eval
type: runbook
status: draft-built
created: 2026-06-01
scope: HP Z2 llama.cpp H2 endpoint runner and content-lane supplement
related:
  - docs/h2-model-comparison-plan-2026-05-31.md
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - prompts/rag_aware_eval_set_v0.1.json
---

# HP Z2 llama.cpp H2 Endpoint Runner

This runner exercises the reviewed `EMR_AI_24clinic` `/explain` endpoint from
the Main PC while HP Z2 hosts llama.cpp and the Ollama-compatible shim. It is
for the frozen H2 Primary 4 x 17 model-comparison lane and the follow-up
content-lane supplement only.

It does not write `C:\Github\EMR_AI_24clinic`, does not write
`data/llm_settings.json`, does not store raw prompts, and does not store raw
model responses.

## Files

- Runner: `tools/hpz2_llamacpp_h2_endpoint_runner.py`
- Config: `models_config_hpz2_llamacpp_phase2_l2_v0.1.json`
- Eval set: `prompts/rag_aware_eval_set_v0.1.json`
- Output root: `C:\Github\hpz2-run-artifacts\results\`

## Execution Gate

The runner refuses real work unless an explicit execution flag is present:

```powershell
C:\Github\EMR_AI_24clinic\.venv\Scripts\python.exe `
  tools\hpz2_llamacpp_h2_endpoint_runner.py `
  --confirm-h2-content-lane-supplement
```

The older full heavy-run confirmation remains accepted for the original H2
matrix lane:

```powershell
C:\Github\EMR_AI_24clinic\.venv\Scripts\python.exe `
  tools\hpz2_llamacpp_h2_endpoint_runner.py `
  --confirm-phase2-heavy-run
```

Neither flag authorizes L3/L4/L5, additional models, cleanup, downloads, EMR
writes, commits, or pushes.

The C1 endpoint-hypothesis replay lane has its own flag:

```powershell
C:\Github\EMR_AI_24clinic\.venv\Scripts\python.exe `
  tools\hpz2_llamacpp_h2_endpoint_runner.py `
  --confirm-h2-c1-endpoint-replay
```

Default C1 replay is an 8-call pilot: Qwen official + Granite x
`smoke-09-bst`, `RA-03-safety-boundary`,
`RA-06-dexisy-pediatric-nsaid-insurance`, and
`RA-07-umk-uri-syrup-age-insurance`. Use `--primary4-c1-replay` only after the
pilot is reviewed.

The default C1 replay keeps the eval payload retrieval options unchanged
(`top_k=5`, `min_similarity=0.45`, `lexical_rerank=false`). To run the scoped
C1 top-10 retrieval-policy experiment from the 2026-06-06 query policy plan,
use the named policy flag:

```powershell
C:\Github\EMR_AI_24clinic\.venv\Scripts\python.exe `
  tools\hpz2_llamacpp_h2_endpoint_runner.py `
  --confirm-h2-c1-endpoint-replay `
  --retrieval-policy h2_c1_current_aug_top10_v0
```

This policy keeps the existing H2 retrieval query augmentation and changes only
the C1 replay request payload `options.top_k` to `10`. It does not mutate the
eval JSON defaults, does not use expected source IDs to construct the live
query, and does not make top-10 retrieval a pass criterion by itself.

## Dirty-Worktree Policy

Default behavior is to reject dirty `local-llm-eval` and dirty
`EMR_AI_24clinic` before execution.

During the 2026-06-01 hardening-plus-supplement gate, the runner can allow only
these approved local `local-llm-eval` working-tree paths:

- `tools/hpz2_llamacpp_h2_endpoint_runner.py`
- `docs/hpz2-llamacpp-h2-endpoint-runner-2026-06-01.md`

Use the exception only with the explicit flag:

```powershell
C:\Github\EMR_AI_24clinic\.venv\Scripts\python.exe `
  tools\hpz2_llamacpp_h2_endpoint_runner.py `
  --confirm-h2-content-lane-supplement `
  --allow-approved-runner-worktree
```

The output JSON records the allowed dirty lines. `EMR_AI_24clinic` must remain
clean; there is no dirty exception for the EMR repo.

The runner performs a local harness dependency preflight before HP runtime
startup. If the Python interpreter cannot import `fastapi`, it stops before
loading a model and reports that the EMR virtualenv interpreter should be used.

## Runtime Hardening

- HP PowerShell commands use `-EncodedCommand` for complex scripts.
- `llama-server` and shim run through SSH foreground processes; detached
  `Start-Process` stdout is not treated as PID evidence.
- The runner lock records the coordinator process PID, avoiding false duplicate
  counts from parent/child Python processes in a virtual environment.
- Each model pair is torn down before the next model starts.
- Final HP preflight is recorded after the run to verify no `18080`/`18081`
  listener and no stale llama/shim process.
- Failed attempts should be preserved as separate artifact directories before
  rerun.

## Content Lane

For each model-called case with list-valued `expected_summary_keywords`, the
runner parses the raw LLM JSON in memory, checks whether each keyword appears
in `summary`, and writes only safe metadata:

- `content_lane_status`
- `content_lane_pass`
- keyword expected/hit counts
- missing keyword list

The parsed summary text is transient and is not written to JSON or markdown.

## C1 Endpoint Replay Lane

The C1 replay lane is separate from the broad H2 matrix and content-lane
supplement. It records manual-review metadata and stores endpoint response
bodies plus raw LLM JSON text only for the selected synthetic replay cells,
after PHI scanning. It does not change `EMR_AI_24clinic` code or production
prompts.

For each C1 cell, the runner records retrieval-policy metadata and diagnostics:

- `retrieval_policy_id`
- `retrieval_options_original`
- `retrieval_options_effective`
- `expected_source_rank`
- `retrieved_expected_hit_at_5`
- `retrieved_expected_hit_at_10`
- `expected_source_not_retrieved`
- `retrieved_expected_but_not_cited`
- `ra03_source_index_hygiene_unresolved`

`ra03_source_index_hygiene_unresolved` is a diagnostic lane for the optional
`rule:drug:sme` source in RA-03, not a C1 pass/fail criterion.

Primary output files are:

- `h2_c1_endpoint_replay_results.json`
- `h2_c1_endpoint_replay_summary.md`
- `responses\<model>\<case>__endpoint_response.json`
- `responses\<model>\<case>__raw_llm_response.txt`

Cases with string placeholders such as `{TBD-by-user-spot-check}` are recorded
as `not_scored_tbd_expected_keywords`. RA-04 is recorded as
`not_applicable_early_return` and must not call the model.

## Output

Each run creates a timestamped artifact directory under:

```text
C:\Github\hpz2-run-artifacts\results\
```

If `--output-dir` is supplied manually, it must still resolve under that output
root. The runner rejects paths outside the artifact repo.

Primary files:

- `h2_model_comparison_results.json`
- `h2_model_comparison_summary.md`
- `runtime_logs\<run_id>\<model>\llama.*.log`
- `runtime_logs\<run_id>\<model>\shim.*.log`

Read result JSON with Python `json.load` when non-ASCII source IDs or Korean
text are present. Do not use PowerShell `ConvertFrom-Json` as the sole validity
check for these artifacts.

## STOP Conditions

Stop and report if any of these occur:

- missing explicit execution confirmation flag;
- unapproved dirty repo path;
- dirty `EMR_AI_24clinic`;
- stale HP runtime process or occupied `18080`/`18081`;
- missing selected GGUF file;
- HP C: free space below 100 GiB;
- HP memory load at or above 92%;
- tunnel or health check failure;
- RA-04 calls the model;
- PHI hit count above zero;
- unapproved model, schema mode, case set, prompt, or retrieval setting.
