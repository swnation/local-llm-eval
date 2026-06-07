#!/usr/bin/env python3
"""HP Z2 Gemma 4 QAT llama.cpp output-contract pilot runner.

Dry-run validates the tiny synthetic matrix only. Real execution is refused
unless both --confirm-hpz2 and
--confirm-gemma-llamacpp-output-contract-pilot are provided.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from hpz2_lmstudio_phase2_l2_semantic_runner import (
    call_chat_completion,
    load_json,
    response_format_payload,
    write_json,
)
from hpz2_llamacpp_h2_output_contract_calibration_runner import (
    normalize_source_id,
    scan_phi_like,
    strip_code_fence,
)
from hpz2_llamacpp_phase2_l2_runner import (
    build_server_args,
    memory_snapshot,
    output_root,
    preflight as base_preflight,
    preflight_pass as base_preflight_pass,
    server_url,
    wait_for_server,
)


DEFAULT_CONFIG = "models_config_hpz2_llamacpp_phase2_l2_v0.1.json"
DEMO_SOURCE_ID = "kb:DEMO_GEMMA_OUTPUT:001"
DEMO_CITATION = f"[{DEMO_SOURCE_ID}]"
DEFAULT_MODELS = ["hpz2-gemma4-26b-a4b-qat-q4_0"]
REFERENCE_MODELS = ["hpz2-gemma4-31b-qat-q4_0"]
DEFAULT_CONTRACTS = ["G1", "G2"]

QAT_MODELS: list[dict[str, Any]] = [
    {
        "label": "hpz2-gemma4-26b-a4b-qat-q4_0",
        "backend": "llama.cpp",
        "model_family": "google/gemma-4-26b-a4b-it-qat",
        "model_path": r"C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B-it-QAT-GGUF\gemma-4-26B-A4B-it-QAT-Q4_0.gguf",
        "served_model_id": "hpz2-gemma4-26b-a4b-qat-q4_0",
        "_quant": "Q4_0",
        "_expected_size_bytes": 14439362752,
        "_sha256": "9B96AA267521008235F8792590CB8E2DC47A8A236C6FF1767964CBBE32510873",
        "inference_options": {"temperature": 0.0, "max_tokens": 512},
    },
    {
        "label": "hpz2-gemma4-31b-qat-q4_0",
        "backend": "llama.cpp",
        "model_family": "google/gemma-4-31b-it-qat",
        "model_path": r"C:\Users\test\.lmstudio\models\lmstudio-community\gemma-4-31B-it-QAT-GGUF\gemma-4-31B-it-QAT-Q4_0.gguf",
        "served_model_id": "hpz2-gemma4-31b-qat-q4_0",
        "_quant": "Q4_0",
        "_expected_size_bytes": 17651000768,
        "_sha256": "E664C3B437599D70EB7C470E66AAA938C0948C1851A9257F86A96306B94E8C18",
        "inference_options": {"temperature": 0.0, "max_tokens": 512},
    },
]

CONTRACTS: list[dict[str, Any]] = [
    {
        "id": "G1",
        "label": "final-answer-control",
        "response_format": "none",
        "max_tokens": 512,
    },
    {
        "id": "G2",
        "label": "json-schema-native-contract",
        "response_format": "json_schema",
        "max_tokens": 512,
    },
]


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def iso_now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def run_cmd(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except Exception as exc:
        return {"returncode": -1, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def powershell(script: str, timeout: int = 60) -> dict[str, Any]:
    return run_cmd(["powershell", "-NoProfile", "-Command", script], timeout=timeout)


def now_result_dir(root_value: str | None, timestamp: str) -> Path:
    return output_root(root_value) / f"gemma_llamacpp_output_contract_pilot_{timestamp}"


def build_prompt(contract: dict[str, Any]) -> tuple[str, str]:
    system = (
        "You are testing output-contract compliance for a synthetic non-PHI "
        "local-model evidence pack. Use only the provided evidence. Do not "
        "invent source IDs. Do not include patient identifiers."
    )
    if contract["id"] == "G1":
        task = "Return one concise final answer sentence with the exact citation."
    else:
        task = (
            "Return only a JSON object with exactly these keys: summary, citations. "
            "citations must be an array containing the exact bracketed source ID."
        )
    user = f"""Case: GEMMA-OUTPUT-CONTRACT-DEMO

Task:
{task}

