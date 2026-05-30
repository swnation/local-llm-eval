---
id: h2-schema-mode-ab-plan-2026-05-30
project: local-llm-eval
type: execution-plan
status: frozen-plan-pending-execution-go
created: 2026-05-30
updated: 2026-05-31
scope: H2 schema-mode A/B execution plan only
---

# H2 Schema-Mode A/B Execution Plan

## Purpose

Resolve the remaining R12 carry note before H2 model comparison: R11/R12 prove
that llama.cpp `b9333` accepts the nested OpenAI-style `json_schema` shape and
that the shim forwards it correctly, but they do not prove hard schema
enforcement across longer clinical prompts.

This plan freezes a small A/B that selects one structured-output mode before
broader H2 model comparison. It is a plan only. It does not authorize
`/explain`, HP runtime startup, model execution, matrix execution, EMR writes,
cleanup, downloads, commit, or push.

## Cases

### Cooperative Baseline: RA-03-safety-boundary

RA-03 is the H1-passed baseline. It should pass both schema modes; failure here
is treated as plumbing/regression evidence, not a schema-mode discriminator.

Locked values:

- orders: `sme`, `trimesy`, `lacto2`
- dx: `a090`
- pediatric age: `1`
- patient_type: `소아`
- options: `top_k=5`, `min_similarity=0.45`, `lexical_rerank=false`
- expected citations:
  - `rule:drug:sme`
  - `kb:소아_AGE_sme_2세미만`
  - `kb:소아_AGE_FGID:007`

Do not change these values without explicit user instruction.

### Discriminating Case: RA-05-rule-kb-nuance-conflict

RA-05 is used only to measure structural/schema enforcement. It must not be
used for final content-quality verdicts in this A/B because
`expected_summary_keywords` and the clinical input review remain user-owned
pending items.

Locked-for-A/B input values:

- dx: `a09`
- orders: `tamiiv`
- order detail: `code=tamiiv`, `dose=IV`, `days=1`
- pediatric age: `11`
- patient_type: `소아`
- options: `top_k=5`, `min_similarity=0.45`, `lexical_rerank=false`
- expected citations:
  - `rule:ped-iv-ban`
  - `kb:소아_IV_수액_재량`

Use RA-05 to compare valid JSON, strict schema conformance, extra-key drift,
citation-array shape, bracketed citation format, citation verifier status, and
PHI scan result. Do not use it to declare final clinical/content quality.

## Matrix

Minimal frozen matrix: 4 cells.

| Case | Schema mode | Model |
|---|---|---|
| RA-03-safety-boundary | `json_object` | `hpz2-l2-qwen36-35b-a3b` |
| RA-03-safety-boundary | `json_schema` | `hpz2-l2-qwen36-35b-a3b` |
| RA-05-rule-kb-nuance-conflict | `json_object` | `hpz2-l2-qwen36-35b-a3b` |
| RA-05-rule-kb-nuance-conflict | `json_schema` | `hpz2-l2-qwen36-35b-a3b` |

Optional expansion: add `hpz2-l2-granite-41-30b-q4km` for an 8-cell run only
after explicit user approval. Granite is not implied by the 4-cell execution GO.

## Execution Contract

When a later execution GO is issued, every cell must keep all variables fixed
except `--schema-mode`.

- Use split topology: Main PC EMR harness over SSH tunnel to HP loopback shim.
- Use loopback only: HP `llama-server` on `127.0.0.1:18080`, HP shim on
  `127.0.0.1:18081`, Main PC tunnel local `127.0.0.1:18081`.
- Use env override only:
  - `EMR_LLM_ENABLED=true`
  - `EMR_LLM_PROVIDER=ollama`
  - `EMR_LLM_MODEL=hpz2-l2-qwen36-35b-a3b`
  - `EMR_LLM_HOST=http://127.0.0.1:18081`
  - `EMR_LLM_TIMEOUT_SECONDS=300`
- For `json_object` cells, run the shim with `--schema-mode json-object`.
- For `json_schema` cells, run the shim with `--schema-mode json-schema`.
- Do not write `data/llm_settings.json`.
- Do not edit `C:\Github\EMR_AI_24clinic`.
- Do not use `scripts/smoke_test_explain.py`.
- Do not run a model matrix, cleanup, download, commit, or push under the A/B
  execution GO.

## Measurement Fields

Report PHI-safe metadata only. Do not put raw model response text in relay or
handoff reports.

Per cell:

- HTTP status
- EMR status
- valid JSON: yes/no
- strict schema conformance:
  - `summary` is string
  - `citations` is array of strings
  - no extra top-level keys (`additionalProperties=false`)
- citation array/bracket format pass/fail
- citation verifier pass/fail
- retrieved chunk count
- citation count
- PHI hit count
- latency and wall time
- repo dirty status before/after
- failure owner: infra / retrieval / schema / citation / PHI / content / unknown
- structural failure vs content failure split

For RA-05, content-quality fields can be captured for later user review, but no
final content verdict is allowed during this A/B.

## Structural Drift Definition

For this A/B, an output is **structural drift** if ANY of the following holds.
This binds the phrase "drifts structurally" in Pre-Registered Decision Rule 1.

1. **Non-JSON** - text does not parse as a JSON object (`json.loads` fails or
   result is not an object).
2. **Extra top-level key** - any top-level key beyond `summary` and `citations`
   (violates `additionalProperties: false`).
3. **Missing/invalid `summary`** - absent or not a string.
4. **`citations` not a string array** - absent, not a list, or any element not
   a string.
5. **Malformed/bracketless citation** - any citation item not in exact
   `"[source_id]"` bracket form
   (`citation_verifier` `CITATION_ITEM_RE = ^\[([^\[\]]+?)\]$`).
