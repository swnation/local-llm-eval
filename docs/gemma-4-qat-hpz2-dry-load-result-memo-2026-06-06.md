---
id: gemma-4-qat-hpz2-dry-load-result-memo-2026-06-06
project: local-llm-eval
type: memo
status: draft
created: 2026-06-06
scope: HP Z2 LM Studio import and text-only dry-load result memo for Gemma 4 31B QAT and Gemma 4 26B A4B QAT
related:
  - docs/gemma-4-qat-no-download-candidate-memo-2026-06-06.md
  - docs/gemma-4-qat-hpz2-download-plan-2026-06-06.md
  - docs/hpz2-modelops-operational-constraints-v0.1.md
  - docs/hpz2-phase2-l2-shortlist-lock-2026-05-27.md
---

# Gemma 4 QAT HP Z2 Dry-Load Result Memo

## Project Goal Check

- direct value: preserve the HP Z2 LM Studio import and text-only dry-load
  evidence for Gemma 4 31B QAT and Gemma 4 26B A4B QAT before any prompt smoke,
  endpoint replay, or model recommendation.
- classification: `maintenance` / modelops candidate-readiness evidence.
- narrower scope: result memo only. No model load, prompt/API call,
  `/explain`, EMR write/reindex, artifact mutation, commit, push, relay update,
  or backup is authorized by this file.

## Summary Verdict

Both downloaded Gemma 4 QAT text GGUF files are viable for bounded HP Z2 LM
Studio text-only loading at context length 4096.

This is a load/fit result only. It is not a model-quality result and does not
promote either model into the current Primary4 endpoint replay shortlist.

| Candidate | HP Z2 result | First role |
|---|---|---|
| Gemma 4 31B QAT Q4_0 | PASS text-only dry-load | HP reference/quality candidate |
| Gemma 4 26B A4B QAT Q4_0 | PASS symbolic-link import + text-only dry-load | HP efficiency comparison candidate |

## Verified File State

Host:

```text
host: HPCHECK
user: test
local-llm-eval: HEAD == origin/main == 23d7734
```

Downloaded source files:

| File | Bytes | SHA256 |
|---|---:|---|
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\gemma-4-31B-it-QAT-Q4_0.gguf` | 17,651,000,768 | `E664C3B437599D70EB7C470E66AAA938C0948C1851A9257F86A96306B94E8C18` |
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\mmproj-gemma-4-31B-it-QAT-BF16.gguf` | 1,200,726,016 | `25F056D3264782639E703C877D55CDDA764658B1B08F045B533FD1A78CB1902F` |
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf` | 14,439,362,752 | `9B96AA267521008235F8792590CB8E2DC47A8A236C6FF1767964CBBE32510873` |
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\mmproj-gemma-4-26B-A4B-it-QAT-BF16.gguf` | 1,194,827,776 | `A823A84619622B7B3132BA760E97BCF959FB13D2213CCCAEF5317DF388D35C3C` |

The `mmproj` files were verified and stored, but were not loaded in this
text-only gate.

## 31B QAT Dry-Load Result

LM Studio model key:

```text
google/gemma-4-31b-qat
```

Estimate command:

```powershell
lms load google/gemma-4-31b-qat --gpu max --context-length 4096 --estimate-only -y
```

Estimate result:

```text
exit_code: 0
estimated GPU memory: 19.22 GiB
estimated total memory: 19.22 GiB
```

Actual dry-load command:

```powershell
lms load google/gemma-4-31b-qat --identifier hpz2-gemma4-31b-qat-dryload --gpu max --context-length 4096 --ttl 120 -y
```

Actual dry-load result:

```text
exit_code: 0
LM Studio load output: loaded successfully in 24.99s
LM Studio load size: 17.56 GiB
identifier: hpz2-gemma4-31b-qat-dryload
context length: 4096
status after load: idle
parallel: 4
unload exit_code: 0
final lms ps: []
```

Interpretation:

- 31B QAT loads on HP Z2 under the bounded text-only LM Studio profile.
- The result is load-readiness evidence only.
- No prompt, API call, endpoint replay, or content/citation evaluation was run.

## 26B A4B QAT Import And Dry-Load Result

The downloaded 26B QAT file was present on disk, but direct path loading failed
before import because LM Studio did not index that exact QAT file.

Failed direct-path estimate:

```text
lms load C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf --gpu max --context-length 4096 --estimate-only -y
exit_code: 1
error: Model not found
```

LM Studio import dry-run showed the intended target:

```text
D:\LLM\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf
```

Actual import command:

```powershell
lms import --symbolic-link --user-repo lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF -y C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf
```

Import result:

```text
exit_code: 0
link type: SymbolicLink
link path: D:\LLM\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf
link target: C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf
hash through link: 9B96AA267521008235F8792590CB8E2DC47A8A236C6FF1767964CBBE32510873
LM Studio listed key: gemma-4-26b-a4b-it-qat
```

Estimate command after import:

```powershell
lms load gemma-4-26b-a4b-it-qat --gpu max --context-length 4096 --estimate-only -y
```

Estimate result:

```text
exit_code: 0
estimated GPU memory: 14.18 GiB
estimated total memory: 14.18 GiB
```

Actual dry-load command:

```powershell
lms load gemma-4-26b-a4b-it-qat --identifier hpz2-gemma4-26b-a4b-qat-dryload --gpu max --context-length 4096 --ttl 120 -y
```

Actual dry-load result:

```text
exit_code: 0
LM Studio load output: loaded successfully in 9.05s
LM Studio load size: 13.45 GiB
identifier: hpz2-gemma4-26b-a4b-qat-dryload
context length: 4096
status after load: idle
vision: false
max context length: 262144
unload exit_code: 0
final lms ps: []
```

Observed OS-visible memory during the 26B dry-load:

```text
before load: 22.90 GiB free / 31.78 GiB visible
after load: 8.40 GiB free / 31.78 GiB visible
after unload: 22.80 GiB free / 31.78 GiB visible
```

Interpretation:

- 26B A4B QAT is a lighter HP Z2 load than 31B QAT under the same context 4096
  LM Studio profile.
- The symbolic-link import is now part of the local HP model state for this
  exact QAT GGUF.
- `vision=false` confirms this was text-only; `mmproj` was not loaded.
- No prompt, API call, endpoint replay, or content/citation evaluation was run.

## Final HP State After Dry-Load

```text
final lms ps: []
runtime process: none
C: free: 555.25 GiB
D: free: 362.57 GiB
E: free: 953.74 GiB
```

No HP `C:\Github\memory` edit was made. The HP result was summarized into the
Main PC relay before this repo memo was drafted; backing up this repo memo and
the follow-up relay state remains a separate Main PC librarian gate.

## Boundaries

This result does not authorize:

- prompt/API call.
- `/explain`.
- endpoint replay.
- EMR write/reindex.
- artifact repo mutation.
- model-quality ranking.
- promotion into Primary4.
- `mmproj` multimodal test.

## Suggested Next Gates

Back up the repo-backed memo and follow-up relay state:

```text
Main PC local-llm-eval librarian pass GO
```

Runtime continuation after repo-backed memo or explicit skip:

```text
HP Z2 local-llm-eval Gemma 4 QAT text-only prompt smoke plan GO
```

Return to the active H2 C1 workstream:

```text
Main PC local-llm-eval H2 C1 retrieval query policy patch implementation GO
```
