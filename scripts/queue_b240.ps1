# ==============================================================
#  queue_b240.ps1 — **오르는 걸 사는 규칙(B231 1차 통과) 확인** (2026-10-07)
#  B231 은 손실 한도 없이 찾은 것 — 그대로 후보로 못 쓴다. 두 가지를 확인한다:
#  ① 나눔 2019 무리 후보 내보내기 → ② (끝 날 다르면 실전 후보 다시) → ③ 실전과 한 계좌로(multi_lab)
#  ④ 나누는 해 2017 · 2021 로 다시 내보내 split_shake 로 판정 (기간을 바꿔도 버티나)
#  사용자 「추가로 확인이 필요한 테스트가 발생하면 허락없이 진행해. 추가 테스트도」
#  판은 하나씩 · 07:20~09:10 피함 · 밤엔 밤샘 시험 끝을 기다림 · 여유 3GB 밑이면 끈다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b240_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_b240 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B240] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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
        if ($ㅁ -eq 0) { 적기 "[B240] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B240] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b240 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B240] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
# ⚠️ 10/7 독립 검사: 처음 만들 때 이 함수를 빠뜨렸다 — 없는 함수를 if 안에서 부르면 if 전체가 조용히 건너뛰어진다
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다|🛑" -Quiet)) }
function 깃발보기($어디) { if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발($어디): $(Get-Content $깃발 -Raw -Encoding UTF8)" } }
function 실전후보다시 {
    깃발보기 "실전 후보 앞"
    밤샘기다리기
    if (-not (기다리기 "실전 후보 다시" 26)) { 그만 "🛑 실전 후보 12시간 기다려도 모자라다" }
    적기 "[B240] 실전 후보 (MULTIDUMP · 지금 자료까지) · 여유 $(여유GB)GB"
    $env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
    $env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
    $밖1 = "${날}_B240_실전후보_$(Get-Date -f HHmm).txt"; $env:LAB_OUT = $밖1
    돌리기 "실전 후보" "scripts\gate7_lab.py"
    foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ 실전 후보가 끝까지 안 갔다" }
}
function 점검($종류) {
    $o = & $py "scripts\preflight_check.py" --종류 $종류 2>&1
    $o | ForEach-Object { 적기 "    [점검] $_" }
    return ($LASTEXITCODE -eq 0)
}
적기 "[B240] B231(오르는 걸 사는 규칙 찾기) 가 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b231|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다" }
$날 = Get-Date -f "yyyy-MM-dd"
# ── ⓪ 오늘 예측 기록 먼저 (12:30 예약분이 대기열을 기다리다 내일로 밀리지 않게 · b-thresholds.json 도 여기서 저장) ──
if ((Get-Date).Hour -ge 7) {
    if (기다리기 "예측 기록" 15) {
        적기 "[B240] ⓪ 예측 기록 (판 사이에 끼움)"
        $env:FD_INLINE = "1"
        & powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\forward_daily.ps1" | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
        Remove-Item env:FD_INLINE -ErrorAction SilentlyContinue
        적기 "[B240] ⓪ 예측 기록 끝"
    }
}
# ── ① 통과 규칙 목록 (B231 결과 · 추세 청산 · 낙폭 체 없음) ──
$env:SPEC_GLOB = "2026-10-0*_B*_무리전용_*_자름20_낙폭체없음_추세.txt"; $env:SPEC_OUT = "multi_rules_spec_trend.json"; $env:SPEC_OUTPRE = "${날}_B240_나눔2019_"
$ms = & $py "scripts\make_spec.py" 2>&1
if ($LASTEXITCODE -ne 0) { 적기 "⚠️ [B240] make_spec 끝 코드 $LASTEXITCODE — 결과 파일 일부가 끝까지 안 갔다 (아래 목록은 끝난 것만)" }
foreach ($k in "SPEC_GLOB", "SPEC_OUT", "SPEC_OUTPRE") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$ms | Select-String "파일 .*개 · 통과 규칙" | ForEach-Object { 적기 "    $_" }
$무리줄 = (Get-Content "data\_labs\multi_rules_spec_trend_groups.txt" -Raw -Encoding UTF8).Trim()
if (-not $무리줄) { 그만 "❌ multi_rules_spec_trend_groups.txt 가 비었다" }
$칸들 = $무리줄 -split ';'
# 나누는 해마다 무리 후보를 낸다 — 2019 가 먼저(한 계좌 합치기에 쓴다) · 2017 · 2021 은 기간 바꿔 다시 시험용
function 내보내기($해) {
    $받 = "data\_labs\trend_split$해.jsonl"
    Remove-Item $받 -ErrorAction SilentlyContinue
    밤샘기다리기
    if (-not (기다리기 "나눔 $해 내보내기" 20)) { 그만 "🛑 나눔 $해 12시간 기다려도 모자라다" }
    if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발" }
    $내칸 = $칸들 | ForEach-Object { $z = $_.Split("|"); "{0}|{1}|{2}|{3}|{4}_B240_나눔{5}_{6}" -f $z[0], $z[1], $z[2], $z[3], $날, $해, ($z[4] -replace "^${날}_B240_나눔2019_", "") }
    적기 "[B240] 나눔 $해 내보내기 시작 (무리 $($내칸.Count)개 · 추세 청산) · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = ($내칸 -join ';'); $env:OWN_EXPORT = "data\_labs\multi_rules_spec_trend.json"; $env:OWN_EXPORT_OUT = "trend_split$해.jsonl"
    $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:OWN_TREND = "1"; $env:OWN_SPLIT = "${해}0101"; $env:LAB_OUT = "${날}_B240_나눔${해}_묶음.txt"
    돌리기 "나눔 $해 내보내기" "scripts\own_lab.py"
    foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "OWN_TREND", "OWN_SPLIT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $빠짐 = @()
    foreach ($칸 in $내칸) { $f = Join-Path "data\_labs" ($칸.Split("|")[4]); if (-not (끝났나 $f "\[대조\] MULTI 내보내기 .* 끝")) { $빠짐 += $칸.Split("|")[4] } }
    if ($빠짐.Count -gt 0) {
        if ($해 -eq "2019") { 그만 "❌❌ [B240] 나눔 2019 끝까지 안 간 무리 $($빠짐.Count)개 — 일부만으로 합치지 않는다: $($빠짐 -join ', ')" }
        적기 "❌❌ [B240] 나눔 $해 끝까지 안 간 무리 $($빠짐.Count)개: $($빠짐 -join ', ')"
    }
    if (-not (Test-Path $받)) { 그만 "❌ 나눔 $해 후보 파일이 없다" }
    깃발보기 "나눔 $해 뒤"
}
# ── ② 실전 후보를 먼저 — 무리 후보와 같은 자료(오늘 밤)로 (10/7 독립 검사: 내보내기 뒤로 두면 10/8 08:01 새 종가가 붙어 끝 날이 갈린다) ──
실전후보다시
내보내기 "2019"
$env:MULTI_SPEC = "multi_rules_spec_trend.json"; $env:MULTI_CAND = "trend_split2019.jsonl"; $env:MULTI_SPLIT = "2019"
if (-not (점검 "multi")) {
    적기 "[B240] 끝 날이 다르다 — 실전 후보를 한 번 더"
    실전후보다시
    if (-not (점검 "multi")) { 그만 "🛑 실전 후보를 다시 내도 점검을 못 넘었다" }
}
# ── ③ 실전과 한 계좌로 ──
깃발보기 "합치기 앞"
if (-not (기다리기 "한 계좌 합치기" 12)) { 그만 "🛑 합치기 12시간 기다려도 모자라다" }
적기 "[B240] 한 계좌 합치기 시작"
$밖 = "${날}_B240_오르는규칙_한계좌.txt"; $env:LAB_OUT = $밖
$env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"
돌리기 "한 계좌 합치기" "scripts\multi_lab.py"
foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] MULTI 끝") { 적기 "[B240] 합치기 ✅ — data\_labs\$밖" } else { 적기 "❌ [B240] 합치기가 끝까지 안 갔다 (기간 바꿔 시험은 계속한다)" }
# ── ④ 기간 바꿔 다시 시험 (나누는 해 2017 · 2021) ──
내보내기 "2017"
내보내기 "2021"
$env:SHAKE_SPEC = "multi_rules_spec_trend.json"; $env:SHAKE_YEARS = "2017,2019,2021"; $env:SHAKE_PRE = "trend_split"; $env:SHAKE_DD = "-999"
$env:LAB_OUT = "${날}_B240_기간바꿔_판정.txt"
$so = & $py "scripts\split_shake.py" 2>&1
$so | Select-Object -Last 12 | ForEach-Object { 적기 "    $_" }
foreach ($k in "SHAKE_SPEC", "SHAKE_YEARS", "SHAKE_PRE", "SHAKE_DD", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$f = "data\_labs\${날}_B240_기간바꿔_판정.txt"
if ((Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] SPLIT 흔들기 끝" -Quiet)) { 적기 "[B240] 기간 바꿔 판정 ✅ — $f" } else { 적기 "❌ [B240] 기간 바꿔 판정이 끝까지 안 갔다" }
적기 "===== queue_b240 끝 ====="
