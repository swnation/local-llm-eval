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
| **R4 review (결과 해석 sign-off)** | **CONDITIONAL GO** — MF-1 (gpt-oss medium A/B/D) 반영 완료 (§5.7) |
| R4.1 — MF-1 검증 결과 codex 응답 | **대기 중** (R4.1 packet 작성 후 송부 예정) |
| 64GB part 2 (Qwen3.6-35B/Gemma 4 26B,31B/magistral/exaone4 split) | R4.1 GO 후 진입 |

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
- **gpt-oss-20b D 카테고리에 `reasoning_effort='medium'` 사용** (R4.1 §5.7 검증: medium은 D_02에서 `JSON_EXTRA_TEXT` hard_fail. medium improves C only; medium is unsafe for D JSON-only)

---

## §6. 현재 production 후보 (provisional, R4 CONDITIONAL GO → MF-1 검증 완료 → R4.1 codex 응답 대기 중)

**시나리오 C 권고**: `gpt-oss-20b 단독 + dynamic reasoning_effort` ★ provisional production candidate
- **C 카테고리**: `reasoning_effort='medium'` (avg 2.00→3.33 실증)
- **D 카테고리**: `reasoning_effort='low'` (avg 4.67 안정, hard_fail 0. medium은 D_02 fence hard_fail §5.7)
- **A/B 카테고리**: `reasoning_effort='low'` (medium 점수 향상 0건, §5.7)
- 종합 avg **3.15** (clinical-hari와 동률) + **hard_fail 0건** (D=low 유지 시)

→ 최초 R4 권고였던 "A/B/C=medium" 은 §5.7 MF-1 검증에서 **"C만 medium, D/A/B=low"** 로 좁혀짐 (medium은 D에 위험).

**대안**:
- 시나리오 A (clinical-hari-q5 단독): 점수 1위(3.15)지만 A_02 retry 시 JSON 응답 경향 — task-format overlay 필요. 운영 단순성에서 시나리오 C 우위
- 시나리오 D (역할 분리, Formatter only): hari-14b-chatml = A 1위 (3.00). 단 D 모두 HF라 단일 모델 후보 X — role-split option으로만 유지

최종 결정은 **64GB part 2에서 Qwen3.6-35B-A3B 등 추가 평가 후**.

---

## §7. 다음 액션 (우선순위 순) — R4.1 GO 반영

현재 작업은 두 트랙으로 분리:

- [Track 1 — v0.2 Local LLM Eval Experiments](docs/experiment-track-2026-05-16.md): R1~R4.1 sign-off 완료, scorer/D smoke/quick rerun/MF-1 verification 모두 닫음.
- [Track 2 — Local LLM Upgrade Plan](docs/local-llm-upgrade-plan.md): Qwen3.6 preview, q8 KV cache, 64GB/128GB, retrieval/memory 확장.

**Track 1 마무리 상태**: R4 CONDITIONAL GO → MF-1 (gpt-oss medium A/B/D) 반영 → **R4.1 GO** (codex sign-off 2026-05-16).

다음 액션:

1. **64GB part 2 준비**: 진입 전 점검 — `models_config_part2.json` 갱신 (Qwen3.6-35B-A3B 1순위 / Gemma 4 26B,31B / magistral 재시도 / exaone4 GPU+CPU split policy)
2. **(선택) Qwen3.6-35B-A3B 32GB preview**: MoE active-3B 특성상 32GB에서 가능성 있음. `part2_preflight` 라벨로 별도 실행
3. **(선택) q8 KV cache 정책 테스트**: `OLLAMA_KV_CACHE_TYPE=q8_0` 환경변수로 별도 round. baseline과 분리 라벨링 필수 (Track 2 §3)
4. **(선택) gpt-oss high 1~2 prompt 실험**: medium보다 더 좋아지는지 / 속도 trade-off
5. **(선택) ministral V7 template Modelfile 재시도**: D_02 1 token EOT 진단
6. **v0.3 정정 (must-fix 후보)**: D_01 `"변경"` 어미 명시 / A_04 `[확인 필요]` marker 강화 / sentence count tolerance ±1→±2 / format-only-fail 점수 정의 — SCORING_CONTRACT.md §13 참조

→ 1번이 우선. 2~5는 64GB 진입 전 시간 여유에 따라 선택.

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
