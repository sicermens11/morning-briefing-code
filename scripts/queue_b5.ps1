# ==============================================================
#  queue_b5.ps1 — **후보 둘을 견주고 같이 켜 본다** (2026-09-22)
#
#  ## 왜 거나
#  B3·B4 에서 세 관문(셋 다 · 해마다 · 걷기)을 다 넘은 것이 **둘** 나왔다:
#    · Ⓗ OR 회전율 위20%·선물20     286,674,396원 113% · -11.7% · 341  걷기 ✅
#    · Ⓗ OR 금속·선물20+시장낙폭      266,907,317원 106% · -10.6% · 324  걷기 ✅
#
#  반영하기 전에 **같이 켰을 때**를 먼저 잰다.
#  9/21 에 ㉥ 을 먼저 반영했다가 ㉦ 과 같이 켜니 ㉥ 이 아무 일도 안 해서 되돌렸다.
#  게다가 B3·B4 표의 여러 줄이 바탕과 **한 글자도 안 달랐다** —
#  하루 3자리에 막혀 더한 것이 하나도 안 들어간 것이다.
#  둘 다 「선물20이 빠진 날」을 쓰므로 **같은 빈 날을 놓고 다툴** 공산이 크다.
#
#  ## 재는 것
#    ① Ⓗ OR 회전율   ② Ⓗ OR 금속   ③ Ⓗ OR 둘 다
#    ③ 이 ①·② 보다 나아야 둘 다 넣을 뜻이 있다.
#    ①·② 가 B3·B4 숫자로 재현 안 되면 **결론을 내지 않는다** (절이 스스로 경고한다)
#
#  앞줄 없음 · 메모리 18GB 관문 · 실행 전 검사 · 07:20~09:10 은 기다렸다 시작
#  ONLY=Q22 라 Q-19 본체(20분)와 옛 절을 건너뛴다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b5_$(Get-Date -f yyyyMMdd_HHmm).log"
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
$앞파일 = "data\_labs\2026-09-21_B4_업종별다시.txt"
function 앞줄끝났나 {
    if (-not (Test-Path $앞파일)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}
적기 "[0] 앞줄(B4)이 끝났나 본다 — 이미 끝났으면 바로 간다"
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
적기 "[B5] Q-22 후보 둘을 견주고 같이 켜 본다 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:ONLY = "Q22"
$env:LAB_OUT = "2026-09-22_B5_후보둘견주기.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [B5] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT", "ONLY") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-22_B5_후보둘견주기.txt"
if (Test-Path $밖) { 적기 "[B5] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [B5] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
적기 "===== queue_b5 끝 ====="
