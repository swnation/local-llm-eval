---
id: local-model-community-recipe-research-memo-2026-06-07
project: local-llm-eval
type: research-memo
status: draft
created: 2026-06-07
scope: Main PC web research memo for community local-model runtime recipes relevant to HP Z2 / Strix Halo-class local LLM evaluation
related:
  - docs/gemma-4-qat-no-download-candidate-memo-2026-06-06.md
  - docs/gemma-4-qat-hpz2-dry-load-result-memo-2026-06-06.md
  - docs/step-3.7-flash-no-download-feasibility-2026-06-06.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
sources:
  - https://github.com/Gygeek/Framework-strix-halo-llm-setup
  - https://github.com/hogeheer499-commits/strix-halo-guide
  - https://github.com/pablo-ross/strix-halo-gmktec-evo-x2/blob/main/QWEN3-CODER-30B_BENCHMARK.md
  - https://github.com/nabe2030/gemma4-vs-qwen35-evo-x2
  - https://github.com/MaxusAI/ryzen-ai-max-rocm-ollama-testbench
  - https://strixhalo.wiki/AI/AI_Capabilities_Overview
  - https://www.fixnum.org/2025-09-11-llama-swap-on-strix-halo/
  - https://github.com/stepfun-ai/Step-3.7-Flash
  - https://lmstudio.ai/models/google/gemma-4-12b-qat
  - https://lmstudio.ai/models/google/gemma-4-26b-a4b-qat
  - https://lmstudio.ai/models/google/gemma-4-31b-qat
  - https://qwen.readthedocs.io/en/latest/run_locally/lmstudio.html
  - https://github.com/ggml-org/llama.cpp/issues/16575
  - https://github.com/ggml-org/llama.cpp/discussions/10879
  - https://github.com/ggml-org/llama.cpp/discussions/21338
  - https://github.com/ggml-org/llama.cpp/discussions/21480
  - https://github.com/ggml-org/llama.cpp/issues/20354
  - https://github.com/tfriedel/qwen3.6-rtx3090-lab/blob/main/GEMMA_FINDINGS.md
  - https://github.com/test1111111111111112/llama-cpp-turboquant-gemma4
---

# Local Model Community Recipe Research Memo

## Project Goal Check

- direct value: collect external recipe patterns that can improve HP Z2
  local-model fit, load, and prompt-smoke planning without running new models.
- classification: `documentation` / modelops research.
- narrower scope: web research memo only. No HP command, no model download, no
  model load, no prompt/API call, no `/explain`, no EMR write/reindex, no
  artifact mutation, no commit/push authorization.

Research date: 2026-06-07.

## Short Verdict

The useful pattern from current public recipes is not a single magic setting.
It is a stack choice:

```text
latest llama.cpp build
  + Vulkan/RADV or carefully verified ROCm path
  + full GPU-addressable offload
  + mmap disabled for large models
  + model-specific reasoning/template/cache controls
  + small-context dry-load before endpoint claims
```

For our HP Z2 lane, this supports three practical decisions:

1. Keep LM Studio as the low-friction management lane for Gemma QAT and manual
   inspection.
2. Keep direct llama.cpp Vulkan as the performance/control lane for Qwen MoE,
   StepFun, and any endpoint-style serving work.
3. Treat Gemma 4 as a model-specific risk lane: QAT sizes look attractive, but
   thinking/template behavior, high-context repetition, and prompt-cache memory
   need explicit small-context smoke evidence before ranking or endpoint use.
   A later Chrome sweep found one strong Strix Halo/EVO-X2 benchmark where
   Gemma 4 26B-A4B Q4_K_M is favored over Qwen 3.5-35B-A3B Q4_K_M on
   Vulkan/RADV; treat that as a reason to run bounded prompt smoke, not as
   endpoint readiness.

This memo does not change the current Primary4 shortlist and does not prove any
new model quality result.

## Source Coverage

| Source class | Status | Use in this memo |
|---|---|---|
| GitHub repos / GitHub issues | usable | primary evidence for recipes, flags, caveats, and model-specific failure modes |
| LM Studio / Qwen docs | usable | model-page memory estimates and LM Studio import/serve workflow |
| Strix Halo Wiki / public blog | usable but secondary | environment and backend-selection context |
| Arca Live | blocked in Chrome sweep | Chrome browser policy rejected direct `https://arca.live/b/ai`; do not route around it from this tool session |

