# ==============================================================
#  forward_daily.ps1 — **예측 기록 매일** (2026-10-06)
#  ① 얼린 무리 규칙 8개(forward-groups-spec.json · 10/2)   → data/forward-groups-log.jsonl
#  ② 반도체·2차전지 3개(forward-sectors-spec.json · 10/6)  → data/forward-sectors-log.jsonl
#  사용자 10/2 「「예측 기록 올리기」 … 진행해.」 · 10/6 「반도체·2차전지 규칙을 예측 기록 장부에 더하고, 화면에는 안 넣는다」
#  · 장 서는 날만 (krx_calendar) · 큰 파이썬(1GB↑)이 돌면 끝날 때까지 기다린다(판은 하나씩) · 평일 06:50~09:10 엔 시작 안 함
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
# 10/7 독립 검사: 내보내기가 1시간쯤 걸린다 — 06:50 뒤에 시작하면 08:02 브리핑과 겹친다 ⇒ 06:50~09:10 엔 시작 안 함
function 아침인가 { $n = Get-Date; $m = $n.Hour * 60 + $n.Minute; return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 410) -and ($m -lt 550)) }

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

# ⚠️ 10/12 발견: ETF(etf-krx)는 저녁 20:37 에야 전날 것을 받아 12:30 엔 마지막 날 ETF 가 없었다 —
#    조선 본선 규칙(ETF시총20)이 마지막 날을 못 봤다. KRX 는 08:00 에 이미 준다 — 내보내기 전에 받는다(몇 초)
$etf = & $py "scripts\collect_krx_etf.py" "--최근" "3" 2>&1
적기 "  ETF 받기: $($etf | Select-Object -Last 1)"

