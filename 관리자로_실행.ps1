# ══════════════════════════════════════════════════════════════
#  관리자 권한 PowerShell 에서 실행한다 (2026-09-11 갱신)
#
#  ⚠️ 월요일 아침 실행 전에 **이것만 해두면** 예약 쪽 위험은 없다
#
#  ① EntryCheck0905 — 09:05 결과 확인이 **절전 해제가 꺼져 있다.**
#     오늘 아침 브리핑에서 겪은 것과 **같은 문제**다. PC 가 자면 안 돈다
#     (나머지 11개 예약은 이미 켜져 있다)
#  ② 작업 스케줄러 로그 — 이미 켰다면 그대로 둔다. 안 켜졌으면 켠다
# ══════════════════════════════════════════════════════════════

Write-Host "① EntryCheck0905 절전 해제 켜는 중..." -ForegroundColor Cyan
$t = Get-ScheduledTask -TaskName EntryCheck0905
$s = $t.Settings
$s.WakeToRun = $true                      # 자고 있어도 깨워서 돌린다
$s.DisallowStartIfOnBatteries = $false    # 배터리여도 시작한다
$s.StopIfGoingOnBatteries = $false        # 배터리로 바뀌어도 안 멈춘다
Set-ScheduledTask -TaskName EntryCheck0905 -Settings $s | Out-Null

Write-Host "② 작업 스케줄러 로그 확인..." -ForegroundColor Cyan
wevtutil sl "Microsoft-Windows-TaskScheduler/Operational" /e:true

Write-Host ""
Write-Host "=== 확인 ===" -ForegroundColor Yellow
foreach ($n in @("MorningSectorBriefing", "EntryCheck0905")) {
    $c = (Get-ScheduledTask -TaskName $n).Settings
    "{0,-24} 절전해제={1,-6} AC만={2,-6} 배터리중지={3}" -f `
        $n, $c.WakeToRun, $c.DisallowStartIfOnBatteries, $c.StopIfGoingOnBatteries
}
$log = wevtutil gl "Microsoft-Windows-TaskScheduler/Operational" | Select-String "enabled"
Write-Host "로그 상태: $log"
Write-Host ""
Write-Host "둘 다 절전해제=True · enabled: true 면 됐다" -ForegroundColor Green