Arca Live should not be treated as negative evidence. It is absent from this
draft because the current search path did not produce usable pages and the
requested Chrome route explicitly blocked direct Arca board access.

## Chrome Targeted Sweep Addendum

The Chrome pass added two useful GitHub sources and two supporting llama.cpp
threads/issues.

### Gemma 4 26B-A4B vs Qwen 3.5-35B-A3B On EVO-X2

The `nabe2030/gemma4-vs-qwen35-evo-x2` repo directly compares Gemma 4
26B-A4B Q4_K_M and Qwen 3.5-35B-A3B Q4_K_M on AMD Ryzen AI Max+ 395 /
Radeon 8060S with llama.cpp Vulkan/RADV.

Useful recipe facts from that repo:

- Host: 128 GB LPDDR5X unified memory, Ubuntu 25.10, RADV GFX1151, llama.cpp
  `b8672`.
- Build: `cmake -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release`.
- Raw benchmark command: `llama-bench -m <model.gguf> -ngl 99 -fa 1 -mmp 0
  -p 2048 -n 32 -ub 2048`.
- Prompt-smoke server recipe includes `--jinja --reasoning off --temp 1.0
  --top-p 0.95 --top-k 64`.
- Reported `llama-bench` result: Gemma 4 26B-A4B Q4_K_M `pp2048 1348 t/s`,
  `tg32 65.4 t/s`; Qwen 3.5-35B-A3B Q4_K_M `pp2048 730 t/s`,
  `tg32 72.9 t/s`.
- The repo attributes Gemma's prompt-processing advantage to not using
  GatedDeltaNet, while Qwen has slightly faster generation due to fewer active
  parameters.
- The repo reports the earlier Gemma `<unused49>` flood as F16 GGUF-specific,
  with Q4_K_M working correctly in that benchmark.

Interpretation for us:

- This is the strongest public evidence found so far that Gemma 4 26B-A4B is
  not merely a "fits in memory" candidate on Strix Halo-class hardware.
- It supports prioritizing a Gemma 4 26B-A4B text-only prompt smoke after
  review, while keeping the result outside endpoint/model-ranking lanes.
- It does not override our HP dry-load evidence, because the repo uses Linux
  RADV and Q4_K_M while our current HP file is LM Studio QAT Q4_0 on Windows.

### ROCm/Ollama Validation Stack

The `MaxusAI/ryzen-ai-max-rocm-ollama-testbench` repo is a Docker stack for
Ollama built against ROCm 7.2.2 with native gfx1151 support. It is less directly
applicable to our current Windows/LM Studio path, but it is useful as a failure
taxonomy for future Linux/ROCm experiments.

Relevant failure checks:

- silent CPU fallback can appear as `library=cpu` and `total_vram="0 B"`.
- hard GPU page faults can occur during rocBLAS first dispatch.
- the repo separates MES firmware, IOMMU passthrough, rocBLAS pruning, native
  gfx1151 build support, and Linux permissions as distinct root causes.
- it uses a validation ladder (`make validate`, `make validate-full`) rather
  than treating one successful response as proof of GPU execution.

Interpretation for us:

- Do not switch the HP project lane from Windows Vulkan/LM Studio to ROCm based
  on this source.
- If we later open a Linux/ROCm lane, copy the validation-ladder style:
  prove firmware, permissions, container, GPU discovery, and model inference
  separately.

## Recipe Patterns Found

### 1. Strix Halo / 128GB Unified Memory Setup

The strongest GitHub setup guide treats Strix Halo as a GTT/unified-memory
platform rather than a fixed-VRAM discrete GPU. It recommends making most of
the 128 GB system memory available to the GPU-addressable path, disabling mmap
for GPU inference, and fully offloading layers.

Relevant public recipe details:

- BIOS/kernel examples target very large GTT allocation, for example
  `amdgpu.gttsize=117760` on Linux for about 115 GB GPU-addressable memory.
- `--no-mmap` is treated as important for large model GPU loading.
- `-ngl 99` / high `-ngl` is used to force full offload.
- `llama-bench` examples use `-mmp 0` as the benchmark equivalent of disabling
  mmap.

Applicability to our HP Z2:

- Our HP Z2 standing baseline is 128 GB RAM with 96 GB VRAM allocation, but it
  is Windows/LM Studio/Vulkan-oriented, not the same Linux GTT path.
