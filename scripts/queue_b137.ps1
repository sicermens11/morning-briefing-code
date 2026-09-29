# ==============================================================
#  queue_b11.ps1 — **선물을 하루 늦춰도 ① 이 사나** (2026-09-22)
#
#  ## 왜 거나
#  ① 회전율 위20%·선물20 은 세 관문을 다 넘었는데 **실전에 못 넣었다.**
#  코스피200선물 파일 도착 시각을 재보니 영업일 하루 늦게 온다:
#      20260916(수) -> 09-17 20:30 · 20260917(목) -> 09-18 20:30
#      20260918(금) -> 09-21 20:30
#  기준일 선물값이 그날 저녁에나 오니, 넣어도 **조용히 한 번도 안 켜진다.**
#
#  ⇒ 실전에서 **실제로 쥘 수 있는 값**으로 다시 잰다:
#     선물20 을 기준일이 아니라 **기준일 직전 거래일**로 낸다.
#     통과하면 넣을 수 있고, 떨어지면 못 넣는다. 둘 다 답이다.
#
#  ## ⚠️ 바탕이 바뀌었다
#  의료·정밀기기·낙폭60 은 **오늘 실전에 넣었다** (커밋 49dbde7).
#  그러니 물음은 「Ⓗ 에 ① 을 더하면?」이 아니라
#  **「Ⓗ + 의료 에 ① 을 더하면?」** 이다. 바탕을 옛것으로 두면 딴 답이 나온다.
#  걷기도 밑거름을 **바탕**으로 놓고, 증분(앞·뒤 둘 다 늘었나)까지 찍는다.
#
#  ## 재는 것
#    ⓪ Ⓗ + 의료 (지금 실전 · 바탕)
#    ⓪ + 회전율(선물 그날)       ← 원래 잰 것. 실전엔 못 쓴다
#    ⓪ + 회전율(선물 하루 늦춤)   ← **실전에서 쓸 수 있는 것**
#    각각 셋 다 · 해마다 · 걷기 · 증분
#
#  앞줄 B10 · 메모리 18GB 관문 · 실행 전 검사 · 07:20~09:10 은 기다렸다 시작
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b137_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    # ⭐ 2026-09-23 — 휴장일엔 브리핑이 안 돈다. 연휴 나흘 × 1시간 50분을 그냥 버리고 있었다
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    if (-not ((($h -eq 7) -and ($m -ge 20)) -or ($h -eq 8) -or (($h -eq 9) -and ($m -lt 10)))) { return $false }
    & $py "scripts\krx_calendar.py" *> $null
    if ($LASTEXITCODE -ne 0) { return $false }   # 휴장 — 비켜 줄 이유가 없다
    return $true
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
$앞파일 = "data\_labs\2026-09-28_B122_가치사슬바구니.txt"
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
    적기 "===== queue_b49 비켜남 ====="
    exit 0
}
적기 "[0] 앞줄(B122)이 끝났나 본다 — 이미 끝났으면 바로 간다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 2880)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
메모리관문 18
메모리적기 "판 시작 전"

적기 "[0] 실행 전 검사 (이름·거름 겹침·짝 풀기)"
$aud = & $py "scripts/audit_small_base.py" --절 "FIN" 2>&1
if ($LASTEXITCODE -ne 0) { 적기 "❌ 소형 규칙 오염 조사에서 걸렸다 — 판을 안 띄운다"; $aud | Select-Object -Last 8 | ForEach-Object { 적기 "    $_" }; exit 1 }
적기 "[0] 소형 규칙 오염 조사 통과"
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 적기 "❌ 실행 전 검사에서 걸렸다 — 판을 띄우지 않는다"; exit 1 }
적기 "[B137] FIN — 재무 문 넷을 흔든다 (잉여금·부채·흑자·대금하한) - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:ONLY = "FIN"

$env:LAB_OUT = "2026-09-29_B137_재무문_흔들기.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [B137] 터졌다: $($_.Exception.Message)" }
foreach ($k in "TIMEMAP", "TIMEMAP", "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "VANISH_KIND", "OPENFIN", "SIZE_LO", "SIZE_HI2", "LAB_OUT", "ONLY") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-29_B137_재무문_흔들기.txt"
if (Test-Path $밖) { 적기 "[B137] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [B137] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
# ⭐ 2026-09-24 — 제 로그를 제가 읽는다. 터졌으면 깃발을 세워 **뒤 판을 멈춘다**
$끝줄 = @(Get-Content $log -Tail 40 -ErrorAction SilentlyContinue)
$터짐 = @($끝줄 | Where-Object { $_ -match "Traceback|[A-Za-z]+Error|터졌다" })
if ($터짐.Count -gt 0) {
    $쪽지 = "B49 이 터졌다 ($(Get-Date -f 'MM-dd HH:mm')) — " + ($터짐[-1])
    Set-Content -Path "data\_labs\_STOP.txt" -Value $쪽지 -Encoding UTF8
    적기 "🛑 이 판이 터졌다 — 멈춤 깃발을 세웠다 (뒤 판은 안 돈다)"
    적기 "   $($터짐[-1])"
}
적기 "===== queue_b137 끝 ====="
