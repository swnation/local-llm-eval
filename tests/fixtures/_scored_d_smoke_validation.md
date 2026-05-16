# Scored Results — v0.2 quick rerun

- 채점 시각: 2026-05-16T04:58:51.549185
- 모델 수: 2
- 채점 규칙: SCORING_CONTRACT.md (R3 sign-off)

## Summary — 모델별 카테고리 점수

| Model | D_json_phi | Total_avg | HardFail# |
|---|---|---|---|
| gemma4-latest | 0.00 (n=3) | 0.00 | 3 |
| gpt-oss-20b-low | 4.67 (n=3) | 4.67 | 0 |

## Hard-fail 발생 케이스


### gemma4-latest

- **D_01** (D_json_phi): JSON 앞뒤에 markdown fence (```) 추가 | tags: JSON_EXTRA_TEXT
- **D_02** (D_json_phi): JSON 앞뒤에 markdown fence (```) 추가 | tags: JSON_EXTRA_TEXT
- **D_03** (D_json_phi): JSON 앞뒤에 markdown fence (```) 추가 | tags: JSON_EXTRA_TEXT

## 태그 발생 매트릭스

| Model | JSON_EXTRA_TEXT |
|---|---|
| gemma4-latest | 3 |
| gpt-oss-20b-low | 0 |

## 프롬프트별 상세


### D_json_phi


#### D_01

| Model | Score | HardFail | Tags | Req Missing | Forbidden Present |
|---|---|---|---|---|---|
| gemma4-latest | 0 | YES | JSON_EXTRA_TEXT | 0 | 2 |
| gpt-oss-20b-low | 4 | no | - | 0 | 2 |

#### D_02

| Model | Score | HardFail | Tags | Req Missing | Forbidden Present |
|---|---|---|---|---|---|
| gemma4-latest | 0 | YES | JSON_EXTRA_TEXT | 0 | 0 |
| gpt-oss-20b-low | 5 | no | - | 0 | 0 |

#### D_03

| Model | Score | HardFail | Tags | Req Missing | Forbidden Present |
|---|---|---|---|---|---|
| gemma4-latest | 0 | YES | JSON_EXTRA_TEXT | 0 | 0 |
| gpt-oss-20b-low | 5 | no | - | 0 | 0 |
