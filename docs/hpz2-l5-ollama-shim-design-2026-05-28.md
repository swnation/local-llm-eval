---
id: hpz2-l5-ollama-shim-design-2026-05-28
project: local-llm-eval
type: runbook
status: implementation-ready
created: 2026-05-28
scope: HP Z2 local Ollama-compatible shim for Phase 2 L5 minimal smoke
---

# HP Z2 L5 Ollama-Compatible Shim

이 문서는 Phase 2 L5 `/explain` 최소 smoke 전에 필요한 작은 통역 서버
설계와 사용법을 정리한다. 핵심 목적은 `EMR_AI_24clinic` 코드를 고치지
않고, 현재 Ollama 전용 호출을 HP Z2의 llama.cpp 서버로 연결하는 것이다.

## 왜 필요한가

현재 EMR `/explain` 경로는 Ollama 방식만 안다.

```text
EMR -> POST /api/generate
```

하지만 HP Z2의 primary backend는 llama.cpp OpenAI-compatible 서버다.

```text
llama.cpp -> POST /v1/chat/completions
```

그래서 중간에 다음처럼 통역층을 둔다.

```text
EMR ollama_client.py
  -> http://127.0.0.1:18081/api/generate
  -> hpz2_ollama_compat_llamacpp_shim.py
  -> http://127.0.0.1:18080/v1/chat/completions
  -> llama-server.exe
```

## 파일 위치

구현 파일:

```text
C:\Github\local-llm-eval\tools\hpz2_ollama_compat_llamacpp_shim.py
```

테스트:

```text
C:\Github\local-llm-eval\tests\test_hpz2_ollama_compat_llamacpp_shim.py
```

EMR repo에는 파일을 추가하거나 수정하지 않는다.

## 요청 변환 계약

EMR이 shim으로 보내는 요청:

```json
{
  "model": "hpz2-l2-qwen36-35b-a3b",
  "system": "...",
  "prompt": "...",
  "stream": false,
  "format": {
    "type": "object"
  }
}
```

Shim이 llama.cpp로 보내는 요청:

```json
{
  "model": "hpz2-l2-qwen36-35b-a3b",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "stream": false,
  "temperature": 0.0,
  "max_tokens": 8192,
  "response_format": {"type": "json_object"}
}
```

Shim이 EMR로 돌려주는 응답:

```json
{
  "model": "hpz2-l2-qwen36-35b-a3b",
  "response": "{\"summary\":\"...\",\"citations\":[\"[rule:drug:sme]\"]}",
  "done": true
}
```

EMR은 `response` 값만 읽으므로 이 응답이면 기존 `ollama_client.py`와
호환된다.

## 모델 이름 매핑

기본은 요청의 `model` 값을 그대로 llama.cpp에 전달한다.

필요하면 alias를 둘 수 있다.

```powershell
python tools\hpz2_ollama_compat_llamacpp_shim.py `
  --model-map hpz2-primary=hpz2-l2-qwen36-35b-a3b
```

그러면 EMR 설정의 모델명을 `hpz2-primary`로 두어도 실제 llama.cpp에는
`hpz2-l2-qwen36-35b-a3b`가 전달된다.

## 실행 명령

llama-server가 먼저 `127.0.0.1:18080`에서 떠 있어야 한다. Shim은 모델을
자동으로 load/unload하지 않는다.

```powershell
cd C:\Github\local-llm-eval
python tools\hpz2_ollama_compat_llamacpp_shim.py `
  --listen-host 127.0.0.1 `
  --listen-port 18081 `
  --upstream http://127.0.0.1:18080/v1 `
  --timeout-seconds 300 `
  --default-model hpz2-l2-qwen36-35b-a3b
```

EMR은 나중에 별도 GO 후 env override만 사용한다. 설정 파일을 쓰지 않는
방식이 우선이다.

```powershell
$env:EMR_LLM_ENABLED='true'
$env:EMR_LLM_PROVIDER='ollama'
$env:EMR_LLM_MODEL='hpz2-l2-qwen36-35b-a3b'
$env:EMR_LLM_HOST='http://127.0.0.1:18081'
$env:EMR_LLM_TIMEOUT_SECONDS='300'
```

