#!/usr/bin/env python3
"""
Clinical-Assist 모델 평가 스크립트

사용법:
  python eval_runner.py             # LM Studio (localhost:1234)
  python eval_runner.py --ollama    # Ollama (localhost:11434)

외부 라이브러리 의존성 없음. Python 표준 라이브러리만 사용.
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

# --- 설정 (필요 시 수정) ---
LM_STUDIO_URL = "http://localhost:1234/v1"
OLLAMA_URL = "http://localhost:11434/v1"
PROMPTS_FILE = "prompts/test_suite_v0.2.json"
RESULTS_DIR = "results"
TIMEOUT_SEC = 600  # 큰 모델은 첫 응답 오래 걸릴 수 있음


def load_prompts(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def call_model(base_url, model, system, user, temperature, max_tokens):
    """LM Studio / Ollama OpenAI 호환 API 호출"""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            elapsed = time.time() - start
            result = json.loads(resp.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        tok_per_sec = round(completion_tokens / elapsed, 1) if elapsed > 0 else 0

        return {
            "success": True,
            "elapsed_sec": round(elapsed, 1),
            "completion_tokens": completion_tokens,
            "tok_per_sec": tok_per_sec,
            "response": content,
        }
    except urllib.error.URLError as e:
        return {"success": False, "error": f"연결 오류: {e}. LM Studio Server가 켜져 있는지 확인하세요."}
    except Exception as e:
        return {"success": False, "error": f"오류: {type(e).__name__}: {e}"}


def run_evaluation(base_url, model_label):
    prompts_data = load_prompts(PROMPTS_FILE)

    results = {
        "model_label": model_label,
        "base_url": base_url,
        "timestamp": datetime.now().isoformat(),
        "prompts_version": prompts_data.get("version", "unknown"),
        "tests": [],
    }

    total = len(prompts_data["tests"])
    for i, test in enumerate(prompts_data["tests"], 1):
        print(f"[{i}/{total}] {test['id']} - {test['title']}")

        result = call_model(
            base_url=base_url,
            model=model_label,
            system=test["system"],
            user=test["user"],
            temperature=test.get("temperature", 0.3),
            max_tokens=test.get("max_tokens", 2048),
        )

        results["tests"].append({
            "id": test["id"],
            "category": test["category"],
            "title": test["title"],
            "expected": test.get("expected", ""),
            **result,
        })

        if result["success"]:
            print(f"    ✓ {result['elapsed_sec']}s, {result['tok_per_sec']} tok/s, {result['completion_tokens']} tokens")
        else:
            print(f"    ✗ {result['error']}")
            # 연결 오류면 더 이상 진행해도 의미 없음
            if "연결 오류" in result["error"]:
                print("\n중단: LM Studio Server 확인 후 다시 실행하세요.")
                return None

    return results


def save_results(results, model_label):
    Path(RESULTS_DIR).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = model_label.replace("/", "_").replace(":", "_").replace(" ", "_")

    # JSON (원본)
    json_path = f"{RESULTS_DIR}/{safe_label}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Markdown (사람용)
    md_path = f"{RESULTS_DIR}/{safe_label}_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 평가 결과: {model_label}\n\n")
        f.write(f"- 실행 시각: {results['timestamp']}\n")
        f.write(f"- API: {results['base_url']}\n")
        f.write(f"- 프롬프트 버전: {results['prompts_version']}\n\n")

        # 속도/성공률 요약
        successful = [t for t in results["tests"] if t["success"]]
        f.write("## 요약\n\n")
        f.write(f"- 성공: {len(successful)}/{len(results['tests'])}\n")
        if successful:
            avg_speed = sum(t["tok_per_sec"] for t in successful) / len(successful)
            avg_time = sum(t["elapsed_sec"] for t in successful) / len(successful)
            total_tokens = sum(t["completion_tokens"] for t in successful)
            f.write(f"- 평균 속도: {avg_speed:.1f} tok/s\n")
            f.write(f"- 평균 응답 시간: {avg_time:.1f}초\n")
            f.write(f"- 총 생성 토큰: {total_tokens}\n\n")

        # 카테고리별 묶기
        categories = {}
        for test in results["tests"]:
            cat = test["category"]
            categories.setdefault(cat, []).append(test)

        for cat_name, tests in categories.items():
            f.write(f"## 카테고리: {cat_name}\n\n")
            for test in tests:
                f.write(f"### {test['id']}: {test['title']}\n\n")
                if test.get("expected"):
                    f.write(f"**기대값**: {test['expected']}\n\n")

                if test["success"]:
                    f.write(f"**측정**: {test['elapsed_sec']}초 / {test['tok_per_sec']} tok/s / {test['completion_tokens']} tokens\n\n")
                    f.write("**응답**:\n\n")
                    f.write("```\n")
                    f.write(test["response"])
                    f.write("\n```\n\n")
                else:
                    f.write(f"**오류**: {test['error']}\n\n")

                f.write("---\n\n")

    return json_path, md_path


def main():
    print("=" * 70)
    print("Clinical-Assist 모델 평가")
    print("=" * 70)

    # 옵션 처리
    if len(sys.argv) > 1 and sys.argv[1] == "--ollama":
        base_url = OLLAMA_URL
        print(f"모드: Ollama ({base_url})")
    else:
        base_url = LM_STUDIO_URL
        print(f"모드: LM Studio ({base_url})")

    print()
    print("주의: LM Studio Server가 시작되어 있고, 평가할 모델이 로드되어 있어야 합니다.")
    print("      (LM Studio 좌측 사이드바 → Developer → Start Server)")
    print()

    model_label = input("모델 라벨 입력 (결과 파일명에 사용): ").strip()
    if not model_label:
        print("라벨이 비어있습니다. 종료.")
        sys.exit(1)

    # 프롬프트 파일 존재 확인
    if not Path(PROMPTS_FILE).exists():
        print(f"\n오류: 프롬프트 파일 없음 ({PROMPTS_FILE})")
        print("eval_runner.py가 있는 폴더에서 실행하세요.")
        sys.exit(1)

    print(f"\n평가 시작: {model_label}")
    print("-" * 70)

    results = run_evaluation(base_url, model_label)

    if results is None:
        sys.exit(1)

    json_path, md_path = save_results(results, model_label)

    print()
    print("=" * 70)
    print("저장 완료:")
    print(f"  JSON:     {json_path}")
    print(f"  Markdown: {md_path}")
    print("=" * 70)
    print()
    print("다음 단계:")
    print("  1. VS Code에서 .md 파일 열어 각 응답 확인 (A/B/C/D 카테고리)")
    print("  2. D 카테고리 (JSON+PHI): 채점 스크립트로 hard_fail 확인")
    print("  3. 다른 모델 평가: LM Studio에서 다른 모델 로드 후 같은 명령 재실행")


if __name__ == "__main__":
    main()
