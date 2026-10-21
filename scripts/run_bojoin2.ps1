# ==============================================================
#  run_bojoin2.ps1 — 10/21 밤 BOJOIN 첫 판(보완 같이 = 뒤 45% · −44.7%) 뒤 · 빈 날만 · 중형만 · 대형만(BOJOIN2=1) · 반영 없음
#  run_mincand 가 끝난 뒤에 돈다
#  사용자 10/14 「대형 1조↑를 나중에 금액별 성적 시험에서 다시 본다고 했는데 그 시점은 언제야?」
#  사용자 10/13 「돈과 하루 자리를 나눠 쓰는 건 테스트를 위한 거잖아? …」 → 「합치면 손해」 가 「한 번에 20%」 가정 탓인가
#  ① 실전 후보 다시(MULTIDUMP · 업종 갈래 끈 지금 규칙) ② 오늘(끝 날 10/12) B·반도체 후보로 make_mix ③ 비중 20·10·2% × (B·반도체) × (2019~·2024~) 합치기
#  ④ 결정 대기 후보 넷(ADDCHK)을 비중 10·2% 로 · 큰 계산 자물쇠 · 07:20~09:10·12:30 예측 기록에 비켜 준다 · C 는 10/13 예측 기록이 빠져 다음에
#  사용자 10/13 「이미 걸려있는 테스트를 끝내고 진행하자」 · live_vs_sim 첫 대조: 9/3~ 실전 산다 16건 중 시험과 겹침 1건
#  왜: 10/12 밤 NEW18 세 판과 night_chain3 의 현금 규칙 찾기가 옛 「계좌 낙폭 −12%」 체(MAXDD −12)로 걸려 있었다
#      10/2 결정 「계좌 낙폭은 체가 아니라 정보로」(사용자 「그렇다」) — 그래서 셋 다 「통과 없음」 · 이 줄은 MAXDD −999
#  낮 12:30 예측 기록이 먼저 돌게 비켜 준다 · 07:20 전에 못 끝나는 판은 09:10 뒤로
#  ⚠️ 이름에 queue_ 를 안 쓴다
# ==============================================================
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\run_bojoin2_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
function 껍데기($무늬) { @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match $무늬 }).Count }
$깃발 = "data\_labs\_STOP.txt"
# 걸리는 분을 받아 「지금 시작하면 07:20 전에 못 끝나거나 아침 시간(07:20~09:10)인가」
function 아침과겹치나($걸림분) {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    $평일 = ([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5)
    return ($평일 -and (($m + $걸림분) -gt 440) -and ($m -lt 550))
}
function 차례기다리기($이름, $문GB, $걸림분) {
    $ㅁ = 0
    while ((아침과겹치나 $걸림분) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) {
        if ($ㅁ % 60 -eq 0) { 적기 "[BOJOIN2] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 · 아침과 겹침 $(아침과겹치나 $걸림분) (약 ${걸림분}분 걸림) — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8)"; 적기 "===== night_chain 끝 ====="; exit 1 }
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden -RedirectStandardError "run-logs\bojoin2_err_$(Get-Date -f HHmm).txt"
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [BOJOIN2] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "night_chain 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[BOJOIN2] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }
$표준 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"; BASE_SELL = "0.4,15,40 / 0.6,40,90"; BASE_PICKS = "120"; SIZE_HI = "999999" }
function gate7($이름, $only, $밖, $대조, $걸림분) {
    차례기다리기 $이름 15 $걸림분
    적기 "[BOJOIN2] $이름 시작 · 여유 $(여유GB)GB"
    foreach ($k in $표준.Keys) { Set-Item "env:$k" $표준[$k] }
    $env:ONLY = $only; $env:LAB_OUT = $밖
    돌리기 $이름 "scripts\gate7_lab.py"
    foreach ($k in @($표준.Keys) + @("ONLY", "LAB_OUT")) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) $대조) { 적기 "[BOJOIN2] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [BOJOIN2] $이름 끝까지 안 갔다 — data\_labs\$밖" }
}


# ── 낮 예측 기록(12:30 forward_daily)에 길을 비켜 준다 — 12:30 이 지났고 오늘 「예측 기록 끝」 이 없으면 기다린다
function 예측기록차례인가 {
    $n = Get-Date
    if ([int]$n.DayOfWeek -eq 0 -or [int]$n.DayOfWeek -eq 6) { return $false }   # 10/18 — 주말엔 낮 예측 기록이 안 돈다
    if ($n.Hour * 60 + $n.Minute -lt 750) { return $false }
    $fl = "run-logs\forward_daily_$(Get-Date -f yyyyMMdd).log"
    $cal = Get-Content "data\_holiday_today.txt" -ErrorAction SilentlyContinue
    if (-not (Test-Path $fl)) { return ($n.Hour -lt 20) }   # 아직 안 떴으면(휴장일이면 안 뜬다) 20시까지만 기다린다
    return (-not (Select-String -Path $fl -Pattern "===== 예측 기록 끝 =====|휴장" -Quiet -Encoding UTF8))
}
function 차례($이름, $문GB, $걸림분) {
    $ㅁ = 0
    while (예측기록차례인가) { if ($ㅁ % 60 -eq 0) { 적기 "[BOJOIN2] $이름 — 낮 예측 기록(12:30)이 먼저 — 기다린다" }; Start-Sleep 60; $ㅁ++ }
    차례기다리기 $이름 $문GB $걸림분
    while (예측기록차례인가) { Start-Sleep 60 }
}
function 소유($이름, $groups, $새, $뺄, $밖묶음, $걸림분, $대조파일) {
    차례 $이름 25 $걸림분
    적기 "[BOJOIN2] $이름 시작 · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = $groups; $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = $밖묶음
    foreach ($k in $새) { Set-Item "env:$k" "1" }
    if ($뺄) { $env:OWN_NEW_DROP = $뺄 }
    돌리기 $이름 "scripts\own_lab.py"
    foreach ($k in @("OWN_GROUPS", "MAXDD", "OWN_CUT", "LAB_OUT", "OWN_NEW_DROP") + $새) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $대조파일) "\[대조\] 무리 규모") { 적기 "[BOJOIN2] $이름 ✅ — data\_labs\$대조파일" } else { 적기 "❌ [BOJOIN2] $이름 끝까지 안 갔다 — data\_labs\$대조파일" }
}


