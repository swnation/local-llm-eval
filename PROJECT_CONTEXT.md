# Project Context — Local LLM Eval

> **새 세션 진입 시 가장 먼저 읽는 파일.** README/리포트 전체 다시 읽지 말고 여기서 시작.
> 마지막 갱신: 2026-05-18 (64GB Part 2 (a'') gpt-oss maxtok8k fair-compare 완료 — Scenario A 확정)
>
> 64GB RAM 업그레이드 완료. Part 2 진입: (a) 2048-cap FAIL → (a') Qwen maxtok8k 3.77 → (a'') gpt-oss maxtok8k 3.23 (Δ vs 2048: -0.08, Scenario A). **Qwen +0.54 fair-compare lead 확정** (라벨 정합성 OK). 다음 진입은 #9 MoE+dense round (RAG 전략 판단 trigger).

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

## §3. 현재 상태 (2026-05-17 기준)

| 단계 | 상태 |
|---|---|
| v0.1 → v0.2 prompt set + R0/R1 review | 완료 (R1 GO) |
| Step 1 harness 조정 (v0.2 JSON + scorer schema + README) | 완료 (R2 GO) |
| Step 2 `score_runner.py` 작성 (SCORING_CONTRACT.md 구현) | 완료 (R3 GO) |
| Step 3 D smoke + Step 4 quick rerun (7 모델 × 13 prompts) | 완료, exaone4만 VRAM OOM skip |
| 보조 실험 (chatml fallback / gpt-oss medium / D_02 retry / A_02 retry) | 완료 |
| R4 review (결과 해석 sign-off) | 완료 — MF-1 (gpt-oss medium A/B/D) 반영 (§5.7) |
| R4.1 — MF-1 검증 codex sign-off | **GO** (2026-05-16, Track 1 closed) |
| **64GB part 2 config skeleton** (Qwen3.6-35B / Gemma 4 26B,31B / magistral / exaone4 split) | **갱신 완료 (2026-05-16)** — Ollama provider 통일. Qwen3.6은 `qwen3.6:35b-a3b` pull 완료, 나머지는 ollama_name/import 실측 대기 |
| **Qwen3.6-35B-A3B 32GB preview** | **완료 (2026-05-16, part2_preflight default KV / thinking-off)** — D smoke 4.67 HF0, full 13 avg 3.31 HF0 |
| **v0.3 scoring/prompt 정정** | **완료 (2026-05-17)** — D_01 forbidden false-positive / A_04 marker / sentence tolerance ±2 / format-only score=4 반영. Qwen raw v0.3 rescore: avg 3.38 HF0 |
| **Track 1 v0.3 raw rescore 비교** | **완료 (2026-05-17)** — quick_rerun 7 + gpt-oss medium C/ABD + HARI ChatML 기존 raw 재채점. gpt-oss dynamic v0.3 **3.31 HF0**, Qwen v0.3 **3.38 HF0** |
| **64GB RAM 업그레이드** | **완료 (2026-05-17)** — Part 2 본 실행 진입 |
| **Qwen3.6-35B-A3B thinking-on 64GB part2 (a)** | **D smoke FAIL (2026-05-17, part2_64gb_defaultkv_thinking_on)** — D_01/D_03 `EMPTY_RESPONSE` (completion_tokens 2048 cap, reasoning trace exhausted output budget). D_02만 5점. D avg 1.67 / hard_fail 2. Full 13 보류. [report](reviews/qwen35b-part2-64gb-thinking-on-2026-05-17-report.md) |
| **Qwen3.6-35B-A3B thinking-on 64GB part2 (a') maxtok8k diagnostic** | **D smoke PASS + Full 13 PASS (2026-05-18, part2_64gb_diagnostic_maxtok8k_thinking_on)** — `max_tokens=8192` override. D smoke 5.00 HF0 (tokens 1642–2417, cap 미도달). Full 13 avg **3.77 HF0** (A 3.75 / B 3.33 / C 3.00 / D 5.00). 32GB thinking-off 대비 A +1.25, Total +0.39. 단 8192 budget이라 2048-cap baselines과 직접 비교 금지 — diagnostic 라벨. [report](reviews/qwen35b-part2-64gb-thinking-on-maxtok8k-2026-05-18-report.md) |
| **gpt-oss dynamic 64GB part2 (a'') maxtok8k fair-compare** | **PASS — Scenario A 확정 (2026-05-18, fair_compare_gpt_oss_dynamic_maxtok8k)** — low+medium 양쪽 full 13 (max_tokens=8192). Composite (A/B/D low + C medium) **3.23 HF0**, 2048 baseline 3.31 대비 **Δ -0.08** (noise). 토큰 최대 1232 (8k cap 멀리 미달). gpt-oss는 8k에서 score 거의 안 움직임 — Qwen maxtok8k 3.77 vs gpt-oss maxtok8k 3.23 = **+0.54 fair-compare lead (apples-to-apples)** 라벨 정합 확보. Medium D 진단 finding: 2048의 §5.7 fence fail이 8k에서 재현 안 됨 (5.00 HF0). §5 rule 변경 근거로는 불충분. [report](reviews/gpt-oss-dynamic-maxtok8k-fair-compare-2026-05-18-report.md) |

---

## §4. 핵심 결정 (R1~R3 누적)

### §4.1 평가셋 구조 (v0.3 current / v0.2 baseline 보존)
- A 차팅 정리 4 / B NEEDS_REVIEW 설명 3 / C rule finding 문장화 3 / D JSON+PHI 3 = **13개**
- 4층 rubric: `required_elements` / `forbidden_elements` / `format_requirements` / `hard_fail`
- 평가 태그 **15종** (자동/수동 분리)
- 현재 신규 실행 기본 prompt: `prompts/test_suite_v0.3.json`
- v0.2 quick rerun baseline은 `prompts/test_suite_v0.2.json` 에 보존. v0.2/v0.3 결과 비교 시 prompt version label 필수.

### §4.2 scorer contract (R2/R3 sign-off + v0.3 정정)
- 5단계 검사 우선순위: `hard_fail → forbidden → required → format → score`
- D 카테고리는 `required_layer: "json_schema"` 로 `required_elements` 대체
- 점수 분기 순서: `0 → 2 → 5 → 4 → 3 → 1` (R3 must-fix 반영)
- v0.3 정정: format-only fail은 4점 / sentence tolerance 기본 ±2 / A_04 `required_marker` 구조화 / D_01 `"변경"` 단순 명사 false-positive 제거
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

## §6. 현재 production 후보 (provisional, R4.1 GO 이후)

**시나리오 C 권고**: `gpt-oss-20b 단독 + dynamic reasoning_effort` ★ provisional production candidate
- **C 카테고리**: `reasoning_effort='medium'` (avg 2.00→3.33 실증)
- **D 카테고리**: `reasoning_effort='low'` (v0.2 avg 4.67, v0.3 raw rescore 5.00, hard_fail 0. medium은 D_02 fence hard_fail §5.7)
- **A/B 카테고리**: `reasoning_effort='low'` (medium 점수 향상 0건, §5.7)
- v0.2 종합 avg **3.15** (clinical-hari와 동률) + **hard_fail 0건** (D=low 유지 시)
- v0.3 raw rescore 종합 avg **3.31 / hard_fail 0** (A 2.75 / B 2.33 / C 3.33 / D 5.00). Qwen 비교는 이 값을 기준으로 보는 것이 apples-to-apples.

→ 최초 R4 권고였던 "A/B/C=medium" 은 §5.7 MF-1 검증에서 **"C만 medium, D/A/B=low"** 로 좁혀짐 (medium은 D에 위험).

**대안**:
- 시나리오 A (clinical-hari-q5 단독): 점수 1위(3.15)지만 A_02 retry 시 JSON 응답 경향 — task-format overlay 필요. 운영 단순성에서 시나리오 C 우위
- 시나리오 D (역할 분리, Formatter only): hari-14b-chatml = A 1위 (3.00). 단 D 모두 HF라 단일 모델 후보 X — role-split option으로만 유지

최종 결정은 **64GB part 2에서 Qwen3.6-35B-A3B 등 추가 평가 후**.

**신규 challenger (32GB preview)**:
- `qwen3.6:35b-a3b` + `reasoning_effort='none'` (`thinking-off`, default KV, `part2_preflight`)
- full 13 prompts: v0.2 score **avg 3.31 / hard_fail 0**, v0.3 rescore **avg 3.38 / hard_fail 0**. D JSON+PHI는 v0.3 기준 **5.00 / hard_fail 0**, PHI stress 통과.
- gpt-oss dynamic v0.3(3.31 HF0)보다 avg는 높지만 격차는 **+0.08**로 축소됨. A 약어 보존과 B_01 exact/name mismatch 설명에서 required 누락이 있어 **즉시 production 교체가 아니라 64GB part 2 priority 1 challenger** 로 유지.
- 자세한 해석: [reviews/qwen35b-preview-32gb-2026-05-16-report.md](reviews/qwen35b-preview-32gb-2026-05-16-report.md)

**Qwen thinking-on 64GB part 2 (2026-05-17)**:
- `qwen3.6:35b-a3b` + `reasoning_effort='medium'` (`thinking-on`, default KV, `part2_64gb_defaultkv_thinking_on`)
- D smoke **FAIL**: D_01/D_03 `EMPTY_RESPONSE` (completion_tokens=2048 cap, reasoning trace consumed output budget). D_02만 통과 (5점). D avg **1.67 / hard_fail 2**. Full 13 보류.
- 결론: 현재 production 후보 (gpt-oss dynamic 3.31 HF0) **유지**. Qwen thinking-on은 default-ctx 단일 정책으로는 D 자동화 안전성 미달.
- 후속 가설: ① Qwen용 dynamic policy (C/A/B=thinking-on, D=thinking-off) ② max_tokens 상향 별도 round. 이번 라운드는 fair-compare 보존을 위해 retry 안 함.
- 자세한 해석: [reviews/qwen35b-part2-64gb-thinking-on-2026-05-17-report.md](reviews/qwen35b-part2-64gb-thinking-on-2026-05-17-report.md)

**Qwen thinking-on 64GB part 2 (a') maxtok8k diagnostic (2026-05-18)**:
- `qwen3.6:35b-a3b` + `reasoning_effort='medium'` + `max_tokens=8192` (`part2_64gb_diagnostic_maxtok8k_thinking_on`)
- D smoke **PASS** (5.00 HF0, completion_tokens 1642–2417, 8192 cap 미도달) → Full 13 진입
- Full 13: **avg 3.77 / HF 0** (A **3.75** / B 3.33 / C 3.00 / D 5.00). 32GB thinking-off (3.38) 대비 A +1.25 / Total +0.39. 모든 prompt가 8k cap 미도달, A_02가 최대 4449 tokens.
- 자세한 해석: [reviews/qwen35b-part2-64gb-thinking-on-maxtok8k-2026-05-18-report.md](reviews/qwen35b-part2-64gb-thinking-on-maxtok8k-2026-05-18-report.md)

**gpt-oss dynamic 64GB part 2 (a'') maxtok8k fair-compare (2026-05-18)**:
- `gpt-oss:20b` × 2 (low + medium) at `max_tokens=8192` (`fair_compare_gpt_oss_dynamic_maxtok8k`)
- low full 13: **3.15 HF0** (A 3.00 / B 2.67 / C 2.00 / D 5.00). 2048 대비 +0.15 (noise)
- medium full 13: **3.23 HF0** (A 3.50 / B 2.00 / C 2.33 / D 5.00). C 카테고리 2048의 3.33에서 8k에서 2.33으로 하락 (-1.00) — sampling noise 가능
- **Composite (A/B/D low + C medium, HF selected-set)**: **3.23 HF0**. 2048 composite 3.31 대비 **Δ -0.08** (noise 수준)
- 토큰: low 최대 485, medium 최대 1232. 8k cap 한 번도 미도달 — **2048 cap이 gpt-oss에는 충분했다는 증거**
- 가설 판정: **Scenario A 확정** (gpt-oss는 maxtok8k에서 거의 안 움직임). 8k는 budget overkill
- Medium D 진단 finding: **medium D도 5.00 / HF 0, JSON parse 모두 OK, fence/think leak 없음**. 2048 cap의 §5.7 `medium D=fence fail` 패턴이 8k에서 재현 안 됨. 흥미로운 신호지만 단일 round 진단으로 §5 forbidden rule 변경 근거 불충분 — 별도 multi-seed verification 필요
- **Qwen vs gpt-oss apples-to-apples (both maxtok8k)**: **Qwen 3.77 vs gpt-oss 3.23 = +0.54** (A +0.75 / B +0.66 / C +0.67 / D 0). 라벨 정합성 확보된 진짜 격차
- 자세한 해석: [reviews/gpt-oss-dynamic-maxtok8k-fair-compare-2026-05-18-report.md](reviews/gpt-oss-dynamic-maxtok8k-fair-compare-2026-05-18-report.md)

**결론 (production candidate, R5 pending)**:
- `gpt-oss-20b dynamic` (2048 cap, 3.31 HF0) **provisional 유지**
- Qwen 64GB thinking-on maxtok8k (3.77 HF0)는 **+0.54 fair-compare lead 확정된 challenger**
- 즉시 displacement 보류 사유: ① 운영 latency (Qwen 35B 38분 vs gpt-oss 6분, full 13 기준 ~6×) ② VRAM split (Qwen 61%/39% CPU/GPU vs gpt-oss 20%/80%) ③ maxtok8k 비용 (4× output budget) ④ Round 9 dense/MoE 후보 미측정 — RAG-augmented 작은 모델이 더 나은 architecture일 가능성
- 최종 후보 결정: Round 9 결과 후

---

## §7. 다음 액션 (우선순위 순) — R4.1 GO 반영

현재 작업은 두 트랙으로 분리:

- [Track 1 — v0.2 Local LLM Eval Experiments](docs/experiment-track-2026-05-16.md): R1~R4.1 sign-off 완료, scorer/D smoke/quick rerun/MF-1 verification 모두 닫음.
- [Track 2 — Local LLM Upgrade Plan](docs/local-llm-upgrade-plan.md): Qwen3.6 preview, q8 KV cache, 64GB/128GB, retrieval/memory 확장.

**Track 1 마무리 상태**: R4 CONDITIONAL GO → MF-1 (gpt-oss medium A/B/D) 반영 → **R4.1 GO** (codex sign-off 2026-05-16).

다음 액션:

1. ~~**64GB part 2 준비**: `models_config_part2.json` 갱신~~ → **완료 (2026-05-16)**. ollama provider 통일 / Qwen3.6-35B-A3B PRIORITY 1 / Gemma 4 26B,31B / magistral retry / exaone4 split policy 반영. 잔여 작업: Gemma/magistral/exaone4 ollama_name 실측/import.
2. ~~**Qwen3.6-35B-A3B 32GB preview**~~ → **완료 (2026-05-16)**. `qwen3.6:35b-a3b`, default KV, `reasoning_effort='none'`, D smoke 후 full 13 실행. avg 3.31 / hard_fail 0.
3. **(선택) q8 KV cache 정책 테스트**: `OLLAMA_KV_CACHE_TYPE=q8_0` 환경변수로 별도 round. baseline과 분리 라벨링 필수 (Track 2 §3). Qwen default-KV preview가 이미 통과했으므로 q8은 품질/메모리 비교 목적일 때만.
4. **(선택) gpt-oss high 1~2 prompt 실험**: medium보다 더 좋아지는지 / 속도 trade-off
5. **(선택) ministral V7 template Modelfile 재시도**: D_02 1 token EOT 진단
6. ~~**v0.3 정정**: D_01 `"변경"` 어미 명시 / A_04 `[확인 필요]` marker 강화 / sentence count tolerance ±1→±2 / format-only-fail 점수 정의~~ → **완료 (2026-05-17)**. `SCORING_CONTRACT.md`, `score_runner.py`, `prompts/test_suite_v0.3*.json`, regression test 반영.
7. ~~**Track 1 v0.3 raw rescore**~~ → **완료 (2026-05-17)**. 기존 raw만 재채점: quick_rerun 7, gpt-oss medium C/ABD, HARI ChatML. gpt-oss dynamic 3.31 HF0, Qwen 3.38 HF0.
8. **Part 2 본 실행 (64GB 업그레이드 완료 후)** — 최우선. 순서:
   - (a) ~~Qwen3.6-35B-A3B **thinking-on** 본 측정~~ → **D smoke FAIL (2026-05-17)**. D_01/D_03 EMPTY_RESPONSE (output 2048 cap, reasoning trace 소진). full 13 보류. [report](reviews/qwen35b-part2-64gb-thinking-on-2026-05-17-report.md)
   - (a') ~~Qwen thinking-on **maxtok8k diagnostic** retry~~ → **PASS (2026-05-18)**. Full 13 avg 3.77 HF0 (A 3.75 / B 3.33 / C 3.00 / D 5.00). 단 diagnostic 라벨 — 2048-cap baselines과 직접 비교 금지. [report](reviews/qwen35b-part2-64gb-thinking-on-maxtok8k-2026-05-18-report.md)
   - (a'') ~~fair-compare round (gpt-oss dynamic maxtok8k)~~ → **완료 (2026-05-18)**. composite **3.23 HF0** (2048 baseline 3.31 대비 Δ -0.08, Scenario A). Qwen vs gpt-oss apples-to-apples 격차 **+0.54** 확정. [report](reviews/gpt-oss-dynamic-maxtok8k-fair-compare-2026-05-18-report.md)
   - (b) Gemma 4 26B → 31B: `ollama pull` 시도 → registry miss면 GGUF import. `models_config_part2.json` `_status: tbd_verify_ollama_registry_or_import` 항목 해결.
   - (c) magistral retry: ollama-imports/Modelfile.magistral 명시 V7 template으로 생성.
   - (d) exaone4-32b GPU+CPU split: `num_gpu` 단계적 결정 (full → 40 → 32 → 24), `_split` 라벨 분리 round, 다른 모델 동시 로드 금지.
   - (e) 종합: v0.3 기준 Qwen/Gemma/exaone4 vs gpt-oss dynamic 비교 → §6 production 후보 갱신.
9. **MoE / 16GB-VRAM dense 비교 라운드 (진행 예정)** — `qwen3:30b-a3b`, `mixtral:8x7b`, `gemma3:12b`, `qwen3:14b`, `qwen3:8b` 후보. default 2048 cap (gpt-oss dynamic 3.31 baseline과 fair compare). Dense 12-14B가 gpt-oss ±0.3 안에 들면 RAG-augmented 작은 모델 architecture 전략 정당화 / 멀리 떨어지면 큰 모델 답.

→ 다음 우선: **9번 MoE/dense 비교** → **8 (b/c/d) Part 2 잔여 모델**. 3번(q8 KV)·4번(gpt-oss high)·5번(ministral V7)은 Part 2 종료 후 선택 항목.

---

## §8. 핵심 파일 경로

### Spec / 운영 기준
- [README.md](README.md) — 폴더 진입점 + 실행 가이드
- [SCORING_CONTRACT.md](SCORING_CONTRACT.md) — scorer 행동 정확 명세 (v0.3 current)
- [prompts/test_suite_v0.3.json](prompts/test_suite_v0.3.json) — v0.3 current 13 prompts (운영본)
- [prompts/test_suite_v0.2.json](prompts/test_suite_v0.2.json) — v0.2 final 13 prompts (baseline 보존본)
- [prompts/local-llm-eval-prompts-clinical-assist-v0.2.md](prompts/local-llm-eval-prompts-clinical-assist-v0.2.md) — 문서 정본

### 도구
- [eval_runner_auto.py](eval_runner_auto.py) — 자동 모드 평가 runner
- [eval_runner.py](eval_runner.py) — 수동 모드
- [score_runner.py](score_runner.py) — 자동 채점 (SCORING_CONTRACT.md 구현체)

### Config
- [models_config_quick_rerun.json](models_config_quick_rerun.json) — 7 모델 all-ollama
- [models_config_d_smoke.json](models_config_d_smoke.json) — D smoke용 2 모델
- [models_config_part2.json](models_config_part2.json) — 64GB용 (Qwen3.6-35B 등)
- [models_config_qwen35b_thinking_on_64gb.json](models_config_qwen35b_thinking_on_64gb.json) — 64GB 업그레이드 직후 첫 실행용 Qwen thinking-on 단독 config
- [models_config_hari{8,14}b_chatml.json](models_config_hari14b_chatml.json) — 보조 실험용

### Review packets
- [reviews/review-packet-v0.1-r0.md](reviews/review-packet-v0.1-r0.md) + [gpt-r0-review-response.md](reviews/gpt-r0-review-response.md)
- [reviews/review-packet-v0.2-r1.md](reviews/review-packet-v0.2-r1.md) + [gpt-r1-review-response.md](reviews/gpt-r1-review-response.md)
- [reviews/codex-r2-response.md](reviews/codex-r2-response.md) — Step 1 산출물 review (CONDITIONAL GO → GO)
- [reviews/codex-r3-response.md](reviews/codex-r3-response.md) — compute_score 분기 (CONDITIONAL GO → GO)
- [reviews/review-packet-v0.2-r4-quick-rerun.md](reviews/review-packet-v0.2-r4-quick-rerun.md) ★ **현재 진행 round**
- [reviews/claude-code-handoff-64gb-upgrade-2026-05-17.md](reviews/claude-code-handoff-64gb-upgrade-2026-05-17.md) — 64GB 업그레이드 후 Claude Code 복귀용 handoff

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
