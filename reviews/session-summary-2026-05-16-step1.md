# Session Summary — Step 1 + Ollama 통일 결정

**Date**: 2026-05-16
**Working folder**: `c:\Github\local-llm-eval\`
**Archive (정본 동결)**: `c:\Github\knowledge-archive\projects\clinical-assist\local-llm-eval\` @ f74181c
**Prior state**: v0.2 final (R0 CONDITIONAL GO → R1 GO) 확정. 다음은 32GB quick rerun.
**This session**: Step 1 평가 harness 조정 완료 + Ollama 통일 결정 → import 대기.

---

## §0. 한 줄 요약

Working folder가 v1(21 prompts) 상태였음을 발견 → archive의 v0.2 final 산출물을 복사·반영하고, prompt JSON을 4층 rubric 포함 형태로 신규 생성. 측정 일관성 + 운영 단순화를 위해 LM Studio 3개 모델을 Ollama로 통일하기로 결정 → import 스크립트 준비 완료. 다음은 본인 PC에서 `import.ps1` 실행 → D smoke → 전체 quick rerun.

---

## §1. 시작 시점 상태

- 사용자 보고: v0.2 final 확정, archive push @ f74181c, "Step 1부터 시작하자" + "rename 잔재 점검" 요청
- Working folder는 **rename 직후 v1 그대로**였음:
  - `README.md` = v1.1 (21 prompts, `clinical-assist-eval/` 폴더 트리 참조, §5 Step 1~5 plan 없음)
  - `prompts/test_suite_v1.json` = 21 prompts (rule_classification / critical_false_negative / korean_medical 카테고리)
  - `eval_runner.py` / `eval_runner_auto.py` = v1 (DEFAULT_PROMPTS_FILE이 v1 json)
  - `reviews/` 폴더 없음, v0.1/v0.2 prompts .md 없음
- Archive에는 v0.2 정본 산출물 모두 존재:
  - `README.md` (§5에 Step 1~5 plan)
  - `prompts/local-llm-eval-prompts-clinical-assist-v0.1.md` / `v0.2.md` (1366 lines)
  - `reviews/review-packet-v0.1-r0.md` + `gpt-r0-review-response.md` + `review-packet-v0.2-r1.md` + `gpt-r1-review-response.md`

---

## §2. 의사결정 (사용자 확인)

### §2.1 Rename audit (clinical-assist-eval → local-llm-eval)

| 발견 | 처리 |
|---|---|
| `README.md:9` 의 `clinical-assist-eval/` 트리 표현 | README 전체 재작성으로 자동 해소 |
| `prompts/test_suite_v1.json:3` "총 21개" outdated description | v0.2 json으로 대체 + v1은 prompts/archive/ 이동 |
| `eval_runner*.py` 의 "Clinical-Assist 모델 평가" 문자열 | 유지 (프로젝트명 의미로 여전히 유효) |
| `c:\Github\clinical-assist-eval.zip` | 보존 (rename 직전 백업, 사용자 판단) |
| Hardcoded path (`C:\Github\clinical-assist-eval`) | 0건 |
| `.gitignore`, `.vscode`, `.code-workspace` | 문제 없음 |
| `models_config*.json` | 폴더명 의존 없음 (localhost URL만) |

### §2.2 v0.2 산출물 sync 방식 (사용자 선택)

- **Archive → working 복사** (권장 선택됨)
  - Archive는 동결 스냅샷으로 보존, working은 활성 작업 공간
  - README는 archive 베이스 + v1의 실행 가이드를 병합
- `test_suite_v1.json` → **별도 보관 후 v0.2로 대체** (권장 선택됨)
  - `prompts/archive/test_suite_v1.json`으로 이동
  - results/ 폴더 안의 v1 응답들과의 trace는 보존

### §2.3 Ollama vs LM Studio 혼합 → Ollama 통일

- 현재 7 quick rerun 모델 분포: Ollama 4 / LM Studio 3
- 통일 이점: 서버 1개만 운영 + inference param 일관(thread/batch/kv cache default 동일) → 모델 간 비교가 더 공정
- 통일 방향: **Ollama 쪽** (이미 4개라 옮길 모델 더 적음 + Ollama→LM Studio가 더 어려움. `clinical-hari-q5-current` 같은 사용자 custom Modelfile 모델은 LM Studio로 옮기기 까다로움)

---

## §3. Step 1 산출물 (working folder 변경 사항)

### §3.1 신설

| 파일 | 내용 |
|---|---|
| `prompts/test_suite_v0.2.json` ★ | v0.2 final을 JSON 변환. 13 prompts + 4층 rubric (`required_elements` / `forbidden_elements` / `format_requirements` / `hard_fail`) + 15 평가 태그 매핑 + JSON-only 엄격 플래그(`json_only_strict: true` for D) + PHI substring 리스트(`phi_substrings` for D_02) + 카테고리별 language_policy (NB-3 처리용) |
| `prompts/local-llm-eval-prompts-clinical-assist-v0.1.md` | archive에서 복사 (히스토리) |
| `prompts/local-llm-eval-prompts-clinical-assist-v0.2.md` | archive에서 복사 (문서 정본) |
| `prompts/test_suite_v0.2_d_only.json` | D_01~D_03 subset (smoke run용) |
| `models_config_quick_rerun.json` | 7개 모델 ollama 통일 버전 |
| `models_config_d_smoke.json` | D smoke용 2개 모델 (gpt-oss-20b-low, gemma4-latest) |
| `reviews/review-packet-v0.1-r0.md` | archive 복사 |
| `reviews/gpt-r0-review-response.md` | archive 복사 |
| `reviews/review-packet-v0.2-r1.md` | archive 복사 |
| `reviews/gpt-r1-review-response.md` | archive 복사 |
| `ollama-imports/Modelfile.hari-q3-8b-i1` | 최소 Modelfile + ChatML(Qwen3) fallback |
| `ollama-imports/Modelfile.hari-q3-14b-i1` | 위와 동일 패턴 |
| `ollama-imports/Modelfile.ministral-3-14b-reasoning` | 최소 + Mistral V7 fallback |
| `ollama-imports/import.ps1` | 사전 점검 + 3개 import + smoke probe |

### §3.2 변경

| 파일 | 변경 |
|---|---|
| `README.md` | 전체 재작성. archive v0.2 베이스 + v1 실행 가이드(사전 준비, lms CLI, 자동/수동 모드) 융합. `clinical-assist-eval/` 트리 참조 제거. §5에 Step 1~5 plan + 진행 상태. |
| `eval_runner.py` | `PROMPTS_FILE` → `prompts/test_suite_v0.2.json` |
| `eval_runner_auto.py` | `DEFAULT_PROMPTS_FILE` → `prompts/test_suite_v0.2.json` |
| `models_config_quick_rerun.json` | provider 모두 ollama로. LM Studio 3개의 `_imported_from` 메타 주석 추가. ollama_name: `hari-q3-8b-i1:latest` / `hari-q3-14b-i1:latest` / `ministral-3-14b-reasoning:latest` |

### §3.3 이동

| 원경로 | 새 경로 |
|---|---|
| `prompts/test_suite_v1.json` | `prompts/archive/test_suite_v1.json` |

---

## §4. test_suite_v0.2.json 스키마 (Codex 리뷰 대상)

### Top-level

```json
{
  "version": "0.2",
  "status": "v0.2 final (R0 CONDITIONAL GO -> R1 GO, 2026-05-15)",
  "description": "...",
  "source_doc": "prompts/local-llm-eval-prompts-clinical-assist-v0.2.md",
  "common_system": "<§1 공통 system prompt>",
  "scoring": {
    "rubric_layers": [...],
    "auto_priority_order": ["hard_fail", "forbidden_elements", "required_elements", "format_requirements"],
    "score_range_after_hard_fail_pass": [1, 5],
    "score_on_hard_fail": 0,
    "score_rule": "..."
  },
  "category_meta": {
    "A_charting": {"priority": 1, "language_policy": "ko_with_medical_en_allowed", "nb3_note": "..."},
    "B_needs_review": {"priority": 3, "language_policy": "ko"},
    "C_rule_finding": {"priority": 2, "language_policy": "ko"},
    "D_json_phi": {"priority": "minimum_pass_for_automation", "language_policy": "json_only_strict"}
  },
  "tags_legend": {
    "EMPTY_RESPONSE": {"auto": true, "trigger": "..."},
    ... (15개)
  },
  "tests": [ ... 13 prompt objects ... ]
}
```

### Per-prompt

```json
{
  "id": "A_01",
  "category": "A_charting",
  "title": "...",
  "intent": "...",
  "expected": "사람 검토용 (모델 미전송)",
  "system": "<공통 system prompt 복제 — runner 호환>",
  "user": "[입력]\\n<JSON inline, no fence>\\n\\n[지시사항]\\n<task prompt text>",
  "temperature": 0.3,
  "max_tokens": 2048,
  "rubric": {
    "required_elements": [
      "직접 substring",
      {"any_of": ["대안1", "대안2"]},
      {"regex": "패턴"}
    ],
    "forbidden_elements": [...],
    "format_requirements": {
      "language": "ko" | "ko_with_medical_en_allowed" | "json_only_strict",
      "min_sentences": 3,
      "max_sentences": 6,
      "structure": "S/O/A_3sections" | "prose" | "json_only" | ...,
      "policy": "...optional..."
    },
    "hard_fail": {
      "json_only_strict": false,    // D 카테고리만 true
      "phi_substrings": [],          // D_02만 ["홍길동", "12345", "750101"]
      "conditions": ["빈 응답", "...", "..."]
    }
  },
  "tag_mapping": {
    "실패 조건 설명": "TAG_NAME"
  },
  "v0_2_changes": "MF-X / SF-Y / NB-Z 반영 메모 (해당 시)"
}
```

### D 카테고리 특수 (JSON schema 부속)

D_01/D_02/D_03 의 rubric에는 `json_schema` 객체가 추가됨:

```json
"json_schema": {
  "required_top_level_keys": ["case_id", "summary", "items"],
  "top_level_keys_exact": true,
  "items_length": 3,
  "required_item_keys": ["finding_id", "rule_id", "severity", "review_reason", "recommended_check"],
  "item_keys_exact": true,
  "required_finding_ids": ["rule-0001", "rule-0002", "rule-0003"],
  "preserve_input_values": ["rule_id", "severity"],
  "language_text_fields": {"language": "ko", "fields": ["summary", "review_reason", "recommended_check"]}
}
```

---

## §5. Ollama 통일 + import 대기

### §5.1 옮길 모델 (3개)

| Label | GGUF | 새 ollama 이름 |
|---|---|---|
| `hari-8b-i1` | `C:/Users/swnat/.lmstudio/models/mradermacher/hari-q3-8b-i1-GGUF/hari-q3-8b.i1-Q4_K_S.gguf` | `hari-q3-8b-i1:latest` |
| `hari-14b-i1` | `C:/Users/swnat/.lmstudio/models/mradermacher/hari-q3-14b-i1-GGUF/hari-q3-14b.i1-Q4_K_S.gguf` | `hari-q3-14b-i1:latest` |
| `ministral-3-14b-reasoning` | `C:/Users/swnat/.lmstudio/models/lmstudio-community/Ministral-3-14B-Reasoning-2512-GGUF/Ministral-3-14B-Reasoning-2512-Q6_K.gguf` | `ministral-3-14b-reasoning:latest` |

### §5.2 Modelfile 정책

- **최소 Modelfile** (`FROM <gguf-path>` 한 줄)로 시작 — 최신 GGUF 메타데이터에 chat_template이 들어있으면 ollama가 자동 picks up
- **Fallback 템플릿** 주석으로 준비:
  - hari (Qwen3 기반 추정): ChatML 템플릿 + `<|im_start|>` / `<|im_end|>` stop tokens
  - ministral: Mistral V7 (`[SYSTEM_PROMPT]` / `[INST]` / `[/INST]` / `</s>`)
- import.ps1이 끝에 각 모델 1회 호출 ("안녕. 한 줄로 응답.") → 응답 출력으로 template 정상 동작 확인. 깨지면 사용자가 Modelfile에서 fallback 블록 uncomment 후 재import.

### §5.3 측정 일관성에 대한 주의

Ollama 통일의 명시적 이유:
1. 서버 1개 운영 (LM Studio Server + lms CLI 불필요)
2. inference param default 일관 (thread 수, kv cache, batch size, sampler default 등)
3. 모델 로드/언로드 메커니즘 일관 (`ollama stop` 만)
4. 메모리 충돌 위험 감소 (두 시스템이 동시에 모델 보유 X)

단점:
- ollama auto-template 검증이 필요 (import.ps1의 probe call로 1차 점검)
- 이전 v1 평가 결과는 Ollama 4 / LM Studio 3 혼합 환경이라 v0.2 결과와 직접 비교 시 inference param 차이 변수 추가됨 (이건 어차피 prompt set 자체가 다르니 큰 문제 아님)

---

## §6. 현재 상태 및 다음 액션

### Status

- [x] Rename audit
- [x] Step 1: harness 조정 (test_suite_v0.2.json + runner 갱신 + quick_rerun config + README)
- [x] D smoke 준비 (subset prompts + 2 ollama 모델 config)
- [x] Ollama import 준비 (Modelfile 3개 + import.ps1)
- [ ] **import.ps1 실행 (사용자 PC, 진행 대기)**
- [ ] D smoke run (6 calls, 5~10분)
- [ ] 전체 7 모델 × 13 prompt quick rerun (91 calls, 30~60분)
- [ ] Step 2: 자동 채점 스크립트 (NB-3 처리 포함)
- [ ] 결과 + smoke 응답을 묶어 R2 packet 작성 (필요 시)

### 실행 순서 (사용자 PC)

```powershell
# 1. Ollama로 3개 모델 import + smoke probe
cd c:\Github\local-llm-eval\ollama-imports
.\import.ps1

