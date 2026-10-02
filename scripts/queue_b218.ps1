# ==============================================================
#  queue_b218.ps1 — **자름 20(낙폭 체 없이) 끝 → 새 통과 목록으로 표 만들기 → 자름 10 → 자름 30** (2026-10-02)
#  사용자: 「너의 권고대로 하자」 (자름 20 이 끝나면 자름 10 보다 먼저 표 만드는 판을 끼워 넣는다 · B216 껍데기를 껐다)
#  ① 돌고 있는 queue_own(-Cut 20 -NoDD) 이 끝나길 기다린다
#  ② make_spec — 새 통과 목록 → multi_rules_spec.json · multi_groups.txt
#  ③ gate7 MULTIDUMP(실전 후보) → ④ own_lab OWN_EXPORT(무리 후보) → ⑤ multi_lab (돈만 관문 · 500만 N년)
#  ⑥ queue_own -Cut 10 -NoDD → ⑦ -Cut 30 -NoDD
#  판은 하나씩 · 밤 0~7시면 밤샘 옛 시험이 끝나길 기다린다 · 여유 3GB 밑이면 끈다 · 화면 파일 안 건드림
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b218_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; Set-Content $깃발 "queue_b218 $s $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; 적기 "===== queue_b218 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B218] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*===== 시험 끝 =====" -Quiet -Encoding UTF8
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
        if ($ㅁ -eq 0) { 적기 "[B218] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B218] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b218 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B218] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback" -Quiet)) }

# ── ① 자름 20 판이 끝나길 ──
적기 "[B218] ① 자름 20(낙폭 체 없이) 판이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_own' -and $_.CommandLine -match '-Cut 20' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
# 10/2 독립 검사: 묶음은 무리 하나만 터져도 깃발을 세운다 → 주말 내내 아무것도 안 돈다.
#   메모리로 꺼진 깃발이면 멈추고, 무리가 터진 깃발이면 내용을 적고 걷어 낸 뒤 그 무리를 뺀 채 간다
if (Test-Path $깃발) {
    $깃 = (Get-Content $깃발 -Raw -Encoding UTF8)
    적기 "⚠️ [B218] 멈춤 깃발이 서 있다: $깃"
    if ($깃 -match "메모리|여유") { 적기 "🛑 메모리 깃발 — 안 돈다"; 적기 "===== queue_b218 끝 ====="; exit 1 }
    Move-Item $깃발 "data\_labs\_STOP_B218이걷음_$(Get-Date -f yyyyMMdd_HHmm).txt" -Force
    적기 "⚠️ [B218] 무리가 터진 깃발이라 걷어 냈다 — 그 무리 규칙은 빠진 채 간다"
}
적기 "[B218] ① 자름 20 끝 확인"

# ── ② 새 통과 목록 ──
$env:SPEC_GLOB = "2026-10-0*_B*_무리전용_*_자름20_낙폭체없음.txt"; $env:SPEC_OUTPRE = "${날}_B218_내보내기_"
$sp = & $py "scripts\make_spec.py" 2>&1
$rc = $LASTEXITCODE
foreach ($k in "SPEC_GLOB", "SPEC_OUTPRE") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$sp | Select-Object -First 1 | ForEach-Object { 적기 "    $_" }
$sp | Where-Object { "$_" -match "⚠️|🛑|ⓘ" } | ForEach-Object { 적기 "    $_" }
$sp | Select-Object -Last 2 | ForEach-Object { 적기 "    $_" }
if ($rc -eq 2) { 적기 "⚠️ [B218] 끝까지 안 간 무리 파일이 있다 — 그 무리 규칙은 빠진 채 간다" } elseif ($rc -ne 0) { 그만 "❌ ② 통과 목록을 못 만들었다 (코드 $rc)" }
if (-not (Test-Path "data\_labs\multi_groups.txt")) { 그만 "❌ ② multi_groups.txt 가 없다" }
$무리줄 = (Get-Content "data\_labs\multi_groups.txt" -Raw -Encoding UTF8).Trim()
if (-not $무리줄) { 그만 "❌ ② 통과 규칙이 하나도 없다" }

