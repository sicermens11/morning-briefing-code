# Run this in an ADMIN PowerShell window.
#   & "C:\Users\mrblue\Claude\morning breifing_code\fix-tasks.ps1"
#
# WHY (Korean comments are in 관리자로_실행.ps1; this file is ASCII-only
# on purpose, because PowerShell 5.1 reads a BOM-less UTF-8 file as cp949
# and the mangled Korean gets parsed as commands -> CommandNotFoundException,
# which is exactly what happened on 2026-09-11).
#
# 1) EntryCheck0905 (09:05 entry check) has WakeToRun OFF -> it will not run
#    if the PC is asleep. Every other scheduled task already has it ON.
# 2) Turn on the Task Scheduler operational log so a missed run leaves a trace.

Write-Host "[1/2] EntryCheck0905 ..." -ForegroundColor Cyan
$t = Get-ScheduledTask -TaskName EntryCheck0905
$s = $t.Settings
$s.WakeToRun = $true
$s.DisallowStartIfOnBatteries = $false
$s.StopIfGoingOnBatteries = $false
Set-ScheduledTask -TaskName EntryCheck0905 -Settings $s | Out-Null

Write-Host "[2/2] Task Scheduler log ..." -ForegroundColor Cyan
wevtutil sl "Microsoft-Windows-TaskScheduler/Operational" /e:true

Write-Host ""
Write-Host "=== RESULT ===" -ForegroundColor Yellow
foreach ($n in @("MorningSectorBriefing", "EntryCheck0905")) {
    $c = (Get-ScheduledTask -TaskName $n).Settings
    "{0,-24} WakeToRun={1,-6} AConly={2,-6} StopOnBattery={3}" -f `
        $n, $c.WakeToRun, $c.DisallowStartIfOnBatteries, $c.StopIfGoingOnBatteries
}
$log = wevtutil gl "Microsoft-Windows-TaskScheduler/Operational" | Select-String "enabled"
Write-Host "Log: $log"
Write-Host ""
Write-Host "OK if both say WakeToRun=True and Log shows enabled: true" -ForegroundColor Green
