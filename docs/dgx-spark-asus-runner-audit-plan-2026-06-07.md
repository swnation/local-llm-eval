---
id: dgx-spark-asus-runner-audit-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: Main PC audit plan for HP Z2-specific llama.cpp runners before any DGX Spark ASUS runtime retargeting
related:
  - docs/dgx-spark-asus-128gb-1tb-transition-plan-2026-06-07.md
  - docs/gemma-4-qat-llamacpp-c1-endpoint-replay-candidate-plan-2026-06-07.md
  - tools/hpz2_llamacpp_gemma_output_contract_pilot.py
  - tools/hpz2_llamacpp_h2_endpoint_runner.py
  - tools/hpz2_llamacpp_phase2_l2_runner.py
  - tests/test_hpz2_llamacpp_gemma_output_contract_pilot.py
  - tests/test_hpz2_llamacpp_h2_endpoint_runner.py
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
---

# DGX Spark ASUS Runner Audit Plan

## Project Goal Check

- direct value: identify the HP Z2-specific runtime assumptions that must be
  isolated before any DGX Spark runner patch or model execution.
- classification: `direct progress` with safety and portability value.
- narrower scope: Main PC audit plan only. No code patch, HP command, DGX
  command, model download/load, prompt/API call, `/explain`, endpoint replay,
  EMR write/reindex, artifact mutation, relay update, librarian backup, commit,
  or push is authorized by this file.

## Decision

Do not retarget the HP Z2 runners by simple rename.

The current runner surface is not a portable "llama.cpp runner" yet. It is a
set of HP Z2/Windows/LM Studio-path-specific tools with useful logic embedded
inside them.

Recommended policy:

```text
Preserve HP Z2 runners as legacy evidence runners.
Create DGX support through a host-profile or new DGX bootstrap-probe surface
only after live DGX first-boot evidence exists.
```

Before DGX arrival, the safe work is audit/planning only.

## Current Source State

Reviewed source baseline:

```text
local-llm-eval@1ffec17a12848f27d01f0c38171693351d9e6c37
docs(rag): plan DGX Spark transition
```

Transition decision carried:

- HP Z2 is legacy/return-closeout only for new work by default.
- DGX Spark ASUS 128 GB / 1 TB is the future runtime target only after
  first-boot/bootstrap probe.
- Existing HP artifacts remain host-specific historical evidence.

## Audit Scope

Primary files:

- `tools/hpz2_llamacpp_gemma_output_contract_pilot.py`
- `tools/hpz2_llamacpp_h2_endpoint_runner.py`
- `tools/hpz2_llamacpp_phase2_l2_runner.py`
- `models_config_hpz2_llamacpp_phase2_l2_v0.1.json`

Tests:

- `tests/test_hpz2_llamacpp_gemma_output_contract_pilot.py`
- `tests/test_hpz2_llamacpp_h2_endpoint_runner.py`

Out of scope for this plan:

- `EMR_AI_24clinic` changes.
- `hpz2-run-artifacts` mutation.
- actual DGX command execution.
- model download/copy/load.
- endpoint replay.
- production model recommendation.

## Audit Findings

### 1. Host identity is encoded in names and guards

Evidence:

- `tools/hpz2_llamacpp_gemma_output_contract_pilot.py` uses
  `DEFAULT_MODELS = ["hpz2-gemma4-26b-a4b-qat-q4_0"]` and confirm flag
  `--confirm-hpz2`.
- `tools/hpz2_llamacpp_h2_endpoint_runner.py` uses `PRIMARY_MODELS` and
  `C1_REPLAY_PILOT_MODELS` with `hpz2-*` labels.
- tests construct args with `confirm_hpz2=True`.

Risk:

- A shallow rename can make DGX output look comparable to HP output even when
  host/backend/model paths differ.

Required audit outcome:

- Keep HP labels as HP evidence labels.
- Add DGX labels only after DGX model path/hash evidence exists.
- Do not use a generic free-form model selector for DGX until allowlisted host
  profiles exist.

