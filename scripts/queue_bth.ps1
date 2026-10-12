# ==============================================================
#  queue_bth.ps1 — **B 에 사는 문턱 −1 · −2 · −3.5 를 걸면 지금 규칙과 합쳐 돈이 느나** (2026-10-12)
#  사용자 「지금 규칙에 3.5% 적용하는게 뭐였지? B에는 조금더 엄격한 기준을 적용하면 되지 않아?」 · B 는 문턱 없음(99)
#  문턱만 바꾼 스펙(make_spec_th) → 7무리 내보내기(한 프로세스 · 끝 날 10/8) → 지금 규칙과 합치기 2019~ · 2024~ (보호·이익 절반 포함)
#  한 문턱 약 50분 · 12GB · 하나씩
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_bth_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_bth 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[BTH] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
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
        if ($ㅁ -eq 0) { 적기 "[BTH] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
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
        if ((여유GB) -lt 3) { 적기 "🛑 [BTH] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_bth 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[BTH] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
# ⚠️ 10/7 독립 검사: 처음 만들 때 이 함수를 빠뜨렸다 — 없는 함수를 if 안에서 부르면 if 전체가 조용히 건너뛰어진다
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }   # 10/8: 🛑 는 「이 해엔 조건이 없어 못 만든다」 안내 줄이기도 하다(정상) — 터짐으로 세지 않는다
function 깃발보기($어디) { if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발($어디): $(Get-Content $깃발 -Raw -Encoding UTF8)" } }
function 실전후보다시 {
    깃발보기 "실전 후보 앞"
    밤샘기다리기
    if (-not (기다리기 "실전 후보 다시" 15)) { 그만 "🛑 실전 후보 12시간 기다려도 모자라다" }
    적기 "[BTH] 실전 후보 (MULTIDUMP · 지금 자료까지) · 여유 $(여유GB)GB"
    $env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
    $env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "MULTIDUMP"
    $밖1 = "${날}_BTH_실전후보_$(Get-Date -f HHmm).txt"; $env:LAB_OUT = $밖1
    돌리기 "실전 후보" "scripts\gate7_lab.py"
    foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (-not (끝났나 (Join-Path "data\_labs" $밖1) "\[대조\] MULTIDUMP 끝")) { 그만 "❌ 실전 후보가 끝까지 안 갔다" }
}
function 점검($종류) {
    $o = & $py "scripts\preflight_check.py" --종류 $종류 2>&1
    $o | ForEach-Object { 적기 "    [점검] $_" } | Out-Null   # 10/8: 적기 가 줄을 돌려줘서 함수 값이 배열이 되어 「못 넘음」 이 「넘음」 으로 읽혔다
    return ($LASTEXITCODE -eq 0)
}
function 합치기($이름, $스펙, $후보, $나눔, $꼬리) {
    깃발보기 "$이름 앞"
    $env:MULTI_SPEC = $스펙; $env:MULTI_CAND = $후보; $env:MULTI_SPLIT = $나눔
    if (-not (점검 "multi")) { 적기 "⚠️ [BTH] $이름 — 점검 못 넘음(끝 날·나눔) · 건너뜀"; foreach ($k in "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }; return }
    if (-not (기다리기 $이름 12)) { 그만 "🛑 12시간 기다려도 모자라다" }
    적기 "[BTH] $이름 한 계좌 + 보호 시작"
    $밖 = "${날}_BTH_${꼬리}.txt"; $env:LAB_OUT = $밖
    $env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"; $env:MULTI_PROTECT = "1"
    돌리기 $이름 "scripts\multi_lab.py"
    foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST", "MULTI_PROTECT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] 보호 끝") { 적기 "[BTH] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [BTH] $이름 끝까지 안 갔다" }
}
$날 = Get-Date -f "yyyy-MM-dd"
$무리8 = @(
    "섹터|조선 본선|||${날}_BTH_조선본선.txt", "섹터|휴머노이드/로봇|||${날}_BTH_로봇.txt",
    "섹터|해운|||${날}_BTH_해운.txt", "규모||700|1000|${날}_BTH_소형_700_1000.txt",
    "업종|비금속|||${날}_BTH_비금속.txt", "업종|섬유·의류|||${날}_BTH_섬유의류.txt",
    "업종|종이·목재|||${날}_BTH_종이목재.txt"
)
foreach ($문 in @("-1", "-2", "-3.5")) {
    깃발보기 "문턱 $문 앞"
    $o = & $py "scripts\make_spec_th.py" $문 2>&1; 적기 "    $o"
    if (-not (기다리기 "문턱 $문 내보내기" 15)) { 그만 "🛑 12시간 기다려도 모자라다" }
    Remove-Item "data\_labs\fg_cand_th$문.jsonl" -ErrorAction SilentlyContinue
    적기 "[BTH] 문턱 $문 — B 7무리 내보내기 시작 · 여유 $(여유GB)GB"
    $무리이번 = $무리8 | ForEach-Object { $_ -replace '_BTH_', "_BTH${문}_" }
    $env:OWN_GROUPS = ($무리이번 -join ';'); $env:OWN_EXPORT = "data\_labs\spec_B_th$문.json"; $env:OWN_EXPORT_OUT = "fg_cand_th$문.jsonl"
    $env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_BTH${문}_묶음.txt"
    돌리기 "문턱 $문 내보내기" "scripts\own_lab.py"
    foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $o = & $py "scripts\make_mix.py" "Bth$문" "_labs\spec_B_th$문.json" "_labs\fg_cand_th$문.jsonl" 2>&1; 적기 "    $o"
    합치기 "지금 규칙 + B 문턱 $문 (2019~)" "spec_mix_Bth$문.json" "mix_cand_Bth$문.jsonl" "2019" "지금+B문턱${문}_2019"
    $env:MULTI_MIXSPLIT = "1"
    합치기 "지금 규칙 + B 문턱 $문 (2024~)" "spec_mix_Bth$문.json" "mix_cand_Bth$문.jsonl" "2024" "지금+B문턱${문}_2024"
    Remove-Item env:MULTI_MIXSPLIT -ErrorAction SilentlyContinue
}
적기 "===== queue_bth 끝 ====="
