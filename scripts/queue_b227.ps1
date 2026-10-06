# ==============================================================
#  queue_b227.ps1 — **실전 + 얼린 8개 한 계좌** (2026-10-06)
#  균형 표의 「실전 + 옛 20개」 3.65억 · −43.4% 는 20개 중 12개가 나눔 흔들기에서 무너진 것까지 든 값이다(부풀었을 수 있음)
#  ⇒ 버틴 8개(forward-groups-spec.json · 예측 기록용)만 더하면 어떤지 잰다 · 후보 파일은 B219 가 낸 forward_groups_cand.jsonl
#  사용자: 「"부풀었을 수 있음"이면 더 테스트해봐야하고」 · 「혹시 테스트 결과에서 추가로 테스트가 필요하면 허락없이 진행해.」
#  B225 · B226 뒤 · 약 10분 · 9GB 밑
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b227_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B227] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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

적기 "[B227] B225 · B226 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b225|queue_b226|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b227 끝 ====="; exit 1 }
밤샘기다리기
$ㅁ = 0
while ((((여유GB) -lt 15) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) { if ($ㅁ -eq 0) { 적기 "[B227] 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }; Start-Sleep 60; $ㅁ++ }
$날 = Get-Date -f "yyyy-MM-dd"
적기 "[B227] multi_lab 실전 + 얼린 8 시작 · 여유 $(여유GB)GB"
$env:MULTI_SPEC = "..\forward-groups-spec.json"; $env:MULTI_CAND = "..\forward_groups_cand.jsonl"
$env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"
$밖 = "${날}_B227_실전더하기_얼린8.txt"; $env:LAB_OUT = $밖
$최대 = 0.0
$p = Start-Process -FilePath $py -ArgumentList "scripts\multi_lab.py" -PassThru -WindowStyle Hidden
$null = $p.Handle
while (-not $p.HasExited) {
    Start-Sleep 30
    try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
    if ((여유GB) -lt 3) { 적기 "🛑 [B227] 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b227 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
}
foreach ($k in "MULTI_SPEC", "MULTI_CAND", "MULTI_NODD", "MULTI_HORIZON", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
적기 ("[B227] multi_lab 끝 — 코드 {0} · 최대 메모리 {1:N1}GB" -f $p.ExitCode, $최대)
$f = Join-Path "data\_labs" $밖
$터 = (-not (Test-Path $f)) -or (Select-String -Path $f -Pattern "Traceback|🛑" -Quiet)
적기 ("[B227] {0} — {1}" -f $(if ($터) { "터짐 ❌" } else { "✅" }), $f)
적기 "===== queue_b227 끝 ====="
