# ==============================================================
#  queue_b219.ps1 — **예측 기록(무리 규칙 8개) + 화면 사실 바로잡기(CARDLIVE 종가 칸)** (2026-10-02)
#  사용자: 「「사실 바로잡기(화면 문구)」와 「예측 기록 올리기」 두가지 진행해.」
#  B218(자름 20 → 표 → 자름 10 → 30)이 끝난 뒤에 돈다 (판은 하나씩)
#  ① own_lab OWN_EXPORT=data/forward-groups-spec.json (얼린 8개 · 7무리) → forward_groups.py → data/forward-groups-log.jsonl
#  ② gate7 CARDLIVE — rule-capital.json 에 「종가」 칸(매일 종가 평가 낙폭 · 가장 깊은 구간) · 화면이 그 칸을 읽는다
#  밤 0~7시면 밤샘 옛 시험 끝을 기다린다 · 평일 07:20~09:10 피함 · 여유 3GB 밑이면 끈다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b219_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
function 아침인가 {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 440) -and ($m -lt 550))
}
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B219] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*===== 시험 끝 =====" -Quiet -Encoding UTF8
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B219] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    return (-not (((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)))
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [B219] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b219 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B219] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}

적기 "[B219] B218 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b218|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b219 끝 ====="; exit 1 }
$날 = Get-Date -f "yyyy-MM-dd"

# ── ① 예측 기록 ──
밤샘기다리기
if (-not (기다리기 "① 예측 기록 후보" 20)) { 적기 "🛑 ① 12시간 기다려도 모자라다"; 적기 "===== queue_b219 끝 ====="; exit 1 }
Remove-Item "data\forward_groups_cand.jsonl" -ErrorAction SilentlyContinue
$무리들 = @(
    "섹터|조선 본선|||${날}_B219_예측_조선본선.txt", "섹터|휴머노이드/로봇|||${날}_B219_예측_로봇.txt",
    "섹터|해운|||${날}_B219_예측_해운.txt", "규모||700|1000|${날}_B219_예측_소형_700_1000.txt",
    "업종|비금속|||${날}_B219_예측_비금속.txt", "업종|섬유·의류|||${날}_B219_예측_섬유의류.txt",
    "업종|종이·목재|||${날}_B219_예측_종이목재.txt"
)
적기 "[B219] ① 예측 기록 후보 시작 (무리 $($무리들.Count)개 · 얼린 8개) · 여유 $(여유GB)GB"
$env:OWN_GROUPS = ($무리들 -join ';'); $env:OWN_EXPORT = "data\forward-groups-spec.json"; $env:OWN_EXPORT_OUT = "forward_groups_cand.jsonl"
$env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_B219_1_예측후보_묶음.txt"
돌리기 "① 예측 기록 후보" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$빠짐 = @()
foreach ($칸 in $무리들) { $f = Join-Path "data\_labs" ($칸.Split("|")[4]); if (-not ((Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] MULTI 내보내기 .* 끝" -Quiet))) { $빠짐 += $칸.Split("|")[4] } }
if ($빠짐.Count -gt 0) { 적기 "❌ [B219] ① 끝까지 안 간 무리 $($빠짐.Count)개: $($빠짐 -join ', ') — 예측 기록은 있는 것만 적는다" }
$fo = & $py "scripts\forward_groups.py" 2>&1
$fo | ForEach-Object { 적기 "    $_" }

# ── ② 화면 사실 바로잡기 (CARDLIVE · 종가 칸) ──
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — ② 안 함"; 적기 "===== queue_b219 끝 ====="; exit 1 }
밤샘기다리기
# 10/2 독립 검사: CARDLIVE 는 50분 안팎 — 평일 07:05~07:19 에 시작하면 08:00 브리핑 중에 화면 파일을 쓴다 ⇒ 평일 06:00~09:10 엔 시작 안 함
while (([int](Get-Date).DayOfWeek -ge 1) -and ([int](Get-Date).DayOfWeek -le 5) -and ((Get-Date).Hour * 60 + (Get-Date).Minute -ge 360) -and ((Get-Date).Hour * 60 + (Get-Date).Minute -lt 550)) {
    Start-Sleep 60
}
if (-not (기다리기 "② CARDLIVE" 26)) { 적기 "🛑 ② 12시간 기다려도 모자라다"; 적기 "===== queue_b219 끝 ====="; exit 1 }
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 2 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 적기 "❌ 실행 전 검사에서 걸렸다 — ② 안 띄운다"; 적기 "===== queue_b219 끝 ====="; exit 1 }
적기 "[B219] ② CARDLIVE 시작 (화면 낙폭을 매일 종가 평가로) · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "CARDLIVE"
$밖2 = "${날}_B219_2_화면성적표_종가.txt"; $env:LAB_OUT = $밖2
돌리기 "② CARDLIVE" "scripts\gate7_lab.py"
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$f = Join-Path "data\_labs" $밖2
$끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "rule-capital.json 새로 썼다" -Quiet) -and (Select-String -Path $f -Pattern "종가 기준 계좌 낙폭" -Quiet)
$터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)
적기 ("[B219] ② {0}" -f $(if ($끝 -and -not $터) { "끝까지 ✅ — 화면 파일 새로 씀(다음 브리핑부터)" } else { "터짐 ❌ — 화면 파일은 전 것 그대로일 수 있다" }))
if (-not $끝 -or $터) { Set-Content $깃발 "queue_b219 CARDLIVE 터짐 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8 }
적기 "===== queue_b219 끝 ====="
