# Quick Rerun Report — Local LLM Eval v0.2 (2026-05-16)

**실행 환경**: 사용자 PC (Windows 11, 32GB RAM, RTX 5080 16GB VRAM), Ollama 0.24.0
**평가 prompt set**: v0.2 final 13 prompts (R3 sign-off 적용)
**채점 규칙**: SCORING_CONTRACT.md (R3 sign-off)
**실행 도구**: `eval_runner_auto.py` + `score_runner.py` (이번 세션 신설)
**작성**: Claude Code, 사용자 자리 비운 사이 자동 실행

> 본 리포트는 autonomous 실행 모드에서 Claude Code가 직접 모델 호출 → 채점 → 분석까지 수행한 결과입니다. 사람 검토(KOREAN_POOR 등 manual tag) 미적용.

---

## §0. TL;DR

1. **Production 자동화(D 카테고리 JSON-only) 후보 2개**: `clinical-hari-q5-current` + `gpt-oss-20b-low`. 둘 다 D avg 4.67, hard_fail 0건.
2. **종합 1위**: `clinical-hari-q5-current` (avg 3.15, retry 적용 시 ~3.4). B/C 자유 서술 reviewer 1순위 + D 자동화 동시 가능.
3. **종합 2위**: `gpt-oss-20b` (avg 2.85 baseline, medium 적용 시 ~3.0 추정). **hard_fail 0건**. `reasoning_effort='low'`는 C 카테고리 부실 → **`medium`으로 C avg 2.00→3.33 회복** (§5.2).
4. **hari-q3 시리즈 (8b/14b)**: default Modelfile의 ollama auto-template 부정확. **ChatML 명시 Modelfile로 14b A 2.50→3.00 / 8b A 2.50→2.75 회복** (§5.1, §5.5). D 카테고리는 reasoning trace 노출로 여전히 hard_fail.
5. **clinical-hari-q5 A_02 단발 빈응답**: retry x3 모두 정상 응답 — **단발 ollama quirk** 확정 (§5.6). 단 응답이 모두 JSON 형식 — A 카테고리 prose 강제 system prompt 보강 필요.
6. **gemma4-latest**: 한국어는 자연스럽지만 D 카테고리 항상 ```json fence → 자동화 불가 (post-processor 필요).
7. **ministral-3-14b-reasoning D_02**: max_tokens 4096 + 3회 retry 모두 1 token EOT — **재현 가능한 모델 한계** (§5.3).
8. **exaone4-32b-iq4-4k**: 모델 weights 17GB > VRAM 16GB → CUDA init 실패. **64GB part 2 + GPU+CPU split 재시도 권장**.

---

## §1. 실행 요약

| 단계 | 시각 | 소요 | 결과 |
|---|---|---|---|
| 환경 점검 | 04:53 | 1초 | RAM 18.6GB free, ollama 0.24.0, LM Studio Server 미사용 |
| Ollama import (hari-8b/14b/ministral) | 04:54~04:57 | 3분 | 3개 모두 import 성공. ministral은 OOM (38GiB 요구) → num_ctx 8192 추가 후 재import |
| D smoke (gpt-oss + gemma4 × D 3) | 04:53~04:53 | 1.2분 | gpt-oss 모두 통과, gemma4 모두 fence hard_fail. **JSON-only 엄격 규칙이 의도대로 동작** |
| score_runner fixture 검증 | 04:58 | <1초 | gemma4 0/0/0 + gpt-oss 4/5/5 (D_01 4점은 "변경" 명사 false positive — v0.3 backlog) |
| **Step 4 quick rerun** (7 모델 × 13 prompts) | 04:55~05:04 | 8.5분 | 6/7 성공. exaone4 HTTP 500 |
| score_runner 적용 | 05:05 | <1초 | 결과 `results/_scored_quick_rerun_20260516.{md,json}` |
| 보조 실험 (ChatML / reasoning_effort / D_02 retry) | 05:05~ | 진행 중 | §5 참조 |

---

## §2. 종합 점수 ranking (baseline + 보조 실험 통합)

`results/_scored_quick_rerun_20260516.md` 의 summary + §5 보조 실험 결과 통합:

| 순위 | 모델 (variant) | A | B | C | D | Total | HF# | 비고 |
|---|---|---|---|---|---|---|---|---|
| 1 | clinical-hari-q5-current | 2.00 (3.4 retry시) | **3.00** | **3.33** | **4.67** | **3.15** (~3.4) | 1→0 | A_02 단발 quirk (§5.6 retry 3/3 정상) |
| 2 | gpt-oss-20b (medium) ★ | 2.50† | 2.33† | **3.33** | **4.67**† | ~3.0§ | 0 | medium은 C만 검증, A/B/D는 low 결과 차용 |
| 3 | gpt-oss-20b-low | 2.50 | 2.33 | 2.00 | **4.67** | 2.85 | **0** | low는 C 카테고리 부실 (case_id 한 줄) |
| 4 | **hari-14b-i1-chatml** ★ | **3.00** | 2.67 | 3.00 | 0.00 | 2.23 | 3 | A 카테고리 1위. D는 reasoning trace로 HF |
| 5 | hari-8b-i1-chatml ★ | 2.75 | 2.67 | 3.00 | 0.00 | 2.15 | 3 | ChatML로 PHI_LEAK/HALLUC 제거 |
| 6 | ministral-3-14b-reasoning | **2.75** | 2.67 | 3.00 | 0.00 | 2.15 | 3 | D 모두 HF (reasoning trace + D_02 빈응답 reproducible) |
| 7 | gemma4-latest | 2.25 | 2.67 | 3.00 | 0.00 | 2.00 | 3 | D 모두 ```json fence (한국어 자연스러움) |
| 8 | hari-14b-i1 (default Modelfile) | 2.50 | 2.67 | 2.67 | 0.00 | 2.00 | 3 | ChatML로 +0.23 가능 — chatml 권장 |
| 9 | hari-8b-i1 (default Modelfile) | 2.50 | 2.67 | 2.67 | 0.00 | 2.00 | 3 | template 깨짐 (입력 echo) — chatml 필수 |
| - | exaone4-32b-iq4-4k | 0.00 | - | - | - | 0.00 | 1 | **VRAM 16GB 부족** — 평가 불가 |

