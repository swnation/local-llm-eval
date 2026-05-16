# Project Context — Local LLM Eval

> **새 세션 진입 시 가장 먼저 읽는 파일.** README/리포트 전체 다시 읽지 말고 여기서 시작.
> 마지막 갱신: 2026-05-16 (R3 sign-off + Step 4 quick rerun 완료, R4 review 대기 중)

---

## §1. 프로젝트 정체성

`c:\Github\local-llm-eval\` — clinical-assist 시스템의 **보조 local LLM 평가** 폴더. clinical-assist 본 프로젝트(`projects/clinical-assist/`)와 분리.

평가 대상: clinical-assist의 OCR + master DB matcher + parser + deterministic rule engine 결과 위에 **설명·정리·문장화·리뷰**를 담당할 local LLM.

---

## §2. LLM 역할 정의 (절대 변경 금지)

| 한다 | 안 한다 |
|---|---|
| 차팅 문장 정리 (A) | OCR 주엔진 / 정본 추출 |
| NEEDS_REVIEW 이유 설명 (B) | hard safety 판단 |
| Rule finding → report 문장화 (C) | 자동 수정 / 자동 확정 |
| JSON+PHI safe summary (D) | 처방 변경 / 임상 확정 지시 |

→ **LLM은 판단 엔진이 아닌 설명·정리·검토 보조 엔진**.

---

## §3. 현재 상태 (2026-05-16 기준)

| 단계 | 상태 |
|---|---|
| v0.1 → v0.2 prompt set + R0/R1 review | 완료 (R1 GO) |
| Step 1 harness 조정 (v0.2 JSON + scorer schema + README) | 완료 (R2 GO) |
| Step 2 `score_runner.py` 작성 (SCORING_CONTRACT.md 구현) | 완료 (R3 GO) |
| Step 3 D smoke + Step 4 quick rerun (7 모델 × 13 prompts) | 완료, exaone4만 VRAM OOM skip |
| 보조 실험 (chatml fallback / gpt-oss medium / D_02 retry / A_02 retry) | 완료 |
| **R4 review (결과 해석 sign-off)** | **packet 작성됨, codex 응답 대기 중** |
| 64GB part 2 (Qwen3.6-35B/Gemma 4 26B,31B/magistral/exaone4 split) | R4 GO 후 진입 |

---

## §4. 핵심 결정 (R1~R3 누적)

### §4.1 평가셋 구조 (v0.2 final, R1 GO)
- A 차팅 정리 4 / B NEEDS_REVIEW 설명 3 / C rule finding 문장화 3 / D JSON+PHI 3 = **13개**
- 4층 rubric: `required_elements` / `forbidden_elements` / `format_requirements` / `hard_fail`
- 평가 태그 **15종** (자동/수동 분리)

### §4.2 scorer contract (R2 + R3 sign-off)
- 5단계 검사 우선순위: `hard_fail → forbidden → required → format → score`
- D 카테고리는 `required_layer: "json_schema"` 로 `required_elements` 대체
- 점수 분기 순서: `0 → 2 → 5 → 4 → 3 → 1` (R3 must-fix 반영)
- 정확한 spec: [SCORING_CONTRACT.md](SCORING_CONTRACT.md)

### §4.3 NB-3 (R1 비차단 의견, scorer 처리)
- A 카테고리 (영어 의료 약어 보존 의도) 응답에 `MIXED_LANGUAGE` 자동 hard_fail **금지**
- `category_meta.A_charting.language_policy = "ko_with_medical_en_allowed"` 플래그로 표시
- scorer는 해당 플래그 시 자동 적용 X

### §4.4 PHI 정책
- 출력은 `case_id` 만 사용 — 환자명/차트번호/주민번호/요청되지 않은 patient_context 출력 금지
- D_02는 의도적 stress test (input에 PHI 포함, output substring 검사)

---

## §5. 금지사항 (round별)

### R4 진행 중 금지
- v0.2 prompt 본문 수정 (must-fix 발견 시만 예외)
- scoring rubric 재설계 (채점 결과를 뒤집는 bug 발견 시만 예외)
- production 최종 채택 확정 (32GB only 평가 — 64GB part 2 후 결정)
- `_scored_*.json` 직접 편집 (재실행으로만 갱신)

### 항상 금지
- archive 폴더(`knowledge-archive/`) 산출물 직접 수정 (동결 스냅샷)
- `prompts/archive/test_suite_v1.json` 사용 (v0.2로 대체됨)
- LM Studio provider 모델 추가 (Ollama 통일 결정)

---

## §6. 현재 production 후보 (provisional, R4 대기 중)

**시나리오 C 추천**: `gpt-oss-20b 단독 + dynamic reasoning_effort`
- D 카테고리: `reasoning_effort='low'` (avg 4.67, hard_fail 0)
- A/B/C 카테고리: `reasoning_effort='medium'` (C avg 2.00→3.33 실증)
- hard_fail 0건 + 단일 모델 운영 + 모델 swap 비용 없음

**대안**:
- 시나리오 A (clinical-hari-q5 단독): 점수 1위(3.15)지만 A_02 단발 quirk + JSON 응답 경향 — 운영 패치 필요
- 시나리오 D (역할 분리): hari-14b-chatml = Formatter (A 3.00 1위) + 다른 모델 조합

최종 결정은 **64GB part 2에서 Qwen3.6-35B-A3B 등 추가 평가 후**.

---

## §7. 다음 액션 (우선순위 순)

1. **R4 codex review 진행** — packet + report.md만 먼저 전달. 응답 기다림.
2. **R4 응답이 GO이면**: gpt-oss medium A/B/D 검증 (현재 C만 측정됨) → 64GB part 2 진입 준비
3. **R4 응답이 CONDITIONAL GO이면**: Q4의 추가 검증 항목 수행 → R4.1
4. **64GB part 2**: Qwen3.6-35B-A3B (1순위, Apache + a3b MoE) / Gemma 4 26B,31B / magistral 재시도 / exaone4 GPU+CPU split
5. v0.3 정정 (must-fix 후보): D_01 `"변경"` 어미 명시 / A_04 `[확인 필요]` marker 강화 / sentence count tolerance ±1→±2 — SCORING_CONTRACT.md §13 참조

---

## §8. 핵심 파일 경로

### Spec / 운영 기준
- [README.md](README.md) — 폴더 진입점 + 실행 가이드
- [SCORING_CONTRACT.md](SCORING_CONTRACT.md) — scorer 행동 정확 명세 (R3 sign-off)
- [prompts/test_suite_v0.2.json](prompts/test_suite_v0.2.json) — v0.2 final 13 prompts (운영본)
- [prompts/local-llm-eval-prompts-clinical-assist-v0.2.md](prompts/local-llm-eval-prompts-clinical-assist-v0.2.md) — 문서 정본

### 도구
- [eval_runner_auto.py](eval_runner_auto.py) — 자동 모드 평가 runner
- [eval_runner.py](eval_runner.py) — 수동 모드
- [score_runner.py](score_runner.py) — 자동 채점 (SCORING_CONTRACT.md 구현체)

### Config
- [models_config_quick_rerun.json](models_config_quick_rerun.json) — 7 모델 all-ollama
- [models_config_d_smoke.json](models_config_d_smoke.json) — D smoke용 2 모델
- [models_config_part2.json](models_config_part2.json) — 64GB용 (Qwen3.6-35B 등)
- [models_config_hari{8,14}b_chatml.json](models_config_hari14b_chatml.json) — 보조 실험용

### Review packets
- [reviews/review-packet-v0.1-r0.md](reviews/review-packet-v0.1-r0.md) + [gpt-r0-review-response.md](reviews/gpt-r0-review-response.md)
- [reviews/review-packet-v0.2-r1.md](reviews/review-packet-v0.2-r1.md) + [gpt-r1-review-response.md](reviews/gpt-r1-review-response.md)
- [reviews/codex-r2-response.md](reviews/codex-r2-response.md) — Step 1 산출물 review (CONDITIONAL GO → GO)
- [reviews/codex-r3-response.md](reviews/codex-r3-response.md) — compute_score 분기 (CONDITIONAL GO → GO)
- [reviews/review-packet-v0.2-r4-quick-rerun.md](reviews/review-packet-v0.2-r4-quick-rerun.md) ★ **현재 진행 round**

### Step 4 산출물
- [reviews/quick-rerun-2026-05-16-report.md](reviews/quick-rerun-2026-05-16-report.md) — 종합 리포트
- `results/_scored_quick_rerun_20260516.{md,json}` — 채점 결과
- `results/_scored_{hari{8,14}b_chatml,gpt_oss_medium}_20260516.{md,json}` — 보조 실험 채점
- `results/findings_index.jsonl` — retrieval-friendly index (다음에 생성)
- [reviews/session-summary-2026-05-16-step1.md](reviews/session-summary-2026-05-16-step1.md) — Step 1 세션 정리

### Archive (동결 스냅샷)
- `c:\Github\knowledge-archive\projects\clinical-assist\local-llm-eval\` @ f74181c (2026-05-15)
- 직접 수정 금지

---

## §9. 새 세션 entry checklist

새 Claude 세션 들어왔을 때 순서:

1. 이 파일 읽기 (PROJECT_CONTEXT.md) — 1분
2. §3 현재 상태에서 어디부터 진입할지 확인
3. 필요 시 specific 파일만 (§8 참조)
4. R4 진행 중이면 [review-packet-v0.2-r4-quick-rerun.md](reviews/review-packet-v0.2-r4-quick-rerun.md) + codex 응답 (있을 시) 확인
5. 새로운 결정 발생 시 본 파일의 §3/§4/§6/§7 갱신 (필수)

→ **세션 종료 전 본 파일 갱신은 약속**.

---

**End of PROJECT_CONTEXT.md** — 새 세션은 여기서 시작.