### 2. Model paths are Windows and LM Studio specific

Evidence:

- Gemma QAT paths are hard-coded as
  `C:\Users\test\.lmstudio\models\...` in
  `tools/hpz2_llamacpp_gemma_output_contract_pilot.py`.
- the HP config stores model paths under
  `C:\Users\test\.lmstudio\models\...`.

Risk:

- DGX Spark is expected to use Linux-like paths until proven otherwise.
- 1 TB internal storage makes path/cache policy a first-class runtime decision,
  not a mechanical path replacement.

Required audit outcome:

- DGX model paths must come from a DGX host profile or DGX model inventory.
- The first DGX plan must decide internal/external/NAS model root before large
  model downloads.

### 3. Runtime backend is HP Vulkan/Windows specific

Evidence:

- HP config binary is
  `C:/github/llama-cpp-runtime/b9333/llama-server.exe`.
- HP config default args select `-dev Vulkan0` and HP tuning flags.
- runner process checks look for `llama-server`/`llama-server.exe` style
  processes.

Risk:

- DGX Spark backend may be CUDA or another NVIDIA stack, not HP Vulkan.
- ARM64 and GB10 support must be verified live.
- HP flags such as `-dev Vulkan0`, Windows binary path, or x86 build
  assumptions may be invalid.

Required audit outcome:

- Do not carry HP `default_args` into DGX without a live llama.cpp smoke.
- DGX backend selection belongs to the bootstrap probe, not this audit plan.

### 4. Preflight is PowerShell/Windows-specific

Evidence:

- Gemma runner uses PowerShell `Get-NetTCPConnection` and `Get-CimInstance` for
  ports/shim process checks.
- L2 runner uses PowerShell `Get-CimInstance Win32_OperatingSystem`,
  `Get-PSDrive`, and `lms status`.
- H2 endpoint runner remote preflight is a PowerShell script executed over SSH.

Risk:

- These checks will not run on a Linux-like DGX OS.
- `nvidia-smi`, disk, memory, process, and port checks need separate DGX
  implementations.

Required audit outcome:

- Separate preflight into host-specific implementations.
- DGX preflight must record OS, architecture, driver/CUDA, memory reporting,
  free disk, ports, and process state before any model load.

### 5. Endpoint runner is tied to HP SSH plus local EMR harness topology

Evidence:

- H2 endpoint runner sets `HP_SSH = "test@192.168.68.50"`.
- It starts remote HP PowerShell commands, then starts a local SSH tunnel:
  `ssh -L 18081:127.0.0.1:18081 -N`.
- It starts `hpz2_ollama_compat_llamacpp_shim.py` remotely on HP and calls the
  Main PC EMR harness through `EMR_LLM_HOST=http://127.0.0.1:18081`.

Risk:

- DGX network identity, OS, and shim/runtime topology are unknown.
- Endpoint replay should not be the first DGX run.

Required audit outcome:

- Do not port H2 endpoint runner before DGX bootstrap and synthetic
  output-contract baseline.
- Treat endpoint-runner DGX support as a later gate after host profile and
  synthetic bridge pass.

### 6. Artifact output defaults are HP-specific

Evidence:

- L2 runner output root defaults to
  `C:/github/hpz2-run-artifacts/results`.
- H2 endpoint runner output root defaults to
  `C:/Github/hpz2-run-artifacts/results`.

Risk:

- DGX results could be mixed into an HP artifact repo.

Required audit outcome:

- Keep `hpz2-run-artifacts` HP-only unless a separate artifact-repo decision
  says otherwise.
- First DGX artifact publish needs a host-specific repo or neutral artifact
  root decision.

### 7. C1 candidate selector is still HP/Qwen/Granite scoped

Evidence:

- `C1_REPLAY_PILOT_MODELS` contains Qwen official and Granite only.
- `--primary4-c1-replay` expands to HP Primary4, not Gemma QAT and not DGX.
- Gemma C1 candidate plan already found that a dedicated selector is required.

