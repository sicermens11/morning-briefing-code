# ==============================================================
#  queue_b221.ps1 — **연휴 빈 시간 채우기** (2026-10-02) · B220 뒤 · 화 07:15 까지 (장 서는 날 아침이면 끈다)
#  사용자: 「그럼 금 저녁~화 새벽까지 테스트 진행되도록 다 테스트 걸려있는거지?」 — 계산하니 월 새벽~화 아침이 빈다
#  ① 큰 종목 30 종목별 규칙 (data/big30.json · 「종목」 무리 30개 묶음 · 낙폭 체 없이) — 계획표 6
#  ② 2019년 이후 재료로 시장 전체 (OWN_ALL · 2020~2023 찾기 / 2024~ 확인 · 낙폭 체 없이) — 계획표 4
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b221_$(Get-Date -f yyyyMMdd_HHmmss).log"
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
    적기 "[B221] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*===== 시험 끝 =====" -Quiet -Encoding UTF8
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((장날아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B221] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B221] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b221 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; $껐다 = $true; break }
        if (장날아침인가) { 적기 "⏹ [B221] $이름 — 장 서는 날 07:15, 브리핑과 안 겹치게 **끈다** (결과는 거기까지)"; try { Stop-Process -Id $p.Id -Force } catch { }; $껐다 = $true; break }
    }
    적기 ("[B221] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB{3}" -f $이름, $p.ExitCode, $최대, $(if ($껐다) { " · 껐음" } else { "" }))
    return $껐다
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback" -Quiet)) }

적기 "[B221] B220 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b218|queue_b219|queue_b220|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b221 끝 ====="; exit 1 }
$날 = Get-Date -f "yyyy-MM-dd"

# ── ① 큰 종목 30 ──
밤샘기다리기
if ((-not (장날아침인가)) -and (기다리기 "① 큰 종목 30" 20)) {
    $목 = (Get-Content "data\big30.json" -Raw -Encoding UTF8 | ConvertFrom-Json).종목
    $칸들 = @(); $k = 0
    foreach ($z in $목) { $k++; $칸들 += "종목|$($z.code)|||${날}_B221_종목_$('{0:D2}' -f $k)_$($z.code).txt" }
    적기 "[B221] ① 큰 종목 30 시작 ($($칸들.Count)무리 한 프로세스) · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = ($칸들 -join ';'); $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_B221_큰종목30_묶음.txt"
    $null = 돌리기 "① 큰 종목 30" "scripts\own_lab.py"
    foreach ($k2 in "OWN_GROUPS", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k2" -ErrorAction SilentlyContinue }
    $끝수 = @($칸들 | Where-Object { 끝났나 (Join-Path "data\_labs" ($_.Split("|")[4])) "\[대조\] 무리" }).Count
    적기 "[B221] ① 끝까지 간 종목 $끝수 / $($칸들.Count)"
} else { 적기 "⏹ [B221] ① 못 띄움(아침이거나 메모리)" }

# ── ② 2019년 이후 재료 · 시장 전체 ──
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — ② 안 함"; 적기 "===== queue_b221 끝 ====="; exit 1 }
밤샘기다리기
if ((-not (장날아침인가)) -and (기다리기 "② 2019 재료 시장 전체" 30)) {
    $밖2 = "${날}_B221_2019재료_시장전체_낙폭체없음.txt"
    적기 "[B221] ② 2019년 이후 재료 시장 전체 (2020~2023 찾기 · 2024~ 확인) 시작 · 여유 $(여유GB)GB"
    $env:OWN_ALL = "1"; $env:OWN_START = "20200102"; $env:OWN_SPLIT = "20240101"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = $밖2
    $껐 = 돌리기 "② 2019 재료 시장 전체" "scripts\own_lab.py"
    foreach ($k2 in "OWN_ALL", "OWN_START", "OWN_SPLIT", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k2" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖2) "\[대조\] 무리") { 적기 "[B221] ② ✅ — data\_labs\$밖2" } elseif ($껐) { 적기 "⏹ [B221] ② 아침에 껐다 — 결과는 거기까지" } else { 적기 "❌ [B221] ② 끝까지 안 갔다" }
} else { 적기 "⏹ [B221] ② 못 띄움(아침이거나 메모리)" }
적기 "===== queue_b221 끝 ====="
