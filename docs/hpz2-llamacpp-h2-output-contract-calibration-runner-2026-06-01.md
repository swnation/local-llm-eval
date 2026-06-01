---
id: hpz2-llamacpp-h2-output-contract-calibration-runner-2026-06-01
project: local-llm-eval
type: runbook
status: runner-build-ready-no-execution
created: 2026-06-01
scope: HP Z2 llama.cpp H2 output-contract calibration runner
related:
  - docs/h2-output-contract-calibration-plan-2026-06-01.md
  - prompts/h2_output_contract_calibration_v0.1.json
  - tools/hpz2_llamacpp_h2_output_contract_calibration_runner.py
---

# HP Z2 H2 Output-Contract Calibration Runner

## Purpose

This runner calibrates how local models follow output-format instructions before
another H2 endpoint model ranking attempt.

It tests output contract behavior only. It does not call `/explain`, does not
use the shim, does not write to `EMR_AI_24clinic`, and does not assess endpoint
readiness.

## Files

- Runner:
  `tools/hpz2_llamacpp_h2_output_contract_calibration_runner.py`
- Synthetic fixture:
  `prompts/h2_output_contract_calibration_v0.1.json`
- Plan:
  `docs/h2-output-contract-calibration-plan-2026-06-01.md`
- Tests:
  `tests/test_hpz2_llamacpp_h2_output_contract_calibration_runner.py`

## Default Matrix

Dry-run and future execution default to the 24-call pilot:

```text
2 models x 3 synthetic cases x 4 output contracts = 24 calls
```

Default models:

- `hpz2-l2-qwen36-35b-a3b`
- `hpz2-l2-granite-41-30b-q4km`

Use `--primary4` only after a clean pilot and a separate expansion GO.

## Dry Run

Main PC dry-run:

```powershell
python tools\hpz2_llamacpp_h2_output_contract_calibration_runner.py --dry-run
```

Expected behavior:

- validates config, fixture, selected models, selected cases, and contracts
- prints planned 24-call matrix
- does not start `llama-server`
- does not load a model
- does not call `/explain`
- does not call the shim
- does not write EMR files
- does not write raw response artifacts

Validation commands used at build time:

```powershell
python -m py_compile tools\hpz2_llamacpp_h2_output_contract_calibration_runner.py tests\test_hpz2_llamacpp_h2_output_contract_calibration_runner.py
python -m unittest tests.test_hpz2_llamacpp_h2_output_contract_calibration_runner
python tools\hpz2_llamacpp_h2_output_contract_calibration_runner.py --dry-run
```

Build-time result: all three passed on Main PC.

Review hardening after worker feedback:

- PHI-like raw output is now scored through a redacted metadata path and does
  not preserve `normalized_summary` or citations in aggregate JSON.
- Required-source misses and distractor-source use now block
  `citation_exact_pass` and `normalizer_pass`.
- Unit coverage includes required-source miss, distractor-source use, and
  PHI-redacted scoring.

## Future HP Execution

Execution is not authorized by this runbook. If later approved, use:

```powershell
python tools\hpz2_llamacpp_h2_output_contract_calibration_runner.py `
  --confirm-hpz2 `
  --confirm-output-contract-calibration
```

Do not run this without explicit:

```text
HP Z2 H2 output-contract calibration run GO
```

## Output Artifacts

Future execution writes under:

```text
C:\Github\hpz2-run-artifacts\results\h2_output_contract_calibration_<timestamp>\
```

Expected files:

- `output_contract_calibration_results.json`
- `output_contract_calibration_summary.md`
- `raw_responses\*.txt`
- `prompts\*.txt`
- per-model `llama-server` stdout/stderr logs

Raw responses are permitted only because the fixture is synthetic and non-PHI.
The runner scans fixture and output text for PHI-like patterns.

## Output Contracts

| contract | meaning | response_format |
|---|---|---|
| C1 | strict endpoint-like JSON with bracketed citations | `json_object` |
| C2 | JSON with endpoint keys and bare source IDs | `json_object` |
| C3 | relaxed JSON with `answer` and `sources` | `json_object` |
| C4 | freeform Korean answer with inline bracketed citations | none |

## Interpretation

The runner separates:

- semantic model potential
- normalizer feasibility
- native contract convenience
- endpoint contract hypothesis for later replay

It does not decide endpoint readiness. Endpoint readiness requires a later
`/explain` lane.

The pilot artifact is also not a final pass/fail verdict until manual review
fills or confirms:

- `semantic_pass`
- `grounding_pass`
- `citation_claim_pass`
- `safety_pass`

Automated fields are contract and citation-copy evidence only.

## Hard Stops

- No `/explain`.
- No shim.
- No EMR write.
- No production prompt change.
- No PHI or PHI-like fixture.
- No cleanup/download.
- No reference model expansion without separate GO.
- Stop if PHI-like text appears in fixture or raw output.
- Stop if `llama-server` fails teardown.