# ① 얼린 8개 (7무리 · 옛 −12% 체 설정 그대로)
$날 = Get-Date -f "yyyy-MM-dd"
$무리8 = @(
    "섹터|조선 본선|||${날}_예측_조선본선.txt", "섹터|휴머노이드/로봇|||${날}_예측_로봇.txt",
    "섹터|해운|||${날}_예측_해운.txt", "규모||700|1000|${날}_예측_소형_700_1000.txt",
    "업종|비금속|||${날}_예측_비금속.txt", "업종|섬유·의류|||${날}_예측_섬유의류.txt",
    "업종|종이·목재|||${날}_예측_종이목재.txt"
)
# 10/7 B 사이트 반영 — 같은 실행에서 무리마다 재료 기준선을 남긴다(아침 빠른 모드가 쓴다)
$env:OWN_THRESH_SAVE = "data\b-thresholds.json"
내보내기 "얼린8" "forward-groups-spec.json" "forward_groups_cand.jsonl" $무리8 "-12"
Remove-Item env:OWN_THRESH_SAVE -ErrorAction SilentlyContinue
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
# ⑤ 2026-10-13 **임원·주요주주 여럿이 함께 산 종목** 예측 기록 — 사용자 10/13 「응」(화면엔 안 넣고 기록만 · 20건↑ 쌓이면 판단) · 약 80초 · 4GB 안팎
$o5 = & $py "scripts\forward_insider.py" 2>&1
$o5 | Select-Object -Last 2 | ForEach-Object { 적기 "    [임원 함께 매수] $_" }
# ④ 2026-10-12 **C(전체 시장 규칙 4개) 예측 기록** — 10/8 첫 판(B243) 뒤 **매일 돌리는 곳이 없었다**(0줄 · 내가 「예측 기록 중」 이라 잘못 말함)
#    사용자 10/7 「오케이 그렇게 하자.」(20건↑ + 2주 뒤 판단) — 그러려면 매일 쌓여야 한다
#    OWN_ALL 24GB 판이라 여유 32GB↑ · 큰 파이썬 0 · 대기열 0 일 때만(보통 밤) · 다음 날 05:30 까지 기다리고(아침 08:02·B 아침 계산과 안 겹치게) 못 하면 건너뛴다
#    forward_groups.py 는 빠진 날을 다음 실행에서 몰아 적는다(얼린 날 뒤 매수만)
$끝기다림 = (Get-Date).Date.AddDays(1).AddHours(5).AddMinutes(30)
$ㅁC = 0
#    ⚠️ 10/12 저녁: 아무것도 안 돌 때 여유가 28.7~30.9GB 뿐이라 32 를 영영 못 넘었다 → 28 로 낮춤
#    ⚠️ 10/13 15:41: 28GB 에서 시작했는데 브라우저 등이 더 써서 도중에 여유 2.9GB → 지킴이가 껐다(그날 C 빠짐)
#       → **꺼지면 30분 뒤 다시**(최대 3번 · 다음 날 05:30 까지) · 다시 할 땐 30GB 를 기다린다
$C됨 = $false
for ($시도 = 1; ($시도 -le 3) -and (-not $C됨); $시도++) {
    $문C = if ($시도 -eq 1) { 28 } else { 30 }
    while ((((여유GB) -lt $문C) -or ((큰파이썬) -gt 0) -or ((대기열) -gt 0)) -and ((Get-Date) -lt $끝기다림)) {
        if ($ㅁC % 60 -eq 0) { 적기 "  C 기다린다($시도 번째 · 문 ${문C}GB) — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 · 대기열 $(대기열)개" }
        Start-Sleep 60; $ㅁC++
    }
    if ((Get-Date) -ge $끝기다림) {
        적기 "⚠️ C: $($끝기다림.ToString('MM-dd HH:mm')) 까지 여유 ${문C}GB 가 안 됐다 — 오늘 C 는 건너뛴다(다음 실행이 몰아 적는다)"
        break
    }
    Remove-Item "data\forward_market_cand.jsonl" -ErrorAction SilentlyContinue
    $env:OWN_ALL = "1"; $env:OWN_START = "20200102"; $env:OWN_SPLIT = "20240101"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"
    $env:OWN_EXPORT = "data\forward-market-spec.json"; $env:OWN_EXPORT_OUT = "forward_market_cand.jsonl"; $env:LAB_OUT = "${날}_예측기록_C시장전체.txt"
    적기 "  C 후보 내보내기 시작($시도 번째) · 여유 $(여유GB)GB"
    $pC = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    $null = $pC.Handle
    $꺼짐 = $false
    while (-not $pC.HasExited) {
        Start-Sleep 30
        if ((여유GB) -lt 3) { 적기 "🛑 C 여유 $(여유GB)GB — 끈다($시도 번째)"; try { Stop-Process -Id $pC.Id -Force } catch { }; $꺼짐 = $true; break }
    }
    foreach ($k3 in "OWN_ALL", "OWN_START", "OWN_SPLIT", "MAXDD", "OWN_CUT", "OWN_EXPORT", "OWN_EXPORT_OUT", "LAB_OUT") { Remove-Item "env:$k3" -ErrorAction SilentlyContinue }
    적기 "  C 후보 내보내기 끝 — 코드 $($pC.ExitCode)"
    if ($꺼짐 -or -not (Test-Path "data\forward_market_cand.jsonl")) {
        if ($시도 -lt 3) { 적기 "  ↻ C 를 30분 뒤 다시 한다"; Start-Sleep 1800 }
        continue
    }
    $C됨 = $true
    $env:FG_SPEC = "forward-market-spec.json"; $env:FG_CAND = "forward_market_cand.jsonl"; $env:FG_LOG = "forward-market-log.jsonl"
    $o3 = & $py "scripts\forward_groups.py" 2>&1
    foreach ($k3 in "FG_SPEC", "FG_CAND", "FG_LOG") { Remove-Item "env:$k3" -ErrorAction SilentlyContinue }
    $o3 | Select-Object -Last 3 | ForEach-Object { 적기 "    [C 시장 전체] $_" }
}
if (-not $C됨) { 적기 "⚠️ C: 세 번 안에 못 끝냈다 — 오늘 C 는 건너뛴다(다음 실행이 몰아 적는다)" }

# ③ 변화 감지 보고서 — 매주 한 번 (월요일, 또는 마지막 보고서가 6일 넘었으면) · 가볍다(지수·후보 파일만)
#    사용자 10/6 「너 권고대로 하자.」(기준 확정) · 10/2 「만들어두자.」
$마지막 = Get-ChildItem "data\watch\watch-*.md" -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
$묵음 = if ($마지막) { ((Get-Date) - $마지막.LastWriteTime).TotalDays } else { 99 }
if (([int](Get-Date).DayOfWeek -eq 1) -or ($묵음 -gt 6)) {
    $w = & $py "scripts\regime_watch.py" 2>&1
    $w | Select-Object -Last 1 | ForEach-Object { 적기 "    [변화 감지] $_" }
}
적기 "===== 예측 기록 끝 ====="
