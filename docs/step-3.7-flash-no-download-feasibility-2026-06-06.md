---
id: step-3.7-flash-no-download-feasibility-2026-06-06
project: local-llm-eval
type: feasibility-memo
status: draft
created: 2026-06-06
updated: 2026-06-06
scope: Main PC no-download feasibility review for StepFun Step-3.7-Flash as a separate HP Z2 large-MoE side track
related:
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - docs/hpz2-phase2-ladder-progress-v0.1.md
  - docs/rag_aware_eval_design_r0.md
  - prompts/rag_aware_eval_set_v0.1.json
---

# Step-3.7-Flash No-Download Feasibility Memo

## Project Goal Check

- Direct value: preserve a plausible large-MoE local candidate without mixing it
  into the active H2 C1 retrieval/citation gate.
- Classification: maintenance / future feasibility intake.
- Narrower scope: document-only source review and fit estimate. No HP command,
  no weight download, no model execution, no `/explain`, no EMR write, no
  commit/push authorization by this memo.

## Short Verdict

Step-3.7-Flash should remain in scope as a separate HP Z2 128GB-class
large-MoE feasibility side track.

User-reported HP hardware baseline for this side track: HP Z2 has 128 GB RAM,
with current VRAM allocation set to 96 GB. Treat this as the standing planning
assumption for future sessions; the HP preflight should verify live free disk,
free RAM, allocation state, and loaded-model/process state rather than asking
the user to restate the hardware class.

The old fixed 71 GB cutoff should not block it. The right decision point is a
model-specific fit preflight: quant size, active-parameter profile, backend
support, current HP disk, current HP RAM pressure, context length, KV-cache
footprint, and whether the tested backend can actually load this architecture.

This memo does not prove that HP Z2 can run it. The evidence supports only this
conditional path:

```text
Main PC no-download memo
  -> HP Z2 no-download fit preflight
  -> StepFun branch/build preflight
  -> quant selection review
  -> explicit download GO
  -> dry-load / tiny synthetic smoke
```

2026-06-06 HP no-download fit preflight result: HP resource state supports
continuing the side track, but not with `Q3_K_M` as the first dry-load target.
The first realistic load-feasibility probe is now `IQ3_XXS`, conditional on a
separate StepFun llama.cpp branch/build preflight. `Q3_K_M` and larger quants
should be deferred until a smaller quant proves the runtime path.

## Source Snapshot

Verified from public sources on 2026-06-06, without downloading model weights:

- The StepFun / Hugging Face model card describes Step-3.7-Flash as a
  198B-parameter sparse MoE vision-language model with a 196B language backbone
  and 1.8B vision encoder.
- The same primary source says it activates about 11B parameters per token,
  supports a 256k context window, and exposes low / medium / high reasoning
  levels.
- License is Apache-2.0.
- StepFun lists local deployment support through vLLM, SGLang, Transformers,
  and llama.cpp.
- StepFun's llama.cpp instructions point to a StepFun fork / `step3.7` branch,
  not merely the existing local HP llama.cpp baseline.
- The official GGUF repo provides BF16, Q8_0, Q4_K_S, IQ4_XS, Q3_K_L, Q3_K_M,
  IQ3_XXS, and a separate 4 GB multimodal projector.
- The official GGUF card says Q4 and below can be hosted on 128 GB unified
  memory class machines, but that claim is not the same as a verified HP Z2
  Windows/Vulkan result.

References:

- https://huggingface.co/stepfun-ai/Step-3.7-Flash
- https://huggingface.co/stepfun-ai/Step-3.7-Flash-GGUF
- https://github.com/stepfun-ai/Step-3.7-Flash

## Quant Fit Estimate

This table is a planning estimate only. It assumes the user-reported HP 128 GB
RAM / 96 GB VRAM allocation baseline, but does not include current HP OS memory
pressure, exact free RAM, disk state, context/KV-cache growth, or Windows Vulkan
backend quirks.

| Quant | File size | Initial treatment | Rationale |
|---|---:|---|---|
| BF16 | 394 GB | no-go for HP local smoke | Full precision is outside the practical local envelope. |
| Q8_0 | 209 GB | no-go for HP local smoke | Too large before runtime and KV overhead. |
| Q4_K_S | 112 GB | high-pressure candidate only after smaller quant success | Official balanced quant, but the source lists about 7 GB runtime overhead and 120 GB minimum unified/VRAM for the Q4-class path. HP margin may be too small once OS/KV/cache are counted. |
| IQ4_XS | 105 GB | high-pressure candidate only after smaller quant success | Slightly smaller than Q4_K_S; still close to the 128GB-class edge. |
| Q3_K_L | 103 GB | high-pressure candidate only after smaller quant success | Aggressive size reduction but still near Q4-class pressure. |
| Q3_K_M | 94 GB | deferred / too tight for first dry-load after HP preflight | File size is about 87.4 GiB binary before runtime and KV overhead. Against the observed 90.96 GiB Vulkan budget, the remaining margin is too small for a first probe. Revisit only after a smaller quant proves the path. |
| IQ3_XXS | 76 GB | conditional first load-feasibility probe | File size is about 70.6 GiB binary. It has the best first-fit margin under the observed HP Vulkan budget, but should answer only "can this class load/run at all," not final quality. |
| mmproj F16 | 4 GB | skip for first text-only smoke | `/explain` evaluation is text-only. Vision projector is unnecessary for the first local feasibility pass. |

## HP Z2 No-Download Fit Preflight Result

