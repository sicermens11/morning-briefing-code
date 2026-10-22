<#
  register-kis-compare.ps1 — 예약 「KisCompare0856」 을 만든다 (2026-10-22)

  ⚠️ **관리자 권한 PowerShell 에서 실행해야 한다.**
      & "C:\Users\mrblue\Claude\morning breifing_code\scripts\register-kis-compare.ps1"

  무엇: 월~금 08:56 에 scripts\kis_compare_antc.py 를 돌린다 — 한국투자증권(모의) 예상체결가를 받아
        NH 값(08:55 판정에 쓴 것)과 나란히 data\_kis_compare.log 에 적는다. **조회만 · 주문 없음.**
  왜:   사용자 10/22 「가(권고)로 하자」 — 자동매매를 한국투자증권으로 옮기기 전 두 값이 같은지 확인차.
        같다고 확인되면 이 예약은 지운다:  Unregister-ScheduledTask KisCompare0856 -Confirm:$false
  다섯 가지(memory/scheduled-task-checklist): ① python 전체 경로 ② WakeToRun·StartWhenAvailable ③ 배터리 무관 ④ 재시도 3회/10분 ⑤ 월~금 + 스크립트 안 휴장 가드
#>
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$sc = "C:\Users\mrblue\Claude\morning breifing_code\scripts\kis_compare_antc.py"
$a = New-ScheduledTaskAction -Execute $py -Argument "`"$sc`"" -WorkingDirectory "C:\Users\mrblue\Claude\morning breifing_code"
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "08:56"
$s = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
     -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$p = New-ScheduledTaskPrincipal -UserId "mrblue" -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName "KisCompare0856" -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null
$k = Get-ScheduledTask KisCompare0856
Write-Output ("등록됨: {0} · 다음 실행 {1}" -f $k.State, ($k | Get-ScheduledTaskInfo).NextRunTime)
