# Codex R3 review 처리 응답 — 2026-05-16

> Codex R3 CONDITIONAL GO (Must-fix 1개)에 대한 처리 보고. SCORING_CONTRACT.md §10 compute_score 분기 순서 정정 + 회귀 테스트 + format-only-fail 케이스 backlog 추가.

---

## §0. 판정 요청

R3 GO 요청. Must-fix 1개 완전 반영 + 검증 통과. v0.2 prompt 본문 / D rubric / quick rerun config 변경 없음.

---

## §1. Must-fix 반영

### MF-1 — compute_score 분기 순서 정정

**Codex 의견**: `required_missing_count <= 2` 분기가 `forbidden_present_count >= 3` 검사보다 위에 있어서, forbidden 다수(3+) 케이스가 잘못 score 3으로 분류됨. score_rule 2점 정의("required 중요 누락 3+ 또는 forbidden 다수")를 따르려면 `>= 3` 검사를 score 3 분기보다 위로 올려야 함.

**처리**: 분기 순서를 `0 → 2 → 5 → 4 → 3 → 1` 로 재배치.

**Before**:

```python
if checks["hard_fail"]: return 0
# 5
if req_m == 0 and forb_p == 0 and fmt: return 5
# 4
if req_m == 0 and forb_p <= 2 and fmt: return 4
# 3 ← 이게 forbidden>=3 케이스를 흡수
if req_m <= 2 or (forb_p <= 2 and req_m <= 4): return 3
# 2 ← 도달 불가 (위 3 분기가 흡수)
if req_m >= 3 or forb_p >= 3: return 2
return 1
```

**After**:

```python
if checks["hard_fail"]: return 0
# 2 (먼저 검사 — forbidden 다수/required 중대 누락 흡수 방지)
if req_m >= 3 or forb_p >= 3: return 2
# 5
if req_m == 0 and forb_p == 0 and fmt: return 5
# 4
if req_m == 0 and forb_p <= 2 and fmt: return 4
# 3 (이제 forbidden<=2 강제)
if req_m <= 2 and forb_p <= 2: return 3
return 1
```

→ score 2 정의 (required 3+ OR forbidden 3+) 가 가장 먼저 검사되어 다른 분기에 흡수 안 됨. score 3 분기의 OR도 AND로 변경 (forbidden<=2 강제) — score 4에서 forbidden<=2 + format_pass 요구하니 일관성.

추가: §10 코드 블록 위에 inline 주석으로 R3 must-fix 적용 이유 명시.

---

## §2. 회귀 테스트 결과

분기 순서 변경 후 13 케이스 회귀 테스트:

| Case | req_missing | forbidden | format_pass | hard_fail | score | 의도 |
|---|---|---|---|---|---|---|
| all clean | 0 | 0 | True | False | **5** | ★ |
| req 0 + forb 1 | 0 | 1 | True | False | **4** | minor forbidden |
| req 0 + forb 2 | 0 | 2 | True | False | **4** | minor forbidden |
| **req 0 + forb 3** | **0** | **3** | **True** | **False** | **2** | ★ R3 fix — 이전엔 3 |
| req 1 + forb 0 | 1 | 0 | True | False | **3** | 일부 누락 |
| req 2 + forb 2 | 2 | 2 | True | False | **3** | 경계 |
| **req 2 + forb 3** | **2** | **3** | **True** | **False** | **2** | ★ R3 fix — 이전엔 3 |
| req 3 + forb 0 | 3 | 0 | True | False | **2** | 중대 누락 |
| req 3 + forb 3 | 3 | 3 | True | False | **2** | 둘 다 |
| req 0 + forb 0 + format fail | 0 | 0 | False | False | **3** | §3 참조 |
| req 0 + forb 1 + format fail | 0 | 1 | False | False | **3** | §3 참조 |
| req 1 + forb 1 + format fail | 1 | 1 | False | False | **3** | 일부 누락 |
| hard_fail | 0 | 0 | True | True | **0** | ★ |

