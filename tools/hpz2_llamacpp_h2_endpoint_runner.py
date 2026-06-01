#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import base64
import datetime as dt
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


HP_SSH = "test@192.168.68.50"
LOCAL_REPO = Path("C:/Github/local-llm-eval")
EMR_REPO = Path("C:/Github/EMR_AI_24clinic")
CONFIG_PATH = LOCAL_REPO / "models_config_hpz2_llamacpp_phase2_l2_v0.1.json"
EVAL_SET_PATH = LOCAL_REPO / "prompts/rag_aware_eval_set_v0.1.json"
DEFAULT_OUTPUT_ROOT = Path("C:/Github/hpz2-run-artifacts/results")
RESULT_DIR = DEFAULT_OUTPUT_ROOT / "h2_endpoint_run_unset"
LOCK_PATH = RESULT_DIR / "run.lock"
REMOTE_LOG_ROOT = "C:\\Users\\test\\AppData\\Local\\Temp\\hpz2-h2-model-comparison"
PRIMARY_MODELS = [
    "hpz2-l2-qwen36-35b-a3b",
    "hpz2-l2-qwen36-35b-a3b-mtp-mxfp4",
    "hpz2-l2-qwen36-35b-a3b-mtp-q8",
    "hpz2-l2-granite-41-30b-q4km",
]
C1_REPLAY_PILOT_MODELS = [
    "hpz2-l2-qwen36-35b-a3b",
    "hpz2-l2-granite-41-30b-q4km",
]
C1_REPLAY_CASE_IDS = [
    "smoke-09-bst",
    "RA-03-safety-boundary",
    "RA-06-dexisy-pediatric-nsaid-insurance",
    "RA-07-umk-uri-syrup-age-insurance",
]
APPROVED_RUNNER_WORKTREE_PATHS = {
    "tools/hpz2_llamacpp_h2_endpoint_runner.py",
    "docs/hpz2-llamacpp-h2-endpoint-runner-2026-06-01.md",
    "docs/h2-output-contract-primary4-expansion-review-2026-06-02.md",
    "docs/h2-c1-endpoint-hypothesis-replay-design-2026-06-02.md",
}


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def local_pid_running(pid: int) -> bool:
    proc = run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], timeout=10)
    return f'"{pid}"' in proc.stdout


def release_lock(lock_fd: int) -> None:
    try:
        os.close(lock_fd)
    except OSError:
        pass
    try:
        if LOCK_PATH.exists() and LOCK_PATH.read_text(encoding="ascii").strip() == str(os.getpid()):
            LOCK_PATH.unlink()
    except OSError:
        pass


def acquire_lock() -> int:
    if LOCK_PATH.exists():
        try:
            existing = int(LOCK_PATH.read_text(encoding="ascii").strip())
        except ValueError:
            existing = 0
        if existing and local_pid_running(existing):
            raise RuntimeError(f"another runner appears active: pid {existing}")
        LOCK_PATH.unlink()
    lock_fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(lock_fd, str(os.getpid()).encode("ascii"))
    atexit.register(release_lock, lock_fd)
    return lock_fd


