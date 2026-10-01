# ==============================================================
#  queue_b212.ps1 — **여러 규칙 한 계좌 (MULTI)** (2026-10-01)
#  ① gate7 ONLY=MULTIDUMP — 실전 규칙의 그날 후보 → data/_labs/multi_cand_live.jsonl (화면 파일 안 건드림)
#  ② own_lab OWN_EXPORT — 통과 무리 규칙 20개(15무리)의 그날 후보 → data/_labs/multi_cand_own.jsonl
#  ③ multi_lab — 한 계좌로 합쳐 하루 최대 4·6·8·10·제한 없음 · 앞/뒤 · 하나씩 쌓기
#  사용자: 「재료는 AND여도 규칙은 OR가 맞는 것 같은데」 · 「넣되 표에 ⚠️를 붙이는 걸로 진행하자」
#  판은 하나씩 (앞 판이 끝나야 다음) · 07:20~09:10 피함 · 여유 3GB 밑이면 끈다
# ==============================================================
param([switch]$Dry)
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b212_$(Get-Date -f yyyyMMdd_HHmmss).log"
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
# 무리 15개 — 종류|값|BIG_LO|BIG_HI|결과 파일 (스펙의 「무리」 글과 own_lab _무리글 이 같아야 규칙을 찾는다)
$무리들 = @(
    "규모||10000||2026-10-01_B212_내보내기_대형1조.txt",
    "규모||700|1000|2026-10-01_B212_내보내기_소형_700_1000.txt",
    "섹터|조선 기자재|||2026-10-01_B212_내보내기_조선기자재.txt",
    "섹터|조선 본선|||2026-10-01_B212_내보내기_조선본선.txt",
    "섹터|휴머노이드/로봇|||2026-10-01_B212_내보내기_로봇.txt",
    "섹터|바이오 CDMO|||2026-10-01_B212_내보내기_CDMO.txt",
    "섹터|우주/스페이스X|||2026-10-01_B212_내보내기_우주.txt",
    "섹터|해운|||2026-10-01_B212_내보내기_해운.txt",
    "업종|건설|||2026-10-01_B212_내보내기_건설.txt",
    "업종|비금속|||2026-10-01_B212_내보내기_비금속.txt",
    "업종|섬유·의류|||2026-10-01_B212_내보내기_섬유의류.txt",
    "업종|운송·창고|||2026-10-01_B212_내보내기_운송창고.txt",
    "업종|음식료·담배|||2026-10-01_B212_내보내기_음식료.txt",
    "업종|제약|||2026-10-01_B212_내보내기_제약.txt",
    "업종|종이·목재|||2026-10-01_B212_내보내기_종이목재.txt"
)
if ($Dry) { $무리들 | ForEach-Object { Write-Output $_ }; Write-Output "무리 $($무리들.Count)개"; exit 0 }
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 안 돈다"; 적기 "===== queue_b212 끝 ====="; exit 1 }

function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B212] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    return (-not (((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)))
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [B212] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b212 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B212] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다|🛑" -Quiet)) }
function 그만($s) { 적기 $s; Set-Content $깃발 "queue_b212 $s $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; 적기 "===== queue_b212 끝 ====="; exit 1 }

# ── ① 실전 규칙 후보 ──
if (-not (기다리기 "① MULTIDUMP" 26)) { 그만 "🛑 ① 12시간 기다려도 모자라다" }
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 2 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 그만 "❌ 실행 전 검사에서 걸렸다" }
적기 "[B212] ① MULTIDUMP 시작 · 여유 $(여유GB)GB"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
$밖1 = "2026-10-01_B212_1_실전후보.txt"; $env:LAB_OUT = $밖1
돌리기 "① MULTIDUMP" "scripts\gate7_lab.py"
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ ① 실전 후보가 끝까지 안 갔다" }

# ── ② 무리 규칙 후보 (덧붙여 쓰므로 먼저 지운다) ──
Remove-Item "data\_labs\multi_cand_own.jsonl" -ErrorAction SilentlyContinue
if (-not (기다리기 "② OWN_EXPORT" 20)) { 그만 "🛑 ② 12시간 기다려도 모자라다" }
적기 "[B212] ② OWN_EXPORT 시작 (무리 $($무리들.Count)개 한 프로세스) · 여유 $(여유GB)GB"
$env:OWN_GROUPS = ($무리들 -join ';'); $env:OWN_EXPORT = "data\_labs\multi_rules_spec.json"; $env:MAXDD = "-12"
$env:LAB_OUT = "2026-10-01_B212_2_무리후보_묶음.txt"
돌리기 "② OWN_EXPORT" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "MAXDD", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$빠짐 = @()
foreach ($칸 in $무리들) { $f = Join-Path "data\_labs" ($칸.Split("|")[4]); if (-not (끝났나 $f "\[대조\] MULTI 내보내기 .* 끝")) { $빠짐 += $칸.Split("|")[4] } }
if ($빠짐.Count -gt 0) { 그만 "❌ ② 끝까지 안 간 무리 $($빠짐.Count)개: $($빠짐 -join ', ')" }

# ── ③ 한 계좌로 합치기 ──
if (-not (기다리기 "③ multi_lab" 12)) { 그만 "🛑 ③ 12시간 기다려도 모자라다" }
적기 "[B212] ③ multi_lab 시작 · 여유 $(여유GB)GB"
$밖3 = "2026-10-01_B212_여러규칙_한계좌.txt"; $env:LAB_OUT = $밖3
돌리기 "③ multi_lab" "scripts\multi_lab.py"
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
if (-not (끝났나 (Join-Path "data\_labs" $밖3) "\[대조\] MULTI 끝")) { 그만 "❌ ③ 합치기가 끝까지 안 갔다" }
적기 "[B212] 끝까지 ✅ — 결과 data\_labs\$밖3"
적기 "===== queue_b212 끝 ====="
