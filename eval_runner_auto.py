#!/usr/bin/env python3
"""
Clinical-Assist 모델 자동 평가 스크립트 (안전성 패치 적용)

사용법:
  python eval_runner_auto.py                              # 기본 (models_config.json)
  python eval_runner_auto.py --config models_config_part1.json
  python eval_runner_auto.py --config models_config_part2.json

특징:
  - lms CLI로 LM Studio 모델 자동 로드/언로드 (--identifier로 API 식별자 일치 보장)
  - 'ollama stop' + 'ollama ps' 확인으로 메모리 회수 검증
  - prompt별 partial save (중간 실패 시 데이터 손실 방지)
  - 모델 로드 실패 또는 연속 timeout 시 해당 모델 skip 후 다음 모델 진행
  - 외부 라이브러리 의존성 없음 (Python 표준 라이브러리만)
"""

import json
import time
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

# --- 설정 ---
LM_STUDIO_URL = "http://localhost:1234/v1"
OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_PROMPTS_FILE = "prompts/test_suite_v0.2.json"
DEFAULT_MODELS_CONFIG = "models_config.json"
RESULTS_DIR = "results"
TIMEOUT_SEC = 600
LOAD_WAIT_SEC = 3
CONSECUTIVE_TIMEOUT_LIMIT = 2  # 한 모델에서 연속 timeout 발생 시 skip 기준


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_lms(args, timeout=300):
    """lms CLI 호출."""
    cmd = ["lms"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8"
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return -1, "", "lms 명령을 찾을 수 없음. 'lms bootstrap' 먼저 실행하세요."


def lms_unload_all():
    print("  [lms] 모든 LM Studio 모델 언로드...")
    code, out, err = run_lms(["unload", "--all"])
    if code != 0 and err.strip():
        print(f"  [lms] 언로드 메시지: {err.strip()}")


def lms_load(model_key, identifier, load_options):
    """LM Studio에 모델 로드. --identifier로 API 호출용 식별자를 명시 지정."""
    args = ["load", model_key, "--identifier", identifier]
    for k, v in load_options.items():
        flag = f"--{k.replace('_', '-')}"
        args.extend([flag, str(v)])

    print(f"  [lms] 로드 중: {model_key} as '{identifier}' (옵션: {load_options})")
    code, out, err = run_lms(args, timeout=600)
    if code != 0:
        print(f"  [lms] 로드 실패: {err.strip()}")
        return False
    print(f"  [lms] 로드 성공")
    return True


def ollama_stop(model_name):
    """Ollama 모델 즉시 언로드 + 확인."""
    try:
        result = subprocess.run(
            ["ollama", "stop", model_name],
            capture_output=True, text=True, timeout=30, encoding="utf-8"
        )
        if result.returncode == 0:
            print(f"  [ollama] {model_name} stop 명령 완료")
        else:
            print(f"  [ollama] stop 경고: {result.stderr.strip()}")
    except FileNotFoundError:
        print(f"  [ollama] 'ollama' 명령 없음. 메모리 회수 건너뜀.")
        return
    except Exception as e:
        print(f"  [ollama] stop 예외: {e}")

    # 'ollama ps'로 실제 언로드 확인
    time.sleep(2)
    try:
        ps_result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True,
            timeout=15, encoding="utf-8"
        )
        if ps_result.returncode == 0 and model_name in ps_result.stdout:
            print(f"  [ollama] ⚠️  '{model_name}'이 ollama ps에 여전히 보임. 다음 모델 진행 전 5초 추가 대기.")
            time.sleep(5)
        else:
            print(f"  [ollama] 메모리 회수 확인됨")
    except Exception as e:
        print(f"  [ollama] ps 확인 실패 (계속 진행): {e}")