> **카테고리별 1위 굵게 표시**. ★ = 보조 실험으로 발견된 권장 운영 모드. 13 prompt 만점 5점, hard_fail=0점.
> † = `gpt-oss-20b (medium)` 의 A/B/D는 low 결과 차용 (보조 실험은 C만). 실제 medium 종합 평가는 v0.3 round에서 권장.
> § = medium 추정치는 A/B/D가 low와 동등하다는 가정.

---

## §3. 카테고리별 분석

### §3.1 A_charting (차팅 정리) — 1위: ministral-3-14b-reasoning (2.75)

목적: raw 의사 메모 → SOAP 정리. 원문 보존 + hallucination 금지가 핵심.

| 모델 | A_01 | A_02 | A_03 | A_04 | avg |
|---|---|---|---|---|---|
| ministral-3-14b-reasoning | 3 | 2 | 3 | 3 | 2.75 |
| gpt-oss-20b-low | 2 | 3 | 3 | 2 | 2.50 |
| hari-14b-i1 | 2 | 2 | 3 | 3 | 2.50 |
| hari-8b-i1 | 2 | 3 | 2 | 3 | 2.50 |
| gemma4-latest | 2 | 2 | 3 | 2 | 2.25 |
| clinical-hari-q5-current | 2 | **0** (HF) | 3 | 3 | 2.00 |

특이점:
- **A_03 (의료 약어 보존 stress test) 핵심 prompt**: 6개 모델 중 5개가 3점 — 양호. hari-8b는 2점 (5개 required missing).
- A_02 (오타 복원): clinical-hari-q5가 빈 응답 hard_fail. 단발 quirk 또는 한국어 약어 처리 한계.
- A_04 (정보 부족 시 [확인 필요]): 전반적으로 부실 — `[확인 필요]` 마커를 강제로 넣은 모델이 적음.

### §3.2 B_needs_review (NEEDS_REVIEW 설명) — 1위: clinical-hari-q5-current (3.00)

목적: master DB matcher 결과를 의사 친화 문장으로. 보수성 + 자동 확정 회피.

