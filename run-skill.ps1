<#
run-skill.ps1 — 주기 실행 스킬 공용 런처 (2026-08-21 신설)

morning-sector-briefing 외의 주기 실행 스킬(value-chain-map-updater, weekly-action-review)을
Windows 작업 스케줄러가 이걸로 부른다. 브리핑 전용 런처(run-briefing.ps1)는 제목 suffix·테스트
모드 같은 브리핑 고유 사정이 있어 따로 두고, 나머지는 여기로 묶는다.

사용:
    run-skill.ps1 -Skill weekly-action-review
    run-skill.ps1 -Skill value-chain-map-updater -DryRun

⚠️ 이 파일은 반드시 **UTF-8 BOM 포함**으로 저장할 것.
   Windows PowerShell 5.1은 BOM 없는 UTF-8 스크립트를 ANSI로 읽어서, 스크립트 안의 한글이
   실행 시점에 깨진다. 그러면 깨진 프롬프트가 claude에게 전달되는데 로그만 봐서는 원인을
   알기 어렵다(2026-08-21 브리핑 첫 테스트에서 실제로 겪음). -DryRun으로 먼저 확인할 것.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('value-chain-map-updater', 'weekly-action-review', 'entry-check')]
    [string]$Skill,

    # entry-check 전용: 어느 시간대 슬롯인지(0905=개장직후 / 1220=점심).
    # 하루에 두 번 돌 수 있어서 결과 저장 시 슬롯으로 구분한다.
    [ValidateSet('0905', '1220')]
    [string]$Slot = '0905',

    # claude를 부르지 않고 조립된 프롬프트만 출력(한글 인코딩 확인용)
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'

$claude  = "C:\Users\mrblue\.local\bin\claude.exe"
$logDir  = "C:\Users\mrblue\Claude\morning breifing_code\run-logs"
$stamp   = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$logFile = Join-Path $logDir "$Skill`_$stamp.log"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

function Write-Log([string]$msg) {
    Add-Content -Path $logFile -Value ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg) -Encoding utf8
}

Write-Log "=== $Skill 시작 ==="

if (-not (Test-Path $claude)) {
    Write-Log "치명적: claude CLI를 찾을 수 없음 ($claude). 실행 중단."
    exit 1
}

# --- 스킬별 마무리 지시 ------------------------------------------------------
switch ($Skill) {
    'value-chain-map-updater' {
        $tail = @"
- STEP 4는 파일 전체를 재생성하지 않는다. 바뀐 섹터의 OR-쿼리 줄만 Edit으로 고친다.
- 백업(SKILL-backups\value-chain-map_[날짜].md)을 먼저 만든 뒤에 고친다.
- 마지막에 요약을 5줄 이내로 출력한다: 추가 종목 / 삭제 종목 / 재확인 건수 / 실패한 항목 / 카카오 알림 결과.
"@
    }
    'entry-check' {
        $tail = @"
- STEP 1에서 스크립트를 부를 때 슬롯 인자를 그대로 넘긴다: -Args @('--save','--slot','$Slot')
- 종목을 새로 발굴하지 않는다. 오늘 브리핑이 정한 픽만 판정한다.
- 카카오 본문은 200자 안팎으로 짧게 — 출근길·점심에 폰으로 보는 것이다.
- 09:05 슬롯이면 추세·수급 이야기를 쓰지 않는다(그 시각엔 무의미하다). 시초가 갭과 조건 충족 여부만 쓴다.
- 마지막에 3줄 이내 요약을 출력한다: 판정 요약 / 카카오 결과 / 실패 항목.
"@
    }
    'weekly-action-review' {
        $tail = @"
- STEP 3의 호출 캡(종목당 1회·전체 20회, 섹터ETF 5회)을 넘기지 않는다. 안 나오는 종목은 "데이터 미확인"으로 두고 넘어간다.
- STEP 6 Gmail 발송까지 반드시 도달한다. 중간이 실패해도 확보한 데이터만으로 리뷰를 발송한다.
- 마지막에 요약을 5줄 이내로 출력한다: 리뷰 대상 종목수 / 적중·빗나감 / 데이터 미확인 / Gmail 결과 / 실패한 항목.
"@
    }
}

$prompt = @"
$Skill 스킬을 실행해라. 이 실행은 스케줄러에 의한 무인 자동실행이다.

반드시 지킬 것:
- 스킬의 STEP 0부터 순서대로 따른다. STEP 0의 도구 스키마 선조회를 건너뛰지 않는다.
- 사용자에게 질문하지 않는다. 응답할 사람이 없다. 판단이 애매하면 스킬에 적힌 안전 기본값을 따른다.
- 셸은 PowerShell이다. bash 관용구를 실행하지 않는다.
$tail
"@

# ⚠️ ToolSearch가 반드시 들어가야 한다. 이 환경의 MCP 도구는 전부 deferred 상태라
#    ToolSearch로 스키마를 불러오지 못하면 커넥터가 붙어 있어도 "도구 없음"으로 실패한다.
$allowed = @(
    'ToolSearch', 'Read', 'Write', 'Edit', 'Glob', 'Grep', 'Skill',
    # ⚠️ PowerShell은 반드시 있어야 한다 (2026-08-25 실제 사고로 확인).
    #    이게 빠져 있어서 entry-check가 `run-py.ps1`을 호출하지 못하고 **권한 거부 13건**으로
    #    판정을 통째로 실패했다. 로컬 스크립트로 데이터를 가져오는 구조라, 셸 도구가 막히면
    #    스킬이 아무것도 못 한다. 브리핑 런처에는 처음부터 있었는데 이 공용 런처에만 없었다.
    'PowerShell', 'Bash',
    'mcp__claude_ai_PlayMCP__*',
    'mcp__claude_ai_FMP__*',
    'mcp__claude_ai_Gmail__*'
)

