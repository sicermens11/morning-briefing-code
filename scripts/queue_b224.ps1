# ==============================================================
#  queue_b224.ps1 — **후보 200 (OWN_K=40 · 돈 시뮬로 넘기는 조건 70 → 약 200) 을 맨 끝으로** (2026-10-04) · B223 뒤 · 화 07:15 까지
#  10/4 03:50 B220 ③ 시장 전체(새 달력 18)가 24.5GB 까지 써 여유 1.9GB → 안전장치가 껐고 깃발 때문에 ④ 후보 200 이 건너뛰어졌다 → 맨 끝으로
#  사용자 「테스트가 멈추거나 터지면 가만히 있지 말고 감지해서 테스트 이어가」
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b224_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
function 장날아침인가 {
    # 장 서는 날 07:15 이후 ~ 09:10 — 돌고 있는 판을 끄고 새 판을 안 띄운다
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    if (-not (($m -ge 435) -and ($m -lt 550))) { return $false }
    & $py "scripts\krx_calendar.py" *> $null
    return ($LASTEXITCODE -eq 0)
}
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B224] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*(===== 시험 끝 =====|시험을 건너뛴다)" -Quiet -Encoding UTF8   # 10/4: 새 자료가 없으면 시험을 건너뛰고 「시험 끝」 을 안 찍는다
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((장날아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B224] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    return (-not (((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)))
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0; $껐다 = $false
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [B224] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b224 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; $껐다 = $true; break }
        if (장날아침인가) { 적기 "⏹ [B224] $이름 — 장 서는 날 07:15, 브리핑과 안 겹치게 **끈다** (결과는 거기까지)"; try { Stop-Process -Id $p.Id -Force } catch { }; $껐다 = $true; break }
    }
    적기 ("[B224] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB{3}" -f $이름, $p.ExitCode, $최대, $(if ($껐다) { " · 껐음" } else { "" }))
    return $껐다
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback" -Quiet)) }

적기 "[B224] B223 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b219|queue_b220|queue_b221|queue_b222|queue_b223|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b224 끝 ====="; exit 1 }
밤샘기다리기
if (장날아침인가) { 적기 "⏹ [B224] 장 서는 날 아침이라 안 띄운다"; 적기 "===== queue_b224 끝 ====="; exit 0 }
적기 "[B224] 후보 200 (OWN_K=40) · 자름 20 · 낙폭 체 없이 시작"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut 20 -NoDD -K 40 | Out-Null
적기 "[B224] 후보 200 대기열 끝"
적기 "===== queue_b224 끝 ====="
