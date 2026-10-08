# ==============================================================
#  queue_b243.ps1 — **C(전체 시장 규칙 4개) 예측 기록 첫 판** (2026-10-08 · 3연휴용)
#  사용자 10/7 「C는 예측 기록을 본 뒤 판단」 · 「3,4는 너 권고대로」(주 1회) · 10/8 「일요일까지 필요한 테스트를 짜던가」
#  얼린 규칙 data/forward-market-spec.json(M01~M04 · 10/8 12:07) → 후보 내보내기(OWN_ALL · 24GB 판) → forward_groups → forward-market-log.jsonl
#  B240~B242 뒤 · 여유 32GB↑ 에서만 · 판은 하나씩
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b243_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_b243 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B243] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*(===== 시험 끝 =====|시험을 건너뛴다)" -Quiet -Encoding UTF8   # 10/4: 새 자료가 없으면 시험을 건너뛰고 「시험 끝」 을 안 찍는다
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 아침인가 {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 440) -and ($m -lt 550))
}
function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B243] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B243] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b243 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B243] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
# ⚠️ 10/7 독립 검사: 처음 만들 때 이 함수를 빠뜨렸다 — 없는 함수를 if 안에서 부르면 if 전체가 조용히 건너뛰어진다
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }   # 10/8: 🛑 는 「이 해엔 조건이 없어 못 만든다」 안내 줄이기도 하다(정상) — 터짐으로 세지 않는다
function 깃발보기($어디) { if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발($어디): $(Get-Content $깃발 -Raw -Encoding UTF8)" } }
function 실전후보다시 {
    깃발보기 "실전 후보 앞"
    밤샘기다리기
    if (-not (기다리기 "실전 후보 다시" 26)) { 그만 "🛑 실전 후보 12시간 기다려도 모자라다" }
    적기 "[B243] 실전 후보 (MULTIDUMP · 지금 자료까지) · 여유 $(여유GB)GB"
    $env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
    $env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
    $밖1 = "${날}_B243_실전후보_$(Get-Date -f HHmm).txt"; $env:LAB_OUT = $밖1
    돌리기 "실전 후보" "scripts\gate7_lab.py"
    foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ 실전 후보가 끝까지 안 갔다" }
}
function 점검($종류) {
    $o = & $py "scripts\preflight_check.py" --종류 $종류 2>&1
    $o | ForEach-Object { 적기 "    [점검] $_" }
    return ($LASTEXITCODE -eq 0)
}
적기 "[B243] B240·B241·B242 가 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b240|queue_b241|queue_b242' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
깃발보기 "시작 앞"
$날 = Get-Date -f "yyyy-MM-dd"
밤샘기다리기
if (-not (기다리기 "C 예측 기록" 32)) { 그만 "🛑 12시간 기다려도 여유 32GB 가 안 된다" }
적기 "[B243] C(전체 시장 4개) 예측 기록 — 후보 내보내기 시작 (OWN_ALL · 2020~ · 나눔 2024) · 여유 $(여유GB)GB"
Remove-Item "data\forward_market_cand.jsonl" -ErrorAction SilentlyContinue
$env:OWN_ALL = "1"; $env:OWN_START = "20200102"; $env:OWN_SPLIT = "20240101"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"
$env:OWN_EXPORT = "data\forward-market-spec.json"; $env:OWN_EXPORT_OUT = "forward_market_cand.jsonl"
$밖 = "${날}_B243_C예측기록_후보.txt"; $env:LAB_OUT = $밖
돌리기 "C 후보 내보내기" "scripts\own_lab.py"
foreach ($k in "OWN_ALL", "OWN_START", "OWN_SPLIT", "MAXDD", "OWN_CUT", "OWN_EXPORT", "OWN_EXPORT_OUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (-not (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] MULTI 내보내기 .* 끝")) { 그만 "❌ C 후보 내보내기가 끝까지 안 갔다" }
$env:FG_SPEC = "forward-market-spec.json"; $env:FG_CAND = "forward_market_cand.jsonl"; $env:FG_LOG = "forward-market-log.jsonl"
$o = & $py "scripts\forward_groups.py" 2>&1
foreach ($k in "FG_SPEC", "FG_CAND", "FG_LOG") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$o | Select-Object -Last 4 | ForEach-Object { 적기 "    [C] $_" }
적기 "[B243] ✅ C 예측 기록 첫 판 — data\forward-market-log.jsonl (얼린 날 뒤 매수만 · 첫 판은 0줄이 정상)"
적기 "===== queue_b243 끝 ====="
