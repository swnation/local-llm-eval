"""
보조 실험 §5.6: clinical-hari-q5 A_02 단독 retry x3.
Step 4에서 elapsed 2.4s + completion_tokens 283 but response empty.
ollama 응답 parsing 또는 reasoning trace only 가능성 점검.
"""
import json
import urllib.request
import time
from pathlib import Path
from datetime import datetime

PROMPTS = json.loads(
    Path(r"c:\Github\local-llm-eval\prompts\test_suite_v0.2.json").read_text(encoding="utf-8")
)
A02 = next(t for t in PROMPTS["tests"] if t["id"] == "A_02")

results = {
    "model_label": "clinical-hari-q5-current",
    "experiment": "A_02 retry x3 — diagnose Step 4 empty response (283 tokens generated, 0 chars in content)",
    "timestamp": datetime.now().isoformat(),
    "trials": [],
}

for trial in range(1, 4):
    body = {
        "model": "clinical-hari-q5:latest",
        "messages": [
            {"role": "system", "content": A02["system"]},
            {"role": "user", "content": A02["user"]},
        ],
        "temperature": A02.get("temperature", 0.3),
        "max_tokens": A02.get("max_tokens", 2048),
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
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read().decode("utf-8"))
        elapsed = time.time() - start
        # Check both OpenAI compat path AND ollama-native fields
        content = resp["choices"][0]["message"].get("content", "")
        reasoning = resp["choices"][0]["message"].get("reasoning_content", "")  # some openai-compat impls
        usage = resp.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        results["trials"].append({
            "trial": trial,
            "success": True,
            "elapsed_sec": round(elapsed, 1),
            "completion_tokens": completion_tokens,
            "content_len_chars": len(content or ""),
            "reasoning_len_chars": len(reasoning or ""),
            "content": content,
            "reasoning_content": reasoning,
            "raw_full_response_keys": list(resp["choices"][0]["message"].keys()),
        })
        print(f"   OK  {elapsed:.1f}s, {completion_tokens} tokens, content={len(content or '')} chars, reasoning={len(reasoning or '')} chars", flush=True)
        if content:
            print(f"   content preview: {content[:150]}", flush=True)
    except Exception as e:
        elapsed = time.time() - start
        print(f"   FAIL  {e}", flush=True)
        results["trials"].append({
            "trial": trial,
            "success": False,
            "error": str(e),
        })

out_path = Path(r"c:\Github\local-llm-eval\results") / f"clinical_hari_a02_retry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {out_path}")