def call_model(base_url, model_id, system, user, temperature, max_tokens, extra_options=None):
    """OpenAI 호환 API 호출."""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if extra_options:
        payload.update(extra_options)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
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
        return {"success": False, "error": f"연결 오류: {e}", "error_type": "connection"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timeout {TIMEOUT_SEC}s", "error_type": "timeout"}
    except Exception as e:
        # urllib timeout도 여기 잡힘
        err_str = str(e)
        if "timed out" in err_str.lower() or "timeout" in err_str.lower():
            return {"success": False, "error": f"timeout {TIMEOUT_SEC}s", "error_type": "timeout"}
        return {"success": False, "error": f"{type(e).__name__}: {e}", "error_type": "other"}


def partial_save(results, partial_path):
    """Prompt별 임시 저장 (중간 실패 시 데이터 손실 방지)."""
    try:
        with open(partial_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"    [partial-save] 경고: {e}")


def run_one_model(model_cfg, prompts_data):
    """모델 하나에 대해 모든 프롬프트 실행."""
    label = model_cfg["label"]
    provider = model_cfg.get("provider", "lm_studio")

    # 1. 모델 로드
    if provider == "lm_studio":
        base_url = LM_STUDIO_URL
        lms_unload_all()
        time.sleep(1)
        load_options = model_cfg.get("load_options", {})
        # --identifier로 API 식별자를 label과 일치시킴
        if not lms_load(model_cfg["lms_key"], label, load_options):
            return {
                "model_label": label,
                "provider": provider,
                "error": "모델 로드 실패 - skip",
                "tests": []
            }
        time.sleep(LOAD_WAIT_SEC)
        model_id = label  # --identifier로 지정한 값과 일치
    elif provider == "ollama":
        base_url = OLLAMA_URL
        model_id = model_cfg["ollama_name"]
        print(f"  [ollama] 모델: {model_id} (자동 로드)")
    else:
        return {"model_label": label, "error": f"알 수 없는 provider: {provider}", "tests": []}

    # 2. 결과 dict 준비 + partial save 경로
    results = {
        "model_label": label,
        "provider": provider,
        "base_url": base_url,
        "model_id": model_id,
        "timestamp": datetime.now().isoformat(),
        "prompts_version": prompts_data.get("version", "unknown"),
        "load_options": model_cfg.get("load_options", {}),
        "inference_options": model_cfg.get("inference_options", {}),
        "tests": [],
    }

    Path(RESULTS_DIR).mkdir(exist_ok=True)
    safe_label = label.replace("/", "_").replace(":", "_").replace(" ", "_")
    partial_path = f"{RESULTS_DIR}/.{safe_label}_partial.json"

    extra_inference = model_cfg.get("inference_options", {})
    total = len(prompts_data["tests"])
    consecutive_timeouts = 0
    model_skipped = False

    for i, test in enumerate(prompts_data["tests"], 1):
        print(f"    [{i:2d}/{total}] {test['id']}: {test['title'][:40]}")
        result = call_model(
            base_url=base_url, model_id=model_id,
            system=test["system"], user=test["user"],
            temperature=test.get("temperature", 0.3),
            max_tokens=test.get("max_tokens", 2048),
            extra_options=extra_inference,
        )
        results["tests"].append({
            "id": test["id"], "category": test["category"],
            "title": test["title"], "expected": test.get("expected", ""),
            **result,
        })

        # 매 prompt 후 partial save (안전장치)
        partial_save(results, partial_path)

        if result["success"]:
            print(f"          ✓ {result['elapsed_sec']}s, {result['tok_per_sec']} tok/s")
            consecutive_timeouts = 0
        else:
            print(f"          ✗ {result['error']}")
            # 연결 오류면 전체 중단 (서버 다운)
            if result.get("error_type") == "connection":
                results["interrupted"] = True
                return results
            # 연속 timeout 카운트
            if result.get("error_type") == "timeout":
                consecutive_timeouts += 1
                if consecutive_timeouts >= CONSECUTIVE_TIMEOUT_LIMIT:
                    print(f"\n  ⚠️  연속 timeout {CONSECUTIVE_TIMEOUT_LIMIT}회 → 이 모델 skip, 다음 모델로 진행")
                    results["model_skipped"] = True
                    results["skip_reason"] = f"연속 timeout {CONSECUTIVE_TIMEOUT_LIMIT}회"
                    model_skipped = True
                    break

    # 3. 모델 언로드
    if provider == "lm_studio":
        lms_unload_all()
        time.sleep(1)
    elif provider == "ollama":
        ollama_stop(model_id)

    # 4. partial 파일 정리 (정상 완료 시)
    try:
        if Path(partial_path).exists():
            Path(partial_path).unlink()
    except Exception:
        pass

    return results


def save_results(results):
    """모델 평가 완료 후 최종 JSON + Markdown 저장."""
    Path(RESULTS_DIR).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = results["model_label"].replace("/", "_").replace(":", "_").replace(" ", "_")

    # JSON
    json_path = f"{RESULTS_DIR}/{safe_label}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Markdown
    md_path = f"{RESULTS_DIR}/{safe_label}_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 평가 결과: {results['model_label']}\n\n")
        f.write(f"- 실행 시각: {results['timestamp']}\n")
        f.write(f"- Provider: {results.get('provider', 'unknown')}\n")
        f.write(f"- Model ID: {results.get('model_id', 'unknown')}\n")
        if results.get("load_options"):
            f.write(f"- Load options: `{results['load_options']}`\n")
        if results.get("inference_options"):
            f.write(f"- Inference options: `{results['inference_options']}`\n")
        if results.get("model_skipped"):
            f.write(f"- ⚠️  모델 SKIP: {results.get('skip_reason', '')}\n")
        f.write("\n")

        successful = [t for t in results["tests"] if t.get("success")]
        f.write("## 요약\n\n")
        f.write(f"- 성공: {len(successful)}/{len(results['tests'])}\n")
        if successful:
            avg_speed = sum(t["tok_per_sec"] for t in successful) / len(successful)
            avg_time = sum(t["elapsed_sec"] for t in successful) / len(successful)
            f.write(f"- 평균 속도: {avg_speed:.1f} tok/s\n")
            f.write(f"- 평균 응답 시간: {avg_time:.1f}초\n\n")

        categories = {}
        for test in results["tests"]:
            categories.setdefault(test["category"], []).append(test)

        for cat_name, tests in categories.items():
            f.write(f"## 카테고리: {cat_name}\n\n")
            for test in tests:
                f.write(f"### {test['id']}: {test['title']}\n\n")
                if test.get("expected"):
                    f.write(f"**기대값**: {test['expected']}\n\n")
                if test.get("success"):
                    f.write(f"**측정**: {test['elapsed_sec']}s / {test['tok_per_sec']} tok/s / {test['completion_tokens']} tokens\n\n")
                    f.write("**응답**:\n\n```\n")
                    f.write(test["response"])
                    f.write("\n```\n\n")
                else:
                    f.write(f"**오류**: {test.get('error', 'unknown')}\n\n")
                f.write("---\n\n")

    return json_path, md_path


