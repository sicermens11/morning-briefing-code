<#
move-tasks-to-code.ps1 — 예약 작업 3종의 런처 경로를 code 폴더로 이전 (2026-08-25)

배경:
  런처가 `Claude\Templates\`(Cowork 폴더)에 있었다. Cowork와 데이터를 공유하면서 두 시스템이
  서로를 "자기 자신의 2차 실행"으로 오인하는 사고가 실제로 발생해(briefing-daily-log.md에
  08-24·08-25 각각 두 항목이 섞여 기록됨) 전면 분리했다. 런처도 함께 code 폴더로 옮긴다.
  이렇게 하면 나중에 Cowork를 정리할 때 Templates를 통째로 지워도 아무 영향이 없다.

⚠️ 관리자 권한 필요. 작업이 S4U로 등록돼 있어 일반 권한으로는 "Access is denied"가 난다.

결과는 code\run-logs\schedule-change.log 에 기록된다.
#>

$log = "C:\Users\mrblue\Claude\morning breifing_code\run-logs\schedule-change.log"
$dir = Split-Path $log -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
function Log([string]$m) {
    Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) -Encoding utf8
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Log "=== 런처 경로 이전 시도 (관리자권한=$isAdmin) ==="
if (-not $isAdmin) { Log "치명적: 관리자 권한 없음. 중단."; exit 1 }

$CODE = 'C:\Users\mrblue\Claude\morning breifing_code'

# 작업별 새 실행 인자
$plan = @(
    @{ Name = 'MorningSectorBriefing'
       Arg  = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$CODE\run-briefing.ps1`"" },
    @{ Name = 'WeeklyActionReview'
       Arg  = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$CODE\run-skill.ps1`" -Skill weekly-action-review" },
    @{ Name = 'ValueChainMapUpdater'
       Arg  = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$CODE\run-skill.ps1`" -Skill value-chain-map-updater" }
)

foreach ($p in $plan) {
    try {
        $before = (Get-ScheduledTask -TaskName $p.Name -ErrorAction Stop).Actions[0].Arguments
        Log "$($p.Name) 변경 전: $before"
        $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $p.Arg
        Set-ScheduledTask -TaskName $p.Name -Action $action -ErrorAction Stop | Out-Null
        $after = (Get-ScheduledTask -TaskName $p.Name).Actions[0].Arguments
        Log "$($p.Name) 변경 후: $after"
    } catch {
        Log "$($p.Name) 실패: $($_.Exception.Message)"
    }
}

Log "=== 끝 ==="
