#!/usr/bin/env python3
"""
findings_index.jsonl 생성기.

목적: scored_*.json 의 두꺼운 채점 결과를 retrieval-friendly 한 줄 인덱스로 압축.
사용 예: "D 카테고리에서 fence 붙인 모델?", "A에서 PHI_LEAK 케이스?" 같은 질문에 즉시 답.

각 줄 schema (jsonl):
{
  "model": "gpt-oss-20b-low",
  "prompt_id": "D_01",
  "category": "D_json_phi",
  "title": "Multiple findings -> JSON array summary",
  "score": 4,
  "hard_fail": false,
  "hard_fail_reason": "",
  "tags_auto": ["..."],
  "required_missing_n": 0,
  "forbidden_present_n": 2,
  "format_pass": true,
  "elapsed_sec": 20.2,
  "tok_per_sec": 18.2,
  "response_excerpt": "first 200 chars of response",
  "source_scored_file": "_scored_quick_rerun_20260516.json",
  "variant": "baseline"   // baseline | chatml | medium | a02_retry 등
}

사용법:
    python tools/build_findings_index.py
"""
import json
from pathlib import Path
from datetime import datetime

REPO = Path(r"c:\Github\local-llm-eval")
RESULTS = REPO / "results"
OUT = RESULTS / "findings_index.jsonl"


def variant_of(scored_file_name: str) -> str:
    if "hari8b_chatml" in scored_file_name:
        return "chatml"
    if "hari14b_chatml" in scored_file_name:
        return "chatml"
    if "gpt_oss_medium" in scored_file_name:
        return "medium"
    return "baseline"


def response_excerpt(model_label: str, prompt_id: str, results_dir: Path) -> str:
    """raw response 파일에서 첫 200자 추출."""
    # Match latest raw file by glob
    pattern = f"{model_label}_*.json"
    candidates = sorted(results_dir.glob(pattern), reverse=True)
    # exclude scored/comparison/log files
    candidates = [
        c for c in candidates
        if not c.name.startswith("_")
        and not c.name.startswith(".")
        and "_scored_" not in c.name
    ]
    if not candidates:
        return ""
    try:
        d = json.loads(candidates[0].read_text(encoding="utf-8"))
        for t in d.get("tests", []):
            if t.get("id") == prompt_id:
                resp = t.get("response", "") or ""
                return resp[:200].replace("\n", " ")
    except Exception:
        return ""
    return ""


def first_or_empty(lst):
    return lst[0] if lst else ""


def process_scored_file(scored_path: Path, out_lines: list):
    data = json.loads(scored_path.read_text(encoding="utf-8"))
    variant = variant_of(scored_path.name)
    for model_block in data.get("models", []):
        model_label = model_block.get("model_label", "?")
        for s in model_block.get("scored", []):
            entry = {
                "model": model_label,
                "variant": variant,
                "prompt_id": s.get("prompt_id"),
                "category": s.get("category"),
                "title": s.get("title"),
                "score": s.get("score"),
                "hard_fail": bool(s.get("hard_fail")),
                "hard_fail_reason": first_or_empty(s.get("hard_fail_reasons", [])),
                "tags_auto": s.get("tags_auto", []),
                "required_missing_n": len(s.get("required_missing", [])),
                "forbidden_present_n": len(s.get("forbidden_present", [])),
                "format_pass": s.get("format_pass"),
                "elapsed_sec": s.get("elapsed_sec"),
                "tok_per_sec": s.get("tok_per_sec"),
                "response_excerpt": response_excerpt(
                    model_label.replace(":", "_"),  # match filename pattern
                    s.get("prompt_id", ""),
                    RESULTS,
                ),
                "source_scored_file": scored_path.name,
            }
            out_lines.append(json.dumps(entry, ensure_ascii=False))


