# ==============================================================
#  queue_b220.ps1 — **연휴 채우기** (2026-10-02) · B219 뒤 · 10/5(월) 대체휴일이라 화 07:15 까지
#  사용자: 「다음주 월요일도 대체휴일로 빨간날이야. 테스트 필요한 거 있으면 채우면 좋을 것 같아. 우리 퀀트 후보를 단단해줄!」
#  ① 2차전지 넓힌 무리 (data/2차전지-universe.json) · ② 로봇 넓힌 무리 (data/로봇-universe.json) — 둘 다 「종목」 무리 · 낙폭 체 없이 · 자름 20
#  ③ 시장 전체(무리 안 나눔) + 새 달력 재료 18 (OWN_ALL · OWN_NEWCAL) — 기준 문서 4번 · 처음 돌림 · 메모리 가장 큼
#  ④ ⑭ 돈 시뮬 후보 70 → 약 200 (OWN_K=40) · 43무리 묶음 · 낙폭 체 없이 · 자름 20
#  장 서는 평일 07:15 에 아직 돌고 있는 판은 **끈다**(브리핑과 안 겹치게) · 밤 0~7시면 밤샘 옛 시험 끝을 기다린다 · 여유 3GB 밑이면 끈다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b220_$(Get-Date -f yyyyMMdd_HHmmss).log"
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
    적기 "[B220] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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
        if ($ㅁ -eq 0) { 적기 "[B220] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B220] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b220 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; $껐다 = $true; break }
        if (장날아침인가) { 적기 "⏹ [B220] $이름 — 장 서는 날 07:15, 브리핑과 안 겹치게 **끈다** (결과는 거기까지)"; try { Stop-Process -Id $p.Id -Force } catch { }; $껐다 = $true; break }
    }
    적기 ("[B220] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB{3}" -f $이름, $p.ExitCode, $최대, $(if ($껐다) { " · 껐음" } else { "" }))
    return $껐다
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback" -Quiet)) }

적기 "[B220] B218·B219 가 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b218|queue_b219|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b220 끝 ====="; exit 1 }
$날 = Get-Date -f "yyyy-MM-dd"

# ── ① ② 넓힌 섹터 둘 ──
foreach ($섹 in @(@("2차전지", "data\2차전지-universe.json"), @("로봇", "data\로봇-universe.json"))) {
    $이름, $파일 = $섹
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — $이름 안 함"; 적기 "===== queue_b220 끝 ====="; exit 1 }
    if (-not (Test-Path $파일)) { 적기 "⚠️ [B220] $파일 이 없다 — $이름 건너뜀"; continue }
    밤샘기다리기
    if (-not (기다리기 "$이름 넓힌 무리" 20)) { 적기 "🛑 [B220] $이름 12시간 기다려도 모자라다 — 건너뜀"; continue }
    $코드 = ((Get-Content $파일 -Raw -Encoding UTF8 | ConvertFrom-Json).종목) -join ','
    $밖 = "${날}_B220_${이름}넓힌무리_낙폭체없음.txt"
    적기 "[B220] $이름 넓힌 무리 시작 ($(($코드 -split ',').Count)종목) · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = "종목|$코드|||$밖"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_B220_${이름}_묶음.txt"
    $null = 돌리기 "$이름 넓힌 무리" "scripts\own_lab.py"
    foreach ($k in "OWN_GROUPS", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] 무리") { 적기 "[B220] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [B220] $이름 이 끝까지 안 갔다" }
}

# ── ③ 시장 전체 · 무리 안 나눔 + 새 달력 재료 18 ──
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — ③ 안 함"; 적기 "===== queue_b220 끝 ====="; exit 1 }
밤샘기다리기
if (기다리기 "③ 시장 전체" 30) {
    $밖3 = "${날}_B220_시장전체_새달력_낙폭체없음.txt"
    적기 "[B220] ③ 시장 전체(무리 안 나눔) + 새 달력 재료 18 시작 · 여유 $(여유GB)GB"
    $env:OWN_ALL = "1"; $env:OWN_NEWCAL = "1"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = $밖3
    $껐 = 돌리기 "③ 시장 전체" "scripts\own_lab.py"
    foreach ($k in "OWN_ALL", "OWN_NEWCAL", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖3) "\[대조\] 무리") { 적기 "[B220] ③ ✅ — data\_labs\$밖3" } elseif ($껐) { 적기 "⏹ [B220] ③ 아침에 껐다 — 결과는 거기까지(다음 연휴·밤에 이어서)" } else { 적기 "❌ [B220] ③ 끝까지 안 갔다" }
} else { 적기 "🛑 [B220] ③ 12시간 기다려도 모자라다 — 건너뜀" }

# ── ④ ⑭ 돈 시뮬 후보 70 → 약 200 (OWN_K=40) · 43무리 ──
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — ④ 안 함"; 적기 "===== queue_b220 끝 ====="; exit 1 }
밤샘기다리기
if (장날아침인가) { 적기 "⏹ [B220] ④ 는 장 서는 날 아침이라 안 띄운다"; 적기 "===== queue_b220 끝 ====="; exit 0 }
적기 "[B220] ④ 후보 200 (OWN_K=40) · 자름 20 · 낙폭 체 없이 시작"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut 20 -NoDD -K 40 | Out-Null
적기 "[B220] ④ 대기열 끝"
적기 "===== queue_b220 끝 ====="
