---
id: dgx-spark-asus-128gb-1tb-transition-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: Main PC transition plan after the user ordered an ASUS DGX Spark OEM system with 128 GB memory and 1 TB storage
related:
  - docs/gemma-4-qat-llamacpp-c1-endpoint-replay-candidate-plan-2026-06-07.md
  - docs/gemma-4-qat-llamacpp-endpoint-readiness-bridge-plan-2026-06-07.md
  - docs/gemma-4-qat-llamacpp-output-contract-runner-plan-2026-06-07.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - tools/hpz2_llamacpp_gemma_output_contract_pilot.py
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - https://www.nvidia.com/en-us/products/workstations/dgx-spark/
  - https://www.asus.com/us/networking-iot-servers/desktop-ai-supercomputer/ultra-small-ai-supercomputers/asus-ascent-gx10/techspec/
  - https://docs.nvidia.com/dgx/dgx-spark-porting-guide/index.html
---

# DGX Spark ASUS 128GB 1TB Transition Plan

## Project Goal Check

- direct value: prevent the current Gemma/C1 endpoint-replay work from
  continuing down an HP Z2-specific runtime path after the user ordered the
  replacement DGX Spark-class system.
- classification: `direct progress` with safety and continuity value.
- narrower scope: Main PC plan and relay update only. No code patch, HP command,
  DGX command, model load, prompt/API call, `/explain`, endpoint replay, EMR
  write/reindex, artifact mutation, machine-role file edit, librarian backup,
  commit, or push is authorized by this file.

## User Hardware Update

User-reported purchase:

```text
ASUS DGX Spark OEM class system
ASUS Ascent GX10 family
128 GB unified memory
1 TB internal storage
HP Z2 will be returned
```

Current official reference points, checked on 2026-06-07:

- NVIDIA DGX Spark reference platform: GB10 Grace Blackwell, 20-core ARM CPU,
  128 GB LPDDR5x coherent unified system memory, DGX OS, and up to 1 PFLOP FP4
  theoretical performance.
- ASUS Ascent GX10 public specs describe the ASUS OEM system as a GB10-based
  desktop AI supercomputer with 128 GB LPDDR5x unified memory.
- ASUS datasheet/searchable spec variants include 1 TB, 2 TB, and 4 TB storage
  options. The user's ordered unit is the 1 TB variant.
- NVIDIA DGX Spark porting guidance treats the platform as ARM-based with
  unified CPU/GPU memory, not an x86 workstation with a discrete GPU memory
  model.

Arrival-time verification is still required. Do not treat the ordered spec as a
live runnable host until first-boot evidence is captured.

## Decision

HP Z2 is no longer the forward runtime target for new `local-llm-eval` model
execution.

HP Z2 becomes:

- legacy evidence source.
- return/cleanup target.
- optional one-time export/closeout target only if the user gives an explicit
  HP return-closeout GO.

DGX Spark ASUS becomes:

- the future runtime target after physical arrival and bootstrap probe.
- not endpoint-ready.
- not automatically equivalent to HP Z2.
- not authorized for model execution until DGX-specific preflight passes.

The previous next gate,

```text
Main PC local-llm-eval Gemma llama.cpp C1 endpoint-replay candidate runner patch GO
```

should be paused as an HP-targeted execution path. It can be resumed only after
the runner is retargeted or reviewed for DGX Spark.

## Evidence Preservation

Keep existing HP Z2 artifacts and plans as durable historical evidence:

- HP Z2 Gemma dry-load and prompt-smoke evidence.
- direct llama.cpp output-contract pilot artifact.
- synthetic endpoint-readiness bridge artifact.
- Gemma C1 endpoint-replay candidate plan at `local-llm-eval@e62bd8b`.
- `hpz2-run-artifacts@40e2a0e` bridge artifact.

Do not rewrite these as DGX evidence.

Do not delete or reinterpret HP Z2 artifacts just because the host is being
returned. They remain valid for the exact host/backend/version they measured.

## Immediate Routing Change

Main PC remains:

- repo write owner.
- review/docs/commit/push control plane.
- live memory relay owner.

HP Z2 becomes:

- no-new-run host by default.
- artifact/history source only.
- not a memory writer.

DGX Spark ASUS should initially be treated as:

- execution candidate.
- memory read-only consumer.
- artifact producer after a dedicated artifact repository/naming decision.

Do not edit `C:\Github\memory\MACHINE_ROLES.md` from this target-project
session. A durable common machine-role update needs a separate common-rule or
machine-role-change GO.

## Artifact Repository Decision

Do not publish DGX Spark artifacts into `hpz2-run-artifacts` by default.

Recommended options, to be decided before first DGX artifact publish:

1. Create a new `dgx-spark-run-artifacts` repo for DGX-only results.
2. Create a neutral `local-llm-run-artifacts` repo and move future host-specific
   directories under `hpz2/` and `dgx-spark/`.
