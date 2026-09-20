# ==============================================================
#  queue_rejudge.ps1 — **새 잣대로 전부 다시 판정** (2026-09-20 · 사용자)
#
#  사용자: 「셋 넣어!」「근데 그럼 여태 4관문 테스트 했던거 다시 해야하는 거 아니야?」
#
#  ## 무엇이 바뀌었나 (docs/판정장치점검.md)
#    · 해마다를 **승패 세기 → 평균 ± 오차 · t** 로
#    · **낙폭**도 같이 본다 (전에는 돈만 봤다)
#    · 죽은 구간(±0.5 · ±1) 없앰 — 내가 고른 선이 승패를 만들었다
#    · ⬜「못 가른다」는 **기각이 아니다** — t ≤ -2 일 때만 ❌
#    · 무작위 대조 문턱 25% → 10%
#    · 판정 12곳을 함수 하나로 모았다
#
#  ## 다시 보게 되는 것
#    · ㉢ 문턱 후보 넷 — 「4승 5패 ❌」로 떨어뜨렸는데 t 는 전부 |t|<1 이었다
#    · 유상증자 거르개 — 「1승 2패 ❌」
#    · 옛 4관문 표 전체 (A·B·C)
#
#  앞줄(PAIR)이 끝난 뒤 · 메모리 18GB 관문 · 07:20~09:10 은 기다렸다 시작
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_rejudge_$(Get-Date -f yyyyMMdd_HHmm).log"
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
# ⚠️ 앞줄 판정은 **결과 파일 + 큰 파이썬 없음**으로 본다.
#    로그 글귀로 보면 로그가 잠겼을 때 영영 기다린다 (2026-09-19 23:08 에 겪었다)
$앞파일 = "data\_labs\2026-09-20_PAIR_쌍다시.txt"
function 앞줄끝났나 {
    if (-not (Test-Path $앞파일)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}

적기 "[0] 앞줄(PAIR)이 끝나길 기다린다"
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

적기 "[REJUDGE] 새 잣대(평균±오차·t·낙폭)로 전부 다시 판정 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:LAB_OUT = "2026-09-20_REJUDGE_새잣대.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [REJUDGE] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-20_REJUDGE_새잣대.txt"
if (Test-Path $밖) { 적기 "[REJUDGE] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [REJUDGE] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
적기 "===== queue_rejudge 끝 ====="
