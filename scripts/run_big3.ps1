# ==============================================================
#  run_big3.ps1 — 16:08 메모리로 멈춘 큰 판 다시: 새 재료 18개 규칙 찾기 세 띠 → 현금흐름 규칙 찾기 (2026-10-13 16:40)
#  가상 메모리 48 → 64GB(사용자 10/13 「권고대로 하자」 · 처음 크기 32768MB) 뒤 · 큰 계산 자물쇠(biglock)로 하나씩 · 낙폭 체 없음(MAXDD −999)
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
$log = "run-logs\run_big3_$(Get-Date -f yyyyMMdd_HHmmss).log"
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
        if ($ㅁ % 60 -eq 0) { 적기 "[BIG3] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 · 아침과 겹침 $(아침과겹치나 $걸림분) (약 ${걸림분}분 걸림) — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8)"; 적기 "===== night_chain 끝 ====="; exit 1 }
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [BIG3] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "night_chain 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[BIG3] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }
$표준 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"; BASE_SELL = "0.4,15,40 / 0.6,40,90"; BASE_PICKS = "120"; SIZE_HI = "999999" }
function gate7($이름, $only, $밖, $대조, $걸림분) {
    차례기다리기 $이름 15 $걸림분
    적기 "[BIG3] $이름 시작 · 여유 $(여유GB)GB"
    foreach ($k in $표준.Keys) { Set-Item "env:$k" $표준[$k] }
    $env:ONLY = $only; $env:LAB_OUT = $밖
    돌리기 $이름 "scripts\gate7_lab.py"
    foreach ($k in @($표준.Keys) + @("ONLY", "LAB_OUT")) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) $대조) { 적기 "[BIG3] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [BIG3] $이름 끝까지 안 갔다 — data\_labs\$밖" }
}


# ── 낮 예측 기록(12:30 forward_daily)에 길을 비켜 준다 — 12:30 이 지났고 오늘 「예측 기록 끝」 이 없으면 기다린다
function 예측기록차례인가 {
    $n = Get-Date
    if ($n.Hour * 60 + $n.Minute -lt 750) { return $false }
    $fl = "run-logs\forward_daily_$(Get-Date -f yyyyMMdd).log"
    $cal = Get-Content "data\_holiday_today.txt" -ErrorAction SilentlyContinue
    if (-not (Test-Path $fl)) { return ($n.Hour -lt 20) }   # 아직 안 떴으면(휴장일이면 안 뜬다) 20시까지만 기다린다
    return (-not (Select-String -Path $fl -Pattern "===== 예측 기록 끝 =====|휴장" -Quiet -Encoding UTF8))
}
function 차례($이름, $문GB, $걸림분) {
    $ㅁ = 0
    while (예측기록차례인가) { if ($ㅁ % 60 -eq 0) { 적기 "[BIG3] $이름 — 낮 예측 기록(12:30)이 먼저 — 기다린다" }; Start-Sleep 60; $ㅁ++ }
    차례기다리기 $이름 $문GB $걸림분
    while (예측기록차례인가) { Start-Sleep 60 }
}
function 소유($이름, $groups, $새, $뺄, $밖묶음, $걸림분, $대조파일) {
    차례 $이름 25 $걸림분
    적기 "[BIG3] $이름 시작 · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = $groups; $env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:LAB_OUT = $밖묶음
    foreach ($k in $새) { Set-Item "env:$k" "1" }
    if ($뺄) { $env:OWN_NEW_DROP = $뺄 }
    돌리기 $이름 "scripts\own_lab.py"
    foreach ($k in @("OWN_GROUPS", "MAXDD", "OWN_CUT", "LAB_OUT", "OWN_NEW_DROP") + $새) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $대조파일) "\[대조\] 무리 규모") { 적기 "[BIG3] $이름 ✅ — data\_labs\$대조파일" } else { 적기 "❌ [BIG3] $이름 끝까지 안 갔다 — data\_labs\$대조파일" }
}


. "$PSScriptRoot\biglock.ps1"
function 잠그고소유($이름, $groups, $새, $뺄, $밖묶음, $걸림분, $대조파일) {
    차례 $이름 25 $걸림분
    if (-not (큰판잡기 $이름)) { 적기 "❌ [BIG3] $이름 — 자물쇠를 24시간 못 잡았다 · 건너뜀"; return }
    try { 소유 $이름 $groups $새 $뺄 $밖묶음 $걸림분 $대조파일 } finally { 큰판놓기 }
}
적기 "[BIG3] 시작 · 여유 $(여유GB)GB(한도 64GB)"
# ① 새 재료 18개 규칙 찾기 다시 — 10/12 밤 판은 옛 −12% 체로 「통과 없음」(무효) · 겹침 0.7↑ 12개는 뺀다
$뺄N = "복권MAX20,모멘텀12_1,대금배20,VWAP거리20,일목전환기준,RSI2,ROA,영업이익자산,ROIC근사,AltmanZ,넷넷,이익수익률EV"
foreach ($칸 in @(@("300", "2000", 260), @("2000", "10000", 120), @("10000", "", 70))) {
    $날 = Get-Date -f "yyyy-MM-dd"
    $밖N = "${날}_NEW18_규모$($칸[0])_$($칸[1])_낙폭체없음.txt"
    잠그고소유 "새 재료 규칙 찾기 $($칸[0])~$($칸[1])억(낙폭 체 없음)" "규모||$($칸[0])|$($칸[1])|$밖N" @("OWN_NEWPV", "OWN_NEWFIN") $뺄N "${날}_NEW18_묶음_낙폭체없음.txt" $칸[2] $밖N
}
# ② 현금흐름 규칙 찾기 — 겹침 검사(10/13 14:44)는 끝났다 · 빼는 재료 0개
$날 = Get-Date -f "yyyy-MM-dd"
$밖C = Get-ChildItem "data\_labs\*_CF251_현금재료_겹침.txt" | Sort-Object LastWriteTime | Select-Object -Last 1
$뺄C = @()
if ($밖C) { foreach ($m in (Select-String -Path $밖C.FullName -Pattern "^\s+(\S+)\s+값 .*❌ 뺀다" -Encoding UTF8 -ErrorAction SilentlyContinue)) { $뺄C += $m.Matches[0].Groups[1].Value } }
적기 "[BIG3] 현금 겹침 결과 $($밖C.Name) — 빼는 재료 $($뺄C.Count)개"
잠그고소유 "현금 재료 규칙 찾기(300~2,000억 · 낙폭 체 없음)" "규모||300|2000|${날}_CF251_규모300_2000_낙폭체없음.txt" @("OWN_NEWCF") ($뺄C -join ",") "${날}_CF251_묶음2.txt" 260 "${날}_CF251_규모300_2000_낙폭체없음.txt"
적기 "===== run_big3 끝 ====="
