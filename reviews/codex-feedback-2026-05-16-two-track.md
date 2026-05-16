# Codex Feedback — Two-Track Plan and Claude Updates

> Date: 2026-05-16
> Scope: feedback on Claude's latest repo-organization and local LLM upgrade notes.

---

## Verdict

GO for the two-track split.

Claude's changes are directionally strong: `PROJECT_CONTEXT.md` is a useful session entry point, `findings_index.jsonl` is the right first retrieval surface, and R4 packet-first review keeps the next review from drifting into scorer/code redesign.

---

## What Looks Good

1. **PROJECT_CONTEXT.md as entry point**
   - Good fit for this repo.
   - It prevents new sessions from rereading every report and reopening settled R1/R2/R3 decisions.
   - The "금지사항" section is especially useful because this project has several tempting but out-of-scope branches.

2. **findings_index.jsonl**
   - This is the right lightweight version of "local RAG" for now.
   - It answers practical review questions faster than a full vector stack.
   - The sample queries are immediately useful.

3. **R4 packet strategy**
   - Correct to send only packet + report first.
   - `score_runner.py` and raw scored JSON should stay optional unless the reviewer challenges scoring.

4. **64GB/128GB priority**
   - Correct: before hardware expansion dominates the conversation, validate `gpt-oss medium A/B/D`.
   - 64GB part 2 is meaningful, but current blocker is interpretation and targeted missing experiments.

5. **Serena/OpenCode/MCP treatment**
   - Correctly kept as a separate track.
   - Borrowing the memory/indexing concept is useful; adopting a full tool stack now would distract from eval.

---

## Things To Tighten

1. **README current-state drift**
   - `README.md` still has older quick-rerun wording in places.
   - This is not a blocker because `PROJECT_CONTEXT.md` is now the entry point.
   - Recommended: avoid large README rewrites now; add links to the two track docs and let `PROJECT_CONTEXT.md` carry current status.

2. **RAG wording**
   - `PROJECT_CONTEXT.md §8` is an index of retrieval targets, not actual RAG yet.
   - Claude already notes this. Keep the distinction explicit.

3. **Qwen3.6 social signal**
   - Treat Reddit/LocalLLM claims as prioritization signals only.
   - The repo should decide by D smoke, full 13-prompt scores, hard_fail count, and PHI behavior.

4. **KV q8_0**
   - Valuable, but do not retroactively blend q8 results with the f16/default quick rerun.
   - Label q8 runs as a runtime matrix experiment.

5. **clinical-hari-q5**
   - Keep it as score leader but not automatic production winner.
   - Its A_02 quirk and JSON-style charting output need operational guidance before production use.

---

## Recommended Repo Shape

Two durable docs should exist alongside `PROJECT_CONTEXT.md`:

- `docs/experiment-track-2026-05-16.md`
  - what happened, current results, R4 status, v0.3 candidate fixes
- `docs/local-llm-upgrade-plan.md`
  - runtime/hardware/model/RAG upgrade plan, kept separate from quick-rerun scoring

This avoids turning README into a giant living notebook.

---

## Recommended Next Actions

1. Send R4 packet + quick rerun report.
2. If R4 GO, run `gpt-oss medium` on A/B/D.
3. Run Qwen3.6-35B-A3B as a clearly labeled `part2_preflight` preview.
4. Keep q8 KV as a separate runtime experiment with explicit labels.
5. Add a tiny query helper for `results/findings_index.jsonl` if manual querying becomes repetitive.

---

## Bottom Line

Claude's proposed organization is solid. The most important guardrail is separation:

- Track 1 = completed v0.2 experiment interpretation.
- Track 2 = local LLM runtime/model/RAG upgrade planning.

Do not let exploratory Qwen/q8/RAG work rewrite the already completed f16/default quick-rerun baseline.

