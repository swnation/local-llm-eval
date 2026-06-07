#!/usr/bin/env python3
"""HP Z2 Gemma reasoning-control / output-contract pilot runner.

This runner is intentionally narrow. It uses LM Studio's local
OpenAI-compatible API for two synthetic non-PHI prompts and stores metadata
only. It does not call /explain, EMR, llama.cpp, or the Ollama shim.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(os.environ.get("LOCAL_LLM_EVAL_REPO", Path(__file__).resolve().parents[1])).resolve()
DEFAULT_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_MODELS_URL = "http://127.0.0.1:1234/v1/models"
DEMO_CITATION = "[kb:DEMO_GEMMA_OUTPUT:001]"

G1_PROMPT = (
    '다음 문장을 한 문장으로 짧게 요약해줘. 환자 정보는 없다. '
    '"이 테스트는 로컬 모델이 짧은 한국어 지시를 따라 최종 답변을 생성하는지 확인한다."'
)

G2_PROMPT = """근거:
- source_id=kb:DEMO_GEMMA_OUTPUT:001
- 내용=로컬 모델 출력 계약 테스트는 합성 데이터만 사용하며 실제 환자 정보가 없다.

요청:
한국어 한 문장 summary와 citations 배열만 포함한 JSON을 출력하라.
citations에는 [kb:DEMO_GEMMA_OUTPUT:001]만 넣어라."""


@dataclass(frozen=True)
class PilotModel:
    label: str
    model_key: str
    identifier: str
    load_args: tuple[str, ...]


PILOT_MODELS = (
    PilotModel(
        label="gemma-4-31b-qat",
        model_key="google/gemma-4-31b-qat",
        identifier="hpz2-gemma4-31b-qat-output-contract",
        load_args=(
            "lms",
            "load",
            "google/gemma-4-31b-qat",
            "--identifier",
            "hpz2-gemma4-31b-qat-output-contract",
            "--gpu",
            "max",
            "--context-length",
            "4096",
            "--ttl",
            "120",
            "-y",
        ),
    ),
    PilotModel(
        label="gemma-4-26b-a4b-qat",
        model_key="gemma-4-26b-a4b-it-qat",
        identifier="hpz2-gemma4-26b-a4b-qat-output-contract",
        load_args=(
            "lms",
            "load",
            "gemma-4-26b-a4b-it-qat",
            "--identifier",
            "hpz2-gemma4-26b-a4b-qat-output-contract",
            "--gpu",
            "max",
            "--context-length",
            "4096",
            "--ttl",
            "120",
            "-y",
        ),
    ),
)


def run_cmd(args: list[str] | tuple[str, ...], timeout: int = 300) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            list(args),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "args": list(args),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "elapsed_sec": round(time.time() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else "timeout"
        return {
            "args": list(args),
            "returncode": 124,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "elapsed_sec": round(time.time() - started, 3),
        }


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 300) -> tuple[int | None, dict[str, Any] | None, str | None, float]:
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw), None, round(time.time() - started, 3)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, None, raw[:500], round(time.time() - started, 3)
    except Exception as exc:  # noqa: BLE001 - metadata runner should capture request failure.
        return None, None, str(exc)[:500], round(time.time() - started, 3)


def phi_like_hits(text: str) -> list[str]:
    if not text:
        return []
    patterns = [
        r"\b\d{6}-\d{7}\b",
        r"\b\d{3}-\d{3,4}-\d{4}\b",
        r"\b01[016789]-\d{3,4}-\d{4}\b",
        r"chart[_ -]?no\s*[:=]",
        r"rrn\s*[:=]",
        r"주민등록번호\s*[:=]",
        r"차트번호\s*[:=]",
        r"환자명\s*[:=]",
    ]
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def _stringify_message_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def lms_ps_is_empty(command_result: dict[str, Any]) -> bool:
    if command_result.get("returncode") != 0:
        return False
    try:
        parsed = json.loads(command_result.get("stdout") or "")
    except json.JSONDecodeError:
        return False
    return parsed == []


def summarize_response(
    *,
    model_label: str,
    contract: str,
    max_tokens: int,
    response_format_requested: bool,
    http_status: int | None,
    data: dict[str, Any] | None,
    api_error: str | None,
    latency_sec: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "model_label": model_label,
        "contract": contract,
        "max_tokens": max_tokens,
        "response_format_requested": response_format_requested,
        "http_status": http_status,
        "latency_sec": latency_sec,
        "api_error": api_error,
        "ok": False,
        "finish_reason": None,
        "message_keys": [],
        "content_chars": 0,
        "reasoning_chars": 0,
        "reasoning_tokens": None,
        "completion_tokens": None,
        "output_channel_status": "request_failed" if api_error else "unknown",
        "phi_like_hit_count": 0,
        "json_parse_status": None,
        "json_keys": None,
        "citations_exact": None,
        "pass_status": "FAIL",
        "caveat": None,
    }
    if not data:
        return result

    try:
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        result["finish_reason"] = choice.get("finish_reason")
        result["message_keys"] = sorted(message.keys())
        content = _stringify_message_value(message.get("content")).strip()
        reasoning = "\n".join(
            _stringify_message_value(message.get(key)).strip()
            for key in ("reasoning", "reasoning_content", "reasoning_details", "thinking", "thoughts")
            if _stringify_message_value(message.get(key)).strip()
        )
        usage = data.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        result["completion_tokens"] = usage.get("completion_tokens")
        result["reasoning_tokens"] = details.get("reasoning_tokens")
        result["content_chars"] = len(content)
        result["reasoning_chars"] = len(reasoning)
        result["phi_like_hit_count"] = len(phi_like_hits(content) + phi_like_hits(reasoning))
        result["ok"] = http_status == 200

        if content:
            result["output_channel_status"] = "content"
        elif reasoning or (result["reasoning_tokens"] or 0) > 0:
            result["output_channel_status"] = "reasoning_only_output"
        else:
            result["output_channel_status"] = "empty_content"

        if contract == "G1":
            if result["ok"] and content and result["phi_like_hit_count"] == 0:
                result["pass_status"] = "PASS"
            return result

        if "```" in content:
            result["json_parse_status"] = "markdown_fence_present"
            return result

        try:
            parsed = json.loads(content)
        except Exception:  # noqa: BLE001 - parse status only.
            result["json_parse_status"] = "parse_failed"
            return result

        if not isinstance(parsed, dict):
            result["json_parse_status"] = "parsed_non_object"
            return result

        result["json_parse_status"] = "parsed"
        result["json_keys"] = sorted(parsed.keys())
        citations = parsed.get("citations")
        result["citations_exact"] = citations == [DEMO_CITATION]
        keys_exact = set(parsed.keys()) == {"summary", "citations"}
        summary_ok = isinstance(parsed.get("summary"), str) and bool(parsed["summary"].strip())
        if result["ok"] and keys_exact and summary_ok and result["citations_exact"] and result["phi_like_hit_count"] == 0:
            result["pass_status"] = "PASS"
        return result
    except Exception as exc:  # noqa: BLE001 - summary failure should be explicit metadata.
        result["api_error"] = f"summarize_error: {exc}"
        return result


def api_call(api_url: str, model_key: str, prompt: str, max_tokens: int, response_format: dict[str, Any] | None = None) -> tuple[int | None, dict[str, Any] | None, str | None, float]:
    payload: dict[str, Any] = {
        "model": model_key,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    return http_json(api_url, payload, timeout=420)


def run_g1(api_url: str, model: PilotModel) -> list[dict[str, Any]]:
    attempts = []
    status, data, error, elapsed = api_call(api_url, model.model_key, G1_PROMPT, 512)
    first = summarize_response(
        model_label=model.label,
        contract="G1",
        max_tokens=512,
        response_format_requested=False,
        http_status=status,
        data=data,
        api_error=error,
        latency_sec=elapsed,
    )
    attempts.append(first)
    if first["output_channel_status"] == "reasoning_only_output" or first["content_chars"] == 0:
        status, data, error, elapsed = api_call(api_url, model.model_key, G1_PROMPT, 1024)
        retry = summarize_response(
            model_label=model.label,
            contract="G1",
            max_tokens=1024,
            response_format_requested=False,
            http_status=status,
            data=data,
            api_error=error,
            latency_sec=elapsed,
        )
        if retry["pass_status"] == "PASS":
            retry["pass_status"] = "PASS_WITH_REASONING_BUDGET_CAVEAT"
            retry["caveat"] = "G1 needed max_tokens=1024 after 512-token empty/reasoning-only attempt"
        attempts.append(retry)
    return attempts


def run_g2(api_url: str, model: PilotModel) -> list[dict[str, Any]]:
    attempts = []
    status, data, error, elapsed = api_call(api_url, model.model_key, G2_PROMPT, 1024, {"type": "json_object"})
    first = summarize_response(
        model_label=model.label,
        contract="G2",
        max_tokens=1024,
        response_format_requested=True,
        http_status=status,
        data=data,
        api_error=error,
        latency_sec=elapsed,
    )
    attempts.append(first)
    if error and status in (400, 404, 422):
        status, data, retry_error, elapsed = api_call(api_url, model.model_key, G2_PROMPT, 1024)
        retry = summarize_response(
            model_label=model.label,
            contract="G2",
            max_tokens=1024,
            response_format_requested=False,
            http_status=status,
            data=data,
            api_error=retry_error,
            latency_sec=elapsed,
        )
        retry["caveat"] = "response_format_unsupported_or_rejected; retried without response_format"
        if retry["pass_status"] == "PASS":
            retry["pass_status"] = "PASS_WITH_RESPONSE_FORMAT_UNSUPPORTED"
        attempts.append(retry)
    return attempts


def write_summary_markdown(result_dir: Path, preflight: dict[str, Any], models: list[dict[str, Any]]) -> None:
    lines = [
        "# Gemma reasoning-control output-contract pilot metadata",
        "",
        f"- result_dir: `{result_dir}`",
        "- raw_model_output_stored: false",
        f"- host: {preflight['host']}",
        f"- repo_head: {preflight['repo_head']['stdout']}",
        "",
        "| model | contract attempts | final status | caveat |",
        "|---|---|---|---|",
    ]
    for model in models:
        statuses = []
        caveats = []
        for key in ("g1", "g2"):
            for attempt in model.get(key, []):
                statuses.append(
                    f"{attempt['contract']}:{attempt['max_tokens']}:{attempt['pass_status']}:{attempt['output_channel_status']}"
                )
                if attempt.get("caveat"):
                    caveats.append(attempt["caveat"])
        lines.append(
            f"| {model['model_label']} | {'; '.join(statuses) or model.get('status')} | {model.get('status')} | {'; '.join(caveats)} |"
        )
    (result_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_abort_summary(result_dir: Path, preflight: dict[str, Any], reason: str) -> None:
    payload = {
        "artifact_type": "gemma_reasoning_output_contract_pilot_aborted",
        "raw_model_output_stored": False,
        "result_dir": str(result_dir),
        "preflight": preflight,
        "abort_reason": reason,
    }
    (result_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-hpz2", action="store_true")
    parser.add_argument("--confirm-model-execution", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--models-url", default=DEFAULT_MODELS_URL)
    parser.add_argument("--output-root", default=str(REPO_ROOT / "results"))
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.dry_run and not (args.confirm_hpz2 and args.confirm_model_execution):
        print("Refusing execution: pass --confirm-hpz2 and --confirm-model-execution, or use --dry-run.", file=sys.stderr)
        return 2

    result_dir = Path(args.output_root) / f"gemma_reasoning_output_contract_pilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result_dir.mkdir(parents=True, exist_ok=True)
    preflight = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "platform": platform.platform(),
        "repo_status": run_cmd(["git", "status", "--short", "--branch"]),
        "repo_head": run_cmd(["git", "rev-parse", "HEAD"]),
        "repo_upstream": run_cmd(["git", "rev-parse", "@{u}"]),
        "lms_ps_before": run_cmd(["lms", "ps", "--json"]),
        "models_api_before": http_json(args.models_url, None, timeout=10)[:3],
    }

    if args.dry_run:
        payload = {
            "artifact_type": "gemma_reasoning_output_contract_pilot_dry_run",
            "raw_model_output_stored": False,
            "result_dir": str(result_dir),
            "preflight": preflight,
            "planned_models": [model.__dict__ for model in PILOT_MODELS],
            "planned_calls_max": 8,
        }
        (result_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"DRY_RUN_RESULT_DIR={result_dir}")
        return 0

    if not lms_ps_is_empty(preflight["lms_ps_before"]):
        write_abort_summary(result_dir, preflight, "lms ps was not empty before execution")
        print(f"ABORT_RESULT_DIR={result_dir}")
        print("ABORT_REASON=lms ps was not empty before execution", file=sys.stderr)
        return 3

    calls: list[dict[str, Any]] = []
    model_results: list[dict[str, Any]] = []
    abort_reason = None
    for model in PILOT_MODELS:
        lms_before_model = run_cmd(["lms", "ps", "--json"])
        if not lms_ps_is_empty(lms_before_model):
            abort_reason = f"lms ps was not empty before loading {model.label}"
            model_results.append(
                {
                    "model_label": model.label,
                    "model_key": model.model_key,
                    "status": "ABORTED_STALE_LOADED_MODEL",
                    "lms_ps_before_model": lms_before_model,
                }
            )
            break
        load = run_cmd(model.load_args, timeout=1200)
        entry: dict[str, Any] = {
            "model_label": model.label,
            "model_key": model.model_key,
            "identifier": model.identifier,
            "load": load,
            "lms_ps_after_load": run_cmd(["lms", "ps", "--json"]),
        }
        if load["returncode"] != 0:
            entry["status"] = "LOAD_FAILED"
            model_results.append(entry)
            continue
        g1 = run_g1(args.api_url, model)
        g2 = run_g2(args.api_url, model)
        calls.extend(g1 + g2)
        unload = run_cmd(["lms", "unload", model.identifier], timeout=180)
        if unload["returncode"] != 0:
            unload = run_cmd(["lms", "unload", "--all"], timeout=180)
        entry.update(
            {
                "g1": g1,
                "g2": g2,
                "unload": unload,
                "lms_ps_after_unload": run_cmd(["lms", "ps", "--json"]),
                "status": "DONE",
            }
        )
        model_results.append(entry)
        time.sleep(5)

    final_state = {
        "final_unload": run_cmd(["lms", "unload", "--all"], timeout=180),
        "lms_ps_final": run_cmd(["lms", "ps", "--json"]),
        "repo_status_final": run_cmd(["git", "status", "--short", "--branch"]),
    }
    summary = {
        "artifact_type": "gemma_reasoning_output_contract_pilot_metadata",
        "raw_model_output_stored": False,
        "result_dir": str(result_dir),
        "preflight": preflight,
        "models": model_results,
        "calls": calls,
        "final_state": final_state,
    }
    if abort_reason:
        summary["abort_reason"] = abort_reason
    (result_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_summary_markdown(result_dir, preflight, model_results)

    print(f"RESULT_DIR={result_dir}")
    print(f"SUMMARY_JSON={result_dir / 'summary.json'}")
    for call in calls:
        print(
            "CALL "
            f"{call['model_label']} {call['contract']} max_tokens={call['max_tokens']} "
            f"rf={call['response_format_requested']} status={call['pass_status']} "
            f"channel={call['output_channel_status']} content_chars={call['content_chars']} "
            f"reasoning_chars={call['reasoning_chars']} reasoning_tokens={call['reasoning_tokens']} "
            f"phi={call['phi_like_hit_count']} json={call['json_parse_status']} "
            f"citations_exact={call['citations_exact']}"
        )
    print(f"FINAL_LMS_PS={final_state['lms_ps_final']['stdout']}")
    if abort_reason:
        print(f"ABORT_REASON={abort_reason}", file=sys.stderr)
        return 3
    if final_state["lms_ps_final"]["stdout"].strip() not in ("[]", ""):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
