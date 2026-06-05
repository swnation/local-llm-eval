#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from hpz2_llamacpp_h2_endpoint_runner import (
    augment_h2_retrieval_query,
    scalar_query_value,
    unique_query,
)


LOCAL_REPO = Path("C:/Github/local-llm-eval")
EMR_REPO = Path("C:/Github/EMR_AI_24clinic")
EVAL_SET_PATH = LOCAL_REPO / "prompts" / "rag_aware_eval_set_v0.1.json"
DEFAULT_OUTPUT_ROOT = LOCAL_REPO / "results"
DEFAULT_CASE_IDS = [
    "RA-03-safety-boundary",
    "RA-06-dexisy-pediatric-nsaid-insurance",
    "RA-07-umk-uri-syrup-age-insurance",
]
RESULT_PREFIX = "h2_c1_retrieval_probe"


class ProbeConfigError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def git_head(repo: Path) -> str:
    result = run_git(repo, ["rev-parse", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else ""


def git_status_short(repo: Path) -> list[str]:
    result = run_git(repo, ["status", "--short"])
    if result.returncode != 0:
        raise ProbeConfigError(f"could not read git status for {repo}: {result.stderr.strip()}")
    return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]


def assert_clean_git(repo: Path, label: str) -> dict[str, Any]:
    status = git_status_short(repo)
    if status:
        preview = "; ".join(status[:5])
        raise ProbeConfigError(f"{label} is not clean; refusing retrieval probe: {preview}")
    return {"head": git_head(repo), "status": "clean"}


def snapshot_tree(root: Path) -> dict[str, dict[str, Any]]:
    if not root.exists():
        return {}

    snapshot: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        try:
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                snapshot[f"{relative}/"] = {"type": "dir"}
                continue
            stat = path.stat()
        except OSError as exc:
            raise ProbeConfigError(f"could not snapshot {root}: {exc}") from exc

        snapshot[relative] = {
            "type": "file" if path.is_file() else "other",
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    return snapshot


def diff_tree_snapshots(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    shared_keys = before_keys & after_keys
    return {
        "added": sorted(after_keys - before_keys),
        "removed": sorted(before_keys - after_keys),
        "changed": sorted(key for key in shared_keys if before[key] != after[key]),
    }


def snapshot_diff_has_changes(diff: dict[str, list[str]]) -> bool:
    return any(diff.get(key) for key in ("added", "removed", "changed"))


def snapshot_diff_preview(diff: dict[str, list[str]]) -> str:
    parts: list[str] = []
    for key in ("added", "removed", "changed"):
        values = diff.get(key) or []
        if not values:
            continue
        preview = ", ".join(values[:5])
        if len(values) > 5:
            preview += f", ... (+{len(values) - 5} more)"
        parts.append(f"{key}={preview}")
    return "; ".join(parts) or "none"


def emr_ignored_cache_snapshot(emr_repo: Path) -> dict[str, dict[str, dict[str, Any]]]:
    return {"rag_index": snapshot_tree(emr_repo / "rag_index")}


def assert_emr_ignored_cache_unchanged(
    before: dict[str, dict[str, dict[str, Any]]],
    after: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, list[str]]]:
    diffs = {
        root: diff_tree_snapshots(before.get(root, {}), after.get(root, {}))
        for root in sorted(set(before) | set(after))
    }
    changed = {root: diff for root, diff in diffs.items() if snapshot_diff_has_changes(diff)}
    if changed:
        preview = "; ".join(f"{root}: {snapshot_diff_preview(diff)}" for root, diff in changed.items())
        raise ProbeConfigError(f"EMR ignored cache changed during retrieval probe; refusing output write: {preview}")
    return diffs


def set_offline_embedding_env(emr_repo: Path) -> dict[str, str]:
    hf_home = emr_repo / "rag_index" / "_build" / "hf_cache"
    forced = {
        "HF_HOME": str(hf_home),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
    }
    os.environ.update(forced)
    return forced


def disable_bytecode_writes_for_emr_import() -> None:
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def preflight_paths(emr_repo: Path) -> dict[str, Any]:
    build_dir = emr_repo / "rag_index" / "_build"
    chunks_dir = emr_repo / "rag_index" / "chunks"
    hf_cache = build_dir / "hf_cache"
    required = [
        build_dir / "vectors.npz",
        chunks_dir,
        hf_cache / "hub",
    ]
    missing = [str(path) for path in required if not path.exists()]
    jsonl_count = len(list(chunks_dir.glob("*.jsonl"))) if chunks_dir.exists() else 0
    if jsonl_count == 0:
        missing.append(str(chunks_dir / "*.jsonl"))
    if missing:
        raise ProbeConfigError(f"missing local retrieval/index cache paths: {missing}")
    return {
        "vectors": str(build_dir / "vectors.npz"),
        "chunks_dir": str(chunks_dir),
        "chunk_jsonl_count": jsonl_count,
        "hf_cache": str(hf_cache),
    }


def case_by_id(eval_set: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in eval_set.get("cases", []):
        if case.get("id") == case_id:
            return case
    raise ProbeConfigError(f"case not found in eval set: {case_id}")


def import_local_runner() -> Any:
    tools_dir = LOCAL_REPO / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import hpz2_lmstudio_phase2_stage_a_runner as stage_a_runner

    return stage_a_runner


def request_for_case(case: dict[str, Any], default_options: dict[str, Any]) -> dict[str, Any]:
    stage_a_runner = import_local_runner()
    return stage_a_runner.case_payload(case, default_options)


def merge_weight_kg(context: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(context, ensure_ascii=False))
    weight = request.get("weight_kg")
    if isinstance(weight, (int, float)) and 0 < float(weight) <= 300:
        merged["weight_kg"] = weight
    return merged


def expected_source_ids(case: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for source_id in case.get("expected_citations_includes_at_least", []) or []:
        text = str(source_id).strip()
        if text and not text.startswith("{TBD") and text not in values:
            values.append(text)
    return values


def expected_rule_source_ids(case: dict[str, Any]) -> list[str]:
    return [source_id for source_id in expected_source_ids(case) if source_id.startswith("rule:")]


def rule_drug_codes(case: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for source_id in expected_rule_source_ids(case):
        if source_id.startswith("rule:drug:"):
            code = source_id.removeprefix("rule:drug:").strip()
            if code and code not in codes:
                codes.append(code)
    return codes


def age_weight_parts(context: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    age = scalar_query_value(context.get("age"))
    if age:
        parts.extend([f"age {age}", f"{age}세"])
    weight_kg = scalar_query_value(context.get("weight_kg"))
    if weight_kg:
        parts.extend([f"weight_kg {weight_kg}", f"{weight_kg}kg"])
    return parts


def old_aug_query(base_query: str, context: dict[str, Any]) -> str:
    parts: list[Any] = [base_query, *age_weight_parts(context)]
    for item in context.get("order_details", []) or []:
        if not isinstance(item, dict):
            continue
        dose = str(item.get("dose", "")).strip()
        note = str(item.get("_note", "")).strip()
        if dose:
            parts.append(f"dose {dose}")
        if note:
            parts.append(note)
    return unique_query(parts)


def primary_order_detail(context: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    order_details = [item for item in context.get("order_details", []) or [] if isinstance(item, dict)]
    expected_codes = set(rule_drug_codes(case))
    for item in order_details:
        code = str(item.get("code", "")).strip()
        if code in expected_codes:
            return item
    if order_details:
        return order_details[0]
    orders = context.get("orders")
    if isinstance(orders, list) and orders:
        return {"code": str(orders[0]).strip()}
    return {}


def primary_order_query(base_query: str, context: dict[str, Any], case: dict[str, Any]) -> str:
    parts: list[Any] = [base_query, *age_weight_parts(context)]
    item = primary_order_detail(context, case)
    code = str(item.get("code", "")).strip()
    dose = str(item.get("dose", "")).strip()
    note = str(item.get("_note", "")).strip()
    if dose:
        parts.append(f"{code} dose {dose}" if code else f"dose {dose}")
    if note:
        parts.append(f"{code} {note}" if code else note)
    return unique_query(parts)


def oracle_expected_query(base_query: str, case: dict[str, Any]) -> str:
    parts: list[Any] = [base_query]
    parts.extend(expected_rule_source_ids(case))
    parts.extend(rule_drug_codes(case))
    return unique_query(parts)


def base_variant_specs(
    *,
    base_query: str,
    context: dict[str, Any],
    case: dict[str, Any],
    top_k: int,
    min_similarity: float,
    lexical_rerank: bool,
) -> list[dict[str, Any]]:
    current_query = augment_h2_retrieval_query(base_query, context)
    primary_query = primary_order_query(base_query, context, case)
    variants = [
        {
            "variant_id": "emr_base",
            "query": base_query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "lexical_rerank": lexical_rerank,
        },
        {
            "variant_id": "h2_old_aug",
            "query": old_aug_query(base_query, context),
            "top_k": top_k,
            "min_similarity": min_similarity,
            "lexical_rerank": lexical_rerank,
        },
        {
            "variant_id": "h2_current_aug",
            "query": current_query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "lexical_rerank": lexical_rerank,
        },
        {
            "variant_id": "primary_order_aug",
            "query": primary_query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "lexical_rerank": lexical_rerank,
        },
        {
            "variant_id": "oracle_expected_source_diag",
            "query": oracle_expected_query(base_query, case),
            "top_k": top_k,
            "min_similarity": min_similarity,
            "lexical_rerank": lexical_rerank,
        },
    ]
    for parent_id, query in (("h2_current_aug", current_query), ("primary_order_aug", primary_query)):
        for wide_top_k in (10, 20):
            variants.append(
                {
                    "variant_id": f"wide_topk_diag:{parent_id}:k{wide_top_k}",
                    "query": query,
                    "top_k": wide_top_k,
                    "min_similarity": min_similarity,
                    "lexical_rerank": lexical_rerank,
                }
            )
    for parent_id, query in (
        ("emr_base", base_query),
        ("h2_current_aug", current_query),
        ("primary_order_aug", primary_query),
    ):
        variants.append(
            {
                "variant_id": f"minsim_zero_diag:{parent_id}:k20",
                "query": query,
                "top_k": 20,
                "min_similarity": 0.0,
                "lexical_rerank": lexical_rerank,
            }
        )
    return variants


def retrieved_metadata(results: list[dict[str, Any]], expected: list[str]) -> list[dict[str, Any]]:
    expected_set = set(expected)
    rows: list[dict[str, Any]] = []
    for index, result in enumerate(results, start=1):
        source_id = str(result.get("source_id", "")).strip()
        rows.append(
            {
                "rank": index,
                "source_id": source_id,
                "similarity": result.get("similarity"),
                "lexical_overlap": result.get("lexical_overlap"),
                "is_expected": source_id in expected_set,
            }
        )
    return rows


def rank_map(retrieved: list[dict[str, Any]]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for item in retrieved:
        source_id = str(item.get("source_id", "")).strip()
        rank = int(item.get("rank", 0))
        if source_id and rank and source_id not in ranks:
            ranks[source_id] = rank
    return ranks


def hit_at_k(expected: list[str], ranks: dict[str, int], k: int) -> dict[str, Any]:
    hits = [source_id for source_id in expected if ranks.get(source_id, k + 1) <= k]
    return {
        "any": bool(hits),
        "all": bool(expected) and len(hits) == len(expected),
        "source_ids": hits,
    }


def owner_hint(expected: list[str], retrieved: list[str]) -> str:
    if not expected:
        return "no_expected_sources"
    if not retrieved:
        return "retrieval_reachability"
    if len(retrieved) == len(expected):
        return "retrieval_reached"
    return "partial_retrieval_reachability"


def summarize_variant(spec: dict[str, Any], results: list[dict[str, Any]], expected: list[str]) -> dict[str, Any]:
    retrieved = retrieved_metadata(results, expected)
    ranks = rank_map(retrieved)
    expected_retrieved = [source_id for source_id in expected if source_id in ranks]
    expected_not_retrieved = [source_id for source_id in expected if source_id not in ranks]
    return {
        **spec,
        "retrieved": retrieved,
        "expected_source_retrieved": expected_retrieved,
        "expected_source_not_retrieved": expected_not_retrieved,
        "expected_source_rank": {source_id: ranks.get(source_id) for source_id in expected},
        "hit_at_5": hit_at_k(expected, ranks, 5),
        "hit_at_10": hit_at_k(expected, ranks, 10),
        "hit_at_20": hit_at_k(expected, ranks, 20),
        "owner_hint": owner_hint(expected, expected_retrieved),
    }


def import_emr_retrieval(emr_repo: Path) -> tuple[Any, Any]:
    disable_bytecode_writes_for_emr_import()
    if str(emr_repo) not in sys.path:
        sys.path.insert(0, str(emr_repo))
    from app.llm.prompt_builder import build_retrieval_query
    from app.rag.retriever import Retriever

    return build_retrieval_query, Retriever


def selected_cases(eval_set: dict[str, Any], case_ids: list[str]) -> list[dict[str, Any]]:
    return [case_by_id(eval_set, case_id) for case_id in case_ids]


def planned_case_variants(eval_set: dict[str, Any], case: dict[str, Any], build_retrieval_query: Any) -> dict[str, Any]:
    request = request_for_case(case, dict(eval_set.get("common_options_default", {})))
    check_result = dict(request.get("check_result") or {})
    context = merge_weight_kg(dict(request.get("context") or {}), request)
    options = dict(request.get("options") or {})
    top_k = int(options.get("top_k", 5))
    min_similarity = float(options.get("min_similarity", 0.45))
    lexical_rerank = bool(options.get("lexical_rerank", False))
    base_query = build_retrieval_query(check_result, context)
    expected = expected_source_ids(case)
    return {
        "case_id": str(case.get("id", "")),
        "expected_source_ids": expected,
        "expected_rule_source_ids": expected_rule_source_ids(case),
        "variants": base_variant_specs(
            base_query=base_query,
            context=context,
            case=case,
            top_k=top_k,
            min_similarity=min_similarity,
            lexical_rerank=lexical_rerank,
        ),
    }


def run_retrieval_probe(args: argparse.Namespace) -> int:
    if not args.confirm_retrieval_only_probe and not args.dry_run:
        print("Refusing live retrieval probe without --confirm-retrieval-only-probe.", file=sys.stderr)
        return 2

    eval_set_path = Path(args.eval_set)
    emr_repo = Path(args.emr_repo)
    output_root = Path(args.output_root)
    eval_set = read_json(eval_set_path)
    case_ids = args.case_id or list(DEFAULT_CASE_IDS)

    if args.dry_run:
        print("dry-run only; no EMR retriever import, live retrieval, /explain, or LLM call was executed.")
        print(f"cases: {', '.join(case_ids)}")
        return 0

    offline_env = set_offline_embedding_env(emr_repo)
    index_paths = preflight_paths(emr_repo)
    emr_git_before = assert_clean_git(emr_repo, "EMR_AI_24clinic")
    emr_ignored_cache_before = emr_ignored_cache_snapshot(emr_repo)
    local_status_before = git_status_short(LOCAL_REPO)
    build_retrieval_query, retriever_cls = import_emr_retrieval(emr_repo)
    retriever = retriever_cls()

    cases_payload: list[dict[str, Any]] = []
    for case in selected_cases(eval_set, case_ids):
        case_payload = planned_case_variants(eval_set, case, build_retrieval_query)
        for variant in case_payload["variants"]:
            results = retriever.retrieve(
                variant["query"],
                top_k=int(variant["top_k"]),
                min_similarity=float(variant["min_similarity"]),
                lexical_rerank=bool(variant["lexical_rerank"]),
            )
            variant.update(summarize_variant(variant, results, case_payload["expected_source_ids"]))
        cases_payload.append(case_payload)

    emr_ignored_cache_after = emr_ignored_cache_snapshot(emr_repo)
    emr_ignored_cache_diff = assert_emr_ignored_cache_unchanged(
        emr_ignored_cache_before,
        emr_ignored_cache_after,
    )
    emr_git_after = assert_clean_git(emr_repo, "EMR_AI_24clinic")
    timestamp = args.timestamp or dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_dir = output_root / f"{RESULT_PREFIX}_{timestamp}"
    payload = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "local_llm_eval_head": git_head(LOCAL_REPO),
        "local_llm_eval_status_before": local_status_before,
        "emr_ai_24clinic_head": emr_git_before["head"],
        "emr_ai_24clinic_head_after": emr_git_after["head"],
        "eval_set_path": str(eval_set_path),
        "emr_repo_path": str(emr_repo),
        "index_paths": index_paths,
        "offline_mode": offline_env,
        "emr_ignored_cache_guard": {
            "paths": ["rag_index"],
            "diff": emr_ignored_cache_diff,
        },
        "cases": cases_payload,
    }
    write_outputs(result_dir, payload)
    print(result_dir)
    return 0


def write_outputs(result_dir: Path, payload: dict[str, Any]) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    json_path = result_dir / "h2_c1_retrieval_probe_results.json"
    md_path = result_dir / "h2_c1_retrieval_probe_summary.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with md_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# H2 C1 Retrieval-Only Probe\n\n")
        handle.write(f"- generated_at: `{payload['generated_at']}`\n")
        handle.write(f"- local_llm_eval_head: `{payload['local_llm_eval_head']}`\n")
        handle.write(f"- emr_ai_24clinic_head: `{payload['emr_ai_24clinic_head']}`\n")
        handle.write("- runtime: no HP Z2 / no LLM / no `/explain`\n\n")
        handle.write("| case | variant | expected retrieved | expected missing | owner hint |\n")
        handle.write("|---|---|---|---|---|\n")
        for case in payload.get("cases", []):
            for variant in case.get("variants", []):
                handle.write(
                    "| "
                    + " | ".join(
                        [
                            str(case.get("case_id", "")),
                            str(variant.get("variant_id", "")),
                            ", ".join(variant.get("expected_source_retrieved") or []) or "-",
                            ", ".join(variant.get("expected_source_not_retrieved") or []) or "-",
                            str(variant.get("owner_hint", "")),
                        ]
                    )
                    + " |\n"
                )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="H2 C1 retrieval-only probe runner.")
    parser.add_argument("--eval-set", default=str(EVAL_SET_PATH))
    parser.add_argument("--emr-repo", default=str(EMR_REPO))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--case-id", action="append", help="case id to probe; default is RA-03/RA-06/RA-07")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-retrieval-only-probe", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        return run_retrieval_probe(args)
    except ProbeConfigError as exc:
        print(f"probe config error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
