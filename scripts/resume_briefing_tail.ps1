# ==============================================================
#  resume_briefing_tail.ps1 — 브리핑 예약이 1시간 제한에 걸려 꺼졌을 때 **claude 뒤 단계**를 이어서 돈다 (2026-10-06)
#  10/6: MorningSectorBriefing 예약(제한 1시간)이 09:02 에 run-briefing.ps1 을 껐다(결과 267014).
#        claude(08:14~)는 혼자 계속 돌았지만 컨센서스·서술 값·보유 현황·**웹 게시**를 아무도 안 했다
#  쓰는 법: -ClaudePid <claude 프로세스 번호> -Log <그날 briefing_*.log>
#           claude 가 끝나길 기다렸다가 run-briefing.ps1 의 「컨센서스 적재」부터 「건강검진」까지 같은 순서로 돈다
# ==============================================================
param(
    [int]$ClaudePid = 0,
    [Parameter(Mandatory = $true)][string]$Log
)
$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
function Write-Log($s) { Add-Content -Path $Log -Value "[$(Get-Date -f 'HH:mm:ss')] $s" -Encoding utf8 }

if ($ClaudePid -gt 0) {
    Write-Log "⚠️ 예약이 1시간 제한에 꺼졌다 — resume_briefing_tail 이 claude($ClaudePid) 끝을 기다린다"
    $ㅁ = 0
    while ((Get-Process -Id $ClaudePid -ErrorAction SilentlyContinue) -and ($ㅁ -lt 120)) { Start-Sleep 30; $ㅁ++ }
    if (Get-Process -Id $ClaudePid -ErrorAction SilentlyContinue) { Write-Log "⚠️ claude 가 60분 더 안 끝났다 — 기다림을 그만두고 있는 것으로 게시한다" }
    else { Write-Log "claude 종료 확인 (resume_briefing_tail)" }
}

$con = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'fetch_consensus.py'
Write-Log "컨센서스 적재: $con"
$enr = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'enrich_log.py'
Write-Log "서술 값 기록: $enr"
$pf = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'fetch_portfolio.py'
Write-Log "보유 현황: $pf"

Write-Log "웹사이트 게시 중... (resume_briefing_tail)"
$pubOut = & (Join-Path $PSScriptRoot 'publish_pages.ps1')
$pubCode = $LASTEXITCODE
$pubOut | ForEach-Object { Write-Log "  $_" }
if ($pubCode -ne 0) { Write-Log "⚠️ 웹사이트 게시 실패(exit=$pubCode)" }

try {
    $hz = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'check_health.py' -Args @('--days', '30')
    if ($hz) {
        $hzj = $hz | ConvertFrom-Json
        Write-Log ("건강검진 | 실패 {0}건" -f $hzj.실패건수)
    }
} catch { Write-Log "건강검진 건너뜀: $($_.Exception.Message)" }
Write-Log "=== 종료 (resume_briefing_tail) ==="