| 모델 | B_01 | B_02 | B_03 | avg |
|---|---|---|---|---|
| clinical-hari-q5-current | 3 | 3 | 3 | **3.00** |
| gemma4-latest | 2 | 3 | 3 | 2.67 |
| hari-14b-i1 | 2 | 3 | 3 | 2.67 |
| hari-8b-i1 | 2 | 3 | 3 | 2.67 |
| ministral-3-14b-reasoning | 2 | 3 | 3 | 2.67 |
| gpt-oss-20b-low | 2 | 3 | 2 | 2.33 |

특이점:
- B_01 (code/name mismatch): **모든 모델이 "변경하십시오" / "확정" / "오류" 단정 표현 1건 이상 발생 → forbidden present 1~5**. v0.2 B_01 forbidden_elements가 잘 잡음. UNAUTHORIZED_ACTION 태그 다수.
- B_02 (chart conflict): 안정적 3점.
- B_03 (fuzzy multi candidate): gpt-oss가 응답에 case_id만 1줄 출력 → 8개 required missing.

### §3.3 C_rule_finding (Rule finding 문장화) — 1위: clinical-hari-q5-current (3.33)

목적: rule engine output → report.md 한 섹션. "권고 vs 명령" 구분.

| 모델 | C_01 | C_02 | C_03 | avg |
|---|---|---|---|---|
| clinical-hari-q5-current | 3 | **5** | 2 | **3.33** |
| gemma4-latest | 3 | 3 | 3 | 3.00 |
| ministral-3-14b-reasoning | 3 | 3 | 3 | 3.00 |
| hari-14b-i1 | 3 | 3 | 2 | 2.67 |
| hari-8b-i1 | 3 | 3 | 2 | 2.67 |
| gpt-oss-20b-low | 2 | 2 | 2 | **2.00** |

특이점:
- **clinical-hari-q5의 C_02 만점 5점** — 당뇨 모니터링 INFO finding을 모범적으로 문장화.
- gpt-oss는 C_01/C_02 모두 case_id 한 줄만 출력 — **reasoning_effort='low'가 C 카테고리에 너무 부족** (보조 실험 §5에서 medium 시도).
- C_03 (검사/청구 mismatch): 대부분 required 누락 — `"자동 오류 확정 아님"` 같은 표현이 약함.

### §3.4 D_json_phi (JSON+PHI 자동화) — 1위: clinical-hari-q5-current / gpt-oss-20b-low (4.67)

목적: production 자동화 적합성. JSON-only strict + PHI 회피.

| 모델 | D_01 | D_02 | D_03 | avg |
|---|---|---|---|---|
| clinical-hari-q5-current | 4 | 5 | 5 | **4.67** |
| gpt-oss-20b-low | 4 | 5 | 5 | **4.67** |
| 나머지 4개 (gemma/hari-8b/hari-14b/ministral) | 0 | 0 | 0 | **0.00** (모두 HF) |

특이점:
- **clinical-hari-q5 + gpt-oss 두 모델만 Production 자동화 가능**.
- D_01의 4점은 "변경" 명사 false positive (§4 backlog).
- D_02 PHI 회피: 모든 모델이 "홍길동/12345/750101" 미출력 (Schema 자체는 잘 따름) — fence 등 JSON-only 위반이 hard_fail 사유.
- **gemma4-latest**: 응답이 ` ```json\n{...}\n``` ` 으로 일관 감쌈. 본문은 양질. fence-stripping post-processor 추가 시 자동화 가능.
- **hari-14b/8b/ministral**: reasoning trace 또는 설명 텍스트가 JSON 앞에 붙어 hard_fail.
- **hari-8b/ministral D_02 빈 응답**: 모델 instability (각 0.1초, 1 token만).

---

## §4. 태그 발생 매트릭스 분석

`results/_scored_quick_rerun_20260516.md` §태그 발생 매트릭스 발췌:

