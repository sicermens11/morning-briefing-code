<#
set-briefing-time.ps1 — MorningSectorBriefing 실행 시각 변경 (2026-08-21 신설)

⚠️ 관리자 권한 필요. 이 작업은 S4U(로그온 여부와 관계없이 실행)로 등록돼 있어서,
   일반 권한으로 Set-ScheduledTask를 호출하면 "Access is denied"가 난다.

사용:
  Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy','Bypass','-File','<이 파일>','-Time','08:00'

결과는 Templates\run-logs\schedule-change.log 에 기록된다
(권한 상승된 창은 바로 닫혀서 화면으로는 확인하기 어렵다).
#>
param(
    # "HH:mm" 24시간 형식
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{2}:\d{2}$')]
    [string]$Time,

    [string]$TaskName = 'MorningSectorBriefing'
)

$log = "C:\Users\mrblue\Claude\Templates\run-logs\schedule-change.log"
$dir = Split-Path $log -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

function Log([string]$m) {
    Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) -Encoding utf8
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Log "=== 시각 변경 시도: $TaskName → $Time (관리자권한=$isAdmin) ==="
if (-not $isAdmin) { Log "치명적: 관리자 권한 없음. 중단."; exit 1 }

try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $before = $task.Triggers[0].StartBoundary
    Log "변경 전 트리거: $before"

    # 기존 요일 구성(월~금)을 그대로 유지하고 시각만 바꾼다.
    $trigger = New-ScheduledTaskTrigger -Weekly `
                 -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
                 -At $Time

    Set-ScheduledTask -TaskName $TaskName -Trigger $trigger -ErrorAction Stop | Out-Null

    # ⚠️ 설명(Description)도 반드시 함께 바꾼다.
    #    트리거만 고치면 작업 스케줄러 목록의 설명에는 옛 시각이 그대로 남아, "실행 시각이
    #    몇 시지?"를 확인할 때 서로 다른 두 값이 보인다(2026-08-21에 실제로 겪음: 트리거는
    #    08:00인데 설명은 08:30으로 남아 있었다). 표시용 텍스트라 동작에는 영향이 없지만,
    #    진단할 때 사람을 헷갈리게 하는 종류의 불일치라 여기서 같이 처리한다.
    #
    #    ⚠️ Set-ScheduledTask에는 -Description 파라미터가 없다(2026-08-21 실패로 확인).
    #    작업 객체의 Description 속성을 직접 고쳐 -InputObject로 되돌려주는 방식을 쓴다.
    $desc = "평일 $Time 모닝 섹터 브리핑 (Claude Code / morning-sector-briefing 스킬)"
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $task.Description = $desc
    Set-ScheduledTask -InputObject $task -ErrorAction Stop | Out-Null
    Log "설명 갱신    : $desc"

    $after = (Get-ScheduledTask -TaskName $TaskName).Triggers[0].StartBoundary
    $next  = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
    Log "변경 후 트리거: $after"
    Log "다음 실행     : $next"
    Log "성공"
} catch {
    Log "실패: $($_.Exception.Message)"
    exit 1
}
