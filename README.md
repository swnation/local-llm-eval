# Local LLM Evaluation — Clinical-assist

> Clinical-assist에서 local LLM의 본 역할(설명·정리·검토 보조 엔진) 평가 프로젝트의 **작업(working) 폴더**.
> 정본 산출물 archive는 `c:\Github\knowledge-archive\projects\clinical-assist\local-llm-eval\` (f74181c @ 2026-05-15).

**새 세션 entry point**: [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — 역할/현재 상태/결정/금지사항/다음 액션이 한 페이지로. 본 README는 사용법/실행 가이드 위주.

---

## §0. 폴더 목적

Clinical-assist 시스템에서 PaddleOCR + master DB matcher + parser + deterministic rule engine이 만든 결과 위에 **설명·정리·문장화·리뷰**를 담당할 local LLM을 평가하기 위한 prompt set, review 결과, 실행 결과 보관 폴더.

핵심 원칙:

- **LLM은 판단 엔진이 아님**. OCR/master DB 매칭/parser/rule engine이 이미 만든 deterministic 결과를 입력받아 의사 친화적으로 설명·정리·문장화·리뷰만 수행
- **LLM은 다음을 하지 않음**: OCR 주엔진, 정본 추출, hard safety 판단, 자동 수정, 최종 임상 확정, 처방 변경 지시
- **LLM이 잘하는 영역**: 차팅 문장 정리, NEEDS_REVIEW 이유 설명, rule finding을 report.md 문장화, JSON+PHI safe summary

---

## §1. 폴더 구조

```
local-llm-eval/
├── README.md                                              ← 이 문서 (진입점)
├── .gitignore
├── eval_runner.py                                         ← 수동 모드
├── eval_runner_auto.py                                    ← 자동 모드 (권장)
├── models_config.json                                     ← 전체 14개 모델 (64GB용)
├── models_config_part1.json                               ← 32GB용 10개 모델
├── models_config_part2.json                               ← 64GB용 무거운 4개 모델
├── models_config_remaining.json                           ← 잔여 미평가 모델
├── models_config_quick_rerun.json                         ← v0.2 quick rerun 7개 모델 ★
├── prompts/
│   ├── test_suite_v0.2.json                               ← v0.2 final 운영본 (13 prompts + 4층 rubric)
│   ├── local-llm-eval-prompts-clinical-assist-v0.1.md     ← v0.1 초안 (히스토리)
│   ├── local-llm-eval-prompts-clinical-assist-v0.2.md     ← v0.2 final 문서 정본 (사람이 읽는 형식)
│   └── archive/
│       └── test_suite_v1.json                             ← 구 v1 prompts (21개, 보관용)
├── reviews/
│   ├── review-packet-v0.1-r0.md                           ← R0 packet (Claude 작성)
│   ├── gpt-r0-review-response.md                          ← GPT R0 응답 (CONDITIONAL GO)
│   ├── review-packet-v0.2-r1.md                           ← R1 packet (Claude 작성)
│   └── gpt-r1-review-response.md                          ← GPT R1 응답 (GO)
└── results/                                                ← 결과 저장 (gitignored)
    ├── (v1 시절 21-prompt 결과 보관 중)
    └── results.zip
