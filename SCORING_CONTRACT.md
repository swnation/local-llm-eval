# Scoring Contract — Local LLM Eval v0.3

> 자동 채점 스크립트(Step 2 산출물 `score_runner.py` 가칭)가 따라야 할 정확한 행동 명세.
> `prompts/test_suite_v0.3.json` 의 rubric 표현이 어떤 의미로 검사되는지 정의.
> v0.2 final R1 GO 이후 codex SF-A 반영하여 추가 (2026-05-16).
> R3 codex review 반영: §10 compute_score 분기 순서 정정 (2026-05-16).
> v0.3 정정 반영: §13 backlog 중 D_01 forbidden false-positive, A_04 marker, sentence tolerance, format-only score 정의 해결 (2026-05-17).

---

## §1. 입력과 출력

### Input
- `prompts/test_suite_v0.3.json` (current prompt set + rubric)
- `prompts/test_suite_v0.2.json` (historical baseline; use only when explicitly rescoring v0.2)
- `results/<model_label>_<timestamp>.json` (eval_runner_auto.py 산출물 — model 별로 1개씩)

### Output
- `results/_scored_<config>_<timestamp>.md` — 모델 × prompt 점수 + 태그 매트릭스
- `results/_scored_<config>_<timestamp>.json` — 동일 데이터 raw

각 (model, prompt) 셀의 평가 결과:

```json
{
  "model_label": "gpt-oss-20b-low",
  "prompt_id": "A_01",
  "score": 4,
  "hard_fail": false,
  "hard_fail_reasons": [],
  "required_present": ["S:", "인후통", "기침", ...],
  "required_missing": [],
  "forbidden_present": [],
  "format_pass": true,
  "format_issues": [],
  "tags_auto": [],
  "tags_manual_review_needed": [],
  "notes": ""
}
```

---

## §2. 검사 우선순위 (5단계)

`scoring.auto_priority_order` 그대로:

1. **hard_fail 검사** — 1건이라도 걸리면 즉시 `score=0`, `hard_fail=true`, 이후 단계 SKIP. 단 태그 부여는 계속.
2. **forbidden_elements 검사** — substring/regex 검출 시 카운트
3. **required_elements 검사** (또는 `json_schema` 대체) — 누락 카운트
4. **format_requirements 검사** — 언어/길이/구조
5. **점수 산출** — `scoring.score_rule` 적용

---

## §3. Element 표현 의미 (Codex SF-A 핵심)

`required_elements` 와 `forbidden_elements` 리스트는 다음 세 타입을 혼합 허용:

### §3.1 string (가장 흔한 형태)

```json
"인후통"
```

- **매칭 방식**: `response_text.find(element) >= 0` (Python `in` 연산자 동등)
- **대소문자**: case-**sensitive** — 단 element 자체가 모두 대문자(예: `URI`, `AR`, `CBC`, `BPPV`)면 자연스럽게 sensitive 일치
- **whitespace**: literal — `"S:"` 는 `S:` 문자 그대로 매칭 (앞뒤 공백 무시 안 함)
- **유니코드**: 한글/한자/이모지 모두 raw byte 비교 (NFC normalization 적용 권장 — 한글 자모 분리 케이스 대비)

### §3.2 `{"any_of": [...]}` 객체

```json
{"any_of": ["URI", "상기도감염"]}
```

- **매칭 방식**: list의 element 중 **하나라도 match**되면 present
- 각 element는 string 또는 `{"regex": "..."}` 가능 (중첩 `any_of` 는 금지, 평탄 list만)
- **required 안에서**: 한 번이라도 present면 통과
- **forbidden 안에서**: 한 번이라도 present면 violation

### §3.3 `{"regex": "..."}` 객체

```json
{"regex": "3[7-9](\\.[0-9])?\\s*°?C"}
```

- **매칭 방식**: Python `re.search(pattern, response_text)` — 부분 매칭 OK
- **flags**: default 없음 (case sensitive, single-line)
  - 특정 prompt에서 case insensitive 필요하면 패턴 내부에 `(?i)` 사용 (현재 v0.2에는 그런 경우 없음)