def generate_comparison_summary(all_results, config_name=""):
    """여러 모델 결과를 한 파일에 비교 요약."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{config_name}" if config_name else ""
    path = f"{RESULTS_DIR}/_comparison{suffix}_{timestamp}.md"

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# 모델 비교 요약\n\n생성: {timestamp}\n")
        if config_name:
            f.write(f"Config: {config_name}\n")
        f.write("\n")

        f.write("## 속도 및 성공률\n\n")
        f.write("| 모델 | 성공 | 평균 속도 | 평균 응답시간 | Skip 여부 |\n")
        f.write("|---|---|---|---|---|\n")
        for r in all_results:
            successful = [t for t in r["tests"] if t.get("success")]
            skip_flag = "⚠️ SKIP" if r.get("model_skipped") else "-"
            if successful:
                avg_speed = sum(t["tok_per_sec"] for t in successful) / len(successful)
                avg_time = sum(t["elapsed_sec"] for t in successful) / len(successful)
                f.write(f"| {r['model_label']} | {len(successful)}/{len(r['tests'])} | {avg_speed:.1f} tok/s | {avg_time:.1f}s | {skip_flag} |\n")
            else:
                f.write(f"| {r['model_label']} | 0/{len(r['tests'])} | - | - | {skip_flag} |\n")

        f.write("\n## 프롬프트별 모델 응답 비교\n\n")
        f.write("같은 프롬프트에 대한 모델별 응답입니다. 직접 비교하세요.\n\n")

        all_prompt_ids = []
        if all_results:
            all_prompt_ids = [t["id"] for t in all_results[0]["tests"]]

        for pid in all_prompt_ids:
            first_test = next((t for t in all_results[0]["tests"] if t["id"] == pid), None)
            if not first_test:
                continue

            f.write(f"### {pid}: {first_test['title']}\n\n")
            f.write(f"**카테고리**: {first_test['category']}\n\n")
            if first_test.get("expected"):
                f.write(f"**기대값**: {first_test['expected']}\n\n")

            for r in all_results:
                test = next((t for t in r["tests"] if t["id"] == pid), None)
                if not test:
                    continue
                f.write(f"#### {r['model_label']}\n\n")
                if test.get("success"):
                    f.write(f"_{test['elapsed_sec']}s / {test['tok_per_sec']} tok/s_\n\n")
                    f.write("```\n" + test["response"] + "\n```\n\n")
                else:
                    f.write(f"오류: {test.get('error', 'unknown')}\n\n")

            f.write("---\n\n")

    return path


def main():
    parser = argparse.ArgumentParser(description="Clinical-Assist 모델 평가")
    parser.add_argument("--config", default=DEFAULT_MODELS_CONFIG,
                        help=f"모델 설정 파일 경로 (기본: {DEFAULT_MODELS_CONFIG})")
    parser.add_argument("--prompts", default=DEFAULT_PROMPTS_FILE,
                        help=f"프롬프트 파일 경로 (기본: {DEFAULT_PROMPTS_FILE})")
    args = parser.parse_args()

    print("=" * 70)
    print("Clinical-Assist 모델 자동 평가 (안전성 패치 적용)")
    print("=" * 70)
    print(f"Config: {args.config}")
    print(f"Prompts: {args.prompts}")
    print()

    if not Path(args.config).exists():
        print(f"오류: {args.config} 파일이 없습니다.")
        sys.exit(1)
    if not Path(args.prompts).exists():
        print(f"오류: {args.prompts} 파일이 없습니다.")
        sys.exit(1)

    print("[사전 점검] lms CLI 확인...")
    code, out, err = run_lms(["status"], timeout=10)
    if code != 0:
        print(f"  ✗ lms 명령 실패: {err.strip()}")
        print("    → 'lms bootstrap' 실행 후 새 터미널에서 재시도.")
        sys.exit(1)
    print(f"  ✓ lms OK")

    config = load_json(args.config)
    prompts_data = load_json(args.prompts)

    models = config["models"]
    print(f"\n평가 대상: {len(models)}개 모델 × {len(prompts_data['tests'])}개 프롬프트 = {len(models) * len(prompts_data['tests'])}회 호출")
    for i, m in enumerate(models, 1):
        print(f"  {i:2d}. {m['label']} ({m.get('provider', 'lm_studio')})")

    print("\n시작합니다... (Ctrl+C로 중단 가능)")
    print("=" * 70)

    overall_start = time.time()
    all_results = []

    for idx, model_cfg in enumerate(models, 1):
        print(f"\n[모델 {idx}/{len(models)}] {model_cfg['label']}")
        print("-" * 70)
        model_start = time.time()

        try:
            results = run_one_model(model_cfg, prompts_data)
        except KeyboardInterrupt:
            print("\n\n중단됨 (Ctrl+C)")
            break
        except Exception as e:
            print(f"\n  예상치 못한 오류: {type(e).__name__}: {e}")
            continue

        if results.get("tests"):
            json_path, md_path = save_results(results)
            print(f"  저장: {md_path}")
            all_results.append(results)

        elapsed = time.time() - model_start
        print(f"  소요: {elapsed:.1f}초 ({elapsed/60:.1f}분)")

        if results.get("interrupted"):
            print("\n연결 오류로 전체 중단.")
            break

    total_elapsed = time.time() - overall_start
    print("\n" + "=" * 70)
    print("모든 평가 완료")
    print("=" * 70)
    print(f"총 소요: {total_elapsed:.1f}초 ({total_elapsed/60:.1f}분)")
    print(f"완료된 모델: {len(all_results)}개")
    skipped = sum(1 for r in all_results if r.get("model_skipped"))
    if skipped:
        print(f"⚠️  Skip된 모델: {skipped}개 (results 파일에서 'model_skipped' 확인)")
    print(f"\n결과 파일: {RESULTS_DIR}/")

    if len(all_results) >= 2:
        config_name = Path(args.config).stem
        summary_path = generate_comparison_summary(all_results, config_name)
        print(f"비교 요약: {summary_path}")


if __name__ == "__main__":
    main()