- The recipe supports our existing policy: do not ask the user to restate the
  hardware class; verify live free disk/RAM/VRAM/process state per gate.
- It also supports keeping the 71 GB fixed cutoff retired. Fit should be
  model/backend-specific.

### 2. Direct llama.cpp Vulkan/RADV Often Beats Wrapper Convenience

The most relevant Strix Halo benchmark repo reports that recent direct
llama.cpp Vulkan/RADV builds can substantially outperform easy wrappers for
generation-heavy chat/coding workloads.

Observed patterns:

- Direct `llama-bench` rows for Qwen-family MoE models are reported in the
  60-100 tokens/s class depending on model, quant, build, and host state.
- The same repo treats exact build version and raw CSV/log evidence as core
  reproducibility anchors.
- It reports that updating llama.cpp gave larger MoE gains than batch/ubatch
  sweeps in that test series.
- A representative direct server command uses:

```text
AMD_VULKAN_ICD=RADV ./build-vulkan/bin/llama-server \
  -m <model.gguf> \
  -ngl 999 -fa --no-mmap -c 8192 \
  --host 0.0.0.0 --port 8080
```

Applicability to our HP Z2:

- This reinforces the current project split: LM Studio is secondary/manual;
  direct llama.cpp remains the right control/performance lane for endpoint
  experiments.
- Before importing these numbers, we must not compare raw community `tg128`
  rows with our `/explain` endpoint results. Our endpoint has retrieval,
  structured-output, prompt, citation, and safety lanes.
- For future HP direct-run planning, build hash, backend, driver, command
  flags, context length, and raw run artifact must be captured.

### 3. Vulkan vs ROCm Is Workload-Specific

The public recipes do not converge on "ROCm always wins" or "Vulkan always
wins." The more useful rule is:

- Vulkan/RADV is repeatedly favored for single-user generation-heavy GGUF chat
  on Strix Halo-class systems.
- ROCm/HIP may win prompt-processing / prefill-heavy rows, especially with
  rocWMMA or hipBLASlt paths.
- Container routes such as kyuz0 toolboxes are repeatedly referenced as a way
  to get current llama.cpp/ROCm/Vulkan builds without hand-maintaining the full
  stack.
- The llama.cpp Vulkan performance discussion asks contributors to record the
  exact git hash and Vulkan info string with `llama-bench` results; it also
  notes `RADV_PERFTEST=nogttspill` as a relevant RADV-specific knob.
- The GatedDeltaNet issue for gfx1151 reports that Qwen3.5 GDN models can fall
  back to CPU in Vulkan or underperform through HIP, while non-GDN models avoid
  that specific bottleneck.

Applicability to our HP Z2:

- Our current Windows HP path should keep Vulkan/LM Studio/direct llama.cpp as
  the first practical lane.
- ROCm should be a separate backend experiment, not silently substituted into
  the active H2 C1 or Gemma QAT lanes.
- If long-context prefill becomes the bottleneck, a Linux/ROCm comparison can
  be justified, but that is a separate host/backend gate.

### 4. Windows 96GB VRAM/VGM Has a Specific Large-Load Caveat

A llama.cpp issue reports a Strix Halo-like Windows setup with 128 GB RAM and
96 GB VRAM/VGM encountering a load failure above roughly 64 GB effective VRAM
use in LM Studio/Vulkan. The issue is closed and not proof of current HP
behavior, but it is directly relevant because the hardware class and 96 GB
allocation resemble our HP planning baseline.

Applicability to our HP Z2:

- For models above roughly 64 GiB device-local pressure, do not rely on the
  configured 96 GB allocation alone.
- Require live dry-load evidence with exact model, context, backend, driver,
  process state, and post-unload check.
- This specifically affects StepFun IQ3/Q3/Q4 and other 70B-120B-class probes
  more than the already dry-loaded Gemma 31B/26B QAT files.

### 5. LM Studio Import/Serve Recipes Are Useful For Management, Not Final Eval

The Qwen local docs describe LM Studio as supporting GGUF and MLX model formats,
download/search inside the app, `lms import <path/to/model.gguf>`, and local API
serving through `lms server start`. LM Studio's Gemma 4 QAT pages also expose
model-page defaults and memory estimates:

