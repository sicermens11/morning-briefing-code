# ==============================================================
#  queue_b241.ps1 — **B(업종별 8개) 아침 후보 대조** (2026-10-08)
#  ① 예측 기록(보통 방식 · 10/7 자료까지) ② 아침 방식(OWN_END=20261006 + OWN_LIVE) ③ compare_live 대조
#  사용자 10/7 「B는 반영」 · 「그렇다고 테스트의 정확도가 떨어져서는 안돼!」 — 하나도 안 다를 때만 쓴다
#  B240 뒤 · 판은 하나씩 · 07:20~09:10 피함 · 여유 3GB 밑이면 끈다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b241_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_b241 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B241] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*(===== 시험 끝 =====|시험을 건너뛴다)" -Quiet -Encoding UTF8   # 10/4: 새 자료가 없으면 시험을 건너뛰고 「시험 끝」 을 안 찍는다
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
        if ($ㅁ -eq 0) { 적기 "[B241] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [B241] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b241 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B241] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
# ⚠️ 10/7 독립 검사: 처음 만들 때 이 함수를 빠뜨렸다 — 없는 함수를 if 안에서 부르면 if 전체가 조용히 건너뛰어진다
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }   # 10/8: 🛑 는 「이 해엔 조건이 없어 못 만든다」 안내 줄이기도 하다(정상) — 터짐으로 세지 않는다
function 깃발보기($어디) { if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발($어디): $(Get-Content $깃발 -Raw -Encoding UTF8)" } }
function 실전후보다시 {
    깃발보기 "실전 후보 앞"
    밤샘기다리기
    if (-not (기다리기 "실전 후보 다시" 26)) { 그만 "🛑 실전 후보 12시간 기다려도 모자라다" }
    적기 "[B241] 실전 후보 (MULTIDUMP · 지금 자료까지) · 여유 $(여유GB)GB"
    $env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
    $env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
    $밖1 = "${날}_B241_실전후보_$(Get-Date -f HHmm).txt"; $env:LAB_OUT = $밖1
    돌리기 "실전 후보" "scripts\gate7_lab.py"
    foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ 실전 후보가 끝까지 안 갔다" }
}
function 점검($종류) {
    $o = & $py "scripts\preflight_check.py" --종류 $종류 2>&1
    $o | ForEach-Object { 적기 "    [점검] $_" } | Out-Null   # 10/8: 적기 가 줄을 돌려줘서 함수 값이 배열이 되어 「못 넘음」 이 「넘음」 으로 읽혔다
    return ($LASTEXITCODE -eq 0)
}
적기 "[B241] B240(기간 바꿔 판정)이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b240' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
깃발보기 "시작 앞"
# ── ① 오늘 예측 기록 (10/7 자료까지 · 보통 방식) — 대조 ② 의 「보통 방식」 파일을 만든다 ──
#    12:30 예약분은 대기열이 있으면 기다리므로 여기서 끼워 돌린다 (FD_INLINE · 같은 일을 두 번 해도 새 줄은 안 생긴다)
if (-not (기다리기 "예측 기록" 15)) { 그만 "🛑 예측 기록 12시간 기다려도 모자라다" }
적기 "[B241] ① 예측 기록 (보통 방식 · 오늘 자료까지)"
$env:FD_INLINE = "1"
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\forward_daily.ps1" | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
Remove-Item env:FD_INLINE -ErrorAction SilentlyContinue
$새끝 = (Select-String -Path "data\forward_groups_cand.jsonl" -Pattern '"끝날": "(\d+)"' | Select-Object -First 1).Matches.Groups[1].Value
적기 "[B241] ① 끝 — 보통 방식 후보 끝 날 $새끝"
if ($새끝 -ne "20261007") { 그만 "🛑 보통 방식 후보 끝 날이 20261007 이 아니다($새끝) — 대조 ② 를 못 한다" }
# ── ② 아침 방식: 10/6 까지 자료만 + 다음 거래일 자리 (10/7 아침에 돌렸다면 낼 후보) ──
깃발보기 "아침 방식 앞"
if (-not (기다리기 "아침 방식" 15)) { 그만 "🛑 아침 방식 12시간 기다려도 모자라다" }
$날8 = $날 -replace '-', ''
$무리8 = @(
    "섹터|조선 본선|||${날}_B241_아침_조선본선.txt", "섹터|휴머노이드/로봇|||${날}_B241_아침_로봇.txt",
    "섹터|해운|||${날}_B241_아침_해운.txt", "규모||700|1000|${날}_B241_아침_소형_700_1000.txt",
    "업종|비금속|||${날}_B241_아침_비금속.txt", "업종|섬유·의류|||${날}_B241_아침_섬유의류.txt",
    "업종|종이·목재|||${날}_B241_아침_종이목재.txt"
)
Remove-Item "data\_labs\forward_groups_cand_live1006.jsonl" -ErrorAction SilentlyContinue
적기 "[B241] ② 아침 방식 시작 (OWN_END=20261006 · OWN_LIVE · 얼린 8개 · 예측 기록과 같은 설정) · 여유 $(여유GB)GB"
$t0 = Get-Date
$env:OWN_GROUPS = ($무리8 -join ';'); $env:OWN_EXPORT = "data\forward-groups-spec.json"; $env:OWN_EXPORT_OUT = "_labs\forward_groups_cand_live1006.jsonl"
$env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:OWN_END = "20261006"; $env:OWN_LIVE = "1"; $env:LAB_OUT = "${날}_B241_아침방식_묶음.txt"
돌리기 "아침 방식" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "OWN_END", "OWN_LIVE", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
적기 ("[B241] ② 걸린 시간 {0:N0}분" -f ((Get-Date) - $t0).TotalMinutes)
$빠짐 = @()
foreach ($칸 in $무리8) { $f = Join-Path "data\_labs" ($칸.Split("|")[4]); if (-not (끝났나 $f "\[대조\] MULTI 내보내기 .* 끝")) { $빠짐 += $칸.Split("|")[4] } }
if ($빠짐.Count -gt 0) { 그만 "❌ ② 끝까지 안 간 무리 $($빠짐.Count)개: $($빠짐 -join ', ')" }
# ── ③ 대조 ──
$밖 = "data\_labs\${날}_B241_아침후보_대조.txt"
$o = & $py "scripts\compare_live.py" --live "data\_labs\forward_groups_cand_live1006.jsonl" --old "data\_labs\forward_groups_cand_data1006.jsonl" --new "data\forward_groups_cand.jsonl" --spec "data\forward-groups-spec.json" --out $밖 2>&1
$rc = $LASTEXITCODE
$o | Select-Object -Last 14 | ForEach-Object { 적기 "    $_" }
if ($rc -eq 0) { 적기 "[B241] ③ 대조 ✅ 하나도 안 다르다 — $밖" } else { 적기 "❌ [B241] ③ 대조 다름(코드 $rc) — $밖" }
적기 "===== queue_b241 끝 ====="