## Healthcheck

Shim 자체 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:18081/health
```

응답 예:

```json
{
  "status": "ok",
  "upstream": {
    "status": "ok",
    "http_status": 200,
    "latency_ms": 3
  },
  "target": "http://127.0.0.1:18080/v1"
}
```

`status=ok`는 shim이 살아 있다는 뜻이고, `upstream.status=ok`는
llama.cpp 쪽 healthcheck도 통과했다는 뜻이다.

## 에러 매핑

| 상황 | Shim 응답 | EMR 쪽 기대 |
|---|---|---|
| 잘못된 JSON | HTTP 400 | 호출 실패 |
| `stream=true` | HTTP 400 | fail closed |
| llama.cpp 연결 안 됨 | HTTP 503 | `llm_unavailable` |
| llama.cpp timeout | HTTP 504 | unavailable 계열 |
| 모델 없음 | HTTP 404 + `model not found` | `llm_model_not_found` |
| llama.cpp 이상 응답 | HTTP 502 | unavailable 계열 |

주의: EMR 현재 구현은 HTTP 504를 별도 timeout status로 분류하지 않고
unavailable 계열로 본다. EMR 코드를 건드리지 않는 것이 이번 설계의
우선순위라서 이 차이는 허용한다.

## PHI / 로깅 안전

Shim은 다음 값을 로그에 남기지 않는다.

- `prompt`
- `system`
- LLM response text
- 전체 request body
- retrieved context
- dx/orders/order_details

로그에는 status, latency, model alias, mapped model, upstream status만 남긴다.
또한 listen host는 `localhost` 또는 `127.0.0.1`만 허용한다.

## H1 Minimal Smoke 전 preflight

아래가 모두 통과하기 전에는 `/explain`을 실행하지 않는다.

1. `local-llm-eval` HEAD가 shim 구현 commit 이상이고 clean.
2. `EMR_AI_24clinic` HEAD `218bf51f` 계열 clean, read-only 유지.
3. HP hostname `HPCHECK`.
4. C: free `>= 100 GiB`.
5. memory load `< 92%`.
6. stale `llama-server` 프로세스 없음.
7. 선택 모델 GGUF 파일 실제 존재 확인.
8. llama-server 단일 모델 load 성공.
9. shim `/health`에서 `upstream.status=ok`.
10. EMR env가 `http://127.0.0.1:18081`을 가리킴.
11. RA-03 값이 `sme + trimesy + lacto2`, `dx=a090`, `age=1` 그대로임.

## STOP 조건

즉시 중단:

- 사용자 GO 없이 `/explain` 실행.
- EMR repo 파일 수정.
- `data/llm_settings.json` 쓰기.
- shim이 `0.0.0.0` 등 외부 bind를 시도.
- 로그에 prompt/system/response가 나타남.
- 모델 파일 없음.
- llama-server load 실패.
- shim healthcheck 실패.
- C: free `< 100 GiB`.
- memory load `>= 92%`.
- RA-03 값 drift.
- 임의 runtime arg 변경 또는 자동 retry.

## 테스트

실제 모델 없이 fake llama.cpp 서버로만 검증한다.

```powershell
cd C:\Github\local-llm-eval
python -m unittest tests.test_hpz2_ollama_compat_llamacpp_shim
```

검증 범위:

- `/api/generate` -> `/v1/chat/completions` 변환.
- `system` / `prompt`가 OpenAI `messages`로 보존됨.
- model alias mapping.
- Ollama-compatible `response` 반환.
- `stream=true` fail closed.
- 404 model-not-found 매핑.
- `/health` upstream status.
- prompt/system/response가 로그에 남지 않음.
- loopback-only bind/upstream 제한.

## 현재 결론

이 shim이 통과하면 EMR 코드는 바꾸지 않아도 된다. 단, 이것은 L5 heavy
run 실행 허가가 아니다. 다음 단계는 shim 구현 commit/push, HP pull,
HP에서 fake/health preflight, 그 다음 별도 H1 `/explain` smoke GO다.
