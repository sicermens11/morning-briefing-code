# Run this in an ADMIN PowerShell window:
#   & "C:\Users\mrblue\Claude\morning breifing_code\fix-tasks2.ps1"
#
# WHY (ASCII-only on purpose: PowerShell 5.1 reads a BOM-less UTF-8 file as
# cp949 and mangled Korean gets parsed as commands -> CommandNotFoundException)
#
# FOUND 2026-09-11 21:05. Scheduled tasks with LogonType=Interactive are tied to
# the interactive console session. When any console in that session gets a
# Ctrl+C / close, they die with exit code 3221225786 (0xC000013A =
# STATUS_CONTROL_C_EXIT).
#
# Evidence on this machine today:
#   LogonType=Interactive -> ConsensusSlowFill, KrxArrivalFine, SelfCheck-2000,
#                            EveningDataCollect, WeekendLabs2  ALL 3221225786
#   LogonType=S4U         -> MorningSectorBriefing              result 0 (fine)
#
# This also explains the 2026-09-11 08:50 miss: FetchAntc0850 is Interactive and
# ran at 09:25 instead, while the 08:02 briefing (S4U) ran on time.
#
# S4U = "Run whether user is logged on or not" WITHOUT storing a password.
# It keeps local + internet access (HTTP APIs are fine); only mapped network
# drives / SMB shares are unavailable. Nothing here uses those.
#
# Changing a task's principal requires elevation, which is why this script
# exists instead of being done automatically.

$ErrorActionPreference = "Continue"
$root = "breifing"
$ok = @(); $bad = @(); $skip = @()

Write-Host "[1/2] Switching Interactive tasks to S4U ..." -ForegroundColor Cyan
Get-ScheduledTask | Where-Object {
    ($_.Actions.Arguments -match $root -or $_.Actions.Execute -match $root) -and
    $_.Principal.LogonType -eq "Interactive"
} | ForEach-Object {
    $n = $_.TaskName
    try {
        $pr = New-ScheduledTaskPrincipal -UserId $_.Principal.UserId `
              -LogonType S4U -RunLevel $_.Principal.RunLevel
        Set-ScheduledTask -TaskName $n -Principal $pr -ErrorAction Stop | Out-Null
        $ok += $n
    } catch {
        $bad += ("{0} :: {1}" -f $n, $_.Exception.Message)
    }
}

Write-Host ""
Write-Host "=== RESULT ===" -ForegroundColor Yellow
Write-Host ("changed : {0}" -f $ok.Count) -ForegroundColor Green
$ok | ForEach-Object { "    $_" }
if ($bad.Count) {
    Write-Host ("failed  : {0}" -f $bad.Count) -ForegroundColor Red
    $bad | ForEach-Object { "    $_" }
}

Write-Host ""
Write-Host "[2/2] Verify (LogonType should be S4U everywhere)" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object {
    $_.Actions.Arguments -match $root -or $_.Actions.Execute -match $root
} | Sort-Object TaskName | ForEach-Object {
    $i = Get-ScheduledTaskInfo -TaskName $_.TaskName
    "{0,-26} {1,-12} state={2,-9} last={3} result={4}" -f `
        $_.TaskName, $_.Principal.LogonType, $_.State, $i.LastRunTime, $i.LastTaskResult
}

Write-Host ""
Write-Host "OK when every LogonType says S4U." -ForegroundColor Green
Write-Host "Tasks that still say Interactive will keep dying with 3221225786." -ForegroundColor Yellow
