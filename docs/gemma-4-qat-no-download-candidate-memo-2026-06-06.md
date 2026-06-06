---
id: gemma-4-qat-no-download-candidate-memo-2026-06-06
project: local-llm-eval
type: memo
status: draft
created: 2026-06-06
scope: Main PC no-download candidate memo for Gemma 4 QAT 12B/26B/31B
related:
  - docs/hpz2-phase2-l2-shortlist-lock-2026-05-27.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
sources:
  - https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/
  - https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/
  - https://lmstudio.ai/models/google/gemma-4-12b-qat
  - https://lmstudio.ai/models/google/gemma-4-26b-a4b-qat
  - https://lmstudio.ai/models/google/gemma-4-31b-qat
  - https://huggingface.co/lmstudio-community/gemma-4-12B-it-QAT-GGUF
  - https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF
  - https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF
---

# Gemma 4 QAT No-Download Candidate Memo

## Project Goal Check

- direct value: decide whether the newly available Gemma 4 QAT models deserve a
  local-llm-eval candidate lane without mixing them into the active H2 C1
  citation/retrieval gate.
- classification: `maintenance` / candidate intake with future evaluation
  value.
- narrower scope: no-download memo only. No model download, HP/subpc command,
  dry-load, model execution, `/explain`, EMR write, config mutation, commit,
  push, relay update, or backup is authorized by this file.

## Verdict

Gemma 4 QAT should be considered, but the candidates should be split by host
class.

| Model | 16 GB VRAM PC fit verdict | local-llm-eval role |
|---|---|---|
| Gemma 4 12B QAT | **GO for no-download fit preflight** | best 16 GB VRAM candidate; small local baseline/challenger |
| Gemma 4 26B A4B QAT | **CONDITIONAL stretch** | fit-preflight only; likely tight at useful context lengths |
| Gemma 4 31B QAT | **NO for 16 GB VRAM first pass** | HP Z2/reference candidate only |

This does not promote any Gemma 4 QAT model into the current Primary4 endpoint
replay shortlist. It only creates a candidate intake decision surface.

## Evidence Snapshot

Public-source no-download facts checked on 2026-06-06:

- Google introduced Gemma 4 12B as a 12B-parameter model intended for local
  devices with 16 GB VRAM or unified memory and released it under Apache 2.0.
- Google's QAT announcement frames Gemma 4 QAT as quantization-aware trained
  models intended to preserve quality better than post-training quantization at
  lower memory.
- LM Studio lists the user-provided Gemma 4 QAT entries with installable GGUF
  variants and minimum memory estimates.

Observed model-size surface:

| Model page | LM Studio min memory | HF GGUF Q4_0 size | Practical note |
|---|---:|---:|---|
| `gemma-4-12b-qat` | 7.0 GB | 6.98 GB | large headroom on 16 GB VRAM before KV/cache/context |
| `gemma-4-26b-a4b-qat` | 16.0 GB | 14.4 GB | may load, but 16 GB VRAM headroom is narrow |
| `gemma-4-31b-qat` | 19.0 GB | 17.7 GB | exceeds 16 GB first-pass VRAM budget |

The fit estimates are not execution evidence. They do not prove throughput,
context stability, citation quality, structured output reliability, or endpoint
readiness.

## Candidate Interpretation

### Gemma 4 12B QAT

This is the most relevant new candidate for a 16 GB VRAM PC.

Reasons:

- Q4_0 GGUF footprint is small enough to leave meaningful room for runtime
  overhead and KV cache.
- It is specifically positioned for local 16 GB-class hardware.
- It is small enough to test as a low-cost local RAG helper or fallback without
  competing with HP Z2 large-model lanes.

Recommended first role:

```text
16GB local baseline/challenger for output-contract and RAG-aware smoke lanes
```

### Gemma 4 26B A4B QAT

This is a stretch candidate for a 16 GB VRAM PC, not a default.

Reasons:

- Q4_0 file size is close to the whole 16 GB VRAM budget.
- A4B active-parameter behavior may help runtime speed, but memory fit still
  needs live preflight because KV/cache/context can push the load over budget.
- It may be more appropriate for HP Z2 or for a short-context subpc dry-load
  probe than for a stable 16 GB endpoint lane.

Recommended first role:

```text
conditional no-download fit estimate, then dry-load only if live VRAM/free RAM/process state is favorable
```

### Gemma 4 31B QAT

This should not be treated as the 16 GB VRAM target.

Reasons:

- Q4_0 size is above 16 GB before runtime overhead.
- LM Studio's minimum memory estimate is above 16 GB.
- It is more consistent with HP Z2/reference evaluation than with subpc
  16 GB VRAM probing.

Recommended first role:

```text
HP Z2 reference candidate only, after higher-priority H2 C1 validity gates
```

## Suggested No-Download Next Gates

Main PC memo/decision gate:

```text
Main PC local-llm-eval Gemma 4 QAT candidate memo review GO
```

16 GB VRAM PC preflight gate, if the 16 GB machine is the intended target:

```text
subpc local-llm-eval Gemma 4 12B QAT no-download fit preflight GO
```

HP Z2 reference-fit gate:

```text
HP Z2 local-llm-eval Gemma 4 QAT no-download fit preflight GO
```

Any download, dry-load, model run, `/explain`, endpoint replay, or config
mutation remains a separate explicit GO.