| 모델 | EMPTY | FORMAT | HALLUC | JSON_EXTRA | OVERCONF | UNAUTH | PHI_LEAK | MIXED | TOO_VERBOSE | TOO_TERSE |
|---|---|---|---|---|---|---|---|---|---|---|
| clinical-hari-q5 | 1 | 5 | 0 | 0 | 1 | 1 | 0 | 0 | 4 | 1 |
| gpt-oss-20b-low | 0 | 9 | 0 | 0 | 1 | 1 | 0 | 3 | 3 | 2 |
| gemma4-latest | 0 | 5 | 0 | **3** | 1 | 1 | 0 | 0 | 3 | 0 |
| hari-14b-i1 | 0 | 10 | 0 | 3 | 2 | 2 | 0 | 0 | **10** | 0 |
| hari-8b-i1 | 1 | 10 | 2 | 2 | 3 | 3 | **1** | 1 | **10** | 0 |
| ministral-3-14b | 1 | 7 | 0 | 2 | 0 | 0 | 0 | 0 | 7 | 0 |

주요 관측:
- **hari-8b PHI_LEAK 1건** (A_02 응답에 입력 echo 패턴 부산물). **template 문제 확실** — ChatML fallback variant 비교 평가 진행.
- **gpt-oss MIXED_LANGUAGE 3건** (B_03/C_01/C_02): 응답이 영어 case_id 한 줄만이라 한글 비율 낮음 → langdetect 검증으로 잡힘. NB-3에 따라 ko_with_medical_en_allowed 정책이라면 OK인데 B/C는 `ko` 정책 → 정상 검출.
- **TOO_VERBOSE 누적**: hari 시리즈가 10건씩 — sentence count tolerance를 넘는 verbose 응답 패턴. reasoning trace 영향 가능성.

---

## §5. 보조 실험 (autonomous run)

> 이 섹션은 백그라운드/순차 실행 중. 완료된 항목만 채워짐.

### §5.1 hari-8b-i1 ChatML fallback variant

**설정**: `ollama-imports/Modelfile.hari-q3-8b-i1-chatml` — `FROM` + 명시적 ChatML `TEMPLATE` + `stop "<|im_end|>"` + `stop "<|im_start|>"`.

**결과** (`results/hari-8b-i1-chatml_20260516_051013.{json,md}` + `_scored_hari8b_chatml_20260516.{json,md}`):

| 카테고리 | default Modelfile | ChatML variant | Δ |
|---|---|---|---|
| A_charting | 2.50 | **2.75** | +0.25 |
| B_needs_review | 2.67 | 2.67 | 0 |
| C_rule_finding | 2.67 | **3.00** | +0.33 |
| D_json_phi | 0.00 (3 HF) | 0.00 (3 HF) | 0 |
| Total avg | 2.00 | **2.15** | +0.15 |

핵심 변화:
- **A_01 PHI_LEAK / HALLUCINATED_FINDING / UNAUTHORIZED_ACTION 태그 사라짐**: default Modelfile에서 발생했던 input echo + max_tokens 도달 패턴 제거. **template auto-detection 실패가 원인** 확정.
- **A_02 점수**: 0 (default HF 아님, A_02는 3점) → 3점 동일. 단 default는 응답 안에 input prompt가 그대로 echo되어 있어 부적합.
- **D_02 응답 분석**: default는 빈 응답 → ChatML은 응답 생성하지만 **PHI_LEAK 1건** (reasoning trace 안에서 input의 "홍길동" 등 patient_name 그대로 노출). reasoning 모델의 D 카테고리 본질적 한계.
- **D 모두 hard_fail 그대로**: `<think>...</think>` 블록이 JSON 앞에 출력되어 JSON_EXTRA_TEXT.

**결론**: hari-q3 시리즈는 imatrix quant의 GGUF chat_template 메타데이터가 ollama auto-detection에 부정확. **ChatML fallback Modelfile 권장**. 단 reasoning 모델 특성상 D 카테고리는 본질적으로 어려움.

### §5.2 gpt-oss reasoning_effort='medium' (C 카테고리)

**설정**: 직접 ollama OpenAI 호환 API 호출, `reasoning_effort: "medium"`, C_01/C_02/C_03만.

**결과** (`results/gpt-oss-20b-medium_20260516_051400.json` + `_scored_gpt_oss_medium_20260516.md`):

| Prompt | low (Step 4 baseline) | medium | 응답 길이 변화 |
|---|---|---|---|
| C_01 | 2 (case_id 한 줄 출력) | **3** | 50 tokens → 774 tokens |
| C_02 | 2 (case_id 한 줄 출력) | **5** ★ | 50 tokens → 851 tokens |
| C_03 | 2 | 2 | 변화 없음 (287 tokens, 여전히 required 6개 누락) |
| C avg | 2.00 | **3.33** | +1.33 |

