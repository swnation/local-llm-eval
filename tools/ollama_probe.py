import argparse
import json
import time
import urllib.request


def generate(model: str, prompt: str, num_predict: int) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=600) as response:
        raw = response.read().decode("utf-8")
    elapsed = time.perf_counter() - started
    result = json.loads(raw)
    result["_wall_seconds"] = elapsed
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--num-predict", type=int, default=64)
    parser.add_argument(
        "--prompt",
        default="Say hello in one short sentence, then list three local LLM benchmark checks.",
    )
    args = parser.parse_args()

    result = generate(args.model, args.prompt, args.num_predict)
    eval_count = result.get("eval_count") or 0
    eval_duration = result.get("eval_duration") or 0
    prompt_eval_count = result.get("prompt_eval_count") or 0
    prompt_eval_duration = result.get("prompt_eval_duration") or 0

    summary = {
        "model": args.model,
        "wall_seconds": round(result["_wall_seconds"], 3),
        "load_seconds": round((result.get("load_duration") or 0) / 1e9, 3),
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_seconds": round(prompt_eval_duration / 1e9, 3),
        "eval_count": eval_count,
        "eval_seconds": round(eval_duration / 1e9, 3),
        "tokens_per_second": round(eval_count / (eval_duration / 1e9), 2)
        if eval_count and eval_duration
        else None,
        "done_reason": result.get("done_reason"),
        "response_preview": result.get("response", "")[:300],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
