# ==============================================================
#  queue_b232.ps1 — **고점 거름(−20·−25·−30·−35%) 다시 · 매일 종가 낙폭** (2026-10-06) · 균형 표가 종가 낙폭이라 같은 기준으로 (10/1 B210 은 산 값 낙폭) · B229·B230 뒤 · B231 앞
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b232_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B232] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*(===== 시험 끝 =====|시험을 건너뛴다)" -Quiet -Encoding UTF8
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 브리핑시간인가 {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 360) -and ($m -lt 550))
}

적기 "[B232] B229 · B230 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b229|queue_b230|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b232 끝 ====="; exit 1 }
밤샘기다리기
while (브리핑시간인가) { Start-Sleep 60 }
$ㅁ = 0
while ((((여유GB) -lt 26) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) { if ($ㅁ -eq 0) { 적기 "[B232] 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }; Start-Sleep 60; $ㅁ++ }
while (브리핑시간인가) { Start-Sleep 60 }
$날 = Get-Date -f "yyyy-MM-dd"
적기 "[B232] PEAKCUT 시작 (고점 거름 · 매일 종가 낙폭) · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "PEAKCUT"; $env:PEAK_CLOSE = "1"
$밖 = "${날}_B232_고점거름_종가.txt"; $env:LAB_OUT = $밖
$최대 = 0.0
$p = Start-Process -FilePath $py -ArgumentList "scripts\gate7_lab.py" -PassThru -WindowStyle Hidden
$null = $p.Handle
while (-not $p.HasExited) {
    Start-Sleep 30
    try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
    if ((여유GB) -lt 3) { 적기 "🛑 [B232] 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b232 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
}
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT", "PEAK_CLOSE") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
적기 ("[B232] PEAKCUT 끝 — 코드 {0} · 최대 메모리 {1:N1}GB" -f $p.ExitCode, $최대)
$f = Join-Path "data\_labs" $밖
$끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] PEAKCUT 끝" -Quiet)
$터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)
적기 ("[B232] {0} — {1}" -f $(if ($끝 -and -not $터) { "끝까지 ✅" } else { "터짐 ❌" }), $f)
적기 "===== queue_b232 끝 ====="
