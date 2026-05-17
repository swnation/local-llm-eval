# Claude Code Handoff: 64GB Upgrade

Date: 2026-05-17

Purpose: resume `c:\Github\local-llm-eval` after the workstation RAM upgrade from 32GB to 64GB.

## Frozen State

- Track 1 is closed: R4.1 GO.
- v0.3 scoring/prompt corrections are committed in `0978cff`.
- v0.3 apples-to-apples rescore comparison is committed in `f714475`.
- Current pre-upgrade freeze commit should include this handoff and `PROJECT_CONTEXT.md` 64GB banner.
- `PROJECT_CONTEXT.md` is the authoritative entry point.

Current comparison baseline:

| Model | A | B | C | D | Total | HF |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B 32GB preview, thinking-off | 2.50 | 3.33 | 3.00 | 5.00 | 3.38 | 0 |
| gpt-oss dynamic, C=medium and others low | 2.75 | 2.33 | 3.33 | 5.00 | 3.31 | 0 |

Decision before upgrade: Qwen is priority 1 challenger, not a production replacement yet. Qwen leads by +0.08 on v0.3 but gpt-oss still has operational simplicity and stronger A/C.

## First Checks After Upgrade

Run these before model work:

```powershell
git -c safe.directory=C:/Github/local-llm-eval log --oneline -5
git -c safe.directory=C:/Github/local-llm-eval status --short
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
ollama ps
ollama list
```

Expected repo state: clean working tree, latest commit is the 64GB handoff/freeze commit.

## First Experiment

Do not start with the full `models_config_part2.json` matrix. Start with Qwen thinking-on only:

```powershell
python eval_runner_auto.py --config models_config_qwen35b_thinking_on_64gb.json --prompts prompts/test_suite_v0.3_d_only.json
```

Then score the exact timestamped raw result, replacing the timestamp:

```powershell
python score_runner.py --prompts prompts/test_suite_v0.3_d_only.json --results-glob "results/qwen3.6-35b-a3b-64gb-thinking-on_<TIMESTAMP>.json" --output results/_scored_qwen35b_64gb_thinking_on_d_smoke_v03_<YYYYMMDD>
```

If D smoke has `hard_fail 0`, run full 13:

```powershell
python eval_runner_auto.py --config models_config_qwen35b_thinking_on_64gb.json --prompts prompts/test_suite_v0.3.json
python score_runner.py --prompts prompts/test_suite_v0.3.json --results-glob "results/qwen3.6-35b-a3b-64gb-thinking-on_<TIMESTAMP>.json" --output results/_scored_qwen35b_64gb_thinking_on_full_v03_<YYYYMMDD>
```

## Next Part 2 Order

1. Qwen3.6-35B-A3B thinking-on: D smoke, then full 13 if safe.
2. Gemma 4 26B, then 31B: try `ollama pull` first; GGUF import only if registry misses.
3. magistral retry: use an explicit Mistral V7 chat template Modelfile before rerunning.
4. exaone4-32b split: isolated round; empirically choose `num_gpu` by full GPU then 40/32/24 on OOM.
5. After scoring with v0.3, update `PROJECT_CONTEXT.md` §6 and §7.

Deferred items:

- q8 KV runtime matrix: separate global-runtime round only.
- gpt-oss `reasoning_effort='high'`: selective 1-2 prompt experiment after Part 2, unless the user asks otherwise.

## Collaboration Note

User preference for the next phase: Claude Code should focus on planning, cross-checking, and feedback. Avoid launching long experiments unless the user explicitly assigns execution. When the user reports GPT/session output, verify artifact existence, scored markdown headers, git status/log, and obvious metric consistency.
