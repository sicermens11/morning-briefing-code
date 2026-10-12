# ==============================================================
#  night_cf251.ps1 — **B251 현금흐름 재료 5개 겹침 검사 → 규칙 찾기** (2026-10-12 · 밤 · 현금흐름 2015~2024 다 받은 뒤)
#  ⚠️ 이름에 queue_ 를 안 쓴다 — 예측 기록(forward_daily)의 C 가 queue_* 가 있으면 안 돌고, 이건 C 뒤(mix_night) 를 기다리므로 서로 기다리게 된다
#  기다림: 현금흐름 해 파일 10개 + mix_night 끝 + 큰 파이썬 0 · 06:00 넘으면 그만 · 규칙 찾기는 05:30 전에 시작할 때만
#  무리 300~2,000억 · OWN_NEWCF · 겹침 0.7↑ 은 뺀다(사용자 10/8)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\night_cf251_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== night_cf251 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[CF251] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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
        if ($ㅁ -eq 0) { 적기 "[CF251] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [CF251] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "night_cf251 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[CF251] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
# ⚠️ 10/7 독립 검사: 처음 만들 때 이 함수를 빠뜨렸다 — 없는 함수를 if 안에서 부르면 if 전체가 조용히 건너뛰어진다
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }   # 10/8: 🛑 는 「이 해엔 조건이 없어 못 만든다」 안내 줄이기도 하다(정상) — 터짐으로 세지 않는다
function 깃발보기($어디) { if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발($어디): $(Get-Content $깃발 -Raw -Encoding UTF8)" } }
function 실전후보다시 {
    깃발보기 "실전 후보 앞"
    밤샘기다리기
    if (-not (기다리기 "실전 후보 다시" 15)) { 그만 "🛑 실전 후보 12시간 기다려도 모자라다" }
    적기 "[CF251] 실전 후보 (MULTIDUMP · 지금 자료까지) · 여유 $(여유GB)GB"
    $env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
    $env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
    $밖1 = "${날}_CF251_실전후보_$(Get-Date -f HHmm).txt"; $env:LAB_OUT = $밖1
    돌리기 "실전 후보" "scripts\gate7_lab.py"
    foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ 실전 후보가 끝까지 안 갔다" }
}
function 점검($종류) {
    $o = & $py "scripts\preflight_check.py" --종류 $종류 2>&1
    $o | ForEach-Object { 적기 "    [점검] $_" } | Out-Null   # 10/8: 적기 가 줄을 돌려줘서 함수 값이 배열이 되어 「못 넘음」 이 「넘음」 으로 읽혔다
    return ($LASTEXITCODE -eq 0)
}
function 합치기($이름, $스펙, $후보, $나눔, $꼬리) {
    깃발보기 "$이름 앞"
    $env:MULTI_SPEC = $스펙; $env:MULTI_CAND = $후보; $env:MULTI_SPLIT = $나눔
    if (-not (점검 "multi")) { 적기 "⚠️ [CF251] $이름 — 점검 못 넘음(끝 날·나눔) · 건너뜀"; foreach ($k in "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }; return }
    if (-not (기다리기 $이름 12)) { 그만 "🛑 12시간 기다려도 모자라다" }
    적기 "[CF251] $이름 한 계좌 + 보호 시작"
    $밖 = "${날}_CF251_${꼬리}.txt"; $env:LAB_OUT = $밖
    $env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"; $env:MULTI_PROTECT = "1"
    돌리기 $이름 "scripts\multi_lab.py"
    foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST", "MULTI_PROTECT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] 보호 끝") { 적기 "[CF251] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [CF251] $이름 끝까지 안 갔다" }
}
적기 "[CF251] 현금흐름 10해 · mix_night 끝을 기다린다"
$한계 = (Get-Date).Date.AddDays(1).AddHours(6)
while ((Get-Date) -lt $한계) {
    $해수 = @(Get-ChildItem "data\dart-cf\[0-9][0-9][0-9][0-9].json" -ErrorAction SilentlyContinue).Count
    $믹스 = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'mix_night\.ps1|cf_night\.ps1' }).Count
    if ($해수 -ge 10 -and $믹스 -eq 0 -and (큰파이썬) -eq 0) { break }
    Start-Sleep 60
}
if ((Get-Date) -ge $한계) { 그만 "🛑 06:00 까지 현금흐름 10해·mix_night 가 안 끝났다 — 그만둔다(내일 다시 건다)" }
$날 = Get-Date -f "yyyy-MM-dd"
$밖C = "${날}_CF251_현금재료_겹침.txt"
적기 "[CF251] 겹침 검사 시작 · 여유 $(여유GB)GB"
$env:OWN_GROUPS = "규모||300|2000|$밖C"; $env:OWN_NEWCF = "1"; $env:OWN_CORR = "1"; $env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_CF251_묶음.txt"
돌리기 "현금 재료 겹침" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_NEWCF", "OWN_CORR", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$뺄 = @()
foreach ($m in (Select-String -Path (Join-Path "data\_labs" $밖C) -Pattern "^\s+(\S+)\s+값 .*❌ 뺀다" -Encoding UTF8 -ErrorAction SilentlyContinue)) { $뺄 += $m.Matches[0].Groups[1].Value }
적기 "[CF251] 겹침 끝 — 빼는 재료 $($뺄.Count)개: $($뺄 -join ', ')"
if ((Get-Date).Hour -ge 5 -and (Get-Date).Minute -ge 30 -or (Get-Date).Hour -ge 6) { 그만 "⚠️ 05:30 넘었다 — 규칙 찾기는 다음에(아침 08:02 와 안 겹치게)" }
$밖S = "${날}_CF251_규모300_2000.txt"
적기 "[CF251] 규칙 찾기 시작(300~2,000억 · 현금 재료 + 기존) · 여유 $(여유GB)GB"
$env:OWN_GROUPS = "규모||300|2000|$밖S"; $env:OWN_NEWCF = "1"; $env:OWN_NEW_DROP = ($뺄 -join ","); $env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_CF251_묶음2.txt"
돌리기 "현금 재료 규칙 찾기" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_NEWCF", "OWN_NEW_DROP", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (끝났나 (Join-Path "data\_labs" $밖S) "\[대조\] 무리 규모") { 적기 "[CF251] ✅ — data\_labs\$밖S" } else { 적기 "❌ [CF251] 끝까지 안 갔다 — data\_labs\$밖S" }
적기 "===== night_cf251 끝 ====="
