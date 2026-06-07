---
id: gemma-4-qat-reasoning-control-output-contract-pilot-result-memo-2026-06-07
project: local-llm-eval
type: memo
status: draft
created: 2026-06-07
scope: HP Z2 Gemma 4 QAT reasoning-control and output-contract pilot result
related:
  - docs/gemma-4-qat-reasoning-control-output-contract-plan-2026-06-07.md
  - docs/gemma-4-qat-hpz2-text-only-prompt-smoke-result-memo-2026-06-07.md
  - tools/hpz2_gemma_reasoning_output_contract_pilot.py
---

# Gemma 4 QAT Reasoning-Control Output-Contract Pilot Result

## Project Goal Check

- direct value: determine whether Gemma 4 QAT can safely enter an
  endpoint-style JSON output-contract lane after the first text-only prompt
  smoke.
- classification: `direct progress` with modelops safety value.
- narrower scope: result memo plus Main PC runner-plan evidence only. No
  `/explain`, EMR write/reindex, endpoint replay, model ranking, relay update,
  backup, commit, or push is authorized by this file.

## Execution Summary

HP Z2 executed a bounded LM Studio local API pilot from the current repo-backed
plan.

```text
host: hpcheck
local-llm-eval: HEAD == origin/main == c08f6fb718d893858066633f68dd378b9503e528
result metadata: C:\Github\local-llm-eval\results\gemma_reasoning_output_contract_pilot_20260607_113148\
raw model output stored: false
```

Preflight and final state:

```text
lms ps before/final: []
ports 18080/18081: clear
C: free before pilot: 555.03 GiB
HP repo final status: clean, HEAD == origin/main
```

The run used only LM Studio's local OpenAI-compatible API on
`127.0.0.1:1234`. It did not call `/explain`, EMR, `llama-server`, the Ollama
shim, or ports `18080/18081`.

## Pilot Results

| Model | G1 final-answer control | G2 JSON contract |
|---|---|---|
| Gemma 4 31B QAT | PASS at `max_tokens=512`; final content present, PHI-like hits 0. Reasoning still appeared (`reasoning_tokens=457`, `reasoning_chars=1418`). | FAIL. `response_format: {"type":"json_object"}` returned HTTP 400: allowed values are `json_schema` or `text`. Retry without `response_format` returned content but with markdown fence, so raw final content failed JSON contract. |
| Gemma 4 26B A4B QAT | PASS at `max_tokens=512`; final content present, PHI-like hits 0, no reasoning channel observed. | FAIL. Same HTTP 400 for `json_object`; retry without `response_format` returned content but with markdown fence, so raw final content failed JSON contract. |

## Interpretation

- Both Gemma QAT candidates can produce final Korean content in a short
  synthetic non-PHI prompt.
- 26B A4B remains the cleaner first candidate for a next Gemma output-contract
  check because it passed G1 without observed reasoning-channel output.
- 31B remains reference-only for now because it still consumed visible reasoning
  budget even when it produced final content at `max_tokens=512`.
- Current LM Studio API behavior is not compatible with the existing
  `json_object` assumption for this Gemma gate. The next compatibility check
  must test OpenAI-style `json_schema` or an explicitly text-mode prompt
  strategy, not endpoint replay.
- Retry without `response_format` is insufficient for this gate because both
  models wrapped JSON in markdown fences.

## Main PC Runner Plan

The working-tree runner draft is:

```text
tools/hpz2_gemma_reasoning_output_contract_pilot.py
tests/test_hpz2_gemma_reasoning_output_contract_pilot.py
```

Local validation before HP copy:

```text
python -m py_compile tools\hpz2_gemma_reasoning_output_contract_pilot.py tests\test_hpz2_gemma_reasoning_output_contract_pilot.py
python -m unittest tests.test_hpz2_gemma_reasoning_output_contract_pilot
```

Result:

```text
6 tests OK
```

Recommended next runner patch, if the user opens it:

1. Add a G2-json-schema lane using `response_format.type = "json_schema"` with
   strict `summary` and `citations` schema.
2. Keep the existing no-`response_format` retry as diagnostic only, not a pass
   path while markdown fences remain.
3. Prioritize `gemma-4-26b-a4b-it-qat` for the first json-schema compatibility
   check; keep `google/gemma-4-31b-qat` as reference with reasoning-budget
   caveat.
4. Continue storing metadata only. Do not store raw model output unless a later
   synthetic-output artifact gate explicitly allows a short PHI-scan-clean
   sample.

## Decision

Do not run Gemma endpoint replay yet.

The next technical gate should be:

```text
Main PC local-llm-eval Gemma json_schema output-contract runner patch GO
```

Only after that runner patch is reviewed and HP-pulled should HP run:

```text
HP Z2 local-llm-eval Gemma json_schema output-contract pilot GO
```

Neither gate authorizes `/explain`, EMR write/reindex, Primary4 promotion,
model ranking, artifact commit/push, relay update, librarian backup, or
production recommendation.