Preflight date: 2026-06-06. Host access used `ssh test@192.168.68.50`; the
`hpcheck` alias timed out. Scope stayed no-download and no-execution: no model
weights were downloaded, no model was loaded, no dry-load was attempted, no
`/explain` call was made, and no EMR or artifact repo write was performed.

Observed HP state:

- Machine: `HP Z2 Mini G1a Workstation Desktop PC`.
- Windows visible RAM after the 96 GB VRAM allocation: total `31.78 GiB`,
  free `20.07 GiB`.
- GPU: `AMD Radeon(TM) 8060S Graphics`, integrated Vulkan device.
- Vulkan device-local heap: size `95.75 GiB`, budget `90.96 GiB`, usage `0`.
- Disk free: C: `589.30 GiB`, D: `346.06 GiB`, E: `953.74 GiB`.
- `lms ps --json` returned `[]`; no LM Studio model was loaded.
- LM Studio server was listening on port `1234` with PID `45180`.
- Ports `18080` and `18081` had no listeners.
- No stale `llama-server` or shim process was found.
- HP `local-llm-eval` checkout was clean/synced at `f4869d6`; it was not
  pulled during this gate.

Runtime evidence:

- Existing local llama.cpp runtime:
  `C:\Github\llama-cpp-runtime\b9333\llama-server.exe`, version
  `9333 (35c9b1f39)`.
- LM Studio Vulkan backends inspected: 2.16.0 build `5306f4b` and 2.18.0 build
  `06d26df`.
- `C:\Github\llama-cpp-runtime` is not a git repo, and no checked StepFun
  branch/source checkout was found in the inspected paths.

Fit verdict:

- Disk capacity: PASS.
- Loaded-model/process/port state: PASS.
- 96 GB VRAM allocation premise: PASS by live Vulkan heap evidence.
- `Q3_K_M`: DEFER / too tight for first dry-load under the observed
  `90.96 GiB` device-local budget.
- `IQ3_XXS`: CONDITIONAL first candidate after StepFun branch/build preflight.
- `Q4_K_S`, `IQ4_XS`, and `Q3_K_L`: not first candidates under the current
  heap budget.
- StepFun llama.cpp branch/build support on HP remains `needs evidence`.

## HP Z2 Fit Considerations

The target side track should not assume the existing H2 C1 runtime profile will
work unchanged. Step-3.7-Flash needs its own fit preflight because:

- the local HP llama.cpp baseline was built around currently installed Qwen,
  Granite, GPT-OSS, and related candidates, not Step-3.7;
- StepFun's documented llama.cpp path uses a StepFun fork / branch;
- HP hardware class is no longer an open question for planning: use the
  user-reported 128 GB RAM / 96 GB VRAM allocation baseline, then verify live
  free resources during HP preflight;
- the official 256k context capability is not required for `clinical-assist`
  `/explain`, and starting at 256k would waste the first fit test;
- the first HP test should use a small context such as 8k or 16k, then expand
  only if dry-load and tiny smoke are stable;
- model file size alone is not enough because KV cache, runtime overhead,
  backend allocation, and OS memory pressure decide the real fit;
- the 4 GB multimodal projector should be excluded from the first text-only
  path.

## Recommended Gate Sequence

1. `Main PC local-llm-eval Step-3.7-Flash feasibility memo review GO`
   - Review this memo only.
   - No HP command, no download, no model execution.

2. `Main PC local-llm-eval Step-3.7-Flash feasibility memo commit GO`
   - Commit this document if accepted.
   - No HP command, no download, no model execution.

3. `HP Z2 local-llm-eval Step-3.7-Flash no-download fit preflight GO`
   - DONE on 2026-06-06.
   - Result: HP resource state allows continuing, but `Q3_K_M` is too tight as
     the first dry-load target. `IQ3_XXS` is the conditional first probe.
   - StepFun branch/build support remains `needs evidence`.

4. `HP Z2 local-llm-eval Step-3.7-Flash StepFun llama.cpp branch/build preflight GO`
   - Verify whether the StepFun llama.cpp branch can be obtained/built or
     otherwise matched by an existing runtime.
   - No model download and no model execution.

5. `Main PC local-llm-eval Step-3.7-Flash quant selection review GO`
   - Current default after HP preflight: `IQ3_XXS` as load-feasibility probe
     only.
   - Reconsider `Q3_K_M` only after StepFun branch/build evidence and a smaller
     quant path succeed.

6. Later, only after explicit user approval:
   `HP Z2 local-llm-eval Step-3.7-Flash IQ3_XXS dry-load GO`
   - This would be the first gate that downloads a selected quant and attempts
     dry-load/tiny synthetic smoke.

## Do Not Conclude Yet

The following remain `needs evidence`:

- current HP Z2 free disk and free RAM at the moment of any future test;
- whether HP's Windows/Vulkan stack can use the StepFun llama.cpp branch
  cleanly;
- actual load memory at 8k / 16k context;
- output quality under Korean clinical explanation prompts;
- citation discipline against the RAG-aware C1 lane;
- whether Step-3.7's reasoning-level controls are usable and stable through the
  selected backend.

## Relationship to Active H2 C1 Work

This is not a replacement for the active H2 C1 retrieval-only probe. It is a
future side track for large-MoE feasibility.

Active H2 C1 work remains:

```text
HP Z2 local-llm-eval H2 C1 retrieval-only probe pull/verify GO
```

Step-3.7 should only proceed when the user wants a separate large-MoE feasibility
lane and is willing to spend disk/time on a later explicit download/dry-load
gate.
