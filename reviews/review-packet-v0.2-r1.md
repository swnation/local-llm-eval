# Review Packet — local-llm-eval-prompts-clinical-assist v0.2 R1

**검토 대상**: `local-llm-eval-prompts-clinical-assist-v0.2.md` (1338 lines, 별도 첨부)
**Review round**: R1 (must-fix only loop)
**작성일**: 2026-05-15
**Reviewer**: GPT (cross-review)
**Previous round**: R0 CONDITIONAL GO (MF 4 + SF 5 + Minor 3)
**SOP**: session-collaboration-rules-v1 (must-fix only loop, R1 = MF/SF 반영 확인)

---

## §0. R1 컨텍스트 (R0에서 받은 결과 + v0.2 반영)

### §0.1 R0 결과 요약

R0 판정: **CONDITIONAL GO**

| 분류 | 수 | 처리 방침 |
|------|-----|----------|
| Must-fix | 4개 | v0.2에서 전부 반영 (필수) |
| Should-fix | 5개 | v0.2에서 전부 반영 (사용자 권장 옵션 2 선택) |
| Minor | 3개 | v0.2에서 미반영 (§9.3 backlog 기록) |

### §0.2 v0.2 변경 사항 요약

R0의 9개 항목 (MF 4 + SF 5) 모두 v0.2에 반영. Minor 3개는 backlog. v0.2 §10 changelog 섹션에 변경 표 명시.

**Must-fix 반영 위치**:

| ID | v0.2 위치 | 변경 핵심 |
|----|-----------|----------|
| MF-1 | §5 B_02 (라인 ~526-595) | task framing 변경, K29.0 언급 강제 제거, 대체 코드 단정 표현 forbidden 추가 |
| MF-2 | §6 C_02 (라인 ~731-810) | `INSULIN_CHANGE_MONITORING_MISSING` WARNING → `DIABETES_MONITORING_REVIEW` INFO로 완화 (선택 A) |
| MF-3 | §4 A_01 (라인 ~195) | required `r/o` 강제 → "r/o 또는 가능성 또는 의심 중 1개" |
| MF-4 | §2.4 신설 + §7 D 전체 (라인 ~105, ~975, ~1057, ~1161) | JSON-only 엄격 검사 규칙. `response.strip() 전체가 JSON object` + JSON 앞뒤 1자도 hard_fail |

**Should-fix 반영 위치**:

| ID | v0.2 위치 | 변경 핵심 |
|----|-----------|----------|
| SF-1 | §1 system prompt (라인 ~44-60) | PHI 범위 확장 (patient_context, 성별/나이/지역 포함) |
| SF-2 | §3 평가 태그 (라인 ~107-128) | `SCHEMA_EXTRA_KEY`, `JSON_EXTRA_TEXT` 신설 + 자동/수동 컬럼 |
| SF-3 | §4 A_02 (라인 ~268-275) | "allowed: 30대 남성 표현은 원문 기반이므로 허용" 항목 신설 |
| SF-4 | §6 C_01 + C_02 format_requirements (라인 ~717, ~795) | "약물명 언급 가능, 변경/감량/중단 지시 금지" 명시 |
| SF-5 | §9.2 1단계 (라인 ~1264) | "21/21 성공" → "응답 생성/속도/format 측정이 가능했던 7개" |

**Minor 미반영 (§9.3 backlog)**:
- MN-1: A_03 tenderness +/- 우선 표기 (현재도 둘 다 OK 상태)
- MN-2: PHI substring 자동화 일반화 (자동 채점 스크립트 작성 시)
- MN-3: `KOREAN_POOR` 인간 review tag (§3 표 자동/수동 컬럼에 이미 "수동" 마킹 완료)

### §0.3 v0.1 → v0.2 정량 변화

- 총 라인: 1240 → 1338 (+98 line)
- 섹션 신설: §2.4 (JSON-only 엄격 규칙) + §10 (Changelog)
- prompt 본문 수정: A_01, A_02, B_02, C_01, C_02 (5개)
- production code 영향: 없음 (eval adapter schema, production schema 변경 X)

---

## §1. R1 검토 요청 사항

R1은 must-fix only loop입니다. 다음 3축에 한정.

### §1.1 MF 반영 완전성 (필수)

R0에서 받은 Must-fix 4개가 v0.2 §5 B_02 / §6 C_02 / §4 A_01 / §2.4+§7 D 전체에 **정확히 반영**됐는지 확인:

1. **MF-1 B_02**: K29.0 대체 코드 제안 framing이 완전히 제거되고 "확인 필요 신호 설명"으로 전환됐는지. forbidden에 단정 표현이 충분히 들어갔는지.
2. **MF-2 C_02**: rule_id, severity, finding, evidence가 모두 일관되게 완화됐는지. 인슐린 처방 자체의 변경 권고로 확장될 risk가 남아있는지.
3. **MF-3 A_01**: r/o 단독 강제가 완화됐는지. forbidden(확진/진단됨)은 그대로 유지됐는지.
4. **MF-4 D 카테고리**: §2.4 신설 규칙 + D_01/D_02/D_03 각 hard_fail에 "JSON 앞뒤 1자도 hard_fail" 명시가 모두 들어갔는지. 자동 채점 구현 시 모호성이 없는지.