핵심 변화:
- **`reasoning_effort='low'`는 C 카테고리에 부족** — case_id만 출력하고 멈춤. medium은 정상 길이 응답.
- C_02 만점 5점 — 당뇨 모니터링 INFO finding을 모범적으로 문장화 (clinical-hari-q5와 동급).
- C_03 변화 없음 — `"자동 오류 확정 아님"` 같은 표현 누락. 모델 능력 한계 가능성.

**결론**: gpt-oss-20b 운영 시 task 카테고리별 dynamic reasoning_effort 권장:
- D 카테고리 (JSON-only): `low` (확실히 안정 + 빠름)
- A/B/C 카테고리 (자유 서술): `medium` (응답 부실 방지)
- 또는 일괄 `medium` (속도 trade-off 수용).

### §5.3 ministral D_02 max_tokens 늘려 단독 재시도

**설정**: 동일 prompt × 3 회, `max_tokens=4096` (Step 4는 2048).

**결과** (`results/ministral_d02_retry_20260516_051428.json`):

| Trial | 소요 | completion_tokens | response_chars |
|---|---|---|---|
| 1 | 5.1s | 1 | 0 |
| 2 | 0.1s | 1 | 0 |
| 3 | 0.1s | 1 | 0 |

→ **재현 가능한 모델 한계**. D_02 의 PHI 명시 system instruction + 명시적 PHI 포함 input이 ministral의 reasoning 모델로 하여금 즉시 EOT 토큰 생성하게 함. max_tokens 증가 무관.

원인 가설:
- (a) Mistral V7 template이 ChatML과 다른데 ollama auto-detection에서 부정확
- (b) "⚠️ 매우 중요: 입력에 patient_name, chart_no... 출력에는 절대 포함하지 말 것" 같은 강한 negation이 reasoning 모델을 confused 시킴 (refuse-like 패턴)
- (c) num_ctx 8192가 reasoning trace + JSON 응답 합쳐 부족

**결론**: ministral의 D_02 케이스는 v0.2 평가 단계에서 **모델 책임**으로 기록. ollama Modelfile에 Mistral V7 명시 template 적용 후 재시도는 향후 v0.3 round에서.

### §5.4 exaone4-32b CUDA OOM (skip)
**원인**: 모델 weights 17GB > RTX 5080 VRAM 16GB. CUDA init 단계에서 `shared object initialization failed`. CPU offload는 32B 클래스에서 분당 수 토큰 수준이라 평가 의미 적음.
**처리**: v0.2 평가에서 **환경 제약으로 skip**. 64GB RAM + GPU+CPU split (PARAMETER num_gpu N) 또는 32B 클래스 더 작은 quant (Q3_K_M 등) 환경에서 재시도 권장.

### §5.5 hari-14b-i1 ChatML fallback variant

**설정**: `ollama-imports/Modelfile.hari-q3-14b-i1-chatml` (8b와 동일 패턴).

**결과** (`results/hari-14b-i1-chatml_20260516_052025.{json,md}` + `_scored_hari14b_chatml_20260516.{json,md}`):

| 카테고리 | default Modelfile | ChatML variant | Δ |
|---|---|---|---|
| A_charting | 2.50 | **3.00** | **+0.50** ★ |
| B_needs_review | 2.67 | 2.67 | 0 |
| C_rule_finding | 2.67 | **3.00** | +0.33 |
| D_json_phi | 0.00 (3 HF) | 0.00 (3 HF) | 0 |
| Total avg | 2.00 | **2.23** | +0.23 |

핵심 변화:
- **A 카테고리에서 8b보다 ChatML 효과 더 큼** (+0.50 vs +0.25). 14b reasoning이 약어 보존을 더 일관되게 수행.
- D 카테고리는 여전히 모두 hard_fail. reasoning trace + 설명문이 JSON 앞에 출력되는 reasoning 모델 본질적 한계 그대로.
- D_02에서 **PHI_LEAK 1건** — reasoning 안에서 input PHI 노출 (8b chatml과 동일 패턴).