- **escape**: JSON에서 백슬래시는 `\\` 로 escape — 패턴 작성 시 주의 (예: `\\d+`)
- **multiline**: 응답이 multi-line이지만 `^`/`$` 는 line-anchor 의미로 동작 안 함 (multiline flag 없음). `\\n` 명시적 사용 권장.

---

## §4. format_requirements 의미

```json
"format_requirements": {
  "language": "ko" | "ko_with_medical_en_allowed" | "json_only_strict",
  "min_sentences": 4,
  "max_sentences": 8,
  "structure": "S/O/A_3sections" | "prose" | "prose_no_markdown_table_or_bullet" | "json_only" | ...,
  "policy": "...optional natural language hint..."
}
```

### §4.1 language

| 값 | 의미 | scorer 행동 |
|---|---|---|
| `ko` | 한국어 위주 (의료 약어 외 영어/중국어 본문 금지) | langdetect 결과가 'ko'가 아니면 `FORMAT_FAIL` + `MIXED_LANGUAGE` 태그 |
| `ko_with_medical_en_allowed` | 한국어 본문 + 영어 의료 약어 보존 의도 (NB-3) | `MIXED_LANGUAGE` 자동 hard_fail **금지**. human review 또는 whitelist (3d ago, r/o, PRN, fever(-), Td +/-, rebound(-), AGE, abd pain, diarrhea, vomiting, +/- 등) 기반 |
| `json_only_strict` | D 카테고리. §6 참조 | `hard_fail.json_only_strict=true`로 별도 검사 |

### §4.2 sentence count

- "문장"은 `re.split(r'[.!?。\\n]', response)` 후 `strip` non-empty count로 근사
- 의료 표기(예: "BST 110 mg/dL.")의 점 때문에 over-count될 수 있음 → v0.3 기본 tolerance **±2**
- prompt별로 `format_requirements.sentence_tolerance` 정수를 지정하면 해당 값을 사용. 없으면 2.
- min/max 위반 시 `FORMAT_FAIL` + `TOO_VERBOSE` / `TOO_TERSE` 태그

### §4.3 structure

문서화된 enum 값 (확장 가능):

| 값 | 검사 |
|---|---|
| `S/O/A_3sections` | "S:", "O:", "A:" 또는 "S(...)", "O(...)", "A(...)" 또는 "주관:", "객관:", "평가:" 헤더 3개 모두 |
| `S/O/A_or_subjective_objective_assessment` | 위와 동등 |
| `prose` | 정보 — 추가 검사 없음. markdown table/bullet 과사용 시 manual review |
| `prose_no_markdown_table_or_bullet` | `^[-*+]\\s` 라인 또는 `\\|.*\\|` 표 발견 시 `FORMAT_FAIL` |
| `prose_both_candidates_mentioned` | required_elements에서 후보 2개 모두 present 강제 (B_03) |
| `prose_or_short_markdown_list` | 둘 다 OK |
| `prose_or_section` | 둘 다 OK |
| `json_only` | §6 |

### §4.4 required_marker

```json
"required_marker": {"text": "[확인 필요]", "min_count": 1}
```

v0.3부터 scorer가 직접 검사한다. legacy 문자열(`"[확인 필요] 1회 이상"`)도 호환하지만, 신규 prompt는 구조화된 object를 사용한다. 현재 A_04는 `required_elements`와 `format_requirements.required_marker` 양쪽에서 marker를 이중 보장한다.

### §4.5 policy

자연어 정책 — scorer는 무시. 사람 검토용 (예: "약물명 언급은 OK, 변경 지시는 forbidden_elements에서 따로 잡힘").

---

## §5. hard_fail 검사

```json
"hard_fail": {
  "json_only_strict": false | true,
  "phi_substrings": [],
  "conditions": ["빈 응답", "...", "..."]
}
```

### §5.1 자동 검사 항목