if ($DryRun) {
    Write-Output "===== [DryRun] $Skill 허용 도구 ====="
    $allowed | ForEach-Object { Write-Output "  $_" }
    Write-Output "`n===== [DryRun] 전달될 프롬프트 ====="
    Write-Output $prompt
    Write-Output "`n===== [DryRun] 끝 — claude는 호출하지 않았음 ====="
    Write-Log "DryRun으로 종료(claude 미호출)"
    exit 0
}

# ⚠️ claude.exe 호출 전 필수 (2026-08-25 추가, run-briefing.ps1과 동일 사고).
#    한국어 Windows의 기본 콘솔 인코딩이 cp949라, 이 줄이 없으면 claude의 UTF-8 출력이
#    깨진 채 로그에 남아 사후 확인이 불가능해진다.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Log "claude 실행 시작..."
$sw = [System.Diagnostics.Stopwatch]::StartNew()

# 모델 선택(2026-08-25): entry-check는 "판단"이 아니라 "대조"다 — 조건이 이미 숫자로 박혀 있고
# 스크립트가 판정까지 끝내므로, 남는 일은 결과를 짧은 문장으로 옮기는 것뿐이다. 가벼운 모델로 충분하다.
# 나머지 스킬은 갭 판정·서술이 필요하므로 Opus를 쓴다.
$model = if ($Skill -eq 'entry-check') { 'claude-sonnet-5' } else { 'claude-opus-5' }
Write-Log "모델: $model"

# --output-format json: 실행 요약과 함께 토큰·비용을 받는다(2026-08-21 추가, run-briefing.ps1과 동일 이유).
$raw = & $claude -p $prompt --allowedTools @allowed --max-turns 200 --model $model --output-format json
$code = $LASTEXITCODE

$sw.Stop()
Write-Log "claude 종료 (exit=$code, 소요 $([math]::Round($sw.Elapsed.TotalMinutes,1))분)"

# 계측 파싱 실패가 실행 실패가 되지 않도록 감싼다(부가 정보일 뿐이다).
$result = $null
try {
    $j = $raw | ConvertFrom-Json
    $u = $j.usage
    $inTotal = [int]$u.input_tokens + [int]$u.cache_creation_input_tokens + [int]$u.cache_read_input_tokens
    Write-Log ("사용량 | 턴 {0} | 입력 {1:N0} (캐시읽기 {2:N0} · 캐시생성 {3:N0} · 신규 {4:N0}) | 출력 {5:N0} | 비용 ${6:N2}(0이면 미제공)" -f `
        $j.num_turns, $inTotal, [int]$u.cache_read_input_tokens, [int]$u.cache_creation_input_tokens, `
        [int]$u.input_tokens, [int]$u.output_tokens, $(if ($null -ne $j.total_cost_usd) { [double]$j.total_cost_usd } else { 0 }))
    if ($j.permission_denials -and $j.permission_denials.Count -gt 0) {
        Write-Log "⚠️ 권한 거부 $($j.permission_denials.Count)건 — 허용 도구 목록 확인 필요"
    }
    if ($j.is_error) { Write-Log "⚠️ claude가 오류로 종료함 (subtype=$($j.subtype))" }
    $result = $j.result
} catch {
    Write-Log "사용량 파싱 실패: $($_.Exception.Message) — 아래에 원문을 남긴다"
    $result = $raw
}

Write-Log "--- 실행 요약 ---"
if ($result) { Add-Content -Path $logFile -Value $result -Encoding utf8 }
Write-Log "--- 요약 끝 ---"

# ⚠️⚠️ **진입체크가 끝나면 웹을 다시 올린다** (2026-08-31 신설).
#    카카오 전송을 폐지하면서 09:05 판정의 **유일한 출구가 웹**이 됐다. 그런데 사이트는
#    08:00에 만들어지므로, 다시 올리지 않으면 **09:05 결과가 하루 종일 안 보인다** —
#    정확히는 다음 날 아침에야 보인다. 그때 보는 판정은 아무 쓸모가 없다.
#    ⚠️ 모델을 부르지 않는다. 파일을 다시 조립해 올리는 것뿐이라 토큰이 들지 않는다.
#    ⚠️ 실패해도 진입체크 자체를 실패로 만들지 않는다 — 판정은 이미 로그에 저장됐다.
if ($Skill -eq 'entry-check') {
    Write-Log "웹 재게시 중(09:05 판정을 화면에 올린다)..."
    try {
        $pub = & (Join-Path $PSScriptRoot 'scripts\publish_pages.ps1')
        $pub | ForEach-Object { Write-Log "  $_" }
    } catch {
        Write-Log "웹 재게시 실패: $($_.Exception.Message) — 판정은 로그에 남아 있다"
    }
}

Get-ChildItem $logDir -Filter "$Skill`_*.log" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-180) } |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Log "=== 종료 ==="
exit $code
