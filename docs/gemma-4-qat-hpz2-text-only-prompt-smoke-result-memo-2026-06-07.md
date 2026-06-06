---
id: gemma-4-qat-hpz2-text-only-prompt-smoke-result-memo-2026-06-07
project: local-llm-eval
type: memo
status: draft
created: 2026-06-07
scope: HP Z2 LM Studio text-only prompt smoke result memo for Gemma 4 31B QAT and Gemma 4 26B A4B QAT
related:
  - docs/gemma-4-qat-hpz2-text-only-prompt-smoke-plan-2026-06-07.md
  - docs/gemma-4-qat-hpz2-dry-load-result-memo-2026-06-06.md
  - docs/local-model-community-recipe-research-memo-2026-06-07.md
---

# Gemma 4 QAT HP Z2 Text-Only Prompt Smoke Result Memo

## Project Goal Check

- direct value: preserve the first HP Z2 final-answer prompt-smoke evidence for
  the already dry-load-verified Gemma 4 QAT 31B and 26B A4B models.
- classification: `direct progress` with modelops safety value.
- narrower scope: result memo only. No model load, prompt/API call,
  `/explain`, EMR write/reindex, artifact mutation, endpoint replay, model
  ranking, relay update, backup, commit, or push is authorized by this file.

## Summary Verdict

Both Gemma 4 QAT candidates returned a non-empty final answer to the planned
short non-PHI Korean text prompt through the LM Studio local OpenAI-compatible
API.

This is prompt-smoke evidence only. It is not endpoint readiness, a content
quality ranking, a citation-grounding result, or promotion into the current H2
Primary4 endpoint replay shortlist.

| Candidate | Prompt-smoke result | Important caveat |
|---|---|---|
| Gemma 4 31B QAT Q4_0 | PASS at `max_tokens=1024` | `max_tokens=256` produced reasoning-only output; high reasoning budget observed |
| Gemma 4 26B A4B QAT Q4_0 | PASS at `max_tokens=1024` | No reasoning channel observed; faster final answer in this tiny smoke |

## Verified Starting State

Host:

```text
host: HPCHECK
user: test
local-llm-eval: HEAD == origin/main == 2b87cf9e3443c920a8171e6e85a1ff2c6548098d
```

Preflight:

```text
C: free: 555.08 GiB
lms ps: []
ports 18080/18081: clear
```

Downloaded GGUF file checks matched the dry-load memo:

| File | Bytes | SHA256 |
|---|---:|---|
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\gemma-4-31B-it-QAT-Q4_0.gguf` | 17,651,000,768 | `E664C3B437599D70EB7C470E66AAA938C0948C1851A9257F86A96306B94E8C18` |
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\mmproj-gemma-4-31B-it-QAT-BF16.gguf` | 1,200,726,016 | `25F056D3264782639E703C877D55CDDA764658B1B08F045B533FD1A78CB1902F` |
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf` | 14,439,362,752 | `9B96AA267521008235F8792590CB8E2DC47A8A236C6FF1767964CBBE32510873` |
| `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\mmproj-gemma-4-26B-A4B-it-QAT-BF16.gguf` | 1,194,827,776 | `A823A84619622B7B3132BA760E97BCF959FB13D2213CCCAEF5317DF388D35C3C` |

The `mmproj` files were checked but not loaded. This gate was text-only.

## Execution Method

The plan expected one short synthetic non-PHI Korean prompt:

```text
다음 문장을 한 문장으로 짧게 요약해줘. 환자 정보는 없다. "이 테스트는 로컬 모델이 짧은 한국어 지시를 따라 최종 답변을 생성하는지 확인한다."
```

LM Studio CLI chat was not a reliable execution surface for this gate:

- Korean prompt quoting/parsing was not stable enough for the planned command.
- A simple ASCII `lms chat -p hello` call timed out at 180 seconds and left
  `lms ps` empty.

The smoke therefore used the LM Studio local OpenAI-compatible API on
`127.0.0.1:1234`. This did not use `/explain`, EMR, ports `18080/18081`,
`llama-server`, the Ollama shim, or `hpz2-run-artifacts`.

Raw model output text is intentionally not stored in this memo.

## 31B QAT Prompt Smoke

LM Studio model key:

```text
google/gemma-4-31b-qat
```

Load command:

```powershell
lms load google/gemma-4-31b-qat --identifier hpz2-gemma4-31b-qat-prompt-smoke --gpu max --context-length 4096 --ttl 120 -y
```

Load evidence:

```text
first load: PASS, 24.20s, 17.56 GiB
reload: PASS, 11.65s, 17.56 GiB
```

Prompt-smoke evidence:

| Setting | Result |
|---|---|
| `max_tokens=256` | caveat: `content_chars=0`, reasoning-only, `finish_reason=length`, `completion_tokens=256`, `reasoning_tokens=253` |
| `max_tokens=1024` | PASS: final content generated |
| API time at pass setting | 67.17 seconds |
| final content length | 348 characters |
| reasoning content length | 2281 characters |
| reasoning tokens | 630 |
| finish reason | `stop` |
| PHI-like hits | 0 |

Interpretation:

- 31B QAT can produce final Korean text on HP Z2 through LM Studio API.
- The tiny prompt still consumed substantial reasoning budget before final
  content. Any later endpoint-style or output-contract test should pre-register
  Gemma-specific reasoning/template controls instead of assuming short prompts
  behave like the Primary4 llama.cpp endpoint candidates.

## 26B A4B QAT Prompt Smoke

LM Studio model key:

```text
gemma-4-26b-a4b-it-qat
```

Load command:

```powershell
lms load gemma-4-26b-a4b-it-qat --identifier hpz2-gemma4-26b-a4b-qat-prompt-smoke --gpu max --context-length 4096 --ttl 120 -y
```

Load evidence:

```text
load: PASS, 10.76s, 13.45 GiB
```

Prompt-smoke evidence:

| Setting | Result |
|---|---|
| `max_tokens=1024` | PASS: final content generated |
| API time | 2.71 seconds |
| final content length | 580 characters |
| reasoning content length | 0 characters |
| reasoning tokens | 0 |
| completion tokens | 132 |
| finish reason | `stop` |
| PHI-like hits | 0 |

Interpretation:

- 26B A4B QAT can produce final Korean text on HP Z2 through LM Studio API.
- In this tiny smoke, it behaved more cleanly than 31B QAT for final-answer
  generation. This is not enough evidence to rank model quality or endpoint
  readiness.

## Final HP State

```text
local-llm-eval: clean at 2b87cf9e3443c920a8171e6e85a1ff2c6548098d
lms ps: []
LM Studio local server port 1234: still running, expected
ports 18080/18081: clear
llama-server/shim processes: none
C: free: 555.08 GiB
```

No HP `C:\Github\memory` edit was made. No artifact repo mutation was made.

## Boundaries

This result does not authorize:

- `/explain`.
- endpoint replay.
- EMR write/reindex.
- artifact repo mutation.
- model-quality ranking.
- promotion into Primary4.
- multimodal or `mmproj` testing.
- broad Gemma output-contract calibration.

## Suggested Next Gates

Return to the active H2 C1 retrieval-policy lane:

```text
HP Z2 local-llm-eval H2 C1 retrieval policy top10 endpoint replay pilot GO
```

If this memo should become durable repo state:

```text
Main PC local-llm-eval Gemma prompt smoke result memo commit/push GO
```

If Gemma continuation is desired later:

```text
Main PC local-llm-eval Gemma reasoning-control/output-contract plan GO
```