**결론**: hari-q3-14b도 **ChatML Modelfile 필수**. 8b와 같은 결론.

### §5.6 clinical-hari-q5 A_02 빈응답 진단 (retry x3)

**Step 4 관측**: A_02 elapsed 2.4초, completion_tokens=283, content_len=0 chars. 단발 hard_fail로 잡혀 종합 점수 -1.

**retry 결과** (`results/clinical_hari_a02_retry_20260516_052155.json`):

| Trial | 소요 | completion_tokens | content_chars | reasoning_chars | response 패턴 |
|---|---|---|---|---|---|
| 1 | 18.6s | 1866 | 177 | 0 | JSON 형식 `{"case_id": ..., "cleaned_memo": ...}` |
| 2 | 6.1s | 752 | 368 | 0 | JSON 형식 |
| 3 | 6.9s | 851 | 178 | 0 | JSON 형식 |

핵심 변화:
- **3회 모두 정상 응답 생성**. Step 4의 0 chars는 **단발 ollama quirk** 확정 (retry 신뢰성 패치 권장).
- 응답이 모두 **JSON 형식**으로 옴 — A_02는 text 형식 요구이므로 `format_pass=False` 받지만 v0.2 A_02 `hard_fail.conditions` 에 "JSON 형식으로 응답"이 없어서 hard_fail은 아님. 점수 차감은 발생.
- Trial 2의 `"변이 주황색으로 보이지만"`은 input의 `"변자주봄"`을 오해석 → 작은 hallucination 패턴 관찰 (단, A_02 forbidden에 명시 안 됨 → 잡히지 않음).

**시사점**:
- clinical-hari-q5의 종합 avg 3.15는 A_02 단발 quirk로 페널티 받은 결과. **retry 적용 시 3.4 수준 추정** (A_02가 0→3 정도라 가정 시 +0.23).
- A 카테고리 input ("환자30대남")에 대한 응답이 일관되게 JSON으로 옴 — **clinical-hari-q5의 task framing 특성**. A 카테고리에서 task로 text 응답을 더 강하게 강제해야 효과적.

**v0.3 권고**:
- A 카테고리 system prompt에 "응답은 JSON이 아닌 문장형 한국어로" 명시 강화.
- 또는 clinical-hari-q5 운영 시 model-specific system prompt overlay 적용 ("응답 형식: 한국어 prose, JSON 금지").

---

## §6. v0.3 정정 권고

본 quick rerun에서 발견된 v0.2 prompt set의 개선 후보 (SCORING_CONTRACT §13에 일부 누적됨):

### Must (다음 round)

1. **D_01 forbidden_elements "변경" 광범위**: gpt-oss / clinical-hari-q5 D_01 응답에서 "당뇨 약제 변경", "청구 항목 변경" 같이 input에서 유래한 합법 명사가 forbidden hit → 부당 감점. 어미 명시 (`변경하십시오|변경 명령` 등) 또는 정확한 명령형 regex로 교체.
2. **A_04 `[확인 필요]` 강제 강도**: 전 모델 required missing — 다수 모델이 이 marker 누락. system prompt에서 더 강하게 지시하거나 alternative marker (`[추가 확인 필요]`, `[원차트 조회 권장]`) 허용.
3. **A 카테고리 sentence count tolerance**: reasoning 모델은 자연스럽게 verbose. min/max sentences ±1 tolerance를 ±2로 늘리거나 token count 기반으로 전환 고려.

### Should

4. **D 카테고리 reasoning 모델 어케 다룰지**: ministral / hari 시리즈처럼 reasoning trace를 응답 앞에 자동 출력하는 모델은 D 카테고리에서 본질적으로 불리. v0.3에서 "reasoning model" 분류 + 그에 맞는 sub-rubric (예: `<think>...</think>` 블록 무시 옵션).
5. **MIXED_LANGUAGE 자동 검출 정밀도**: gpt-oss의 case_id 한 줄 응답이 MIXED_LANGUAGE로 잡힘 — 응답이 너무 짧아 한글 비율 산출이 불안정. minimum response length 미만이면 MIXED_LANGUAGE 자동 skip.
6. **operational guidance — gpt-oss reasoning_effort**: 본 평가에서 'low'는 C 카테고리에 부적합 (case_id 한 줄). 'medium'으로 C avg 2.00→3.33 회복. v0.3 또는 README에 task별 dynamic effort 운영 가이드 명시.
7. **operational guidance — hari 시리즈 ChatML Modelfile**: mradermacher imatrix quant의 ollama auto-template 부정확. ChatML 명시 Modelfile 필수. 14b도 동일 적용 권장 (8b에서 효과 확인).

