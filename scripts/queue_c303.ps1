# ==============================================================
#  queue_c303.ps1 — **100~300억 규칙을 지금 규칙과 한 계좌로 합치면 돈이 느나** (2026-10-09 · multi_lab ⑯ 보호 포함)
#  C302: 3/3 버틴 3개(외인1↑ · 낙폭둔화↑ · 60일선대비↓) · 2/2(2017 못 만듦) 4개 · 2/3 2개 — 3개만 / 9개 전부 두 가지로
#  실전 후보를 지금 자료로 다시 낸다(끝 날 10/7 맞추기 · 9.5GB) → 합치기 두 번(5~11GB) · 하나씩
#  ⚠️ 낙폭은 종가 기준 · 300억 아래는 상장폐지 17.7%·거래대금 작음 — 결과와 같이 적는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_c303_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_c303 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[C303] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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
        if ($ㅁ -eq 0) { 적기 "[C303] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [C303] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_c303 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[C303] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
# ⚠️ 10/7 독립 검사: 처음 만들 때 이 함수를 빠뜨렸다 — 없는 함수를 if 안에서 부르면 if 전체가 조용히 건너뛰어진다
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }   # 10/8: 🛑 는 「이 해엔 조건이 없어 못 만든다」 안내 줄이기도 하다(정상) — 터짐으로 세지 않는다
function 깃발보기($어디) { if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발($어디): $(Get-Content $깃발 -Raw -Encoding UTF8)" } }
function 실전후보다시 {
    깃발보기 "실전 후보 앞"
    밤샘기다리기
    if (-not (기다리기 "실전 후보 다시" 26)) { 그만 "🛑 실전 후보 12시간 기다려도 모자라다" }
    적기 "[C303] 실전 후보 (MULTIDUMP · 지금 자료까지) · 여유 $(여유GB)GB"
    $env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
    $env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
    $밖1 = "${날}_C303_실전후보_$(Get-Date -f HHmm).txt"; $env:LAB_OUT = $밖1
    돌리기 "실전 후보" "scripts\gate7_lab.py"
    foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ 실전 후보가 끝까지 안 갔다" }
}
function 점검($종류) {
    $o = & $py "scripts\preflight_check.py" --종류 $종류 2>&1
    $o | ForEach-Object { 적기 "    [점검] $_" } | Out-Null   # 10/8: 적기 가 줄을 돌려줘서 함수 값이 배열이 되어 「못 넘음」 이 「넘음」 으로 읽혔다
    return ($LASTEXITCODE -eq 0)
}
적기 "[C303] C302 가 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_c302.ps1' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
깃발보기 "시작 앞"
$날 = Get-Date -f "yyyy-MM-dd"
# 10/8 사용자 「합치는건 지금 규칙이 못 보는 매수 기회를 보기 위해서니까 2번은 목적에 맞는데 수익율이 줄어들거나 낙폭이 커지는 1,3번은 맞지 않은 거잖아?」
#   → 세 묶음을 「보호」(실전 먼저 · 빈날 · 몫30/50) 와 함께 합친다 (multi_lab ⑯ MULTI_PROTECT)
function 합치기($이름, $스펙, $후보, $나눔, $꼬리) {
    깃발보기 "$이름 앞"
    $env:MULTI_SPEC = $스펙; $env:MULTI_CAND = $후보; $env:MULTI_SPLIT = $나눔
    if (-not (점검 "multi")) { 적기 "⚠️ [C303] $이름 — 점검 못 넘음(끝 날·나눔) · 건너뜀"; foreach ($k in "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }; return }
    if (-not (기다리기 $이름 12)) { 그만 "🛑 12시간 기다려도 모자라다" }
    적기 "[C303] $이름 한 계좌 + 보호 시작"
    $밖 = "${날}_C303_${꼬리}.txt"; $env:LAB_OUT = $밖
    $env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"; $env:MULTI_PROTECT = "1"
    돌리기 $이름 "scripts\multi_lab.py"
    foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST", "MULTI_PROTECT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] 보호 끝") { 적기 "[C303] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [C303] $이름 끝까지 안 갔다" }
}
실전후보다시
합치기 "100~300억 3개(3/3)" "spec_c301_33.json" "c301_split2019.jsonl" "2019" "초소형3_합치기"
합치기 "100~300억 9개 전부" "spec_c301.json" "c301_split2019.jsonl" "2019" "초소형9_합치기"
적기 "===== queue_c303 끝 ====="
