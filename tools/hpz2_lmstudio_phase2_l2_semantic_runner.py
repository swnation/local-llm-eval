#!/usr/bin/env python3
"""
HP Z2 LM Studio Phase 2 L2 semantic smoke runner.

L2 is synthetic LM Studio-only evaluation. It does not import or call
EMR_AI_24clinic and it never calls /explain. Real execution is refused unless
both --confirm-hpz2 and --confirm-l2-run are provided.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "models_config_hpz2_lmstudio_phase2_l2_semantic_v0.1.json"
DEFAULT_EVAL_SET = "prompts/rag_aware_eval_set_v0.1.json"
DEFAULT_SERVER_URL = "http://127.0.0.1:1234/v1"
RESULTS_DIR = Path("results")

LOAD_TIMEOUT_SEC = 1200
ESTIMATE_TIMEOUT_SEC = 300
STATUS_TIMEOUT_SEC = 30
UNLOAD_TIMEOUT_SEC = 180
API_TIMEOUT_SEC = 600

REQUIRED_LANES = {
    "semantic_rag_lane",
    "normalizer_lane",
    "native_contract_lane",
    "real_endpoint_lane",
}
REQUIRED_HOOK_PREFIXES = ("C1_", "C2_", "C3_", "C4_", "C5_", "C6_", "C7_")
PLACEHOLDER_PATTERNS = (
    re.compile(r"^\{TBD(?:-[^}]*)?\}$", re.IGNORECASE),
    re.compile(r"^\{TBD-by-user-spot-check\}$", re.IGNORECASE),
    re.compile(r"^\{placeholder\}$", re.IGNORECASE),
)


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def run_cmd(cmd: list[str], timeout: int) -> dict[str, Any]:
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


def normalize_cli_args(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise TypeError("lms_cli_args must be a string or list of strings")


def option_args(options: dict[str, Any], include_ttl: bool = True) -> list[str]:
    args: list[str] = []
    for key, value in options.items():
        if key == "ttl" and not include_ttl:
            continue
        args.extend(["--" + key.replace("_", "-"), str(value)])
    return args


def lms_status(lms_exe: str) -> dict[str, Any]:
    return run_cmd([lms_exe, "status"], timeout=STATUS_TIMEOUT_SEC)


def lms_status_has_no_models(status: dict[str, Any]) -> bool:
    if status.get("returncode") != 0:
        return False
    text = f"{status.get('stdout', '')}\n{status.get('stderr', '')}".lower()
    return "no models loaded" in text or "no loaded models" in text


def wait_for_no_models(lms_exe: str, timeout_sec: int = 120, poll_sec: int = 5) -> dict[str, Any]:
    deadline = time.perf_counter() + timeout_sec
    last = lms_status(lms_exe)
    while time.perf_counter() < deadline:
        if lms_status_has_no_models(last):
            return last
        time.sleep(poll_sec)
        last = lms_status(lms_exe)
    return last


def unload_all(lms_exe: str) -> dict[str, Any]:
    return run_cmd([lms_exe, "unload", "--all"], timeout=UNLOAD_TIMEOUT_SEC)


def disk_free_info(pacing: dict[str, Any]) -> dict[str, Any]:
    path = str(pacing.get("free_space_path", "C:\\"))
    floor_gib = float(pacing.get("free_space_floor_gib", pacing.get("free_space_floor_gb", 100)))
    usage = shutil.disk_usage(path)
    free_gib = usage.free / (1024 ** 3)
    return {
        "path": path,
        "free_bytes": usage.free,
        "free_gib": round(free_gib, 3),
        "floor_gib": floor_gib,
        "pass": free_gib >= floor_gib,
    }


def sleep_cooldown(seconds: int | float, reason: str) -> dict[str, Any]:
    delay = max(0.0, float(seconds or 0))
    event = {
        "reason": reason,
        "requested_sec": delay,
        "slept_sec": delay,
    }
    if delay <= 0:
        return event
    print(f"  wait {delay:.1f}s: {reason}", flush=True)
    time.sleep(delay)
    return event


def cooldown_seconds_for_model(pacing: dict[str, Any], model_label: str, failed: bool) -> tuple[float, str]:
    candidates = [float(pacing.get("post_unload_cooldown_sec", 0) or 0)]
    reasons = ["post_unload"]
    if model_label in set(str(label) for label in pacing.get("large_model_labels", [])):
        candidates.append(float(pacing.get("post_large_model_cooldown_sec", 0) or 0))
        reasons.append("large_model")
    if failed:
        candidates.append(float(pacing.get("post_failure_cooldown_sec", 0) or 0))
        reasons.append("failure")
    return max(candidates), "max(" + ",".join(reasons) + ")"


def pacing_gate(
    lms_exe: str,
    pacing: dict[str, Any],
    phase: str,
    *,
    do_unload: bool,
    cooldown_sec: int | float = 0,
    cooldown_reason: str = "",
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "phase": phase,
        "unload_requested": do_unload,
    }
    if do_unload:
        event["unload"] = unload_all(lms_exe)
    event["unload_success"] = (not do_unload) or event.get("unload", {}).get("returncode") == 0
    event["lms_status"] = wait_for_no_models(lms_exe)
    event["no_models_loaded"] = lms_status_has_no_models(event["lms_status"])
    event["free_space"] = disk_free_info(pacing)
    event["pass"] = event["unload_success"] and event["no_models_loaded"] and bool(event["free_space"].get("pass"))
    if event["pass"] and float(cooldown_sec or 0) > 0:
        event["cooldown"] = sleep_cooldown(cooldown_sec, cooldown_reason or phase)
    return event


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


def openai_base_url(value: str) -> str:
    clean = str(value).strip().rstrip("/")
    return clean if clean.endswith("/v1") else f"{clean}/v1"


def is_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    if text == "":
        return True
    return any(pattern.match(text) for pattern in PLACEHOLDER_PATTERNS)


def contains_placeholder_marker(value: Any) -> bool:
    text = str(value or "")
    if is_placeholder(text):
        return True
    return bool(re.search(r"\{TBD(?:-[^}]*)?\}|\{placeholder\}", text, flags=re.IGNORECASE))


def strip_source_wrappers(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        return text[1:-1].strip()
    return text


def extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""
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
    return ""


def strip_code_fences(text: str) -> str:
    clean = str(text or "").strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def normalize_output(text: str) -> dict[str, Any]:
    raw_text = str(text or "")
    stripped = strip_code_fences(raw_text)
    candidates = [stripped]
    first_object = extract_first_json_object(stripped)
    if first_object and first_object not in candidates:
        candidates.append(first_object)

    parsed: Any = None
    parse_status = "not_json"
    schema_error = ""
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            parse_status = "json_parse_ok"
            break
        except json.JSONDecodeError as exc:
            schema_error = str(exc)

    summary = ""
    citations: list[str] = []
    if isinstance(parsed, dict):
        summary = str(parsed.get("summary") or parsed.get("answer") or "").strip()
        raw_citations = parsed.get("citations", [])
        if isinstance(raw_citations, str):
            citations.append(raw_citations)
        elif isinstance(raw_citations, list):
            for item in raw_citations:
                if isinstance(item, dict):
                    citations.append(str(item.get("source_id") or item.get("id") or ""))
                else:
                    citations.append(str(item))

    if not citations:
        citations.extend(re.findall(r"\[([^\[\]\r\n]{1,200})\]", raw_text))

    normalized_citations = []
    for citation in citations:
        clean = strip_source_wrappers(citation)
        if clean and clean not in normalized_citations:
            normalized_citations.append(clean)

    summary_has_placeholder = contains_placeholder_marker(summary)
    citation_has_placeholder = any(is_placeholder(strip_source_wrappers(item)) for item in normalized_citations)
    native_contract_pass = (
        isinstance(parsed, dict)
        and isinstance(parsed.get("summary"), str)
        and isinstance(parsed.get("citations"), list)
        and all(isinstance(item, str) for item in parsed.get("citations", []))
        and not summary_has_placeholder
        and not citation_has_placeholder
    )
    normalizer_pass = bool(summary and normalized_citations and not summary_has_placeholder and not citation_has_placeholder)
    return {
        "raw_text": raw_text,
        "extracted_json": parsed if isinstance(parsed, dict) else None,
        "parse_status": parse_status,
        "schema_error": "" if parsed is not None else schema_error,
        "summary": summary,
        "summary_has_placeholder": summary_has_placeholder,
        "citation_has_placeholder": citation_has_placeholder,
        "citations": normalized_citations,
        "native_contract_pass": native_contract_pass,
        "normalizer_pass": normalizer_pass,
    }


def source_ids_from_evidence(case: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in case.get("evidence_pack", []):
        source_id = strip_source_wrappers(item.get("source_id", ""))
        if source_id and source_id not in ids:
            ids.append(source_id)
    return ids


def acceptable_set_for_case(l2_case: dict[str, Any], eval_case: dict[str, Any], eval_set: dict[str, Any]) -> dict[str, Any]:
    policy = dict(l2_case.get("acceptable_citation_set") or eval_case.get("acceptable_citation_set") or {})
    if not policy:
        required = list(eval_case.get("expected_citations_includes_at_least", []))
        policy["required_all"] = [strip_source_wrappers(item) for item in required if not is_placeholder(item)]
    policy.setdefault("invalid_aliases", [])
    policy.setdefault("optional_hits", [])
    return policy


def score_citations(returned: list[str], evidence_ids: list[str], policy: dict[str, Any]) -> dict[str, Any]:
    returned_clean = [strip_source_wrappers(item) for item in returned if strip_source_wrappers(item)]
    placeholders = [item for item in returned_clean if is_placeholder(item)]
    invalid_aliases = [item for item in returned_clean if item in set(policy.get("invalid_aliases", []))]
    invalid_unknown = [
        item
        for item in returned_clean
        if item not in evidence_ids and item not in invalid_aliases and item not in placeholders
    ]
    required_all = [strip_source_wrappers(item) for item in policy.get("required_all", [])]
    core_any_of = [strip_source_wrappers(item) for item in policy.get("core_any_of", [])]
    strong_all = [strip_source_wrappers(item) for item in policy.get("strong_all", [])]
    optional_hits = [strip_source_wrappers(item) for item in policy.get("optional_hits", [])]

    required_pass = all(item in returned_clean for item in required_all) if required_all else None
    core_pass = any(item in returned_clean for item in core_any_of) if core_any_of else required_pass
    if core_pass is None:
        core_pass = bool(returned_clean) and not placeholders and not invalid_aliases and not invalid_unknown
    strong_pass = all(item in returned_clean for item in strong_all) if strong_all else required_pass

    return {
        "returned_source_ids": returned_clean,
        "evidence_source_ids": evidence_ids,
        "placeholder_citations": placeholders,
        "invalid_aliases": invalid_aliases,
        "invalid_unknown_citations": invalid_unknown,
        "required_all": required_all,
        "required_pass": required_pass,
        "core_any_of": core_any_of,
        "core_citation_pass": bool(core_pass),
        "strong_all": strong_all,
        "strong_citation_pass": bool(strong_pass) if strong_pass is not None else False,
        "optional_hits": [item for item in optional_hits if item in returned_clean],
        "citation_integrity": not placeholders and not invalid_aliases and not invalid_unknown and bool(core_pass),
    }


def case_manual_review_needed(eval_case: dict[str, Any]) -> bool:
    return is_placeholder(eval_case.get("expected_summary_keywords"))


def evaluate_semantic_lanes(
    *,
    text: str,
    l2_case: dict[str, Any],
    eval_case: dict[str, Any],
    eval_set: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_output(text)
    evidence_ids = source_ids_from_evidence(l2_case)
    policy = acceptable_set_for_case(l2_case, eval_case, eval_set)
    citation_score = score_citations(normalized["citations"], evidence_ids, policy)
    manual_review_needed = case_manual_review_needed(eval_case)
    safety_pass = not citation_score["placeholder_citations"] and not normalized["summary_has_placeholder"]
    grounding_pass = citation_score["citation_integrity"]
    semantic_pass = None if manual_review_needed else bool(normalized["summary"] and grounding_pass and safety_pass)
    failure_owner = None
    if not normalized["summary"]:
        failure_owner = "model"
    elif normalized["summary_has_placeholder"]:
        failure_owner = "model"
    elif citation_score["placeholder_citations"]:
        failure_owner = "model"
    elif citation_score["invalid_unknown_citations"] or citation_score["invalid_aliases"]:
        failure_owner = "model"
    elif manual_review_needed:
        failure_owner = "manual_review_needed"

    return {
        "lanes": {
            "semantic_rag_lane": {
                "semantic_pass": semantic_pass,
                "grounding_pass": grounding_pass,
                "citation_integrity": citation_score["citation_integrity"],
                "safety_pass": safety_pass,
                "manual_review_needed": manual_review_needed,
                "failure_owner": failure_owner,
            },
            "normalizer_lane": {
                "normalizer_pass": normalized["normalizer_pass"],
                "normalizer_error": "" if normalized["normalizer_pass"] else "missing summary or citations",
                "extracted_summary": normalized["summary"],
                "extracted_citations": normalized["citations"],
            },
            "native_contract_lane": {
                "native_contract_pass": normalized["native_contract_pass"],
                "parse_status": normalized["parse_status"],
                "schema_error": normalized["schema_error"],
            },
            "real_endpoint_lane": {
                "endpoint_pass": None,
                "response_status": "not_run_l2_synthetic_only",
                "latency_ms": None,
                "verifier_result": "not_run_l2_synthetic_only",
                "PHI_zero_hit": None,
            },
        },
        "citation_score": citation_score,
        "r2_metric_hooks": {
            "claim_count": None,
            "claim_grounded_count": None,
            "claim_grounding_score": None,
            "retrieval_precision_at_k": None,
            "retrieval_recall_proxy": None,
            "response_completeness": "manual_review_needed" if manual_review_needed else None,
            "case_metric_profile": l2_case.get("case_metric_profile"),
            "metric_risk_notes": l2_case.get("metric_risk_notes", ""),
        },
        "normalized_output": normalized,
    }


def eval_case_map(eval_set: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(case.get("id")): case for case in eval_set.get("cases", [])}


def validate_config(config: dict[str, Any], eval_set: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    lanes = set(eval_set.get("evaluation_lanes", {}).keys())
    missing_lanes = sorted(REQUIRED_LANES - lanes)
    if missing_lanes:
        errors.append(f"eval_set missing evaluation lanes: {', '.join(missing_lanes)}")
    placeholder_policy = eval_set.get("placeholder_policy", {})
    if placeholder_policy.get("id") != "P7-placeholder-rejection":
        errors.append("eval_set placeholder_policy.id must be P7-placeholder-rejection")
    hook_keys = eval_set.get("r2_metric_hooks", {}).keys()
    for prefix in REQUIRED_HOOK_PREFIXES:
        if not any(str(key).startswith(prefix) for key in hook_keys):
            errors.append(f"eval_set r2_metric_hooks missing {prefix}")
    if config.get("_l2_semantic_smoke", {}).get("mode") != "l2_synthetic_semantic_smoke":
        errors.append("config _l2_semantic_smoke.mode must be l2_synthetic_semantic_smoke")
    if "/explain" in json.dumps(config.get("_l2_semantic_smoke", {}), ensure_ascii=False).lower():
        errors.append("L2 config must not include /explain execution scope")
    pacing = config.get("_execution_pacing", {})
    if not isinstance(pacing, dict):
        errors.append("config _execution_pacing must be an object")
        pacing = {}
    for key in ("post_unload_cooldown_sec", "post_large_model_cooldown_sec", "post_failure_cooldown_sec"):
        try:
            if float(pacing.get(key, 0)) < 0:
                errors.append(f"_execution_pacing.{key} must be non-negative")
        except (TypeError, ValueError):
            errors.append(f"_execution_pacing.{key} must be numeric")
    try:
        if float(pacing.get("free_space_floor_gib", pacing.get("free_space_floor_gb", 100))) < 100:
            errors.append("_execution_pacing free-space floor must be >= 100 GiB")
    except (TypeError, ValueError):
        errors.append("_execution_pacing free-space floor must be numeric")

    labels = [str(model.get("label", "")) for model in config.get("models", [])]
    if len(labels) != len(set(labels)):
        errors.append("model labels must be unique")
    label_set = set(labels)
    for label in pacing.get("large_model_labels", []):
        if str(label) not in label_set:
            errors.append(f"_execution_pacing.large_model_labels references unknown label: {label}")
    default_tier = str(config.get("_default_tier", "default"))
    if default_tier != "all" and default_tier not in config.get("_model_tiers", {}):
        errors.append(f"config _default_tier not found in _model_tiers: {default_tier}")
    for tier_name, tier_labels in config.get("_model_tiers", {}).items():
        if not isinstance(tier_labels, list):
            errors.append(f"_model_tiers.{tier_name} must be a list")
            continue
        for label in tier_labels:
            if str(label) not in label_set:
                errors.append(f"_model_tiers.{tier_name} references unknown label: {label}")
    for model in models:
        for field in ("label", "provider", "lms_key", "served_model_id", "load_options", "inference_options"):
            if field not in model:
                errors.append(f"model {model.get('label', '<missing>')} missing {field}")
        if model.get("provider") != "lm_studio":
            errors.append(f"model {model.get('label')} provider must be lm_studio")

    cases_by_id = eval_case_map(eval_set)
    l2_case_ids: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id", ""))
        eval_case_id = str(case.get("eval_case_id", ""))
        if not case_id:
            errors.append("L2 case missing case_id")
        if case_id in l2_case_ids:
            errors.append(f"duplicate L2 case_id: {case_id}")
        l2_case_ids.append(case_id)
        if eval_case_id not in cases_by_id:
            errors.append(f"{case_id}: unknown eval_case_id {eval_case_id}")
            continue
        evidence_ids = source_ids_from_evidence(case)
        if not evidence_ids:
            errors.append(f"{case_id}: evidence_pack is empty")
        for item in case.get("evidence_pack", []):
            source_id = strip_source_wrappers(item.get("source_id", ""))
            if is_placeholder(source_id):
                errors.append(f"{case_id}: evidence source_id is placeholder")
            if contains_placeholder_marker(item.get("text", "")):
                errors.append(f"{case_id}: evidence text contains placeholder marker")
        policy = acceptable_set_for_case(case, cases_by_id[eval_case_id], eval_set)
        for key in ("required_all", "core_any_of", "strong_all", "optional_hits"):
            for source_id in policy.get(key, []):
                clean = strip_source_wrappers(source_id)
                if is_placeholder(clean):
                    errors.append(f"{case_id}: {key} contains placeholder")
                if clean and clean not in evidence_ids:
                    errors.append(f"{case_id}: {key} source_id not in evidence_pack: {clean}")
        if "real_endpoint" in str(case.get("mode", "")).lower():
            errors.append(f"{case_id}: L2 case mode must not be real endpoint")

    ra03 = cases_by_id.get("RA-03-safety-boundary", {}).get("explain_request", {}).get("context", {})
    if ra03.get("orders") != ["sme", "trimesy", "lacto2"] or ra03.get("dx") != ["a090"] or ra03.get("age") != 1:
        errors.append("RA-03 resolved values drifted from sme+trimesy+lacto2 / a090 / age=1")
    return errors


def select_models(config: dict[str, Any], wanted: list[str] | None, tier: str | None) -> list[dict[str, Any]]:
    models = list(config.get("models", []))
    models_by_label = {str(model.get("label", "")): model for model in models}
    if wanted:
        wanted_order = [str(label) for label in wanted]
    else:
        tier_name = tier or str(config.get("_default_tier", "default"))
        tiers = config.get("_model_tiers", {})
        if tier_name == "all":
            wanted_order = [str(model.get("label", "")) for model in models]
        else:
            wanted_order = [str(label) for label in tiers.get(tier_name, [])]
            if not wanted_order:
                raise ValueError(f"unknown or empty model tier: {tier_name}")
    selected = [models_by_label[label] for label in wanted_order if label in models_by_label]
    missing = sorted(set(wanted_order) - {str(model.get("label", "")) for model in selected})
    if missing:
        raise ValueError(f"unknown model labels: {', '.join(missing)}")
    return selected


def select_cases(config: dict[str, Any], wanted: list[str] | None) -> list[dict[str, Any]]:
    cases = list(config.get("l2_cases", []))
    if not wanted:
        return cases
    wanted_set = set(wanted)
    selected = [case for case in cases if case.get("case_id") in wanted_set]
    missing = sorted(wanted_set - {str(case.get("case_id", "")) for case in selected})
    if missing:
        raise ValueError(f"unknown L2 case IDs: {', '.join(missing)}")
    return selected


def build_prompt(config: dict[str, Any], case: dict[str, Any], eval_case: dict[str, Any]) -> tuple[str, str]:
    prompt_cfg = config.get("_prompt_template", {})
    system = str(prompt_cfg.get("system", "")).strip()
    evidence_lines = []
    for item in case.get("evidence_pack", []):
        evidence_lines.append(f"- [{item['source_id']}] {item['text']}")
    expected = acceptable_set_for_case(case, eval_case, {})
    user = str(prompt_cfg.get("user_template", "")).format(
        case_id=case.get("case_id", ""),
        eval_case_id=case.get("eval_case_id", ""),
        task=case.get("task", ""),
        case_context=json.dumps(case.get("case_context", {}), ensure_ascii=False, indent=2),
        evidence_pack="\n".join(evidence_lines),
        acceptable_citation_set=json.dumps(expected, ensure_ascii=False, indent=2),
        output_contract=json.dumps(prompt_cfg.get("output_contract", {}), ensure_ascii=False, indent=2),
    )
    return system, user


def apply_prompt_profile(system: str, user: str, options: dict[str, Any]) -> tuple[str, str]:
    system_parts: list[str] = []
    user_parts: list[str] = []
    if options.get("system_prefix"):
        system_parts.append(str(options["system_prefix"]).strip())
    if system:
        system_parts.append(system)
    if options.get("system_suffix"):
        system_parts.append(str(options["system_suffix"]).strip())
    if options.get("user_prefix"):
        user_parts.append(str(options["user_prefix"]).strip())
    if user:
        user_parts.append(user)
    if options.get("user_suffix"):
        user_parts.append(str(options["user_suffix"]).strip())
    return "\n\n".join(part for part in system_parts if part), "\n\n".join(part for part in user_parts if part)


def response_format_payload(mode: str | None) -> dict[str, Any] | None:
    clean = str(mode or "none").lower()
    if clean in {"none", "off", "false"}:
        return None
    if clean == "json_object":
        return {"type": "json_object"}
    if clean == "json_schema":
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "l2_semantic_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "citations": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["summary", "citations"],
                    "additionalProperties": False,
                },
            },
        }
    raise ValueError(f"unsupported response_format: {mode}")


def call_chat_completion(server_url: str, model_id: str, system: str, user: str, options: dict[str, Any]) -> dict[str, Any]:
    url = openai_base_url(server_url) + "/chat/completions"
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(options.get("temperature", 0.0)),
        "max_tokens": int(options.get("max_tokens", 512)),
        "stream": False,
    }
    for key in ("top_p", "top_k", "min_p", "presence_penalty", "frequency_penalty", "repeat_penalty"):
        if key in options:
            payload[key] = options[key]
    response_format = response_format_payload(options.get("response_format"))
    if response_format:
        payload["response_format"] = response_format

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=int(options.get("timeout_seconds", API_TIMEOUT_SEC))) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        text = str(parsed.get("choices", [{}])[0].get("message", {}).get("content", "") or "")
        return {
            "status": "ok",
            "text": text,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "usage": parsed.get("usage", {}),
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "status": "http_error",
            "text": "",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error": f"HTTP {exc.code}: {body[:300]}",
        }
    except Exception as exc:
        return {
            "status": "request_error",
            "text": "",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def merged_inference_options(config: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    options.update(config.get("_inference_profile_defaults", {}))
    options.update(model.get("inference_options", {}))
    options.setdefault("response_format", "none")
    options.setdefault("temperature", 0.0)
    options.setdefault("max_tokens", 512)
    options.setdefault("timeout_seconds", API_TIMEOUT_SEC)
    return options


def dry_run_report(config: dict[str, Any], eval_set: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]]) -> int:
    errors = validate_config(config, eval_set, models, cases)
    print(f"{config.get('_stage_label', 'HP Z2 Phase 2 L2 Semantic Smoke')} dry-run")
    print(f"mode: {config.get('_l2_semantic_smoke', {}).get('mode')}")
    print(f"models: {len(models)}")
    for model in models:
        print(f"  - {model['label']} -> {model['lms_key']} [{model.get('_tier', '-')}]")
    print(f"cases: {len(cases)}")
    for case in cases:
        evidence_ids = ", ".join(source_ids_from_evidence(case))
        print(f"  - {case['case_id']} ({case['eval_case_id']}): {evidence_ids}")
    print(f"lanes: {', '.join(sorted(eval_set.get('evaluation_lanes', {}).keys()))}")
    print(f"placeholder_policy: {eval_set.get('placeholder_policy', {}).get('id')}")
    print(f"metric_hooks: {len(eval_set.get('r2_metric_hooks', {}))}")
    pacing = config.get("_execution_pacing", {})
    print(f"post_unload_cooldown_sec: {pacing.get('post_unload_cooldown_sec')}")
    print(f"post_large_model_cooldown_sec: {pacing.get('post_large_model_cooldown_sec')}")
    print(f"post_failure_cooldown_sec: {pacing.get('post_failure_cooldown_sec')}")
    print(f"free_space_floor_gib: {pacing.get('free_space_floor_gib', pacing.get('free_space_floor_gb', 100))}")
    if errors:
        print("validation errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("dry-run only; no lms commands, model loads, LM Studio API calls, /explain calls, or EMR writes were executed.")
    return 0


def write_outputs(payload: dict[str, Any], timestamp: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(exist_ok=True)
    prefix = str(payload.get("result_prefix", "hpz2_lmstudio_phase2_l2_semantic"))
    json_path = RESULTS_DIR / f"{prefix}_{timestamp}.json"
    md_path = RESULTS_DIR / f"{prefix}_{timestamp}.md"
    write_json(json_path, payload)
    with md_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# HP Z2 Phase 2 L2 Semantic Smoke\n\n")
        handle.write(f"- generated_at: {payload['generated_at']}\n")
        handle.write(f"- config: `{payload['config']}`\n")
        handle.write(f"- eval_set: `{payload['eval_set']}`\n")
        handle.write("- endpoint: not used; L2 synthetic only\n\n")
        pacing = payload.get("pacing", {})
        handle.write("## Pacing\n\n")
        handle.write(f"- post_unload_cooldown_sec: {pacing.get('post_unload_cooldown_sec')}\n")
        handle.write(f"- post_large_model_cooldown_sec: {pacing.get('post_large_model_cooldown_sec')}\n")
        handle.write(f"- post_failure_cooldown_sec: {pacing.get('post_failure_cooldown_sec')}\n")
        handle.write(f"- free_space_floor_gib: {pacing.get('free_space_floor_gib', pacing.get('free_space_floor_gb', 100))}\n")
        pre_gate = payload.get("pre_run_gate", {})
        if pre_gate:
            free_space = pre_gate.get("free_space", {})
            handle.write(
                f"- pre_run_gate: pass={pre_gate.get('pass')}, "
                f"no_models_loaded={pre_gate.get('no_models_loaded')}, "
                f"free_gib={free_space.get('free_gib')}\n"
            )
        handle.write("\n")
        handle.write("| model | case | status | semantic | normalizer | native | core cite | strong cite | failure |\n")
        handle.write("|---|---|---|---:|---:|---:|---:|---:|---|\n")
        for row in payload.get("results", []):
            if not row.get("cases"):
                handle.write(
                    "| {model} | - | {status} | - | - | - | - | - | {failure} |\n".format(
                        model=row.get("model_label"),
                        status="error" if row.get("error") else "not_run",
                        failure=row.get("error") or "",
                    )
                )
                continue
            for case in row.get("cases", []):
                lanes = case.get("lanes", {})
                semantic = lanes.get("semantic_rag_lane", {})
                normalizer = lanes.get("normalizer_lane", {})
                native = lanes.get("native_contract_lane", {})
                citation = case.get("citation_score", {})
                handle.write(
                    "| {model} | {case} | {status} | {semantic} | {normalizer} | {native} | {core} | {strong} | {failure} |\n".format(
                        model=row.get("model_label"),
                        case=case.get("case_id"),
                        status=case.get("api_status"),
                        semantic=semantic.get("semantic_pass"),
                        normalizer=normalizer.get("normalizer_pass"),
                        native=native.get("native_contract_pass"),
                        core=citation.get("core_citation_pass"),
                        strong=citation.get("strong_citation_pass"),
                        failure=semantic.get("failure_owner") or row.get("error") or "",
                    )
                )
    return json_path, md_path


def run_l2(args: argparse.Namespace, config: dict[str, Any], eval_set: dict[str, Any]) -> int:
    if not args.confirm_hpz2 or not args.confirm_l2_run:
        print("Refusing real L2 execution without --confirm-hpz2 and --confirm-l2-run.", flush=True)
        return 2
    models = select_models(config, args.models, args.tier)
    cases = select_cases(config, args.case_ids)
    errors = validate_config(config, eval_set, models, cases)
    if errors:
        for error in errors:
            print(f"config error: {error}")
        return 2

    lms_exe = find_lms_exe()
    pacing = config.get("_execution_pacing", {})
    status = lms_status(lms_exe)
    if status.get("returncode") != 0:
        print(status.get("stderr", "lms status failed"))
        return 1

    cases_by_id = eval_case_map(eval_set)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": args.config,
        "eval_set": args.eval_set,
        "stage_label": config.get("_stage_label"),
        "result_prefix": config.get("_result_artifact_prefix", "hpz2_lmstudio_phase2_l2_semantic"),
        "server_url": args.server_url,
        "host": {
            "node": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "pacing": pacing,
        "lms_status_before": status,
        "results": [],
        "stopped_early": False,
    }
    payload["pre_run_gate"] = pacing_gate(
        lms_exe,
        pacing,
        "pre_run",
        do_unload=bool(pacing.get("unload_all_before_each_model", True)),
    )
    if not payload["pre_run_gate"].get("pass"):
        payload["stopped_early"] = True
        payload["stop_reason"] = "pre-run pacing gate failed"
        payload["lms_status_after"] = lms_status(lms_exe)
        json_path, md_path = write_outputs(payload, timestamp)
        print(f"wrote: {json_path}")
        print(f"wrote: {md_path}")
        return 1

    cli_args_default = normalize_cli_args(config.get("_load_profile", {}).get("lms_cli_args"))
    for model in models:
        label = str(model["label"])
        row: dict[str, Any] = {
            "model_label": label,
            "lms_key": model["lms_key"],
            "served_model_id": model["served_model_id"],
            "load_options": model.get("load_options", {}),
            "pacing_events": [],
            "cases": [],
        }
        print(f"\n{label}", flush=True)
        row["pre_model_gate"] = pacing_gate(
            lms_exe,
            pacing,
            "pre_model_load",
            do_unload=bool(pacing.get("unload_all_before_each_model", True)),
            cooldown_sec=pacing.get("post_unload_cooldown_sec", 0),
            cooldown_reason="pre-load post-unload cooldown",
        )
        if not row["pre_model_gate"].get("pass"):
            row["success"] = False
            row["error"] = "pre-model pacing gate failed"
            payload["results"].append(row)
            payload["stopped_early"] = True
            break

        if config.get("_load_profile", {}).get("estimate_before_load", True) and not args.skip_estimate:
            row["estimate"] = estimate_model(lms_exe, model["lms_key"], model.get("load_options", {}), cli_args_default)
            if row["estimate"].get("returncode") != 0:
                row["error"] = "estimate failed"
                row["success"] = False
                row["recovery"] = pacing_gate(
                    lms_exe,
                    pacing,
                    "estimate_failure_recovery",
                    do_unload=True,
                    cooldown_sec=pacing.get("post_failure_cooldown_sec", 0),
                    cooldown_reason="post-failure cooldown",
                )
                payload["results"].append(row)
                if not row["recovery"].get("pass"):
                    payload["stopped_early"] = True
                    break
                continue
        load = load_model(lms_exe, model["lms_key"], model["served_model_id"], model.get("load_options", {}), cli_args_default)
        row["load"] = load
        if load.get("returncode") != 0:
            row["error"] = "load failed"
            row["success"] = False
            row["recovery"] = pacing_gate(
                lms_exe,
                pacing,
                "load_failure_recovery",
                do_unload=True,
                cooldown_sec=pacing.get("post_failure_cooldown_sec", 0),
                cooldown_reason="post-failure cooldown",
            )
            payload["results"].append(row)
            if not row["recovery"].get("pass"):
                payload["stopped_early"] = True
                break
            continue
        options = merged_inference_options(config, model)
        for l2_case in cases:
            eval_case = cases_by_id[str(l2_case["eval_case_id"])]
            system, user = build_prompt(config, l2_case, eval_case)
            system, user = apply_prompt_profile(system, user, options)
            api = call_chat_completion(args.server_url, model["served_model_id"], system, user, options)
            scored = evaluate_semantic_lanes(
                text=api.get("text", ""),
                l2_case=l2_case,
                eval_case=eval_case,
                eval_set=eval_set,
            )
            row["cases"].append(
                {
                    "case_id": l2_case["case_id"],
                    "eval_case_id": l2_case["eval_case_id"],
                    "api_status": api.get("status"),
                    "api_latency_ms": api.get("latency_ms"),
                    "usage": api.get("usage", {}),
                    **scored,
                }
            )
            if api.get("status") != "ok":
                row["error"] = f"generation failed: {api.get('status')}"
                row["generation_error"] = api.get("error", "")
                break
        row["success"] = not row.get("error")
        cooldown_sec, cooldown_reason = cooldown_seconds_for_model(pacing, label, failed=bool(row.get("error")))
        row["post_model_gate"] = pacing_gate(
            lms_exe,
            pacing,
            "post_model",
            do_unload=bool(pacing.get("unload_all_after_each_model", True)),
            cooldown_sec=cooldown_sec,
            cooldown_reason=f"between-model cooldown {cooldown_reason}",
        )
        payload["results"].append(row)
        if not row["post_model_gate"].get("pass"):
            row["success"] = False
            row["error"] = row.get("error") or "post-model pacing gate failed"
            payload["stopped_early"] = True
            break
    payload["lms_status_after"] = lms_status(lms_exe)
    json_path, md_path = write_outputs(payload, timestamp)
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    return 1 if payload.get("stopped_early") else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HP Z2 Phase 2 L2 semantic smoke.")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--eval-set", default=DEFAULT_EVAL_SET)
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    parser.add_argument("--tier", default=None, help="Model tier from config _model_tiers; default comes from config.")
    parser.add_argument("--models", nargs="*", help="Optional model label subset.")
    parser.add_argument("--case-ids", nargs="*", help="Optional L2 case_id subset.")
    parser.add_argument("--skip-estimate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-hpz2", action="store_true")
    parser.add_argument("--confirm-l2-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(REPO_ROOT / args.config)
    eval_set = load_json(REPO_ROOT / args.eval_set)
    models = select_models(config, args.models, args.tier)
    cases = select_cases(config, args.case_ids)
    if args.dry_run:
        return dry_run_report(config, eval_set, models, cases)
    return run_l2(args, config, eval_set)


if __name__ == "__main__":
    raise SystemExit(main())
