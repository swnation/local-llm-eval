#!/usr/bin/env python3
"""HP Z2 H2 output-contract calibration runner.

Dry-run validates the synthetic fixture and selected matrix only. Real model
execution is refused unless both --confirm-hpz2 and
--confirm-output-contract-calibration are provided.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from hpz2_lmstudio_phase2_l2_semantic_runner import call_chat_completion, load_json, write_json
from hpz2_llamacpp_phase2_l2_runner import (
    build_server_args,
    memory_snapshot,
    output_root,
    preflight,
    preflight_pass,
    server_url,
    wait_for_server,
)


DEFAULT_CONFIG = "models_config_hpz2_llamacpp_phase2_l2_v0.1.json"
DEFAULT_FIXTURE = "prompts/h2_output_contract_calibration_v0.1.json"
PILOT_MODELS = ["hpz2-l2-qwen36-35b-a3b", "hpz2-l2-granite-41-30b-q4km"]
PRIMARY4_MODELS = [
    "hpz2-l2-qwen36-35b-a3b",
    "hpz2-l2-qwen36-35b-a3b-mtp-mxfp4",
    "hpz2-l2-qwen36-35b-a3b-mtp-q8",
    "hpz2-l2-granite-41-30b-q4km",
]

PHI_LIKE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("resident_registration_like", re.compile(r"\b\d{6}-\d{7}\b")),
    ("phone_like", re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")),
    ("chart_no_label", re.compile(r"(차트번호|등록번호|환자번호)\s*[:=]?\s*\w+", re.I)),
    ("patient_name_label", re.compile(r"(환자명|이름)\s*[:=]?\s*\S+", re.I)),
]


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def iso_now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def scan_phi_like(text: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in PHI_LIKE_PATTERNS:
        if pattern.search(text):
            hits.append(name)
    return hits


def format_evidence(case: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in case.get("evidence", []):
        lines.append(
            "[{source_id}] {title}\n{content}".format(
                source_id=item.get("source_id", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
            )
        )
    return "\n\n".join(lines)


def valid_source_ids(case: dict[str, Any]) -> list[str]:
    return [str(item.get("source_id", "")) for item in case.get("evidence", []) if item.get("source_id")]


def example_for_contract(fixture: dict[str, Any], contract: dict[str, Any]) -> str:
    example = fixture.get("positive_example", {})
    source_id = str(example.get("source_id", "rule:drug:example"))
    summary = str(example.get("summary", "EXAMPLE은 근거상 확인 대상입니다."))
    if contract["id"] == "C1":
        return json.dumps({"summary": summary, "citations": [f"[{source_id}]"]}, ensure_ascii=False)
    if contract["id"] == "C2":
        return json.dumps({"summary": summary, "citations": [source_id]}, ensure_ascii=False)
    if contract["id"] == "C3":
        return json.dumps({"answer": summary, "sources": [source_id]}, ensure_ascii=False)
    return str(example.get("freeform", f"{summary} [{source_id}]"))


def build_prompt(fixture: dict[str, Any], case: dict[str, Any], contract: dict[str, Any]) -> tuple[str, str]:
    system = (
        "You are testing output-contract compliance for a synthetic non-PHI "
        "clinical RAG evidence pack. Use only the provided evidence. Do not "
        "invent source IDs. Do not include patient identifiers."
    )
    source_ids = valid_source_ids(case)
    negative = fixture.get("negative_example", {})
    user = f"""Case: {case['id']}
Purpose: {case.get('purpose', '')}

Task:
{case['task']}

Evidence pack:
{format_evidence(case)}

Valid source IDs:
{json.dumps(source_ids, ensure_ascii=False)}

Required source IDs:
{json.dumps(case.get('required_sources', []), ensure_ascii=False)}

Output contract {contract['id']} ({contract.get('label', '')}):
{contract.get('description', '')}
Expected shape:
{contract.get('expected_shape', '')}

Positive example using a different source ID:
{example_for_contract(fixture, contract)}

Negative example:
{negative.get('description', '')}
{negative.get('text', '')}

