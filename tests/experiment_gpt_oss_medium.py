"""
보조 실험 §5.2: gpt-oss reasoning_effort='medium' 으로 C 카테고리 재호출.
default 'low'에서는 C_01/C_02 응답이 case_id 한 줄만 출력됨.
"""
import json
import urllib.request
from pathlib import Path
from datetime import datetime

PROMPTS = json.loads(
    Path(r"c:\Github\local-llm-eval\prompts\test_suite_v0.2.json").read_text(encoding="utf-8")
)

C_TESTS = [t for t in PROMPTS["tests"] if t["category"] == "C_rule_finding"]
assert len(C_TESTS) == 3, f"expected 3 C tests, got {len(C_TESTS)}"

results = {
    "model_label": "gpt-oss-20b-medium",
    "base_url": "http://localhost:11434/v1",
    "timestamp": datetime.now().isoformat(),
    "prompts_version": PROMPTS.get("version"),
    "experiment": "reasoning_effort='medium' for C category (vs 'low' baseline)",
    "tests": [],
}

for t in C_TESTS:
    body = {
        "model": "gpt-oss:20b",
        "messages": [
            {"role": "system", "content": t["system"]},
            {"role": "user", "content": t["user"]},
        ],
        "temperature": t.get("temperature", 0.3),
        "max_tokens": t.get("max_tokens", 2048),
        "stream": False,
        "reasoning_effort": "medium",  # the key change
    }
    print(f"[{t['id']}] {t['title']}", flush=True)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    import time
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
        print(f"   OK  {elapsed:.1f}s, {completion_tokens} tokens, {tok_per_sec} tok/s", flush=True)
    except Exception as e:
        elapsed = time.time() - start
        print(f"   FAIL  {e}", flush=True)
        results["tests"].append({
            "id": t["id"],
            "category": t["category"],
            "title": t["title"],
            "success": False,
            "error": str(e),
        })

out_path = Path(r"c:\Github\local-llm-eval\results") / f"gpt-oss-20b-medium_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {out_path}")
