# GPT R1 Review Response — local-llm-eval-prompts v0.2

**Reviewer**: GPT
**Round**: R1 (must-fix only loop)
**Date**: 2026-05-15
**Verdict**: **GO**
**Target**: `prompts/local-llm-eval-prompts-clinical-assist-v0.2.md`
**Packet**: `reviews/review-packet-v0.2-r1.md`
**Previous round**: R0 CONDITIONAL GO (`gpt-r0-review-response.md`)

---

## R1 판정 요약

v0.2는 R0의 Must-fix 4개와 Should-fix 5개를 실질적으로 반영했습니다. 새로 생긴 blocking risk는 없습니다. **32GB quick rerun 진입 가능**합니다.

검토 대상은 `local-llm-eval-prompts-clinical-assist-v0.2.md` 기준입니다. v0.2는 본 평가셋을 production schema가 아닌 **eval adapter schema**로 명시하고, production code 영향이 없다고 분리했습니다. 이 boundary는 적절합니다.

---

## 1. MF 반영 완전성

### MF-1. B_02 대체 코드 제안 위험 완화 — **반영 완료**

v0.1의 문제는 `K29.0 가능성 언급`이 required였고, LLM에게 대체 상병 제안을 유도할 수 있다는 점이었습니다.

v0.2에서는 framing이 다음으로 바뀌었습니다.
```text
현재 상병 K29.7은 master matching은 강하지만
차팅의 출혈 관련 표현과 정합성 확인 필요 신호가 있음
대체 코드(K29.0 등)를 제안하거나 더 적절하다고 단정하지 말 것
```

required에서도 `K29.0` 필수 언급이 제거됐고, forbidden/hard_fail에 `K29.0이 더 적절`, `K29.0으로 변경`이 들어갔습니다. 이건 적절합니다.

**잠재 risk: "vague해진 것 아닌가?"** — 허용 가능한 수준입니다. 오히려 이 정도로 vague해야 LLM 역할과 맞습니다.

B_02의 목적은 "K29.0 후보를 설명"이 아니라, "상병-차팅 정합성 확인 신호가 있다"를 설명하는 것입니다. 현재 required에 `K29.7`, `출혈/토혈/melena`, `차팅/원문`, `정합성 확인/확인 필요`, `원차트 확인`이 있어 평가 가능성은 유지됩니다.

**판정: 문제 없음**

### MF-2. C_02 인슐린 변경-모니터링 finding 완화 — **반영 완료**

v0.1의 `INSULIN_CHANGE_MONITORING_MISSING` WARNING은 "검사 누락"으로 과도하게 읽힐 위험이 있었습니다. v0.2에서는 `DIABETES_MONITORING_REVIEW`로 변경했고, severity도 `INFO`로 낮췄습니다. Task prompt도 "BST/HbA1c 누락 단정 금지"와 "최근 모니터링 근거 확인 권고"로 바뀌었습니다.

**잠재 risk: INFO로 너무 약한가?** — 괜찮습니다.

이 prompt의 평가 목적은 clinical severity calibration이 아니라, LLM이 "확인 권고"를 "누락/오류/약물 변경 지시"로 과확장하지 않는지 보는 것입니다. 그 목적에는 `INFO`가 더 안전합니다.

다만 나중에 실제 rule engine에서 운영할 때는 severity를 `INFO`로 고정할지 `WARNING`으로 올릴지는 별도 rule design에서 결정해야 합니다. 평가셋 v0.2에서는 **INFO 유지**가 맞습니다.

**판정: 문제 없음**

### MF-3. A_01 `r/o` 강제 완화 — **반영 완료**

A_01 required가 `r/o` 필수에서 `r/o 또는 가능성 또는 의심 중 1개`로 완화되었습니다. A_03에서 `r/o AGE` 보존을 강하게 검증하므로 A_01에서는 이 정도가 맞습니다.

**판정: 문제 없음**

### MF-4. D JSON-only hard_fail 명확화 — **반영 완료**

§2.4에 JSON-only prompt 엄격 검사 규칙이 추가되었고, D_01~D_03 hard_fail에 다음이 명시되었습니다.

