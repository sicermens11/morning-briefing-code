<#
  fix-antc-triggers.ps1 — 예상체결가 예약을 **세 시각 고정**으로 바꾼다 (2026-09-14)

  ⚠️ **관리자 권한으로 실행해야 한다.**

  무엇이 잘못됐나
  ---------------
  `FetchAntc0850` 트리거에 **반복 5분 · 지속 15분**(PT5M/PT15M)이 걸려 있었다.
  의도는 「08:50 에 API 가 막히면 건진다」(재시도)였는데, 구현이 `Repetition`
  이라 **성공해도 계속 돌며 덮어썼다.**

      08:50  32/40 받음  ->  살 것 2개      웹 게시
      08:55  35/40 받음  ->  살 것 1개      덮어씀
      09:00  26/40 받음  ->  **살 것 없음**  덮어씀   <- 이게 남았다
      09:05   0/40       ->  실패(코드 1)

  09:00 은 **장이 열린 뒤**라 예상체결가가 아니라 시가였다. 21종목을 실제
  시가와 맞춰 보니 09:00 값은 평균 오차 0.04%p — 사실상 시가 그 자체다.

  무엇으로 바꾸나
  ---------------
      08:50  로그만 (표본 수집 — 나중에 「어느 시각이 시가를 잘 맞히나」 판정용)
      08:55  **판정** (forward-log 에 기록 · 웹 게시)
      08:58  08:55 가 실패했을 때만 기록 (성공했으면 덮지 않는다)

  09:00 이후는 아예 안 돈다. `fetch_antc.py` 도 `< 09:00` 으로 막는다.

  되돌리려면
  ----------
      $r = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '08:50'
      $r.Repetition = (New-ScheduledTaskTrigger -Once -At '08:50' `
          -RepetitionInterval (New-TimeSpan -Minutes 5) `
          -RepetitionDuration (New-TimeSpan -Minutes 15)).Repetition
      Set-ScheduledTask -TaskName 'FetchAntc0850' -Trigger $r
#>
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$이름 = 'FetchAntc0850'

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Output '관리자 권한이 아니다. PowerShell 을 **관리자로 실행** 해서 다시 돌려라.'
    exit 1
}

$전 = (Get-ScheduledTask -TaskName $이름).Triggers
Write-Output ("전: 트리거 {0}개" -f $전.Count)
foreach ($t in $전) {
    $반 = if ($t.Repetition -and $t.Repetition.Interval) {
        "반복 $($t.Repetition.Interval)/$($t.Repetition.Duration)"
    }
    else { '반복 없음' }
    Write-Output ("    {0} · 요일 {1} · {2}" -f $t.StartBoundary.Substring(11, 5), $t.DaysOfWeek, $반)
}

$평일 = 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
$새것 = @(
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $평일 -At '08:50'),
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $평일 -At '08:55'),
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $평일 -At '08:58')
)
Set-ScheduledTask -TaskName $이름 -Trigger $새것 | Out-Null

$후 = (Get-ScheduledTask -TaskName $이름).Triggers
Write-Output ''
Write-Output ("후: 트리거 {0}개" -f $후.Count)
$탈 = 0
foreach ($t in $후) {
    $반 = if ($t.Repetition -and $t.Repetition.Interval) {
        "**반복 $($t.Repetition.Interval)** <- 남아 있으면 안 된다"
    }
    else { '반복 없음' }
    if ($t.Repetition -and $t.Repetition.Interval) { $탈++ }
    if ($t.DaysOfWeek -ne 62) { $탈++ }
    Write-Output ("    {0} · 요일마스크 {1} · {2}" -f $t.StartBoundary.Substring(11, 5),
        $t.DaysOfWeek, $반)
}

$정보 = Get-ScheduledTaskInfo -TaskName $이름
Write-Output ("상태 {0} · 다음 실행 {1}" -f (Get-ScheduledTask -TaskName $이름).State,
    $정보.NextRunTime)

if ($후.Count -eq 3 -and $탈 -eq 0) {
    Write-Output ''
    Write-Output '✅ 08:50 · 08:55 · 08:58 세 번, 반복 없음, 월~금. 09:00 이후는 안 돈다'
}
else {
    Write-Output ''
    Write-Output ("⚠️ 트리거 {0}개 · 어긋남 {1}건 — 위 목록을 확인해라" -f $후.Count, $탈)
}
