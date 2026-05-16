# Ollama import script for LM Studio GGUF -> Ollama
# Step 1 follow-up: 7 quick rerun 모델을 모두 Ollama로 통일하기 위한 import.
#
# 사용법 (PowerShell):
#   cd c:\Github\local-llm-eval\ollama-imports
#   .\import.ps1
#
# 안전 점검: 이미 존재하는 ollama 모델은 import 시 덮어쓰기 됨. 기존에 이 이름의
# 다른 모델이 있다면 사전에 확인 후 실행.

$ErrorActionPreference = "Stop"

Write-Host "=== Ollama import start ===" -ForegroundColor Cyan

# --- 사전 점검 ---
Write-Host "`n[1/5] ollama CLI 점검..."
$null = & ollama --version
if ($LASTEXITCODE -ne 0) { Write-Error "ollama CLI not found."; exit 1 }
Write-Host "  OK"

Write-Host "`n[2/5] GGUF 파일 존재 점검..."
$files = @(
    "C:/Users/swnat/.lmstudio/models/mradermacher/hari-q3-8b-i1-GGUF/hari-q3-8b.i1-Q4_K_S.gguf",
    "C:/Users/swnat/.lmstudio/models/mradermacher/hari-q3-14b-i1-GGUF/hari-q3-14b.i1-Q4_K_S.gguf",
    "C:/Users/swnat/.lmstudio/models/lmstudio-community/Ministral-3-14B-Reasoning-2512-GGUF/Ministral-3-14B-Reasoning-2512-Q6_K.gguf"
)
foreach ($f in $files) {
    if (-not (Test-Path $f)) { Write-Error "Missing GGUF: $f"; exit 1 }
    $size = (Get-Item $f).Length / 1GB
    Write-Host ("  OK ({0:N1} GB)  {1}" -f $size, $f)
}

# --- Import ---
Write-Host "`n[3/5] hari-q3-8b-i1 import..."
& ollama create hari-q3-8b-i1 -f .\Modelfile.hari-q3-8b-i1
if ($LASTEXITCODE -ne 0) { Write-Error "hari-q3-8b-i1 import failed"; exit 1 }

Write-Host "`n[4/5] hari-q3-14b-i1 import..."
& ollama create hari-q3-14b-i1 -f .\Modelfile.hari-q3-14b-i1
if ($LASTEXITCODE -ne 0) { Write-Error "hari-q3-14b-i1 import failed"; exit 1 }

Write-Host "`n[5/5] ministral-3-14b-reasoning import..."
& ollama create ministral-3-14b-reasoning -f .\Modelfile.ministral-3-14b-reasoning
if ($LASTEXITCODE -ne 0) { Write-Error "ministral-3-14b-reasoning import failed"; exit 1 }

Write-Host "`n=== Import 완료. ollama list 확인 ===" -ForegroundColor Green
& ollama list | Select-String -Pattern "hari-q3|ministral-3-14b"

Write-Host "`n--- Smoke test (각 모델 1회 호출, template 동작 점검) ---" -ForegroundColor Cyan
$probe = @{model=""; messages=@(@{role="user"; content="안녕. 한 줄로 응답."}); stream=$false; options=@{num_predict=50}}

foreach ($name in @("hari-q3-8b-i1", "hari-q3-14b-i1", "ministral-3-14b-reasoning")) {
    Write-Host "`n  -> $name"
    $probe.model = $name
    $body = $probe | ConvertTo-Json -Depth 5
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 120
        $out = $r.message.content.Substring(0, [Math]::Min(150, $r.message.content.Length))
        Write-Host "     $out"
    } catch {
        Write-Warning "     호출 실패: $_"
    }
}

Write-Host "`n=== 끝 ===" -ForegroundColor Green
Write-Host "응답이 정상 한국어/영어로 보이면 OK."
Write-Host "응답이 깨지거나 <|im_end|> 같은 token이 그대로 보이면, 해당 Modelfile에서 fallback TEMPLATE 블록을 uncomment하고 다시 import 하세요."
