#!/usr/bin/env python3
"""
HP Z2 LM Studio smoke matrix runner.

This script is intentionally separate from eval_runner_auto.py. It measures a
single backend-smoke prompt across a fixed list of LM Studio models and records
load time, API wall time, raw completion-token throughput, and visible output.

It does not call EMR_AI_24clinic, does not run RAG Phase 2, and does not score
clinical prompts.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG = "models_config_hpz2_lmstudio_smoke_v0.1.json"
DEFAULT_PROMPTS = "prompts/hpz2_lmstudio_smoke_v0.1.json"
DEFAULT_SERVER_URL = "http://127.0.0.1:1234/v1"
RESULTS_DIR = Path("results")
LOAD_TIMEOUT_SEC = 900
API_TIMEOUT_SEC = 600


def load_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_lms_exe() -> str:
    found = shutil.which("lms")
    if found:
        return found

    candidates = [
        Path.home() / ".lmstudio" / "bin" / "lms.exe",
        Path.home() / ".lmstudio" / "bin" / "lms",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        "lms CLI was not found. Run LM Studio bootstrap or add lms.exe to PATH."
    )


def run_cmd(cmd: list[str], timeout: int) -> dict:
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
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


def option_args(options: dict, include_ttl: bool = True) -> list[str]:
    args: list[str] = []
    for key, value in options.items():
        if key == "ttl" and not include_ttl:
            continue
        flag = "--" + key.replace("_", "-")
        args.extend([flag, str(value)])
    return args


def unload_all(lms_exe: str) -> dict:
    return run_cmd([lms_exe, "unload", "--all"], timeout=120)


def estimate_model(lms_exe: str, model_key: str, load_options: dict) -> dict:
    cmd = [lms_exe, "load", model_key]
    cmd.extend(option_args(load_options, include_ttl=False))
    cmd.append("--estimate-only")
    return run_cmd(cmd, timeout=300)


def load_model(lms_exe: str, model_key: str, identifier: str, load_options: dict) -> dict:
    cmd = [lms_exe, "load", model_key, "--identifier", identifier]
    cmd.extend(option_args(load_options))
    return run_cmd(cmd, timeout=LOAD_TIMEOUT_SEC)


def call_chat_completion(server_url: str, model_id: str, test: dict, extra_options: dict) -> dict:
    url = server_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": test["system"]},
            {"role": "user", "content": test["user"]},
        ],
        "temperature": test.get("temperature", 0.0),
        "max_tokens": test.get("max_tokens", 512),
        "stream": False,
    }
    payload.update(extra_options or {})

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_SEC) as resp:
            raw_body = resp.read().decode("utf-8", errors="replace")
        elapsed = time.perf_counter() - start
        parsed = json.loads(raw_body)
        message = parsed.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "") or ""
        usage = parsed.get("usage", {}) or {}
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        raw_tok_s = None
        if isinstance(completion_tokens, (int, float)) and elapsed > 0:
            raw_tok_s = round(completion_tokens / elapsed, 3)
        return {
            "success": True,
            "api_wall_s": round(elapsed, 3),
            "visible_output": content.strip(),
            "visible_output_empty": content.strip() == "",
            "usage": usage,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "raw_completion_tok_s": raw_tok_s,
            "response_raw": parsed,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "success": False,
            "api_wall_s": round(time.perf_counter() - start, 3),
            "error": f"HTTP {exc.code}: {body}",
        }
    except Exception as exc:
        return {
            "success": False,
            "api_wall_s": round(time.perf_counter() - start, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def safe_name(value: str) -> str:
    return (
        value.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def write_outputs(payload: dict, timestamp: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(exist_ok=True)
    json_path = RESULTS_DIR / f"hpz2_lmstudio_smoke_{timestamp}.json"
    md_path = RESULTS_DIR / f"hpz2_lmstudio_smoke_{timestamp}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# HP Z2 LM Studio Smoke Matrix\n\n")
        f.write(f"- generated: {payload['generated_at']}\n")
        f.write(f"- host: {payload['host']['node']}\n")
        f.write(f"- backend: {payload['backend']['provider']}\n")
        f.write(f"- runtime: {payload['backend']['runtime']}\n")
        f.write(f"- server_url: `{payload['server_url']}`\n")
        f.write(f"- prompt_set: `{payload['prompt_set']}`\n\n")
        f.write("| model | status | load_s | api_wall_s | raw tok/s | tokens | visible | error |\n")
        f.write("|---|---:|---:|---:|---:|---:|---|---|\n")
        for row in payload["results"]:
            status = "pass" if row.get("success") else "fail"
            api = row.get("api", {})
            visible = api.get("visible_output", "")
            visible_short = visible.replace("\n", " ")[:80]
            token_text = "-"
            if api.get("completion_tokens") is not None or api.get("total_tokens") is not None:
                token_text = f"{api.get('completion_tokens', '-')}/{api.get('total_tokens', '-')}"
            error = row.get("error") or api.get("error") or ""
            f.write(
                "| {model} | {status} | {load_s} | {api_s} | {tok_s} | {tokens} | {visible} | {error} |\n".format(
                    model=row["model_label"],
                    status=status,
                    load_s=row.get("load_s", "-"),
                    api_s=api.get("api_wall_s", "-"),
                    tok_s=api.get("raw_completion_tok_s", "-"),
                    tokens=token_text,
                    visible=visible_short or "(empty)",
                    error=error.replace("\n", " ")[:120],
                )
            )

        f.write("\nNotes:\n")
        for note in payload.get("measurement_policy", []):
            f.write(f"- {note}\n")

    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HP Z2 LM Studio smoke matrix.")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--prompts", default=DEFAULT_PROMPTS)
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    parser.add_argument("--models", nargs="*", help="Optional subset by config label.")
    parser.add_argument("--skip-estimate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm-hpz2",
        action="store_true",
        help="Required for real execution to avoid accidental runs on non-HP hosts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    prompts = load_json(args.prompts)
    test = prompts["tests"][0]
    models = config["models"]
    if args.models:
        wanted = set(args.models)
        models = [m for m in models if m["label"] in wanted]
        missing = sorted(wanted - {m["label"] for m in models})
        if missing:
            print(f"Unknown model labels: {', '.join(missing)}", file=sys.stderr)
            return 2

    if not models:
        print("No models selected.", file=sys.stderr)
        return 2

    print("HP Z2 LM Studio smoke matrix")
    print(f"config: {args.config}")
    print(f"prompts: {args.prompts}")
    print(f"server: {args.server_url}")
    print(f"models: {len(models)}")
    for model in models:
        print(f"  - {model['label']} -> {model['lms_key']}")

    if args.dry_run:
        print("dry-run only; no lms commands or API calls were executed.")
        return 0

    if not args.confirm_hpz2:
        print("Refusing to run without --confirm-hpz2.", file=sys.stderr)
        return 2

    lms_exe = find_lms_exe()
    status = run_cmd([lms_exe, "status"], timeout=30)
    if status["returncode"] != 0:
        print(status["stderr"], file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": args.config,
        "prompt_set": args.prompts,
        "server_url": args.server_url,
        "backend": config.get("_backend", {}),
        "load_profile": config.get("_load_profile", {}),
        "measurement_policy": config.get("_measurement_policy", []),
        "host": {
            "node": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "lms_exe": lms_exe,
        "lms_status": status,
        "results": [],
    }

    for index, model in enumerate(models, start=1):
        label = model["label"]
        key = model["lms_key"]
        load_options = model.get("load_options", {})
        extra_options = model.get("inference_options", {})
        print(f"\n[{index}/{len(models)}] {label} ({key})")

        unload_all(lms_exe)
        row = {
            "model_label": label,
            "lms_key": key,
            "role": model.get("_role", ""),
            "load_options": load_options,
            "inference_options": extra_options,
        }

        if not args.skip_estimate:
            print("  estimate...")
            estimate = estimate_model(lms_exe, key, load_options)
            row["estimate"] = estimate
            if estimate["returncode"] != 0:
                row["success"] = False
                row["error"] = "estimate failed"
                payload["results"].append(row)
                print(f"  estimate failed: {estimate['stderr'].strip()}")
                continue

        print("  load...")
        load = load_model(lms_exe, key, label, load_options)
        row["load"] = load
        row["load_s"] = load["elapsed_s"]
        if load["returncode"] != 0:
            row["success"] = False
            row["error"] = "load failed"
            payload["results"].append(row)
            print(f"  load failed: {load['stderr'].strip()}")
            unload_all(lms_exe)
            continue

        time.sleep(1)
        print("  api smoke...")
        api = call_chat_completion(args.server_url, label, test, extra_options)
        row["api"] = api
        row["success"] = bool(api.get("success")) and not api.get("visible_output_empty")
        if row["success"]:
            print(
                "  pass: load={load_s}s api={api_s}s tok/s={tok_s} visible={visible!r}".format(
                    load_s=row["load_s"],
                    api_s=api.get("api_wall_s"),
                    tok_s=api.get("raw_completion_tok_s"),
                    visible=api.get("visible_output", "")[:80],
                )
            )
        else:
            print(f"  fail: {api.get('error') or 'empty visible output'}")

        payload["results"].append(row)
        unload_all(lms_exe)
        time.sleep(1)

    final_status = run_cmd([lms_exe, "status"], timeout=30)
    payload["lms_status_after"] = final_status
    json_path, md_path = write_outputs(payload, timestamp)
    print(f"\nwrote: {json_path}")
    print(f"wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
