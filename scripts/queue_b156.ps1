# ==============================================================
#  queue_b156.ps1 — **낙폭 한계별 기회·끝 자산** (2026-09-30)
#  사용자: 「④ 퀀트 화면 6장 「과거에 어땠나」 숫자는 화면이 실제로 쓰는 규칙과 맞도록 바꾸자」
#  gate7 CARDLIVE → data/rule-cases.json · data/rule-capital.json 을 새로 쓴다 (전 것은 _labs 에 둔다)
#  앞줄 B153 · 메모리 18GB 관문 · 07:20~09:10 은 기다렸다 시작
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b156_$(Get-Date -f yyyyMMdd_HHmm).log"
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
function 메모리관문($필요GB = 18, $최대분 = 40) {
    $ㅁ = 0
    # ⭐ 2026-09-29 — 기다리는 동안 **아침 시간대면 여유가 돼도 안 뜬다.**
    #    밤새 기다리다 07:20~09:10 에 메모리가 풀리면 브리핑과 겹쳐 뜬다. 브리핑이 먼저다
    while ((((메모리여유GB) -lt $필요GB) -or (아침인가)) -and $ㅁ -lt $최대분) {
        if ($ㅁ -eq 0) { 적기 ("[메모리] 여유 {0} GB — {1} GB 될 때까지 기다린다" -f (메모리여유GB), $필요GB) }
        Start-Sleep -Seconds 60; $ㅁ = $ㅁ + 1
    }
    if ($ㅁ -gt 0) { 적기 "[메모리] $ㅁ 분 기다렸다" }
    # ⭐⭐⭐ 2026-09-29 — **끝까지 모자라면 돌지 않는다.** 전에는 40분 기다린 뒤
    #    여유가 그대로여도 **그냥 떴다** (늦추기만 하고 막지 않았다).
    #    재부팅으로 커밋 한도가 45 -> 33.9GB 가 된 날 B142 이 여유 16.5GB 에서 뜰 참이었다
    if ((메모리여유GB) -lt $필요GB) {
        적기 ("🛑 [메모리] {0}분 기다려도 여유 {1} GB — {2} GB 가 안 된다. 이 판은 돌지 않는다" -f
              $ㅁ, (메모리여유GB), $필요GB)
        exit 1
    }
}
# ⚠️ 메모리 — 판 하나가 24GB 다. 앞줄이 끝나고 커밋이 돌아온 뒤에만 시작한다
$앞파일 = "data\_labs\2026-09-29_B141_실전바탕_섹터캡_전력원전.txt"
function 앞줄끝났나 {
    # ⚠️ 2026-09-29 밤 — 결과 파일은 판이 **시작할 때** 생긴다 → 앞 판과 같이 뜰 수 있었다.
    #    앞 큐 로그의 「끝 =====」 줄로 본다
    $앞로그 = @(Get-ChildItem "run-logs\queue_b155_*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1)
    if ($앞로그.Count -eq 0) { return $false }
    if (-not (Select-String -Path $앞로그[0].FullName -Pattern "queue_b155 끝 =====" -Quiet)) { return $false }
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
적기 "[0] 앞줄(B155)이 끝났나 본다 — 이미 끝났으면 바로 간다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 2880)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
# ⭐ 2026-09-29 (사용자 「B142은 메모리 괜찮을 때 바로 돌려」) — 720분(12시간)까지 기다린다
메모리관문 18 720
메모리적기 "판 시작 전"
if (Test-Path $멈춤깃발) {
    적기 "🛑 기다리는 동안 앞 판이 터졌다 — 이 판은 돌지 않는다"
    적기 "===== queue_b156 끝 ====="
    exit 0
}

적기 "[0] 실행 전 검사 (이름·거름 겹침·짝 풀기)"
$aud = & $py "scripts/audit_small_base.py" --절 "SLOTWALK" 2>&1
if ($LASTEXITCODE -ne 0) { 적기 "❌ 소형 규칙 오염 조사에서 걸렸다 — 판을 안 띄운다"; $aud | Select-Object -Last 8 | ForEach-Object { 적기 "    $_" }; exit 1 }
적기 "[0] 소형 규칙 오염 조사 통과"
$chk = & $py "scripts\check_lab_ready.py" 2>&1
$chk | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
if ($LASTEXITCODE -ne 0) { 적기 "❌ 실행 전 검사에서 걸렸다 — 판을 띄우지 않는다"; exit 1 }
적기 "[B156] SLOTWALK — 하루 최대 6→8·10 앞뒤 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:ONLY = "SLOTWALK"

$env:LAB_OUT = "2026-09-30_B156_하루최대_앞뒤.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [B156] 터졌다: $($_.Exception.Message)" }
foreach ($k in "TIMEMAP", "TIMEMAP", "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "VANISH_KIND", "OPENFIN", "SIZE_LO", "SIZE_HI2", "LAB_OUT", "ONLY", "RULE_HI") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-30_B156_하루최대_앞뒤.txt"
if (Test-Path $밖) { 적기 "[B156] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [B156] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
# ⭐ 2026-09-24 — 제 로그를 제가 읽는다. 터졌으면 깃발을 세워 **뒤 판을 멈춘다**
$끝줄 = @(Get-Content $log -Tail 40 -ErrorAction SilentlyContinue)
$터짐 = @($끝줄 | Where-Object { $_ -match "Traceback|[A-Za-z]+Error|터졌다" })
if ($터짐.Count -gt 0) {
    $쪽지 = "B156 이 터졌다 ($(Get-Date -f 'MM-dd HH:mm')) — " + ($터짐[-1])
    Set-Content -Path "data\_labs\_STOP.txt" -Value $쪽지 -Encoding UTF8
    적기 "🛑 이 판이 터졌다 — 멈춤 깃발을 세웠다 (뒤 판은 안 돈다)"
    적기 "   $($터짐[-1])"
}
적기 "===== queue_b156 끝 ====="
