---
id: gemma-4-qat-llamacpp-output-contract-runner-plan-2026-06-07
project: local-llm-eval
type: runner-plan
status: draft
created: 2026-06-07
scope: Main PC plan for a future HP Z2 Gemma 4 QAT llama.cpp output-contract pilot runner
related:
  - docs/gemma-4-qat-reasoning-control-output-contract-pilot-result-memo-2026-06-07.md
  - docs/gemma-4-qat-hpz2-text-only-prompt-smoke-result-memo-2026-06-07.md
  - docs/gemma-4-qat-hpz2-dry-load-result-memo-2026-06-06.md
  - docs/local-model-community-recipe-research-memo-2026-06-07.md
  - tools/hpz2_llamacpp_h2_output_contract_calibration_runner.py
  - tools/hpz2_llamacpp_phase2_l2_runner.py
---

# Gemma 4 QAT llama.cpp Output-Contract Runner Plan

## Project Goal Check

- direct value: move the next Gemma output-contract check back onto the locked
  official HP Z2 backend lane, llama.cpp direct `llama-server`.
- classification: `direct progress` with modelops safety value.
- narrower scope: Main PC plan only. No runner patch, HP command, model load,
  prompt/API call, `/explain`, EMR write/reindex, artifact mutation, relay
  update, backup, commit, or push is authorized by this file.

## Status

This is the corrected runner plan after the LM Studio pilot.

The existing Main PC runner
`tools/hpz2_gemma_reasoning_output_contract_pilot.py` is useful supporting
evidence only. It should not become the official next Gemma execution path,
because the project backend lane is locked as:

```text
llama.cpp primary / LM Studio secondary
```

The future runner should use direct llama.cpp `/v1/chat/completions` through
`llama-server`, not LM Studio, not the Ollama shim, and not `/explain`.

## Evidence To Carry

Gemma QAT load and prompt evidence:

| Candidate | Evidence carry | Runner implication |
|---|---|---|
| Gemma 4 26B A4B QAT Q4_0 | HP dry-load PASS; LM Studio prompt smoke produced final content with no observed reasoning channel; LM Studio output-contract G2 failed because `json_object` was rejected and text fallback used a markdown fence. | First llama.cpp pilot target. |
| Gemma 4 31B QAT Q4_0 | HP dry-load PASS; LM Studio prompt smoke produced final content only after higher token budget and showed substantial reasoning-channel use. | Optional reference after 26B, not the first blocker for endpoint eligibility. |

Known file evidence from the repo-backed dry-load/prompt-smoke memos:

| Label to use in new runner | Text GGUF path | SHA256 |
|---|---|---|
| `hpz2-gemma4-26b-a4b-qat-q4_0` | `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf` | `9B96AA267521008235F8792590CB8E2DC47A8A236C6FF1767964CBBE32510873` |
| `hpz2-gemma4-31b-qat-q4_0` | `C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\gemma-4-31B-it-QAT-Q4_0.gguf` | `E664C3B437599D70EB7C470E66AAA938C0948C1851A9257F86A96306B94E8C18` |

The existing llama.cpp config currently contains non-QAT Gemma entries:

- `hpz2-l2-gemma-4-31b-it` -> Unsloth Q8_K_XL.
- `hpz2-l2-google-gemma-4-26b-a4b` -> Q8_0.
- `hpz2-l2-unsloth-gemma-4-26b-a4b-it` -> MXFP4_MOE.

The future runner must not use those labels as if they are the QAT Q4_0 files.
Either add explicit QAT labels in a patch gate or keep the QAT model descriptors
inside the Gemma-specific runner.

## Execution Topology

Plan phase:

- Host: Main PC.
- Scope: docs and runner design only.
- No HP command and no model execution.

Future implementation phase, only after explicit patch GO:

- Host: Main PC.
- Suggested runner:
  `tools/hpz2_llamacpp_gemma_output_contract_pilot.py`.
- Suggested tests:
  `tests/test_hpz2_llamacpp_gemma_output_contract_pilot.py`.
- Reuse existing helpers from `tools/hpz2_llamacpp_phase2_l2_runner.py` where
  practical: `build_server_args`, `preflight`, `preflight_pass`, `server_url`,
  `wait_for_server`, `memory_snapshot`, and teardown style.
- Reuse structured-output payload shape from the existing shared
  `response_format_payload("json_schema")` path and the shim
  `json_schema` wrapper shape.
- Evaluate reusing scoring helpers from
  `tools/hpz2_llamacpp_h2_output_contract_calibration_runner.py` for strict
  JSON parsing, no-fence detection, citation matching, PHI-like scanning, and
  reasoning-only classification before duplicating those rules.

Future execution phase, only after explicit HP GO:

- Host: HP Z2.
- Backend: direct `llama-server.exe`.
- API: `POST http://127.0.0.1:18080/v1/chat/completions`.
- Data: synthetic non-PHI output-contract prompt only.
- No `/explain`, no EMR repo call, no shim, no LM Studio API, no endpoint replay.
- Text-only. Do not load or reference `mmproj`.

## Runtime Controls

Use the locked llama.cpp primary runtime stance unless a later patch/review gate
finds a hard support blocker:

```text
-dev Vulkan0
-ngl all
-sm none
-mg 0
--no-mmap
--no-host
--kv-offload
--op-offload
-fa on
-ctk q8_0
-ctv q8_0
--cache-ram 0
--no-cache-prompt
--ctx-checkpoints 0
-b 1024
-ub 256
-np 1
--reasoning off
```

Fallback only after a documented load/start failure:

```text
-b 256 -ub 64
```

The runner must record the exact server args used and whether the process
accepted them. If Gemma fails because llama.cpp cannot load the architecture,
template, or GGUF, classify it as `runtime_support_blocker`, not as a
model-quality failure.

Any repeated token flood, `<unused49>`-style loop, whitespace-only output,
reasoning-only output, or ignored reasoning control should be classified as
`runtime_template_or_reasoning_control`, not as a semantic model ranking.

## Response-Format Plan

The first native contract check should use nested OpenAI-style `json_schema`,
because this shape is already implemented in the repo and llama.cpp accepted it
in the prior minimal direct capability probe:

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "gemma_output_contract_response",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "summary": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["summary", "citations"],
      "additionalProperties": false
    }
  }
}
```

`json_object` may be added as a diagnostic lane only after the `json_schema`
lane is implemented. It should not be the first Gemma QAT blocker because the
recent LM Studio pilot rejected `json_object`, while llama.cpp has a known
nested `json_schema` support path.

No-`response_format` text fallback is diagnostic only. A markdown fence or
recoverable embedded JSON is still a native-contract fail for this gate.

## Minimal Matrix

Default pilot:

```text
1 model x 2 contracts = 2 calls
```

Model:

- `hpz2-gemma4-26b-a4b-qat-q4_0`

Contracts:

- `G1-final-answer-control`
- `G2-json-schema-native-contract`

Optional reference expansion, after the 26B pilot passes teardown and metadata
safety:

```text
+ 1 model x 2 contracts = +2 calls
```

Reference model:

- `hpz2-gemma4-31b-qat-q4_0`

Do not expand into endpoint replay, Primary4 comparison, or model ranking from
this runner.

## Synthetic Prompt Contract

Use one short non-PHI evidence pack with a single exact source ID:

```text
source_id: kb:DEMO_GEMMA_OUTPUT:001
topic: local model output-contract demonstration
content: This synthetic evidence says the output must explain only that the
local model is being tested for final-answer and JSON-contract behavior.
```

Expected native JSON:

```json
{
  "summary": "The local model is being tested for final-answer and JSON-contract behavior.",
  "citations": ["[kb:DEMO_GEMMA_OUTPUT:001]"]
}
```

The exact summary wording can vary, but it must stay within the synthetic
claim. The citation must exactly include `[kb:DEMO_GEMMA_OUTPUT:001]`.

## Pass And Stop Criteria

`G1-final-answer-control` passes only if:

- HTTP status is 2xx.
- final assistant content is non-empty.
- PHI-like hit count is 0.
- no raw patient-like identifiers appear.
- no model output body is stored by default.
- `reasoning_chars == 0` or absent. If final content exists but reasoning is
  present, classify as `reasoning_control_warn` and keep the model out of
  endpoint eligibility.

`G2-json-schema-native-contract` passes only if:

- HTTP status is 2xx.
- final assistant content parses as a single JSON object without stripping a
  markdown fence or extracting embedded JSON.
- keys are exactly `summary` and `citations`.
- `summary` is a non-empty string.
- `citations` is an array.
- citations include exactly `[kb:DEMO_GEMMA_OUTPUT:001]`.
- PHI-like hit count is 0.
- no reasoning-only or token-loop behavior appears.

Stop the runner before any expansion if:

- preflight finds stale `llama-server`, shim process, or occupied
  `18080/18081`.
- C: free space is below the project floor.
- HP repo is not clean/synced at the expected commit for the run.
- QAT text GGUF file or SHA256 verification fails.
- llama.cpp exits early or rejects required runtime args.
- Gemma emits repeated token loops, whitespace-only output, or reasoning-only
  output after the pre-registered token budget.
- any PHI-like hit is detected.

## Artifact And Logging Policy

Default output should be PHI-safe metadata only:

- model label.
- GGUF path and SHA256 match status.
- exact runtime args.
- response_format lane.
- HTTP status.
- final `content_chars`.
- `reasoning_chars` and `reasoning_tokens`, if the API exposes them.
- parse status and contract pass/fail.
- PHI-like hit count.
- preflight/final ports and process counts.

Do not store raw long model output by default. A later synthetic-output artifact
gate may explicitly allow a short PHI-scan-clean output sample, but this plan
does not.

## Validation For The Patch Gate

The future patch gate should validate:

```powershell
python -m py_compile tools\hpz2_llamacpp_gemma_output_contract_pilot.py tests\test_hpz2_llamacpp_gemma_output_contract_pilot.py
python -m unittest tests.test_hpz2_llamacpp_gemma_output_contract_pilot
python -m unittest discover -s tests
git diff --check
```

The patch should include unit tests for:

- nested `json_schema` payload shape.
- strict JSON parse fail on markdown fences.
- exact citation matching.
- reasoning-only classification.
- PHI-like scan over content plus reasoning text.
- dry-run refusing execution without both explicit HP and pilot confirms.
- preflight fail-closed behavior for stale runtime process or non-empty loaded
  model state if LM Studio state is touched for safety inspection.

## Next Gates

Implementation gate:

```text
Main PC local-llm-eval Gemma llama.cpp output-contract runner patch GO
```

After commit/push and HP pull/verify, execution gate:

```text
HP Z2 local-llm-eval Gemma llama.cpp output-contract pilot GO
```

Maintenance gates remain separate:

```text
Main PC local-llm-eval Gemma llama.cpp output-contract runner commit/push GO
Main PC local-llm-eval relay update GO
Main PC local-llm-eval librarian pass GO
```
