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

Confirmed via SSH on 2026-05-18. Connection verified, Ollama running, models pulled, benchmarks executed.

```text
sub_host: DESKTOP-ATD4TUK
os: Windows (exact build TBD)
cpu: AMD Ryzen 7 5800X
ram: 32 GB
gpu_count: 1
gpu: NVIDIA GeForce RTX 4070 Ti SUPER
vram: 16 GB
nvidia_driver: TBD
python: TBD
ollama_version: TBD
ollama_models: qwen3:8b, qwen3:14b, gpt-oss:20b, qwen3:30b-a3b
connection_method: ssh -i C:\Users\swnat\.ssh\codex_sub_ed25519 swnat@192.168.68.52
shared_folder_or_repo_path: C:\Github\local-llm-eval
intended_role: sub20b_eval_runner
```

### Benchmark Results (2026-05-18, ollama_probe.py)

| Model | Host | tok/s | Notes |
|---|---|---:|---|
| `qwen3:14b` | mainpc | ~57 | num_ctx uncontrolled (may be >4k) |
| `qwen3:14b` | subpc | ~62 | stable; mainpc와 실질 동급 |
| `gpt-oss:20b` | mainpc | ~82 | num_ctx=131k 상태 (불리) |
| `gpt-oss:20b` | subpc | ~135 | num_ctx=4k 추정; 같은 ctx면 메인도 향상 가능 |
| `qwen3:30b-a3b` | mainpc | ~31 (warm) | cold load ~19s |
| `qwen3:30b-a3b` | subpc | ~24 (warm) | cold load ~213s; 반복 러너 비실용 |

**Fair-compare 주의**: 메인은 일부 모델에서 Ollama가 큰 num_ctx로 잡혀 있어 tok/s가 낮게 나올 수 있음. 순수 비교는 `num_ctx=4096` 강제 후 재측정 필요.

### Sub-Computer Role Assignment

| Role | Models | Rationale |
|---|---|---|
| Primary runner | `qwen3:14b`, `gpt-oss:20b` | 62~135 tok/s, 16GB VRAM 내 안정 |
| Low-resource fallback | `qwen3:8b` | 5.2 GB, sub-second per prompt |
| Experimental limit | `qwen3:30b-a3b` | cold 213s, warm 24 tok/s — 1회성 실험만 |
| Not suitable | 35B+, long context, RAG-heavy | VRAM/RAM 한계 → 메인 전용 |

Intended roles:

- `sub20b_eval_runner` — 8B/14B/20B D-smoke, quick eval, 반복 벤치
- `rag_eval_runner` — qwen3:8b/14b + RAG 빠른 반복 (메인에서 최종 비교)

### Standardized Commands (run from mainpc)

**Config**: `models_config_subpc.json` (qwen3:8b, qwen3:14b, gpt-oss:20b only)

```powershell
# SSH alias (if configured): ssh subpc
# Full form:
$SSH = "ssh -i C:\Users\swnat\.ssh\codex_sub_ed25519 swnat@192.168.68.52"

# 1. Probe (single model tok/s check)
Invoke-Expression "$SSH `"cd /d C:\Github\local-llm-eval && python tools/ollama_probe.py qwen3:14b`""

# 2. D-smoke only (quick safety gate)
Invoke-Expression "$SSH `"cd /d C:\Github\local-llm-eval && python eval_runner_auto.py --config models_config_subpc.json --prompts prompts/test_suite_v0.3.json`""

# 3. Full 13 eval (same command, config determines scope)
# Same as above — models_config_subpc.json runs all 3 models × 13 prompts

# 4. Result retrieval (scp to mainpc)
scp -i C:\Users\swnat\.ssh\codex_sub_ed25519 "swnat@192.168.68.52:C:/Github/local-llm-eval/results/*subpc*" C:\Github\local-llm-eval\results\subpc\
```

**After retrieval**: score/interpret on mainpc. Subpc produces raw results; mainpc is source of truth for scoring and documentation.

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
