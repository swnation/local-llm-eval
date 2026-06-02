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

PHI_PATTERN_NAMES = [
    "resident_registration_like",
    "mobile_phone_like",
    "landline_phone_like",
    "chart_number_like",
    "korean_name_label_like",
]


class HarnessHardStop(RuntimeError):
    def __init__(self, message: str, partial_results: list[dict[str, Any]]) -> None:
        super().__init__(message)
        self.partial_results = partial_results


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
        "raw_citation_source_ids": [],
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
    if isinstance(citations, list):
        meta["raw_citation_source_ids"] = [
            strip_source_wrappers(item)
            for item in citations
            if strip_source_wrappers(item)
        ]
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


def strip_source_wrappers(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1].strip()
    return text


def clean_source_ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        source_id = strip_source_wrappers(value)
        if source_id and not source_id.startswith("{TBD") and source_id not in cleaned:
            cleaned.append(source_id)
    return cleaned


def rubric_text_items(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            items.append(text)
    return items


def concept_rubric_items(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    items: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        if isinstance(value, str):
            concept_id = value.strip()
            any_of = [concept_id] if concept_id else []
        elif isinstance(value, dict):
            concept_id = str(value.get("id") or f"concept_{index + 1}").strip()
            any_of = rubric_text_items(value.get("any_of"))
        else:
            continue
        if concept_id and any_of:
            items.append({"id": concept_id, "any_of": any_of})
    return items


def invalid_rubric_items(rubric: dict[str, Any]) -> list[str]:
    invalid: list[str] = []
    if "literal_required" in rubric and not isinstance(rubric.get("literal_required"), list):
        invalid.append("literal_required")
    if "concept_required" not in rubric:
        return invalid
    values = rubric.get("concept_required")
    if not isinstance(values, list):
        invalid.append("concept_required")
        return invalid
    for index, value in enumerate(values):
        if isinstance(value, str):
            if not value.strip():
                invalid.append(f"concept_required[{index}]")
        elif isinstance(value, dict):
            if not rubric_text_items(value.get("any_of")):
                concept_id = str(value.get("id") or f"concept_required[{index}]").strip()
                invalid.append(concept_id or f"concept_required[{index}]")
        else:
            invalid.append(f"concept_required[{index}]")
    return invalid


def text_contains_any(summary_text: str, candidates: list[str]) -> bool:
    folded = summary_text.casefold()
    return any(candidate.casefold() in folded for candidate in candidates)


def content_meta_defaults(
    *,
    status: str,
    content_pass: bool | None,
    expected_count: int = 0,
    hit_count: int = 0,
    missing: list[str] | None = None,
) -> dict[str, Any]:
    missing = list(missing or [])
    return {
        "content_lane_status": status,
        "content_lane_pass": content_pass,
        "content_keywords_expected_count": expected_count,
        "content_keywords_hit_count": hit_count,
        "content_keywords_missing": missing,
        "content_rubric_mode": "legacy_keywords",
        "content_literal_expected_count": 0,
        "content_literal_hit_count": 0,
        "content_literal_missing": [],
        "content_literal_pass": None,
        "content_concept_expected_count": 0,
        "content_concept_hit_count": 0,
        "content_concept_missing": [],
        "content_concept_pass": None,
        "content_rubric_invalid_items": [],
    }


def content_lane_meta(case: dict[str, Any], trace: dict[str, Any], *, llm_called: bool) -> dict[str, Any]:
    if not bool(case.get("model_call_expected", True)):
        return content_meta_defaults(status="not_applicable_early_return", content_pass=None)
    expected = case.get("expected_summary_keywords")
    rubric = case.get("expected_summary_rubric")
    has_rubric = isinstance(rubric, dict)
    if not llm_called:
        return content_meta_defaults(status="not_scored_no_model_call", content_pass=None)
    keywords = [str(item).strip() for item in expected if str(item).strip()] if isinstance(expected, list) else []
    if not isinstance(expected, list) and not has_rubric:
        return content_meta_defaults(status="not_scored_tbd_expected_keywords", content_pass=None)
    if not trace.get("valid_json") or not isinstance(trace.get("_summary_for_scoring"), str):
        return content_meta_defaults(
            status="not_scored_invalid_json",
            content_pass=None,
            expected_count=len(keywords),
            missing=keywords,
        )
    summary_text = str(trace.get("_summary_for_scoring", "")).casefold()
    missing = [keyword for keyword in keywords if keyword.casefold() not in summary_text]
    meta = {
        "content_lane_status": "pass" if not missing else "missing_keywords",
        "content_lane_pass": not missing,
        "content_keywords_expected_count": len(keywords),
        "content_keywords_hit_count": len(keywords) - len(missing),
        "content_keywords_missing": missing,
    }
    meta.update(
        {
            "content_rubric_mode": "legacy_keywords",
            "content_literal_expected_count": 0,
            "content_literal_hit_count": 0,
            "content_literal_missing": [],
            "content_literal_pass": None,
            "content_concept_expected_count": 0,
            "content_concept_hit_count": 0,
            "content_concept_missing": [],
            "content_concept_pass": None,
            "content_rubric_invalid_items": [],
        }
    )
    if not has_rubric:
        return meta

    literal_items = rubric_text_items(rubric.get("literal_required"))
    concept_items = concept_rubric_items(rubric.get("concept_required"))
    invalid_items = invalid_rubric_items(rubric)
    if invalid_items:
        meta.update(
            {
                "content_rubric_mode": "keyword_to_concept",
                "content_lane_status": "not_scored_invalid_rubric",
                "content_lane_pass": None,
                "content_rubric_invalid_items": invalid_items,
            }
        )
        return meta
    if not literal_items and not concept_items:
        meta.update(
            {
                "content_rubric_mode": "keyword_to_concept",
                "content_lane_status": "not_scored_empty_rubric",
                "content_lane_pass": None,
            }
        )
        return meta
    literal_missing = [item for item in literal_items if item.casefold() not in summary_text]
    concept_missing = [
        item["id"]
        for item in concept_items
        if not text_contains_any(summary_text, item["any_of"])
    ]
    literal_pass = not literal_missing if literal_items else None
    concept_pass = not concept_missing if concept_items else None
    rubric_pass = (literal_pass is not False) and (concept_pass is not False)
    meta.update(
        {
            "content_rubric_mode": "keyword_to_concept",
            "content_lane_status": "pass" if rubric_pass else "missing_rubric_items",
            "content_lane_pass": rubric_pass,
            "content_literal_expected_count": len(literal_items),
            "content_literal_hit_count": len(literal_items) - len(literal_missing),
            "content_literal_missing": literal_missing,
            "content_literal_pass": literal_pass,
            "content_concept_expected_count": len(concept_items),
            "content_concept_hit_count": len(concept_items) - len(concept_missing),
            "content_concept_missing": concept_missing,
            "content_concept_pass": concept_pass,
        }
    )
    return meta


def citation_policy_for_case(case: dict[str, Any], expected_source_ids: list[str]) -> dict[str, Any]:
    policy = dict(case.get("acceptable_citation_set") or {})
    if not policy:
        policy["required_all"] = list(expected_source_ids)
    for key in ("required_all", "core_any_of", "strong_all", "optional_hits", "invalid_aliases"):
        policy[key] = clean_source_ids(policy.get(key))
    return policy


def citation_policy_meta(policy: dict[str, Any], returned_source_ids: list[str]) -> dict[str, Any]:
    returned = set(returned_source_ids)
    required_all = clean_source_ids(policy.get("required_all"))
    core_any_of = clean_source_ids(policy.get("core_any_of"))
    strong_all = clean_source_ids(policy.get("strong_all"))
    optional_hits = [source_id for source_id in clean_source_ids(policy.get("optional_hits")) if source_id in returned]
    invalid_alias_hits = [source_id for source_id in clean_source_ids(policy.get("invalid_aliases")) if source_id in returned]
    required_all_missing = [source_id for source_id in required_all if source_id not in returned]
    core_any_of_hits = [source_id for source_id in core_any_of if source_id in returned]
    core_any_of_missing = list(core_any_of) if core_any_of and not core_any_of_hits else []
    strong_all_missing = [source_id for source_id in strong_all if source_id not in returned]
    required_pass = not required_all_missing if required_all else None
    core_pass = bool(core_any_of_hits) if core_any_of else required_pass
    strong_pass = not strong_all_missing if strong_all else required_pass
    has_positive_gate = bool(required_all or core_any_of)
    if invalid_alias_hits:
        policy_pass = False
    elif has_positive_gate:
        policy_pass = not required_all_missing and not core_any_of_missing
    else:
        policy_pass = None
    return {
        "required_all": required_all,
        "required_all_missing": required_all_missing,
        "required_all_pass": required_pass,
        "core_any_of": core_any_of,
        "core_any_of_hits": core_any_of_hits,
        "core_any_of_missing": core_any_of_missing,
        "core_any_of_pass": core_pass,
        "strong_all": strong_all,
        "strong_all_missing": strong_all_missing,
        "strong_all_pass": strong_pass,
        "optional_hits": optional_hits,
        "invalid_alias_hits": invalid_alias_hits,
        "policy_pass": policy_pass,
    }


def citation_reachability_meta(
    case: dict[str, Any],
    *,
    expected_source_ids: list[str],
    retrieved_source_ids: list[str],
    returned_source_ids: list[str],
) -> dict[str, Any]:
    expected = clean_source_ids(expected_source_ids)
    retrieved = set(retrieved_source_ids)
    returned = set(returned_source_ids)
    expected_retrieved = [source_id for source_id in expected if source_id in retrieved]
    expected_not_retrieved = [source_id for source_id in expected if source_id not in retrieved]
    expected_retrieved_not_cited = [
        source_id for source_id in expected_retrieved if source_id not in returned
    ]
    expected_satisfied = [source_id for source_id in expected if source_id in returned]
    policy = citation_policy_for_case(case, expected)
    policy_result = citation_policy_meta(policy, returned_source_ids)
    required_all = clean_source_ids(policy_result.get("required_all"))
    core_any_of = clean_source_ids(policy_result.get("core_any_of"))
    invalid_aliases = clean_source_ids(policy.get("invalid_aliases"))
    policy_required_not_retrieved = [source_id for source_id in required_all if source_id not in retrieved]
    policy_required_retrieved_not_cited = [
        source_id for source_id in required_all if source_id in retrieved and source_id not in returned
    ]
    policy_core_retrieved = [source_id for source_id in core_any_of if source_id in retrieved]
    policy_core_returned = [source_id for source_id in core_any_of if source_id in returned]
    policy_core_not_retrieved = list(core_any_of) if core_any_of and not policy_core_retrieved else []
    policy_core_retrieved_not_cited = (
        list(policy_core_retrieved) if core_any_of and policy_core_retrieved and not policy_core_returned else []
    )
    policy_has_positive_gate = bool(required_all or core_any_of)
    policy_reachability_pass = (
        not policy_required_not_retrieved and not policy_core_not_retrieved
        if policy_has_positive_gate
        else None
    )
    if policy_result.get("invalid_alias_hits"):
        policy_selection_pass = False
    elif policy_has_positive_gate:
        policy_selection_pass = not policy_required_retrieved_not_cited and not policy_core_retrieved_not_cited
    else:
        policy_selection_pass = None
    return {
        "expected_source_ids": expected,
        "expected_source_retrieved": expected_retrieved,
        "expected_source_not_retrieved": expected_not_retrieved,
        "expected_retrieved_not_cited": expected_retrieved_not_cited,
        "expected_source_satisfied": expected_satisfied,
        "expected_source_reachability_pass": not expected_not_retrieved,
        "citation_selection_pass": not expected_retrieved_not_cited,
        "citation_policy_reachability_pass": policy_reachability_pass,
        "citation_policy_selection_pass": policy_selection_pass,
        "citation_policy_required_not_retrieved": policy_required_not_retrieved,
        "citation_policy_required_retrieved_not_cited": policy_required_retrieved_not_cited,
        "citation_policy_core_not_retrieved": policy_core_not_retrieved,
        "citation_policy_core_retrieved_not_cited": policy_core_retrieved_not_cited,
        "citation_policy": policy_result,
    }


def source_id_near_misses(raw_source_ids: list[str], retrieved_source_ids: list[str]) -> list[dict[str, str]]:
    retrieved = set(retrieved_source_ids)
    near_misses: list[dict[str, str]] = []
    for raw_source_id in raw_source_ids:
        if raw_source_id in retrieved:
            continue
        underscore_as_colon = raw_source_id.replace("_", ":")
        if underscore_as_colon in retrieved:
            near_misses.append(
                {
                    "raw": raw_source_id,
                    "canonical": underscore_as_colon,
                    "kind": "underscore_to_colon",
                }
            )
    return near_misses


def source_id_fidelity_meta(
    raw_source_ids: list[str],
    retrieved_source_ids: list[str],
    *,
    threshold: float = 0.30,
) -> dict[str, Any]:
    retrieved = set(retrieved_source_ids)
    exact = [source_id for source_id in raw_source_ids if source_id in retrieved]
    dropped = [source_id for source_id in raw_source_ids if source_id not in retrieved]
    drop_rate = len(dropped) / max(len(raw_source_ids), 1)
    if not raw_source_ids:
        status = "not_scored"
    elif not dropped:
        status = "pass"
    elif drop_rate > threshold:
        status = "fail"
    else:
        status = "warning"
    return {
        "raw_citation_source_ids": raw_source_ids,
        "exact_match_source_ids": exact,
        "dropped_not_in_retrieved": dropped,
        "near_miss_mutations": source_id_near_misses(raw_source_ids, retrieved_source_ids),
        "fidelity_drop_rate": drop_rate,
        "fidelity_threshold": threshold,
        "source_id_fidelity_lane_status": status,
        "source_id_fidelity_exact_pass": not dropped if raw_source_ids else None,
        "source_id_fidelity_threshold_pass": drop_rate <= threshold if raw_source_ids else None,
    }


def classify_failure_lanes(case: dict[str, Any]) -> list[str]:
    lanes: list[str] = []
    if case["phi_hit_count"] > 0:
        lanes.append("PHI")
    if case["http_status"] != 200:
        lanes.append("infra_http")
    if case["emr_status"] in {"llm_unavailable", "llm_timeout", "llm_model_not_found", "internal_error"}:
        lanes.append("infra_llm")
    if case["model_call_expected"] and not case["llm_called"]:
        lanes.append("retrieval_no_model_call")
    if case["llm_called"] and (not case.get("valid_json") or not case.get("strict_schema") or case.get("structural_drift")):
        lanes.append("schema")
    if case.get("source_id_fidelity", {}).get("source_id_fidelity_lane_status") == "fail":
        lanes.append("source_id_fidelity")
    policy_reachability_pass = case.get("citation_policy_reachability_pass")
    policy_selection_pass = case.get("citation_policy_selection_pass")
    if policy_reachability_pass is False:
        lanes.append("retrieval_reachability")
    elif policy_reachability_pass is None and case.get("expected_source_not_retrieved"):
        lanes.append("retrieval_reachability")
    if policy_selection_pass is False:
        lanes.append("citation_selection")
    elif policy_selection_pass is None and case.get("expected_retrieved_not_cited"):
        lanes.append("citation_selection")
    if case.get("citation_issues"):
        lanes.append("citation_returned_invalid")
    if case.get("content_lane_pass") is False:
        lanes.append("content")
    if case["emr_status"] != case["expected_status"]:
        lanes.append("status_mismatch")
    return lanes


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
    lanes = case.get("failure_lanes") or classify_failure_lanes(case)
    if "retrieval_reachability" in lanes:
        return "retrieval"
    if any(owner in lanes for owner in ("source_id_fidelity", "citation_selection", "citation_returned_invalid")):
        return "citation"
    policy_pass = case.get("citation_policy", {}).get("policy_pass")
    if policy_pass is False:
        return "citation"
    if case.get("expected_citations_missing") and policy_pass is not True:
        return "citation"
    if case.get("content_lane_pass") is False:
        return "content"
    if case["emr_status"] != case["expected_status"]:
        return "unknown"
    return ""


def has_citation_issue(case: dict[str, Any]) -> bool:
    policy_pass = case.get("citation_policy", {}).get("policy_pass")
    if case.get("citation_issues"):
        return True
    if policy_pass is False:
        return True
    if case.get("expected_citations_missing") and policy_pass is not True:
        return True
    return False


def phi_pattern_hits(text: str, phi_patterns: list[Any]) -> list[str]:
    hits: list[str] = []
    for index, pattern in enumerate(phi_patterns):
        try:
            matched = bool(pattern.search(text))
        except Exception:
            matched = False
        if matched:
            hits.append(PHI_PATTERN_NAMES[index] if index < len(PHI_PATTERN_NAMES) else f"pattern_{index}")
    return hits


def phi_field_scan(value: Any, scan_output, phi_patterns: list[Any]) -> dict[str, Any]:
    text = str(value or "")
    hit, _ = scan_output(text)
    return {
        "hit": bool(hit),
        "length": len(text),
        "pattern_hits": phi_pattern_hits(text, phi_patterns),
    }


def replay_phi_diagnostics(
    *,
    body: dict[str, Any],
    raw_llm_text: str,
    scan_output,
    phi_patterns: list[Any],
) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []

    def add(field: str, value: Any) -> None:
        item = {"field": field}
        item.update(phi_field_scan(value, scan_output, phi_patterns))
        fields.append(item)

    def add_body_scalars(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                add_body_scalars(item, f"{path}.{safe_slug(str(key))}")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                add_body_scalars(item, f"{path}[{index}]")
            return
        if value is None or isinstance(value, bool):
            return
        if isinstance(value, (str, int, float)):
            add(path, value)

    add("summary", body.get("summary", ""))
    add("error_message", body.get("error_message", ""))
    for index, citation in enumerate(body.get("citations", []) or []):
        if isinstance(citation, dict):
            add(f"citations[{index}].snippet", citation.get("snippet", ""))
    for index, item in enumerate(body.get("retrieved", []) or []):
        if isinstance(item, dict):
            add(f"retrieved[{index}].snippet", item.get("snippet", ""))
    add_body_scalars(body, "body")
    add("endpoint_body_json", json.dumps(body, ensure_ascii=False, sort_keys=True))
    add("raw_llm_text", raw_llm_text)

    hit_fields = [field for field in fields if field.get("hit")]
    pattern_hits = sorted({name for field in hit_fields for name in field.get("pattern_hits", [])})
    return {
        "fields_scanned": len(fields),
        "hit_count": len(hit_fields),
        "hit_fields": hit_fields,
        "pattern_hits": pattern_hits,
    }


def is_nonblocking_phi_diagnostic_field(field: str) -> bool:
    if field == "endpoint_body_json":
        return True
    if field == "body.case_id":
        return True
    if re.fullmatch(r"body\.retrieved\[\d+\]\.similarity", field):
        return True
    return False


def phi_diagnostic_blocking_fields(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in diagnostics.get("hit_fields", [])
        if isinstance(item, dict) and not is_nonblocking_phi_diagnostic_field(str(item.get("field", "")))
    ]


def phi_diagnostic_nonblocking_fields(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in diagnostics.get("hit_fields", [])
        if isinstance(item, dict) and is_nonblocking_phi_diagnostic_field(str(item.get("field", "")))
    ]


def write_replay_response_artifacts(
    *,
    model_label: str,
    case_id: str,
    body: dict[str, Any],
    raw_llm_text: str,
    scan_output,
    phi_patterns: list[Any] | None = None,
) -> tuple[dict[str, str], bool]:
    paths: dict[str, str] = {}
    response_dir = RESULT_DIR / "responses" / safe_slug(model_label)
    response_dir.mkdir(parents=True, exist_ok=True)
    body_text = json.dumps(body, ensure_ascii=False, indent=2)
    diagnostics = replay_phi_diagnostics(
        body=body,
        raw_llm_text=raw_llm_text,
        scan_output=scan_output,
        phi_patterns=phi_patterns or [],
    )
    if phi_diagnostic_blocking_fields(diagnostics):
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
    from app.llm import phi_strip

    scan_output = phi_strip.scan_output
    phi_patterns = list(getattr(phi_strip, "PHI_PATTERNS", []))

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
        output_phi = output_phi_hit(body, scan_output) if isinstance(body, dict) else True
        phi_hit = output_phi
        response_paths: dict[str, str] = {}
        raw_storage_phi_hit = False
        phi_scan_diagnostics: dict[str, Any] = {}
        if store_replay_responses and isinstance(body, dict):
            raw_llm_text = str(trace.get("_raw_llm_text_for_storage", "")) if llm_called else ""
            phi_scan_diagnostics = replay_phi_diagnostics(
                body=body,
                raw_llm_text=raw_llm_text,
                scan_output=scan_output,
                phi_patterns=phi_patterns,
            )
            response_paths, raw_storage_phi_hit = write_replay_response_artifacts(
                model_label=model_label,
                case_id=case_id,
                body=body,
                raw_llm_text=raw_llm_text,
                scan_output=scan_output,
                phi_patterns=phi_patterns,
            )
            phi_hit = phi_hit or raw_storage_phi_hit
        phi_scan_blocking_fields = [
            str(item.get("field", ""))
            for item in phi_diagnostic_blocking_fields(phi_scan_diagnostics)
        ]
        phi_scan_nonblocking_fields = [
            str(item.get("field", ""))
            for item in phi_diagnostic_nonblocking_fields(phi_scan_diagnostics)
        ]
        phi_scan_hit_fields = [
            str(item.get("field", ""))
            for item in phi_scan_diagnostics.get("hit_fields", [])
            if isinstance(item, dict)
        ]
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
        raw_citation_source_ids = trace.get("raw_citation_source_ids", []) if llm_called else []
        source_id_fidelity = source_id_fidelity_meta(raw_citation_source_ids, retrieved_source_ids)
        reachability = citation_reachability_meta(
            case,
            expected_source_ids=expected,
            retrieved_source_ids=retrieved_source_ids,
            returned_source_ids=returned_source_ids,
        )
        manual_lanes = (
            {
                "semantic": "pending",
                "grounding": "pending",
                "citation_claim": "pending",
                "safety": "pending",
                "note": "",
            }
            if store_replay_responses and llm_called
            else {}
        )
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
            "raw_citation_source_ids": raw_citation_source_ids,
            "extra_top_level_keys": trace.get("extra_top_level_keys", []) if llm_called else [],
            "retrieved_count": len(body.get("retrieved", []) or []) if isinstance(body, dict) else 0,
            "citation_count": len(body.get("citations", []) or []) if isinstance(body, dict) else 0,
            "returned_source_ids": returned_source_ids,
            "retrieved_source_ids": retrieved_source_ids,
            "source_id_fidelity": source_id_fidelity,
            "expected_source_ids": reachability["expected_source_ids"],
            "expected_source_retrieved": reachability["expected_source_retrieved"],
            "expected_source_not_retrieved": reachability["expected_source_not_retrieved"],
            "expected_retrieved_not_cited": reachability["expected_retrieved_not_cited"],
            "expected_source_satisfied": reachability["expected_source_satisfied"],
            "expected_source_reachability_pass": reachability["expected_source_reachability_pass"],
            "citation_selection_pass": reachability["citation_selection_pass"],
            "citation_policy_reachability_pass": reachability["citation_policy_reachability_pass"],
            "citation_policy_selection_pass": reachability["citation_policy_selection_pass"],
            "citation_policy_required_not_retrieved": reachability["citation_policy_required_not_retrieved"],
            "citation_policy_required_retrieved_not_cited": reachability["citation_policy_required_retrieved_not_cited"],
            "citation_policy_core_not_retrieved": reachability["citation_policy_core_not_retrieved"],
            "citation_policy_core_retrieved_not_cited": reachability["citation_policy_core_retrieved_not_cited"],
            "citation_policy": reachability["citation_policy"],
            "citation_issues": citation_issues,
            "expected_citations_missing": expected_missing,
            "phi_hit_count": 1 if phi_hit else 0,
            "phi_output_hit": bool(output_phi),
            "phi_scan_diagnostics": phi_scan_diagnostics,
            "phi_scan_hit_fields": phi_scan_hit_fields,
            "phi_scan_blocking_hit_fields": phi_scan_blocking_fields,
            "phi_scan_nonblocking_hit_fields": phi_scan_nonblocking_fields,
            "phi_scan_pattern_hits": phi_scan_diagnostics.get("pattern_hits", []),
            "response_artifacts": response_paths,
            "replay_raw_storage_phi_blocked": raw_storage_phi_hit,
            "manual_review_needed": store_replay_responses and llm_called,
            "manual_lanes": manual_lanes,
            "semantic_pass": None if store_replay_responses and llm_called else None,
            "grounding_pass": None if store_replay_responses and llm_called else None,
            "citation_claim_pass": None if store_replay_responses and llm_called else None,
            "safety_pass": None if store_replay_responses and llm_called else None,
        }
        row.update(content_lane_meta(case, trace, llm_called=llm_called))
        row["failure_lanes"] = classify_failure_lanes(row)
        row["failure_owner"] = classify_failure(row)
        results.append(row)
        if row["phi_hit_count"] > 0:
            raise HarnessHardStop(f"PHI hard stop at {case_id}", results)
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
                f"{sum(1 for c in cases if has_citation_issue(c))} | "
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
                    f"reach_gap={len(case.get('expected_source_not_retrieved') or [])} "
                    f"cite_gap={len(case.get('expected_retrieved_not_cited') or [])} "
                    f"policy_reach={case.get('citation_policy_reachability_pass')} "
                    f"policy_select={case.get('citation_policy_selection_pass')} "
                    f"policy_pass={case.get('citation_policy', {}).get('policy_pass')} "
                    f"sid={case.get('source_id_fidelity', {}).get('source_id_fidelity_lane_status', '-')} "
                    f"lanes={','.join(case.get('failure_lanes') or []) or '-'} "
                    f"phi={case['phi_hit_count']} "
                    f"phi_blocking={','.join(case.get('phi_scan_blocking_hit_fields') or []) or '-'} "
                    f"phi_nonblocking={','.join(case.get('phi_scan_nonblocking_hit_fields') or []) or '-'} "
                    f"phi_patterns={','.join(case.get('phi_scan_pattern_hits') or []) or '-'} "
                    f"owner={case['failure_owner'] or '-'}\n"
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
            if isinstance(exc, HarnessHardStop):
                model_row["cases"] = exc.partial_results
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
