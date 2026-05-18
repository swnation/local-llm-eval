# Connected Environment Handoff - 2026-05-18

Purpose: quick environment brief for Claude/Codex sessions that do not know the
newly connected runtime, secondary GPU, or sub-machine assumptions.

Use this as an environment handoff only. Do not treat it as an evaluation result
or production decision record.

---

## 1. Confirmed From Current Codex Shell

Collected on 2026-05-18 from `C:\Github`.

| Item | Value |
|---|---|
| Visible host | `MAINPC` |
| Workspace root | `C:\Github` |
| Local LLM eval repo | `C:\Github\local-llm-eval` |
| Shell | Windows PowerShell |
| OS reported by runtime | `Microsoft Windows 10.0.26200` |
| OS build from `cmd /c ver` | `10.0.26200.8457` |
| CPU | `AMD Ryzen 9 9950X 16-Core Processor` |
| Logical processors | `32` |
| RAM | 63.6 GB total confirmed from Claude session on 2026-05-18; 2 x 32 GB `F5-5600J3636D32G` |
| RAM speed | WMI reports 4800 MT/s (JEDEC base); user confirmed XMP enabled at 5600 MT/s |
| Disk C: | 1.86 TB total / 1.17 TB used / 693 GB free, confirmed from Claude session on 2026-05-18 |
| Python | `3.12.10` |
| Ollama | `0.24.0` |
| Git repo status at check | `main...origin/main`, no tracked changes reported |

GPU inventory from `nvidia-smi`:

| GPU | VRAM | Driver |
|---|---:|---|
| NVIDIA GeForce RTX 5080 | 16303 MiB | 591.86 |
| NVIDIA GeForce RTX 3070 | 8192 MiB | 591.86 |

Confirmation note:

- The original sandboxed Codex shell could not confirm RAM and disk free-space:
  `Win32_*`, `systeminfo`, and `fsutil volume diskfree` checks returned access
  denied under that sandboxed user.
- A later Claude session on 2026-05-18 confirmed RAM and C: disk capacity from
  the local machine. Treat XMP 5600 MT/s as user-confirmed runtime context, not
  a WMI-observed value.

---

## 2. Ollama Models Currently Visible

`ollama list` showed these local model names:

| Model | Size | Relevant use / round |
|---|---:|---|
| `mixtral:8x7b` | 26 GB | Round 9 MoE comparator; D hard-fail risk observed |
| `qwen3:30b-a3b` | 18 GB | Round 9 MoE comparator; reasoning leak / D hard-fail risk observed |
| `qwen3:14b` | 9.3 GB | Round 9 small dense candidate; matched gpt-oss baseline on non-RAG v0.3 |
| `gemma3:12b` | 8.1 GB | Round 9 dense comparator; D markdown-fence hard-fail, possible prompt reinforcement target |
| `qwen3:8b` | 5.2 GB | Round 9 small dense candidate; low-resource RAG-candidate lane |
| `qwen3.6:35b-a3b` | 23 GB | Part 2 Qwen challenger; thinking-off preview and thinking-on maxtok8k diagnostic |
| `hari-q3-14b-i1-chatml:latest` | 8.6 GB | Track 1 auxiliary ChatML fallback experiment |
| `hari-q3-8b-i1-chatml:latest` | 4.8 GB | Track 1 auxiliary ChatML fallback experiment |
| `ministral-3-14b-reasoning:latest` | 11 GB | Track 1 / part 2 diagnostic candidate |
| `hari-q3-14b-i1:latest` | 8.6 GB | Track 1 quick-rerun candidate |
| `hari-q3-8b-i1:latest` | 4.8 GB | Track 1 quick-rerun candidate |
| `exaone4-32b-iq4-4k:latest` | 17 GB | Part 2 split/offload candidate |
| `gpt-oss:20b` | 13 GB | Current provisional dynamic-effort baseline; R4/R4.1 and maxtok8k fair-compare |
| `clinical-hari-q5:latest` | 5.9 GB | Track 1 quick-rerun candidate |
| `qwen3-vl:8b` | 6.1 GB | Installed multimodal model; not part of current text baseline |
| `gemma4:latest` | 9.6 GB | Track 1 quick-rerun candidate / Gemma-family baseline |

---

## 3. Sub-Computer / Remote Environment Status

This session can see `MAINPC` only. If a separate sub-computer is connected,
its specs are not automatically confirmed from this shell.

Fill or confirm before Claude uses the sub-computer for any run:

```text
sub_host:
os:
cpu:
ram:
gpu_count:
gpu:
vram:
nvidia_driver:
python:
ollama_version:
ollama_models:
connection_method:
shared_folder_or_repo_path:
intended_role:
```

Suggested intended roles:

- `qwen35b_preview`
- `part2_64gb_runner`
- `q8kv_runtime_round`
- `rag_eval_runner`
- `secondary_gpu_experiment`

---

## 4. Evaluation Labeling Rules

Any result produced after the environment change must record runtime metadata.
Do not merge it into the existing quick-rerun baseline without labels.

Minimum metadata for each new run:

```text
run_label:
host:
repo_commit:
prompt_suite:
model_id:
ollama_name:
quant:
provider:
num_ctx:
max_tokens:
kv_cache_type:
flash_attention:
reasoning_or_thinking_mode:
gpu_used:
ram_confirmed:
oom_or_partial_offload:
```

Recommended label examples:

```text
qwen35b_part2_64gb_maxtok8k_thinking_on_mainpc
qwen3_14b_rag_eval_defaultkv_mainpc
gpt_oss_dynamic_q8kv_flash_mainpc
subpc_qwen35b_preview_q8kv
```

---

## 5. Guardrails For Claude

- Do not assume RAM from old notes if the current run depends on memory limits.
- Do not mix default/f16 KV results with `q8_0` KV results in one ranking table
  unless the table explicitly separates runtime labels.
- Do not treat Reddit or LocalLLM claims as evidence. Use them only to prioritize
  candidates for local measurement.
- Do not use `reasoning_effort=medium` for `gpt-oss:20b` D-category JSON-only
  work unless a new labeled verification round explicitly approves it.
- For Qwen thinking-on runs, verify `max_tokens` before judging failures:
  previous 2048-cap runs could exhaust the output budget on reasoning trace.

---

## 6. Current Project Decision Context

Short version for Claude:

- Track 1 v0.2/v0.3 local LLM evaluation is closed through R4.1 GO.
- Current provisional production baseline remains `gpt-oss:20b` dynamic effort,
  unless superseded by a labeled, reviewed later round.
- Strong challengers already observed in project docs:
  - `qwen3.6:35b-a3b` thinking-on with higher token budget.
  - `qwen3:14b` / `qwen3:8b` as small dense candidates, especially for future
    RAG-augmented architecture.
- Next work should keep two tracks separate:
  - evaluation result interpretation
  - local LLM environment / runtime upgrade plan

Primary repo entry point remains:

```text
C:\Github\local-llm-eval\PROJECT_CONTEXT.md
```