Evidence pack:
[{DEMO_SOURCE_ID}] This synthetic evidence says the output must explain only that the local model is being tested for final-answer and JSON-contract behavior.

Valid source IDs:
["{DEMO_SOURCE_ID}"]

Required citation:
{DEMO_CITATION}

Do not output any patient name, chart number, resident registration number, phone number, or clinical instruction.
"""
    return system, user


def select_models(labels: list[str] | None, include_reference: bool) -> list[dict[str, Any]]:
    wanted = labels or DEFAULT_MODELS + (REFERENCE_MODELS if include_reference else [])
    by_label = {model["label"]: model for model in QAT_MODELS}
    missing = [label for label in wanted if label not in by_label]
    if missing:
        raise ValueError("unknown Gemma QAT model label(s): " + ", ".join(missing))
    return [by_label[label] for label in wanted]


def select_contracts(wanted: list[str] | None) -> list[dict[str, Any]]:
    labels = wanted or DEFAULT_CONTRACTS
    by_id = {contract["id"]: contract for contract in CONTRACTS}
    missing = [label for label in labels if label not in by_id]
    if missing:
        raise ValueError("unknown contract ID(s): " + ", ".join(missing))
    return [by_id[label] for label in labels]


def validate_static(config: dict[str, Any], models: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if config.get("backend") != "llama.cpp":
        errors.append("backend must be llama.cpp")
    default_args = [str(item) for item in config.get("runtime", {}).get("default_args", [])]
    for flag in ("--no-mmap", "--no-host", "--kv-offload", "--op-offload", "--cache-ram", "--ctx-checkpoints", "--reasoning"):
        if flag not in default_args:
            errors.append(f"runtime.default_args missing {flag}")
    for model in models:
        for key in ("label", "model_path", "served_model_id", "_sha256"):
            if not model.get(key):
                errors.append(f"model missing {key}: {model}")
        model_path = str(model.get("model_path", ""))
        if "QAT-Q4_0.gguf" not in model_path:
            errors.append(f"model is not the QAT Q4_0 text GGUF: {model.get('label')}")
        if "mmproj" in model_path.lower():
            errors.append(f"mmproj is not allowed in text-only pilot: {model.get('label')}")
    if [contract["id"] for contract in contracts] != sorted([contract["id"] for contract in contracts], key=DEFAULT_CONTRACTS.index):
        errors.append("contracts must stay in G1 then G2 order when both are selected")
    return errors


def file_verification(model: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(model["model_path"]))
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "expected_sha256": model.get("_sha256"),
        "sha256": "",
        "sha256_match": False,
        "size_bytes": None,
        "expected_size_bytes": model.get("_expected_size_bytes"),
        "size_match": False,
    }
    if not path.exists() or not path.is_file():
        return result
    result["size_bytes"] = path.stat().st_size
    result["size_match"] = result["size_bytes"] == model.get("_expected_size_bytes")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    result["sha256"] = digest.hexdigest().upper()
    result["sha256_match"] = result["sha256"] == str(model.get("_sha256", "")).upper()
    return result


def runtime_snapshot() -> dict[str, Any]:
    script = r"""