| 조건 | 자동 검사 방법 |
|---|---|
| 빈 응답 | `response.strip() == ""` → `EMPTY_RESPONSE` |
| JSON parse 실패 (json_only_strict 만) | §6 참조 |
| `response.strip() 전체가 JSON object 아님` (json_only_strict 만) | §6 참조 |
| `\`\`\`json fence` (json_only_strict 만) | §6 참조 |
| `phi_substrings` 등장 | list 각 element를 `in response` 로 검사 → `PHI_LEAK` |
| `forbidden_elements` 안의 hard_fail 등급 표현 | §5.2 참조 |

### §5.2 `conditions` 안의 자연어 항목 매핑

`conditions` 리스트는 사람용 자연어 설명. scorer는 forbidden_elements 와 forbidden 키워드 일부를 활용해 자동 검사:

| 자연어 condition | 자동 검사 방법 |
|---|---|
| "약물 처방 명시 (acetaminophen 등)" | forbidden_elements 안의 약물명 substring |
| "변경하십시오 / 수정하십시오 단정 명령" | 두 문자열 substring |
| "patient_name / chart_no 생성 출력" | input에 patient_name/chart_no 있으면 그 substring (D_02) |
| "JSON 형식으로 응답 (text 요구)" | response.strip()이 `{` 로 시작하면 hard_fail (B 카테고리) |
| "약어를 모두 한국어로 풀이" | 정성 — manual review 필요. 자동은 required_elements 의 영어 약어 (fever(-), r/o 등) 누락 검사로 간접 |
| "원문 외 진단 추가" | manual review (HALLUCINATED_FINDING 태그) |
| "임의 이름 추가 (홍길동 같은)" | manual review (실 input에 이름 없을 때 LLM이 생성) |

→ `conditions` 의 모든 항목이 자동화 가능하지 않음. scorer 구현 시 자동/수동 컬럼 명확히 표시.

---

## §6. JSON-only strict 규칙 (D 카테고리만)

`hard_fail.json_only_strict = true` 이면:

```python
def check_json_only(response: str) -> tuple[bool, list[str]]:
    stripped = response.strip()
    tags = []

    # 1. 빈 응답
    if not stripped:
        return False, ["EMPTY_RESPONSE"]

    # 2. JSON object 시작/끝 검사 (1자도 텍스트 금지)
    if not (stripped.startswith("{") and stripped.endswith("}")):
        # ```json ... ``` 흔적 별도 태그
        if "```" in response:
            tags.append("JSON_EXTRA_TEXT")
        else:
            tags.append("JSON_EXTRA_TEXT")
        return False, tags

    # 3. JSON parse
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        tags.append("JSON_PARSE_FAIL")
        return False, tags

    return True, []
```

→ 위 통과 후 `rubric.json_schema` 검증으로 진행 (§7).

---

## §7. json_schema 검증 (D 카테고리 required layer 대체)

`rubric.required_layer == "json_schema"` 이면 `rubric.required_elements` 대신 `rubric.json_schema` 객체로 required 검사:

| json_schema 키 | 의미 |
|---|---|
| `required_top_level_keys` | 응답 객체 top-level에 반드시 존재할 key set (모두 있어야 통과) |
| `top_level_keys_exact` | `true` 면 위 set 외 key 추가 금지 (`SCHEMA_EXTRA_KEY`). `false` 또는 부재 시 추가 OK |
| `case_id_value` | 응답 `case_id` 값이 이 string과 정확히 일치 (D_02 사용) |
| `items_length` / `reviews_length` | array 길이 (정수). 불일치 시 `MISSING_REQUIRED_ELEMENT` |
| `required_item_keys` | array element 객체 안의 필수 key set |
| `item_keys_exact` | `true` 면 element 객체에 추가 key 금지 |
| `required_finding_ids` / `required_review_ids` | array element 안의 특정 id 값 모두 등장 |
| `preserve_input_values` | input에 있던 값(rule_id/severity 등)이 응답에 그대로 보존 |
| `language_text_fields.fields` | 지정된 field 값들이 `language_text_fields.language` (ko) 언어인지 검사 |

### §7.1 검증 절차

```python
def validate_json_schema(parsed_response: dict, input_data: dict, schema_spec: dict) -> list[str]:
    issues = []

    # 1. top-level keys
    actual_keys = set(parsed_response.keys())
    required_keys = set(schema_spec["required_top_level_keys"])
    missing = required_keys - actual_keys
    extra = actual_keys - required_keys
    if missing:
        issues.append(f"MISSING_REQUIRED_ELEMENT: top-level keys missing {missing}")
    if schema_spec.get("top_level_keys_exact") and extra:
        issues.append(f"SCHEMA_EXTRA_KEY: top-level extra {extra}")

    # 2. case_id_value
    if "case_id_value" in schema_spec:
        if parsed_response.get("case_id") != schema_spec["case_id_value"]:
            issues.append(f"MISSING_REQUIRED_ELEMENT: case_id mismatch")

    # 3. array length
    for arr_key in ("items", "reviews"):
        length_key = f"{arr_key}_length" if arr_key == "items" else "reviews_length"
        if length_key in schema_spec:
            if len(parsed_response.get(arr_key, [])) != schema_spec[length_key]:
                issues.append(f"MISSING_REQUIRED_ELEMENT: {arr_key} length mismatch")

    # 4~7. item keys / required ids / preserve / language
    # ... (구현 생략)

    return issues
