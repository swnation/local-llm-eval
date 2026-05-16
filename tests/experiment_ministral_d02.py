"""
보조 실험 §5.3: ministral D_02 단독 재시도. Step 4에서 0.1초/1 token 빈 응답.
max_tokens 늘리고 num_ctx 그대로 두고 재호출.
"""
import json
import urllib.request
import time
from pathlib import Path
from datetime import datetime

PROMPTS = json.loads(
    Path(r"c:\Github\local-llm-eval\prompts\test_suite_v0.2.json").read_text(encoding="utf-8")
)
D02 = next(t for t in PROMPTS["tests"] if t["id"] == "D_02")

results = {
    "model_label": "ministral-3-14b-reasoning",
    "experiment": "D_02 retry x3 with max_tokens=4096",
    "timestamp": datetime.now().isoformat(),
    "trials": [],
}

for trial in range(1, 4):
    body = {
        "model": "ministral-3-14b-reasoning",
        "messages": [
            {"role": "system", "content": D02["system"]},
            {"role": "user", "content": D02["user"]},
        ],
        "temperature": D02.get("temperature", 0.2),
        "max_tokens": 4096,  # 2048 → 4096
        "stream": False,
    }
    print(f"[trial {trial}/3]", flush=True)
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
        results["trials"].append({
            "trial": trial,
            "success": True,
            "elapsed_sec": round(elapsed, 1),
            "completion_tokens": completion_tokens,
            "response_len_chars": len(content),
            "response_starts_with": content[:50] if content else "(empty)",
            "response_full": content,
        })
        print(f"   OK  {elapsed:.1f}s, {completion_tokens} tokens, {len(content)} chars", flush=True)
    except Exception as e:
        elapsed = time.time() - start
        print(f"   FAIL  {e}", flush=True)
        results["trials"].append({
            "trial": trial,
            "success": False,
            "error": str(e),
        })

out_path = Path(r"c:\Github\local-llm-eval\results") / f"ministral_d02_retry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {out_path}")
