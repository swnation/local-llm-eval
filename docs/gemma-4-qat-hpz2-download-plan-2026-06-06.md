---
id: gemma-4-qat-hpz2-download-plan-2026-06-06
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-06
scope: HP Z2 download plan for Gemma 4 31B QAT and Gemma 4 26B A4B QAT, including mmproj files
related:
  - docs/gemma-4-qat-no-download-candidate-memo-2026-06-06.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - docs/hpz2-phase2-l2-shortlist-lock-2026-05-27.md
sources:
  - https://lmstudio.ai/models/google/gemma-4-31b-qat
  - https://lmstudio.ai/models/google/gemma-4-26b-a4b-qat
  - https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF
  - https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF
---

# Gemma 4 QAT HP Z2 Download Plan

## Project Goal Check

- direct value: prepare a bounded HP Z2 download plan for Gemma 4 31B QAT and
  Gemma 4 26B A4B QAT so later local testing can start from verified files.
- classification: `maintenance` / modelops candidate intake.
- narrower scope: plan only. No download, dry-load, model execution,
  llama-server/shim start, `/explain`, EMR write/reindex, config mutation,
  commit, push, relay update, or backup is authorized by this file.

## Decision

Download both text-model GGUF files and both `mmproj` files when a later
download GO is issued.

Rationale:

- The current local-llm-eval RAG lane is text-only, so `mmproj` will not be
  loaded for first text dry-load or endpoint checks.
- The user explicitly wants `mmproj` kept with the models.
- The extra disk cost is small on HP Z2: about 2.23 GiB for both `mmproj`
  files combined.

The recommended evaluation split remains:

- Gemma 4 31B QAT: HP Z2 quality/reference candidate.
- Gemma 4 26B A4B QAT: HP Z2 efficiency comparison candidate.
- Load only one model at a time.

## Current HP Z2 Preflight Snapshot

Checked on 2026-06-06 before writing this plan:

```text
host/user: hpcheck / hpcheck\test
local-llm-eval: HEAD == origin/main == c0722ccffb50f6186d24384726eeb0a517af603d
repo status: clean
visible RAM: total 31.78 GiB, free 20.24 GiB, used 36.31%
standing hardware baseline: 128 GB RAM with 96 GB VRAM allocation
disk free: C: 588.26 GiB, D: 362.57 GiB, E: 953.74 GiB
LM Studio loaded models: []
ports: 18080/18081 free; 1234 listening for LM Studio server
```

Interpretation:

- The HP Z2 has enough disk headroom to store both model bundles under the
  current LM Studio model root on `C:`.
- The download itself should not change loaded model state.
- Before the actual download, repeat this preflight because free disk/RAM and
  loaded model state are drift-prone.

## Files To Download

Destination root:

```text
C:\Users\test\.lmstudio\models\lmstudio-community\
```

31B bundle:

| File | URL | Bytes | GiB |
|---|---|---:|---:|
| `gemma-4-31B-it-QAT-Q4_0.gguf` | `https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF/resolve/main/gemma-4-31B-it-QAT-Q4_0.gguf` | 17,651,000,768 | 16.44 |
| `mmproj-gemma-4-31B-it-QAT-BF16.gguf` | `https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF/resolve/main/mmproj-gemma-4-31B-it-QAT-BF16.gguf` | 1,200,726,016 | 1.12 |

26B A4B bundle:

| File | URL | Bytes | GiB |
|---|---|---:|---:|
| `gemma-4-26B-A4B-it-QAT-Q4_0.gguf` | `https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF/resolve/main/gemma-4-26B-A4B-it-QAT-Q4_0.gguf` | 14,439,362,752 | 13.45 |
| `mmproj-gemma-4-26B-A4B-it-QAT-BF16.gguf` | `https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF/resolve/main/mmproj-gemma-4-26B-A4B-it-QAT-BF16.gguf` | 1,194,827,776 | 1.11 |

Total planned download size:

```text
34,485,917,312 bytes
32.12 GiB
```

## Proposed Download Order

Download in this order:

1. Gemma 4 31B QAT text model.
2. Gemma 4 31B QAT `mmproj`.
3. Gemma 4 26B A4B QAT text model.
4. Gemma 4 26B A4B QAT `mmproj`.

Reasoning:

- 31B is the primary HP candidate.
- If the run is interrupted, the most important candidate is available first.
- `mmproj` is stored next to its matching text model, but not loaded during
  text-only dry-load unless a later multimodal GO exists.

## Proposed Download Command Shape

Use a later HP Z2 download GO before running any of this.

Preferred direct-download shape:

```powershell
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'Continue'

$downloads = @(
  @{
    Url = 'https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF/resolve/main/gemma-4-31B-it-QAT-Q4_0.gguf'
    Path = 'C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\gemma-4-31B-it-QAT-Q4_0.gguf'
    Bytes = 17651000768
  },
  @{
    Url = 'https://huggingface.co/lmstudio-community/gemma-4-31B-it-QAT-GGUF/resolve/main/mmproj-gemma-4-31B-it-QAT-BF16.gguf'
    Path = 'C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\mmproj-gemma-4-31B-it-QAT-BF16.gguf'
    Bytes = 1200726016
  },
  @{
    Url = 'https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF/resolve/main/gemma-4-26B-A4B-it-QAT-Q4_0.gguf'
    Path = 'C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf'
    Bytes = 14439362752
  },
  @{
    Url = 'https://huggingface.co/lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF/resolve/main/mmproj-gemma-4-26B-A4B-it-QAT-BF16.gguf'
    Path = 'C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\mmproj-gemma-4-26B-A4B-it-QAT-BF16.gguf'
    Bytes = 1194827776
  }
)

foreach ($item in $downloads) {
  $dir = Split-Path -Parent $item.Path
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Start-BitsTransfer -Source $item.Url -Destination $item.Path
}
```

If `Start-BitsTransfer` fails on Hugging Face redirect handling, use the same
URL/path table with `Invoke-WebRequest -OutFile` or a Hugging Face CLI download
method. Do not install new tools during the download gate without separate GO.

## Post-Download Verification

After the later download GO, verify all of these:

```powershell
$downloads | ForEach-Object {
  $file = Get-Item -LiteralPath $_.Path
  [pscustomobject]@{
    Path = $file.FullName
    Bytes = $file.Length
    ExpectedBytes = $_.Bytes
    SizeMatch = ($file.Length -eq $_.Bytes)
    Sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash
  }
}
```

Required pass criteria:

- all four files exist.
- all four file sizes match the planned byte counts.
- SHA256 hashes are recorded in the closeout artifact/relay.
- `lms ps --json` remains `[]`.
- ports `18080/18081` remain free.
- no `llama-server` or shim process is started.
- `C:` free space remains above the 100 GiB floor.

## Non-Goals

This plan does not authorize:

- dry-load.
- llama.cpp or LM Studio model load.
- `mmproj` multimodal test.
- `/explain`.
- endpoint replay.
- EMR write/reindex.
- config mutation.
- model ranking.
- artifact repo mutation.

## Next Gates

Download gate:

```text
HP Z2 local-llm-eval Gemma 4 31B+26B QAT download GO
```

After download verification, first dry-load gate:

```text
HP Z2 local-llm-eval Gemma 4 31B QAT text-only dry-load preflight GO
```

Efficiency comparison dry-load gate:

```text
HP Z2 local-llm-eval Gemma 4 26B A4B QAT text-only dry-load preflight GO
```
