# ==============================================================
#  enable-nightly-news.ps1 — 밤 종목뉴스 예약을 **다시 켠다** (2026-09-28)
#
#  ⚠️ **관리자 권한으로 열린 PowerShell 창**에서 돌려야 한다.
#     보통 창에서는 "액세스가 거부되었습니다" 로 죽는다.
#
#  왜 꺼져 있었나
#  ---------------
#  2026-09-15 23:40, 2,200종목을 받던 중 종목 하나(001720)를 파일로 쓰다가
#      OSError: [Errno 22] Invalid argument
#  가 났고 **작업 전체가 죽었다.** 그 뒤 예약이 꺼진 채 13일이 지났다.
#  2026-09-28 에 같은 파일에 같은 방식으로 다시 써 보니 **멀쩡히 써진다** —
#  그날만의 일시적 사정(파일 잠김·백신·동기화)이었다.
#
#  그래서 켜기 전에 collect_news.py 를 먼저 고쳤다:
#    · 옆에 썼다가 바꿔치기(os.replace) — 쓰다 만 파일이 안 남는다
#    · 실패하면 2초 쉬고 한 번 더
#    · 그래도 안 되면 **그 종목만 건너뛰고 계속** 간다 (끝에 몇 개 실패했는지 찍는다)
#
#  깨우기·재시도 설정(WakeToRun · StartWhenAvailable · 재시도 3회/10분)은
#  이미 제대로 돼 있어서 **손대지 않는다.** 켜기만 한다.
# ==============================================================
$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName "NightlyNews" -ErrorAction SilentlyContinue
if (-not $t) {
    Write-Host "NightlyNews 예약이 없다. scripts\add-nightly-news.ps1 로 먼저 만들어야 한다." -ForegroundColor Red
    exit 1
}

Write-Host "켜기 전 상태 : $($t.State)"
Enable-ScheduledTask -TaskName "NightlyNews" | Out-Null

$t = Get-ScheduledTask -TaskName "NightlyNews"
$i = Get-ScheduledTaskInfo -TaskName "NightlyNews"
Write-Host "켜고 난 상태 : $($t.State)" -ForegroundColor Green
Write-Host "다음 실행    : $($i.NextRunTime)"
Write-Host ""
Write-Host "확인할 것 — 내일 아침 run-logs\nightly_news_20260929.log 에" -ForegroundColor Cyan
Write-Host "            '끝 · 받음 NNNN' 이 찍혀 있으면 정상이다." -ForegroundColor Cyan
