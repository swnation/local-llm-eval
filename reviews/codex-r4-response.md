# Codex R4 review 처리 응답 — 2026-05-16

> R4 CONDITIONAL GO 응답에 대한 처리 보고. Must-fix 1 (gpt-oss medium A/B/D 검증) 완전 반영 + Should-fix 4 / Minor 2 톤 조정. R4 GO sign-off 요청 (또는 추가 조건 의견).

---

## §0. 판정 요청

R4 GO 요청 — provisional production candidate 승격.

R4 CONDITIONAL GO의 must-fix 항목 (gpt-oss medium A/B/D 검증)을 즉시 반영. 결과는 **시나리오 C 가설을 valid로 유지하되 운영 범위를 좁히는 방향**으로 정착. report.md / PROJECT_CONTEXT.md / findings index 모두 갱신.

---

## §1. Must-fix 반영

### MF-1 — gpt-oss-20b medium A/B/D 검증

**Codex 의견**: 시나리오 C가 "D=low, A/B/C=medium" 권고였으나 medium은 C만 측정됨. A/B/D에서 medium이 JSON strict / verbosity / forbidden 유지하는지 확인 전에는 provisional production candidate로 승격 불가.

**처리**: 즉시 실행. `gpt-oss:20b` + `reasoning_effort='medium'` × 10 prompts (A_01~A_04 + B_01~B_03 + D_01~D_03).

**산출물**:
- 실험 스크립트: `tests/experiment_gpt_oss_medium_abd.py`
- raw: `results/gpt-oss-20b-medium-abd_20260516_210613.json`
- scored: `results/_scored_gpt_oss_medium_abd_20260516.{md,json}`
- 본문 반영: `reviews/quick-rerun-2026-05-16-report.md` §5.7 신설

**결과 표**:

| 카테고리 | low (baseline) | medium (§5.7) | Δ | 해석 |
|---|---|---|---|---|
| A_charting | 2.50 | 2.50 | 0 | medium 이점 없음 (A_01:2, A_02:2, A_03:3, A_04:3 — low와 동일) |
| B_needs_review | 2.33 | 2.33 | 0 | medium 이점 없음 (B_01:2, B_02:3, B_03:2 — low와 동일) |
| D_json_phi | 4.67 | **3.00** | **-1.67** ★ | **D_02에서 ```json fence hard_fail** — low에선 정상 |
| HF# | 0 | **1** | +1 | medium은 D에서 위험 |

→ **결정적 발견**: medium은 D_02 응답을 `` ```json ... ``` `` fence로 감쌈. low에서는 raw JSON 정상 반환. **medium은 D에 사용 금지**.

→ **A/B는 medium 이점 0건** — 시간/메모리 cost 대비 이득 없음.

### 운영 정책 재조정 (최초 권고 → 갱신)

| 카테고리 | 최초 (R4 packet §3 Q1) | **갱신 (§5.7 검증 후)** |
|---|---|---|
| A | medium | **low** |
| B | medium | **low** |
| C | medium | medium (유지) |
| D | low | low (유지) |

→ "C만 medium, 나머지는 low" 로 좁혀짐. medium 적용 범위 축소.

### 시나리오 C 종합 avg 재계산

`(A:2.50×4 + B:2.33×3 + C:3.33×3 + D:4.67×3) / 13 =` **3.15**

- 점수상: clinical-hari-q5-current와 동률
- hard_fail: **0건** (D=low 유지 시) — clinical-hari는 A_02 단발 1건
- 운영 단순성: gpt-oss는 task-format overlay 없이 동등 점수 — clinical-hari는 prose 강제 overlay 필요 (§5.6)

→ **시나리오 C를 provisional production candidate 로 권고하는 근거 충분**.

---

## §2. Should-fix 반영

### SF-1 — "provisional hypothesis" → "provisional production candidate" 표현 승격

**Codex 의견**: A/B/D medium 검증 후 승격 가능. 현재는 hypothesis 단계.

**처리**: §5.7 MF-1 검증 후 **승격**. report.md §7과 §0/§2/§4 모두 "provisional production candidate (R4 CONDITIONAL GO → MF-1 검증 후 GO)" 로 갱신.

### SF-2 — clinical-hari-q5 점수 1위 보류 해석 합리

변경 없음. report.md §7 시나리오 A 항목에 task-format overlay 운영 리스크 명시 강화.

### SF-3 — hari-14b-chatml = role-split option only

**처리**: §7 시나리오 D 갱신 — "단일 모델 운영 후보 아님 — role-split option으로만 유지" 명시. D 카테고리 hard_fail 3건이라 단독 운영 부적합.

### SF-4 — 64GB 전 필수 = gpt-oss medium A/B/D 하나만

**처리**: §5.7로 즉시 닫음. ministral template / clinical-hari retry xN / gpt-oss high 는 §9 다음 액션의 (선택) 항목으로 남김.

---

## §3. Minor 반영

### MN-1 — report §7 clinical-hari "가장 안정적" 표현 톤 조정

**처리**: 갱신 완료.

Before: "시나리오 A (단일 모델): clinical-hari-q5-current. 가장 안정적 production 후보"
After: "시나리오 A (단일 모델, clinical-hari-q5): 점수상 가장 강한 단일 모델 후보(avg 3.15)이나, A_02 단발 빈응답 + A 카테고리 응답이 일관 JSON 형식으로 옴 → task-format overlay 운영 필요. retry로만 해결되는 단순 quirk 아님."

### MN-2 — D_01 "변경" false positive v0.3 backlog

**처리**: 변경 없음. 이미 SCORING_CONTRACT.md §13 backlog에 누적됨 (Codex R3 처리 시). R4 결과 해석을 뒤집지 않음.

---

## §4. 변경 파일 요약

| 파일 | 변경 |
|---|---|
| `tests/experiment_gpt_oss_medium_abd.py` | 신규 — MF-1 실행 스크립트 |
| `results/gpt-oss-20b-medium-abd_20260516_210613.json` | 신규 — raw 결과 |
| `results/_scored_gpt_oss_medium_abd_20260516.{md,json}` | 신규 — 채점 결과 |
| `reviews/quick-rerun-2026-05-16-report.md` | §0 TL;DR / §2 ranking / §5.2 결론 정정 / **§5.7 신설** / §7 시나리오/권장결정 갱신 |
| `PROJECT_CONTEXT.md` | §3 상태 / §6 production 후보 갱신 (R4 CONDITIONAL GO → MF-1 반영) |
| `results/findings_index.jsonl` + `findings_index.README.md` | 재생성 (118 entries, gpt-oss-20b-medium 13 entries 포함) |
| `reviews/codex-r4-response.md` | 신규 — 이 문서 |

→ Prompt 본문 / scorer 코드 / scoring rubric 변경 0건. R4 Non-goals 준수.

---

## §5. R4.1 sign-off 요청 (codex)

R4 CONDITIONAL GO의 단일 must-fix를 §5.7로 닫음. 발견 사항(medium은 D에 위험, A/B 점수 향상 없음)으로 시나리오 C 운영 정책이 더 보수적 방향(C만 medium)으로 정착. 점수상 clinical-hari와 동률 + hard_fail 0건 우위.

**Codex 추가 sign-off 항목 요청**:

1. 시나리오 C의 **운영 정책 재조정 ("C만 medium, D/A/B=low")** 이 R4 GO 조건을 충족하는가? 또는 추가 should-fix 있는가?
2. report.md §7과 §0의 "provisional production candidate" 승격 표현이 적절한가?
3. 64GB part 2 진입 전 추가 검증 항목 (gpt-oss high 1~2 prompt 실험, ministral V7 template Modelfile 재시도 등)이 **필수 아닌 선택**으로 두는 결정이 합리적인가?

추가 must-fix 없으면 **R4 GO** 로 간주하고 64GB part 2 진입 준비 단계로 이동. CONDITIONAL GO 추가 발생 시 R4.2 round.

---

## §6. v0.3 backlog (R4 처리 시 누적)

이번 round에서 신규 backlog 항목 없음. 기존 누적 유지:

| 항목 | 출처 |
|---|---|
| D_01 forbidden "변경" 어미 명시 (false positive) | SCORING_CONTRACT §13 (R3 처리) / R4 MN-2 동일 |
| A_04 [확인 필요] marker 강화 | SCORING_CONTRACT §13 |
| sentence count tolerance ±1→±2 | SCORING_CONTRACT §13 |
| reasoning 모델 D 카테고리 sub-rubric | SCORING_CONTRACT §13 |
| MIXED_LANGUAGE 짧은 응답 skip | SCORING_CONTRACT §13 |
| operational guidance: gpt-oss dynamic effort | §5.7 신규 (운영 문서로 분리 권장) |
| operational guidance: hari ChatML Modelfile | §5.1/§5.5 (이미 docs/local-llm-upgrade-plan.md §6 반영됨) |

---

**문서 끝**

본 round는 R2/R3 같은 must-fix only loop 패턴 그대로 — must-fix 1개 즉시 반영 + R4.1 sign-off 요청.
