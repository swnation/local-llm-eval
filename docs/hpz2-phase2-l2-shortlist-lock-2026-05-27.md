---
id: hpz2-phase2-l2-shortlist-lock-2026-05-27
project: local-llm-eval
type: decision
status: active
created: 2026-05-27
scope: HP Z2 llama.cpp Phase 2 L2 shortlist lock after overnight matrix and probes
related:
  - docs/hpz2-phase2-ladder-progress-v0.1.md
  - docs/hpz2-phase2-backend-lane-decision-2026-05-26.md
  - docs/hpz2-llamacpp-phase2-l2-runner-2026-05-26.md
  - models_config_hpz2_llamacpp_phase2_l2_v0.1.json
  - ../hpz2-run-artifacts/results/hpz2_llamacpp_l2_integrated_report_20260527.md
---

# HP Z2 Phase 2 L2 Shortlist Lock - 2026-05-27

Decision lock: HP Z2 Phase 2 candidate evaluation keeps llama.cpp as the
primary backend and promotes a four-model L2 primary shortlist. This document
codifies the result of the 2026-05-27 overnight `--tier all` matrix and bonus
probes. It does not authorize model execution, cleanup, downloads, L3/L4/L5,
real `/explain`, EMR writes, commit, or push.

## Evidence

Primary integrated report:

```text
C:\Github\hpz2-run-artifacts\results\hpz2_llamacpp_l2_integrated_report_20260527.md
```

Artifact repo commit: `80907506d07686e84df2cf6e9448b5c632a7dffd`.

Key result directories:

| Result | Path | Outcome |
|---|---|---|
| Current config full matrix | `results/llamacpp_phase2_l2_20260527_043835/` | 13 models x 4 cases, 52/52 API, 52/52 core and strong citation, 39/52 semantic, 13 RA-05 manual review |
| Granite 4.1 30B probe | `results/llamacpp_phase2_l2_20260527_053341/` | official IBM GGUF, 4/4 API and citation, 3/4 semantic plus RA-05 manual review |
| EXAONE 4.5 probes | `_054139/`, `_193206/`, `_193533/` | Q4_K_M and BF16 load failures under llama.cpp `b9333` |
| Aya Expanse 32B probe | `results/llamacpp_phase2_l2_20260527_055825/` | API path worked, but citation/semantic quality was poor |
| K-EXAONE official IQ4_XS probe | `results/llamacpp_phase2_l2_20260527_072333/` | load failure and server termination issue |
| K-EXAONE Q2_K fallback | `results/llamacpp_phase2_l2_20260527_193900/` | runnable community fallback; secondary viability evidence only |

RA-05 manual-review cells are expected under the current user-owned wording
baseline. They are not treated as runtime instability.

## Primary Shortlist

| Label | Role | Evidence |
|---|---|---|
| `hpz2-l2-qwen36-35b-a3b` | first-pass default | fastest stable primary candidate, full matrix avg 2198.2 ms, citation 4/4 |
| `hpz2-l2-qwen36-35b-a3b-mtp-mxfp4` | primary comparator | full matrix avg 2552.2 ms, citation 4/4 |
| `hpz2-l2-qwen36-35b-a3b-mtp-q8` | quality variant | full matrix avg 3037.2 ms, citation 4/4 |
| `hpz2-l2-granite-41-30b-q4km` | official enterprise/RAG diversity comparator | IBM official GGUF, probe avg 13856.2 ms, citation 4/4 |

The config tier is `primary_shortlist`. It is a decision surface, not an
execution authorization.

## Reference / Historical

These remain useful comparison evidence, but are not current first-pass
defaults:

- `hpz2-l2-qwen35-122b-a10b`
- `hpz2-l2-qwen35-122b-a10b-mtp`
- `hpz2-l2-openai-gpt-oss-120b`
- `hpz2-l2-mistral-small-32-24b`
- `hpz2-l2-llama-33-70b-instruct`
- `hpz2-l2-gemma-4-31b-it`

Gemma 4 26B and GPT-OSS 20B variants remain comparison carry from the full
matrix, but are not part of the locked primary shortlist.

## Current Primary Exclusions

| Candidate | Decision | Reason |
|---|---|---|
| EXAONE 4.5 33B | exclude from current primary | official LG GGUF has strong RAG/Korean interest, but current llama.cpp `b9333` failed with tensor-count mismatch in Q4_K_M and BF16 probes |
| Aya Expanse 32B | exclude | API path worked, but L2 citation/semantic behavior was not useful for this RAG shortlist |
| K-EXAONE 236B official IQ4_XS | exclude | official GGUF default profile failed to load and did not exit cleanly |
| K-EXAONE 236B Q2_K mradermacher | secondary hold only | runnable but low-trust community fallback quant; not primary proof |
| Nemotron Super 49B | deferred | GGUF publisher verification was not completed for this run |

## Operational Carry

- llama.cpp remains the primary lane; LM Studio remains secondary/historical.
- `models_config_hpz2_llamacpp_phase2_l2_v0.1.json` now includes Granite 4.1
  30B and the `primary_shortlist` tier.
- Existing catalog models remain in the config for reproducibility and
  reference. Their presence does not imply primary selection.
- The 2026-05-27 cleanup removed many previously tested local model folders.
  Treat `model_path` entries as expected canonical locations, not proof that the
  files are currently present on HP. Future execution requires a fresh
  file-existence, disk, and download preflight.
- No real `/explain` is authorized by this lock.
- No EMR write is authorized by this lock.
- RA-03 remains fixed as `sme + trimesy + lacto2`, `dx=a090`, `age=1`.
- L3/L4/L5 require separate GO and a fresh preflight.

## Next Decision Surface

Recommended next step is repo review of this codification, then user choice
between:

1. L3 normalizer feasibility on the locked primary shortlist.
2. L5 heavy-run planning only after RA-03 user-owned checks and EMR read-only
   constraints are reconfirmed.
3. EXAONE 4.5 runtime-support watch, not immediate execution.
