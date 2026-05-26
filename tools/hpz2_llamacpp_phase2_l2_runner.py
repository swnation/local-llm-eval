#!/usr/bin/env python3
"""HP Z2 Phase 2 L2 synthetic semantic runner for the llama.cpp primary lane.

Dry-run validates config/spec only. Real model execution is refused unless both
--confirm-hpz2 and --confirm-l2-run are provided.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from hpz2_lmstudio_phase2_l2_semantic_runner import (
    build_prompt,
    call_chat_completion,
    eval_case_map,
    evaluate_semantic_lanes,
    load_json,
    merged_inference_options,
    select_cases,
    select_models,
    write_json,
)


DEFAULT_OUTPUT_ROOT = Path("C:/github/hpz2-run-artifacts/results")
FALLBACK_OUTPUT_ROOT = Path("results")


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


def memory_snapshot(c_free_path: str = "C:\\") -> dict[str, Any]:
    script = rf"""
$os = Get-CimInstance Win32_OperatingSystem
$drive = Get-PSDrive -Name '{Path(c_free_path).drive.rstrip(":") or "C"}'
[pscustomobject]@{{
  memory_load_pct = [int](100 - (($os.FreePhysicalMemory / $os.TotalVisibleMemorySize) * 100))
  total_phys_gib = [math]::Round($os.TotalVisibleMemorySize / 1MB, 3)
  avail_phys_gib = [math]::Round($os.FreePhysicalMemory / 1MB, 3)
  total_page_file_gib = [math]::Round($os.TotalVirtualMemorySize / 1MB, 3)
  avail_page_file_gib = [math]::Round($os.FreeVirtualMemory / 1MB, 3)
  c_free_gib = [math]::Round($drive.Free / 1GB, 3)
}} | ConvertTo-Json -Compress
"""
    result = powershell(script)
    try:
        parsed = json.loads(result["stdout"])
        parsed["ok"] = True
        return parsed
    except Exception:
        return {"ok": False, "error": result}


def no_llama_server_process() -> dict[str, Any]:
    script = """
