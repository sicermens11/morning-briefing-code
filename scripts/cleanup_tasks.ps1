# ==============================================================
#  cleanup_tasks.ps1 — 이제 필요 없는 예약을 끄고, 지나간 일회성 예약을 지운다 (2026-09-16)
#
#  사용자 물음 「수집 중에 이제 필요없는데 수집하는 거 있나?」 → 셋을 끈다 (사용자 결정 뒤)
#    ConsensusSlowFill  02:30 매일  한경 컨센서스 띄엄띄엄 받기 — 빠진 달 0 이 된 지 며칠, 매일 「받을 것이 없다」
#    KrxArrivalFine     07:30 매일  KRX 자료 도착 시각 재는 탐침 — 답(08:10)을 얻었다. 매일 267014 로 죽는다
#    NightlyNews        23:30 매일  전 종목 뉴스 이력 — 뉴스 재료는 어떤 꼴로도 ❌ (평소배 · 종목분할 0/10). 후보 40개 뉴스는 저녁 수집이 따로 받는다
#  지나간 일회성(다시 안 돈다 · 목록만 어지럽힌다): AutoSearch 5개 · RedoLabs · EveningCollectVerify · CapitalResume0905 · DartOldBackfill · SundayLabs
#
#  ⚠️ 예약 변경은 관리자 권한이 필요하다 — **관리자 PowerShell** 에서:
#      & "C:\Users\mrblue\Claude\morning breifing_code\scripts\cleanup_tasks.ps1"
#  ⚠️ 끄기만 한다(Disable). 되살리려면 Enable-ScheduledTask 이름
# ==============================================================
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$끌것 = @("ConsensusSlowFill", "KrxArrivalFine", "NightlyNews")
$지울것 = @("AutoSearch-Fri", "AutoSearch-Sat1", "AutoSearch-Sat2", "AutoSearch-Sun1", "AutoSearch-Sun2",
            "RedoLabs", "EveningCollectVerify", "CapitalResume0905", "DartOldBackfill", "SundayLabs")

foreach ($n in $끌것) {
    $t = Get-ScheduledTask $n -ErrorAction SilentlyContinue
    if ($t) { Disable-ScheduledTask $n | Out-Null; Write-Output "  ⏸ 껐다  $n" } else { Write-Output "  · 없음  $n" }
}
foreach ($n in $지울것) {
    $t = Get-ScheduledTask $n -ErrorAction SilentlyContinue
    if ($t) { Unregister-ScheduledTask $n -Confirm:$false; Write-Output "  🗑 지웠다 $n" } else { Write-Output "  · 없음  $n" }
}
Write-Output ""
Write-Output "남은 우리 예약:"
Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' -and $_.State -ne 'Disabled' -and ($_.Actions.Arguments -match 'breifing|auto_0850') } |
    ForEach-Object { "  {0,-24} {1}" -f $_.TaskName, $_.State }
