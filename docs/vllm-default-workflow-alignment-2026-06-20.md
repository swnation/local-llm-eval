---
id: vllm-default-workflow-alignment-2026-06-20
project: local-llm-eval
type: alignment
status: current-baseline
created: 2026-06-20
scope: DGX Spark vLLM baseline for local model use across the workspace
related:
  - docs/dgx-spark-asus-bootstrap-probe-plan-2026-06-07.md
  - docs/dgx-spark-asus-runner-audit-plan-2026-06-07.md
  - docs/dgx-spark-artifact-repo-root-decision-plan-2026-06-07.md
  - ../AGENTS.md
---

# vLLM Default Workflow Alignment

## Decision

Future local-model work should use vLLM as the default serving baseline.

Default resident endpoints:

| Host | Role | Endpoint | Served model id | Status on 2026-06-20 |
|---|---|---|---|---|
| `dgxasus` | GX10 / memory owner / primary workspace | `http://127.0.0.1:8000/v1/chat/completions` | `qwen3.6-35b-a3b` | `/v1/models` responded |
| `dgxgiga` | DGX Spark node 2 / execution peer after gate | `http://127.0.0.1:8004/v1/chat/completions` | `qwen3.6-35b-a3b-dgxgiga` | `/v1/models` responded |

This replaces the old default assumption that new work should target HP Z2,
LM Studio, Ollama, or llama.cpp first. Those lanes remain historical evidence,
fallbacks, or special experiments only.

## What This Does Not Approve

This alignment does not approve:

- PHI input or raw patient data.
- real `/explain` use.
- large model start/stop/switch.
- Open WebUI profile refresh.
- EMR source writes or RAG reindexing.
- artifact mutation.
- relay update, commit, push, or backup.
- promotion of Qwen35 output to final truth without source verification.

All of those remain separate gates.

## Project Alignment Table

| Project | vLLM baseline meaning | Current action |
|---|---|---|
| `agent-round-manager` | Qwen35 vLLM is the default helper worker for non-PHI packets, watcher tasks, and source-pointer drafts. | Already mostly aligned. Keep Codex/Claude/user as verifier and gate owners. |
| `local-llm-eval` | DGX/vLLM is the new runtime direction for future eval lanes. HP/llama.cpp docs are legacy evidence unless explicitly reopened. | Use this document plus DGX preflight evidence before new execution. |
| `EMR_AI_24clinic` | `/explain` may support vLLM through OpenAI-compatible chat completions, but production use remains disabled until reviewed. | Review the in-flight vLLM provider patch before adopting. |
| `clinic-audit-review` | vLLM/Qwen35 can help with non-PHI planning, summaries, and source-pointer drafts only. | Do not send PHI or raw patient screenshots. |
| `24clinic_training` | vLLM/Qwen35 can help with non-PHI seed review and wording, not training-data truth. | Keep dataset gates separate. |
| `codex-solo` | vLLM/Qwen35 is an advisory helper lane, not coordinator authority. | Keep shared memory, repo docs, tests, and user GO as source of truth. |

## Legacy Lane Reading Rule

When older docs mention HP Z2, LM Studio, Ollama, or llama.cpp:

- treat them as historical evidence unless the active relay explicitly reopens
  that lane.
- do not port HP paths, PowerShell commands, Vulkan flags, or `hpz2-*` labels
  into DGX work by rename.
- do not compare old HP artifacts directly with DGX/vLLM artifacts without a
  reviewed comparison plan.

## RAG And Reranker Boundary

The current RAG problem is not solved by switching the serving backend to vLLM.

Current retrieval baseline remains:

```text
top_k = 5
min_similarity = 0.45
lexical_rerank = false
```

Reranker and retrieval changes remain separate evaluation gates. vLLM can serve
the answer model, but source reachability, citation policy, RAG index state, and
manual clinical judgment still need their own evidence.

## Next Gates

Recommended order:

1. Review the in-flight `EMR_AI_24clinic` vLLM provider patch.
2. Decide whether to make vLLM the default saved provider or keep it opt-in by
   env/settings for the first smoke.
3. Rebuild or locate the RAG index needed for retrieval-only probes.
4. Run a non-PHI vLLM `/explain` smoke only after EMR repo state is clean and
   the user opens that gate.
5. Record any DGX runtime artifacts in `dgx-spark-run-artifacts`, not
   `hpz2-run-artifacts`.
