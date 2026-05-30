---
id: hpz2-l5-ollama-shim-design-2026-05-28
project: local-llm-eval
type: runbook
status: implemented-step3-reviewed-h1-pass-shutdown-r10
created: 2026-05-28
updated: 2026-05-30
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

## H1 Minimal Smoke Plan R8

R8 overrides the older preflight pin above where it still names `218bf51f` as
the only EMR baseline. This section is still plan-only; it does not authorize
`/explain`.

### Audit pins

- `local-llm-eval` repo/doc baseline at R8 entry:
  `3000ceb` (`docs(rag): sync shim step3 review status`)
- Shim implementation commit:
  `21c6379e0fbb8c54d6932de0ee22a1b7a86277c8`
- Main PC EMR reviewed commits:
  `218bf51f0af66907333aa9c619ac2a0f732eb6d1` and latest observed
  `543e1f9ef5a0e4fcb49c47e4a55b0e5e661a6944`
- HP EMR drift observed:
  `ef6e40f...`; `218bf51f` was not a valid object on HP before refresh.
- Main PC diff check:
  `ef6e40f..543e1f9` had no changes under `app`, `scripts`, or `rag_index`.
  This makes the older HP baseline functionally low risk for `/explain`, but it
  is still not audit-clean. Refresh HP EMR before execution.

### Preferred topology

Default H1 topology is split execution:

```text
Main PC EMR harness
  -> 127.0.0.1:18081 through SSH tunnel
  -> HP Z2 loopback shim
  -> HP Z2 loopback llama-server
```

All-on-HP may be used only after HP has refreshed both relevant repos and
reported clean HEADs. In either topology, the shim remains loopback-only.

### Harness boundary

Do not use `scripts/smoke_test_explain.py` for H1 minimal smoke. It runs the
broader smoke set and writes markdown artifacts. H1 minimal uses one in-memory
`TestClient` or equivalent direct harness call for RA-03 only, with process env
override only:

```powershell
$env:EMR_LLM_ENABLED='true'
$env:EMR_LLM_PROVIDER='ollama'
$env:EMR_LLM_MODEL='hpz2-l2-qwen36-35b-a3b'
$env:EMR_LLM_HOST='http://127.0.0.1:18081'
$env:EMR_LLM_TIMEOUT_SECONDS='300'
```

### Pass criteria

- one RA-03 `/explain` request only
- HTTP 200 and EMR status `ok`
- response text parses as JSON with `summary` and `citations`
- citation verifier passes against retrieved chunks
- shim log shows model-name mapping resolved, no 404
- PHI scan hit count is zero
- `local-llm-eval` and `EMR_AI_24clinic` remain clean
- shim and llama-server are shut down; ports `18080` and `18081` have no
  listeners after teardown

### Fail / STOP

Stop after first failure and report only PHI-safe metadata if any of these
happen: `context_insufficient`, `citation_failed`, model not found, timeout,
unavailable, invalid JSON, PHI hit, dirty repo, health failure, model file
missing, or unexpected runtime argument drift.

## H1 RA-03 Tunneled Smoke Result R9

Status: PASS as a one-case endpoint-readiness smoke. This is not a Phase 2
heavy run authorization.

Execution topology:

```text
Main PC EMR .venv harness
  -> SSH tunnel on Main PC 127.0.0.1:18081
  -> HP Z2 loopback shim 127.0.0.1:18081
  -> HP Z2 loopback llama-server 127.0.0.1:18080
```

Audit pins:

- Main PC `EMR_AI_24clinic`: `543e1f9ef5a0e4fcb49c47e4a55b0e5e661a6944`
- Main PC `local-llm-eval`: `0f2da81`
- HP `EMR_AI_24clinic`: clean at `543e1f9`
- HP `local-llm-eval`: clean at `0f2da81`
- HP runtime report before execution: `llama-server` health ok and shim
  `/health` status ok with `upstream.status=ok`
- Successful tunnel target: `test@192.168.68.50`; the `hpcheck` alias had
  host-key verification drift and should not be assumed for the next run.

Harness boundary:

- Exactly one RA-03 `/explain` request.
- RA-03 values stayed locked: `sme + trimesy + lacto2`, `dx=a090`, `age=1`.
- Process env override only:
  `EMR_LLM_ENABLED=true`, `EMR_LLM_PROVIDER=ollama`,
  `EMR_LLM_MODEL=hpz2-l2-qwen36-35b-a3b`,
  `EMR_LLM_HOST=http://127.0.0.1:18081`,
  `EMR_LLM_TIMEOUT_SECONDS=300`.
- No `data/llm_settings.json` write, no EMR repo edit, no
  `scripts/smoke_test_explain.py`, no second request.

PHI-safe result metadata:

- HTTP status: `200`
- EMR status: `ok`
- raw LLM text valid JSON: yes
- JSON has `summary` and `citations`: yes
- citation verifier: pass
- PHI hit count: `0`
- retrieved chunks: `5`
- citations count: `2`
- latency: `17554 ms`
- wall time: `17565 ms`
- Main PC local tunnel listener after teardown: none
- Main PC `EMR_AI_24clinic` and `local-llm-eval` remained clean

Carry:

- H1 confirms the shim plumbing, model-name mapping, valid JSON output, citation
  verification, and PHI-zero metadata for one RA-03 request.
- H1 does not prove model quality or authorize additional cases, a matrix,
  cleanup/download, EMR writes, or `Phase 2 heavy run GO`.
- H2+ quality conclusions still require a schema-fidelity decision. The shim
  currently sends llama.cpp `response_format: {"type":"json_object"}` rather
  than forwarding the strict EMR `format` schema.
- R9 note: runtime shutdown still required a separate HP report at the time of
  the H1 result sync.

## H1 Runtime Shutdown Result R10

Status: DONE. HP confirmed the tunneled H1 runtime was stopped after the
one-case RA-03 run.

Shutdown evidence:

- shim PID `24380`: validated and stopped
- `llama-server` PID `55796`: validated and stopped
- `127.0.0.1:18080`: no listener
- `127.0.0.1:18081`: no listener

Final HP repo status:

- `EMR_AI_24clinic`: clean, `543e1f9 feat(case-review): add core6 rule engine`
- `local-llm-eval`: clean, `0f2da81 docs(rag): pin H1 smoke plan baselines`

Boundaries confirmed: no `/explain`, no `/api/generate`, no edits, no matrix,
no cleanup/download, no commit, and no push during the shutdown step.

Carry: HP `local-llm-eval` is still at R8 (`0f2da81`) and should pull/verify
repo doc R9 (`304836e`) before the next HP task that depends on repo docs.

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

## 현재 상태

Shim 구현은 main PC repo에 커밋되어 origin과 동기화된 상태다.

```text
21c6379e0fbb8c54d6932de0ee22a1b7a86277c8 feat(rag): add HP Z2 ollama llama.cpp shim
```

구현 범위는 3개 파일로 제한됐다.

- `tools/hpz2_ollama_compat_llamacpp_shim.py`
- `tests/test_hpz2_ollama_compat_llamacpp_shim.py`
- `docs/hpz2-l5-ollama-shim-design-2026-05-28.md`

Step 3 loopback health preflight는 HP Z2에서 완료됐고 shutdown까지 확인됐다.

- `llama-server` loopback `:18080` health ok
- shim loopback `:18081` health ok, upstream ok
- `/explain`, `/api/generate`, EMR write, settings write, matrix, cleanup/download
  미수행
- shutdown 후 `llama-server`와 shim 프로세스 없음, ports `18080`/`18081` not
  listening

Shim review도 PASS / CONDITIONAL GO for H1로 닫혔다. EMR은 `/api/generate`를
보내고 `response` 필드만 읽으며, shim 응답 계약은 여기에 맞는다.

H1에서 확인할 carry:

- 응답이 valid JSON인지 확인한다.
- EMR 모델명과 llama.cpp served model/model-map 정합을 확인한다.
- H2+ 품질 비교 전에는 schema fidelity를 재검토한다. 현재 shim은 EMR의 strict
  `format` schema를 그대로 전달하지 않고 llama.cpp `response_format:
  {"type":"json_object"}`만 보낸다.

R9 addendum: H1 RA-03 tunneled smoke has passed as a one-case
endpoint-readiness check. This does not authorize L5 heavy run, additional
`/explain` cases, matrix execution, EMR writes, cleanup, or downloads. R10
confirmed the H1 runtime shutdown; HP still needs to pull/verify repo doc R9
`304836e` before the next HP doc-dependent task.