6. **Strict schema conformance failure** - fails validation against EMR
   `EXPLAIN_JSON_SCHEMA` (required `summary` + `citations`,
   `additionalProperties:false`).

An output with none of the above is **conformant**.

Decision Rule 1 means RA-05 `json_schema` is conformant and RA-05
`json_object` has structural drift. Decision Rule 2 means both modes give the
same drift/conformant classification on RA-05.

Structural drift is shape only. Citation verification (`source_id` in
retrieved chunks and drop-rate checks) is tracked separately as the
citation/content lane, not as structural drift. Do not conflate a
bracket-format failure, which is structural, with citing a non-retrieved
`source_id`, which is citation/content evidence.

## Pre-Registered Decision Rules

1. If RA-05 `json_schema` conforms while RA-05 `json_object` drifts
   structurally, choose `json_schema` for H2 because it better matches the
   operating intent of EMR strict `format`.
2. If there is no meaningful structural difference, choose `json_object` for
   H2 and add a strict-schema conformance metric plus a caveat that llama.cpp
   `b9333` hard enforcement was not demonstrated in the clinical A/B.
3. If RA-03 fails in either mode, stop and diagnose regression/infrastructure
   before choosing a schema mode.
4. If both RA-05 modes fail before reaching schema comparison, stop and do not
   choose a mode from that run.
5. If PHI hit count is greater than zero in any cell, hard STOP and mark the
   run NO-GO.

Do not mix schema modes inside later H2 model comparison. The selected mode
must be fixed and documented before comparing models.

## Safety Envelope

Preflight for any later execution GO:

- HP hostname `hpcheck` / `HPCHECK`.
- Main PC `local-llm-eval` clean at the committed plan baseline or newer.
- HP `local-llm-eval` clean at the committed plan baseline or newer.
- Main PC and HP `EMR_AI_24clinic` clean at `543e1f9` or newer unless a later
  repo pin supersedes it.
- Ports `18080` and `18081` free before start.
- No stale `llama-server` or shim process.
- Model file exists for `hpz2-l2-qwen36-35b-a3b`.
- `C:` free space at least 100 GiB.
- memory load below 92%.
- Use `test@192.168.68.50` if the `hpcheck` SSH alias still has host-key drift.
- Shutdown after the run and confirm ports `18080` and `18081` have no listener.

## Next GO

Recommended sequence:

1. `H2 A/B execution plan review GO`
2. `H2 A/B execution plan commit + push GO`
3. HP pull/verify latest `local-llm-eval`
4. `H2 A/B execution GO (4-cell minimal)`

Optional expansion requires a separate explicit phrase such as
`H2 A/B execution GO (+Granite 8-cell)`.

## Result & Decision (R14, 2026-05-30/31)

Executed under explicit GO. The frozen 4-cell matrix was expanded to 8 cells
with explicit approval (added `hpz2-l2-granite-41-30b-q4km`). Each pair ran an
HP loopback `llama-server` + shim, reached by the Main PC EMR `.venv` harness
over an SSH tunnel; runtime was torn down between pairs and after the final pair
(ports `18080`/`18081` confirmed no listener).

Result: **8/8 cells PASS** — HTTP 200, EMR status `ok`, valid JSON, strict schema
conformant, **structural drift NO**, citation verifier pass, PHI hit count `0`.
Holds for both Qwen 35B A3B official and Granite 4.1 30B, across `json_object`
and `json_schema`.

Decision: **Pre-registered Rule 2** applies (no meaningful structural difference)
-> **H2 uses `json_object`** plus a strict-schema conformance metric and caveat.

Honest caveat (this is the metric/caveat Rule 2 requires):

- The discriminating case RA-05 did **not** drift under `json_object` either, so
  this A/B did not actually exercise the discrimination. We did **not** demonstrate
  `json_schema` hard enforcement, and did **not** observe `json_object` failing.
- The result means "mode-invariant for these 2 cases x 2 Primary-tier models",
  **not** "`json_object` is generally safe". `json_object` adequacy here rests on
  the strong prompt + strong (Primary) models; it is unproven for weaker models,
  harder cases, or longer prompts.
- Keep the strict-schema conformance metric **live in H2 as a tripwire**.
  `json_schema` enforcement remains undemonstrated, not disproven.

RA-05 carry: structure/schema evidence only here, not a content-quality verdict
(expected-summary wording + clinical input review remain user-owned). Content
aside for H2 (not a mode signal): Granite returned 1 citation on RA-03 vs Qwen's
3 (RA-03 expects 3) — a model completeness signal to track in H2.

Runtime/repo: HP runtime torn down (pair 4: shim PID `63764`, `llama-server` PID
`42084` stopped; ports closed). HP repos clean at `local-llm-eval 08a94af` /
`EMR_AI_24clinic 543e1f9`. Main PC `EMR_AI_24clinic` advanced
`543e1f9 -> c6dc30c` (`feat(case-review): add core6 r3 rule context`,
clinical-assist track); `app/llm/` unchanged, so the A/B contract basis is intact.

Process-safety incident (low severity, no data loss): a user-opened Excel view of
`knowledge/master_data/처방자료-모두.xls` was flagged modified; run recovery killed
the user `EXCEL.EXE` and reverted the file. User confirmed view-only, so no data
was lost. Corrective rule: do not auto-revert files the agent did not modify and
do not kill user processes; on a shared workstation, STOP and surface user-caused
dirty state instead.

This result does not authorize Phase 2 heavy run, additional `/explain` cases,
matrix execution, EMR writes, cleanup, downloads, commit, or push.