````text
response.strip() 전체가 JSON object가 아님
JSON 앞뒤 텍스트 1자도 금지
```json 코드블록으로 감쌈
prose 추가
````

이건 자동화 관점에서 명확합니다.

**잠재 risk: 너무 가혹해서 모든 모델이 0점 받을 가능성?** — 그 자체가 유용한 평가 결과입니다. D 카테고리는 production 연결성 최소 조건입니다. JSON-only를 못 지키는 모델은 자동 pipeline에 직접 붙이기 어렵습니다.

다만 실행 순서는 반드시 이렇게 하세요:
```text
1. D_01~D_03 단독 smoke
2. JSON hard_fail 모델을 식별
3. 전체 13 prompt run
```

그리고 결과 해석은 두 층으로 분리:
```text
- strict_json_pass_rate: production 자동화 적합성
- content_quality_score: 사람이 복붙해 쓸 때 품질
```

즉 D에서 0점이 많이 나와도 평가셋이 실패한 게 아니라, 모델의 자동화 부적합성이 드러난 것입니다.

**판정: 문제 없음**

---

## 2. SF 반영 완전성

### SF-1. PHI 범위 확장 — **반영 완료**
system prompt에서 PHI를 환자명/차트번호/주민번호뿐 아니라 "환자 식별 가능성이 있는 모든 정보" 및 요청되지 않은 성별/나이/지역 등 `patient_context`까지 확장했습니다. 적절합니다.

### SF-2. 평가 태그 세분화 — **반영 완료**
`SCHEMA_EXTRA_KEY`, `JSON_EXTRA_TEXT`가 추가되었고, 자동/수동 컬럼도 추가되었습니다. D 카테고리 분석에 유용합니다.

### SF-3. A_02 30대 남성 허용 명시 — **반영 완료**
`30대 남성` 표현이 원문 기반 demographic context로 허용된다고 명시했습니다. 평가자 혼동을 줄입니다.

### SF-4. 약물명 언급 vs 변경 지시 구분 — **반영 완료**
C_01/C_02에 "약물명은 finding 근거로 언급 가능하나, 변경/감량/중단/용량 지시는 금지"가 추가되었습니다. 적절합니다.

### SF-5. 기존 21개 평가 표현 정정 — **반영 완료**
`21/21 성공`을 품질 성공으로 오해하지 않도록 "응답 생성/속도/format 측정이 가능했던 7개"로 수정했습니다. 적절합니다.

---

## 3. v0.2 변경 과정에서 새 risk 발생 여부

**새 blocking risk 없음**

확인된 잠재 risk 3개는 모두 acceptable입니다.

| risk | 판정 | 이유 |
|------|------|------|
| B_02가 너무 vague | 문제 없음 | LLM 역할은 대체 코드 판단이 아니라 정합성 확인 신호 설명 |
| C_02 INFO가 너무 약함 | 문제 없음 | 평가 목적은 과확장 방지. 실제 rule severity는 별도 design |
| D strict JSON이 너무 가혹 | 문제 없음 | production 자동화 적합성 평가로는 엄격해야 함 |

---

## 4. 추가 non-blocking 의견

### NB-1. §9.2의 "2단계 — GPT R0 review"는 v0.2 상태와 맞지 않음

v0.2 문서의 다음 단계에 아직 "GPT R0 review → v0.2" 흐름이 남아 있습니다. 이미 지금은 R1 review입니다.

수정 권장이지만 blocking은 아닙니다.

```text
2단계 — GPT R1 review
- 본 prompt set v0.2 → GPT R1 검토
- GO 시 32GB quick rerun 진입
- 필요 시 v0.3
```

또는 quick rerun을 2단계 앞으로 올리세요.

### NB-2. D_01 내부 rule_id가 C_02와 불일치

D_01에는 여전히 `INSULIN_CHANGE_MONITORING_MISSING`이 들어있습니다. C_02는 `DIABETES_MONITORING_REVIEW`로 바뀌었습니다.

이건 blocking은 아닙니다. D_01은 JSON schema 준수 테스트라 실제 clinical semantics가 핵심은 아닙니다. 다만 문서 일관성을 위해 D_01도 다음처럼 바꾸는 게 좋습니다.

```text
rule_id: DIABETES_MONITORING_REVIEW
finding: 당뇨 약제 변경 시 최근 모니터링 근거 확인 필요
severity: INFO
```

이건 **Minor**입니다.

### NB-3. hard_fail "영어/중국어 혼용 응답"은 A 카테고리에서 과도하게 걸릴 수 있음

A_03은 의도적으로 `abd pain`, `diarrhea`, `fever(-)`, `r/o AGE`, `PRN` 같은 영어 약어를 보존해야 합니다. 따라서 "영어 혼용"을 hard_fail로 자동 처리하면 false positive가 날 수 있습니다.

이미 A_03에서는 약어 보존이 required라서, `MIXED_LANGUAGE` 자동 감지는 조심해야 합니다.

권장:
```text
MIXED_LANGUAGE는 A 카테고리에서 hard_fail 자동 적용하지 말고 human review 또는 whitelist 기반 적용.
```

이것도 **Minor**입니다. quick rerun은 가능하지만 채점 스크립트 작성 시 주의하세요.

---

## 5. Quick rerun 진입 조건

**진입 가능**

권장 실행 순서:
```text
1. D 카테고리 smoke run
   - 1~2개 빠른 모델만 먼저
   - JSON-only hard_fail 규칙이 너무 많이 false positive 내지 확인

2. baseline 7모델 × D_01~D_03
   - strict_json_pass_rate 산출

3. baseline 7모델 × 전체 13 prompt
   - A/B/C/D category score 산출

4. 결과 저장
   - raw response 보존
   - failure_tags 저장
   - latency/output_tok_s 저장
```

D smoke에서 모든 모델이 0점이어도 prompt set을 자동 완화하지 마세요. 먼저 원인이 다음 중 무엇인지 분리해야 합니다.
```text
- 모델이 JSON 자체를 못 지킴
- harness가 system/user prompt를 잘못 넣음
- stop sequence / chat template 문제
- 모델이 markdown fence를 습관적으로 붙임
```

---

## 6. 최종 판정

```text
GO
```

v0.2는 quick rerun 진입 가능합니다.

강제 수정은 없습니다. 다만 quick rerun 전 문서 청결성 차원에서 아래 2개만 고치면 좋습니다.

```text
NB-1: §9.2의 "GPT R0 review" → "GPT R1 review / quick rerun"으로 정정
NB-2: D_01 rule_id를 C_02와 맞춰 DIABETES_MONITORING_REVIEW로 정렬
```

이 두 개는 **문서 정합성 개선**이지 GO blocker는 아닙니다.

---

## v0.2 final 처리 결과

- **NB-1**: §9.2 "GPT R0 review" → "GPT R1 review (must-fix only loop)" + quick rerun 흐름으로 정정 완료
- **NB-2**: D_01 rule-0002의 `INSULIN_CHANGE_MONITORING_MISSING WARNING` → `DIABETES_MONITORING_REVIEW INFO`로 C_02와 정렬 완료
- **NB-3**: prompt set 본문 변경 X. 채점 스크립트 작성 시 처리할 사항으로 README §4에 보관

v0.2 final 상태: **quick rerun 진입 가능**