Return only the requested answer for this case."""
    return system, user


def strip_code_fence(text: str) -> tuple[str, bool]:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped, False
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip(), True
    return stripped, True


def extract_json(text: str) -> tuple[dict[str, Any] | None, str, bool]:
    clean, fenced = strip_code_fence(text)
    try:
        parsed = json.loads(clean)
        return (parsed if isinstance(parsed, dict) else None), "json_ok", fenced
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(clean[start : end + 1])
                return (parsed if isinstance(parsed, dict) else None), "json_recoverable", True
            except json.JSONDecodeError:
                pass
    return None, "invalid", fenced


def normalize_source_id(value: str) -> tuple[str, bool]:
    clean = str(value).strip()
    match = re.fullmatch(r"\[([^\[\]]+)\]", clean)
    if match:
        return match.group(1), True
    return clean, False


def normalize_output(text: str, contract: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    valid_ids = set(valid_source_ids(case))
    required_sources = set(str(item) for item in case.get("required_sources", []))
    distractors = set(str(item) for item in case.get("distractor_sources", []))
    result: dict[str, Any] = {
        "parse_status": "invalid",
        "contract_variant": contract["id"],
        "native_contract_pass": False,
        "normalizer_pass": False,
        "semantic_pass": None,
        "grounding_pass": None,
        "citation_exact_pass": False,
        "citation_claim_pass": None,
        "safety_pass": None,
        "manual_review_needed": True,
        "extra_text": False,
        "extra_keys": [],
        "missing_keys": [],
        "citation_format_error": False,
        "source_id_copy_error": False,
        "summary_length_chars": 0,
        "normalized_summary": "",
        "normalized_citations": [],
        "required_sources_pass": False,
        "required_sources_missing": sorted(required_sources),
        "distractor_sources_pass": True,
        "distractor_sources_used": [],
        "phi_like_hits": scan_phi_like(text),
        "failure_owner": "manual_review_needed",
        "metric_risk_notes": [],
    }

    if contract["id"] == "C4":
        citations = re.findall(r"\[([^\[\]\r\n]{1,200})\]", text)
        summary = re.sub(r"\[[^\[\]\r\n]{1,200}\]", "", text).strip()
        result["parse_status"] = "freeform_only"
        result["normalized_summary"] = summary
        result["normalized_citations"] = citations
        result["summary_length_chars"] = len(summary)
    else:
        parsed, status, extra_text = extract_json(text)
        result["parse_status"] = status
        result["extra_text"] = extra_text
        if not parsed:
            result["metric_risk_notes"].append("JSON contract requested but no JSON object parsed")
            return result
        keys = set(parsed.keys())
        required_keys = set(str(item) for item in contract.get("required_keys", []))
        result["extra_keys"] = sorted(keys - required_keys)
        result["missing_keys"] = sorted(required_keys - keys)
        summary_key = str(contract.get("summary_key") or "")
        citation_key = str(contract.get("citation_key") or "")
        summary = parsed.get(summary_key, "")
        raw_citations = parsed.get(citation_key, [])
        if not isinstance(summary, str):
            result["missing_keys"].append(summary_key)
            summary = ""
        if not isinstance(raw_citations, list):
            result["citation_format_error"] = True
            raw_citations = []
        normalized: list[str] = []
        bracket_flags: list[bool] = []
        for item in raw_citations:
            source_id, was_bracketed = normalize_source_id(str(item))
            if source_id:
                normalized.append(source_id)
                bracket_flags.append(was_bracketed)
        result["normalized_summary"] = summary
        result["normalized_citations"] = normalized
        result["summary_length_chars"] = len(summary)
        if contract.get("citation_style") == "bracketed" and not all(bracket_flags):
            result["citation_format_error"] = True
        if contract.get("citation_style") == "bare" and any(bracket_flags):
            result["citation_format_error"] = True

    citations = [str(item) for item in result["normalized_citations"]]
    copied_unknown = sorted({item for item in citations if item not in valid_ids})
    result["source_id_copy_error"] = bool(copied_unknown)
    if copied_unknown:
        result["metric_risk_notes"].append("source_id not in evidence pack: " + ", ".join(copied_unknown))
    result["required_sources_missing"] = sorted(required_sources - set(citations))
    result["distractor_sources_used"] = sorted(distractors & set(citations))
    result["required_sources_pass"] = not result["required_sources_missing"]
    result["distractor_sources_pass"] = not result["distractor_sources_used"]
    result["citation_exact_pass"] = (
        bool(citations)
        and not result["source_id_copy_error"]
        and result["required_sources_pass"]
        and result["distractor_sources_pass"]
    )
    result["normalizer_pass"] = bool(result["normalized_summary"]) and result["citation_exact_pass"]

    max_chars = contract.get("summary_max_chars")
    length_ok = max_chars is None or result["summary_length_chars"] <= int(max_chars)
    if contract["id"] == "C1":
        result["native_contract_pass"] = (
            result["parse_status"] == "json_ok"
            and not result["extra_text"]
            and not result["extra_keys"]
            and not result["missing_keys"]
            and not result["citation_format_error"]
            and result["citation_exact_pass"]
            and length_ok
        )
    return result


def phi_redacted_scoring(raw_hits: list[str], contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_response_stored": False,
        "parse_status": "not_scored_phi_like_output",
        "contract_variant": contract["id"],
        "native_contract_pass": False,
        "normalizer_pass": False,
        "semantic_pass": None,
        "grounding_pass": None,
        "citation_exact_pass": False,
        "citation_claim_pass": None,
        "safety_pass": False,
        "manual_review_needed": True,
        "extra_text": None,
        "extra_keys": [],
        "missing_keys": [],
        "citation_format_error": None,
        "source_id_copy_error": None,
        "summary_length_chars": 0,
        "normalized_summary": "",
        "normalized_citations": [],
        "required_sources_pass": False,
        "required_sources_missing": [],
        "distractor_sources_pass": False,
        "distractor_sources_used": [],
        "phi_like_hits": raw_hits,
        "failure_owner": "PHI",
        "metric_risk_notes": ["raw response redacted because PHI-like pattern was detected"],
    }


def output_channel_policy_scoring(contract: dict[str, Any], case: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "raw_response_stored": False,
        "parse_status": f"not_scored_{status}",
        "contract_variant": contract["id"],
        "native_contract_pass": False,
        "normalizer_pass": False,
        "semantic_pass": None,
        "grounding_pass": None,
        "citation_exact_pass": False,
        "citation_claim_pass": None,
        "safety_pass": None,
        "manual_review_needed": True,
        "extra_text": None,
        "extra_keys": [],
        "missing_keys": [],
        "citation_format_error": None,
        "source_id_copy_error": None,
        "summary_length_chars": 0,
        "normalized_summary": "",
        "normalized_citations": [],
        "required_sources_pass": False,
        "required_sources_missing": sorted(str(item) for item in case.get("required_sources", [])),
        "distractor_sources_pass": True,
        "distractor_sources_used": [],
        "phi_like_hits": [],
        "failure_owner": "output_channel_policy",
        "metric_risk_notes": ["answer was emitted outside final content channel"],
    }


def workflow_accept(cell: dict[str, Any]) -> bool:
    manual_lanes = ("semantic_pass", "grounding_pass", "citation_claim_pass", "safety_pass")
    return bool(
        cell.get("api_status") == "ok"
        and cell.get("normalizer_pass") is True
        and cell.get("manual_review_needed") is False
        and all(cell.get(lane) is True for lane in manual_lanes)
        and cell.get("failure_owner") not in {"output_channel_policy", "PHI"}
    )


def quarantine_reason(cell: dict[str, Any]) -> str:
    if cell.get("failure_owner") == "output_channel_policy":
        return "reasoning_only_output"
    if cell.get("failure_owner") == "PHI":
        return "phi_like_output"
    if cell.get("api_status") != "ok":
        return "api_failure"
    if cell.get("manual_review_needed") is not False:
        return "manual_review_required"
    if any(cell.get(lane) is not True for lane in ("semantic_pass", "grounding_pass", "citation_claim_pass", "safety_pass")):
        return "manual_review_required"
    if cell.get("normalizer_pass") is False:
        return "validation_failed"
    return "not_accepted"


def validate_fixture(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contracts = fixture.get("contracts", [])
    cases = fixture.get("cases", [])
    contract_ids = [str(item.get("id", "")) for item in contracts]
    case_ids = [str(item.get("id", "")) for item in cases]
    if contract_ids != ["C1", "C2", "C3", "C4"]:
        errors.append("contracts must be exactly C1, C2, C3, C4 in order")
    if len(case_ids) != len(set(case_ids)):
        errors.append("duplicate case ids in fixture")
    if len(cases) < 3:
        errors.append("fixture must include at least 3 cases")
    fixture_text = json.dumps(fixture, ensure_ascii=False)
    phi_hits = scan_phi_like(fixture_text)
    if phi_hits:
        errors.append("fixture contains PHI-like pattern(s): " + ", ".join(phi_hits))
    for case in cases:
        evidence = case.get("evidence", [])
        source_ids = valid_source_ids(case)
        if not evidence:
            errors.append(f"{case.get('id')}: evidence is empty")
        if len(source_ids) != len(set(source_ids)):
            errors.append(f"{case.get('id')}: duplicate source ids")
        for source_id in case.get("required_sources", []):
            if source_id not in source_ids:
                errors.append(f"{case.get('id')}: required source not in evidence: {source_id}")
    return errors


def select_contracts(fixture: dict[str, Any], wanted: list[str] | None) -> list[dict[str, Any]]:
    contracts = list(fixture.get("contracts", []))
    if not wanted:
        return contracts
    wanted_set = set(wanted)
    selected = [contract for contract in contracts if contract.get("id") in wanted_set]
    missing = sorted(wanted_set - {str(contract.get("id", "")) for contract in selected})
    if missing:
        raise ValueError("unknown contract IDs: " + ", ".join(missing))
    return selected


def select_cases(fixture: dict[str, Any], wanted: list[str] | None) -> list[dict[str, Any]]:
    cases = list(fixture.get("cases", []))
    if not wanted:
        return cases
    wanted_set = set(wanted)
    selected = [case for case in cases if case.get("id") in wanted_set]
    missing = sorted(wanted_set - {str(case.get("id", "")) for case in selected})
    if missing:
        raise ValueError("unknown case IDs: " + ", ".join(missing))
    return selected


def select_models(config: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    labels = args.models or (PRIMARY4_MODELS if args.primary4 else PILOT_MODELS)
    by_label = {str(model.get("label", "")): model for model in config.get("models", [])}
    missing = [label for label in labels if label not in by_label]
    if missing:
        raise ValueError("unknown model labels: " + ", ".join(missing))
    return [by_label[label] for label in labels]


def validate_matrix(config: dict[str, Any], fixture: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> list[str]:
    errors = validate_fixture(fixture)
    if config.get("backend") != "llama.cpp":
        errors.append("backend must be llama.cpp")
    if not models:
        errors.append("no models selected")
    if not cases:
        errors.append("no cases selected")
    if not contracts:
        errors.append("no contracts selected")
    for model in models:
        for key in ("label", "model_path", "served_model_id"):
            if not model.get(key):
                errors.append(f"model missing {key}: {model}")
    return errors


def dry_run(config: dict[str, Any], fixture: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> int:
    errors = validate_matrix(config, fixture, models, cases, contracts)
    if errors:
        print("Output-contract calibration dry-run failed:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("HP Z2 H2 output-contract calibration dry-run")
    print(f"models: {len(models)}")
    for model in models:
        print(f"  - {model['label']} -> {model['model_path']}")
    print(f"cases: {len(cases)}")
    for case in cases:
        print(f"  - {case['id']} ({len(case.get('evidence', []))} evidence chunks)")
    print(f"contracts: {len(contracts)}")
    for contract in contracts:
        print(f"  - {contract['id']} {contract.get('label')} [{contract.get('response_format')}]")
    print(f"planned calls: {len(models) * len(cases) * len(contracts)}")
    print("dry-run only; no llama-server, model load, /explain call, shim, EMR write, or raw response artifact was executed.")
    return 0


def result_dir(root_value: str | None, timestamp: str) -> Path:
    return output_root(root_value) / f"h2_output_contract_calibration_{timestamp}"


def write_summary(out_dir: Path, payload: dict[str, Any]) -> Path:
    path = out_dir / "output_contract_calibration_summary.md"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# H2 Output-Contract Calibration\n\n")
        handle.write(f"- generated_at: `{payload['generated_at']}`\n")
        handle.write(f"- mode: `{payload['mode']}`\n")
        handle.write(f"- stopped_early: `{payload.get('stopped_early')}`\n")
        handle.write(f"- stop_reason: `{payload.get('stop_reason', '')}`\n")
        handle.write("- endpoint readiness: not assessed; no `/explain` call\n")
        handle.write("- raw responses: synthetic non-PHI calibration only\n\n")
        handle.write("- manual review lanes must be filled before viability decisions: `semantic_pass`, `grounding_pass`, `citation_claim_pass`, `safety_pass`\n\n")
        handle.write("| model | case | contract | api | channel | parse | native | normalizer | cite exact | required src | semantic | grounding | claim cite | safety | manual review | raw stored | failure owner | quarantine |\n")
        handle.write("|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|\n")
        for model in payload.get("models", []):
            for cell in model.get("cells", []):
                handle.write(
                    "| {model} | {case} | {contract} | {api} | {channel} | {parse} | {native} | {normalizer} | {cite} | {required} | {semantic} | {grounding} | {claim} | {safety} | {manual} | {raw} | {failure} | {quarantine} |\n".format(
                        model=model.get("label"),
                        case=cell.get("case_id"),
                        contract=cell.get("contract_variant"),
                        api=cell.get("api_status"),
                        channel=cell.get("output_channel_status", ""),
                        parse=cell.get("parse_status"),
                        native=cell.get("native_contract_pass"),
                        normalizer=cell.get("normalizer_pass"),
                        cite=cell.get("citation_exact_pass"),
                        required=cell.get("required_sources_pass"),
                        semantic=cell.get("semantic_pass"),
                        grounding=cell.get("grounding_pass"),
                        claim=cell.get("citation_claim_pass"),
                        safety=cell.get("safety_pass"),
                        manual=cell.get("manual_review_needed"),
                        raw=cell.get("raw_response_stored"),
                        failure=cell.get("failure_owner", ""),
                        quarantine=cell.get("quarantine_reason", ""),
                    )
                )
    return path


def run_real(args: argparse.Namespace, config: dict[str, Any], fixture: dict[str, Any], models: list[dict[str, Any]], cases: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> int:
    errors = validate_matrix(config, fixture, models, cases, contracts)
    if errors:
        for error in errors:
            print(error)
        return 2
    if not (args.confirm_hpz2 and args.confirm_output_contract_calibration):
        print("Refusing execution without --confirm-hpz2 and --confirm-output-contract-calibration.", flush=True)
        return 2

    timestamp = now_stamp()
    out_dir = result_dir(args.output_root, timestamp)
    raw_dir = out_dir / "raw_responses"
    prompt_dir = out_dir / "prompts"
    reasoning_dir = out_dir / "reasoning_responses"
    raw_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    reasoning_dir.mkdir(parents=True, exist_ok=True)

    pf = preflight(config)
    ok, reason = preflight_pass(config, pf)
    payload: dict[str, Any] = {
        "generated_at": iso_now(),
        "mode": "h2_output_contract_calibration",
        "backend": "llama.cpp",
        "fixture": args.fixture,
        "config": args.config,
        "raw_model_responses_stored": True,
        "endpoint_readiness_assessed": False,
        "preflight": pf,
        "models": [],
        "stopped_early": False,
        "stop_reason": "",
    }
    if not ok:
        payload["stopped_early"] = True
        payload["stop_reason"] = reason
        write_json(out_dir / "output_contract_calibration_results.json", payload)
        write_summary(out_dir, payload)
        print(f"STOP: {reason}")
        return 1

    runtime = config.get("runtime", {})
    pacing = config.get("pacing", {})
    for model in models:
        row = {
            "label": model["label"],
            "served_model_id": model.get("served_model_id"),
            "model_path": model.get("model_path"),
            "cells": [],
            "memory_before": memory_snapshot(str(pacing.get("c_free_path", "C:\\"))),
        }
        payload["models"].append(row)
        out_stdout = out_dir / f"{model['label']}_server_stdout.txt"
        out_stderr = out_dir / f"{model['label']}_server_stderr.txt"
        cmd = build_server_args(config, model, fallback=args.fallback_args)
        row["server_args"] = cmd
        with out_stdout.open("w", encoding="utf-8", newline="\n") as stdout, out_stderr.open("w", encoding="utf-8", newline="\n") as stderr:
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
                    for contract in contracts:
                        system, user = build_prompt(fixture, case, contract)
                        prompt_path = prompt_dir / f"{model['label']}__{case['id']}__{contract['id']}.txt"
                        prompt_path.write_text(f"[system]\n{system}\n\n[user]\n{user}\n", encoding="utf-8")
                        options = {
                            "response_format": contract.get("response_format", "none"),
                            "temperature": 0.0,
                            "max_tokens": 512,
                            "timeout_seconds": 900,
                        }
                        response = call_chat_completion(server_url(runtime), str(model.get("served_model_id")), system, user, options)
                        text = str(response.get("text", ""))
                        reasoning_text = str(response.get("reasoning_text", ""))
                        raw_hits = scan_phi_like(text + "\n" + reasoning_text)
                        raw_path = raw_dir / f"{model['label']}__{case['id']}__{contract['id']}.txt"
                        reasoning_path = reasoning_dir / f"{model['label']}__{case['id']}__{contract['id']}.txt"
                        raw_stored = False
                        reasoning_stored = False
                        if raw_hits:
                            scoring = phi_redacted_scoring(raw_hits, contract)
                            payload["stopped_early"] = True
                            payload["stop_reason"] = "PHI-like output detected in raw response"
                        elif response.get("output_channel_status") == "reasoning_only_output":
                            if reasoning_text:
                                reasoning_path.write_text(reasoning_text, encoding="utf-8", newline="\n")
                                reasoning_stored = True
                            scoring = output_channel_policy_scoring(contract, case, "reasoning_only_output")
                        else:
                            raw_path.write_text(text, encoding="utf-8", newline="\n")
                            raw_stored = True
                            if reasoning_text:
                                reasoning_path.write_text(reasoning_text, encoding="utf-8", newline="\n")
                                reasoning_stored = True
                            scoring = normalize_output(text, contract, case) if response.get("status") == "ok" else {}
                        cell = {
                            "case_id": case["id"],
                            "contract_variant": contract["id"],
                            "contract_label": contract.get("label"),
                            "api_status": response.get("status"),
                            "latency_ms": response.get("latency_ms"),
                            "usage": response.get("usage", {}),
                            "error": response.get("error", ""),
                            "raw_response_path": str(raw_path) if raw_stored else "",
                            "raw_response_stored": raw_stored,
                            "reasoning_response_path": str(reasoning_path) if reasoning_stored else "",
                            "reasoning_response_stored": reasoning_stored,
                            "output_channel_status": response.get("output_channel_status", ""),
                            "extraction_channel": response.get("extraction_channel", ""),
                            "content_chars": response.get("content_chars", 0),
                            "reasoning_chars": response.get("reasoning_chars", 0),
                            "message_keys": response.get("message_keys", []),
                            "finish_reason": response.get("finish_reason"),
                            "response_format_mode": contract.get("response_format", "none"),
                            "retry_attempted": False,
                            "retry_mode": "none",
                            "workflow_accept": False,
                            "quarantine_reason": "",
                        }
                        cell.update(scoring)
                        cell["workflow_accept"] = workflow_accept(cell)
                        if not cell["workflow_accept"]:
                            cell["quarantine_reason"] = quarantine_reason(cell)
                        row["cells"].append(cell)
                        if payload["stopped_early"]:
                            break
                    if payload["stopped_early"]:
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
        if payload["stopped_early"]:
            time.sleep(float(pacing.get("post_failure_seconds", 180)))
            break
        time.sleep(float(pacing.get("normal_post_model_seconds", 90)))

    payload["final_preflight"] = preflight(config)
    write_json(out_dir / "output_contract_calibration_results.json", payload)
    write_summary(out_dir, payload)
    print(f"wrote {out_dir}")
    return 1 if payload.get("stopped_early") else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE)
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--primary4", action="store_true")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--contracts", nargs="*")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fallback-args", action="store_true")
    parser.add_argument("--confirm-hpz2", action="store_true")
    parser.add_argument("--confirm-output-contract-calibration", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(args.config)
    fixture = load_json(args.fixture)
    models = select_models(config, args)
    cases = select_cases(fixture, args.cases)
    contracts = select_contracts(fixture, args.contracts)
    if args.dry_run:
        return dry_run(config, fixture, models, cases, contracts)
    return run_real(args, config, fixture, models, cases, contracts)


if __name__ == "__main__":
    raise SystemExit(main())
