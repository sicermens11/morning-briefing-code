# ==============================================================
#  queue_b233.ps1 — **B230 ③ 다시** (2026-10-06 밤) · 19:40 multi_lab 이 「자료 끝 날이 다르다」 로 멈춤
#  원인: 실전 후보(multi_cand_live.jsonl · 10/4 B222 ③)는 10/1 까지 · B230 후보 40 은 10/2 까지 → 섞지 않게 막은 것
#  ① gate7 MULTIDUMP 로 실전 후보를 오늘 자료(10/2)까지 다시 ② multi_lab (후보 40 · 같은 설정)
#  사용자 「추가로 확인이 필요한 테스트가 발생하면 허락없이 진행해. 추가 테스트도」 · B229 · B232 뒤 · B231 앞
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b233_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_b233 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B233] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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
        if ($ㅁ -eq 0) { 적기 "[B233] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B233] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b233 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B233] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback" -Quiet)) }
적기 "[B233] B229 · B232 가 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b229|queue_b232|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다" }
$날 = Get-Date -f "yyyy-MM-dd"
밤샘기다리기
if (-not (기다리기 "① MULTIDUMP" 26)) { 그만 "🛑 ① 12시간 기다려도 모자라다" }
적기 "[B233] ① MULTIDUMP 시작 (실전 후보 · 오늘 자료까지) · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
$밖1 = "${날}_B233_1_실전후보.txt"; $env:LAB_OUT = $밖1
돌리기 "① MULTIDUMP" "scripts\gate7_lab.py"
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ ① 실전 후보가 끝까지 안 갔다" }
if (-not (기다리기 "② multi_lab" 12)) { 그만 "🛑 ② 12시간 기다려도 모자라다" }
적기 "[B233] ② multi_lab 시작"
$밖 = "${날}_B233_여러규칙_한계좌_후보40.txt"; $env:LAB_OUT = $밖
$env:MULTI_SPEC = "multi_rules_spec_k40.json"; $env:MULTI_CAND = "multi_cand_own_k40.jsonl"
$env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"
돌리기 "② multi_lab" "scripts\multi_lab.py"
foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] MULTI 끝") { 적기 "[B233] ② 표 ✅ — data\_labs\$밖" } else { 적기 "❌ [B233] ② 합치기가 끝까지 안 갔다" }
적기 "===== queue_b233 끝 ====="