```

---

## §2. 현재 상태 (2026-05-15)

| 단계 | 상태 | 결과 |
|------|------|------|
| v0.1 초안 작성 | 완료 | 13 prompt set, 1240 lines |
| GPT R0 review | 완료 | **CONDITIONAL GO**, Must-fix 4 + Should-fix 5 + Minor 3 |
| v0.2 작성 (MF/SF 반영) | 완료 | 옵션 2 선택, Minor backlog |
| GPT R1 review | 완료 | **GO** + Non-blocking 3 (NB-1/NB-2 정정 완료, NB-3는 채점 스크립트 작성 시 처리) |
| **v0.2 final 확정** | **완료** | quick rerun 진입 가능 |
| test_suite_v0.2.json 생성 | 완료 | 4층 rubric + 평가 태그 매핑 포함 |
| 32GB quick rerun (Step 3~5) | **진행 가능** | D smoke → 7 모델 × 13 prompt |
| 자동 채점 스크립트 | **다음** | §2.3 5단계 + §2.4 JSON-only + 15 평가 태그 + NB-3 |
| 64GB part 2 정식 평가 | 대기 | RAM 업그레이드 후 |

---

## §3. 핵심 결정 사항

### §3.1 평가셋 구조 (v0.2 final)

- **A 차팅 정리 4개** (Priority 1): 의사 raw 메모를 SOAP로 정리. A_03은 의료 약어/기호 보존 stress test
- **B NEEDS_REVIEW 설명 3개**: master DB matcher 결과를 의사 친화 문장으로
- **C Rule finding 문장화 3개**: rule engine output을 report.md 1섹션으로
- **D JSON+PHI stress 3개**: production 자동화 적합성 최소 조건. D_02는 PHI substring stress, D_03은 schema strict

### §3.2 채점 방식

4층 rubric + 점수화 1~5 + 평가 태그 15종 (자동/수동 분리):

- `required_elements`: 응답에 반드시 등장
- `forbidden_elements`: 등장 시 감점
- `format_requirements`: 언어/길이/구조
- `hard_fail`: 1건이라도 걸리면 0점 + STOP
- 평가 태그: EMPTY_RESPONSE / FORMAT_FAIL / SCHEMA_EXTRA_KEY / JSON_EXTRA_TEXT / JSON_PARSE_FAIL / PHI_LEAK / HALLUCINATED_FINDING / OVERCONFIDENT_DIAGNOSIS / UNAUTHORIZED_ACTION / MISSED_REVIEW_REASON / MISSING_REQUIRED_ELEMENT / KOREAN_POOR (수동) / TOO_VERBOSE / TOO_TERSE / MIXED_LANGUAGE

### §3.3 schema boundary

본 평가셋의 input JSON은 **eval adapter schema**임. clinical-assist production schema(G0 thin E2E slice)와 분리. production code 변경 영향 없음.

### §3.4 JSON-only 엄격 규칙 (MF-4)

D 카테고리는 `response.strip() 전체가 JSON object`여야 함. JSON 앞뒤 1자라도 텍스트/markdown fence 있으면 hard_fail.

### §3.5 PHI 정책

- system prompt에서 PHI 범위 = "환자 식별 가능성이 있는 모든 정보" (성별/나이/지역 등 patient_context 포함)
- D_02는 의도적으로 patient_name/chart_no/rrn_prefix를 input에 넣고 output substring 자동 검사 stress test
- output에는 case_id만 사용

---

## §4. NB-3 주의사항 (채점 스크립트 작성 시)

GPT R1에서 받은 non-blocking 의견 중 NB-3는 prompt set 변경 X, 채점 스크립트 작성 시 처리:

> `MIXED_LANGUAGE` 태그는 A 카테고리(`abd pain`, `r/o`, `PRN` 같은 영어 약어 보존이 의도된 시나리오)에서 **자동 적용 hard_fail 금지**. human review 또는 whitelist 기반 적용.

A 카테고리에서 영어 약어 출현은 정상. 자동 detector를 그대로 쓰면 false positive 다수 발생.

`test_suite_v0.2.json` 의 `category_meta.A_charting.language_policy = "ko_with_medical_en_allowed"` 플래그로 표시되어 있음. 채점 스크립트는 이 플래그를 읽어 MIXED_LANGUAGE 자동 적용을 카테고리별로 끄도록 구현 필요.

---

## §5. 다음 세션 진입점 — quick rerun plan

### Step 1. 평가 harness 조정 ← **완료 (2026-05-16)**

- `prompts/test_suite_v0.2.json` 생성 완료 (13 prompts, 4층 rubric, 평가 태그 매핑 포함)
- `eval_runner.py` / `eval_runner_auto.py` 의 `DEFAULT_PROMPTS_FILE` v0.2로 갱신 완료
- `models_config_quick_rerun.json` 신설 완료 (7개 모델)

### Step 2. 자동 채점 스크립트 작성 ← **다음**

별도 스크립트 (`score_runner.py` 가칭):
1. results/*.json 읽기
2. test_suite_v0.2.json 의 rubric 적용
3. 5단계 우선순위 (§2.3): hard_fail → forbidden → required → format → score
4. JSON-only 엄격 규칙 (§2.4): D 카테고리만
5. 15 평가 태그 자동 부여 + 수동 review 마킹
6. NB-3 주의: A 카테고리 MIXED_LANGUAGE 자동 적용 X

Scorer 정확한 행동 명세는 [SCORING_CONTRACT.md](SCORING_CONTRACT.md) 참조 (Codex SF-A 반영, 2026-05-16).

**Fixture 권장 (Codex MN-B)**: Step 3 D smoke 응답을 `tests/fixtures/` 에 복사하고 사람이 정답 라벨링한 `expected_scores.json` 과 함께 두면 scorer 회귀 테스트 가능. 91 calls quick rerun 들어가기 전에 scorer를 fixture로 1차 검증 → 실 결과에 안전하게 적용.

### Step 3. D 카테고리 smoke run

빠른 1~2 모델로 D_01~D_03 먼저:
```powershell
# gpt-oss-20b-low + gemma4-latest 만 임시 config로
# 또는 quick_rerun config로 돌리고 D만 골라서 평가
python eval_runner_auto.py --config models_config_quick_rerun.json
```

목적: JSON-only 엄격 규칙이 실제로 hard_fail을 잡아내는지 + PHI substring 검사 동작 확인.

### Step 4. 전체 7 모델 × 13 prompt quick rerun

```powershell
python eval_runner_auto.py --config models_config_quick_rerun.json
```

예상 소요: 30~60분 (32GB 환경, 91 calls).

### Step 5. 결과 분석 → v0.3 정정 필요 여부 결정

- `_comparison_*.md` + 채점 결과 보고서 분석
- 카테고리별 점수 / 모델별 hard_fail 발생 / 태그 패턴
- v0.3 정정 필요 → R2 review
- 큰 문제 없음 → 64GB part 2 직행

---

## §6. 평가 대상 모델 (32GB quick rerun)

`models_config_quick_rerun.json` 에 등록된 7개:

| Label | Provider | 비고 |
|---|---|---|
| `gpt-oss-20b-low` | ollama | reasoning_effort: low |
| `gemma4-latest` | ollama | |
| `clinical-hari-q5-current` | ollama | |
| `hari-8b-i1` | lm_studio | context 8192 |
| `hari-14b-i1` | lm_studio | context 8192 |
| `ministral-3-14b-reasoning` | lm_studio | context 8192 |
| `exaone4-32b-iq4-4k` | ollama | **NC 라이선스 — production 불가, 참조 측정만** |

64GB 후 part 2에서 추가 평가 예정 (`models_config_part2.json` 참조):
- Qwen3.6-35B-A3B (thinking on/off, MAIN 도전자)
- Gemma 4 26B, Gemma 4 31B
- magistral-small-2509 (재시도)

---

## §7. 사전 준비 (처음 사용 시)

### 7.1 Python

```powershell
python --version
```
3.8 이상이면 OK. **외부 라이브러리 설치 불필요** (표준 라이브러리만 사용).

### 7.2 LM Studio + lms CLI

자동 모드는 `lms` CLI로 모델 로드/언로드 자동화.

**최초 1회**:
```powershell
cmd /c "%USERPROFILE%\.lmstudio\bin\lms.exe bootstrap"
```

**새 터미널** 열고 확인:
```powershell
lms --version
lms ls
```

`lms ls`로 다운로드된 모델 키 확인. `models_config_*.json`의 `lms_key`와 정확히 일치해야 함.

### 7.3 Ollama

```powershell
ollama list
```
`NAME` 칼럼이 `models_config_*.json`의 `ollama_name`과 정확히 일치해야 함.

### 7.4 LM Studio Server 시작

```powershell
lms server start
```
또는 LM Studio GUI 좌측 → Developer → Start Server.

### 7.5 (권장) 사전 메모리 점검

본 실행 전 LM Studio 모델별 메모리 추정치 확인 → OOM 예방:

```powershell
lms load --estimate-only hari-8b-i1 --gpu max --context-length 8192
lms load --estimate-only hari-14b-i1 --gpu max --context-length 8192
lms load --estimate-only mistralai/ministral-3-14b-reasoning --gpu max --context-length 8192
```

각 출력의 `Estimated Total Memory`가 **현재 가용 RAM에 3GB 이상 여유** 있어야 안전. 부족하면 `context_length` 줄이거나 64GB 후로 미루기.

---

## §8. 실행 방법

### 8.1 자동 모드 (권장)

```powershell
# v0.2 quick rerun (오늘 밤): 7개 모델 × 13 prompt
python eval_runner_auto.py --config models_config_quick_rerun.json