$p = Get-Process llama-server -ErrorAction SilentlyContinue
if ($p) { $p | Select-Object Id,ProcessName,StartTime | ConvertTo-Json -Compress } else { '[]' }
"""
    result = powershell(script)
    try:
        parsed = json.loads(result["stdout"] or "[]")
        if isinstance(parsed, dict):
            parsed = [parsed]
        return {"ok": len(parsed) == 0, "processes": parsed}
    except Exception:
        return {"ok": False, "error": result}


def lms_status() -> dict[str, Any]:
    return run_cmd(["lms", "status"], timeout=30)


def lms_no_models_loaded(status: dict[str, Any]) -> bool:
    return status.get("returncode") == 0 and "No Models Loaded" in str(status.get("stdout", ""))


def server_url(runtime: dict[str, Any]) -> str:
    return str(runtime.get("server_url_default") or f"http://{runtime.get('host', '127.0.0.1')}:{runtime.get('port', 18080)}/v1")


def health_url(runtime: dict[str, Any]) -> str:
    return server_url(runtime).removesuffix("/v1") + "/health"


def wait_for_server(runtime: dict[str, Any], proc: subprocess.Popen[str], timeout_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_error = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            return {"ok": False, "error": f"llama-server exited early with code {proc.returncode}"}
        try:
            with urllib.request.urlopen(health_url(runtime), timeout=5) as response:
                body = response.read().decode("utf-8", errors="replace")
            if response.status < 500:
                return {"ok": True, "status": response.status, "body": body[:300]}
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code < 500:
                return {"ok": True, "status": exc.code, "body": ""}
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(int(runtime.get("health_poll_seconds", 3) or 3))
    return {"ok": False, "error": last_error or "health timeout"}


def dedupe_args(args: list[str]) -> list[str]:
    result: list[str] = []
    replace_value_flags = {"-b", "-ub"}
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item in replace_value_flags and idx + 1 < len(args):
            existing_idx = next((i for i, value in enumerate(result) if value == item), None)
            if existing_idx is not None:
                del result[existing_idx:existing_idx + 2]
            result.extend([item, args[idx + 1]])
            idx += 2
        else:
            result.append(item)
            idx += 1
    return result


def build_server_args(config: dict[str, Any], model: dict[str, Any], fallback: bool = False) -> list[str]:
    runtime = dict(config.get("runtime", {}))
    binary = str(runtime.get("binary", "llama-server.exe"))
    args = [
        binary,
        "-m",
        str(model["model_path"]),
        "-a",
        str(model.get("served_model_id") or model["label"]),
        "--host",
        str(runtime.get("host", "127.0.0.1")),
        "--port",
        str(runtime.get("port", 18080)),
        "-c",
        str(runtime.get("context_length", 16384)),
        "-n",
        str(runtime.get("predict_cap", 8192)),
    ]
    args.extend(str(item) for item in runtime.get("default_args", []))
    if fallback:
        args.extend(str(item) for item in runtime.get("fallback_args", []))
    args.extend(str(item) for item in model.get("runtime_overrides", []))
    return dedupe_args(args)


def validate_config(config: dict[str, Any], eval_set: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if config.get("backend") != "llama.cpp":
        errors.append("backend must be llama.cpp")
    runtime = config.get("runtime", {})
    for key in ("binary", "host", "port", "context_length", "predict_cap"):
        if key not in runtime:
            errors.append(f"runtime.{key} missing")
    required_flags = ["--no-mmap", "--no-host", "--kv-offload", "--op-offload", "-fa", "-ctk", "-ctv", "--reasoning"]
    default_args = [str(item) for item in runtime.get("default_args", [])]
    for flag in required_flags:
        if flag not in default_args:
            errors.append(f"runtime.default_args missing {flag}")
    pacing = config.get("pacing", {})
    if float(pacing.get("c_free_floor_gib", 0)) < 100:
        errors.append("pacing.c_free_floor_gib must be >= 100")
    if float(pacing.get("memory_load_abort_percent", 100)) > 92:
        errors.append("pacing.memory_load_abort_percent must be <= 92")
    ra03 = config.get("ra_locks", {}).get("RA-03", {})
    if ra03 != {"patient_context": "sme + trimesy + lacto2", "dx": "a090", "age": 1}:
        errors.append("RA-03 lock drifted from sme+trimesy+lacto2 / a090 / age=1")
    labels = [str(model.get("label", "")) for model in config.get("models", [])]
    if len(labels) != len(set(labels)):
        errors.append("duplicate model labels")
    for model in models:
        for key in ("label", "model_path", "served_model_id"):
            if not model.get(key):
                errors.append(f"model missing {key}: {model}")
    label_set = set(labels)
    for tier_name, tier_labels in config.get("_model_tiers", {}).items():
        for label in tier_labels:
            if label not in label_set:
                errors.append(f"_model_tiers.{tier_name} references unknown label: {label}")
    for label in pacing.get("large_model_labels", []):
        if label not in label_set:
            errors.append(f"pacing.large_model_labels references unknown label: {label}")
    cases_by_id = eval_case_map(eval_set)
    for case in cases:
        if case.get("eval_case_id") not in cases_by_id:
            errors.append(f"l2 case references unknown eval_case_id: {case.get('eval_case_id')}")
    return errors


def dry_run(config: dict[str, Any], eval_set: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]]) -> int:
    errors = validate_config(config, eval_set, models, cases)
    if errors:
        print("Config validation failed:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("HP Z2 Phase 2 L2 llama.cpp dry-run")
    print(f"backend: {config.get('backend')}")
    print(f"models: {len(models)}")
    for model in models:
        extra = " +skip-chat-parsing" if "--skip-chat-parsing" in model.get("runtime_overrides", []) else ""
        print(f"  - {model['label']} -> {model['model_path']}{extra}")
    print(f"cases: {len(cases)}")
    for case in cases:
        print(f"  - {case['case_id']} ({case['eval_case_id']})")
    pacing = config.get("pacing", {})
    print(f"normal_post_model_seconds: {pacing.get('normal_post_model_seconds')}")
    print(f"large_model_post_seconds: {pacing.get('large_model_post_seconds')}")
    print(f"memory_load_abort_percent: {pacing.get('memory_load_abort_percent')}")
    print(f"c_free_floor_gib: {pacing.get('c_free_floor_gib')}")
    print("dry-run only; no llama-server process, model load, LM Studio API call, /explain call, or EMR write was executed.")
    return 0


def output_root(value: str | None) -> Path:
    if value:
        return Path(value)
    if DEFAULT_OUTPUT_ROOT.exists():
        return DEFAULT_OUTPUT_ROOT
    return FALLBACK_OUTPUT_ROOT


def write_outputs(payload: dict[str, Any], root: Path, timestamp: str) -> tuple[Path, Path]:
    out_dir = root / f"llamacpp_phase2_l2_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "full_matrix_results.json"
    md_path = out_dir / "full_matrix_summary.md"
    write_json(json_path, payload)
    with md_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# HP Z2 llama.cpp Phase 2 L2 Semantic Smoke\n\n")
        handle.write(f"- generated_at: {payload['generated_at']}\n")
        handle.write(f"- stopped_early: `{payload.get('stopped_early')}`\n")
        handle.write(f"- stop_reason: `{payload.get('stop_reason')}`\n")
        handle.write(f"- backend: `{payload.get('backend')}`\n")
        handle.write(f"- config: `{payload.get('config')}`\n")
        handle.write(f"- eval_set: `{payload.get('eval_set')}`\n")
        handle.write("- endpoint: not used; L2 synthetic only\n\n")
        handle.write("| model | case | status | semantic | normalizer | native | core cite | strong cite | failure |\n")
        handle.write("|---|---|---|---:|---:|---:|---:|---:|---|\n")
        for row in payload.get("results", []):
            if not row.get("cases"):
                handle.write(f"| {row.get('model_label')} | - | {row.get('status')} | - | - | - | - | - | {row.get('error', '')} |\n")
                continue
            for case in row.get("cases", []):
                lanes = case.get("lanes", {})
                semantic = lanes.get("semantic_rag_lane", {})
                normalizer = lanes.get("normalizer_lane", {})
                native = lanes.get("native_contract_lane", {})
                citation = case.get("citation_score", {})
                handle.write(
                    f"| {row.get('model_label')} | {case.get('case_id')} | {case.get('api_status')} | "
                    f"{semantic.get('semantic_pass')} | {normalizer.get('normalizer_pass')} | "
                    f"{native.get('native_contract_pass')} | {citation.get('core_citation_pass')} | "
                    f"{citation.get('strong_citation_pass')} | {semantic.get('failure_owner') or row.get('error') or ''} |\n"
                )
    return json_path, md_path


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    pacing = config.get("pacing", {})
    mem = memory_snapshot(str(pacing.get("c_free_path", "C:\\")))
    status = lms_status()
    llama_proc = no_llama_server_process()
    return {
        "hostname": socket.gethostname(),
        "memory": mem,
        "lmstudio_status": status,
        "lmstudio_no_models_loaded": lms_no_models_loaded(status),
        "llama_server_process": llama_proc,
    }


def preflight_pass(config: dict[str, Any], report: dict[str, Any]) -> tuple[bool, str]:
    pacing = config.get("pacing", {})
    mem = report.get("memory", {})
    allowed_hosts = {str(host).upper() for host in config.get("_execution_hostnames", [])}
    current_host = str(report.get("hostname", "")).upper()
    if allowed_hosts and current_host not in allowed_hosts:
        return False, f"hostname {report.get('hostname')} is not an approved HP Z2 execution host"
    if not report.get("llama_server_process", {}).get("ok"):
        return False, "stale llama-server process exists"
    if not report.get("lmstudio_no_models_loaded"):
        return False, "LM Studio is not No Models Loaded"
    if mem.get("ok") is False:
        return False, "memory snapshot failed"
    if float(mem.get("c_free_gib", 0)) < float(pacing.get("c_free_floor_gib", 100)):
        return False, "C: free space below floor"
    if float(mem.get("memory_load_pct", 0)) >= float(pacing.get("memory_load_abort_percent", 92)):
        return False, "memory load above abort threshold"
    if float(mem.get("avail_phys_gib", 99)) < float(pacing.get("free_physical_stop_gib", 3.0)):
        return False, "free physical memory below stop threshold"
    return True, ""


def run_real(args: argparse.Namespace, config: dict[str, Any], eval_set: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]]) -> int:
    errors = validate_config(config, eval_set, models, cases)
    if errors:
        for error in errors:
            print(error)
        return 2
    if not (args.confirm_hpz2 and args.confirm_l2_run):
        print("Refusing real L2 execution without --confirm-hpz2 and --confirm-l2-run.", flush=True)
        return 2

    runtime = config.get("runtime", {})
    pacing = config.get("pacing", {})
    timestamp = now_stamp()
    payload: dict[str, Any] = {
        "generated_at": iso_now(),
        "backend": "llama.cpp",
        "config": args.config,
        "eval_set": args.eval_set,
        "runtime": runtime,
        "pacing": pacing,
        "stopped_early": False,
        "stop_reason": None,
        "preflight": preflight(config),
        "results": [],
    }
    ok, reason = preflight_pass(config, payload["preflight"])
    if not ok:
        payload["stopped_early"] = True
        payload["stop_reason"] = reason
        json_path, md_path = write_outputs(payload, output_root(args.output_root), timestamp)
        print(f"STOP: {reason}")
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
        return 1

    cases_by_id = eval_case_map(eval_set)
    for model in models:
        row: dict[str, Any] = {
            "model_label": model["label"],
            "served_model_id": model.get("served_model_id"),
            "model_path": model.get("model_path"),
            "status": "not_started",
            "cases": [],
            "memory_before": memory_snapshot(str(pacing.get("c_free_path", "C:\\"))),
        }
        payload["results"].append(row)
        mem = row["memory_before"]
        if float(mem.get("memory_load_pct", 0)) >= float(pacing.get("memory_load_abort_percent", 92)):
            row["status"] = "blocked"
            row["error"] = "memory abort threshold before model"
            payload["stopped_early"] = True
            payload["stop_reason"] = row["error"]
            break

        out_root = output_root(args.output_root) / f"llamacpp_phase2_l2_{timestamp}"
        out_root.mkdir(parents=True, exist_ok=True)
        stdout_path = out_root / f"{model['label']}_server_stdout.txt"
        stderr_path = out_root / f"{model['label']}_server_stderr.txt"
        cmd = build_server_args(config, model, fallback=args.fallback_args)
        row["server_args"] = cmd
        with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout, stderr_path.open("w", encoding="utf-8", newline="\n") as stderr:
            proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, text=True)
            row["pid"] = proc.pid
            health = wait_for_server(runtime, proc, int(pacing.get("server_start_timeout_seconds", 240)))
            row["health"] = health
            if not health.get("ok"):
                row["status"] = "load_failed"
                row["error"] = health.get("error", "load failed")
                payload["stopped_early"] = True
                payload["stop_reason"] = row["error"]
            else:
                row["status"] = "loaded"
                for case in cases:
                    eval_case = cases_by_id[str(case["eval_case_id"])]
                    system, user = build_prompt(config, case, eval_case)
                    options = merged_inference_options(config, model)
                    response = call_chat_completion(server_url(runtime), str(model.get("served_model_id")), system, user, options)
                    normalized = response.get("text", "")
                    lanes = evaluate_semantic_lanes(
                        text=normalized,
                        l2_case=case,
                        eval_case=eval_case,
                        eval_set=eval_set,
                    )
                    row["cases"].append(
                        {
                            "case_id": case["case_id"],
                            "eval_case_id": case["eval_case_id"],
                            "api_status": response.get("status"),
                            "latency_ms": response.get("latency_ms"),
                            "usage": response.get("usage", {}),
                            "error": response.get("error"),
                            "lanes": lanes["lanes"],
                            "citation_score": lanes["citation_score"],
                            "r2_metric_hooks": lanes["r2_metric_hooks"],
                            "normalized_output": lanes["normalized_output"],
                        }
                    )
                    if response.get("status") != "ok":
                        row["status"] = "api_failed"
                        row["error"] = response.get("error", "API failure")
                        payload["stopped_early"] = True
                        payload["stop_reason"] = row["error"]
                        break
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
        if payload.get("stopped_early"):
            cooldown = float(pacing.get("post_failure_seconds", 180))
            row["cooldown_seconds"] = cooldown
            time.sleep(cooldown)
            break
        cooldown = float(pacing.get("large_model_post_seconds" if model["label"] in pacing.get("large_model_labels", []) else "normal_post_model_seconds", 90))
        row["cooldown_seconds"] = cooldown
        time.sleep(cooldown)

    payload["final_preflight"] = preflight(config)
    json_path, md_path = write_outputs(payload, output_root(args.output_root), timestamp)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 1 if payload.get("stopped_early") else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="models_config_hpz2_llamacpp_phase2_l2_v0.1.json")
    parser.add_argument("--eval-set", default="prompts/rag_aware_eval_set_v0.1.json")
    parser.add_argument("--tier", default=None)
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fallback-args", action="store_true")
    parser.add_argument("--confirm-hpz2", action="store_true")
    parser.add_argument("--confirm-l2-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    eval_set = load_json(args.eval_set)
    models = select_models(config, args.models, args.tier)
    cases = select_cases(config, args.cases)
    if args.dry_run:
        return dry_run(config, eval_set, models, cases)
    return run_real(args, config, eval_set, models, cases)


if __name__ == "__main__":
    raise SystemExit(main())
