# ==============================================================
#  forward_daily.ps1 — **예측 기록 매일** (2026-10-06)
#  ① 얼린 무리 규칙 8개(forward-groups-spec.json · 10/2)   → data/forward-groups-log.jsonl
#  ② 반도체·2차전지 3개(forward-sectors-spec.json · 10/6)  → data/forward-sectors-log.jsonl
#  사용자 10/2 「「예측 기록 올리기」 … 진행해.」 · 10/6 「반도체·2차전지 규칙을 예측 기록 장부에 더하고, 화면에는 안 넣는다」
#  · 장 서는 날만 (krx_calendar) · 큰 파이썬(1GB↑)이 돌면 끝날 때까지 기다린다(판은 하나씩) · 평일 07:20~09:10 엔 시작 안 함
#  · 하루 빠져도 괜찮다 — 다음 날 「아직 안 적은 매수일」 을 몰아 적는다 (규칙이 얼어 있어 늦게 적어도 미래를 못 본다)
#  · 결과 한 줄을 run-logs\forward_daily_YYYYMMDD.log 에
# ==============================================================
$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\forward_daily_$(Get-Date -f yyyyMMdd).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
# ⚠️ 판 대기열(queue_*)이 살아 있으면 판 사이 틈에 끼어들어 겹친다(panels-must-not-overlap) — 대기열이 다 끝나길 기다린다
#    FD_INLINE=1 이면 대기열이 저를 부른 것(판 사이에 끼운 것)이라 대기열은 안 센다
function 대기열 { if ($env:FD_INLINE) { return 0 }; @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_' }).Count }
function 아침인가 { $n = Get-Date; $m = $n.Hour * 60 + $n.Minute; return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 440) -and ($m -lt 550)) }

$cal = & $py "scripts\krx_calendar.py" 2>&1 | Out-String
if ($cal -match "휴장") { 적기 "휴장 — 예측 기록 안 함 ($($cal.Trim()))"; exit 0 }

적기 "===== 예측 기록 시작 · 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 ====="
$ㅁ = 0
while (((큰파이썬) -gt 0) -or ((대기열) -gt 0) -or ((여유GB) -lt 15) -or (아침인가)) {
    if ($ㅁ % 60 -eq 0) { 적기 "  기다린다 — 큰 파이썬 $(큰파이썬)개 · 대기열 $(대기열)개 · 여유 $(여유GB)GB" }
    Start-Sleep 60; $ㅁ++
    if ($ㅁ -ge 1200) { 적기 "⚠️ 20시간 기다려도 판이 안 끝났다 — 오늘은 건너뛴다(내일 몰아 적는다)"; 적기 "===== 예측 기록 끝 ====="; exit 0 }
}

function 내보내기($이름, $스펙, $후보, $무리들, $낙) {
    Remove-Item (Join-Path "data" $후보) -ErrorAction SilentlyContinue
    $env:OWN_GROUPS = ($무리들 -join ';'); $env:OWN_EXPORT = "data\$스펙"; $env:OWN_EXPORT_OUT = $후보
    $env:MAXDD = $낙; $env:OWN_CUT = "20"; $env:LAB_OUT = "$(Get-Date -f yyyy-MM-dd)_예측기록_${이름}_묶음.txt"
    $p = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        if ((여유GB) -lt 3) { 적기 "🛑 $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; break }
    }
    foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    적기 "  $이름 후보 내보내기 끝 — 코드 $($p.ExitCode)"
}

# ① 얼린 8개 (7무리 · 옛 −12% 체 설정 그대로)
$날 = Get-Date -f "yyyy-MM-dd"
$무리8 = @(
    "섹터|조선 본선|||${날}_예측_조선본선.txt", "섹터|휴머노이드/로봇|||${날}_예측_로봇.txt",
    "섹터|해운|||${날}_예측_해운.txt", "규모||700|1000|${날}_예측_소형_700_1000.txt",
    "업종|비금속|||${날}_예측_비금속.txt", "업종|섬유·의류|||${날}_예측_섬유의류.txt",
    "업종|종이·목재|||${날}_예측_종이목재.txt"
)
내보내기 "얼린8" "forward-groups-spec.json" "forward_groups_cand.jsonl" $무리8 "-12"
$o1 = & $py "scripts\forward_groups.py" 2>&1
$o1 | Select-Object -Last 3 | ForEach-Object { 적기 "    [얼린8] $_" }

# ② 반도체·2차전지 (얼린 종목 목록 그대로 · 낙폭 체 없이 고른 설정 그대로)
$sp = Get-Content "data\forward-sectors-spec.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$무리S = @(); $k = 0
foreach ($무 in ($sp.규칙 | ForEach-Object { $_.무리 } | Select-Object -Unique)) {
    $k++; $코드 = $무 -replace '^종목 = ', ''
    $무리S += "종목|$코드|||${날}_예측_섹터$k.txt"
}
내보내기 "반도체2차전지" "forward-sectors-spec.json" "forward_sectors_cand.jsonl" $무리S "-999"
$env:FG_SPEC = "forward-sectors-spec.json"; $env:FG_CAND = "forward_sectors_cand.jsonl"; $env:FG_LOG = "forward-sectors-log.jsonl"
$o2 = & $py "scripts\forward_groups.py" 2>&1
foreach ($k2 in "FG_SPEC", "FG_CAND", "FG_LOG") { Remove-Item "env:$k2" -ErrorAction SilentlyContinue }
$o2 | Select-Object -Last 3 | ForEach-Object { 적기 "    [반도체·2차전지] $_" }
# ③ 변화 감지 보고서 — 매주 한 번 (월요일, 또는 마지막 보고서가 6일 넘었으면) · 가볍다(지수·후보 파일만)
#    사용자 10/6 「너 권고대로 하자.」(기준 확정) · 10/2 「만들어두자.」
$마지막 = Get-ChildItem "data\watch\watch-*.md" -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
$묵음 = if ($마지막) { ((Get-Date) - $마지막.LastWriteTime).TotalDays } else { 99 }
if (([int](Get-Date).DayOfWeek -eq 1) -or ($묵음 -gt 6)) {
    $w = & $py "scripts\regime_watch.py" 2>&1
    $w | Select-Object -Last 1 | ForEach-Object { 적기 "    [변화 감지] $_" }
}
적기 "===== 예측 기록 끝 ====="
