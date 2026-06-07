---
id: dgx-spark-artifact-repo-root-decision-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: Main PC plan for the DGX Spark artifact repository and output-root decision
related:
  - docs/dgx-spark-asus-128gb-1tb-transition-plan-2026-06-07.md
  - docs/dgx-spark-asus-runner-audit-plan-2026-06-07.md
  - docs/dgx-spark-asus-bootstrap-probe-plan-2026-06-07.md
---

# DGX Spark Artifact Repo/Root Decision Plan

## Project Goal Check

- direct value: prevent DGX Spark bootstrap and later runtime evidence from
  being mixed into HP Z2-specific artifact history.
- classification: `maintenance` with direct evidence-hygiene and future
  execution-safety value.
- narrower scope: Main PC decision plan only. No GitHub repository creation,
  local clone, artifact write, HP/DGX command, model download/load, prompt/API
  call, `/explain`, endpoint replay, EMR write/reindex, relay update, librarian
  backup, commit, or push is authorized by this file.

## Decision

Use a new DGX-specific artifact repository.

Selected name:

```text
dgx-spark-run-artifacts
```

Expected GitHub target, pending a separate creation GO:

```text
swnation/dgx-spark-run-artifacts
```

Expected Main PC checkout path, pending a separate clone/setup GO:

```text
C:\Github\dgx-spark-run-artifacts
```

Rationale:

- `hpz2-run-artifacts` is already a host-specific historical evidence repo.
- DGX Spark has a different CPU architecture, GPU/backend stack, OS, model-root
  policy, and likely different runtime lifecycle.
- A new repo avoids accidental HP-vs-DGX comparability claims.
- It preserves old HP results only until the useful setup references are
  extracted and the HP repo is retired under a later explicit gate.
- It keeps the first DGX bootstrap artifact review simple: one host, one repo,
  one evidence lineage.

## Non-Goals

This plan does not:

- create the GitHub repository.
- clone the repository.
- decide public/private visibility.
- migrate HP artifacts.
- modify `hpz2-run-artifacts`.
- delete or archive `hpz2-run-artifacts`.
- define a multi-host artifact taxonomy.
- authorize DGX execution.
- authorize model downloads or model loading.
- authorize `/explain` or endpoint replay.

## Repository Boundary

`hpz2-run-artifacts` remains:

- HP Z2-only historical evidence.
- valid only for the exact host/backend/version evidence it measured.
- not a destination for DGX Spark bootstrap, smoke, bridge, endpoint replay, or
  model-comparison artifacts.
- not a long-term active repo after DGX setup references have been extracted.

`dgx-spark-run-artifacts` should become:

- DGX Spark ASUS-only artifact destination.
- metadata-first runtime evidence repo.
- source-backed evidence store for bootstrap, output-contract, synthetic bridge,
  and later endpoint-replay gates.
- separate from memory/librarian backup.

If the project later adds multiple DGX-class hosts, decide then whether to keep
per-host repos or introduce a neutral `local-llm-run-artifacts` repo. Do not
preemptively generalize now.

## HP Artifact Repo Retirement Decision

User decision:

```text
When the DGX Spark arrives, use the old HP artifact repo only for setup
references that are still useful, then retire/delete it under a later explicit
gate.
```

Useful reference categories:

- artifact metadata shape.
- runtime preflight and final cleanup checks.
- llama.cpp server lifecycle notes.
- PHI/raw-output storage boundaries.
- review/publish workflow lessons.
- known patterns to avoid, such as HP-specific paths, Vulkan args,
  PowerShell preflight, HP SSH topology, and HP-only artifact roots.

Retirement/deletion is not part of this plan. A later retirement gate should:

- verify the HP repo has no uncommitted/unpushed evidence that the project still
  needs.
- copy any setup-only references into DGX docs or the new DGX artifact repo
  README.
- decide whether deletion means local checkout removal only, remote repository
  archival, or remote repository deletion.
- preserve enough relay history to explain why older HP evidence should not be
  used for DGX model ranking or endpoint-readiness claims.
- run a backup after the relay/root state records the retirement result.

## Initial Layout

Recommended initial repository layout:

```text
dgx-spark-run-artifacts/
  README.md
  results/
    dgx_spark_bootstrap_probe_<timestamp>/
      dgx_spark_bootstrap_probe_results.json
      dgx_spark_bootstrap_probe_summary.md
      llama_server_stdout.txt
      llama_server_stderr.txt
```

For the first bootstrap probe, stdout/stderr files are included only if a tiny
serving smoke actually runs. If the probe stops after host/toolchain evidence,
omit runtime logs and record the stop reason in JSON and summary.

## Minimum README Content

The repository README should state:

- purpose: DGX Spark ASUS artifact evidence for `local-llm-eval`.
- boundary: not HP Z2 evidence and not clinical production evidence.
- raw model output policy: store metadata by default; do not store long raw
  model output unless a later gate explicitly approves it.
- PHI policy: synthetic/non-PHI only unless a future project gate says
  otherwise; no patient data.
- publish rule: every committed artifact must name the source repo commit,
  host id, run mode, and stop reason.
- comparison rule: DGX artifacts are not directly comparable to HP artifacts
  without a later reviewed comparison plan.

## First Artifact Requirements

The first artifact should be the bootstrap probe only.

Required fields mirror the bootstrap plan:

- `host_id`
- `generated_at`
- `source_repo_commit`
- `os_release`
- `kernel`
- `architecture`
- `cuda_version`
- `driver_version`
- `nvidia_smi_summary`
- `total_memory_gib`
- `free_memory_gib`
- `disk_free_gib`
- `model_root_policy`
- `llamacpp_commit`
- `llamacpp_build_args`
- `llama_server_binary`
- `tiny_model_source`
- `tiny_model_sha256`
- `server_started`
- `server_health_ok`
- `synthetic_request_ok`
- `phi_like_hits`
- `raw_model_output_stored`
- `final_processes_clean`
- `final_ports_clean`
- `stopped_early`
- `stop_reason`

If no tiny model is approved before the first probe, `tiny_model_source`,
`tiny_model_sha256`, `server_started`, `server_health_ok`, and
`synthetic_request_ok` may be null/false with a clear `stop_reason`.

## Publish Flow

Preferred sequence:

1. Create GitHub repo and Main PC checkout under a separate GO.
2. Add minimal README and `.gitignore`.
3. DGX Spark bootstrap probe writes local artifact output.
4. Main PC reviews the artifact payload before publish.
5. Commit/push the approved artifact into `dgx-spark-run-artifacts`.
6. Relay update records both `local-llm-eval` source commit and
   `dgx-spark-run-artifacts` artifact commit.
7. Librarian backup remains a separate Main PC gate.

## Stop Criteria

Stop before repo creation if:

- the user has not approved the GitHub repository name.
- repository visibility is not decided.
- the GitHub account/owner is unclear.
- creating the repo would require a new auth or billing path.

Stop before artifact publish if:

- the artifact was written under `hpz2-run-artifacts`.
- the artifact lacks `source_repo_commit` or `host_id`.
- raw model output is stored without explicit approval.
- PHI-like hits are present.
- final process/port cleanup failed.
- the artifact claims endpoint readiness, model ranking, Primary4 promotion, or
  `/explain` readiness from the bootstrap probe.

Stop before HP repo retirement/deletion if:

- DGX setup references have not been extracted.
- the HP artifact repo is dirty/diverged in a way that has not been classified.
- the user has not chosen local-only deletion, remote archival, or remote
  deletion.
- relay/root memory has not recorded the intended retirement scope.

## Next Gates

Review and source closeout:

```text
Main PC local-llm-eval DGX Spark artifact repo/root decision plan review/commit/push GO
```

After source closeout, relay update remains separate:

```text
Main PC local-llm-eval DGX Spark artifact repo/root decision plan relay update GO
```

If the plan is committed and the user wants the actual artifact repo created:

```text
Main PC local-llm-eval DGX Spark artifact repo create GO
```

After DGX setup references have been extracted from the old HP artifact repo:

```text
Main PC local-llm-eval HP Z2 artifact repo retirement plan GO
```

After the device arrives:

```text
DGX Spark local-llm-eval llama.cpp bootstrap probe GO
```

Librarian backup remains a separate batched maintenance gate after any later
relay update:

```text
Main PC local-llm-eval librarian pass GO
```