# ── ③ 실전 후보 ──
밤샘기다리기
if (-not (기다리기 "③ MULTIDUMP" 26)) { 그만 "🛑 ③ 12시간 기다려도 모자라다" }
적기 "[B218] ③ MULTIDUMP 시작 · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
$밖3 = "${날}_B218_3_실전후보.txt"; $env:LAB_OUT = $밖3
돌리기 "③ MULTIDUMP" "scripts\gate7_lab.py"
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (-not (끝났나 (Join-Path "data\_labs" $밖3) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ ③ 실전 후보가 끝까지 안 갔다" }

# ── ④ 무리 후보 ──
Remove-Item "data\_labs\multi_cand_own.jsonl" -ErrorAction SilentlyContinue
if (-not (기다리기 "④ OWN_EXPORT" 20)) { 그만 "🛑 ④ 12시간 기다려도 모자라다" }
$칸들 = $무리줄 -split ';'
적기 "[B218] ④ OWN_EXPORT 시작 (무리 $($칸들.Count)개) · 여유 $(여유GB)GB"
$env:OWN_GROUPS = $무리줄; $env:OWN_EXPORT = "data\_labs\multi_rules_spec.json"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"
$env:LAB_OUT = "${날}_B218_4_무리후보_묶음.txt"
돌리기 "④ OWN_EXPORT" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$빠짐 = @(); $못 = 0
foreach ($칸 in $칸들) {
    $f = Join-Path "data\_labs" ($칸.Split("|")[4])
    if (-not (끝났나 $f "\[대조\] MULTI 내보내기 .* 끝")) { $빠짐 += $칸.Split("|")[4] }
    if (Test-Path $f) { $못 += @(Select-String -Path $f -Pattern "🛑 O\d+ .* 못 만든다").Count }
}
if ($못 -gt 0) { 적기 "⚠️ [B218] ④ 규칙을 못 만든 것 $($못)개 — multi_lab 이 뺀다(결과 맨 위 「후보 파일에 없는 규칙」)" }
if ($빠짐.Count -gt 0) { 그만 "❌ ④ 끝까지 안 간 무리 $($빠짐.Count)개: $($빠짐 -join ', ')" }

# ── ⑤ 한 계좌로 합치기 · 500만 N년 ──
if (-not (기다리기 "⑤ multi_lab" 12)) { 그만 "🛑 ⑤ 12시간 기다려도 모자라다" }
적기 "[B218] ⑤ multi_lab 시작"
$밖5 = "${날}_B218_여러규칙_한계좌_새목록.txt"; $env:LAB_OUT = $밖5; $env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"
돌리기 "⑤ multi_lab" "scripts\multi_lab.py"
foreach ($k in "LAB_OUT", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (-not (끝났나 (Join-Path "data\_labs" $밖5) "\[대조\] MULTI 끝")) { 적기 "❌ [B218] ⑤ 합치기가 끝까지 안 갔다 — 자름 10·30 은 그대로 간다" } else { 적기 "[B218] ⑤ 표 ✅ — data\_labs\$밖5" }

# ── ⑤-2 반도체 넓힌 무리 (낙폭 체 없이) ── 사용자 「네 앞당기세요」 (10/2 · 자름 10·30 보다 먼저)
#    data/semis-universe.json (업종코드 261·2927 ∪ 가치사슬 반도체 26 = 190종목) · own_lab 「종목」 무리
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — ⑤-2 반도체 안 함"; 적기 "===== queue_b218 끝 ====="; exit 1 }
밤샘기다리기
if (기다리기 "⑤-2 반도체" 20) {
    $코드 = ((Get-Content "data\semis-universe.json" -Raw -Encoding UTF8 | ConvertFrom-Json).종목) -join ','
    $밖52 = "${날}_B218_반도체넓힌무리_낙폭체없음.txt"
    적기 "[B218] ⑤-2 반도체 넓힌 무리 시작 ($(($코드 -split ',').Count)종목) · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = "종목|$코드|||$밖52"; $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_B218_반도체_묶음.txt"
    돌리기 "⑤-2 반도체" "scripts\own_lab.py"
    foreach ($k in "OWN_GROUPS", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖52) "\[대조\] 무리") { 적기 "[B218] ⑤-2 반도체 ✅ — data\_labs\$밖52" } else { 적기 "❌ [B218] ⑤-2 반도체가 끝까지 안 갔다 — 자름 10·30 은 그대로 간다" }
} else { 적기 "🛑 [B218] ⑤-2 12시간 기다려도 모자라다 — 건너뛴다" }

# ── ⑥ ⑦ 자름 10 · 30 (낙폭 체 없이) ──
foreach ($자름 in "10", "30") {
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 자름 $자름 부터 안 함"; 적기 "===== queue_b218 끝 ====="; exit 1 }
    밤샘기다리기
    적기 "[B218] 자름 $자름 · 낙폭 체 없이 시작"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut $자름 -NoDD | Out-Null
    적기 "[B218] 자름 $자름 대기열 끝"
}
적기 "===== queue_b218 끝 ====="
