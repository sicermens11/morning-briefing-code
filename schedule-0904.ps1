# schedule-0904.ps1 — 09-04 수집 예약 (2026-09-03 작성)
#
# 왜 예약 작업으로 하나:
#   어제(09-02) 새벽 03:53에 세션이 끊긴 적이 있다. 원인 불명.
#   내가 직접 돌리면 세션이 끊길 때 수집도 멈춘다.
#   예약 작업은 세션과 무관하게 돈다.
#
# DART 하루 한도(20,000회) 배분:
#   00:05  공시 백필 900일   약 7,065회  (DartOldBackfill · 이미 등록됨)
#   00:35  업종 분류        약 3,988회  (IndustryCollect)
#   01:00  증자감자         상한 8,500회 (CapitalCollect)
#   ------------------------------------------------
#   합계 약 19,553회 — 한도 안에 들어간다
#   ⚠️ 증자감자는 3,988종목 x 6종 = 23,928회라 하루에 다 못 받는다.
#      8,500회면 약 1,400종목(35%). 나머지는 09-05, 09-06에 이어받는다
#      (collect_capital.py는 이미 받은 종목을 건너뛴다)

$py = 'C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe'
$base = 'C:\Users\mrblue\Claude\morning breifing_code\scripts'

# ── 업종 분류 (공시 백필이 00:23쯤 끝나므로 00:35) ──
$a1 = New-ScheduledTaskAction -Execute $py -Argument ('"' + $base + '\collect_industry.py"')
$t1 = New-ScheduledTaskTrigger -Once -At '2026-09-04 00:35'
Register-ScheduledTask -TaskName 'IndustryCollect' -Action $a1 -Trigger $t1 `
    -Description '업종 분류 수집 (DART 기업개황 induty_code) - 공시 백필 뒤' -Force | Out-Null
Write-Output 'IndustryCollect  2026-09-04 00:35 등록'

# ── 증자감자 (업종이 00:50쯤 끝나므로 01:00) ──
$a2 = New-ScheduledTaskAction -Execute $py -Argument ('"' + $base + '\collect_capital.py" --상한 8500')
$t2 = New-ScheduledTaskTrigger -Once -At '2026-09-04 01:00'
Register-ScheduledTask -TaskName 'CapitalCollect' -Action $a2 -Trigger $t2 `
    -Description '증자감자 6종 수집 - 남은 DART 한도로 (이어받기 가능)' -Force | Out-Null
Write-Output 'CapitalCollect   2026-09-04 01:00 등록 (상한 8500회)'

# ── 확인 ──
Get-ScheduledTask -TaskName 'DartOldBackfill', 'IndustryCollect', 'CapitalCollect' |
    ForEach-Object {
        $i = $_ | Get-ScheduledTaskInfo
        '{0,-20} {1}' -f $_.TaskName, $i.NextRunTime
    }
