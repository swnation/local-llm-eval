# Review Packet — local-llm-eval-prompts-clinical-assist v0.1 R0

**검토 대상**: `local-llm-eval-prompts-clinical-assist-v0.1.md` (1240 lines, 별도 첨부)
**Review round**: R0 (first round, 4-way 분류 + 확신도 라벨)
**작성일**: 2026-05-15
**Reviewer**: GPT (cross-review)
**SOP**: session-collaboration-rules-v1 (R0/R1/R2/R3 회차별 목적, must-fix only loop)

---

## §0. Reviewer 컨텍스트 (왜 이 packet이 만들어졌는가)

### §0.1 세션 흐름 요약

이번 세션은 Clinical-assist의 local LLM 평가셋을 **이전 21개 prompt에서 13개 v0.1 prompt set으로 재설계**한 과정의 산출물입니다.

**핵심 전환점 3개**:

1. **기존 21개 평가의 한계 발견**
   - cfn 11개 + rule_classification 5개 + kmed 5개 = 21개 prompt를 7 모델 × 21 prompt = 147 응답 평가 완료
   - 결과: gemma4-latest 종합 1순위, gpt-oss-20b 보수적, hari 계열 빈 응답 패턴 발견
   - **하지만** 의사 사용자가 push back: "지금 프로젝트에 의학적 판단까지 하는 건 좀 아니지 않아?"
   - 두 번째 push back: "차팅 오타 잡거나 규칙엔진이 놓친 룰 잡는 역할이 LLM의 본 역할 아닌가?"

2. **LLM 역할 재정의 문서 수용**
   - 사용자가 별도 문서로 LLM 본 역할 정리: **"판단 엔진이 아니라 설명·정리·검토 보조 엔진"**
   - LLM 입력 = raw 처방 데이터 X / structured + match_summary + rule_findings + needs_review O
   - LLM 출력 = 자동 수정/임상 변경 지시 X / 설명/정리/리뷰 권고 O
   - 기존 21개 평가는 "LLM에게 raw input 주고 위험 판단 시키기" 구조라 본 역할과 정합 안 됨

3. **새 평가셋 v0.1 작성 + 이전 GPT review 4 조건 반영**

### §0.2 이전 GPT review (CONDITIONAL GO) 의 4 조건

본 v0.1은 이전 GPT review에서 받은 4개 조건을 모두 반영했습니다.

| GPT 권장 | v0.1 반영 위치 |
|----------|----------------|
| 1. rule_classification 완전 폐기 X, "decision 설명 능력" 테스트로 재가공 | §6 C 카테고리에 흡수 (rule engine output JSON 입력 → 의사 친화 문장 생성) |
| 2. 카테고리 A에 **원문 보존 stress test** 반드시 포함 | §4 A_03 "의료 약어/기호 보존 stress test" 핵심 prompt로 명시. 3d ago / fever(-) / Td +/- / r/o / PRN 보존 검증 |
| 3. 카테고리 D는 2개가 아니라 **최소 3개** | §7에 D_01(JSON array) + D_02(PHI substring stress) + D_03(schema strict) = 3개 |
| 4. 채점은 "정답 문장" 대신 **required_elements + forbidden_elements + format + hard_fail** | §2 공통 rubric + 각 prompt별 4층 명세 + §3 평가 태그 13종 |

### §0.3 lightweight cross-check 결과

v0.1 작성 전 clinical-assist repo 현재 schema와 lightweight cross-check 수행:

- `findings.json` 실제 schema (G0): top-level `version`/`case_id`/`summary`/`findings`
- finding item: `finding_id` (dx-match-0001 / dx-invalid-0001), `type`, `section`, `status`, `dx_code`, `ocr_dx_name`, `master_dx_name`, `reason`, `requires_review`
- Forbidden in artifacts: `generated_at`, `captured_at`, `visit_time`, `source_room`, `source_pc`, PHI fields

→ v0.1은 **eval adapter schema**임을 §0.3에 명시. production schema 변경 영향 없음. 현재 G0 단계 (dx matching만 구현, rule engine은 가까운 미래 가정)임도 §9.1에 명시.

### §0.4 v0.1 산출물 통계

- 총 라인: 1240
- 섹션: §0~§9 (10개)
- prompt 수: 13개 (A 4 + B 3 + C 3 + D 3)
- 평가 태그: 13종
- 공통 system prompt: 12 줄 한국어

---

## §1. R0 검토 요청 사항

GPT가 §8에서 직접 제시한 4축 + 추가 2축 = **6축 검토** 요청.

### §1.1 GPT 자체 제시 4축 (필수)

다음 4개 측면이 v0.1에 충분히 반영됐는지 검토:

