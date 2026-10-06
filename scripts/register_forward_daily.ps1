# ==============================================================
#  register_forward_daily.ps1 — **예측 기록 매일 예약 등록** (2026-10-06) · ⚠️ 관리자 PowerShell 에서 한 번 실행
#  평일(월~금) 12:30 · forward_daily.ps1 (휴장일은 스크립트가 스스로 건너뛴다)
#  예약 다섯 가지: ① 전체 경로 ② WakeToRun·StartWhenAvailable ③ 배터리에서도 ④ 실패 시 3번 / 10분 ⑤ 요일 월~금 + 스크립트 휴장 가드
# ==============================================================
$root = "C:\Users\mrblue\Claude\morning breifing_code"
$act = New-ScheduledTaskAction -Execute "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$root\scripts\forward_daily.ps1`"" -WorkingDirectory $root
$trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At "12:30"
$set = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) -ExecutionTimeLimit (New-TimeSpan -Hours 22) -MultipleInstances IgnoreNew
$pri = New-ScheduledTaskPrincipal -UserId "mrblue" -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName "ForwardRecordDaily" -Action $act -Trigger $trg -Settings $set -Principal $pri -Force |
    Select-Object TaskName, State
Write-Output "등록됨 — 다음 실행: $((Get-ScheduledTaskInfo -TaskName ForwardRecordDaily).NextRunTime)"
