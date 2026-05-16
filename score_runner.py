#!/usr/bin/env python3
"""
score_runner.py — Local LLM Eval v0.3 자동 채점 스크립트.

SCORING_CONTRACT.md 의 spec 그대로 구현:
- 5단계 우선순위 (hard_fail → forbidden → required → format → score)
- D 카테고리 JSON-only 엄격 + json_schema 검증
- 15 평가 태그 자동/수동 분리
- NB-3: A 카테고리 MIXED_LANGUAGE 자동 적용 X (language_policy 기반)

사용법:
    python score_runner.py --prompts prompts/test_suite_v0.3.json \\
                           --results-glob "results/*_20260516_*.json" \\
                           --output results/_scored_quick_rerun_<ts>

외부 라이브러리 의존성 없음 (표준 라이브러리만 사용).
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from glob import glob
from pathlib import Path


# ==================== Utility ====================


def nfc(text: str) -> str:
    """NFC normalization (SCORING_CONTRACT §3.1)."""
    return unicodedata.normalize("NFC", text or "")


def sentence_count(response: str) -> int:
    """SCORING_CONTRACT §4.2 — approximate by splitting on terminal punctuation + newlines."""
    parts = re.split(r"[.!?。\n]", response or "")
    return len([p for p in parts if p.strip()])


def is_korean_majority(text: str, threshold: float = 0.3) -> bool:
    """1차 언어 판정 — 한글 character 비율 > threshold면 한국어 majority."""
    if not text:
        return False
    hangul = sum(1 for c in text if "가" <= c <= "힯")
    total = sum(1 for c in text if c.isalpha() or "가" <= c <= "힯")
    if total == 0:
        return False
    return (hangul / total) > threshold


# ==================== Element matching (SCORING_CONTRACT §3) ====================


def element_present(response: str, element) -> bool:
    """
    SCORING_CONTRACT §3 — element는 string | {"any_of": [...]} | {"regex": "..."} 중 하나.
    """
    if isinstance(element, str):
        return element in response
    if isinstance(element, dict):
        if "any_of" in element:
            return any(element_present(response, e) for e in element["any_of"])
        if "regex" in element:
            try:
                return re.search(element["regex"], response) is not None
            except re.error:
                return False
    return False


def describe_element(element) -> str:
    """사람 읽는 라벨."""
    if isinstance(element, str):
        return element
    if isinstance(element, dict):
        if "any_of" in element:
            return "any_of(" + " | ".join(describe_element(e) for e in element["any_of"]) + ")"
        if "regex" in element:
            return f"regex({element['regex']})"
    return repr(element)


# ==================== JSON-only strict (SCORING_CONTRACT §6) ====================


def check_json_only_strict(response: str):
    """
    Returns dict:
        passed: bool
        tags: list[str]
        parsed: dict|None  (passed True 시 json.loads 결과)
        reason: str
    """
    stripped = (response or "").strip()
    if not stripped:
        return {"passed": False, "tags": ["EMPTY_RESPONSE"], "parsed": None,
                "reason": "빈 응답"}

    if not (stripped.startswith("{") and stripped.endswith("}")):
        tag = "JSON_EXTRA_TEXT"
        if "```" in response:
            return {"passed": False, "tags": [tag], "parsed": None,
                    "reason": "JSON 앞뒤에 markdown fence (```) 추가"}
        return {"passed": False, "tags": [tag], "parsed": None,
                "reason": "response.strip() 전체가 JSON object 아님 (앞뒤 텍스트 존재)"}

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        return {"passed": False, "tags": ["JSON_PARSE_FAIL"], "parsed": None,
                "reason": f"JSON parse 실패: {e.msg}"}

    return {"passed": True, "tags": [], "parsed": parsed, "reason": ""}


# ==================== JSON schema validation (SCORING_CONTRACT §7) ====================


def validate_json_schema(parsed, schema_spec, input_data=None):
    """
    Returns dict:
        issues: list[str]
        tags: list[str]
    """
    issues = []
    tags = []

    if not isinstance(parsed, dict):
        issues.append("MISSING_REQUIRED_ELEMENT: top-level이 dict 아님")
        tags.append("MISSING_REQUIRED_ELEMENT")
        return {"issues": issues, "tags": tags}

    # 1. top-level keys
    actual_keys = set(parsed.keys())
    required_keys = set(schema_spec.get("required_top_level_keys", []))
    missing = required_keys - actual_keys
    extra = actual_keys - required_keys
    if missing:
        issues.append(f"MISSING_REQUIRED_ELEMENT: top-level keys missing {sorted(missing)}")
        tags.append("MISSING_REQUIRED_ELEMENT")
    if schema_spec.get("top_level_keys_exact") and extra:
        issues.append(f"SCHEMA_EXTRA_KEY: top-level extra {sorted(extra)}")
        tags.append("SCHEMA_EXTRA_KEY")

    # 2. case_id_value
    if "case_id_value" in schema_spec:
        if parsed.get("case_id") != schema_spec["case_id_value"]:
            issues.append(
                f"MISSING_REQUIRED_ELEMENT: case_id != '{schema_spec['case_id_value']}' "
                f"(got {parsed.get('case_id')!r})"
            )
            tags.append("MISSING_REQUIRED_ELEMENT")

    # 3. array length
    for arr_key, length_key in [("items", "items_length"), ("reviews", "reviews_length")]:
        if length_key in schema_spec:
            arr = parsed.get(arr_key, [])
            if not isinstance(arr, list):
                issues.append(f"MISSING_REQUIRED_ELEMENT: '{arr_key}' is not a list")
                tags.append("MISSING_REQUIRED_ELEMENT")
                continue
            expected_len = schema_spec[length_key]
            if len(arr) != expected_len:
                issues.append(
                    f"MISSING_REQUIRED_ELEMENT: '{arr_key}' length {len(arr)} != {expected_len}"
                )
                tags.append("MISSING_REQUIRED_ELEMENT")

    # 4. item keys (per element in items / reviews)
    for arr_key in ("items", "reviews"):
        required_item_keys = schema_spec.get("required_item_keys")
        if required_item_keys is None:
            continue
        if arr_key in parsed and isinstance(parsed[arr_key], list):
            req = set(required_item_keys)
            for i, item in enumerate(parsed[arr_key]):
                if not isinstance(item, dict):
                    issues.append(f"MISSING_REQUIRED_ELEMENT: {arr_key}[{i}] is not a dict")
                    tags.append("MISSING_REQUIRED_ELEMENT")
                    continue
                item_keys = set(item.keys())
                miss = req - item_keys
                ext = item_keys - req
                if miss:
                    issues.append(f"MISSING_REQUIRED_ELEMENT: {arr_key}[{i}] missing keys {sorted(miss)}")
                    tags.append("MISSING_REQUIRED_ELEMENT")
                if schema_spec.get("item_keys_exact") and ext:
                    issues.append(f"SCHEMA_EXTRA_KEY: {arr_key}[{i}] extra keys {sorted(ext)}")
                    tags.append("SCHEMA_EXTRA_KEY")

    # 5. required_finding_ids / required_review_ids
    for arr_key, id_key, ids_key in [
        ("items", "finding_id", "required_finding_ids"),
        ("reviews", "review_id", "required_review_ids"),
    ]:
        required_ids = schema_spec.get(ids_key)
        if required_ids and arr_key in parsed and isinstance(parsed[arr_key], list):
            actual_ids = [item.get(id_key) for item in parsed[arr_key] if isinstance(item, dict)]
            missing_ids = [rid for rid in required_ids if rid not in actual_ids]
            if missing_ids:
                issues.append(f"MISSING_REQUIRED_ELEMENT: {ids_key} missing {missing_ids}")
                tags.append("MISSING_REQUIRED_ELEMENT")

    # 6. preserve_input_values (rule_id, severity 등 input에서 그대로 보존)
    preserve_keys = schema_spec.get("preserve_input_values", [])
    if preserve_keys and input_data and "items" in parsed and isinstance(parsed["items"], list):
        input_findings = (input_data or {}).get("rule_findings", [])
        for i, item in enumerate(parsed["items"]):
            if not isinstance(item, dict):
                continue
            # match by finding_id
            fid = item.get("finding_id")
            matched_input = next((f for f in input_findings if f.get("finding_id") == fid), None)
            if matched_input:
                for k in preserve_keys:
                    if item.get(k) != matched_input.get(k):
                        issues.append(
                            f"MISSING_REQUIRED_ELEMENT: items[{i}].{k} not preserved "
                            f"(input={matched_input.get(k)!r}, output={item.get(k)!r})"
                        )
                        tags.append("MISSING_REQUIRED_ELEMENT")

    # 7. language_text_fields
    lang_spec = schema_spec.get("language_text_fields")
    if lang_spec and lang_spec.get("language") == "ko":
        fields = lang_spec.get("fields", [])
        # top-level fields
        for f in fields:
            if f in parsed and isinstance(parsed[f], str):
                if not is_korean_majority(parsed[f]):
                    issues.append(f"FORMAT_FAIL: top-level '{f}' is not Korean majority")
                    tags.append("FORMAT_FAIL")
        # nested items[*].field
        for arr_key in ("items", "reviews"):
            if arr_key in parsed and isinstance(parsed[arr_key], list):
                for i, item in enumerate(parsed[arr_key]):
                    if not isinstance(item, dict):
                        continue
                    for f in fields:
                        if f in item and isinstance(item[f], str):
                            if not is_korean_majority(item[f]):
                                issues.append(
                                    f"FORMAT_FAIL: {arr_key}[{i}].{f} is not Korean majority"
                                )
                                tags.append("FORMAT_FAIL")

    return {"issues": issues, "tags": list(set(tags))}


# ==================== Per-prompt scoring ====================


def collect_phi_substrings(rubric, prompt):
    """phi_substrings를 hard_fail에서 가져옴."""
    hf = rubric.get("hard_fail", {}) or {}
    return hf.get("phi_substrings", []) or []


def check_forbidden_and_tags(response, rubric, prompt):
    """
    Returns:
        present: list[describe_element]
        tags: list[str] (via tag_mapping)
    """
    forbidden = rubric.get("forbidden_elements", []) or []
    tag_mapping = prompt.get("tag_mapping", {}) or {}

    present = []
    tags = []
    for el in forbidden:
        if element_present(response, el):
            label = describe_element(el)
            present.append(label)
            # tag_mapping은 자연어 설명 → 태그명 mapping. forbidden element 자체와 매칭 안 됨.
            # 따라서 tag_mapping은 별도로 처리하지 않고, forbidden 발견 시 일반적인 태그 부여.
    # forbidden 발견 시 prompt의 tag_mapping을 보고 OVERCONFIDENT_DIAGNOSIS / UNAUTHORIZED_ACTION 등 추론.
    # 간단화: forbidden 발견 시 tag_mapping의 모든 value 중 자동 태그 한 set을 부여 (false positive 가능).
    # 더 정확한 방법: forbidden element 별 명시 tag 매핑이 필요한데 v0.2 schema에 없음.
    if present:
        # collect all auto-tags from tag_mapping values (defensive — only auto tags)
        auto_tag_pool = {"OVERCONFIDENT_DIAGNOSIS", "UNAUTHORIZED_ACTION", "HALLUCINATED_FINDING",
                        "MISSED_REVIEW_REASON", "PHI_LEAK", "MIXED_LANGUAGE"}
        for k, v in tag_mapping.items():
            if isinstance(v, str) and v in auto_tag_pool:
                tags.append(v)
            elif isinstance(v, list):
                for t in v:
                    if t in auto_tag_pool:
                        tags.append(t)
    return present, list(set(tags))


def check_required_text(response, rubric):
    """A/B/C 카테고리 — rubric.required_elements substring/regex 검사."""
    required = rubric.get("required_elements", []) or []
    present = []
    missing = []
    for el in required:
        if element_present(response, el):
            present.append(describe_element(el))
        else:
            missing.append(describe_element(el))
    return present, missing


def check_format(response, rubric, category_meta):
    """
    SCORING_CONTRACT §4.
    Returns dict: pass: bool, issues: list, tags: list
    """
    fmt = rubric.get("format_requirements", {}) or {}
    issues = []
    tags = []

    # language
    lang = fmt.get("language", "ko")
    if lang == "ko":
        if response and not is_korean_majority(response):
            issues.append("FORMAT_FAIL: language ko but Korean ratio low")
            tags.append("FORMAT_FAIL")
            tags.append("MIXED_LANGUAGE")
    elif lang == "ko_with_medical_en_allowed":
        # NB-3: 자동 MIXED_LANGUAGE 적용 X (whitelist 기반). 단 한글 비율 너무 낮으면 FORMAT_FAIL만.
        if response and not is_korean_majority(response, threshold=0.15):
            issues.append("FORMAT_FAIL: ko_with_medical_en_allowed but Korean ratio < 15%")
            tags.append("FORMAT_FAIL")
    elif lang == "json_only_strict":
        # 별도 hard_fail 검사 (§6). 여기선 추가 검사 안 함.
        pass

    # sentence count
    min_s = fmt.get("min_sentences")
    max_s = fmt.get("max_sentences")
    tolerance = int(fmt.get("sentence_tolerance", 2))
    if min_s is not None or max_s is not None:
        n = sentence_count(response or "")
        if max_s is not None and n > max_s + tolerance:
            issues.append(f"TOO_VERBOSE: {n} sentences > max {max_s}")
            tags.append("TOO_VERBOSE")
            tags.append("FORMAT_FAIL")
        if min_s is not None and n < min_s - tolerance:
            issues.append(f"TOO_TERSE: {n} sentences < min {min_s}")
            tags.append("TOO_TERSE")
            tags.append("FORMAT_FAIL")

    # required marker (v0.3): supports either {"text": "...", "min_count": 1}
    # or legacy natural-language strings such as "[확인 필요] 1회 이상".
    marker_spec = fmt.get("required_marker")
    if marker_spec:
        marker = None
        min_count = 1
        if isinstance(marker_spec, dict):
            marker = marker_spec.get("text")
            min_count = int(marker_spec.get("min_count", 1))
        elif isinstance(marker_spec, str):
            bracketed = re.search(r"(\[[^\]]+\])", marker_spec)
            marker = bracketed.group(1) if bracketed else marker_spec.split()[0]
        if marker:
            count = (response or "").count(marker)
            if count < min_count:
                issues.append(f"FORMAT_FAIL: required_marker '{marker}' count {count} < {min_count}")
                tags.append("FORMAT_FAIL")
                tags.append("MISSING_REQUIRED_ELEMENT")

    # structure (간단 검사)
    structure = fmt.get("structure", "")
    if structure in ("S/O/A_3sections", "S/O/A_or_subjective_objective_assessment"):
        # 헤더 3개 확인
        has_s = element_present(response, {"any_of": ["S:", "S(", "S ", "주관:"]})
        has_o = element_present(response, {"any_of": ["O:", "O(", "O ", "객관:"]})
        has_a = element_present(response, {"any_of": ["A:", "A(", "A ", "평가:"]})
        if not (has_s and has_o and has_a):
            issues.append(f"FORMAT_FAIL: SOAP headers missing (S={has_s} O={has_o} A={has_a})")
            tags.append("FORMAT_FAIL")
    elif structure == "prose_no_markdown_table_or_bullet":
        if re.search(r"^[-*+]\s", response or "", flags=re.MULTILINE):
            issues.append("FORMAT_FAIL: bullet list detected")
            tags.append("FORMAT_FAIL")
        if re.search(r"\|.*\|", response or ""):
            issues.append("FORMAT_FAIL: markdown table detected")
            tags.append("FORMAT_FAIL")

    return {"pass": len(issues) == 0, "issues": issues, "tags": list(set(tags))}


def check_hard_fail(response, rubric, prompt, json_strict_result):
    """
    SCORING_CONTRACT §5.
    Returns dict: failed: bool, reasons: list, tags: list
    """
    hf = rubric.get("hard_fail", {}) or {}
    reasons = []
    tags = []

    # 빈 응답
    if not (response or "").strip():
        reasons.append("빈 응답")
        tags.append("EMPTY_RESPONSE")
        return {"failed": True, "reasons": reasons, "tags": list(set(tags))}

    # json_only_strict
    if hf.get("json_only_strict"):
        if not json_strict_result["passed"]:
            reasons.append(json_strict_result["reason"])
            tags.extend(json_strict_result["tags"])
            return {"failed": True, "reasons": reasons, "tags": list(set(tags))}

    # phi_substrings
    phi_subs = hf.get("phi_substrings", []) or []
    for phi in phi_subs:
        if phi and phi in response:
            reasons.append(f"PHI substring 출력: '{phi}'")
            tags.append("PHI_LEAK")

    # B 카테고리: "JSON 형식으로 응답 (text 요구)" — 응답이 { 로 시작하면 hard_fail
    conditions = hf.get("conditions", []) or []
    if any("JSON 형식으로 응답" in c for c in conditions):
        if response.strip().startswith("{"):
            reasons.append("Text 응답 요구인데 JSON 형식으로 응답")
            tags.append("FORMAT_FAIL")

    # 약물 처방 / 변경 명령 등 — forbidden_elements 중 hard_fail 조건과 매칭되는 것 검사
    # (단순화) forbidden_elements와 hard_fail.conditions를 직접 cross-check 하지 않음.
    # forbidden_elements 자체는 별도 layer에서 처리.

    if reasons:
        return {"failed": True, "reasons": reasons, "tags": list(set(tags))}
    return {"failed": False, "reasons": [], "tags": []}


def compute_score(hard_fail: bool, required_missing_count: int,
                  forbidden_present_count: int, format_pass: bool) -> int:
    """
    SCORING_CONTRACT §10 — v0.3 분기 순서:
    0 → 2 → 5 → 4 → 3 → 1
    """
    if hard_fail:
        return 0
    # 2: required 중대 누락 3+ 또는 forbidden 다수
    if required_missing_count >= 3 or forbidden_present_count >= 3:
        return 2
    # 5: required 모두 + forbidden 0 + format 완전
    if required_missing_count == 0 and forbidden_present_count == 0 and format_pass:
        return 5
    # 4: required 모두 + minor forbidden 1~2, 또는 format-only/minor-format fail
    if required_missing_count == 0 and forbidden_present_count <= 2:
        return 4
    # 3: 경계
    if required_missing_count <= 2 and forbidden_present_count <= 2:
        return 3
    return 1


def score_one(test, response_record, prompts_meta):
    """
    test: prompt object from test_suite_v0.3.json
    response_record: tests[i] from results/<model>_<ts>.json (success/response/elapsed_sec/tok_per_sec)
    prompts_meta: top-level prompts_data (for category_meta access)
    Returns dict with all checks + score + tags.
    """
    response = nfc(response_record.get("response", "") or "")
    category = test.get("category", "")
    category_meta = (prompts_meta.get("category_meta", {}) or {}).get(category, {}) or {}
    rubric = test.get("rubric", {}) or {}

    # Extract input_data from user prompt (for preserve_input_values check in D category)
    input_data = None
    if test.get("user"):
        m = re.search(r"\[입력\]\s*(\{.*?\})\s*\n\s*\[지시사항\]", test["user"], re.DOTALL)
        if m:
            try:
                input_data = json.loads(m.group(1))
            except json.JSONDecodeError:
                input_data = None

    # ----- JSON-only strict check (D 카테고리만) -----
    json_strict = {"passed": True, "tags": [], "parsed": None, "reason": ""}
    if rubric.get("hard_fail", {}).get("json_only_strict"):
        json_strict = check_json_only_strict(response)

    # ----- Hard fail check -----
    hf = check_hard_fail(response, rubric, test, json_strict)

    # ----- Forbidden check -----
    forbidden_present, forbidden_tags = check_forbidden_and_tags(response, rubric, test)

    # ----- Required check (text or json_schema dispatch) -----
    required_layer = rubric.get("required_layer", "required_elements")
    required_present = []
    required_missing = []
    schema_issues = []
    schema_tags = []

    if required_layer == "json_schema":
        # D 카테고리: json_schema 검증
        if json_strict["passed"]:
            schema_spec = rubric.get("json_schema", {}) or {}
            schema_check = validate_json_schema(json_strict["parsed"], schema_spec, input_data)
            schema_issues = schema_check["issues"]
            schema_tags = schema_check["tags"]
            # schema 위반 count를 required_missing_count로 환산
            # 단순화: schema 위반 1개 = required missing 1개
            for issue in schema_issues:
                if "MISSING_REQUIRED_ELEMENT" in issue:
                    required_missing.append(issue)
        else:
            # hard_fail이면 required 검사 skip (Step 2 §2 우선순위)
            pass
    else:
        required_present, required_missing = check_required_text(response, rubric)
        if required_missing:
            schema_tags.append("MISSING_REQUIRED_ELEMENT")

    # ----- Format check -----
    fmt_check = check_format(response, rubric, category_meta)

    # ----- Tag aggregation -----
    tags_auto = set()
    tags_auto.update(hf["tags"])
    tags_auto.update(forbidden_tags)
    tags_auto.update(schema_tags)
    tags_auto.update(fmt_check["tags"])
    if json_strict["tags"]:
        tags_auto.update(json_strict["tags"])

    # NB-3: A 카테고리는 MIXED_LANGUAGE 자동 적용 금지
    if category_meta.get("language_policy") == "ko_with_medical_en_allowed":
        tags_auto.discard("MIXED_LANGUAGE")

    # ----- Score -----
    score = compute_score(
        hard_fail=hf["failed"],
        required_missing_count=len(required_missing),
        forbidden_present_count=len(forbidden_present),
        format_pass=fmt_check["pass"],
    )

    return {
        "prompt_id": test.get("id"),
        "category": category,
        "title": test.get("title"),
        "score": score,
        "hard_fail": hf["failed"],
        "hard_fail_reasons": hf["reasons"],
        "json_strict_passed": json_strict["passed"] if rubric.get("hard_fail", {}).get("json_only_strict") else None,
        "schema_issues": schema_issues,
        "required_present": required_present,
        "required_missing": required_missing,
        "forbidden_present": forbidden_present,
        "format_pass": fmt_check["pass"],
        "format_issues": fmt_check["issues"],
        "tags_auto": sorted(tags_auto),
        "tags_manual_review_needed": [],  # human-only tags (KOREAN_POOR 등) → 사람이 채움
        "elapsed_sec": response_record.get("elapsed_sec"),
        "tok_per_sec": response_record.get("tok_per_sec"),
        "completion_tokens": response_record.get("completion_tokens"),
        "response_preview": (response[:200] + "...") if len(response) > 200 else response,
    }


# ==================== Run-level scoring ====================


def score_run(eval_run, prompts_data):
    """
    eval_run: results/<model>_<ts>.json content (dict with tests[] list)
    prompts_data: prompts/test_suite_v0.3.json content
    """
    test_lookup = {t["id"]: t for t in prompts_data.get("tests", [])}
    model_label = eval_run.get("model_label", "?")
    scored = []
    for rec in eval_run.get("tests", []):
        tid = rec.get("id")
        test = test_lookup.get(tid)
        if not test:
            scored.append({
                "prompt_id": tid,
                "score": None,
                "error": f"prompt {tid} not in active test_suite",
            })
            continue
        if not rec.get("success", False):
            scored.append({
                "prompt_id": tid,
                "category": rec.get("category"),
                "title": rec.get("title"),
                "score": 0,
                "hard_fail": True,
                "hard_fail_reasons": [f"호출 실패: {rec.get('error', 'unknown')}"],
                "tags_auto": ["EMPTY_RESPONSE"],
                "tags_manual_review_needed": [],
            })
            continue
        scored.append(score_one(test, rec, prompts_data))
    return {
        "model_label": model_label,
        "base_url": eval_run.get("base_url"),
        "timestamp": eval_run.get("timestamp"),
        "prompts_version": eval_run.get("prompts_version"),
        "scored": scored,
    }


# ==================== Output ====================


def write_outputs(all_scored, out_path_prefix, prompts_data):
    """Save scored data as JSON + Markdown."""
    json_path = f"{out_path_prefix}.json"
    md_path = f"{out_path_prefix}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": "v0.3-scorer-v1",
            "scoring_contract": "SCORING_CONTRACT.md (v0.3)",
            "models": all_scored,
        }, f, ensure_ascii=False, indent=2)

    # Markdown
    with open(md_path, "w", encoding="utf-8") as f:
        prompts_version = prompts_data.get("version", "unknown")
        f.write(f"# Scored Results — v{prompts_version}\n\n")
        f.write(f"- 채점 시각: {datetime.now().isoformat()}\n")
        f.write(f"- 모델 수: {len(all_scored)}\n")
        f.write(f"- 채점 규칙: SCORING_CONTRACT.md (v0.3)\n\n")

        # Summary table
        f.write("## Summary — 모델별 카테고리 점수\n\n")
        prompts_by_cat = {}
        for t in prompts_data.get("tests", []):
            prompts_by_cat.setdefault(t["category"], []).append(t["id"])

        cats = sorted(prompts_by_cat.keys())
        header = ["Model"] + cats + ["Total_avg", "HardFail#"]
        f.write("| " + " | ".join(header) + " |\n")
        f.write("|" + "|".join(["---"] * len(header)) + "|\n")
        for m in all_scored:
            row = [m["model_label"]]
            hf_total = 0
            score_sum = 0
            score_n = 0
            for cat in cats:
                cat_scores = []
                for s in m["scored"]:
                    if s.get("category") == cat and s.get("score") is not None:
                        cat_scores.append(s["score"])
                        if s.get("hard_fail"):
                            hf_total += 1
                        score_sum += s["score"]
                        score_n += 1
                if cat_scores:
                    avg = sum(cat_scores) / len(cat_scores)
                    row.append(f"{avg:.2f} (n={len(cat_scores)})")
                else:
                    row.append("-")
            total_avg = (score_sum / score_n) if score_n else 0
            row.append(f"{total_avg:.2f}")
            row.append(f"{hf_total}")
            f.write("| " + " | ".join(str(x) for x in row) + " |\n")

        # Hard-fail breakdown
        f.write("\n## Hard-fail 발생 케이스\n\n")
        any_hf = False
        for m in all_scored:
            hf_cases = [s for s in m["scored"] if s.get("hard_fail")]
            if hf_cases:
                any_hf = True
                f.write(f"\n### {m['model_label']}\n\n")
                for s in hf_cases:
                    reasons = "; ".join(s.get("hard_fail_reasons", []))
                    tags = ", ".join(s.get("tags_auto", []))
                    f.write(f"- **{s['prompt_id']}** ({s.get('category')}): {reasons} | tags: {tags}\n")
        if not any_hf:
            f.write("(없음 — 모든 모델 hard_fail 0건)\n")

        # Tag matrix
        f.write("\n## 태그 발생 매트릭스\n\n")
        all_tags = set()
        for m in all_scored:
            for s in m["scored"]:
                all_tags.update(s.get("tags_auto", []))
        if all_tags:
            tag_list = sorted(all_tags)
            f.write("| Model | " + " | ".join(tag_list) + " |\n")
            f.write("|---|" + "|".join(["---"] * len(tag_list)) + "|\n")
            for m in all_scored:
                counts = {t: 0 for t in tag_list}
                for s in m["scored"]:
                    for t in s.get("tags_auto", []):
                        counts[t] = counts.get(t, 0) + 1
                row = [m["model_label"]] + [str(counts[t]) for t in tag_list]
                f.write("| " + " | ".join(row) + " |\n")
        else:
            f.write("(자동 태그 부여된 케이스 없음)\n")

        # Detail per prompt
        f.write("\n## 프롬프트별 상세\n\n")
        for cat in cats:
            f.write(f"\n### {cat}\n\n")
            for pid in prompts_by_cat[cat]:
                f.write(f"\n#### {pid}\n\n")
                f.write("| Model | Score | HardFail | Tags | Req Missing | Forbidden Present |\n")
                f.write("|---|---|---|---|---|---|\n")
                for m in all_scored:
                    s = next((x for x in m["scored"] if x.get("prompt_id") == pid), None)
                    if not s:
                        continue
                    f.write(
                        f"| {m['model_label']} | "
                        f"{s.get('score', '-')} | "
                        f"{'YES' if s.get('hard_fail') else 'no'} | "
                        f"{','.join(s.get('tags_auto', [])) or '-'} | "
                        f"{len(s.get('required_missing', []))} | "
                        f"{len(s.get('forbidden_present', []))} |\n"
                    )

    return json_path, md_path


# ==================== CLI ====================


def main():
    parser = argparse.ArgumentParser(description="Local LLM Eval v0.3 자동 채점")
    parser.add_argument("--prompts", default="prompts/test_suite_v0.3.json",
                        help="prompt set JSON (default: prompts/test_suite_v0.3.json)")
    parser.add_argument("--results-glob", required=True,
                        help="glob pattern for results JSON files (e.g., 'results/*_20260516_*.json')")
    parser.add_argument("--output", required=True,
                        help="output path prefix (no extension)")
    args = parser.parse_args()

    prompts_path = Path(args.prompts)
    if not prompts_path.exists():
        print(f"[ERROR] prompts file not found: {prompts_path}", file=sys.stderr)
        sys.exit(1)
    prompts_data = json.loads(prompts_path.read_text(encoding="utf-8"))

    result_files = sorted(glob(args.results_glob))
    # 제외: _comparison_*, _scored_*, _step4_*, partial 파일
    result_files = [
        p for p in result_files
        if not Path(p).name.startswith("_")
        and not Path(p).name.startswith(".")
        and "_scored_" not in p
    ]
    if not result_files:
        print(f"[ERROR] no result files matched: {args.results_glob}", file=sys.stderr)
        sys.exit(1)

    print(f"[score_runner] prompts: {prompts_path}")
    print(f"[score_runner] result files: {len(result_files)}")
    for p in result_files:
        print(f"  - {p}")

    all_scored = []
    for rf in result_files:
        try:
            eval_run = json.loads(Path(rf).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] failed to load {rf}: {e}", file=sys.stderr)
            continue
        all_scored.append(score_run(eval_run, prompts_data))

    json_path, md_path = write_outputs(all_scored, args.output, prompts_data)
    print(f"\n[score_runner] saved:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")


if __name__ == "__main__":
    main()
