# ==============================================================
#  queue_b234.ps1 — **실전 + 시장 전체 규칙 4개(B229 흔들기 3/3) 한 계좌** (2026-10-06 밤) · 후보 = 나눔 2023 내보내기(⚠️ 10/7 바로잡기: 규칙은 2019~2023 으로 고르고 2024~ 로 통과시켰다 — 2023~ 도 전부 본 기간 · 진짜 검증은 예측 기록뿐) · B233 뒤 · B231 앞
#  사용자 「추가로 확인이 필요한 테스트가 발생하면 허락없이 진행해. 추가 테스트도」
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b234_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B234] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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

적기 "[B234] B233 이 끝나길 기다린다 (실전 후보가 10/2 까지 새로 나와야 끝 날이 맞는다)"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b234 끝 ====="; exit 1 }
밤샘기다리기
$ㅁ = 0
while ((((여유GB) -lt 15) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) { if ($ㅁ -eq 0) { 적기 "[B234] 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }; Start-Sleep 60; $ㅁ++ }
$날 = Get-Date -f "yyyy-MM-dd"
적기 "[B234] multi_lab 실전 + 시장 전체 4 시작 · 여유 $(여유GB)GB"
$env:MULTI_SPEC = "spec_b221_2019all_4.json"; $env:MULTI_CAND = "b221all_split2023.jsonl"
$env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_SPLIT = "2023"
$밖 = "${날}_B234_실전더하기_시장전체4_나눔2023.txt"; $env:LAB_OUT = $밖
$최대 = 0.0
$p = Start-Process -FilePath $py -ArgumentList "scripts\multi_lab.py" -PassThru -WindowStyle Hidden
$null = $p.Handle
while (-not $p.HasExited) {
    Start-Sleep 30
    try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
    if ((여유GB) -lt 3) { 적기 "🛑 [B234] 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b234 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
}
foreach ($k in "MULTI_SPEC", "MULTI_CAND", "MULTI_NODD", "MULTI_HORIZON", "MULTI_SPLIT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
적기 ("[B234] multi_lab 끝 — 코드 {0} · 최대 메모리 {1:N1}GB" -f $p.ExitCode, $최대)
$f = Join-Path "data\_labs" $밖
$터 = (-not (Test-Path $f)) -or (Select-String -Path $f -Pattern "Traceback|🛑" -Quiet)
적기 ("[B234] {0} — {1}" -f $(if ($터) { "터짐 ❌" } else { "✅" }), $f)
적기 "===== queue_b234 끝 ====="
