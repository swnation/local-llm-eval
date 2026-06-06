---
id: gemma-4-qat-reasoning-control-output-contract-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: HP Z2 Gemma 4 QAT reasoning-control and output-contract pilot plan
related:
  - docs/gemma-4-qat-hpz2-text-only-prompt-smoke-result-memo-2026-06-07.md
  - docs/gemma-4-qat-hpz2-text-only-prompt-smoke-plan-2026-06-07.md
  - docs/local-model-community-recipe-research-memo-2026-06-07.md
  - docs/h2-output-contract-calibration-plan-2026-06-01.md
---

# Gemma 4 QAT Reasoning-Control Output-Contract Plan

## Project Goal Check

- direct value: turn the first Gemma prompt-smoke result into a bounded next
  gate that separates reasoning budget, final-answer channel, and JSON contract
  compliance before any endpoint replay or ranking.
- classification: `direct progress` with modelops safety value.
- narrower scope: plan only. No HP command, model load, prompt/API call,
  `/explain`, EMR write/reindex, artifact mutation, model ranking, relay
  update, backup, commit, or push is authorized by this file.

## Why This Gate Exists

The first HP Z2 prompt smoke showed two different Gemma behaviors:

- Gemma 4 31B QAT produced reasoning-only output at `max_tokens=256`, then a
  final answer at `max_tokens=1024` with substantial reasoning budget use.
- Gemma 4 26B A4B QAT produced final content at `max_tokens=1024` with no
  observed reasoning channel in that tiny smoke.

That evidence is useful but not enough for endpoint work. Before Gemma enters
any H2-style endpoint or output-contract comparison, we need a small pilot that
answers:

1. Can each model reliably emit final content instead of reasoning-only output?
2. Is the behavior sensitive to `max_tokens`?
3. Can the model follow a minimal JSON output contract without markdown fences
   or prose wrappers?
4. Does LM Studio expose or honor any usable reasoning/thinking control for
   these model keys?

This gate does not decide model quality or endpoint readiness.

## Execution Topology

Future execution host, only after separate GO:

- HP Z2.
- LM Studio local OpenAI-compatible API on `127.0.0.1:1234`.
- Text-only models; do not load `mmproj`.
- No `llama-server`, no Ollama shim, no ports `18080/18081`, no `/explain`.
- No EMR repo write and no RAG index write/reindex.

Reasoning-control discovery is observational. Do not assume LM Studio supports
a specific thinking toggle. The run should record the runtime version, model
key, API payload fields sent, message keys returned, and whether reasoning
content was present.

Direct llama.cpp Gemma serving with flags such as `--reasoning off`, `--jinja`,
`--cache-ram`, or `--ctx-checkpoints` is a separate later gate. Do not mix it
into this LM Studio pilot.

## Model Scope

Pilot models:

| label | LM Studio key | purpose |
|---|---|---|
| `gemma-4-31b-qat` | `google/gemma-4-31b-qat` | dense/reference candidate; reasoning-budget risk observed |
| `gemma-4-26b-a4b-qat` | `gemma-4-26b-a4b-it-qat` | efficiency candidate; cleaner first final-answer smoke |

No Primary4 endpoint candidates are included. This is a Gemma-family control
pilot, not a comparison against Qwen or Granite.

## Preflight

Before the later HP execution:

```powershell
git -C C:\Github\local-llm-eval fetch origin
git -C C:\Github\local-llm-eval status --short --branch
git -C C:\Github\local-llm-eval rev-parse HEAD
lms ps --json
Get-NetTCPConnection -LocalPort 18080,18081 -ErrorAction SilentlyContinue
```

Required state:

- HP `local-llm-eval` is clean and synced to the user-approved commit.
- `lms ps --json` shows no loaded model before the first load.
- Ports `18080` and `18081` are clear.
- C: free space remains above the project floor.
- The 31B and 26B QAT GGUF hashes still match the dry-load/result memos.
- LM Studio local server availability on `127.0.0.1:1234` is recorded.

Abort before model load if any required state fails.

## Pilot Matrix

Keep the first pilot small:

```text
2 models x 2 contracts x up to 2 token budgets = maximum 8 API calls
```

### Contract G1: Final-Answer Control

Purpose: check final content channel behavior without JSON pressure.

Prompt:

```text
다음 문장을 한 문장으로 짧게 요약해줘. 환자 정보는 없다. "이 테스트는 로컬 모델이 짧은 한국어 지시를 따라 최종 답변을 생성하는지 확인한다."
```

Request defaults:

```json
{
  "temperature": 0,
  "max_tokens": 512,
  "stream": false
}
```

Escalation rule:

- Start with `max_tokens=512`.
- If final content is empty and reasoning content exists, retry once at
  `max_tokens=1024`.
- Do not retry more than once per model for G1.

### Contract G2: Minimal Native JSON Contract

Purpose: check whether Gemma can emit the current endpoint-style envelope on a
synthetic non-PHI source.

Prompt input:

```text
근거:
- source_id=kb:DEMO_GEMMA_OUTPUT:001
- 내용=로컬 모델 출력 계약 테스트는 합성 데이터만 사용하며 실제 환자 정보가 없다.

요청:
한국어 한 문장 summary와 citations 배열만 포함한 JSON을 출력하라.
citations에는 [kb:DEMO_GEMMA_OUTPUT:001]만 넣어라.
```

Expected final content:

```json
{"summary":"한국어 설명","citations":["[kb:DEMO_GEMMA_OUTPUT:001]"]}
```

Request defaults:

```json
{
  "temperature": 0,
  "max_tokens": 1024,
  "stream": false,
  "response_format": {"type": "json_object"}
}
```

If LM Studio rejects `response_format`, rerun G2 once without
`response_format` and mark the contract lane as `response_format_unsupported`.
Do not treat unsupported `response_format` as model semantic failure.

## Runtime Logging

Record metadata only unless a later execution runbook explicitly permits raw
synthetic output storage:

- host and user.
- `local-llm-eval` HEAD.
- LM Studio version/runtime if exposed.
- model key and load command.
- GGUF path/hash verification status.
- API payload controls: `temperature`, `max_tokens`, `response_format`
  presence, and any discovered reasoning/thinking control.
- response status, latency, finish reason, usage/completion tokens if present.
- message keys returned by the API.
- `content_chars`, `reasoning_chars`, and reasoning token count if present.
- output channel status: `content`, `reasoning_only_output`,
  `empty_content`, `request_failed`, or `contract_failed`.
- PHI-like hit count.
- unload status and final `lms ps --json`.
- ports `18080/18081` state.

Raw long model output and reasoning text should not be copied into relay or
memory. A short final content sample may be stored in an artifact only if it is
synthetic, PHI-scan clean, and needed to verify the JSON contract.

## Pass Criteria

### G1 Pass

All must be true:

- API status is OK.
- final content is non-empty.
- output is not reasoning-only, whitespace-only, or repeated-token flood.
- PHI-like hit count is zero.
- model unload succeeds.

If the model passes only after `max_tokens=1024`, mark it
`PASS_WITH_REASONING_BUDGET_CAVEAT`, not a clean pass.

### G2 Pass

All must be true:

- API status is OK.
- final content is non-empty.
- output parses as JSON from the final content channel.
- top-level keys are exactly `summary` and `citations`.
- `summary` is a short Korean string.
- `citations` is exactly `["[kb:DEMO_GEMMA_OUTPUT:001]"]`.
- no markdown fence, prose wrapper, or additional keys are present.
- PHI-like hit count is zero.
- model unload succeeds.

Reasoning-only JSON is a fail for this gate, even if the JSON text would parse.
The endpoint needs final content, not hidden reasoning.

## Decision Rules

- If 26B A4B passes G1 and G2 cleanly while 31B is budget-dependent, prefer 26B
  A4B for the next Gemma output-contract pilot. This is an execution priority,
  not a model-quality ranking.
- If 31B passes only with `max_tokens=1024`, keep it as a reference candidate
  but require explicit reasoning-budget controls before endpoint-style tests.
- If either model emits reasoning-only output under G2, classify the failure as
  `output_channel_policy`, not semantic failure.
- If `response_format` is unsupported or ignored, split the next gate into a
  runner/runtime compatibility patch before any endpoint replay.
- If both models fail G2, do not run Gemma endpoint replay. Return to prompt
  template/control planning.
- If one model passes G1 and G2 with PHI-like hit count zero, a later gate may
  draft a Gemma-specific output-contract pilot artifact. It still does not
  authorize `/explain`, EMR writes, Primary4 promotion, or model ranking.

## Non-Goals

- No `/explain`.
- No H2 C1 endpoint replay.
- No EMR write/reindex.
- No `hpz2-run-artifacts` mutation from this plan.
- No multimodal or `mmproj` testing.
- No direct llama.cpp Gemma serving.
- No broad model ranking against Qwen, Granite, GPT-OSS, StepFun, or other
  families.
- No production recommendation.

## Suggested Next Gates

Execution pilot:

```text
HP Z2 local-llm-eval Gemma reasoning-control output-contract pilot GO
```

If a runner is preferred before HP execution:

```text
Main PC local-llm-eval Gemma reasoning-control output-contract runner plan GO
```
