---
id: dgx-spark-asus-bootstrap-probe-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: Main PC plan for the first DGX Spark ASUS bootstrap probe after device arrival
related:
  - docs/dgx-spark-asus-128gb-1tb-transition-plan-2026-06-07.md
  - docs/dgx-spark-asus-runner-audit-plan-2026-06-07.md
  - docs/gemma-4-qat-llamacpp-output-contract-runner-plan-2026-06-07.md
  - docs/gemma-4-qat-llamacpp-endpoint-readiness-bridge-plan-2026-06-07.md
  - https://docs.nvidia.com/dgx/dgx-spark-porting-guide/index.html
  - https://docs.nvidia.com/dgx/dgx-spark-porting-guide/overview.html
  - https://docs.nvidia.com/dgx/dgx-spark-porting-guide/porting/software-requirements.html
  - https://build.nvidia.com/spark/llama-cpp/overview
  - https://build.nvidia.com/spark/vllm/i
---

# DGX Spark ASUS Bootstrap Probe Plan

## Project Goal Check

- direct value: define the first safe evidence packet for bringing the ASUS
  DGX Spark OEM system into `local-llm-eval` without accidentally running HP
  Z2-specific runners or endpoint replay.
- classification: `direct progress` with safety and operations value.
- narrower scope: Main PC plan only. No DGX command, HP command, code patch,
  model download/load, prompt/API call, `/explain`, endpoint replay, EMR
  write/reindex, artifact mutation, relay update, librarian backup, commit, or
  push is authorized by this file.

## Decision

The first DGX work must be a bootstrap probe, not a Gemma C1 endpoint replay.

The bootstrap probe should establish:

```text
DGX Spark ASUS can be treated as a known Linux/ARM/CUDA host for later
llama.cpp direct-runner work.
```

It must not establish:

- endpoint readiness.
- model quality.
- Primary4 or model-ranking evidence.
- equivalence with HP Z2 artifacts.
- a permanent artifact repository decision.
- a permanent machine-role change.

## Current Source State

Plan baseline:

```text
local-llm-eval@1ffec17a12848f27d01f0c38171693351d9e6c37
docs(rag): plan DGX Spark transition
```

Known local working-tree carry:

- `docs/dgx-spark-asus-runner-audit-plan-2026-06-07.md` may be untracked if
  its review/commit/push gate has not closed yet.
- This bootstrap plan is a separate plan gate and does not depend on committing
  the runner audit plan first.

## Official Platform Facts To Verify Live

Official NVIDIA references, checked on 2026-06-07, describe DGX Spark as:

- ARM-based with integrated Blackwell GPU and 128 GB unified memory.
- DGX OS based on Ubuntu 24.04, with NVIDIA drivers, libraries, frameworks, and
  tools.
- CUDA 13.0 and NVIDIA container runtime available in the software stack.
- `nvidia-smi` available for basic system health monitoring.
- llama.cpp official playbook: CUDA build, GGUF model, `llama-server`, and
  OpenAI-compatible `/v1/chat/completions` endpoint.
- vLLM official playbook: higher-throughput serving path requiring ARM64,
  CUDA 13.0, Docker, NVIDIA Container Toolkit, Python 3.12, and model-specific
  runtime tuning.

These are planning facts only. The probe must verify the actual delivered ASUS
unit because OEM image, storage option, driver versions, and updates may differ.

## Probe Phases

### Phase 0 -- Arrival And Identity

Goal:

- confirm the physical machine, OS, architecture, and remote-access identity.

Collect:

- hostname.
- username used for automation.
- local network identity/IP.
- SSH reachability from Main PC, if SSH is enabled.
- OS release.
- kernel.
- architecture.
- DGX OS / NVIDIA image version if exposed.
- uptime.
- timezone.

Expected:

- Linux-like OS.
- `aarch64` or equivalent ARM64 architecture.
- no assumption that HP paths, Windows commands, or PowerShell exist.

Stop if:

- the host cannot be uniquely identified.
- SSH/user identity is unclear.
- the OS is not the expected DGX/Ubuntu-like environment.

### Phase 1 -- Storage And Memory Baseline

Goal:

- determine whether the 1 TB internal storage is sufficient for immediate
  bootstrap and where model cache should live.

Collect:

- root filesystem free/used space.
- home filesystem free/used space.
- mounted external drives, if any.
- total/free system memory.
- swap status.
- `nvidia-smi` memory view and any unified-memory caveat.

Decision required after collection:

- internal-only short-term cache.
- external NVMe model root.
- NAS/shared model cache.
- per-gate download/delete policy.

Stop if:

- free internal space is already too low for build artifacts plus one small
  bootstrap model.
- the model-root policy is not decided before any large model download.

### Phase 2 -- Development Toolchain Check

Goal:

- confirm the machine can build or run llama.cpp without changing project code.

Collect command availability and versions:

- `git`.
- `cmake`.
- C/C++ compiler.
- `nvcc`.
- `python3`.
- `docker`.
- NVIDIA Container Toolkit / container runtime status if Docker is present.
- `nvidia-smi`.

Stop if:

- CUDA toolkit is absent or mismatched with the official DGX Spark image.
- Docker/container runtime is broken and vLLM is being considered for the next
  gate.
- build tools are absent and llama.cpp source build is the next intended path.

### Phase 3 -- llama.cpp Build/Install Probe

Goal:

- confirm the direct llama.cpp path is viable on this DGX host.

Preferred shape:

- clone/build in a non-system path.
- build CUDA-enabled llama.cpp for DGX Spark.
- record build commit, CMake options, CUDA version, and generated binary path.
- do not install system-wide unless a separate GO approves it.

Do not:

- reuse HP binary path `C:/github/llama-cpp-runtime/...`.
- reuse HP `Vulkan0` args.
- assume Windows executable names.
- load a large model in this phase.

Stop if:

- build fails due ARM64/CUDA compatibility.
- the only workaround would require global system changes.
- the binary path cannot be captured reproducibly.

### Phase 4 -- No-Endpoint Tiny Serving Probe

Goal:

- prove `llama-server` starts, answers a tiny synthetic request, and shuts down
  cleanly on DGX.

Model policy:

- do not use the official NVIDIA Qwen3.6-35B example for the first bootstrap
  smoke unless the user explicitly approves the larger download.
- prefer a small public GGUF for the first serving smoke, with filename, source,
  byte size, and SHA256 recorded.
- if no small GGUF is approved, stop after build/toolchain evidence and defer
  serving smoke.

Request policy:

- synthetic non-PHI prompt only.
- one `/v1/chat/completions` request.
- no `/explain`.
- no EMR harness.
- no shim.
- no C1/RA cases.
- no raw model output body in relay.

Pass requires:

- selected model file exists and hash is recorded.
- `llama-server` health endpoint or equivalent readiness check passes.
- one synthetic request returns HTTP 200.
- response has non-empty final content.
- PHI-like scan on the response metadata/body used for pass/fail is 0.
- server shutdown is explicit.
- final process/port check is clean.

Stop if:

- the model cannot be downloaded or verified.
- `llama-server` exits early.
- the response is reasoning-only or invalid for the tiny contract.
- any PHI-like hit appears.
- final process/port cleanup fails.

## Proposed Evidence Packet

The DGX bootstrap artifact should be metadata-first.

Suggested local artifact shape, pending artifact-repo decision:

```text
results/dgx_spark_bootstrap_probe_<timestamp>/
  dgx_spark_bootstrap_probe_results.json
  dgx_spark_bootstrap_probe_summary.md
  llama_server_stdout.txt        # only if tiny smoke is run
  llama_server_stderr.txt        # only if tiny smoke is run
```

Do not publish this into `hpz2-run-artifacts`.

Until a DGX artifact repo exists, the first run may write a local-only artifact
and then stop for Main PC review.

Minimum JSON fields:

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

## Runtime Boundary

The bootstrap probe must not use:

- HP Z2 model labels.
- `--confirm-hpz2`.
- `hpz2-run-artifacts` as default output.
- Windows paths.
- PowerShell preflight.
- `Vulkan0`.
- LM Studio model paths.
- HP SSH alias or IP.
- HP shim assumptions.

The bootstrap probe may use:

- SSH to DGX Spark after host identity is verified.
- Linux shell commands.
- CUDA-enabled llama.cpp.
- a small synthetic non-PHI prompt.
- local metadata artifact output.

## Relationship To Existing Project Runners

Do not patch `tools/hpz2_llamacpp_h2_endpoint_runner.py` for DGX first.

Recommended sequence remains:

1. DGX bootstrap probe.
2. DGX host profile design.
3. direct output-contract retarget.
4. synthetic bridge retarget.
5. C1 endpoint-replay candidate retarget.
6. vLLM throughput/model-ranking lane only after structural DGX baselines pass.

## vLLM Position

vLLM is not the first bootstrap path for this project.

Use vLLM later if the project needs:

- higher concurrency.
- larger NVFP4/FP8 model serving.
- throughput telemetry.
- OpenAI-compatible serving under load.

Do not use vLLM for the first bootstrap because it adds:

- Docker/container dependency.
- ARM64-specific build/runtime constraints.
- CUDA 13 version sensitivity.
- unified-memory headroom tuning.
- model-specific parser/quant settings.

## Acceptance Criteria For The Plan

This plan is acceptable if it:

- keeps DGX bootstrap separate from endpoint replay.
- keeps HP artifacts and labels as legacy-only.
- avoids `hpz2-run-artifacts` for DGX output by default.
- captures enough host/toolchain/runtime metadata to support a later host
  profile.
- prevents large model downloads before storage policy is decided.
- keeps `/explain` blocked.
- keeps raw model output out of relay.
- names host-specific next GO phrases.

## Next Gates

Source closeout:

```text
Main PC local-llm-eval DGX Spark ASUS bootstrap probe plan review/commit/push GO
```

If committing is deferred, relay closeout after source commit remains separate:

```text
Main PC local-llm-eval DGX Spark ASUS bootstrap probe plan relay update GO
```

After the device arrives and this plan is committed/reviewed:

```text
DGX Spark local-llm-eval llama.cpp bootstrap probe GO
```

Librarian backup remains a separate batched maintenance gate.