. "$PSScriptRoot\biglock.ps1"
function 잠금gate7($이름, $only, $밖, $대조, $분) {
    차례 $이름 15 $분
    if (-not (큰판잡기 $이름)) { 적기 "❌ [BOJOIN2] $이름 — 자물쇠 못 잡음 · 건너뜀"; return }
    try { gate7 $이름 $only $밖 $대조 $분 } finally { 큰판놓기 }
}
function 합치기($이름, $스펙, $후보, $나눔, $꼬리, $w) {
    $env:MULTI_SPEC = $스펙; $env:MULTI_CAND = $후보; $env:MULTI_SPLIT = $나눔; $env:MULTI_WEIGHT = $w
    $o = & $py "scripts\preflight_check.py" --종류 multi 2>&1
    $ok = ($LASTEXITCODE -eq 0)
    $o | Select-Object -Last 3 | ForEach-Object { 적기 "    [점검] $_" } | Out-Null
    if (-not $ok) {
        적기 "⚠️ [BOJOIN2] $이름 — 점검 못 넘음(끝 날·나눔) · 건너뜀"
        foreach ($k in "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT", "MULTI_WEIGHT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
        return
    }
    차례 $이름 12 15
    if (-not (큰판잡기 $이름)) { 적기 "❌ [BOJOIN2] $이름 — 자물쇠 못 잡음"; return }
    try {
        $날 = Get-Date -f "yyyy-MM-dd"
        $밖 = "${날}_MONEY_${꼬리}.txt"; $env:LAB_OUT = $밖
        $env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"; $env:MULTI_PROTECT = "1"
        적기 "[BOJOIN2] $이름 시작 · 여유 $(여유GB)GB"
        돌리기 $이름 "scripts\multi_lab.py"
        if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] 보호 끝") { 적기 "[BOJOIN2] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [BOJOIN2] $이름 끝까지 안 갔다 — data\_labs\$밖" }
    } finally {
        큰판놓기
        foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_SPLIT", "MULTI_WEIGHT", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST", "MULTI_PROTECT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    }
}





$날 = Get-Date -f "yyyy-MM-dd"
Remove-Item env:MKT20, env:MKT60, env:MKT_LIVE, env:POOL_BUYBACK -ErrorAction SilentlyContinue
Remove-Item env:IND_FORCE_ON, env:BOCOUNT, env:ALLSIG_CMP -ErrorAction SilentlyContinue
# 뉴스 시험 후보 뽑기(NEWSDUMP)가 먼저 — 기사 받기는 몇 시간 걸려서 늦게 시작하면 결과가 밀린다 · 최대 3시간 기다린다
$ㅁ = 0
while ($ㅁ -lt 180) {
    $nl = Get-ChildItem run-logs\run_newscut_* -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
    if ($nl -and (Select-String -Path $nl.FullName -Pattern "기사 받기 시작|run_newscut 끝" -Quiet -Encoding UTF8)) { break }
    if ($ㅁ % 30 -eq 0) { 적기 "[BOJOIN2] 뉴스 후보 뽑기가 먼저 — 기다린다" }
    Start-Sleep 60; $ㅁ++
}
$env:BOJOIN2 = "1"
잠금gate7 "보완 빈 날만·중형만·대형만(BOJOIN2)" "BOJOIN" "${날}_$(Get-Date -f HHmm)_BOJOIN2_빈날중형대형.txt" "\[대조\] DDCTRL 끝" 70
Remove-Item env:BOJOIN2 -ErrorAction SilentlyContinue

적기 "===== run_bojoin2 끝 ====="