→ Codex 명시한 must-fix 케이스 (forbidden ≥ 3) 두 가지 모두 정확히 score 2 반환.

---

## §3. 추가 발견 — format-only-fail 케이스 backlog 추가

회귀 테스트 중 v0.2 `scoring.score_rule` 정의가 명시적이지 않은 경계 케이스 발견:

> `required_missing=0` + `forbidden_present<=2` + `format_pass=False`

이 케이스는:
- score 5/4 분기: `format_pass=True` 요구 → 통과 안 됨
- score 2 분기: `>= 3` 요구 안 충족 → 통과 안 됨
- score 3 분기: `req<=2 and forb<=2` 충족 → **현재 동작 = score 3**
- score 1: "대부분 실패" 정의에 비해 너무 가벼움

→ 현재 동작 (score 3) 은 score_rule 해석상 합리적이지만, 명시적 정의는 없음. v0.3 backlog에 추가:

```
- format-only-fail 케이스의 점수 정의 모호함: required_missing=0 + forbidden_present<=2 +
  format_pass=False 인 경우 v0.2 score_rule이 명시적이지 않음. 현재 compute_score는 3을
  반환. v0.3에서 "format-only-fail → 별도 점수 또는 명시 강제" 정의 권장.
```

→ Codex R3에는 미언급 항목이라 must-fix 아님. v0.3 정정 사항으로 backlog 누적.

---

## §4. 변경 파일 요약

| 파일 | 변경 |
|---|---|
| `SCORING_CONTRACT.md` | §10 compute_score 분기 순서 정정 + inline 주석 추가 / frontmatter에 R3 반영 노트 / §13 backlog에 format-only-fail 항목 추가 |
| `reviews/codex-r3-response.md` | 신규 — 이 문서 |

→ `prompts/test_suite_v0.2.json` / `prompts/test_suite_v0.2_d_only.json` / `README.md` / `models_config_*.json` / `eval_runner*.py` 변경 0건.

---

## §5. v0.3 backlog 누적

| 항목 | 출처 |
|---|---|
| MN-1 A_03 tenderness +/- 우선 표기 명시 | v0.2 작성 시점 |
| MN-2 D_02 PHI substring 일반화 (forbidden_phi_values list) | v0.2 작성 시점 |
| C 카테고리 rule_id를 실제 rules.json v1과 정렬 | v0.2 작성 시점 |
| A 카테고리 인수인계 prompt 1개 추가 검토 | v0.2 작성 시점 |
| HALLUCINATED_FINDING 자동 검출 정밀도 | SCORING_CONTRACT §13 |
| 응답 안의 raw template token 감지 | SCORING_CONTRACT §13 |
| 카테고리별 가중치 (`scoring.category_weights`) | SCORING_CONTRACT §10 |
| **format-only-fail 점수 정의** | **R3 회귀 테스트에서 발견** |

---

## §6. 다음 액션 (변동 없음)

R3 GO 시 다음 그대로:

1. `ollama-imports/import.ps1` 실행
2. D smoke: `python eval_runner_auto.py --config models_config_d_smoke.json --prompts prompts/test_suite_v0.2_d_only.json`
3. D smoke 응답 사람 눈 sanity check
4. Step 2 `score_runner.py` 작성 — SCORING_CONTRACT.md를 spec으로 (R3 정정된 분기 순서 적용)
5. D smoke 응답을 fixture로 scorer 회귀 테스트
6. 전체 7 모델 × 13 prompt quick rerun
7. 결과 분석 → v0.3 정정 또는 64GB part 2

---

## §7. R3 sign-off 요청

R3 추가 must-fix 없으면 위 다음 액션 그대로 진입. 회귀 테스트 결과(§2)와 format-only-fail backlog(§3) 모두 명시했으니 sign-off 가능 상태.

**문서 끝**