3. Keep `hpz2-run-artifacts` frozen as a legacy HP repo and use a new DGX repo.

Option 3 is the least confusing for the current evidence chain.

## DGX Bootstrap Probe Requirements

First DGX work should be a bootstrap probe, not a Gemma endpoint replay.

Minimum first-boot capture:

- host name.
- OS and kernel.
- architecture (`aarch64` expected, verify).
- NVIDIA driver / CUDA stack.
- `nvidia-smi` behavior and known unified-memory reporting caveats.
- free disk on the 1 TB internal storage.
- available system memory.
- Python version.
- git availability.
- `llama.cpp` availability or build path.
- whether CUDA backend, Vulkan backend, or another backend is actually used.
- whether `llama-server` starts and stops cleanly on a tiny non-PHI synthetic
  prompt.

The first probe must not call `/explain`.

The first probe must not load large models unless a separate model-specific
fit GO is given.

## Storage Constraint

1 TB internal storage is a real constraint for this project.

Before downloading or copying models, define a model-cache policy:

- internal-only small curated set.
- external NVMe model root.
- NAS/shared cache.
- per-gate download/delete policy.

Do not assume HP model paths such as:

```text
C:\Users\test\.lmstudio\models\...
```

exist or should be recreated on DGX Spark. DGX OS pathing is expected to be
Linux-like until proven otherwise.

## Runtime Porting Risks

HP Z2 runner assumptions that need review before DGX use:

- Windows paths.
- HP-specific model labels and GGUF paths.
- Vulkan device selection such as `Vulkan0`.
- `lms` / LM Studio assumptions.
- `tasklist`, `netstat`, or PowerShell process checks.
- x86 build assumptions.
- discrete-GPU memory assumptions.

DGX Spark-specific risks:

- ARM64 build compatibility.
- CUDA/driver version alignment.
- unified-memory reporting differences.
- FP4/NVFP4 support availability in the actual runtime stack.
- llama.cpp support for GB10 and the selected quantization/runtime backend.
- 1 TB storage pressure.

## Retargeting Plan

Recommended sequence:

1. **Main PC transition plan review/commit**

   Commit this plan after review. No runtime work.

2. **Main PC runner audit plan**

   Identify every HP-specific assumption in:

   - `tools/hpz2_llamacpp_gemma_output_contract_pilot.py`
   - `tools/hpz2_llamacpp_h2_endpoint_runner.py`
   - related tests and docs.

3. **DGX Spark bootstrap probe**

   After the machine arrives, run first-boot and tiny llama.cpp smoke only.

4. **DGX host profile patch**

   Add host abstraction only after live DGX evidence says which backend and
   paths are real.

5. **Gemma output-contract re-baseline**

   Re-run the smallest direct llama.cpp synthetic output-contract pilot on DGX.

6. **Gemma bridge re-baseline**

   Re-run synthetic C1-shaped bridge if output-contract remains clean.

7. **C1 endpoint-replay candidate**

   Only after the DGX direct llama.cpp and synthetic bridge lanes pass should
   the project reopen the tiny 4-cell C1 endpoint-replay candidate lane.

## Stop Criteria

Stop and ask before runtime work if:

- the DGX host has not arrived.
- OS/architecture/driver/CUDA stack is unknown.
- `llama.cpp` backend support is unknown.
- 1 TB storage free-space policy is not decided.
- the runner patch would preserve HP-only paths under a DGX label.
- DGX artifacts would be mixed into `hpz2-run-artifacts` without a repository
  naming decision.
- the work would call `/explain` before a DGX synthetic output-contract
  baseline.
- a plan gate is being used as commit/push, model execution, or artifact publish
  authority.

## Common Memory Candidate

This project-local transition implies a common machine-role update may be
needed later.

Candidate:

```text
source: local-llm-eval DGX Spark ASUS transition
improvement: replace HP Z2 default execution-node wording with HP legacy/returning and DGX Spark pending execution-node wording
affected projects: local-llm-eval first; any future C:\Github local-LLM runtime routing that reads MACHINE_ROLES.md
evidence: user ordered ASUS DGX Spark OEM 128 GB / 1 TB and stated HP will be returned
session-only behavior changed: yes, no new HP runs are treated as default
durable target: C:\Github\memory\MACHINE_ROLES.md and local-llm-eval project README if user approves
required GO: Main PC machine role change GO or codex-solo common machine-role update GO
risk if deferred: future agents may keep routing new runtime work to HP Z2 from stale bootstrap text
```

No common files are edited by this plan.

## Next Gates

Source closeout gate:

```text
Main PC local-llm-eval DGX Spark ASUS 128GB 1TB transition plan review/commit/push GO
```

After DGX arrival:

```text
DGX Spark local-llm-eval llama.cpp bootstrap probe GO
```

Optional common-role gate:

```text
Main PC machine role change GO
```

Librarian backup remains a separate batched maintenance gate.
