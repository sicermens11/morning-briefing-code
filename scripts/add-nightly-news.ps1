<#
  add-nightly-news.ps1 — 예약 NightlyNews 를 등록한다 (2026-09-14)

  ⚠️ **관리자 권한으로 실행해야 한다.**

  무엇을 하나
  -----------
  매일 23:30 에 scripts\nightly_news.ps1 을 돌린다 — 시총 300억↑ 전 종목 뉴스를 덧붙여 받는다.
  네이버 종목뉴스는 1년치뿐이라 매일 받아야 깊이가 쌓인다 (2026-09-14 실측).

  예약 만들 때 다섯 가지 (memory: scheduled-task-checklist)
  ① 실행 파일 전체 경로  ② WakeToRun · StartWhenAvailable  ③ 배터리 무관(데스크톱)
  ④ RestartCount 3 / 10분  ⑤ 주말 가드 — 뉴스는 주말에도 나오니 **매일** 돈다 (의도)
  + LogonType S4U — Interactive 는 콘솔 세션에 묶여 3221225786 으로 죽는다 (2026-09-14 확인)

  되돌리려면:  Unregister-ScheduledTask -TaskName NightlyNews -Confirm:$false
#>
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Output '관리자 권한이 아니다. PowerShell 을 **관리자로 실행** 해서 다시 돌려라.'
    exit 1
}

$이름 = 'NightlyNews'
$스크립트 = 'C:\Users\mrblue\Claude\morning breifing_code\scripts\nightly_news.ps1'
if (-not (Test-Path $스크립트)) { Write-Output "⚠️ 없다: $스크립트"; exit 1 }

$동작 = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$스크립트`""
$방아쇠 = New-ScheduledTaskTrigger -Daily -At '23:30'
$설정 = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 5)
$주체 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

if (Get-ScheduledTask -TaskName $이름 -ErrorAction SilentlyContinue) {
    Set-ScheduledTask -TaskName $이름 -Action $동작 -Trigger $방아쇠 -Settings $설정 -Principal $주체 | Out-Null
    Write-Output "고침: $이름"
}
else {
    Register-ScheduledTask -TaskName $이름 -Action $동작 -Trigger $방아쇠 -Settings $설정 -Principal $주체 | Out-Null
    Write-Output "등록: $이름"
}
$t = Get-ScheduledTask -TaskName $이름
$i = Get-ScheduledTaskInfo -TaskName $이름
Write-Output ("  {0} · 로그온 {1} · 다음 실행 {2}" -f $t.State, $t.Principal.LogonType, $i.NextRunTime)
Write-Output '✅ 매일 23:30 · 시총 300억↑ 전 종목 뉴스 갱신'
