# ==============================================================
#  queue_b213.ps1 — **종가 기준 계좌 낙폭을 무엇이 줄이나 (DDCTRL)** (2026-10-01) · B212 대기열이 끝난 뒤
#  B211: 종가 기준 −38.9%(2020-03) · 2021~ −28.3%(2022) — 손잡이 하나씩(손절·하루 종목 수·시장 거름·또 사기)
#  사용자 10/1: 「혹시 테스트 결과에서 추가로 테스트가 필요하면 허락없이 진행해.」 · 화면 파일 안 건드림
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b213_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    if (-not ((($h -eq 7) -and ($m -ge 20)) -or ($h -eq 8) -or (($h -eq 9) -and ($m -lt 10)))) { return $false }
    & $py "scripts\krx_calendar.py" *> $null
    return ($LASTEXITCODE -eq 0)
}
$깃발 = "data\_labs\_STOP.txt"
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 안 돈다"; 적기 "===== queue_b213 끝 ====="; exit 1 }
# ⚠️ B212 는 세 단계 사이에 큰 파이썬이 없는 틈이 있다 — 그 틈에 끼어들지 않게 **B212 대기열 자체**가 끝나길 기다린다
$ㄱ = 0
while ((@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b212' }).Count -gt 0) -and ($ㄱ -lt 1440)) {
    if ($ㄱ -eq 0) { 적기 "[B213] B212 대기열이 아직 돈다 — 기다린다" }
    Start-Sleep 60; $ㄱ++
}
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 안 돈다"; 적기 "===== queue_b213 끝 ====="; exit 1 }
$ㅁ = 0
while (((아침인가) -or ((여유GB) -lt 26) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
    if ($ㅁ -eq 0) { 적기 "[B213] 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
    Start-Sleep 60; $ㅁ++
}
if (((여유GB) -lt 26) -or ((큰파이썬) -gt 0)) { 적기 "🛑 [B213] 12시간 기다려도 모자라다 — 안 돈다"; 적기 "===== queue_b213 끝 ====="; exit 1 }
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 2 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 적기 "❌ 실행 전 검사에서 걸렸다 — 안 띄운다"; 적기 "===== queue_b213 끝 ====="; exit 1 }
적기 "[B213] DDCTRL 시작 (종가 기준 낙폭을 무엇이 줄이나) · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "DDCTRL"
$밖 = "2026-10-01_B213_낙폭줄이기.txt"; $env:LAB_OUT = $밖
$최대 = 0.0
$p = Start-Process -FilePath $py -ArgumentList "scripts\gate7_lab.py" -PassThru -WindowStyle Hidden
while (-not $p.HasExited) {
    Start-Sleep 30
    try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
    if ((여유GB) -lt 3) { 적기 "🛑 [B213] 여유 $(여유GB)GB — 이 판을 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b213 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
}
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$f = Join-Path "data\_labs" $밖
$끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] DDCTRL 끝" -Quiet)
$터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)
적기 ("[B213] 끝 — 코드 {0} · 최대 메모리 {1:N1}GB · {2}" -f $p.ExitCode, $최대, $(if ($끝 -and -not $터) { "끝까지 ✅" } else { "터짐 ❌" }))
if (-not $끝 -or $터) { Set-Content $깃발 "queue_b213 터짐 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8 }
적기 "===== queue_b213 끝 ====="
