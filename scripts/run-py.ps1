<#
run-py.ps1 — morning-sector-briefing 파이썬 스크립트 실행 래퍼 (Windows 이식용, 2026-08-21 신설)

목적:
  SKILL.md가 파이썬 스크립트를 부를 때 매번 인터프리터 경로를 찾아 헤매지 않도록 한 줄로 고정한다.
  Windows에는 `python`이라는 이름의 Microsoft Store 스텁(WindowsApps\python.exe)이 PATH에 먼저
  걸려 있는 경우가 많다. 이 스텁은 실행하면 아무것도 안 하고 종료코드 9009를 뱉는데, 겉보기엔
  "python이 있다"로 보여서 진단이 오래 걸린다. 그래서 스텁을 명시적으로 걸러낸다.

사용법:
  run-py.ps1 -Script check_jargon.py -Args @('--html-file','C:\...\briefing.html')
  run-py.ps1 -Script compute_ta.py   -Args @('--file','C:\...\ta-input.json')

출력: 스크립트의 stdout(JSON)을 그대로 통과시킨다. 실패 시 stdout에 {"error": "..."} JSON을
      내보내고 종료코드 1 — 호출부가 항상 JSON을 받도록 보장해 파싱 분기를 단순하게 유지한다.
#>
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [string[]]$Args = @()
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir $Script

function Write-ErrorJson([string]$message) {
    # 호출부(LLM)가 항상 JSON을 파싱하면 되도록, 실패도 JSON으로 알린다.
    $payload = @{ error = $message } | ConvertTo-Json -Compress
    Write-Output $payload
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-ErrorJson "스크립트를 찾을 수 없음: $scriptPath"
}

# --- 파이썬 인터프리터 해석 -------------------------------------------------
# 후보를 순서대로 시험해 "실제로 실행되는" 첫 번째를 채택한다.
$candidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)
# PATH에 걸린 python도 후보에 추가하되, WindowsApps 스텁은 제외한다(위 주석 참고).
foreach ($cmd in @('python', 'python3')) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found -and $found.Source -notlike '*WindowsApps*') { $candidates += $found.Source }
}

$python = $null
foreach ($cand in $candidates) {
    if (-not (Test-Path $cand)) { continue }
    # 실제로 코드를 실행해서 살아있는 인터프리터인지 확인(존재 여부만으로는 부족).
    $probe = & $cand -c "print('ok')"
    if ($LASTEXITCODE -eq 0 -and $probe -eq 'ok') { $python = $cand; break }
}

if (-not $python) {
    Write-ErrorJson "실행 가능한 python 인터프리터를 찾지 못함. 확인한 후보: $($candidates -join '; ')"
}

# --- 실행 ------------------------------------------------------------------
# 파이썬이 한글 출력을 cp949로 인코딩하려다 실패하는 것을 막는다(UnicodeEncodeError 방지).
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$output = & $python $scriptPath @Args
$code = $LASTEXITCODE
$output | Write-Output

# --- 스냅샷 (2026-08-26 신설) ----------------------------------------------
# ⚠️ 왜 남기나 — 지금은 **규칙을 바꿔도 내일 아침까지 검증할 방법이 없다.**
#    수집 응답을 저장해두면 다시 받지 않고 STEP4~5(판정·서술)만 재실행할 수 있다.
#    "PER·PBR 재점수화"처럼 *표본이 쌓인 뒤 재검토*로 미뤄둔 것들을 즉시 실험할 수 있게 된다.
#
# ⚠️ 모델 출력이 아니라 **셸이 파일로 쓴다** — 모델이 데이터를 옮겨 적으면 그게 곧 시간이다
#    (실행 시간은 출력 토큰에 정비례, 약 70토큰/초).
#
# 데이터 수집 스크립트만 남긴다. 리포트·검산류는 원본이 아니라 가공 결과라 재생에 쓸모없다.
$snapshotTargets = @('fetch_market.py','fetch_us.py','fetch_dart.py','fetch_sector_news.py',
                     'fetch_stock.py','fetch_sec.py','compute_ta.py')
if ($code -eq 0 -and ($snapshotTargets -contains $Script)) {
    try {
        $day = Get-Date -Format 'yyyy-MM-dd'
        $dir = Join-Path (Split-Path $PSScriptRoot -Parent) "data\snapshots\$day"
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        # 같은 스크립트를 다른 인자로 여러 번 부르므로(예: fetch_dart --disclosures / --stocks)
        # 인자를 파일명에 녹여 서로 덮어쓰지 않게 한다.
        $tag = ($Args -join '_') -replace '[^A-Za-z0-9가-힣_,\-]', ''
        if ($tag.Length -gt 60) { $tag = $tag.Substring(0, 60) }
        $name = if ($tag) { "$($Script -replace '\.py$','')__$tag.json" } else { "$($Script -replace '\.py$','').json" }
        [System.IO.File]::WriteAllText((Join-Path $dir $name), ($output -join "`n"),
                                       (New-Object System.Text.UTF8Encoding $false))
    } catch {
        # ⚠️ 스냅샷 실패가 본 실행을 막지 않는다. 이건 부가 기능이다.
    }
}
exit $code