1. **카테고리 누락**: A/B/C/D 외에 LLM 본 역할(설명·정리·검토 보조)에서 빠진 카테고리가 있는가?
2. **역할 위반**: 어느 prompt가 LLM에게 "판단/자동 수정/임상 변경 지시"를 유도하는 구조로 잘못 짜여있는가?
3. **PHI 위험**: 어느 input/output spec이 PHI leak 위험을 충분히 차단 못 하는가?
4. **채점 불명확성**: required/forbidden/format/hard_fail이 모호하거나 자동 채점 불가능한 prompt가 있는가?

### §1.2 추가 검토 축 2개 (있으면 좋음)

5. **scenario 완전성**: 각 카테고리 내 prompt 분포가 실사용에서 발생할 시나리오를 충분히 cover하는가? (예: A는 외래 차팅만 — 입원 경과기록은 빠짐, B는 매칭 모호만 — duplicate 케이스 빠짐 등)
6. **schema 정합**: eval adapter schema와 §0.3 cross-check 결과 사이에 모순이 있는가? production G1 단계 진입 시 adapter layer 작성에 무리가 없는가?

### §1.3 4-way 분류 + 확신도 라벨 응답 형식

각 issue마다 다음 형식으로 응답 요청:

```
[분류 — Must-fix / Should-fix / Nit / N/A 중 하나]
[확신도 — HIGH / MEDIUM / LOW / 확인 필요]
[위치 — v0.1 §번호 또는 prompt id (예: A_03)]
[내용 — 간결 1~3문장]
[권고 수정안 — 가능하면]
```

분류 정의:
- **Must-fix**: v0.1 R0 GO 불가 (blocker). 반영 후 R1 재검토 필요.
- **Should-fix**: 강 권고. 반영 후 R1로 진행 권장.
- **Nit**: 미세 개선. R1에 반영하면 좋지만 blocker 아님.
- **N/A**: 의도 명확, 조정 불필요.

---

## §2. R0 GO 조건

다음 조건을 만족하면 **R0 GO** 판정:

- Must-fix = 0
- Should-fix가 minor 수정 (각 prompt당 1~2줄 수정 이내)
- 4축 검토에서 critical risk 미발견

조건 미달 시:
- Must-fix 1개 이상 또는 Should-fix가 설계 변경 필요 → **CONDITIONAL GO**
  - 의사 검토 → packet v0.2 정정 → R0 v2 재검토
- 카테고리 자체에 본질적 문제 → **NOT GO**
  - 설계 단계로 복귀

---

## §3. 본 R0 review가 보지 않는 것 (scope 밖)

다음은 R0 scope 밖. **검토 요청 X**.

- 자동 채점 스크립트 코드 자체 (§8의 outline만 있고 실제 코드 없음 — R1 또는 별도 round)
- 실 모델 평가 실행 결과 (아직 안 함 — v0.1 GO 후 진행)
- production schema와 eval adapter schema의 양방향 변환 logic (별도 adapter layer 작성 시점)
- 64GB RAM 업그레이드 후 part 2 모델 추가 (Qwen3.6-35B-A3B 등 — §9.2 3단계)
- 카테고리 가중치 결정 (§9.1 한계 5번 — 별도 결정)

---

## §4. 본 R0 review가 보는 것 (scope 안)

다음은 본 R0의 검토 대상:

- §0~§9 본문 전체 (특히 §4~§7의 13개 prompt 명세)
- 공통 system prompt (§1) 의 안전 원칙이 충분한지
- 평가 태그 13종 (§3) 의 정의가 명확하고 자동 채점 가능한지
- 각 prompt의 required/forbidden/format/hard_fail이 일관되고 자동 채점 가능한지
- A_03 (약어 보존 stress) / D_02 (PHI substring) / D_03 (schema strict) 의 stress level이 충분한지

---

## §5. 첨부

- **`local-llm-eval-prompts-clinical-assist-v0.1.md`** (1240 lines) — 검토 대상 본 산출물 (별도 파일)

---

## §6. 다음 단계

GPT R0 응답 수령 후:

- **R0 GO** → v0.1 freeze + §9.2 1단계(32GB quick rerun) 진입 + 자동 채점 스크립트 작성(별도 round)
- **R0 CONDITIONAL GO** → Must-fix/Should-fix 반영 → v0.2 작성 → R0 v2 재검토
- **R0 NOT GO** → 설계 단계 복귀, 카테고리/scope 재논의

---

## §7. GPT에게 직접 전달할 한 줄

> 본 v0.1은 이전 GPT review 4 조건(rule_classification 재가공 / A_03 원문 보존 stress / D 3개 / 4층 rubric)을 모두 반영한 평가셋 초안입니다. R0 GO 가능 여부와 함께 카테고리 누락 / 역할 위반 / PHI 위험 / 채점 불명확성 4축을 검토해주세요. 추가로 scenario 완전성과 schema 정합도 확인 부탁드립니다.

---

**packet 끝**
