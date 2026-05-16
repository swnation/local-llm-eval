# Local LLM Eval Prompts — Clinical-Assist v0.3

> v0.3 is a narrow scoring/prompt correction layer over the v0.2 final prompt set.
> Full prompt text lives in `test_suite_v0.3.json`; the v0.2 prose document remains historical context.

## Scope

v0.3 keeps the same 13 prompt IDs and the same LLM role boundary:

- A_charting 4
- B_needs_review 3
- C_rule_finding 3
- D_json_phi 3

No new clinical task is introduced. The change is limited to the four `SCORING_CONTRACT.md §13` backlog fixes needed before larger part 2 model comparisons.

## Changes From v0.2

1. D_01 forbidden false-positive fix
   - Removed broad forbidden substrings `"확정"`, `"오류"`, and `"변경"` from D_01.
   - Replaced them with command/assertion regex patterns such as `변경하십시오`, `수정하십시오`, and `오류입니다`.
   - Input-derived noun phrases such as `"당뇨 약제 변경"` are no longer penalized.

2. A_04 required marker hardening
   - `format_requirements.required_marker` is now structured:

```json
{"text": "[확인 필요]", "min_count": 1}
```

3. Sentence-count tolerance
   - Default scorer tolerance is now ±2 instead of ±1.
   - This reduces false format failures from medical abbreviations and numeric punctuation.

4. Format-only score definition
   - `required_missing=0`, `forbidden_present<=2`, `format_pass=false` now scores 4.
   - D JSON-only format violations still hard_fail before this branch.

## Files

- Current full suite: `prompts/test_suite_v0.3.json`
- Current D-only smoke subset: `prompts/test_suite_v0.3_d_only.json`
- Historical full prose doc: `prompts/local-llm-eval-prompts-clinical-assist-v0.2.md`
- Scoring contract: `SCORING_CONTRACT.md`

## Compatibility

v0.2 result tables remain valid historical baselines. New part 2 runs should label prompt version explicitly. If a v0.2 raw run is rescored with v0.3, report it as a **v0.3 rescore**, not as the original v0.2 score.