| Model | LM Studio min system memory | Model-page defaults / notes |
|---|---:|---|
| Gemma 4 12B QAT | 7 GB | thinking default true; temp 1; top-k 64; top-p 0.95 |
| Gemma 4 26B A4B QAT | 16 GB | thinking default true; temp 1; top-k 64; top-p 0.95 |
| Gemma 4 31B QAT | 19 GB | thinking default true; temp 1; top-k 64; top-p 0.95 |

Applicability to our HP Z2:

- This validates the approach already used on HP: import/index model files,
  dry-load with bounded context, then unload and confirm `lms ps []`.
- The 26B A4B symbolic-link import behavior we observed is consistent with the
  need to make LM Studio index local GGUFs rather than assuming any downloaded
  file path is loadable by key.
- LM Studio defaults are not endpoint-eval defaults. For structured clinical
  output, we still need explicit prompt smoke and output-contract validation.

### 6. Gemma 4 Needs Model-Specific Runtime Controls

Gemma 4 community/issue evidence is mixed:

- Older LM Studio/GGUF paths failed when runtime did not recognize the
  `gemma4` architecture. This is a version-support issue, not a model-quality
  issue.
- llama.cpp discussion evidence shows Gemma 4 thinking/template behavior can
  produce `<unused49>` loops when thinking is active or mishandled.
- At least one workaround path uses `--reasoning off`; another reports that
  some enable-thinking flags are ignored or model/build-dependent.
- Separate discussion notes that Gemma 4 prompt checkpoints can consume far
  more RAM than Qwen MoE at the same checkpoint size; maintainer reply says the
  higher pressure is expected for Gemma 4 architecture, with cache/checkpoint
  options available.

Applicability to our HP Z2:

- First Gemma prompt smoke should be text-only, low-risk, and short-context.
- Do not enable `mmproj` or multimodal mode in the first clinical/RAG lane.
- Prefer an explicit "thinking off" path if the backend exposes it; record
  whether the backend actually honors it.
- For direct llama.cpp Gemma tests, include cache/checkpoint settings in the
  logged recipe, for example keep our existing `--cache-ram 0` /
  `--ctx-checkpoints 0` stance unless a specific Gemma checkpoint experiment is
  authorized.
- Treat any repeated token flood, whitespace-only output, or reasoning-only
  output as a runtime/template failure lane, not a semantic model ranking.

### 7. Qwen MoE Recipes Are Strong But Need Architecture Labels

Multiple Strix Halo community repos emphasize Qwen 30B/35B MoE recipes:

- Qwen3-Coder 30B A3B Q4-class GGUF with all layers offloaded and mmap disabled
  is reported around interactive coding speed on Strix Halo-class systems.
- A GMKtec EVO-X2 ROCm/rocWMMA server API benchmark for Qwen3-Coder 30B Q4_K_M
  reports about 70-71 tokens/s generation with `--no-mmap`, 8192 context, and
  2 parallel slots.
- The higher-performance Strix Halo guide reports stronger direct Vulkan/RADV
  rows, but also warns that exact build, quant, host state, and benchmark
  method matter.
- Qwen3.5 GatedDeltaNet variants are a special caveat on gfx1151: one llama.cpp
  issue reports Vulkan CPU fallback for GDN and ineffective HIP acceleration on
  RDNA 3.5.

Applicability to our HP Z2:

- Qwen MoE remains important, but it should be split by architecture. Qwen
  Coder/Next-style rows are not interchangeable with Qwen3.5 GDN rows.
- The Chrome sweep weakens the earlier simple "Qwen stronger than Gemma" view:
  Gemma 4 26B-A4B now has direct Strix Halo Vulkan evidence that is relevant to
  our HP Gemma lane.
- This does not override our current H2 C1 blockers. Retrieval/citation and
  output-contract evidence still decide endpoint readiness.

### 8. Step-3.7-Flash Recipe Confirms Separate Large-MoE Track

The StepFun repo explicitly describes Step-3.7-Flash as local-deployable on
128 GB unified-memory-class systems and lists llama.cpp support. It also says
the llama.cpp route uses StepFun's fork/branch and lists GGUF sizes:

| Quant | Listed size | Memo implication |
|---|---:|---|
| Q4_K_S | 111.5 GB | too tight for our first HP dry-load |
| IQ4_XS | 104.99 GB | too tight until smaller quant proves runtime path |
| Q3_K_L | 102.5 GB | still high-pressure |
| mmproj FP16 | 3.97 GB | skip first text-only probe |

