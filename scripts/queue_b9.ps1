# ==============================================================
#  queue_b9.ps1 — **더한 것이 앞뒤 둘 다에서 일을 해야 고른다** (2026-09-22)
#
#  ## 왜 거나 — Q-25 의 관문이 헐거웠다
#  Q-25 는 다섯을 쌓아 149% 를 만들었다. 그런데 앞 구간 숫자가 안 움직인다:
#    바퀴  더한 것                   앞 끝 자산    산 것
#     1   회전율 위20%·선물20         65,782,537   113
#     2   업종 금융·선물20+시장낙폭      65,782,537   113  ← 똑같다
#     3   업종 의료·정밀기기·낙폭60      69,335,379   116
#     4   업종 화학·선물20+시장낙폭      69,335,379   116  ← 똑같다
#     5   업종 전기전자·선물20+시장낙폭   69,335,379   116  ← 똑같다
#
#  2·4·5 바퀴에 더한 것은 **앞 구간에서 한 종목도 더 못 샀다.** 뒤에만 보탬이 된다.
#  걷기 관문이 **쌓인 것 전체**의 앞뒤를 봤기 때문이다 —
#  1바퀴 회전율이 앞을 이미 + 로 만들어 놔서 뒤에 무엇을 얹어도 「앞 +」로 찍혔다.
#  Q-24 에서 금융이 혼자선 걷기 ❌(앞 0.0%) 였던 그것이 여기선 통과했다.
#
#  ⇒ 관문을 고친다: **쌓인 것의 앞끝·뒤끝과 견줘 둘 다 늘어야** 고른다.
#     고르는 잣대도 전 기간 통짜가 아니라 **걷기로 이은 뒤 끝 자산**으로.
#     바퀴마다 늘어난 폭(%)을 앞뒤 따로 찍는다 — 0.0% 짜리가 다시 못 끼게.
#
#  ## 얼마나 걸리나 (실측)
#    B8 55분에 시뮬 205회 ⇒ 시뮬 한 번 ≈ 5초
#    Q-26 = 자료 35 + 43×2×최대 6바퀴 = 516 시뮬 ≈ 43분
#    ⇒ **1시간 10분 ~ 1시간 30분** (06:00 안팎 · 아침 창 전에 끝난다)
#
#  앞줄 B8 · 메모리 18GB 관문 · 실행 전 검사 · 07:20~09:10 은 기다렸다 시작
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b9_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { }
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -eq 8) -or ($h -eq 9 -and $m -lt 10))
}
function 메모리여유GB {
    return [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1)
}
function 메모리적기($때) {
    $o = Get-CimInstance Win32_OperatingSystem
    적기 ("[메모리] $때 — 물리 남음 {0} GB · 커밋 여유 {1} GB" -f
          [math]::Round($o.FreePhysicalMemory / 1MB, 1), [math]::Round($o.FreeVirtualMemory / 1MB, 1))
}
function 메모리관문($필요GB = 18) {
    $ㅁ = 0
    while ((메모리여유GB) -lt $필요GB -and $ㅁ -lt 40) {
        if ($ㅁ -eq 0) { 적기 ("[메모리] 여유 {0} GB — {1} GB 될 때까지 기다린다" -f (메모리여유GB), $필요GB) }
        Start-Sleep -Seconds 60; $ㅁ = $ㅁ + 1
    }
    if ($ㅁ -gt 0) { 적기 "[메모리] $ㅁ 분 기다렸다" }
}
# ⚠️ 메모리 — 판 하나가 24GB 다. 앞줄이 끝나고 커밋이 돌아온 뒤에만 시작한다
$앞파일 = "data\_labs\2026-09-22_B8_쌓아올리기.txt"
function 앞줄끝났나 {
    if (-not (Test-Path $앞파일)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}
# ⭐ 2026-09-24 — **멈춤 깃발**. 앞 판이 터졌으면 같은 벽에 또 부딪히지 않는다
#    (12:15 에 건 다섯 판이 전부 같은 UnboundLocalError 로 죽었는데 사슬이 그냥 돌았다)
$멈춤깃발 = "data\_labs\_STOP.txt"
if (Test-Path $멈춤깃발) {
    적기 "🛑 멈춤 깃발이 있다 — 이 판은 돌지 않는다. 먼저 고치고 깃발을 지워라"
    적기 ("   " + ((Get-Content $멈춤깃발 -Raw -ErrorAction SilentlyContinue) -replace "`r`n", " "))
    적기 "===== queue_b9 비켜남 ====="
    exit 0
}
적기 "[0] 앞줄(B8)이 끝났나 본다 — 이미 끝났으면 바로 간다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 300)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
메모리관문 18
메모리적기 "판 시작 전"

적기 "[0] 실행 전 검사 (이름·거름 겹침·짝 풀기)"
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 적기 "❌ 실행 전 검사에서 걸렸다 — 판을 띄우지 않는다"; exit 1 }
적기 "[B9] Q-26 더한 것이 앞뒤 둘 다에서 일을 해야 고른다 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:ONLY = "Q26"
$env:LAB_OUT = "2026-09-22_B9_앞뒤둘다일하나.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [B9] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT", "ONLY") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-22_B9_앞뒤둘다일하나.txt"
if (Test-Path $밖) { 적기 "[B9] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [B9] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
# ⭐ 2026-09-24 — 제 로그를 제가 읽는다. 터졌으면 깃발을 세워 **뒤 판을 멈춘다**
$끝줄 = @(Get-Content $log -Tail 40 -ErrorAction SilentlyContinue)
$터짐 = @($끝줄 | Where-Object { $_ -match "Traceback|[A-Za-z]+Error|터졌다" })
if ($터짐.Count -gt 0) {
    $쪽지 = "B9 이 터졌다 ($(Get-Date -f 'MM-dd HH:mm')) — " + ($터짐[-1])
    Set-Content -Path "data\_labs\_STOP.txt" -Value $쪽지 -Encoding UTF8
    적기 "🛑 이 판이 터졌다 — 멈춤 깃발을 세웠다 (뒤 판은 안 돈다)"
    적기 "   $($터짐[-1])"
}
적기 "===== queue_b9 끝 ====="