def ps_quote(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def hp_ps(script: str, *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    script = "$ProgressPreference = 'SilentlyContinue'\n" + script
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return run(["ssh", HP_SSH, "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded], timeout=timeout)


def hp_json(script: str, *, timeout: int = 60) -> Any:
    proc = hp_ps(script, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"remote powershell failed: {proc.stderr.strip() or proc.stdout.strip()}")
    text = proc.stdout.strip()
    if not text:
        return None
    return json.loads(text)


def ps_array(values: list[Any]) -> str:
    return "@(" + ",".join(ps_quote(value) for value in values) + ")"


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._") or "item"


def tail_file(path: Path, max_chars: int = 2000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_output_dir(value: str) -> Path:
    output_root = DEFAULT_OUTPUT_ROOT.resolve()
    resolved = Path(value).resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise RuntimeError(f"--output-dir must be under {output_root}") from exc
    return resolved


def normalize_git_status_path(line: str) -> str:
    raw = line[3:] if len(line) >= 3 else line
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1]
    return raw.strip().replace("\\", "/").strip('"')


def git_state(path: Path) -> dict[str, str]:
    head = run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
    status = run(["git", "status", "--branch", "--short"], cwd=path).stdout.strip()
    return {"head": head, "status": status}


def assert_clean_git(path: Path, name: str, *, approved_dirty_paths: set[str] | None = None) -> dict[str, Any]:
    state = git_state(path)
    dirty = [line for line in state["status"].splitlines() if line and not line.startswith("##")]
    approved_dirty_paths = approved_dirty_paths or set()
    unapproved = [line for line in dirty if normalize_git_status_path(line) not in approved_dirty_paths]
    if unapproved:
        raise RuntimeError(f"{name} dirty: {'; '.join(unapproved[:5])}")
    state["dirty_allowed"] = bool(dirty)
    state["dirty_lines"] = dirty
    state["approved_dirty_paths"] = sorted(approved_dirty_paths) if dirty else []
    return state


def local_harness_dependency_preflight() -> dict[str, Any]:
    required = ["fastapi"]
    missing = [module for module in required if importlib.util.find_spec(module) is None]
    if missing:
        raise RuntimeError(
            "missing local harness Python modules: "
            + ", ".join(missing)
            + "; run with C:\\Github\\EMR_AI_24clinic\\.venv\\Scripts\\python.exe"
        )
    return {"python": sys.executable, "required_modules": required}


def config_model_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(model["label"]): model for model in config["models"]}


def select_model_labels(*, c1_replay: bool, primary4_c1_replay: bool) -> list[str]:
    if not c1_replay:
        return list(PRIMARY_MODELS)
    return list(PRIMARY_MODELS if primary4_c1_replay else C1_REPLAY_PILOT_MODELS)


def select_cases(eval_set: dict[str, Any], *, c1_replay: bool) -> list[dict[str, Any]]:
    cases = list(eval_set["cases"])
    if not c1_replay:
        return cases
    by_id = {str(case.get("id", "")): case for case in cases}
    missing = [case_id for case_id in C1_REPLAY_CASE_IDS if case_id not in by_id]
    if missing:
        raise RuntimeError(f"missing C1 replay cases: {missing}")
    selected = [by_id[case_id] for case_id in C1_REPLAY_CASE_IDS]
    non_model = [str(case.get("id", "")) for case in selected if not bool(case.get("model_call_expected", True))]
    if non_model:
        raise RuntimeError(f"C1 replay cases must call the model: {non_model}")
    return selected


def build_server_args(config: dict[str, Any], model: dict[str, Any]) -> list[str]:
    runtime = config["runtime"]
    args = [
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
    args.extend(str(item) for item in model.get("runtime_overrides", []))
    return args


def preflight_remote(model_paths: list[str]) -> dict[str, Any]:
    paths = "@(" + ",".join(ps_quote(path) for path in model_paths) + ")"
    script = f"""
$ErrorActionPreference = 'Stop'
$ports = @(Get-NetTCPConnection -LocalPort 18080,18081 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess)
$llama = @(Get-Process llama-server -ErrorAction SilentlyContinue | Select-Object Id,ProcessName)
$shim = @(Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*hpz2_ollama_compat_llamacpp_shim.py*' }} | Select-Object ProcessId,CommandLine)
$drive = Get-PSDrive -Name C
$os = Get-CimInstance Win32_OperatingSystem
$files = foreach ($p in {paths}) {{
  $item = Get-Item -LiteralPath $p -ErrorAction SilentlyContinue
  [pscustomobject]@{{ path = $p; exists = [bool]$item; length = if ($item) {{ $item.Length }} else {{ 0 }} }}
}}
[pscustomobject]@{{
  hostname = $env:COMPUTERNAME
  ports = $ports
  llama_processes = $llama
  shim_processes = $shim
  c_free_gib = [math]::Round($drive.Free / 1GB, 2)
  memory_used_pct = [math]::Round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize) * 100, 2)
  memory_free_gib = [math]::Round(($os.FreePhysicalMemory * 1KB) / 1GB, 2)
  files = $files
}} | ConvertTo-Json -Depth 5 -Compress
"""
    return hp_json(script, timeout=30)


def start_hp_foreground(script: str, stdout_path: Path, stderr_path: Path) -> subprocess.Popen[str]:
    encoded = base64.b64encode(("$ProgressPreference = 'SilentlyContinue'\n" + script).encode("utf-16le")).decode("ascii")
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = stdout_path.open("w", encoding="utf-8", newline="\n")
    stderr_handle = stderr_path.open("w", encoding="utf-8", newline="\n")
    try:
        proc = subprocess.Popen(
            ["ssh", HP_SSH, "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
    finally:
        stdout_handle.close()
        stderr_handle.close()
    return proc


def remote_start_llama(config: dict[str, Any], model: dict[str, Any], run_id: str) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    runtime = config["runtime"]
    binary = runtime["binary"]
    label = str(model["label"])
    log_dir = RESULT_DIR / "runtime_logs" / run_id / label
    arg_array = ps_array(build_server_args(config, model))
    script = f"""
$ErrorActionPreference = 'Stop'
Set-Location {ps_quote(str(Path(binary).parent))}
$argsList = {arg_array}
& {ps_quote(binary)} @argsList
exit $LASTEXITCODE
"""
    proc = start_hp_foreground(script, log_dir / "llama.out.log", log_dir / "llama.err.log")
    return proc, {"transport": "ssh_foreground", "log_dir": str(log_dir), "ssh_pid": proc.pid}


def remote_start_shim(model_label: str, run_id: str) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    log_dir = RESULT_DIR / "runtime_logs" / run_id / model_label
    shim_path = "C:\\Github\\local-llm-eval\\tools\\hpz2_ollama_compat_llamacpp_shim.py"
    args = [
        shim_path,
        "--listen-host",
        "127.0.0.1",
        "--listen-port",
        "18081",
        "--upstream",
        "http://127.0.0.1:18080/v1",
        "--default-model",
        model_label,
        "--schema-mode",
        "json-object",
        "--timeout-seconds",
        "300",
        "--max-tokens",
        "8192",
    ]
    arg_array = ps_array(args)
    script = f"""
$ErrorActionPreference = 'Stop'
$argsList = {arg_array}
python @argsList
exit $LASTEXITCODE
"""
    proc = start_hp_foreground(script, log_dir / "shim.out.log", log_dir / "shim.err.log")
    return proc, {"transport": "ssh_foreground", "log_dir": str(log_dir), "ssh_pid": proc.pid}


def hp_health(port: int) -> dict[str, Any]:
    script = f"""
$ErrorActionPreference = 'Continue'
try {{
  $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:{int(port)}/health' -TimeoutSec 5
  [pscustomobject]@{{ ok = $true; status = $r.StatusCode }} | ConvertTo-Json -Compress
}} catch {{
  [pscustomobject]@{{ ok = $false; error = $_.Exception.Message }} | ConvertTo-Json -Compress
}}
"""
    return hp_json(script, timeout=10)


def remote_wait_health(port: int, proc: subprocess.Popen[str], meta: dict[str, Any], *, timeout_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last: dict[str, Any] = {}
    stderr_path = Path(str(meta["log_dir"])) / ("llama.err.log" if port == 18080 else "shim.err.log")
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"remote foreground process exited early with code {proc.returncode}; "
                f"stderr_tail={tail_file(stderr_path)}"
            )
        last = hp_health(port)
        if last.get("ok"):
            return {"ok": True, "status": last.get("status"), "transport_state": "running"}
        time.sleep(3)
    raise RuntimeError(f"health timeout; last={last}; stderr_tail={tail_file(stderr_path)}")


def stop_process(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def remote_stop(pids: list[int]) -> dict[str, Any]:
    pid_array = "@(" + ",".join(str(int(pid)) for pid in pids if pid) + ")"
    script = f"""
$ErrorActionPreference = 'Continue'
foreach ($pidValue in {pid_array}) {{
  Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
}}
Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*hpz2_ollama_compat_llamacpp_shim.py*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}
Start-Sleep -Seconds 2
$ports = @(Get-NetTCPConnection -LocalPort 18080,18081 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalPort,OwningProcess)
$llama = @(Get-Process llama-server -ErrorAction SilentlyContinue | Select-Object Id,ProcessName)
$shim = @(Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*hpz2_ollama_compat_llamacpp_shim.py*' }} | Select-Object ProcessId)
[pscustomobject]@{{ ports = $ports; llama = $llama; shim = $shim }} | ConvertTo-Json -Depth 4 -Compress
"""
    return hp_json(script, timeout=30)


def wait_url(url: str, proc: subprocess.Popen[str], *, timeout_sec: int) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"local tunnel exited early with code {proc.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                body = response.read().decode("utf-8", errors="replace")
            if response.status < 500:
                return {"ok": True, "status": response.status, "body_preview": body[:200]}
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(1)
    raise RuntimeError(f"local health timeout: {last}")


def start_tunnel() -> subprocess.Popen[str]:
    return subprocess.Popen(
        ["ssh", "-L", "18081:127.0.0.1:18081", "-N", HP_SSH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_tunnel(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def schema_meta(text: str) -> dict[str, Any]:
    meta = {
        "valid_json": False,
        "strict_schema": False,
        "citation_format_ok": False,
        "raw_citation_count": 0,
        "extra_top_level_keys": [],
        "_summary_for_scoring": "",
    }
    try:
        parsed = json.loads(str(text).strip())
    except Exception:
        return meta
    meta["valid_json"] = isinstance(parsed, dict)
    if not isinstance(parsed, dict):
        return meta
    keys = set(parsed.keys())
    meta["extra_top_level_keys"] = sorted(keys - {"summary", "citations"})
    if isinstance(parsed.get("summary"), str):
        meta["_summary_for_scoring"] = parsed["summary"]
    citations = parsed.get("citations")
    meta["raw_citation_count"] = len(citations) if isinstance(citations, list) else 0
    meta["strict_schema"] = (
        keys == {"summary", "citations"}
        and isinstance(parsed.get("summary"), str)
        and isinstance(citations, list)
        and all(isinstance(item, str) for item in citations)
    )
    meta["citation_format_ok"] = isinstance(citations, list) and all(
        isinstance(item, str) and re.fullmatch(r"\[[^\[\]]+\]", item.strip()) for item in citations
    )
    return meta


def content_lane_meta(case: dict[str, Any], trace: dict[str, Any], *, llm_called: bool) -> dict[str, Any]:
    if not bool(case.get("model_call_expected", True)):
        return {
            "content_lane_status": "not_applicable_early_return",
            "content_lane_pass": None,
            "content_keywords_expected_count": 0,
            "content_keywords_hit_count": 0,
            "content_keywords_missing": [],
        }
    expected = case.get("expected_summary_keywords")
    if not llm_called:
        return {
            "content_lane_status": "not_scored_no_model_call",
            "content_lane_pass": None,
            "content_keywords_expected_count": 0,
            "content_keywords_hit_count": 0,
            "content_keywords_missing": [],
        }
    if not isinstance(expected, list):
        return {
            "content_lane_status": "not_scored_tbd_expected_keywords",
            "content_lane_pass": None,
            "content_keywords_expected_count": 0,
            "content_keywords_hit_count": 0,
            "content_keywords_missing": [],
        }
    keywords = [str(item).strip() for item in expected if str(item).strip()]
    if not trace.get("valid_json") or not isinstance(trace.get("_summary_for_scoring"), str):
        return {
            "content_lane_status": "not_scored_invalid_json",
            "content_lane_pass": None,
            "content_keywords_expected_count": len(keywords),
            "content_keywords_hit_count": 0,
            "content_keywords_missing": keywords,
        }
    summary_text = str(trace.get("_summary_for_scoring", "")).casefold()
    missing = [keyword for keyword in keywords if keyword.casefold() not in summary_text]
    return {
        "content_lane_status": "pass" if not missing else "missing_keywords",
        "content_lane_pass": not missing,
        "content_keywords_expected_count": len(keywords),
        "content_keywords_hit_count": len(keywords) - len(missing),
        "content_keywords_missing": missing,
    }


def classify_failure(case: dict[str, Any]) -> str:
    if case["phi_hit_count"] > 0:
        return "PHI"
    if case["http_status"] != 200:
        return "infra"
    if case["emr_status"] in {"llm_unavailable", "llm_timeout", "llm_model_not_found", "internal_error"}:
        return "infra"
    if case["model_call_expected"] and not case["llm_called"]:
        return "retrieval"
    if case["llm_called"] and (not case.get("valid_json") or not case.get("strict_schema") or case.get("structural_drift")):
        return "schema"
    if case.get("citation_issues") or case.get("expected_citations_missing"):
        return "citation"
    if case.get("content_lane_pass") is False:
        return "content"
    if case["emr_status"] != case["expected_status"]:
        return "unknown"
    return ""


def write_replay_response_artifacts(
    *,
    model_label: str,
    case_id: str,
    body: dict[str, Any],
    raw_llm_text: str,
    scan_output,
) -> tuple[dict[str, str], bool]:
    paths: dict[str, str] = {}
    response_dir = RESULT_DIR / "responses" / safe_slug(model_label)
    response_dir.mkdir(parents=True, exist_ok=True)
    body_text = json.dumps(body, ensure_ascii=False, indent=2)
    body_phi_hit, _ = scan_output(body_text)
    raw_phi_hit = bool(raw_llm_text and scan_output(raw_llm_text)[0])
    if body_phi_hit or raw_phi_hit:
        return paths, True
    endpoint_path = response_dir / f"{safe_slug(case_id)}__endpoint_response.json"
    endpoint_path.write_text(body_text + "\n", encoding="utf-8", newline="\n")
    paths["endpoint_response_path"] = str(endpoint_path)
    if raw_llm_text:
        raw_path = response_dir / f"{safe_slug(case_id)}__raw_llm_response.txt"
        raw_path.write_text(raw_llm_text, encoding="utf-8", newline="\n")
        paths["raw_llm_response_path"] = str(raw_path)
    return paths, False


def run_harness_for_model(
    model_label: str,
    cases: list[dict[str, Any]],
    eval_set: dict[str, Any],
    *,
    store_replay_responses: bool = False,
) -> list[dict[str, Any]]:
    os.environ.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "EMR_LLM_ENABLED": "true",
            "EMR_LLM_PROVIDER": "ollama",
            "EMR_LLM_MODEL": model_label,
            "EMR_LLM_HOST": "http://127.0.0.1:18081",
            "EMR_LLM_TIMEOUT_SECONDS": "300",
        }
    )
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(LOCAL_REPO))
    sys.path.insert(0, str(LOCAL_REPO / "tools"))
    sys.path.insert(0, str(EMR_REPO))
    os.chdir(EMR_REPO)

    from fastapi.testclient import TestClient
    from hpz2_lmstudio_phase2_stage_a_runner import (
        case_payload,
        expected_citations_missing,
        output_phi_hit,
        returned_citation_issues,
    )
    from app import explain as explain_module
    from app.llm.phi_strip import scan_output

    original_generate = explain_module.generate_llm
    traces: list[dict[str, Any]] = []

    def wrapped_generate(*, prompt: str, system: str = "", settings=None, **kwargs: Any) -> dict[str, Any]:
        result = original_generate(prompt=prompt, system=system, settings=settings, **kwargs)
        raw_text = str(result.get("text", "")) if result.get("status") == "ok" else ""
        meta = schema_meta(raw_text) if result.get("status") == "ok" else schema_meta("")
        meta.update(
            {
                "status": result.get("status"),
                "latency_ms": result.get("latency_ms"),
                "error_message_present": bool(result.get("error_message")),
                "_raw_llm_text_for_storage": raw_text,
            }
        )
        traces.append(meta)
        return result

    explain_module.generate_llm = wrapped_generate
    from app.server import app

    client = TestClient(app)
    default_options = dict(eval_set.get("common_options_default", {}))
    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("id", ""))
        payload = case_payload(case, default_options)
        before = len(traces)
        started = time.perf_counter()
        response = client.post("/explain", json=payload)
        wall_ms = int((time.perf_counter() - started) * 1000)
        try:
            body = response.json()
        except Exception:
            body = {}
        llm_called = len(traces) > before
        trace = traces[-1] if llm_called else {}
        expected = [
            str(source_id)
            for source_id in case.get("expected_citations_includes_at_least", [])
            if str(source_id) and not str(source_id).startswith("{TBD")
        ]
        citation_issues = returned_citation_issues(body) if isinstance(body, dict) else ["<invalid-response>"]
        expected_missing = expected_citations_missing(body, expected) if isinstance(body, dict) else expected
        phi_hit = output_phi_hit(body, scan_output) if isinstance(body, dict) else True
        response_paths: dict[str, str] = {}
        raw_storage_phi_hit = False
        if store_replay_responses and isinstance(body, dict):
            response_paths, raw_storage_phi_hit = write_replay_response_artifacts(
                model_label=model_label,
                case_id=case_id,
                body=body,
                raw_llm_text=str(trace.get("_raw_llm_text_for_storage", "")) if llm_called else "",
                scan_output=scan_output,
            )
            phi_hit = phi_hit or raw_storage_phi_hit
        returned_source_ids = [
            str(citation.get("source_id", "")).strip()
            for citation in body.get("citations", []) or []
            if isinstance(citation, dict)
        ]
        retrieved_source_ids = [
            str(item.get("source_id", "")).strip()
            for item in body.get("retrieved", []) or []
            if isinstance(item, dict)
        ]
        row = {
            "case_id": case_id,
            "http_status": response.status_code,
            "emr_status": str(body.get("status", "")) if isinstance(body, dict) else "",
            "expected_status": str(case.get("expected_status", "ok")),
            "model_call_expected": bool(case.get("model_call_expected", True)),
            "llm_called": llm_called,
            "wall_ms": wall_ms,
            "emr_latency_ms": body.get("latency_ms") if isinstance(body, dict) else None,
            "valid_json": trace.get("valid_json") if llm_called else None,
            "strict_schema": trace.get("strict_schema") if llm_called else None,
            "citation_format_ok": trace.get("citation_format_ok") if llm_called else None,
            "structural_drift": (not trace.get("valid_json") or not trace.get("strict_schema") or not trace.get("citation_format_ok")) if llm_called else False,
            "raw_citation_count": trace.get("raw_citation_count") if llm_called else None,
            "extra_top_level_keys": trace.get("extra_top_level_keys", []) if llm_called else [],
            "retrieved_count": len(body.get("retrieved", []) or []) if isinstance(body, dict) else 0,
            "citation_count": len(body.get("citations", []) or []) if isinstance(body, dict) else 0,
            "returned_source_ids": returned_source_ids,
            "retrieved_source_ids": retrieved_source_ids,
            "citation_issues": citation_issues,
            "expected_citations_missing": expected_missing,
            "phi_hit_count": 1 if phi_hit else 0,
            "response_artifacts": response_paths,
            "replay_raw_storage_phi_blocked": raw_storage_phi_hit,
            "manual_review_needed": store_replay_responses and llm_called,
            "semantic_pass": None if store_replay_responses and llm_called else None,
            "grounding_pass": None if store_replay_responses and llm_called else None,
            "citation_claim_pass": None if store_replay_responses and llm_called else None,
            "safety_pass": None if store_replay_responses and llm_called else None,
        }
        row.update(content_lane_meta(case, trace, llm_called=llm_called))
        row["failure_owner"] = classify_failure(row)
        results.append(row)
        if row["phi_hit_count"] > 0:
            raise RuntimeError(f"PHI hard stop at {case_id}")
        if row["llm_called"] and not row["model_call_expected"]:
            raise RuntimeError(f"unexpected model call at {case_id}")
    return results


def write_outputs(payload: dict[str, Any]) -> tuple[Path, Path]:
    if payload.get("run_mode") == "c1_endpoint_replay":
        json_path = RESULT_DIR / "h2_c1_endpoint_replay_results.json"
        md_path = RESULT_DIR / "h2_c1_endpoint_replay_summary.md"
        title = "H2 C1 Endpoint Replay"
        raw_line = "- raw endpoint responses: stored for selected synthetic replay cells after PHI scan\n\n"
    else:
        json_path = RESULT_DIR / "h2_model_comparison_results.json"
        md_path = RESULT_DIR / "h2_model_comparison_summary.md"
        title = "H2 Model Comparison Endpoint Run"
        raw_line = "- raw model responses: not stored\n\n"
    with json_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with md_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# {title}\n\n")
        handle.write(f"- generated_at: `{payload['generated_at']}`\n")
        handle.write(f"- run_mode: `{payload.get('run_mode')}`\n")
        handle.write(f"- stopped_early: `{payload['stopped_early']}`\n")
        handle.write(f"- stop_reason: `{payload.get('stop_reason') or ''}`\n")
        handle.write(raw_line)
        handle.write("| model | cases | http 200 | ok | valid json | strict schema | structural drift | citation issue | content pass | content missing | content not scored | phi hits | unexpected calls |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for model in payload["models"]:
            cases = model.get("cases", [])
            model_call_cases = [c for c in cases if c.get("model_call_expected")]
            handle.write(
                f"| {model['label']} | {len(cases)} | "
                f"{sum(1 for c in cases if c.get('http_status') == 200)} | "
                f"{sum(1 for c in cases if c.get('emr_status') == 'ok')} | "
                f"{sum(1 for c in model_call_cases if c.get('valid_json') is True)} | "
                f"{sum(1 for c in model_call_cases if c.get('strict_schema') is True)} | "
                f"{sum(1 for c in model_call_cases if c.get('structural_drift'))} | "
                f"{sum(1 for c in cases if c.get('citation_issues') or c.get('expected_citations_missing'))} | "
                f"{sum(1 for c in cases if c.get('content_lane_pass') is True)} | "
                f"{sum(1 for c in cases if c.get('content_lane_pass') is False)} | "
                f"{sum(1 for c in cases if c.get('content_lane_pass') is None)} | "
                f"{sum(int(c.get('phi_hit_count') or 0) for c in cases)} | "
                f"{sum(1 for c in cases if c.get('llm_called') and not c.get('model_call_expected'))} |\n"
            )
        handle.write("\n## Case Metadata\n\n")
        for model in payload["models"]:
            handle.write(f"### {model['label']}\n\n")
            for case in model.get("cases", []):
                handle.write(
                    f"- `{case['case_id']}` http={case['http_status']} status={case['emr_status']} "
                    f"llm_called={case['llm_called']} valid_json={case['valid_json']} "
                    f"strict_schema={case['strict_schema']} drift={case['structural_drift']} "
                    f"retrieved={case['retrieved_count']} citations={case['citation_count']} "
                    f"content={case['content_lane_status']} "
                    f"keyword_hits={case['content_keywords_hit_count']}/{case['content_keywords_expected_count']} "
                    f"phi={case['phi_hit_count']} owner={case['failure_owner'] or '-'}\n"
                )
            handle.write("\n")
    return json_path, md_path


def main() -> int:
    global RESULT_DIR, LOCK_PATH
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-phase2-heavy-run", action="store_true")
    parser.add_argument("--confirm-h2-content-lane-supplement", action="store_true")
    parser.add_argument("--confirm-h2-c1-endpoint-replay", action="store_true")
    parser.add_argument("--primary4-c1-replay", action="store_true")
    parser.add_argument("--allow-approved-runner-worktree", action="store_true")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()
    if not (
        args.confirm_phase2_heavy_run
        or args.confirm_h2_content_lane_supplement
        or args.confirm_h2_c1_endpoint_replay
    ):
        print("Refusing without an explicit H2 execution confirmation flag", file=sys.stderr)
        return 2
    if args.primary4_c1_replay and not args.confirm_h2_c1_endpoint_replay:
        raise RuntimeError("--primary4-c1-replay requires --confirm-h2-c1-endpoint-replay")

    if args.confirm_h2_c1_endpoint_replay and args.confirm_phase2_heavy_run:
        raise RuntimeError("C1 endpoint replay must not be combined with phase2 heavy run")

    if args.confirm_h2_c1_endpoint_replay and args.confirm_h2_content_lane_supplement:
        raise RuntimeError("C1 endpoint replay must not be combined with content-lane supplement")

    if args.output_dir:
        RESULT_DIR = resolve_output_dir(args.output_dir)
    else:
        if args.confirm_h2_c1_endpoint_replay:
            prefix = "h2_c1_endpoint_replay"
        elif args.confirm_h2_content_lane_supplement:
            prefix = "h2_content_lane_supplement"
        else:
            prefix = "h2_model_comparison"
        RESULT_DIR = DEFAULT_OUTPUT_ROOT / f"{prefix}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    RESULT_DIR.mkdir(parents=True, exist_ok=False)
    LOCK_PATH = RESULT_DIR / "run.lock"
    acquire_lock()

    config = load_json(CONFIG_PATH)
    eval_set = load_json(EVAL_SET_PATH)
    models_by_label = config_model_map(config)
    model_labels = select_model_labels(
        c1_replay=args.confirm_h2_c1_endpoint_replay,
        primary4_c1_replay=args.primary4_c1_replay,
    )
    models = [models_by_label[label] for label in model_labels]
    cases = select_cases(eval_set, c1_replay=args.confirm_h2_c1_endpoint_replay)
    approved_dirty_paths = APPROVED_RUNNER_WORKTREE_PATHS if args.allow_approved_runner_worktree else None
    preflight = {
        "main_local_llm_eval": assert_clean_git(
            LOCAL_REPO,
            "Main PC local-llm-eval",
            approved_dirty_paths=approved_dirty_paths,
        ),
        "main_emr": assert_clean_git(EMR_REPO, "Main PC EMR_AI_24clinic"),
        "local_harness": local_harness_dependency_preflight(),
        "hp": preflight_remote([str(model["model_path"]) for model in models]),
    }
    missing = [item["path"] for item in preflight["hp"]["files"] if not item["exists"]]
    if missing:
        raise RuntimeError(f"missing HP model files: {missing}")
    if preflight["hp"]["ports"] or preflight["hp"]["llama_processes"] or preflight["hp"]["shim_processes"]:
        raise RuntimeError("HP stale runtime or port listener detected")
    if float(preflight["hp"]["c_free_gib"]) < 100:
        raise RuntimeError("HP C: free space below 100 GiB")
    if float(preflight["hp"]["memory_used_pct"]) >= 92:
        raise RuntimeError("HP memory load >= 92%")

    payload: dict[str, Any] = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "scope": (
            "H2 C1 endpoint-hypothesis replay"
            if args.confirm_h2_c1_endpoint_replay
            else "H2 Primary 4 x 17 endpoint model comparison"
        ),
        "run_mode": (
            "c1_endpoint_replay"
            if args.confirm_h2_c1_endpoint_replay
            else "content_lane_supplement"
            if args.confirm_h2_content_lane_supplement
            else "phase2_heavy_run"
        ),
        "schema_mode": "json_object",
        "content_lane_method": (
            "manual-review-first C1 replay; keyword hits retained as supporting metadata"
            if args.confirm_h2_c1_endpoint_replay
            else "expected_summary_keywords substring check; raw summaries parsed transiently and not written"
        ),
        "raw_model_responses_stored": bool(args.confirm_h2_c1_endpoint_replay),
        "selected_models": model_labels,
        "selected_cases": [str(case.get("id", "")) for case in cases],
        "preflight": preflight,
        "models": [],
        "stopped_early": False,
        "stop_reason": "",
    }
    if args.dry_run:
        payload["dry_run"] = True
        write_outputs(payload)
        print("dry-run ok")
        return 0

    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    for model in models:
        label = str(model["label"])
        model_row: dict[str, Any] = {"label": label, "cases": [], "remote": {}}
        pids: list[int] = []
        tunnel: subprocess.Popen[str] | None = None
        llama_proc: subprocess.Popen[str] | None = None
        shim_proc: subprocess.Popen[str] | None = None
        try:
            print(f"START {label}", flush=True)
            llama_proc, llama = remote_start_llama(config, model, run_id)
            model_row["remote"]["llama"] = llama
            remote_wait_health(18080, llama_proc, llama, timeout_sec=int(config["pacing"].get("server_start_timeout_seconds", 240)))
            shim_proc, shim = remote_start_shim(label, run_id)
            model_row["remote"]["shim"] = shim
            remote_wait_health(18081, shim_proc, shim, timeout_sec=60)
            tunnel = start_tunnel()
            wait_url("http://127.0.0.1:18081/health", tunnel, timeout_sec=30)
            model_row["cases"] = run_harness_for_model(
                label,
                cases,
                eval_set,
                store_replay_responses=args.confirm_h2_c1_endpoint_replay,
            )
            print(f"DONE {label}", flush=True)
        except Exception as exc:
            payload["stopped_early"] = True
            payload["stop_reason"] = f"{label}: {type(exc).__name__}: {exc}"
            model_row["error"] = payload["stop_reason"]
            safe_reason = payload["stop_reason"].encode("ascii", errors="backslashreplace").decode("ascii")
            print(f"STOP {safe_reason}", flush=True)
        finally:
            stop_tunnel(tunnel)
            stop_process(shim_proc)
            stop_process(llama_proc)
            model_row["teardown"] = remote_stop(list(reversed(pids)))
            payload["models"].append(model_row)
            write_outputs(payload)
        if payload["stopped_early"]:
            break
        time.sleep(90)

    payload["final_hp"] = preflight_remote([str(model["model_path"]) for model in models])
    write_outputs(payload)
    return 1 if payload["stopped_early"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
