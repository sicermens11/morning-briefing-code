<#
  fix-weekend-briefing.ps1 — 브리핑 예약을 **평일만**으로 되돌린다 (2026-09-14)

  ⚠️ **관리자 권한으로 실행해야 한다.** 보통 창에서는 `Access is denied` 가 난다.

  무엇이 잘못됐나
  ---------------
  `MorningSectorBriefing` 혼자 **매일(Daily) 08:02** 로 걸려 있었다.
  나머지 셋은 전부 **월~금(요일마스크 62)** 이다.

      KrxFetchBeforeBriefing   07:52  월~금  ✅
      MorningSectorBriefing    08:02  **매일**  ❌  <- 이것만 다르다
      FetchAntc0850            08:50  월~금  ✅
      EntryCheck0905           09:05  월~금  ✅

  그래서 2026-09-12(토) · 09-13(일) 에도 브리핑이 돌았다.
  지난 주말들(08-29·08-30, 09-05·09-06)에 안 돈 것은 예약이 달라서가 아니라
  **그때는 PC가 꺼져 있었기** 때문이다. 이번 주말엔 시험을 돌리려고 켜 뒀다.

  왜 그냥 두면 안 되나
  --------------------
  주말 브리핑이 **월요일 재료를 먼저 먹는다.** 09-13(일) 기록에 그대로 남아 있다:
      「금요일 마감 후 나온 소식은 09-12(토) 브리핑이 이미 소화해 갭①②가 모두 소진」
  그날 후보는 0개였다.

  되돌리려면
  ----------
      Set-ScheduledTask -TaskName 'MorningSectorBriefing' `
        -Trigger (New-ScheduledTaskTrigger -Daily -At '08:02')
#>
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$이름 = 'MorningSectorBriefing'

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Output '관리자 권한이 아니다. PowerShell 을 **관리자로 실행** 해서 다시 돌려라.'
    exit 1
}

$전 = Get-ScheduledTask -TaskName $이름
Write-Output ("전: {0} · 시각 {1}" -f $전.Triggers[0].CimClass.CimClassName,
    $전.Triggers[0].StartBoundary.Substring(11, 5))

$방아쇠 = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At '08:02'
Set-ScheduledTask -TaskName $이름 -Trigger $방아쇠 | Out-Null

$후 = Get-ScheduledTask -TaskName $이름
$정보 = Get-ScheduledTaskInfo -TaskName $이름
Write-Output ("후: {0} · 요일마스크 {1} · 시각 {2}" -f $후.Triggers[0].CimClass.CimClassName,
    $후.Triggers[0].DaysOfWeek, $후.Triggers[0].StartBoundary.Substring(11, 5))
Write-Output ("상태 {0} · 다음 실행 {1}" -f $후.State, $정보.NextRunTime)

if ($후.Triggers[0].DaysOfWeek -eq 62) {
    Write-Output '✅ 월~금으로 바뀌었다. 다음 실행이 **금요일이 아닌 평일**인지 위에서 확인해라'
}
else {
    Write-Output ("⚠️ 요일마스크가 62 가 아니다 ({0}). 62 = 월+화+수+목+금" -f $후.Triggers[0].DaysOfWeek)
}

Write-Output ''
Write-Output '견줌 — 나머지 셋도 같은지:'
foreach ($n in 'KrxFetchBeforeBriefing', 'FetchAntc0850', 'EntryCheck0905') {
    try {
        $x = Get-ScheduledTask -TaskName $n
        Write-Output ("  {0,-24} {1,-22} 요일마스크 {2}" -f $n,
            $x.Triggers[0].CimClass.CimClassName, $x.Triggers[0].DaysOfWeek)
    }
    catch { Write-Output ("  {0,-24} 없다" -f $n) }
}
