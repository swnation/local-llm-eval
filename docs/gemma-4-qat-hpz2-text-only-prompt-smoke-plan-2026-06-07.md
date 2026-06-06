---
id: gemma-4-qat-hpz2-text-only-prompt-smoke-plan-2026-06-07
project: local-llm-eval
type: plan
status: draft-plan
created: 2026-06-07
scope: HP Z2 text-only LM Studio prompt smoke plan for Gemma 4 31B QAT and Gemma 4 26B A4B QAT
related:
  - docs/gemma-4-qat-hpz2-dry-load-result-memo-2026-06-06.md
  - docs/local-model-community-recipe-research-memo-2026-06-07.md
  - docs/gemma-4-qat-hpz2-download-plan-2026-06-06.md
---

# Gemma 4 QAT HP Z2 Text-Only Prompt Smoke Plan

## Project Goal Check

- direct value: test whether the already dry-load-verified Gemma 4 QAT models
  can return a short non-PHI final text answer before any endpoint or ranking
  work.
- classification: `direct progress` with modelops safety value.
- narrower scope: HP Z2 text-only prompt smoke plan. No execution, model load,
  prompt/API call, `/explain`, EMR write/reindex, artifact mutation, commit,
  push, relay update, or backup is authorized by this file.

## Scope

This plan is for a later **HP Z2** execution gate. It is intentionally outside
the H2 C1 retrieval/citation endpoint lane.

Models:

- `google/gemma-4-31b-qat`
- `gemma-4-26b-a4b-it-qat`

Both are text-only. Do not load `mmproj` files in this first prompt smoke.

## Preconditions

On HP Z2 before execution:

```powershell
git -C C:\Github\local-llm-eval fetch origin
git -C C:\Github\local-llm-eval status --short --branch
git -C C:\Github\local-llm-eval rev-parse HEAD
lms ps --json
Get-NetTCPConnection -LocalPort 18080,18081 -ErrorAction SilentlyContinue
```

Required state:

- `local-llm-eval` is clean and synced to the user-approved commit.
- `lms ps --json` returns no loaded models.
- ports `18080` and `18081` are free.
- C: free space remains above the project floor.
- downloaded GGUF hashes still match the dry-load memo.

## Load Profile

31B QAT:

```powershell
lms load google/gemma-4-31b-qat --identifier hpz2-gemma4-31b-qat-prompt-smoke --gpu max --context-length 4096 --ttl 120 -y
```

26B A4B QAT:

```powershell
lms load gemma-4-26b-a4b-it-qat --identifier hpz2-gemma4-26b-a4b-qat-prompt-smoke --gpu max --context-length 4096 --ttl 120 -y
```

If LM Studio exposes a thinking/reasoning toggle for the model, record the
setting and whether it was honored. Do not infer semantic quality from this
gate.

## Prompt

Use one short synthetic non-PHI Korean prompt:

```text
다음 문장을 한 문장으로 짧게 요약해줘. 환자 정보는 없다. "이 테스트는 로컬 모델이 짧은 한국어 지시를 따라 최종 답변을 생성하는지 확인한다."
```

Expected behavior:

- non-empty final answer.
- no repeated-token flood.
- no whitespace-only output.
- no reasoning-only output.
- no PHI-like output.

## Pass Criteria

A model passes this gate only if all are true:

- load succeeds under context length 4096.
- one text-only non-PHI prompt returns a non-empty final answer.
- output is not repeated-token flood / whitespace-only / reasoning-only.
- output PHI-like hit count is zero.
- unload succeeds.
- final `lms ps --json` shows no loaded model.
- ports `18080` and `18081` remain clear.

## Output

Write only PHI-safe metadata to an HP artifact or handoff note:

```text
host
local-llm-eval HEAD
model key
load command
load time / reported memory
prompt-smoke status
output length
failure lane if any
unload status
final lms ps
ports 18080/18081 state
```

Do not store raw long model output. A short final answer may be reported if it
contains no PHI-like pattern and no sensitive content.

## Non-Goals

- No `/explain`.
- No endpoint replay.
- No EMR write/reindex.
- No model-quality ranking.
- No Primary4 promotion.
- No multimodal or `mmproj` test.
- No H2 C1 retrieval/citation conclusion.

## Next Gate

Execution requires a separate explicit HP Z2 gate:

```text
HP Z2 local-llm-eval Gemma 4 QAT text-only prompt smoke execution GO
```
