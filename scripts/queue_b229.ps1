# ==============================================================
#  queue_b229.ps1 — **B225 다시** (10/6 11:32 나눔 2022 가 여유 2.2GB 로 꺼짐 · 시작 때 여유 27.7GB 뿐이었다 — 10/4 같은 판은 35GB 에서 24.4GB 쓰고 끝) · 여유 32GB↑ 에서만 시작 · 맨 뒤(밤)
#  B221 ② 뒤 2024~ 에서 [수익률120↓] 아무 날의 2.3배 · [자사주직후10↑] 1.24배 · [신저가반등↑] 1.15배 — 하지만 체 없이 고른 1등들
#  ⇒ 나누는 해를 2022 · 2023 · 2025 로 바꿔(설정 고정 · 오분위 문턱만 새 앞 기간 값) 버티는지 본다 (원래 2024 는 B221 ② 결과)
#  사용자: 「혹시 테스트 결과에서 추가로 테스트가 필요하면 허락없이 진행해.」
#  B223 · B224 · queue_own 이 끝난 뒤에 돈다 (판은 하나씩) · 한 판 약 85분(불러오기) · 최대 메모리 B221 ② 24.4GB 보다 작을 것(찾기 안 함)
#  밤 0~7시면 밤샘 옛 시험 끝을 기다린다 · 평일 07:20~09:10 피함 · 여유 3GB 밑이면 끈다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b229_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
function 아침인가 {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 440) -and ($m -lt 550))
}
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B229] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*(===== 시험 끝 =====|시험을 건너뛴다)" -Quiet -Encoding UTF8
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B229] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B229] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b229 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B229] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}

적기 "[B229] B226~B228 · B230 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b226|queue_b227|queue_b228|queue_b230|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
$날 = Get-Date -f "yyyy-MM-dd"
$해들 = @("2022", "2023", "2025")
foreach ($해 in $해들) {
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b229 끝 ====="; exit 1 }
    밤샘기다리기
    if (-not (기다리기 "나눔 $해" 32)) { 적기 "🛑 나눔 $해 12시간 기다려도 모자라다"; 적기 "===== queue_b229 끝 ====="; exit 1 }
    Remove-Item "data\_labs\b221all_split$해.jsonl" -ErrorAction SilentlyContinue
    적기 "[B229] 나눔 $해 시작 (시장 전체 · 2020~ · 규칙 5개 내보내기) · 여유 $(여유GB)GB"
    $env:OWN_ALL = "1"; $env:OWN_START = "20200102"; $env:OWN_SPLIT = "${해}0101"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"
    $env:OWN_EXPORT = "data\_labs\spec_b221_2019all.json"; $env:OWN_EXPORT_OUT = "b221all_split$해.jsonl"
    $env:LAB_OUT = "${날}_B229_흔들기_나눔$해.txt"
    돌리기 "나눔 $해" "scripts\own_lab.py"
    foreach ($k in "OWN_ALL", "OWN_START", "OWN_SPLIT", "MAXDD", "OWN_CUT", "OWN_EXPORT", "OWN_EXPORT_OUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $f = Join-Path "data\_labs" "${날}_B229_흔들기_나눔$해.txt"
    if (-not ((Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] MULTI 내보내기 .* 끝" -Quiet))) { 적기 "❌ [B229] 나눔 $해 끝까지 안 감 — $f" }
}
$env:SHAKE_SPEC = "spec_b221_2019all.json"; $env:SHAKE_YEARS = ($해들 -join ","); $env:SHAKE_PRE = "b221all_split"; $env:SHAKE_DD = "-999"
$env:LAB_OUT = "${날}_B229_흔들기_판정.txt"
$so = & $py "scripts\split_shake.py" 2>&1
$so | Select-Object -Last 12 | ForEach-Object { 적기 "    $_" }
foreach ($k in "SHAKE_SPEC", "SHAKE_YEARS", "SHAKE_PRE", "SHAKE_DD", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
적기 "[B229] ✅ 판정 — data\_labs\${날}_B229_흔들기_판정.txt"
적기 "===== queue_b229 끝 ====="
