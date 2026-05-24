#!/usr/bin/env python3
"""
HP Z2 LM Studio Phase 2 Stage A runner.

This runner is for the HP Z2 execution-only lane. It loads each configured LM
Studio model, routes EMR_AI_24clinic /explain LLM calls to LM Studio through a
runner-side adapter, runs the frozen RAG-aware eval cases, and writes local
result artifacts.

It does not modify EMR_AI_24clinic. It refuses real execution unless both
--confirm-hpz2 and --confirm-heavy-run are provided.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "models_config_hpz2_lmstudio_phase2_stage_a_v0.1.json"
DEFAULT_EVAL_SET = "prompts/rag_aware_eval_set_v0.1.json"
DEFAULT_SERVER_URL = "http://127.0.0.1:1234/v1"
RESULTS_DIR = Path("results")
LOAD_TIMEOUT_SEC = 1200
ESTIMATE_TIMEOUT_SEC = 300
STATUS_TIMEOUT_SEC = 30
UNLOAD_TIMEOUT_SEC = 180
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_TOKENS = 512


EXPLAIN_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "citations"],
    "additionalProperties": False,
}


SMOKE_CARRY_REQUESTS: dict[str, dict[str, Any]] = {
    "smoke-01-dige": {
        "check_result": {
            "level": "warn",
            "message": "dige 처방 불가 여부 설명",
            "sub": "ranitidine 국내 시장 철수 및 대체 약제 확인",
            "source": "rule:dige-market-withdrawn",
        },
        "context": {
            "dx": ["j0390"],
            "orders": ["dige"],
            "order_details": [{"code": "dige", "days": 3}],
            "patient_type": "성인",
            "age": 35,
        },
    },
    "smoke-02-ped-iv": {
        "check_result": {
            "level": "warn",
            "message": "만 12세 미만 소아 IV 수액 제한 설명",
            "sub": "tamiiv 또는 tyiv 포함 모든 IV 수액 원내 운영 원칙 확인",
            "source": "rule:ped-iv-ban",
        },
        "context": {
            "dx": ["j069"],
            "orders": ["tamiiv"],
            "order_details": [{"code": "tamiiv", "days": 1}],
            "patient_type": "소아",
            "age": 8,
        },
    },
    "smoke-03-tysy": {
        "check_result": {
            "level": "unknown",
            "message": "tysy 함량 및 소아 해열제 설명",
            "sub": "세토펜현탁 acetaminophen 농도 확인",
            "source": "dict:tysy",
        },
        "context": {
            "dx": ["j069"],
            "orders": ["tysy"],
            "order_details": [{"code": "tysy", "days": 3}],
            "patient_type": "소아",
            "age": 5,
        },
    },
    "smoke-04-augsy": {
        "check_result": {
            "level": "warn",
            "message": "augsy 1일 상한 설명",
            "sub": "하이크라듀오시럽 amoxicillin-clavulanate 원내 상한 확인",
            "source": "rule:drug:augsy",
        },
        "context": {
            "dx": ["j0390"],
            "orders": ["augsy"],
            "order_details": [{"code": "augsy", "days": 3}],
            "patient_type": "소아",
            "age": 6,
        },
    },
    "smoke-05-uri-insurance": {
        "check_result": {
            "level": "warn",
            "message": "성인 URI 진해거담제 보험 기준 설명",
            "sub": "기침 가래 콧물약 같은 작용 약제 중복 기준 확인",
            "source": "kb:성인_URI",
        },
        "context": {
            "dx": ["j069"],
            "orders": ["ac2", "suda2"],
            "order_details": [{"code": "ac2", "days": 3}, {"code": "suda2", "days": 3}],
            "patient_type": "성인",
            "age": 42,
        },
    },
    "smoke-06-cystitis": {
        "check_result": {
            "level": "unknown",
            "message": "급성 방광염 cipro 처방 근거 설명",
            "sub": "n300 급성 방광염과 cipro 250mg BID 관련 context 확인",
            "source": "kb:급성_방광염_acute_cystitis",
        },
        "context": {
            "dx": ["n300"],
            "orders": ["cipro"],
            "order_details": [{"code": "cipro", "days": 3}],
            "patient_type": "성인",
            "age": 50,
        },
    },
    "smoke-07-age": {
        "check_result": {
            "level": "unknown",
            "message": "소아 AGE 처방 코드 설명",
            "sub": "trimesy lacto2 typow tysy sme hidra 처방 코드 확인",
            "source": "kb:소아_AGE_FGID",
        },
        "context": {
            "dx": ["a090"],
            "orders": ["trimesy", "lacto2", "tysy"],
            "order_details": [{"code": "trimesy", "days": 3}, {"code": "lacto2", "days": 3}],
            "patient_type": "소아",
            "age": 4,
        },
    },
    "smoke-08-migraine": {
        "check_result": {
            "level": "unknown",
            "message": "편두통 약 종류와 처방 기본 설명",
            "sub": "triptan NSAIDs AAP tramadol ergotamine caffeine 확인",
            "source": "kb:편두통_migraine",
        },
        "context": {
            "dx": ["g439"],
            "orders": ["ty", "loxo"],
            "order_details": [{"code": "ty", "days": 3}, {"code": "loxo", "days": 3}],
            "patient_type": "성인",
            "age": 37,
        },
    },
    "smoke-09-bst": {
        "check_result": {
            "level": "warn",
            "message": "BST 코드 누락 룰 설명",
            "sub": "혈당측정 값과 코드 짝짓기 양방향 rule 확인",
            "source": "rule_module:bst",
        },
        "context": {
            "dx": ["e14"],
            "orders": ["bst"],
            "order_details": [{"code": "bst", "days": 1}],
            "patient_type": "성인",
            "age": 61,
        },
    },
    "smoke-10-diabetes": {
        "check_result": {
            "level": "unknown",
            "message": "당뇨 약 종류 및 보험 기준 설명",
            "sub": "2제 3제 이상 병용금기 조합과 인슐린 포장단위 확인",
            "source": "kb:당뇨_DM_diabetes",
        },
        "context": {
            "dx": ["e14"],
            "orders": ["met", "insu"],
            "order_details": [{"code": "met", "days": 30}, {"code": "insu", "days": 30}],
            "patient_type": "성인",
            "age": 58,
        },
    },
}


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_cmd(cmd: list[str], timeout: int, cwd: Path | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_s": round(time.perf_counter() - start, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {timeout}s",
            "elapsed_s": round(time.perf_counter() - start, 3),
        }


def find_lms_exe() -> str:
    found = shutil.which("lms")
    if found:
        return found
    for candidate in (
        Path.home() / ".lmstudio" / "bin" / "lms.exe",
        Path.home() / ".lmstudio" / "bin" / "lms",
    ):
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("lms CLI was not found.")


def option_args(options: dict[str, Any], include_ttl: bool = True) -> list[str]:
    args: list[str] = []
    for key, value in options.items():
        if key == "ttl" and not include_ttl:
            continue
        args.extend(["--" + key.replace("_", "-"), str(value)])
    return args


def normalize_cli_args(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise TypeError("lms_cli_args must be a string or list of strings")


def lms_status(lms_exe: str) -> dict[str, Any]:
    return run_cmd([lms_exe, "status"], timeout=STATUS_TIMEOUT_SEC)


def lms_status_has_no_models(status: dict[str, Any]) -> bool:
    if status.get("returncode") != 0:
        return False
    text = f"{status.get('stdout', '')}\n{status.get('stderr', '')}".lower()
    return "no models loaded" in text or "no loaded models" in text


def unload_all(lms_exe: str) -> dict[str, Any]:
    return run_cmd([lms_exe, "unload", "--all"], timeout=UNLOAD_TIMEOUT_SEC)


def estimate_model(lms_exe: str, model_key: str, load_options: dict[str, Any], cli_args: list[str]) -> dict[str, Any]:
    cmd = [lms_exe, "load", model_key]
    cmd.extend(option_args(load_options, include_ttl=False))
    cmd.append("--estimate-only")
    cmd.extend(cli_args)
    return run_cmd(cmd, timeout=ESTIMATE_TIMEOUT_SEC)


def load_model(
    lms_exe: str,
    model_key: str,
    identifier: str,
    load_options: dict[str, Any],
    cli_args: list[str],
) -> dict[str, Any]:
    cmd = [lms_exe, "load", model_key, "--identifier", identifier]
    cmd.extend(option_args(load_options))
    cmd.extend(cli_args)
    return run_cmd(cmd, timeout=LOAD_TIMEOUT_SEC)


def sleep_with_scale(seconds: int | float, scale: float, reason: str) -> None:
    delay = max(0.0, float(seconds) * max(0.0, scale))
    if delay <= 0:
        return
    print(f"  wait {delay:.1f}s: {reason}")
    time.sleep(delay)


def wait_for_no_models(lms_exe: str, timeout_sec: int = 120, poll_sec: int = 5) -> dict[str, Any]:
    deadline = time.perf_counter() + timeout_sec
    last = lms_status(lms_exe)
    while time.perf_counter() < deadline:
        if lms_status_has_no_models(last):
            return last
        time.sleep(poll_sec)
        last = lms_status(lms_exe)
    return last


def openai_base_url(value: str) -> str:
    clean = str(value).strip().rstrip("/")
    return clean if clean.endswith("/v1") else f"{clean}/v1"


def settings_host_from_server_url(value: str) -> str:
    parsed = urllib.parse.urlparse(str(value))
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.port is None:
        raise ValueError("LM Studio server URL must be loopback http with a port")
    return f"http://{parsed.hostname}:{parsed.port}"


def resolve_app_repo(config: dict[str, Any], config_path: Path, override: str | None) -> Path:
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    app_repo = config.get("_rag_endpoint", {}).get("app_repo")
    if app_repo:
        candidates.append((config_path.parent / str(app_repo)).resolve())
    candidates.append((REPO_ROOT.parent / "EMR_AI_24clinic").resolve())
    for candidate in candidates:
        if candidate.exists() and (candidate / "app" / "explain.py").exists():
            return candidate
    checked = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"EMR_AI_24clinic repo not found. Checked: {checked}")


def emr_git_status(emr_repo: Path) -> dict[str, Any]:
    return run_cmd(["git", "status", "--short", "--branch"], timeout=30, cwd=emr_repo)


def dirty_git_status_lines(status: dict[str, Any]) -> list[str]:
    return [
        line
        for line in str(status.get("stdout", "")).splitlines()
        if line and not line.startswith("##")
    ]


def import_emr_explain(emr_repo: Path):
    emr_path = str(emr_repo)
    if emr_path not in sys.path:
        sys.path.insert(0, emr_path)
    import app.explain as explain_module  # type: ignore
    from app.explain import ExplainRequest  # type: ignore
    from app.llm.phi_strip import scan_output  # type: ignore

    return explain_module, ExplainRequest, scan_output


def explain_response_format(mode: str | None) -> dict[str, Any] | None:
    clean = str(mode or "json_object").strip().lower()
    if clean in {"none", "off", "false", "disabled"}:
        return None
    if clean == "json_schema":
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "explain_response",
                "strict": True,
                "schema": EXPLAIN_RESPONSE_SCHEMA,
            },
        }
    if clean == "json_object":
        return {"type": "json_object"}
    raise ValueError(f"unsupported response_format mode: {mode}")


def extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return text
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def postprocess_llm_text(text: str, modes: list[str]) -> tuple[str, list[str]]:
    current = str(text or "")
    applied: list[str] = []
    for mode in modes:
        clean = str(mode).strip().lower()
        if clean == "extract_first_json_object":
            updated = extract_first_json_object(current)
        elif clean == "strip_think_blocks":
            updated = re.sub(r"<think>.*?</think>", "", current, flags=re.DOTALL | re.IGNORECASE)
        elif clean == "strip_channel_tags":
            updated = re.sub(r"<\|[^>]+?\|>", "", current)
            updated = re.sub(r"<channel\|>", "", updated)
        else:
            continue
        if updated != current:
            applied.append(clean)
            current = updated.strip()
    return current, applied


def apply_prompt_profile(system: str, prompt: str, options: dict[str, Any]) -> tuple[str, str]:
    system_parts = [
        str(options.get("system_prefix", "")).strip(),
        str(system or "").strip(),
        str(options.get("system_suffix", "")).strip(),
    ]
    user_parts = [
        str(options.get("user_prefix", "")).strip(),
        str(prompt or "").strip(),
        str(options.get("user_suffix", "")).strip(),
    ]
    return "\n\n".join(part for part in system_parts if part), "\n\n".join(part for part in user_parts if part)


def merged_inference_options(config: dict[str, Any], model: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    options: dict[str, Any] = {}
    options.update(config.get("_inference_profile_defaults", {}))
    options.update(model.get("inference_options", {}))
    if args.timeout_seconds is not None:
        options["timeout_seconds"] = args.timeout_seconds
    if args.max_tokens is not None:
        options["max_tokens"] = args.max_tokens
    if args.temperature is not None:
        options["temperature"] = args.temperature
    if args.disable_response_format:
        options["response_format"] = "none"
    options.setdefault("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    options.setdefault("max_tokens", DEFAULT_MAX_TOKENS)
    options.setdefault("temperature", 0.0)
    options.setdefault("response_format", "json_object")
    options.setdefault("response_format_fallback", "none")
    options.setdefault("postprocess", [])
    return options


def chat_completion(
    *,
    server_url: str,
    model: str,
    system: str,
    prompt: str,
    options: dict[str, Any],
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    url = openai_base_url(server_url) + "/chat/completions"
    original_system = system
    original_prompt = prompt
    system, prompt = apply_prompt_profile(system, prompt, options)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(options.get("temperature", 0.0)),
        "max_tokens": int(options.get("max_tokens", DEFAULT_MAX_TOKENS)),
        "stream": False,
    }
    for key in ("top_p", "top_k", "min_p", "presence_penalty", "frequency_penalty", "repeat_penalty"):
        if key in options:
            payload[key] = options[key]
    response_format = explain_response_format(str(options.get("response_format", "json_object")))
    if response_format:
        payload["response_format"] = response_format

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    timeout_seconds = int(options.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    try:
        body = urlopen(request, timeout=timeout_seconds).read()
        parsed = json.loads(body.decode("utf-8"))
        message = parsed.get("choices", [{}])[0].get("message", {})
        raw_text = str(message.get("content", "") or "")
        text, postprocess_applied = postprocess_llm_text(raw_text, [str(item) for item in options.get("postprocess", [])])
        return {
            "status": "ok",
            "text": text,
            "raw_text": raw_text,
            "postprocess_applied": postprocess_applied,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "usage": parsed.get("usage", {}) or {},
        }
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        lowered = raw_body.lower()
        fallback = str(options.get("response_format_fallback", "none"))
        if response_format and exc.code == 400 and "response_format" in lowered and fallback != options.get("response_format"):
            retry_options = dict(options)
            retry_options["response_format"] = fallback
            return chat_completion(
                server_url=server_url,
                model=model,
                system=original_system,
                prompt=original_prompt,
                options=retry_options,
                urlopen=urlopen,
            )
        status = "llm_model_not_found" if exc.code == 404 or "model not found" in lowered else "llm_unavailable"
        return {
            "status": status,
            "text": "",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error_message": f"LM Studio HTTP {exc.code}: {raw_body[:300]}",
        }
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        status = "llm_timeout" if isinstance(exc, (socket.timeout, TimeoutError)) else "llm_unavailable"
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, socket.timeout):
            status = "llm_timeout"
        return {
            "status": status,
            "text": "",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error_message": f"LM Studio request failed: {reason}",
        }


def make_lmstudio_generate(
    *,
    server_url: str,
    runtime_options_by_model: dict[str, dict[str, Any]],
    call_counter: dict[str, int],
):
    def generate(*, prompt: str, system: str = "", settings=None, **_: Any) -> dict[str, Any]:
        call_counter["count"] = call_counter.get("count", 0) + 1
        model = str(getattr(settings, "model", "") or "")
        options = dict(runtime_options_by_model.get(model, {}))
        timeout = int(getattr(settings, "timeout_seconds", options.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)) or options.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        options["timeout_seconds"] = timeout
        result = chat_completion(
            server_url=server_url,
            model=model,
            system=system,
            prompt=prompt,
            options=options,
        )
        call_counter["last_trace"] = {
            "model": model,
            "status": result.get("status"),
            "latency_ms": result.get("latency_ms"),
            "usage": result.get("usage", {}),
            "postprocess_applied": result.get("postprocess_applied", []),
            "raw_text": result.get("raw_text", ""),
            "text": result.get("text", ""),
            "error_message": result.get("error_message", ""),
        }
        return result

    return generate


def case_payload(case: dict[str, Any], default_options: dict[str, Any]) -> dict[str, Any]:
    if isinstance(case.get("explain_request"), dict):
        request = json.loads(json.dumps(case["explain_request"], ensure_ascii=False))
        request.setdefault("options", default_options)
        return request
    case_id = str(case.get("id", ""))
    if case_id not in SMOKE_CARRY_REQUESTS:
        raise KeyError(f"carry smoke case payload not found for {case_id}")
    request = json.loads(json.dumps(SMOKE_CARRY_REQUESTS[case_id], ensure_ascii=False))
    request["options"] = dict(default_options)
    return request


def output_phi_hit(response: dict[str, Any], scan_output: Callable[[str], tuple[bool, str]]) -> bool:
    fields = [str(response.get("summary", "")), str(response.get("error_message", ""))]
    for citation in response.get("citations", []) or []:
        if isinstance(citation, dict):
            fields.append(str(citation.get("snippet", "")))
    return any(scan_output(value)[0] for value in fields)


def expected_citations_missing(response: dict[str, Any], expected: list[str]) -> list[str]:
    returned = {
        str(citation.get("source_id", "")).strip()
        for citation in response.get("citations", []) or []
        if isinstance(citation, dict)
    }
    return [source_id for source_id in expected if source_id not in returned]


def returned_citation_issues(response: dict[str, Any]) -> list[str]:
    retrieved = {
        str(item.get("source_id", "")).strip()
        for item in response.get("retrieved", []) or []
        if isinstance(item, dict)
    }
    issues: list[str] = []
    for citation in response.get("citations", []) or []:
        if not isinstance(citation, dict):
            issues.append("<non-dict-citation>")
            continue
        source_id = str(citation.get("source_id", "")).strip()
        if not source_id or source_id not in retrieved:
            issues.append(source_id or "<empty-source-id>")
    return issues


def percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * pct)))
    return ordered[index]


def summarize_model_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ok = [case for case in cases if case.get("model_call_expected") and case.get("expected_status") == "ok"]
    model_call_cases = [case for case in cases if case.get("model_call_expected")]
    walls = [int(case.get("wall_ms") or 0) for case in model_call_cases]
    return {
        "case_count": len(cases),
        "expected_ok_case_count": len(expected_ok),
        "status_match_count": sum(1 for case in cases if case.get("status_matches_expected")),
        "citation_present_count": sum(1 for case in expected_ok if case.get("citation_present")),
        "citation_valid_strict_count": sum(
            1 for case in expected_ok if case.get("citation_present") and case.get("citation_valid_strict")
        ),
        "expected_citation_hit_count": sum(1 for case in expected_ok if not case.get("expected_citations_missing")),
        "json_parse_failed_count": sum(1 for case in cases if case.get("failure_reason") == "json_parse_failed"),
        "schema_failed_count": sum(1 for case in cases if case.get("failure_reason") == "schema_failed"),
        "retrieval_expected_missing_count": sum(
            1 for case in cases if case.get("failure_reason") == "retrieval_expected_missing"
        ),
        "phi_hit_count": sum(1 for case in cases if case.get("output_phi_hit")),
        "llm_call_unexpected_count": sum(1 for case in cases if case.get("llm_called") and not case.get("model_call_expected")),
        "warm_p50_wall_ms": int(statistics.median(walls[1:])) if len(walls) > 1 else 0,
        "warm_p95_wall_ms": percentile(walls[1:], 0.95) if len(walls) > 1 else 0,
    }


def classify_failure_reason(case_result: dict[str, Any]) -> str:
    if case_result.get("status_matches_expected"):
        return ""
    error = str(case_result.get("error_message", ""))
    if "JSON" in error and ("파싱" in error or "parse" in error.lower()):
        return "json_parse_failed"
    if "schema" in error.lower() or "형식" in error:
        return "schema_failed"
    if "bracket" in error.lower():
        return "malformed_citation"
    if "불일치" in error or "mismatch" in error.lower():
        return "dropped_citation"
    expected_missing = set(case_result.get("expected_citations_missing", []) or [])
    retrieved = set(case_result.get("retrieved_source_ids", []) or [])
    if expected_missing and expected_missing.isdisjoint(retrieved):
        return "retrieval_expected_missing"
    if expected_missing:
        return "expected_citation_missing"
    if case_result.get("status") == "citation_failed":
        return "citation_failed"
    return "status_mismatch"


def validate_config(config: dict[str, Any], eval_set: dict[str, Any], selected_models: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    model_labels = [str(model.get("label", "")) for model in config.get("models", [])]
    cell_key = "stage_a_cells" if "stage_a_cells" in config else "stage_ar_cells"
    cell_labels = [str(cell.get("model_label", "")) for cell in config.get(cell_key, [])]
    if len(model_labels) != len(set(model_labels)):
        errors.append("duplicate model labels")
    if len(cell_labels) != len(set(cell_labels)):
        errors.append(f"duplicate {cell_key} model labels")
    missing_models = sorted(set(cell_labels) - set(model_labels))
    if missing_models:
        errors.append(f"{cell_key} without model entries: {', '.join(missing_models)}")
    for model in config.get("models", []):
        if model.get("served_model_id") != model.get("label"):
            errors.append(f"served_model_id != label for {model.get('label')}")
    if len(eval_set.get("cases", [])) != int(config.get("_rag_endpoint", {}).get("case_count", 0)):
        errors.append("eval set case_count mismatch")
    runner = str(config.get("_rag_endpoint", {}).get("runner", ""))
    if runner and not (REPO_ROOT / runner).exists():
        errors.append(f"runner path not found: {runner}")
    for model in selected_models:
        try:
            explain_response_format(str(model.get("inference_options", {}).get("response_format", config.get("_inference_profile_defaults", {}).get("response_format", "json_object"))))
        except Exception as exc:
            errors.append(f"{model.get('label')}: invalid response_format: {exc}")
    if not selected_models:
        errors.append("no models selected")
    return errors


def validate_case_payloads(cases: list[dict[str, Any]], default_options: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for case in cases:
        case_id = str(case.get("id", ""))
        try:
            payload = case_payload(case, default_options)
        except Exception as exc:
            errors.append(f"{case_id}: payload build failed: {exc}")
            continue
        if not isinstance(payload.get("check_result"), dict):
            errors.append(f"{case_id}: check_result is missing or not an object")
        if not isinstance(payload.get("context"), dict):
            errors.append(f"{case_id}: context is missing or not an object")
        if not isinstance(payload.get("options"), dict):
            errors.append(f"{case_id}: options is missing or not an object")
    return errors


def select_models(config: dict[str, Any], wanted: list[str] | None) -> list[dict[str, Any]]:
    models = list(config.get("models", []))
    if not wanted:
        return models
    wanted_set = set(wanted)
    selected = [model for model in models if model.get("label") in wanted_set]
    missing = sorted(wanted_set - {str(model.get("label", "")) for model in selected})
    if missing:
        raise ValueError(f"unknown model labels: {', '.join(missing)}")
    return selected


def select_cases(eval_set: dict[str, Any], wanted: list[str] | None) -> list[dict[str, Any]]:
    cases = list(eval_set.get("cases", []))
    if not wanted:
        return cases
    wanted_set = set(wanted)
    selected = [case for case in cases if case.get("id") in wanted_set]
    missing = sorted(wanted_set - {str(case.get("id", "")) for case in selected})
    if missing:
        raise ValueError(f"unknown case IDs: {', '.join(missing)}")
    return selected


def write_outputs(payload: dict[str, Any], timestamp: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(exist_ok=True)
    prefix = str(payload.get("result_prefix", "hpz2_lmstudio_phase2_stage_a"))
    title = str(payload.get("stage_label", "HP Z2 LM Studio Phase 2 Stage A"))
    json_path = RESULTS_DIR / f"{prefix}_{timestamp}.json"
    md_path = RESULTS_DIR / f"{prefix}_{timestamp}.md"
    with json_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with md_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# {title}\n\n")
        handle.write(f"- generated_at: {payload['generated_at']}\n")
        handle.write(f"- stage_label: `{payload.get('stage_label', '')}`\n")
        handle.write(f"- config: `{payload['config']}`\n")
        handle.write(f"- eval_set: `{payload['eval_set']}`\n")
        handle.write(f"- emr_repo: `{payload['emr_repo']}`\n")
        handle.write(f"- lmstudio_server_url: `{payload['server_url']}`\n")
        handle.write(f"- stopped_early: {payload.get('stopped_early', False)}\n\n")
        handle.write("## Model Summary\n\n")
        handle.write("| model | run | load_s | cases | status match | valid cites | expected cites | json parse fail | retrieval miss | phi hits | warm p50 | warm p95 | error |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for row in payload["results"]:
            summary = row.get("summary", {})
            status = "pass" if row.get("success") else "fail"
            expected_ok = summary.get("expected_ok_case_count", 0)
            citation_text = f"{summary.get('citation_valid_strict_count', 0)}/{expected_ok}"
            expected_text = f"{summary.get('expected_citation_hit_count', 0)}/{expected_ok}"
            status_text = f"{summary.get('status_match_count', 0)}/{summary.get('case_count', 0)}"
            error = str(row.get("error") or "")[:120].replace("\n", " ")
            handle.write(
                f"| {row['model_label']} | {status} | {row.get('load_s', '-')} | "
                f"{summary.get('case_count', 0)} | {status_text} | {citation_text} | "
                f"{expected_text} | {summary.get('json_parse_failed_count', 0)} | "
                f"{summary.get('retrieval_expected_missing_count', 0)} | {summary.get('phi_hit_count', 0)} | "
                f"{summary.get('warm_p50_wall_ms', 0)} | {summary.get('warm_p95_wall_ms', 0)} | {error} |\n"
            )
        handle.write("\n## Case Details\n\n")
        for row in payload["results"]:
            handle.write(f"### {row['model_label']}\n\n")
            for case in row.get("cases", []):
                missing = ", ".join(case.get("expected_citations_missing", [])) or "-"
                handle.write(
                    f"- `{case['case_id']}` status={case['status']} expected={case['expected_status']} "
                    f"wall_ms={case['wall_ms']} citations={case['citation_count']} "
                    f"missing_expected={missing} failure={case.get('failure_reason') or '-'} "
                    f"phi_hit={case['output_phi_hit']}\n"
                )
            handle.write("\n")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HP Z2 LM Studio Phase 2 Stage A.")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--eval-set", default=DEFAULT_EVAL_SET)
    parser.add_argument("--server-url", default=None)
    parser.add_argument("--emr-repo", default=None)
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--case-ids", nargs="*")
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--skip-estimate", action="store_true")
    parser.add_argument("--disable-response-format", action="store_true")
    parser.add_argument("--pacing-scale", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-hpz2", action="store_true")
    parser.add_argument("--confirm-heavy-run", action="store_true")
    return parser.parse_args()


def dry_run_report(config: dict[str, Any], eval_set: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]]) -> int:
    errors = validate_config(config, eval_set, models)
    errors.extend(validate_case_payloads(cases, dict(eval_set.get("common_options_default", {}))))
    print(f"{config.get('_stage_label', 'HP Z2 LM Studio Phase 2 Stage A')} dry-run")
    print(f"models: {len(models)}")
    for model in models:
        profile = model.get("inference_options", {}).get("profile", "strict-baseline")
        response_format = model.get("inference_options", {}).get(
            "response_format", config.get("_inference_profile_defaults", {}).get("response_format", "json_object")
        )
        print(f"  - {model['label']} -> {model['lms_key']} [{profile}, {response_format}]")
    print(f"cases: {len(cases)}")
    print(f"hold_models: {len(config.get('hold_models', []))}")
    pacing = config.get("_execution_pacing", {})
    print(f"post_unload_cooldown_sec: {pacing.get('post_unload_cooldown_sec')}")
    print(f"post_large_model_cooldown_sec: {pacing.get('post_large_model_cooldown_sec')}")
    if errors:
        print("config errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("dry-run only; no lms commands, model loads, LM Studio API calls, or /explain calls were executed.")
    return 0


def run_stage_a(args: argparse.Namespace, config: dict[str, Any], eval_set: dict[str, Any]) -> int:
    if not args.confirm_hpz2 or not args.confirm_heavy_run:
        print("Refusing real execution without --confirm-hpz2 and --confirm-heavy-run.", file=sys.stderr)
        return 2

    config_path = (REPO_ROOT / args.config).resolve()
    emr_repo = resolve_app_repo(config, config_path, args.emr_repo)
    emr_status = emr_git_status(emr_repo)
    server_url = openai_base_url(args.server_url or config.get("_backend", {}).get("server_url_default", DEFAULT_SERVER_URL))
    settings_host = settings_host_from_server_url(server_url)
    models = select_models(config, args.models)
    cases = select_cases(eval_set, args.case_ids)
    common_options = dict(eval_set.get("common_options_default", {}))
    errors = validate_config(config, eval_set, models)
    errors.extend(validate_case_payloads(cases, common_options))
    if errors:
        for error in errors:
            print(f"config error: {error}", file=sys.stderr)
        return 2
    if emr_status.get("returncode") != 0:
        print("Could not read EMR git status.", file=sys.stderr)
        return 2
    dirty_lines = dirty_git_status_lines(emr_status)
    if dirty_lines:
        preview = "; ".join(dirty_lines[:5])
        print(f"EMR_AI_24clinic is not clean; refusing execution: {preview}", file=sys.stderr)
        return 2

    lms_exe = find_lms_exe()
    initial_status = lms_status(lms_exe)
    if initial_status.get("returncode") != 0:
        print(initial_status.get("stderr", ""), file=sys.stderr)
        return 1

    explain_module, ExplainRequest, scan_output = import_emr_explain(emr_repo)
    pacing = config.get("_execution_pacing", {})
    large_labels = set(pacing.get("large_model_labels", []))
    cli_args_default = normalize_cli_args(config.get("_load_profile", {}).get("lms_cli_args"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    call_counter = {"count": 0}
    runtime_options_by_model = {
        str(model.get("served_model_id") or model.get("label")): merged_inference_options(config, model, args)
        for model in models
    }
    explain_module.generate_llm = make_lmstudio_generate(
        server_url=server_url,
        runtime_options_by_model=runtime_options_by_model,
        call_counter=call_counter,
    )

    payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": args.config,
        "eval_set": args.eval_set,
        "server_url": server_url,
        "stage_label": config.get("_stage_label", "HP Z2 LM Studio Phase 2 Stage A"),
        "result_prefix": config.get("_result_artifact_prefix", "hpz2_lmstudio_phase2_stage_a"),
        "emr_repo": str(emr_repo),
        "emr_git_status": emr_status,
        "host": {
            "node": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "pacing": pacing,
        "results": [],
        "stopped_early": False,
    }

    hard_stop = False
    for index, model in enumerate(models, start=1):
        label = str(model["label"])
        key = str(model["lms_key"])
        served_model_id = str(model.get("served_model_id") or label)
        load_options = dict(model.get("load_options", {}))
        cli_args = normalize_cli_args(model.get("lms_cli_args", cli_args_default))
        runtime_options = runtime_options_by_model[served_model_id]
        row: dict[str, Any] = {
            "model_label": label,
            "lms_key": key,
            "served_model_id": served_model_id,
            "role": model.get("_role", ""),
            "load_options": load_options,
            "inference_options": runtime_options,
            "lms_cli_args": cli_args,
            "cases": [],
        }
        print(f"\n[{index}/{len(models)}] {label} ({key})")

        if pacing.get("unload_all_before_each_model", True):
            row["pre_unload"] = unload_all(lms_exe)
            no_models = wait_for_no_models(lms_exe)
            row["pre_load_lms_status"] = no_models
            if not lms_status_has_no_models(no_models):
                row["success"] = False
                row["error"] = "LM Studio did not report no loaded models before load"
                payload["results"].append(row)
                hard_stop = True
                break
            sleep_with_scale(pacing.get("post_unload_cooldown_sec", 0), args.pacing_scale, "post-unload cooldown")

        if config.get("_load_profile", {}).get("estimate_before_load", True) and not args.skip_estimate:
            row["estimate"] = estimate_model(lms_exe, key, load_options, cli_args)
            if row["estimate"].get("returncode") != 0:
                row["success"] = False
                row["error"] = "estimate failed"
                payload["results"].append(row)
                sleep_with_scale(pacing.get("post_failure_cooldown_sec", 0), args.pacing_scale, "post-failure cooldown")
                continue

        load = load_model(lms_exe, key, served_model_id, load_options, cli_args)
        row["load"] = load
        row["load_s"] = load.get("elapsed_s")
        if load.get("returncode") != 0:
            row["success"] = False
            row["error"] = "load failed"
            payload["results"].append(row)
            unload_all(lms_exe)
            sleep_with_scale(pacing.get("post_failure_cooldown_sec", 0), args.pacing_scale, "post-failure cooldown")
            continue

        sleep_with_scale(pacing.get("post_load_settle_sec", 0), args.pacing_scale, "post-load settle")
        os.environ["EMR_LLM_ENABLED"] = "true"
        os.environ["EMR_LLM_PROVIDER"] = "ollama"
        os.environ["EMR_LLM_MODEL"] = served_model_id
        os.environ["EMR_LLM_HOST"] = settings_host
        os.environ["EMR_LLM_TIMEOUT_SECONDS"] = str(runtime_options.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))

        for case in cases:
            case_id = str(case.get("id", ""))
            request_payload = case_payload(case, common_options)
            before_calls = call_counter.get("count", 0)
            call_counter["last_trace"] = {}
            started = time.perf_counter()
            response_error = ""
            try:
                response = explain_module.explain_check_result(ExplainRequest(**request_payload))
            except Exception as exc:  # Keep the model cleanup/report path alive on app-side exceptions.
                response_error = "case execution exception"
                response = {
                    "status": "runner_exception",
                    "summary": "",
                    "error_message": f"{type(exc).__name__}: {exc}",
                    "citations": [],
                    "retrieved": [],
                }
            wall_ms = int((time.perf_counter() - started) * 1000)
            after_calls = call_counter.get("count", 0)
            trace = call_counter.get("last_trace") if after_calls > before_calls else {}
            expected_status = str(case.get("expected_status", "ok"))
            model_call_expected = bool(case.get("model_call_expected", True))
            expected_citations = [
                str(source_id)
                for source_id in case.get("expected_citations_includes_at_least", [])
                if str(source_id) and not str(source_id).startswith("{TBD")
            ]
            citation_issues = returned_citation_issues(response)
            citation_count = len(response.get("citations", []) or [])
            case_result = {
                "case_id": case_id,
                "expected_status": expected_status,
                "status": response.get("status"),
                "status_matches_expected": response.get("status") == expected_status,
                "model_call_expected": model_call_expected,
                "llm_called": after_calls > before_calls,
                "wall_ms": wall_ms,
                "latency_ms": response.get("latency_ms"),
                "citation_count": citation_count,
                "retrieved_count": len(response.get("retrieved", []) or []),
                "citation_present": citation_count > 0,
                "citation_valid_strict": citation_count > 0 and not citation_issues,
                "invalid_returned_citations": citation_issues,
                "expected_citations_missing": expected_citations_missing(response, expected_citations),
                "output_phi_hit": output_phi_hit(response, scan_output),
                "summary": str(response.get("summary", ""))[:500],
                "error_message": response.get("error_message", ""),
                "returned_source_ids": [
                    citation.get("source_id", "")
                    for citation in response.get("citations", []) or []
                    if isinstance(citation, dict)
                ],
                "retrieved_source_ids": [
                    item.get("source_id", "")
                    for item in response.get("retrieved", []) or []
                    if isinstance(item, dict)
                ],
            }
            case_result["failure_reason"] = classify_failure_reason(case_result)
            if trace:
                case_result["llm_trace"] = {
                    "status": trace.get("status"),
                    "latency_ms": trace.get("latency_ms"),
                    "usage": trace.get("usage", {}),
                    "postprocess_applied": trace.get("postprocess_applied", []),
                    "error_message": trace.get("error_message", ""),
                }
                if runtime_options.get("capture_raw_text_preview"):
                    raw_text = str(trace.get("raw_text", ""))
                    processed_text = str(trace.get("text", ""))
                    case_result["llm_raw_text_preview"] = (
                        "<redacted: phi-like output>"
                        if scan_output(raw_text)[0]
                        else raw_text[:1000]
                    )
                    case_result["llm_processed_text_preview"] = (
                        "<redacted: phi-like output>"
                        if scan_output(processed_text)[0]
                        else processed_text[:1000]
                    )
            row["cases"].append(case_result)
            print(
                "  {case_id}: status={status} expected={expected} wall={wall_ms}ms cites={cites} phi={phi}".format(
                    case_id=case_id,
                    status=case_result["status"],
                    expected=expected_status,
                    wall_ms=wall_ms,
                    cites=case_result["citation_count"],
                    phi=case_result["output_phi_hit"],
                )
            )
            if case_result["output_phi_hit"]:
                row["error"] = "PHI output hit"
                hard_stop = True
                break
            if response_error:
                row["error"] = response_error
                hard_stop = True
                break

        row["summary"] = summarize_model_cases(row["cases"])
        row["success"] = (
            not row.get("error")
            and row["summary"]["phi_hit_count"] == 0
            and row["summary"]["llm_call_unexpected_count"] == 0
        )
        payload["results"].append(row)

        if pacing.get("unload_all_after_each_model", True):
            row["post_unload"] = unload_all(lms_exe)
            row["post_unload_lms_status"] = wait_for_no_models(lms_exe)
        cooldown = pacing.get("post_large_model_cooldown_sec" if label in large_labels or row.get("error") else "post_unload_cooldown_sec", 0)
        sleep_with_scale(cooldown, args.pacing_scale, "between-model cooldown")
        if hard_stop:
            payload["stopped_early"] = True
            break

    payload["final_lms_status"] = lms_status(lms_exe)
    json_path, md_path = write_outputs(payload, timestamp)
    print(f"\nwrote: {json_path}")
    print(f"wrote: {md_path}")
    return 1 if payload.get("stopped_early") or any(not row.get("success") for row in payload["results"]) else 0


def main() -> int:
    args = parse_args()
    config = load_json(REPO_ROOT / args.config)
    eval_set = load_json(REPO_ROOT / args.eval_set)
    models = select_models(config, args.models)
    cases = select_cases(eval_set, args.case_ids)
    if args.dry_run:
        return dry_run_report(config, eval_set, models, cases)
    return run_stage_a(args, config, eval_set)


if __name__ == "__main__":
    raise SystemExit(main())