# (옛) 32GB part1: 10 모델 × 21 prompt — v1 시절 도구. v0.2 prompts와 호환됨 (prompts file은 default가 v0.2로 변경됨)
python eval_runner_auto.py --config models_config_part1.json

# 64GB 업그레이드 후: part2
python eval_runner_auto.py --config models_config_part2.json
```

기본값(`--config` 생략 시)은 `models_config.json` (전체 14개). 기본 prompts는 `prompts/test_suite_v0.2.json` (v0.2 final).

### 8.2 동작 흐름

```
모델 1: lms unload --all → lms load --identifier → 13 prompt → 결과 저장 → unload
모델 2: ...
마지막: _comparison_<config명>_<타임스탬프>.md 자동 생성
```

Ollama 모델은 13 prompt 종료 후 `ollama stop`으로 자동 메모리 회수.

### 8.3 결과 파일

```
results/
├── gpt-oss-20b-low_<날짜>.md           # 모델별 상세
├── gpt-oss-20b-low_<날짜>.json         # 모델별 raw 데이터
├── gemma4-latest_<날짜>.md
├── ...
└── _comparison_models_config_quick_rerun_<날짜>.md   ← ★ 같은 prompt끼리 묶임, 직접 비교
```

### 8.4 수동 모드

자동 모드 안 될 때 (lms CLI 문제 등) 또는 즉석에서 한 모델만:

```powershell
python eval_runner.py             # LM Studio (port 1234)
python eval_runner.py --ollama    # Ollama (port 11434)
```

1. LM Studio GUI에서 평가할 모델 로드
2. Server 시작 확인
3. 위 명령 실행
4. 모델 라벨 입력
5. 13 프롬프트 자동 실행 후 저장

---

## §9. 결과 분석 흐름

1. `results/_comparison_*.md` 열기 (VS Code)
2. 각 카테고리별 응답 비교 (A / B / C / D)
3. **특히 D 카테고리**: JSON 앞뒤 텍스트, markdown fence, PHI substring 출력 모델 표시
4. 자동 채점 스크립트 실행 (Step 2 산출물) → 점수 + 태그 행렬 생성
5. 의사결정:
   - 차팅 정리(A) 1등 → Formatter 후보
   - NEEDS_REVIEW 설명(B) 1등 → Reviewer 후보
   - Rule finding(C) 1등 → Report 작성 후보
   - JSON 준수(D) hard_fail 0건 → production 자동화 가능 후보

---

## §10. 자주 발생하는 문제

**`lms 명령을 찾을 수 없음`**
→ `lms bootstrap` 실행 후 **새 터미널** 열고 재시도.

**모델 로드 실패 (메모리 부족)**
→ 필요 메모리 확인: `lms load --estimate-only <model_key>`
→ `load_options.context_length` 줄이거나, 해당 모델을 config에서 제외.

**한국어 깨짐 (PowerShell 화면)**
→ `chcp 65001` (UTF-8 코드페이지) 후 재실행. 결과 .md는 VS Code로 보면 정상.

**timeout**
→ `eval_runner_auto.py`의 `TIMEOUT_SEC` 값 증가 (기본 600초).

**`chat_template_kwargs` 적용 안 됨**
→ LM Studio 0.3.x+ 필요. 구버전이면 업데이트.

**Ollama 모델이 다음 모델 로드 시 메모리 점유 중**
→ `ollama stop <모델명>` 수동 호출.

---

## §11. 모델 설정 커스터마이징

`models_config_*.json`에서 모델 추가/제거/옵션 변경:

```json
{
  "label": "결과 파일명에 사용되는 고유 라벨",
  "provider": "lm_studio | ollama",
  "lms_key": "LM Studio용. 'lms ls' 출력 그대로",
  "ollama_name": "Ollama용. 'ollama list' NAME 칼럼 그대로",
  "load_options": {
    "gpu": "max",
    "context_length": 8192
  },
  "inference_options": {
    "chat_template_kwargs": {"enable_thinking": false},
    "reasoning_effort": "low"
  }
}
```

`load_options`는 LM Studio 전용 (Ollama 무시).
`inference_options`는 OpenAI 호환 API 호출에 그대로 전달.

---

## §12. Prompt 커스터마이징

`prompts/test_suite_v0.2.json` 의 `tests[]` 직접 편집. 각 prompt 객체 키:

```json
{
  "id": "고유ID (A_01, B_01, C_01, D_01 등)",
  "category": "A_charting | B_needs_review | C_rule_finding | D_json_phi",
  "title": "사람이 읽는 제목",
  "intent": "왜 이 prompt를 만들었는지 (사람 검토용, 모델 미전송)",
  "expected": "기대 응답 요약 (사람 검토용, 모델 미전송)",
  "system": "system prompt",
  "user": "user prompt (input JSON + 지시사항)",
  "temperature": 0.3,
  "max_tokens": 2048,
  "rubric": {
    "required_elements": [...],
    "forbidden_elements": [...],
    "format_requirements": {...},
    "hard_fail": {
      "json_only_strict": false,
      "phi_substrings": [],
      "conditions": [...]
    }
  },
  "tag_mapping": {"failure description": "TAG_NAME"}
}
```

자세한 schema는 `prompts/local-llm-eval-prompts-clinical-assist-v0.2.md` (문서 정본) 참조.

---

## §13. 라이선스 / PHI 정책

- 본 폴더 내 prompt set과 review packet은 **PHI 미포함**
- D_02 stress test에 등장하는 "홍길동", "12345", "750101"은 dummy 값
- results/ 폴더의 실 모델 응답도 dummy case_id 기반이라 PHI 미포함 가정
- production 환경 실 환자 데이터 평가는 본 평가셋의 scope 아님

---

## §14. 관련 문서

- LLM 역할 정의 (별도): "Clinical-assist에서 local LLM에게 기대해야 하는 기능 정리" — 사용자 작성, 본 평가셋 설계의 정본
- clinical-assist G0 design: `projects/clinical-assist/design/g0-thin-e2e-slice/` (별도 폴더)
- SOP: `projects/clinical-assist/sop/session-collaboration-rules-v1.md` (R0/R1/R2/R3 회차별 목적, must-fix only loop)
- 평가 대상 PC 환경: 집 PC γ track (`C:\assist_test\.venv-paddle-win50`, RTX 5080 16GB VRAM, 32GB RAM → 64GB 업그레이드 예정)
- Archive (정본 동결 스냅샷): `c:\Github\knowledge-archive\projects\clinical-assist\local-llm-eval\` @ f74181c (2026-05-15)

---

## §15. 변경 이력

- **2026-05-16**: v0.2 final working folder 정비
  - Archive에서 README/prompts v0.1/v0.2 .md / reviews 4개 복사
  - `prompts/test_suite_v0.2.json` 신설 (13 prompts + 4층 rubric + 15 평가 태그 + JSON-only 엄격 + NB-3 플래그)
  - `prompts/archive/test_suite_v1.json` 으로 구 21-prompt 보관
  - `eval_runner.py` / `eval_runner_auto.py`의 `DEFAULT_PROMPTS_FILE` → v0.2
  - `models_config_quick_rerun.json` 신설 (v0.2 §6의 7개 모델)
  - README 전체 재작성 (구 clinical-assist-eval 트리 참조 제거, v0.2 baseline + v1 실행 가이드 융합)
- 2026-05-15 (v1.1): 21-prompt 평가 도구. Critical FN 11개 확장, partial save, ollama stop 검증 등 안전성 패치
- 2026-05-15 (v1.0): 초기 버전 (14 모델, 17 prompts, part1/part2 분리)