```

---

## §8. 태그 부여 규칙

`tags_legend` 의 15개 태그 + 각 prompt의 `tag_mapping` 활용:

| 자동 부여 방식 | 태그 |
|---|---|
| 검사 단계 직접 매핑 | EMPTY_RESPONSE, JSON_PARSE_FAIL, JSON_EXTRA_TEXT, SCHEMA_EXTRA_KEY, PHI_LEAK, MISSING_REQUIRED_ELEMENT |
| forbidden_elements substring 매칭 + prompt.tag_mapping | OVERCONFIDENT_DIAGNOSIS, UNAUTHORIZED_ACTION, HALLUCINATED_FINDING (일부) |
| format 검사 | FORMAT_FAIL, TOO_VERBOSE, TOO_TERSE |
| 카테고리 정책 기반 (NB-3) | MIXED_LANGUAGE (A 카테고리 자동 적용 X) |
| 정성 — 사람만 | KOREAN_POOR |
| 자동 + 수동 둘 다 | HALLUCINATED_FINDING (substring 매칭 + 사람 추가 검토) |

scorer는 자동 가능한 태그만 부여하고, `tags_manual_review_needed` 컬럼에 KOREAN_POOR 등을 항상 빈 list로 두어 사람이 채우게 둠.

---

## §9. NB-3 처리 (MIXED_LANGUAGE 카테고리 whitelist)

A 카테고리 prompt의 응답에 영어 의료 약어가 등장하는 것은 **정상**. scorer 동작:

```python
def detect_mixed_language(response: str, category_meta: dict) -> bool:
    """Returns True if MIXED_LANGUAGE tag should be applied."""
    policy = category_meta.get("language_policy")
    if policy == "ko_with_medical_en_allowed":
        return False  # NB-3: 자동 적용 금지
    # 그 외 카테고리: langdetect 결과 'ko'가 아니거나, en 문장 비율 > threshold
    return langdetect(response) != "ko"
```

향후 (v0.3 backlog): A 카테고리 안에서도 의료 약어 whitelist 외 영어 문장 등장 시 manual review 태그를 별도로 부여하는 옵션.

---

## §10. 점수 결정

```python
def compute_score(checks: dict) -> int:
    if checks["hard_fail"]:
        return 0
    required_missing_count = len(checks["required_missing"])
    forbidden_present_count = len(checks["forbidden_present"])
    format_pass = checks["format_pass"]

    # 분기 순서: 2점 조건을 먼저 검사하여 3점 분기에 흡수되지 않도록.
    # (Codex R3 must-fix: required_missing<=2 분기가 위에 있으면 forbidden>=3 케이스가
    # 잘못 3점을 받음. v0.2 score_rule상 forbidden 다수는 반드시 2점.)

    # 2: required 중요 누락 3+ 또는 forbidden 다수 (3+)
    if required_missing_count >= 3 or forbidden_present_count >= 3:
        return 2

    # 5: required 모두 + forbidden 0 + format 완전
    if required_missing_count == 0 and forbidden_present_count == 0 and format_pass:
        return 5
    # 4: required 모두 + minor forbidden 1~2, 또는 format-only/minor-format fail
    # v0.3 명시: required_missing=0, forbidden_present<=2, format_pass=False 는 4점.
    if required_missing_count == 0 and forbidden_present_count <= 2:
        return 4
    # 3: required 일부 누락 1~2 + forbidden 경미 1~2
    if required_missing_count <= 2 and forbidden_present_count <= 2:
        return 3

    # 1: 그 외 (대부분 실패)
    return 1