# 2. D smoke (응답 사람 눈 sanity check)
cd c:\Github\local-llm-eval
python eval_runner_auto.py --config models_config_d_smoke.json --prompts prompts/test_suite_v0.2_d_only.json

# 3. 위가 OK면 전체 quick rerun
python eval_runner_auto.py --config models_config_quick_rerun.json
```

---

## §7. Codex에게 묻고 싶은 것 (review item 후보)

> 이 섹션은 사용자가 채워서 codex에 함께 전달.
> 예시:
> - Q1: `test_suite_v0.2.json` 의 rubric 구조 (특히 `required_elements` 안에 string / `{"any_of": [...]}` / `{"regex": "..."}` 혼합 형식) 이 자동 채점 스크립트 작성 시 무리 없는 표현인가? 더 단순/일관된 표현이 좋을까?
> - Q2: `category_meta.A_charting.language_policy = "ko_with_medical_en_allowed"` 플래그 + `tags_legend.MIXED_LANGUAGE.auto = "auto_with_category_whitelist"` 표현이 NB-3 처리 의도를 충분히 명확하게 전달하는가?
> - Q3: D 카테고리의 `rubric.json_schema` 객체 (top_level_keys_exact / items_length / required_item_keys 등) 가 채점 스크립트 작성 시 충분한 정보인가? 누락 항목 있는가?
> - Q4: Ollama 통일 결정에 위험/누락 고려사항 있는가? (특히 mradermacher imatrix quant의 ollama 자동 template detection 신뢰도)
> - Q5: D smoke를 사람 눈 sanity check만으로 끝낼지, 채점 스크립트 작성 전에 D smoke 응답으로 rubric을 한 번 더 다듬는 게 좋을지?

---

**End of session summary**
