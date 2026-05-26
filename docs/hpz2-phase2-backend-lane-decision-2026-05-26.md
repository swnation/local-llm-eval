---
id: hpz2-phase2-backend-lane-decision-2026-05-26
project: local-llm-eval
type: decision
status: active
created: 2026-05-26
scope: HP Z2 Phase 2 L2/L3 backend lane decision
related:
  - docs/hpz2-phase2-ladder-progress-v0.1.md
  - docs/hpz2-llamacpp-phase2-l2-runner-2026-05-26.md
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
  - tools/hpz2_llamacpp_phase2_l2_runner.py
  - ../hpz2-run-artifacts/results/llamacpp_vram_full_matrix_20260526_180420/hpz2_llamacpp_transition_and_heavy_run_report.md
---

# HP Z2 Phase 2 Backend Lane Decision

Decision lock: HP Z2 Phase 2 L2/L3 candidate evaluation uses llama.cpp as the
primary execution backend. LM Studio remains available as a secondary lane for
manual model management, UI inspection, and historical comparison.

This decision does not authorize L3, L4, L5, real `/explain`, EMR writes,
cleanup, downloads, commit, or push. It only chooses the execution backend for
synthetic L2 and later runner-side candidate evaluation.

## Decision

| Lane | Status | Use |
|---|---|---|
| llama.cpp `llama-server.exe` | primary | HP Z2 L2/L3 candidate evaluation |
| LM Studio | secondary | model management, manual inspection, historical comparison |
| Ollama/subpc/manual one-offs | historical only | do not mix into official HP Z2 speed baseline |

## Rationale

The HP Z2 full matrix at `hpz2-run-artifacts` commit `cdd3ab1` completed 13
models x 4 L2 cases x 4 llama.cpp profiles with no load failure, no API failure,
clean citation integrity, and no stale `llama-server` process at the end. The
run also showed that explicit llama.cpp flags give better operational control
than app-mediated LM Studio behavior for unattended runs.

Primary default:

```powershell
llama-server.exe -m <model.gguf> -a <alias> --host 127.0.0.1 --port 18080 `
  -c 16384 -n 8192 `
  -dev Vulkan0 -ngl all -sm none -mg 0 `
  --no-mmap --no-host --kv-offload --op-offload -fa on `
  -ctk q8_0 -ctv q8_0 `
  --cache-ram 0 --no-cache-prompt --ctx-checkpoints 0 `
  -b 1024 -ub 256 -np 1 --reasoning off
```

GPT-OSS GGUF models add:

```powershell
--skip-chat-parsing
```

Fallback batch profile if a future model regresses:

```powershell
-b 256 -ub 64
```

## Evidence

Primary artifact:

```text
C:\Github\hpz2-run-artifacts\results\llamacpp_vram_full_matrix_20260526_180420\
```

Key fields:

- `stopped_early = False`
- 208/208 API responses
- 208/208 core citation pass
- 208/208 strong citation pass
- 0 invalid aliases
- 0 unknown citations
- 0 placeholder citations
- final LM Studio state: Server ON, No Models Loaded
- final `llama-server` process state: no process left
- final C: free space: about 234 GiB

Earlier failed/stabilization artifacts are preserved under the same
`hpz2-run-artifacts` commit. They justify the `--no-mmap`, no-host fallback,
Q8 KV, and GPT-OSS parser rules.

## Secondary Lane Carry

LM Studio L2 artifacts remain valid secondary evidence. They are not deleted and
are not reinterpreted as failed. Their operational limitation is repeatability
and runtime control, not total unusability.