```

→ 단순화된 default. forbidden 등급은 "경미" vs "심각" 구분 어려움 → v0.2는 단순 카운트. v0.3에서 카테고리별 가중치 도입 가능 (`scoring.category_weights`).

---

## §11. Edge cases

- **응답이 JSON 외 문법이라도 substring 매칭 OK** (A/B/C 카테고리 — required_elements는 substring이라 응답 형식에 무관)
- **응답 안에 입력 JSON 일부가 echo** — 모델이 system/user message를 그대로 반복할 때 false positive로 substring 매칭됨. 추정 방어: response.strip() 안에 input task prompt 일부 (예: "다음 raw 메모를 SOAP 구조로") 가 그대로 포함되면 모델 가능성 → manual review 마크.
- **유니코드 정규화 차이** — `한글` vs `한글` (NFC vs NFD)이 다른 byte. scorer는 양쪽 모두 NFC normalize 후 비교 권장.
- **regex 충돌** — D_02의 phi_substrings ["12345"] 는 case_id "case_2026-05-15-D002" 와 충돌 안 함 (substring 다름). 단 D_02 응답의 case_id 값을 substring 검사할 때는 phi 검사 전에 case_id 값을 응답에서 제외하거나 별도 처리 필요.

---

## §12. Step 2 진입 시 fixture

Codex MN-B 권고: **D smoke 응답을 Step 2 scorer의 fixture**로 사용.

```
tests/fixtures/
├── d_smoke_gpt_oss_20b_low.json     # 실 응답 (results/ 에서 복사)
├── d_smoke_gemma4_latest.json
└── expected_scores.json              # 사람이 정답 라벨링 (점수 + hard_fail 여부 + 태그)
```

scorer를 fixture로 검증 → 실제 91 calls 결과에 적용 시 안정성 확보.

---

## §13. 미해결 / v0.3 resolved backlog

### §13.1 v0.3에서 해결

- **format-only-fail 케이스 점수 정의**: `required_missing=0` + `forbidden_present<=2` + `format_pass=False` 는 **4점**으로 명시. D 카테고리 JSON-only 위반은 hard_fail이므로 이 규칙의 대상이 아님.
- **D_01 forbidden_elements 단순 명사 false-positive**: `"확정"`, `"오류"`, `"변경"` 단순 substring 금지에서 명령형/단정형 regex로 좁힘. 입력에서 유래한 `"당뇨 약제 변경"` 같은 합법 명사구는 forbidden 위반이 아님.
- **sentence count tolerance**: 기본 ±1에서 **±2**로 완화. 의료 약어와 수치 punctuation 과계산을 줄임.
- **A_04 `[확인 필요]` marker 강화**: `format_requirements.required_marker = {"text": "[확인 필요]", "min_count": 1}` 구조화. scorer가 직접 marker count를 검사.

### §13.2 남은 backlog

- HALLUCINATED_FINDING의 자동 검출 정밀도 (현재는 입력 raw_memo와 응답의 신규 entity diff 기반 — 의미 의역 false negative 다수)
- A 카테고리 외 카테고리에서 의료 약어가 자연스럽게 등장하는 케이스 (B에서 "K29.7" 같은 코드는 영어 약어 아님)
- 카테고리별 가중치 (현재는 카테고리 무관 동일 weight, 분석 단계에서 별도 집계 권장)
- 응답 안의 raw template token (`<|im_end|>`, `<think>` 등) 감지 — ollama auto-template 실패 신호

---

**문서 끝**
