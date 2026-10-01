# ==============================================================
#  queue_b205.ps1 — **지금 실전 규칙 다시 재기 (REVERIFY)** (2026-10-01)
#  사용자: 「혹시 기존 규칙도 재검증할 필요 있을까?」 → 「오케이 너 말대로 진행해」
#  gate7 REVERIFY 절 — 또 사기 금지 · 현금만 · 아무 날 · 비용/비중/나누는 해 · 원전
#  환경은 CARDLIVE(B154) 와 같게 — rule_def 와 같은 값(상대갭 -3.5 · 후보 120 · 나눔 40:60)
#  메모리 26GB 관문(판 하나 약 24GB · 커밋 한도 47.9GB) · 07:20~09:10 피함 · 화면 파일은 안 건드린다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b205_$(Get-Date -f yyyyMMdd_HHmmss).log"
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
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 안 돈다"; 적기 "===== queue_b205 끝 ====="; exit 1 }
$ㅁ = 0
while (((아침인가) -or ((여유GB) -lt 26) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
    if ($ㅁ -eq 0) { 적기 "[B205] 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
    Start-Sleep 60; $ㅁ++
}
if (((여유GB) -lt 26) -or ((큰파이썬) -gt 0)) { 적기 "🛑 [B205] 12시간 기다려도 모자라다 — 안 돈다"; 적기 "===== queue_b205 끝 ====="; exit 1 }
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 2 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 적기 "❌ 실행 전 검사에서 걸렸다 — 안 띄운다"; 적기 "===== queue_b205 끝 ====="; exit 1 }
적기 "[B205] REVERIFY 시작 · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "REVERIFY"
$밖 = "2026-10-01_B205_실전규칙_다시재기.txt"; $env:LAB_OUT = $밖
$최대 = 0.0
$p = Start-Process -FilePath $py -ArgumentList "scripts\gate7_lab.py" -PassThru -WindowStyle Hidden
while (-not $p.HasExited) {
    Start-Sleep 30
    try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
    if ((여유GB) -lt 3) { 적기 "🛑 [B205] 여유 $(여유GB)GB — 이 판을 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b205 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
}
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$f = Join-Path "data\_labs" $밖
$끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] REVERIFY 끝" -Quiet)
$터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)
적기 ("[B205] 끝 — 코드 {0} · 최대 메모리 {1:N1}GB · {2}" -f $p.ExitCode, $최대, $(if ($끝 -and -not $터) { "끝까지 ✅" } else { "터짐 ❌" }))
if (-not $끝 -or $터) { Set-Content $깃발 "queue_b205 터짐 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8 }
적기 "===== queue_b205 끝 ====="
