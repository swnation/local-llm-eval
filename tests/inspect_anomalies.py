"""Quick inspector for anomalous responses in Step 4."""
import json
from pathlib import Path

RESULTS = Path(r"c:\Github\local-llm-eval\results")

cases = [
    ("ministral-3-14b-reasoning_20260516_050415.json", "D_02"),
    ("hari-8b-i1_20260516_050107.json", "D_02"),
    ("clinical-hari-q5-current_20260516_050002.json", "A_02"),
    # 추가 의심: gpt-oss MIXED_LANGUAGE 3건
    ("gpt-oss-20b-low_20260516_045704.json", "C_01"),
    ("gpt-oss-20b-low_20260516_045704.json", "C_02"),
    # 추가: hari-8b A_02 PHI_LEAK
    ("hari-8b-i1_20260516_050107.json", "A_02"),
]

for fname, target in cases:
    p = RESULTS / fname
    d = json.loads(p.read_text(encoding="utf-8"))
    label = d.get("model_label", fname)
    for t in d["tests"]:
        if t["id"] == target:
            print("=" * 70)
            print(f"{label} / {target}")
            print(f"  success={t.get('success')}  elapsed={t.get('elapsed_sec')}s  tokens={t.get('completion_tokens')}")
            resp = t.get("response", "") or ""
            print(f"  len={len(resp)} chars")
            print(f"--- response (first 500 chars) ---")
            print(resp[:500])
            print(f"--- end ---")
            print()
            break