$ports = @(Get-NetTCPConnection -LocalPort 18080,18081 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess)
$shim = @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -like '*hpz2_ollama_compat_llamacpp_shim.py*' } | Select-Object ProcessId,CommandLine)
[pscustomobject]@{
  ports = $ports
  shim_processes = $shim
} | ConvertTo-Json -Depth 4 -Compress
"""
    result = powershell(script)
    try:
        parsed = json.loads(result["stdout"] or "{}")
        return {"ok": result["returncode"] == 0, **parsed}
    except Exception:
        return {"ok": False, "error": result}


def gemma_preflight(config: dict[str, Any], models: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "base": base_preflight(config),
        "runtime": runtime_snapshot(),
        "files": [file_verification(model) for model in models],
    }
    return report


def gemma_preflight_pass(config: dict[str, Any], report: dict[str, Any]) -> tuple[bool, str]:
    base_ok, base_reason = base_preflight_pass(config, report.get("base", {}))
    if not base_ok:
        return False, base_reason
    runtime = report.get("runtime", {})
    if not runtime.get("ok", False):
        return False, "runtime process/port snapshot failed"
    if runtime.get("ports"):
        return False, "port 18080/18081 listener detected before run"
    if runtime.get("shim_processes"):
        return False, "stale shim process detected before run"
    for item in report.get("files", []):
        if not item.get("exists"):
            return False, "selected QAT GGUF file missing: " + str(item.get("path"))
        if not item.get("size_match"):
            return False, "selected QAT GGUF size mismatch: " + str(item.get("path"))
        if not item.get("sha256_match"):
            return False, "selected QAT GGUF SHA256 mismatch: " + str(item.get("path"))
    return True, ""


def strict_json_object(text: str) -> tuple[dict[str, Any] | None, str]:
    clean, fenced = strip_code_fence(text)
    if fenced:
        return None, "markdown_fence_present"
    if clean != text.strip():
        return None, "extra_text"
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(parsed, dict):
        return None, "not_json_object"
    return parsed, "parsed"


def repeated_token_loop(text: str) -> bool:
    if "<unused49>" in text:
        return True
    words = text.split()
    if len(words) < 24:
        return False
    tail = words[-24:]
    return len(set(tail)) <= 3


def scan_response_phi(response: dict[str, Any]) -> list[str]:
    return scan_phi_like(str(response.get("text", "")) + "\n" + str(response.get("reasoning_text", "")))


def base_score(contract: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    content = str(response.get("text", ""))
    reasoning = str(response.get("reasoning_text", ""))
    phi_hits = scan_response_phi(response)
    score: dict[str, Any] = {
        "contract_id": contract["id"],
        "contract_label": contract["label"],
        "contract_pass": False,
        "endpoint_eligible": False,
        "pass_status": "FAIL",
        "failure_owner": "",
        "phi_like_hits": phi_hits,
        "json_parse_status": "",
        "json_keys": [],
        "summary_nonempty": False,
        "citations_exact": False,
        "citation_values": [],
        "reasoning_control_status": "pass" if not reasoning else "reasoning_present",
        "raw_model_output_stored": False,
        "metric_risk_notes": [],
    }
    if response.get("status") != "ok":
        score["failure_owner"] = "api"
        return score
    if phi_hits:
        score["failure_owner"] = "PHI"
        score["metric_risk_notes"].append("PHI-like pattern detected before output scoring")
        return score
    if repeated_token_loop(content + " " + reasoning):
        score["failure_owner"] = "runtime_template_or_reasoning_control"
        score["metric_risk_notes"].append("token loop pattern detected")
        return score
    if response.get("output_channel_status") == "reasoning_only_output":
        score["failure_owner"] = "output_channel_policy"
        score["json_parse_status"] = "not_scored_reasoning_only_output"
        score["metric_risk_notes"].append("answer emitted outside final content channel")
        return score
    return score


def score_g1(response: dict[str, Any]) -> dict[str, Any]:
    score = base_score(CONTRACTS[0], response)
    if score["failure_owner"]:
        return score
    content_chars = int(response.get("content_chars", 0) or 0)
    reasoning_chars = int(response.get("reasoning_chars", 0) or 0)
    if content_chars <= 0:
        score["failure_owner"] = "empty_final_content"
        return score
    if reasoning_chars > 0:
        score["pass_status"] = "WARN"
        score["failure_owner"] = "reasoning_control_warn"
        score["metric_risk_notes"].append("final content present, but reasoning channel was also present")
        return score
    score["contract_pass"] = True
    score["endpoint_eligible"] = True
    score["pass_status"] = "PASS"
    return score


def score_g2(response: dict[str, Any]) -> dict[str, Any]:
    score = base_score(CONTRACTS[1], response)
    if score["failure_owner"]:
        return score
    parsed, parse_status = strict_json_object(str(response.get("text", "")))
    score["json_parse_status"] = parse_status
    if not parsed:
        score["failure_owner"] = "native_contract"
        return score
    keys = sorted(parsed.keys())
    score["json_keys"] = keys
    summary = parsed.get("summary")
    citations = parsed.get("citations")
    score["summary_nonempty"] = isinstance(summary, str) and bool(summary.strip())
    if isinstance(citations, list):
        score["citation_values"] = [str(item) for item in citations]
    normalized = [normalize_source_id(item)[0] for item in score["citation_values"]]
    score["citations_exact"] = score["citation_values"] == [DEMO_CITATION] and normalized == [DEMO_SOURCE_ID]
    if keys != ["citations", "summary"] or not score["summary_nonempty"] or not score["citations_exact"]:
        score["failure_owner"] = "native_contract"
        return score
    score["contract_pass"] = True
    score["endpoint_eligible"] = int(response.get("reasoning_chars", 0) or 0) == 0
    score["pass_status"] = "PASS" if score["endpoint_eligible"] else "WARN"
    if not score["endpoint_eligible"]:
        score["failure_owner"] = "reasoning_control_warn"
        score["metric_risk_notes"].append("JSON contract passed, but reasoning channel was also present")
    return score


def score_response(contract: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    if contract["id"] == "G1":
        return score_g1(response)
    if contract["id"] == "G2":
        return score_g2(response)
    raise ValueError("unsupported contract: " + str(contract.get("id")))


def inference_options(model: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    options = dict(model.get("inference_options", {}))
    options["response_format"] = contract["response_format"]
    options["max_tokens"] = int(contract.get("max_tokens", options.get("max_tokens", 512)))
    options.setdefault("temperature", 0.0)
    options.setdefault("timeout_seconds", 900)
    return options


def write_summary(out_dir: Path, payload: dict[str, Any]) -> Path:
    path = out_dir / "gemma_llamacpp_output_contract_summary.md"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Gemma llama.cpp Output-Contract Pilot\n\n")
        handle.write(f"- generated_at: `{payload['generated_at']}`\n")
        handle.write(f"- stopped_early: `{payload.get('stopped_early')}`\n")
        handle.write(f"- stop_reason: `{payload.get('stop_reason', '')}`\n")
        handle.write("- backend: direct llama.cpp `/v1/chat/completions`\n")
        handle.write("- endpoint readiness: not assessed; no `/explain` call\n")
        handle.write("- raw model output stored: false\n\n")
        handle.write("| model | contract | api | channel | content chars | reasoning chars | parse | pass | endpoint eligible | failure |\n")
        handle.write("|---|---|---|---|---:|---:|---|---|---|---|\n")
        for model in payload.get("models", []):
            for cell in model.get("cells", []):
                handle.write(
                    "| {model} | {contract} | {api} | {channel} | {content} | {reasoning} | {parse} | {status} | {eligible} | {failure} |\n".format(
                        model=model.get("label"),
                        contract=cell.get("contract_id"),
                        api=cell.get("api_status"),
                        channel=cell.get("output_channel_status", ""),
                        content=cell.get("content_chars", 0),
                        reasoning=cell.get("reasoning_chars", 0),
                        parse=cell.get("json_parse_status", ""),
                        status=cell.get("pass_status"),
                        eligible=cell.get("endpoint_eligible"),
                        failure=cell.get("failure_owner", ""),
                    )
                )
    return path


def dry_run(config: dict[str, Any], models: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> int:
    errors = validate_static(config, models, contracts)
    if errors:
        print("Gemma llama.cpp output-contract dry-run failed:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("HP Z2 Gemma llama.cpp output-contract pilot dry-run")
    print("backend: direct llama.cpp /v1/chat/completions")
    print(f"models: {len(models)}")
    for model in models:
        print(f"  - {model['label']} -> {model['model_path']}")
    print(f"contracts: {len(contracts)}")
    for contract in contracts:
        print(f"  - {contract['id']} {contract['label']} [{contract['response_format']}]")
    print(f"planned calls: {len(models) * len(contracts)}")
    print("dry-run only; no llama-server, model load, LM Studio API, shim, /explain, EMR write, or raw output storage was executed.")
    return 0


def run_real(args: argparse.Namespace, config: dict[str, Any], models: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> int:
    errors = validate_static(config, models, contracts)
    if errors:
        for error in errors:
            print(error)
        return 2
    if not (args.confirm_hpz2 and args.confirm_gemma_llamacpp_output_contract_pilot):
        print("Refusing execution without --confirm-hpz2 and --confirm-gemma-llamacpp-output-contract-pilot.", flush=True)
        return 2

    timestamp = now_stamp()
    out_dir = now_result_dir(args.output_root, timestamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    preflight = gemma_preflight(config, models)
    ok, reason = gemma_preflight_pass(config, preflight)
    payload: dict[str, Any] = {
        "generated_at": iso_now(),
        "mode": "gemma_llamacpp_output_contract_pilot",
        "backend": "llama.cpp",
        "config": args.config,
        "raw_model_output_stored": False,
        "endpoint_readiness_assessed": False,
        "preflight": preflight,
        "models": [],
        "stopped_early": False,
        "stop_reason": "",
    }
    if not ok:
        payload["stopped_early"] = True
        payload["stop_reason"] = reason
        write_json(out_dir / "gemma_llamacpp_output_contract_results.json", payload)
        write_summary(out_dir, payload)
        print(f"STOP: {reason}")
        return 1

    runtime = config.get("runtime", {})
    pacing = config.get("pacing", {})
    for model in models:
        row: dict[str, Any] = {
            "label": model["label"],
            "served_model_id": model.get("served_model_id"),
            "model_path": model.get("model_path"),
            "expected_sha256": model.get("_sha256"),
            "server_args": build_server_args(config, model, fallback=args.fallback_args),
            "cells": [],
            "memory_before": memory_snapshot(str(pacing.get("c_free_path", "C:\\"))),
        }
        payload["models"].append(row)
        stdout_path = out_dir / f"{model['label']}_server_stdout.txt"
        stderr_path = out_dir / f"{model['label']}_server_stderr.txt"
        with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout, stderr_path.open("w", encoding="utf-8", newline="\n") as stderr:
            proc = subprocess.Popen(row["server_args"], stdout=stdout, stderr=stderr, text=True)
            row["pid"] = proc.pid
            health = wait_for_server(runtime, proc, int(pacing.get("server_start_timeout_seconds", 240)))
            row["health"] = health
            if not health.get("ok"):
                row["status"] = "load_failed"
                row["error"] = health.get("error", "load failed")
                payload["stopped_early"] = True
                payload["stop_reason"] = "runtime_support_blocker: " + str(row["error"])
            else:
                row["status"] = "loaded"
                for contract in contracts:
                    system, user = build_prompt(contract)
                    options = inference_options(model, contract)
                    response = call_chat_completion(server_url(runtime), str(model["served_model_id"]), system, user, options)
                    score = score_response(contract, response)
                    cell: dict[str, Any] = {
                        "contract_id": contract["id"],
                        "contract_label": contract["label"],
                        "response_format_mode": contract["response_format"],
                        "api_status": response.get("status"),
                        "latency_ms": response.get("latency_ms"),
                        "usage": response.get("usage", {}),
                        "error": response.get("error", ""),
                        "output_channel_status": response.get("output_channel_status", ""),
                        "extraction_channel": response.get("extraction_channel", ""),
                        "content_chars": response.get("content_chars", 0),
                        "reasoning_chars": response.get("reasoning_chars", 0),
                        "message_keys": response.get("message_keys", []),
                        "finish_reason": response.get("finish_reason"),
                    }
                    cell.update(score)
                    row["cells"].append(cell)
                    if cell.get("failure_owner") in {"PHI", "output_channel_policy", "runtime_template_or_reasoning_control"}:
                        payload["stopped_early"] = True
                        payload["stop_reason"] = str(cell.get("failure_owner"))
                        break
                row["status"] = "completed" if not payload["stopped_early"] else "stopped_early"
            proc.terminate()
            try:
                proc.wait(timeout=int(pacing.get("shutdown_timeout_seconds", 30)))
                row["server_exit_code"] = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                row["server_exit_code"] = "killed_after_timeout"
                payload["stopped_early"] = True
                payload["stop_reason"] = "llama-server did not exit"
        row["memory_after"] = memory_snapshot(str(pacing.get("c_free_path", "C:\\")))
        if payload["stopped_early"]:
            time.sleep(float(pacing.get("post_failure_seconds", 180)))
            break
        time.sleep(float(pacing.get("normal_post_model_seconds", 90)))

    payload["final_preflight"] = gemma_preflight(config, models)
    final_ok, final_reason = gemma_preflight_pass(config, payload["final_preflight"])
    if not final_ok:
        payload["stopped_early"] = True
        payload["stop_reason"] = "final_preflight_failed: " + final_reason
    write_json(out_dir / "gemma_llamacpp_output_contract_results.json", payload)
    write_summary(out_dir, payload)
    print(f"wrote {out_dir}")
    return 1 if payload.get("stopped_early") else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--include-31b-reference", action="store_true")
    parser.add_argument("--contracts", nargs="*")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fallback-args", action="store_true")
    parser.add_argument("--confirm-hpz2", action="store_true")
    parser.add_argument("--confirm-gemma-llamacpp-output-contract-pilot", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    models = select_models(args.models, args.include_31b_reference)
    contracts = select_contracts(args.contracts)
    if args.dry_run:
        return dry_run(config, models, contracts)
    return run_real(args, config, models, contracts)


if __name__ == "__main__":
    raise SystemExit(main())