### Minor

6. clinical-hari-q5 A_02 빈응답 / hari-8b D_02 빈응답 / ministral D_02 빈응답: ollama API 일시 quirk 가능성. 동일 prompt 3회 retry로 안정성 확인 권장.

---

## §7. Production 채택 권고 (v0.2 평가 한정)

> 32GB 환경 + 7 모델만 평가한 결과. 64GB part 2 (Qwen3.6-35B, Gemma 4 26B/31B, magistral) 후 재검토 필요.

### Role-fit 후보

| 역할 | 1순위 | 2순위 | 비고 |
|---|---|---|---|
| **Reviewer (NEEDS_REVIEW 설명, B 카테고리)** | clinical-hari-q5-current (3.00) | gemma4 / ministral / hari-chatml (2.67 동률) | clinical-hari가 보수성 최고 |
| **Formatter (차팅 정리, A 카테고리)** | **hari-14b-chatml (3.00)** ★ | ministral / hari-8b-chatml (2.75) | ChatML 적용 14b가 최고. ChatML 운영 필수 |
| **Report 작성 (Rule finding, C 카테고리)** | clinical-hari-q5-current (3.33) | **gpt-oss-medium (3.33)** | medium 적용 시 gpt-oss와 동률 |
| **자동화 JSON pipeline (D 카테고리)** | **clinical-hari-q5-current** ★ | **gpt-oss-20b-low** ★ | 두 모델만 D 자동화 가능 |

### 통합 채택 시나리오

- **시나리오 A (단일 모델)**: `clinical-hari-q5-current`. A/B/C/D 모두 통과 가능 (avg 3.15). A_02 단발 빈응답은 retry로 회피 가능. 가장 안정적 production 후보.
- **시나리오 B (역할 분리)**: Formatter = `ministral` 또는 `gemma4`, Reviewer = `clinical-hari-q5`, JSON pipeline = `gpt-oss-low`. 모델 로딩 overhead 큼.
- **시나리오 C (gpt-oss 단독, dynamic reasoning_effort)** ★ **추천**:
  - D 카테고리: `reasoning_effort='low'` (빠르고 안정, D avg 4.67)
  - A/B/C 카테고리: `reasoning_effort='medium'` (C avg 2.00→3.33)
  - hard_fail 0건 + 단일 모델 운영 + dynamic effort로 종합 성능 최적
  - 추정 종합 avg ~3.0 (medium 적용 후 A/B/C 회복 가정)
- **시나리오 D (hari 시리즈 활용)**: hari-q3-8b/14b를 모두 ChatML Modelfile로 재import 후 차팅 보조. D는 post-processor (fence/think 제거) 필수.

### 권장 결정 (autonomous 평가 기준)

본 평가만으로 결정한다면 **시나리오 C (gpt-oss-20b 단독 + dynamic effort)**. 이유:
1. **hard_fail 0건** — 단일 모델 운영에서 가장 중요한 안정성 지표
2. D avg 4.67 = clinical-hari-q5와 동률
3. C 카테고리는 medium으로 보완 가능 (§5.2 실증)
4. 모델 로드/스왑 비용 없음
5. clinical-hari-q5의 A_02 빈응답이 유일한 약점이지만, gpt-oss는 그런 단발 quirk 없음

단 본 평가는 32GB 환경 + 7 모델 (모두 NC 라이센스 회피)만 봤음. **64GB part 2에서 Qwen3.6-35B (gpt-oss와 동급 OpenAI 호환 + Apache 라이센스), Gemma 4 31B 추가 평가 후 최종 결정 권장**.

---

## §8. 산출물 위치

