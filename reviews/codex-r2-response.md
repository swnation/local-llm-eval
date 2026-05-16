# Codex R2 review 처리 응답 — 2026-05-16

> Codex CONDITIONAL GO 응답에 대한 처리 보고. Must-fix 2개 + Should-fix 1개 + Minor 2개 모두 즉시 반영. v0.2 final 산출물 유지 (prompt 본문 변경 없음, rubric schema 추가만).

---

## §0. 판정 요청

R2 GO 요청. Must-fix 2개 완전 반영, Should-fix 1개 즉시 작성, Minor 2개 정정. Step 1 산출물 sign-off → Step 3 D smoke 진입 + Step 2 채점 스크립트 작성 진입.

---

## §1. Must-fix 반영

### MF-A — D 카테고리 4층 rubric 계약 일관성

**Codex 의견**: D_01~D_03은 `rubric.required_elements` 키가 없고 `json_schema`만 있음. 4층 rubric 계약상 `required_elements: []`를 두거나 `json_schema`가 required layer를 대체한다는 명시 필드 필요.

**처리**: 두 가지 모두 반영.

`prompts/test_suite_v0.2.json` 변경:

1. **각 D prompt rubric에 명시 필드 추가**:
   ```json
   "rubric": {
     "required_layer": "json_schema",
     "required_elements": [],
     "json_schema": { ... },
     "forbidden_elements": [...],
     "format_requirements": {...},
     "hard_fail": {...}
   }
   ```
   → `required_elements: []` 빈 list로 layer 계약 준수 + `required_layer: "json_schema"` 로 검사 dispatch 명시.

2. **top-level `scoring` 객체에 dispatch 룰 추가**:
   ```json
   "scoring": {
     ...
     "required_layer_dispatch": {
       "_doc": "각 prompt rubric의 required_layer 필드로 어느 검사로 required 확인을 수행할지 결정. 기본값은 'required_elements'. D 카테고리는 'json_schema'로 대체.",
       "required_elements": "rubric.required_elements list (string | {any_of: [...]} | {regex: '...'}) 를 substring/regex로 검사",
       "json_schema": "rubric.json_schema 객체 검증으로 대체. rubric.required_elements는 [] 로 비어있음."
     }
   }
   ```

→ 채점 스크립트가 `rubric.required_layer` 필드(없으면 default `"required_elements"`)로 dispatch. D 카테고리는 자동으로 `json_schema` 검증 path 진입.

### MF-B — D_01/D_02 json_schema exact 플래그 보강

**Codex 의견**: D_01/D_02의 `json_schema`에 `top_level_keys_exact` 플래그 누락. D_03만 있음. 일관성 위해 명시 또는 기본값 정책 필요.

**처리**: 명시 쪽으로 통일. D_01/D_02에 `top_level_keys_exact: true` 추가 + 같은 김에 `item_keys_exact: true` 도 추가 (D_03와 정렬).

변경 후 D 카테고리 모두 동일한 strict 정책:

| Prompt | top_level_keys_exact | item_keys_exact |
|---|---|---|
| D_01 | true (신규) | true (신규) |
| D_02 | true (신규) | true (신규) |
| D_03 | true (기존) | true (기존) |

→ scorer 입장에서 D 카테고리는 schema strict 일관 — 추가 key 발견 시 모두 `SCHEMA_EXTRA_KEY` 태그 + 감점.

---

## §2. Should-fix 반영

### SF-A — Scorer contract 문서화

**Codex 의견**: required_elements 안의 string/any_of/regex 혼합 표현은 무리 없음. 다만 scorer contract를 문서화해두면 좋음 — string은 case-sensitive substring인지, regex는 Python `re.search`인지, any_of는 하나만 맞으면 present인지.

**처리**: 즉시 작성. Step 2 진입 직전이라 timely.

신규 파일: `SCORING_CONTRACT.md` (13 sections, ~430 lines)

핵심 명세:

| 표현 | 매칭 방식 |
|---|---|
| `"인후통"` (string) | `response_text.find(s) >= 0` (Python `in` 동등). **case-sensitive** literal substring. 유니코드 NFC normalize 후 비교 권장 |
| `{"any_of": ["URI", "상기도감염"]}` | list 중 **하나라도** match면 present. 중첩 any_of 금지 |
| `{"regex": "3[7-9]..."}` | Python `re.search` (부분 매칭, default flag 없음 — multiline X, case sensitive). JSON escape 주의 (`\\d+`) |

추가 명세:

- §4 format_requirements 의미 (language enum 3종 / sentence count / structure enum / required_marker / policy)
- §5 hard_fail 자동 검사 항목 매핑 (자연어 `conditions` 중 무엇이 자동화 가능한지 컬럼 표시)
- §6 JSON-only strict 규칙 의사코드
- §7 json_schema 검증 절차 (top_level_keys_exact / items_length / item_keys_exact / required_*_ids / preserve_input_values / language_text_fields 각각)
- §8 태그 부여 규칙 (자동 vs 수동)
- §9 NB-3 처리 (A 카테고리 MIXED_LANGUAGE 자동 hard_fail 금지)
- §10 점수 결정 (단순 카운트 기반 default + v0.3 가중치 backlog)
- §11 edge cases (응답 안에 input echo / 유니코드 정규화 / regex 충돌)
- §12 Step 2 진입 시 fixture 권장 (MN-B 반영)
- §13 미해결 (v0.3 backlog)

→ Step 2 scorer 작성 시 이 문서를 spec으로 사용. 구현 결정의 모호함 제거.

---

## §3. Minor 반영

### MN-A — "13 평가 태그" → 15 정정

**Codex 의견**: tags_legend는 실제 15개라 README/session summary의 "13 평가 태그" 표현만 정정.

**처리**: 즉시 정정.

| 파일 | 정정 위치 |
|---|---|
| `README.md` | §3.2 "평가 태그 13종" → "15종" / §5 Step 2 "13 평가 태그" → "15 평가 태그" / §15 변경 이력 "13 평가 태그" → "15 평가 태그" |
| `reviews/session-summary-2026-05-16-step1.md` | §3.1 "13 평가 태그 매핑" → "15 평가 태그 매핑" |

→ `reviews/review-packet-v0.1-r0.md` 의 "13종" 표현은 **유지** (당시 v0.1 설계 시점의 카운트라 historical 정확성. SF-2 패치로 SCHEMA_EXTRA_KEY + JSON_EXTRA_TEXT 2개 신설된 결과가 15개).

### MN-B — D smoke 응답을 scorer fixture로

**Codex 의견**: D smoke를 사람 눈 sanity check로 먼저 돌려도 괜찮지만, 결과를 Step 2 scorer fixture로 써서 JSON fence/extra text/schema extra key가 제대로 잡히는지 확인하는 흐름이 제일 깔끔.

**처리**: README §5 Step 2 안내에 한 줄 추가 + SCORING_CONTRACT §12 에 fixture 폴더 구조 제안.

```
tests/fixtures/
├── d_smoke_gpt_oss_20b_low.json     # 실 응답 (results/ 에서 복사)
├── d_smoke_gemma4_latest.json
└── expected_scores.json              # 사람이 정답 라벨링
```

→ 91 calls quick rerun 들어가기 전 scorer를 fixture로 1차 회귀 테스트.

---

## §4. 변경 파일 요약

| 파일 | 변경 |
|---|---|
| `prompts/test_suite_v0.2.json` | scoring.required_layer_dispatch 추가 / D_01,D_02,D_03 rubric에 required_layer + required_elements:[] + top_level_keys_exact + item_keys_exact |
| `prompts/test_suite_v0.2_d_only.json` | 위와 동기화 (subset 재생성) |
| `SCORING_CONTRACT.md` | 신규 — scorer 행동 정확 명세 (13 sections, ~430 lines) |
| `README.md` | "13 평가 태그" → "15" (3곳), Step 2 안내에 SCORING_CONTRACT.md 링크 + fixture 권장 한 줄 |
| `reviews/session-summary-2026-05-16-step1.md` | "13" → "15" 정정 1곳 |
| `reviews/codex-r2-response.md` | 신규 — 이 문서 |

→ Prompt 본문(system, user, intent, expected) 변경 0건. v0.2 final R1 GO 정신 유지.

---

## §5. v0.3 backlog 누적

이번 round에서 backlog 신규 항목 없음. 기존 항목 유지:

- MN-1 (A_03 tenderness +/- 우선 표기 명시): 미해결
- MN-2 (D_02 PHI substring 자동화 일반화 — `forbidden_phi_values` list 기반): SCORING_CONTRACT §11 에 구현 노트 보강
- C 카테고리 rule_id naming을 실제 rules.json v1과 정렬
- A 카테고리 인수인계 prompt 1개 추가 검토 (Priority 5)
- HALLUCINATED_FINDING 자동 검출 정밀도 (현재는 의미 의역 false negative 다수)

---

## §6. 다음 액션 (사용자 PC)

1. `ollama-imports/import.ps1` 실행 (LM Studio 3개 → Ollama 통일)
2. D smoke run:
   ```powershell
   python eval_runner_auto.py --config models_config_d_smoke.json --prompts prompts/test_suite_v0.2_d_only.json
   ```
3. D smoke 응답 사람 눈 sanity check
4. (병행) Step 2 `score_runner.py` 작성 시작 — SCORING_CONTRACT.md를 spec으로
5. fixture로 scorer 검증
6. 전체 7 모델 × 13 prompt quick rerun (91 calls, 30~60분)
7. 결과 분석 → v0.3 정정 또는 64GB part 2 진입

---

## §7. R2 sign-off 요청

Codex 추가 must-fix 있는지 확인 요청. 없으면 위 다음 액션대로 Step 3/Step 2 병행 진입.

**문서 끝**