Risk:

- Adding DGX/Gemma by modifying Primary4 would pollute the existing comparator
  lane and create false model-ranking evidence.

Required audit outcome:

- A future DGX Gemma candidate selector must be explicit and separate.
- It must not modify `PRIMARY_MODELS` or default C1 replay.

## Recommended Audit Output

The next reviewed plan or patch should produce a small matrix like this:

| Surface | HP-only behavior | DGX requirement | Action |
|---|---|---|---|
| host identity | `hpz2-*` labels and confirm flags | DGX host profile after live probe | preserve HP labels; add DGX labels later |
| model paths | Windows LM Studio paths | DGX model root policy | block until first-boot/storage plan |
| runtime args | Vulkan0 + Windows binary | live backend choice | verify in bootstrap probe |
| preflight | PowerShell/CIM/Get-NetTCPConnection | Linux/ARM/CUDA-aware checks | host-specific preflight |
| artifact root | `hpz2-run-artifacts` | DGX artifact repo/root | decide before first publish |
| endpoint runner | HP SSH/shim/tunnel | DGX topology unknown | defer endpoint replay |
| C1 selector | Qwen/Granite HP lane | explicit DGX/Gemma lane | separate selector only |

## Patch Strategy

Do not patch the endpoint runner first.

Preferred sequence:

1. **DGX Bootstrap Probe Plan**

   Draft a small DGX first-boot probe plan. It should collect host/runtime
   metadata only and run at most a tiny non-PHI llama.cpp smoke after separate
   DGX GO.

2. **Host Profile Design**

   After live DGX evidence, add a minimal host profile concept:

   ```text
   host_id
   os_family
   artifact_root
   model_root
   llama_server_binary
   backend_args
   preflight_kind
   process_check_kind
   port_set
   confirm_flag
   ```

3. **Direct Output-Contract Retarget**

   Retarget only the direct Gemma output-contract runner first. Keep synthetic
   prompts, metadata-only storage, and no `/explain`.

4. **Bridge Retarget**

   Re-run synthetic C1-shaped bridge only if output-contract remains clean.

5. **Endpoint Runner Retarget**

   Only then plan DGX endpoint-runner support, including shim/tunnel topology
   and EMR harness boundary.

## Acceptance Criteria For A Future Patch

A future DGX runner patch is acceptable only if:

- HP Z2 labels and artifact semantics remain unchanged.
- DGX labels are distinct from HP labels.
- no DGX result is written to `hpz2-run-artifacts` by default.
- no HP Windows path is reused for DGX.
- no HP Vulkan args are reused without live DGX backend evidence.
- preflight is host-specific and records the evidence needed for DGX.
- confirm flags are host-specific and cannot be accidentally satisfied by
  `--confirm-hpz2`.
- raw model output storage policy remains unchanged or stricter.
- `/explain` remains blocked until synthetic DGX output-contract and bridge
  gates pass.
- tests cover both HP legacy refusal paths and DGX host-profile refusal paths.

## Stop Criteria

Stop before patching if:

- DGX host has not arrived and the patch needs live backend/path facts.
- the patch would rename HP artifacts or labels to DGX.
- the patch would use `hpz2-run-artifacts` for DGX output.
- the patch would add Gemma/DGX to `PRIMARY_MODELS`.
- the patch would call `/explain` before DGX synthetic baselines.
- the patch would use HP PowerShell preflight on DGX.
- the patch would assume CUDA/Vulkan/FP4 support without live evidence.

## Next Gates

Review and source closeout:

```text
Main PC local-llm-eval DGX Spark ASUS runner audit plan review/commit/push GO
```

Better next technical gate before DGX arrival:

```text
Main PC local-llm-eval DGX Spark ASUS bootstrap probe plan GO
```

After DGX arrival:

```text
DGX Spark local-llm-eval llama.cpp bootstrap probe GO
```

Librarian backup remains a separate batched maintenance gate.