The repo lists about 7 GB runtime overhead and 120 GB minimum unified memory /
VRAM for the Q4-class llama.cpp path.

Applicability to our HP Z2:

- This supports the earlier Step-3.7 conclusion: first realistic HP probe is a
  smaller quant such as `IQ3_XXS`, after StepFun branch/build preflight.
- Do not use StepFun Q4/IQ4 as the first proof of feasibility on the Windows
  96 GB allocation.
- Any StepFun run must remain outside the active H2 C1 retrieval/citation gate.

## Candidate Recipe Matrix For Our Work

| Candidate / family | Community recipe signal | First safe local-llm-eval action |
|---|---|---|
| Gemma 4 12B QAT | LM Studio page says 7 GB min memory; lower pressure | 16GB/subpc no-download fit preflight, then dry-load if desired |
| Gemma 4 26B A4B QAT | HP dry-load already succeeded at 4096; Chrome sweep found direct EVO-X2 Gemma 4 26B-A4B Q4_K_M Vulkan benchmark favoring it over Qwen3.5 in prompt processing and reasoning accuracy | HP text-only prompt smoke plan with thinking/template logging |
| Gemma 4 31B QAT | HP dry-load already succeeded at 4096; dense/ref candidate | HP text-only prompt smoke plan, no quality ranking yet |
| Qwen3-Coder 30B / Qwen3.6 35B MoE | strong Strix Halo recipe coverage, but split GDN vs non-GDN architecture before applying results | keep as external recipe family for future direct llama.cpp serving; avoid architecture-blind ranking |
| Qwen3-Next 80B | external direct Vulkan/RADV 80B-class success signal | no immediate action; possible HP reference lane after active blockers |
| gpt-oss-120b MXFP4 | external Strix Halo success signal, but large-load pressure | needs fresh HP fit/dry-load evidence before any endpoint use |
| Step-3.7-Flash | official 128GB-class local support but high memory pressure | StepFun branch/build preflight, then IQ3_XXS-only first probe |

## Proposed Recipe For Next HP Gemma Prompt Smoke

This is a planning sketch, not an execution authorization.

Preflight:

```text
confirm local-llm-eval HEAD
confirm C:/D:/E: free space
confirm lms ps []
confirm ports 18080/18081 and any LM Studio server port state
record LM Studio version / llama.cpp runtime if exposed
record model key and exact GGUF path/hash
```

Load:

```text
lms load <model-key> --identifier <stable-id> --gpu max --context-length 4096 --ttl 120 -y
```

Prompt smoke:

- text-only, no `mmproj`.
- one synthetic non-PHI prompt.
- record output channel behavior: final text vs reasoning-only vs repeated
  tokens vs whitespace.
- record whether thinking was enabled/disabled and whether the backend honored
  that setting.
- unload and verify `lms ps []`.

Pass condition:

```text
load ok
one text-only non-PHI prompt returns non-empty final answer
no repeated-token flood
no PHI-like output
unload ok
no runtime process remains
```

This still would not be endpoint readiness and would not authorize `/explain`.

## Open Questions

- Arca Live has not been incorporated as evidence. Chrome blocked direct Arca
  board access in this pass; use user-provided Arca links or a separate
  non-Chrome/manual evidence packet if those recipes should become durable
  evidence.
- Windows 96 GB VGM behavior above 64 GB needs current HP-specific live proof.
  Do not extrapolate Linux GTT success to Windows large-model success.
- Gemma 4 thinking/template controls are backend/build-dependent. The next
  prompt smoke should log exact runtime and settings before any qualitative
  interpretation.
- Community speed rows are mostly synthetic prompt or coding/chat rows. They
  should not be compared directly to our RAG-aware `/explain` endpoint lanes.

## Suggested Next Gates

Review this research memo:

```text
Main PC local-llm-eval local-model recipe community research memo review GO
```

If accepted, commit/push/relay:

```text
Main PC local-llm-eval local-model recipe community research memo commit push relay GO
```

Runtime planning after review:

```text
HP Z2 local-llm-eval Gemma 4 QAT text-only prompt smoke plan GO
```

Arca-specific follow-up if wanted:

```text
Main PC local-llm-eval user-provided Arca local-model recipe links review GO
```