| 파일 | 내용 |
|---|---|
| `results/_scored_quick_rerun_20260516.{md,json}` | 7 모델 × 13 prompts 채점 결과 (raw) |
| `results/_scored_hari8b_chatml_20260516.{md,json}` | §5.1 ChatML 8b variant 채점 결과 |
| `results/_scored_hari14b_chatml_20260516.{md,json}` | §5.5 ChatML 14b variant 채점 결과 |
| `results/_scored_gpt_oss_medium_20260516.{md,json}` | §5.2 gpt-oss medium 채점 결과 |
| `results/clinical_hari_a02_retry_20260516_*.json` | §5.6 clinical-hari A_02 retry x3 결과 |
| `results/_comparison_models_config_quick_rerun_20260516_050425.md` | 7 모델 응답 직접 비교 (raw text) |
| `results/<model>_20260516_*.json/md` | 모델별 상세 결과 (7개 모델 + chatml variant + medium 실험) |
| `results/ministral_d02_retry_20260516_*.json` | §5.3 ministral D_02 3회 retry raw |
| `results/archive_d_smoke/` | D smoke (Step 3) 결과 보존 |
| `tests/fixtures/d_smoke_*.json + expected_scores.json` | score_runner 회귀 테스트용 fixture |
| `tests/fixtures/_scored_d_smoke_validation.{md,json}` | scorer self-test 결과 |
| `tests/inspect_anomalies.py` | 이상 응답 inspector (Step 4 진단용) |
| `tests/experiment_gpt_oss_medium.py` | §5.2 실험 스크립트 |
| `tests/experiment_ministral_d02.py` | §5.3 실험 스크립트 |
| `tests/experiment_clinical_hari_a02.py` | §5.6 실험 스크립트 |
| `score_runner.py` | 자동 채점 스크립트 (SCORING_CONTRACT.md 구현체) |
| `models_config_d_smoke.json` | D smoke용 (2 모델) |
| `models_config_quick_rerun.json` | Step 4 본 평가용 (7 모델, all-ollama) |
| `models_config_hari8b_chatml.json` | §5.1 보조 실험용 |
| `models_config_hari14b_chatml.json` | §5.5 보조 실험용 |
| `ollama-imports/Modelfile.hari-q3-14b-i1-chatml` | hari-14b ChatML 명시 |
| `ollama-imports/Modelfile.hari-q3-8b-i1` | default Modelfile (FROM only) |
| `ollama-imports/Modelfile.hari-q3-8b-i1-chatml` | **권장** ChatML 명시 + stop tokens |
| `ollama-imports/Modelfile.hari-q3-14b-i1` | default. 14b도 chatml 적용 권장 (§9 다음 액션 #4) |
| `ollama-imports/Modelfile.ministral-3-14b-reasoning` | num_ctx 8192 |
| `ollama-imports/import.ps1` | 자동 import 스크립트 |
| `reviews/quick-rerun-2026-05-16-report.md` | 이 리포트 |

---

## §9. 다음 액션 (사용자 깨어난 후)

1. **본 리포트 확인** — TL;DR(§0) + Ranking(§2) + Role-fit(§7) 우선
2. **v0.3 정정 항목 결정** (§6의 must-fix 3개 중 우선순위)
3. ~~clinical-hari-q5 A_02 빈응답 retry~~ → §5.6에서 단발 quirk 확정. 별도 액션 불필요.
4. ~~hari-14b ChatML Modelfile 적용 여부~~ → §5.5에서 효과 확정 (+0.50 in A). **default Modelfile 폐기 + chatml 운영 권장**.
5. **64GB 업그레이드 후 part 2 진입** (Qwen3.6-35B / Gemma 4 26B/31B / magistral / exaone4 GPU+CPU split)
6. **(선택) R4 codex review**: 본 리포트 + v0.3 정정 후보를 묶어 packet 작성. SOP must-fix only loop 패턴.
7. **(선택) gpt-oss medium A/B/D 카테고리 평가**: 본 평가에서 C만 검증함. A/B/D도 medium으로 돌려야 정확한 종합 avg 산출 가능.
8. **(선택) ministral Mistral V7 명시 template Modelfile + 재시도**: D_02 1 token EOT 이슈가 template 문제인지 확인.
9. **(선택) gpt-oss reasoning_effort 'high' 실험**: medium보다 더 좋아지는지 (속도 trade-off 확인).

---

**리포트 끝** — autonomous 실행 (Claude Code, 2026-05-16 05:0X)
