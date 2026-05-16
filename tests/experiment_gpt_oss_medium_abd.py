"""
R4 MF-1 실행: gpt-oss-20b reasoning_effort='medium' 으로 A/B/D 추가 평가.

C는 이미 §5.2에서 검증됨 (avg 3.33). 시나리오 C 추천을 production 후보로 승격하려면
A/B/D도 medium에서:
  - D JSON-only strict 유지하는지
  - A/B에서 forbidden/verbosity 증가하는지
확인 필요.

저장: results/gpt-oss-20b-medium-abd_<ts>.json (score_runner가 후속 채점)
"""
import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

PROMPTS = json.loads(
    Path(r"c:\Github\local-llm-eval\prompts\test_suite_v0.2.json").read_text(encoding="utf-8")
)

TARGET_IDS = ["A_01", "A_02", "A_03", "A_04", "B_01", "B_02", "B_03", "D_01", "D_02", "D_03"]
TARGET_TESTS = [t for t in PROMPTS["tests"] if t["id"] in TARGET_IDS]
assert len(TARGET_TESTS) == 10, f"expected 10 tests, got {len(TARGET_TESTS)}"

ts = datetime.now()
results = {
    "model_label": "gpt-oss-20b-medium",
    "base_url": "http://localhost:11434/v1",
    "timestamp": ts.isoformat(),
    "prompts_version": PROMPTS.get("version"),
    "experiment": "R4 MF-1: medium effort for A/B/D (C already covered in §5.2 baseline)",
    "tests": [],
}

print(f"[gpt-oss medium A/B/D] {len(TARGET_TESTS)} prompts", flush=True)

for i, t in enumerate(TARGET_TESTS, 1):
    body = {
        "model": "gpt-oss:20b",
        "messages": [
            {"role": "system", "content": t["system"]},
            {"role": "user", "content": t["user"]},
        ],
        "temperature": t.get("temperature", 0.3),
        "max_tokens": t.get("max_tokens", 2048),
        "stream": False,
        "reasoning_effort": "medium",
    }
    print(f"  [{i:2d}/{len(TARGET_TESTS)}] {t['id']} — {t['title']}", flush=True)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            resp = json.loads(r.read().decode("utf-8"))
        elapsed = time.time() - start
        content = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        tok_per_sec = round(completion_tokens / elapsed, 1) if elapsed > 0 else 0
        results["tests"].append({
            "id": t["id"],
            "category": t["category"],
            "title": t["title"],
            "expected": t.get("expected", ""),
            "success": True,
            "elapsed_sec": round(elapsed, 1),
            "completion_tokens": completion_tokens,
            "tok_per_sec": tok_per_sec,
            "response": content,
        })
        print(f"        OK  {elapsed:.1f}s, {completion_tokens} tokens, {tok_per_sec} tok/s", flush=True)
    except Exception as e:
        elapsed = time.time() - start
        print(f"        FAIL  {e}", flush=True)
        results["tests"].append({
            "id": t["id"],
            "category": t["category"],
            "title": t["title"],
            "success": False,
            "error": str(e),
        })

out_path = Path(r"c:\Github\local-llm-eval\results") / f"gpt-oss-20b-medium-abd_{ts.strftime('%Y%m%d_%H%M%S')}.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {out_path}")