### §1.2 SF 반영 완전성 (강 권고)

Should-fix 5개도 옵션 2 선택으로 모두 반영. 동일하게 정확히 반영됐는지 확인. 특히:

- SF-1: system prompt 변경이 다른 prompt들의 PHI policy와 충돌 안 하는지
- SF-2: 새 태그 2개가 §7 D prompt들의 평가 태그 매핑에 일관되게 적용됐는지

### §1.3 새 risk 발생 여부

v0.2 변경 과정에서 의도치 않은 부작용 발생 가능성:

- B_02 framing 변경 후 prompt가 너무 vague해서 모델이 평가 의도를 못 잡을 risk?
- C_02 severity가 WARNING → INFO로 낮춰진 게 평가 차원에서 너무 약한 case가 된 risk?
- D 카테고리 엄격 규칙 (앞뒤 1자도 hard_fail) 이 너무 가혹해서 거의 모든 모델이 0점 받을 risk? (적절한 stress인지)

### §1.4 4-way 분류 + 확신도 라벨 응답 형식 (R0와 동일)

```
[분류 — Must-fix / Should-fix / Nit / N/A]
[확신도 — HIGH / MEDIUM / LOW / 확인 필요]
[위치 — v0.2 §번호 또는 prompt id]
[내용 — 1~3문장]
[권고 수정안 — 가능하면]
```

---

## §2. R1 GO 조건

R1은 R0와 달리 **must-fix only loop**입니다. GO 조건이 더 좁음.

**GO** 조건:
- 새 Must-fix = 0
- v0.2의 MF/SF 반영 모두 정확
- 새 risk 없음 또는 minor

**CONDITIONAL GO**:
- 새 Must-fix 1~2개 (단순 수정 가능 수준)
- 의사 검토 → v0.3 정정 → quick rerun 진입

**NOT GO**:
- 새 Must-fix 3개 이상 또는 본질적 문제 발견
- 설계 단계 부분 복귀

R0 → R1 → R2 sequence는 SOP에 따라 minimal loop이 원칙. R1에서 발견된 critical issue가 아니면 quick rerun 진입 후 결과 보고 R2 결정.

---

## §3. 본 R1 review가 보지 않는 것 (R0와 동일, 재확인)

다음은 R1 scope 밖. **검토 요청 X**.

- 자동 채점 스크립트 코드 자체 (별도 round)
- 실 모델 평가 실행 결과 (R1 GO 후 진행)
- production schema와 eval adapter schema 변환 logic (별도 adapter layer)
- 64GB RAM 후 part 2 모델 추가 (§9.2 3단계)
- 카테고리 가중치 결정 (§9.1 한계 5번)
- Minor 3개 (§9.3 backlog 기록 완료)

---

## §4. 본 R1 review가 보는 것

다음만 검토 대상:

- v0.2 §1 (system prompt SF-1 반영)
- v0.2 §2.4 (MF-4 신설 규칙)
- v0.2 §3 (SF-2 태그 추가)
- v0.2 §4 A_01 (MF-3) + A_02 (SF-3)
- v0.2 §5 B_02 (MF-1)
- v0.2 §6 C_01 (SF-4) + C_02 (MF-2)
- v0.2 §7 D_01/D_02/D_03 (MF-4)
- v0.2 §9.2 (SF-5)
- v0.2 §10 changelog 정확성

---

## §5. 첨부

- **`local-llm-eval-prompts-clinical-assist-v0.2.md`** (1338 lines) — 검토 대상 v0.2 (별도 파일)
- (참고용) `local-llm-eval-prompts-clinical-assist-v0.1.md` — R0 review 시 검토했던 원본 (필요시)
- (참고용) R0 review 응답 — GPT가 R0에서 직접 작성한 결과

---

## §6. 다음 단계

GPT R1 응답 수령 후:

- **R1 GO** → v0.2 freeze + §9.2 1단계(32GB quick rerun) 진입. GPT 권장: D 카테고리 smoke 먼저 → 전체 7 모델 × 13 prompt
- **R1 CONDITIONAL GO** → 추가 MF/SF 반영 → v0.3 작성 → R1 v2 재검토
- **R1 NOT GO** → 설계 부분 복귀, MF/SF 반영 방향 재논의

---

## §7. GPT에게 직접 전달할 한 줄

> R0 CONDITIONAL GO에서 받은 Must-fix 4 + Should-fix 5를 v0.2에 모두 반영했습니다 (Minor 3은 backlog). R1에서는 MF/SF 반영 완전성 + 새 risk 발생 여부만 확인 부탁드립니다. quick rerun 진입 가능 여부 판정도 같이 부탁드립니다.

---

**packet 끝**