def main():
    scored_files = sorted([
        p for p in RESULTS.glob("_scored_*.json")
        if "validation" not in p.name  # exclude tests/fixtures self-test
    ])
    print(f"Scored files: {len(scored_files)}")
    for p in scored_files:
        print(f"  - {p.name}")

    out_lines = []
    for sp in scored_files:
        process_scored_file(sp, out_lines)

    OUT.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    # Quick stats
    print(f"\nIndex saved: {OUT}")
    print(f"Total entries: {len(out_lines)}")
    counts = {}
    for line in out_lines:
        e = json.loads(line)
        m = e["model"]
        counts.setdefault(m, {"total": 0, "hard_fail": 0, "score_sum": 0})
        counts[m]["total"] += 1
        if e["hard_fail"]:
            counts[m]["hard_fail"] += 1
        if e["score"] is not None:
            counts[m]["score_sum"] += e["score"]
    print("\nPer-model summary:")
    print(f"{'model':<35} {'n':>4} {'avg':>6} {'HF#':>5}")
    for m, c in sorted(counts.items()):
        avg = c["score_sum"] / c["total"] if c["total"] else 0
        print(f"{m:<35} {c['total']:>4} {avg:>6.2f} {c['hard_fail']:>5}")

    # Build aux files
    write_aux(out_lines)


def write_aux(out_lines):
    """README + sample queries 별도 파일로."""
    aux = RESULTS / "findings_index.README.md"
    aux.write_text(f"""# findings_index.jsonl — Retrieval-friendly Eval Index

생성: {datetime.now().isoformat()}
총 entries: {len(out_lines)}

## 용도

scored JSON의 두꺼운 결과를 한 줄씩 압축한 인덱스. retrieval/필터링/요약에 유용.

## Schema (per line)

```json
{{
  "model": "<label>",
  "variant": "baseline | chatml | medium",
  "prompt_id": "A_01..D_03",
  "category": "A_charting | B_needs_review | C_rule_finding | D_json_phi",
  "title": "...",
  "score": 0..5,
  "hard_fail": true|false,
  "hard_fail_reason": "...",
  "tags_auto": [...],
  "required_missing_n": int,
  "forbidden_present_n": int,
  "format_pass": bool,
  "elapsed_sec": float,
  "tok_per_sec": float,
  "response_excerpt": "first 200 chars",
  "source_scored_file": "_scored_*.json"
}}
```

## Sample queries

```python
import json
from pathlib import Path

lines = [json.loads(l) for l in Path("results/findings_index.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

# Q1. D 카테고리에서 fence 붙인 모델?
fence_offenders = [
    e for e in lines
    if e["category"] == "D_json_phi"
    and "JSON_EXTRA_TEXT" in e["tags_auto"]
]
for e in fence_offenders:
    print(f"{{e['model']}} ({{e['variant']}}) / {{e['prompt_id']}}: {{e['hard_fail_reason']}}")

# Q2. A 카테고리에서 PHI_LEAK 발생한 케이스?
phi_in_a = [
    e for e in lines
    if e["category"] == "A_charting"
    and "PHI_LEAK" in e["tags_auto"]
]

# Q3. 만점 5점 받은 모델/prompt 조합?
five_pointers = [
    (e["model"], e["variant"], e["prompt_id"])
    for e in lines if e["score"] == 5
]

# Q4. 모델별 D 카테고리 평균 점수?
from collections import defaultdict
d_scores = defaultdict(list)
for e in lines:
    if e["category"] == "D_json_phi" and e["score"] is not None:
        d_scores[(e["model"], e["variant"])].append(e["score"])
for (m, v), scores in d_scores.items():
    print(f"{{m}} ({{v}}): {{sum(scores)/len(scores):.2f}} (n={{len(scores)}})")
```

## 갱신

`python tools/build_findings_index.py` 재실행 시 모든 `_scored_*.json` 새로 읽어 갱신.
""", encoding="utf-8")
    print(f"Aux README: {aux}")


if __name__ == "__main__":
    main()
