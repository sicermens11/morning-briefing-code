# ==============================================================
#  queue_big.ps1 — ㉠ **크기 문 하나만 바꾼다** (2026-09-15)
#
#  왜 다시 거나
#  ------------
#  M판(2026-09-14)을 「크기 무제한이면 낙폭 -62%」의 근거로 읽었는데,
#  M판과 Z판은 **세 가지**가 달랐다. 크기 탓으로 돌릴 수 없다:
#
#      항목        M판(크기무제한)   Z판(지금)
#      후보수         40            **120**
#      크기상한      999,999억        3,000억
#      매도         50:50          **40:60**
#
#  그래서 **Z판과 똑같이** 두고 `SIZE_HI` 하나만 999999 로 연다.
#  이러면 차이가 **크기 하나**에서만 온다.
#
#  ⚠️ SIZE_HI 는 사건 그물(①)과 규칙 안 상한(②) 을 **둘 다** 연다
#     (`_규칙크기상한` · 2026-09-14 에 묶었다)
#
#  ⚠️ 볼 곳 — 260차 절의 「Ⓗ · 규모별 잣대 · 소형만 / 크기 무제한」 두 줄.
#     SIZE_HI 를 주면 `_H` 자체가 열려 **두 줄이 또 같아진다.**
#     그러니 이 판의 **Ⓗ 기준선 자체**를 Z판 Ⓗ(2.541억 · -5.8% · 263)와 견준다
#
#  ⚠️ 램: 사건 그물이 3,000억 -> 무제한이면 사건이 크게 는다.
#     전에 램 지킴이가 이 시험을 **네 번 죽였다**. 여유를 보고 시작한다
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_big_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    Add-Content -Path $log -Value $줄 -Encoding UTF8
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -eq 8) -or ($h -eq 9 -and $m -lt 10))
}

적기 "[0] 앞선 큰 파이썬이 끝나길 기다린다"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f $여유) GB)"
if ($여유 -lt 8) { 적기 "⚠️ 램 여유가 8GB 미만 — 시작하지 않는다"; exit 0 }

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[BIG_크기만] Z판과 똑같이 두고 **SIZE_HI 만** 연다 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:LAB_OUT = "2026-09-15_BIG_크기만.txt"
try {
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [BIG_크기만] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT") {
    Remove-Item "env:$k" -ErrorAction SilentlyContinue
}
$밖 = Join-Path "data\_labs" "2026-09-15_BIG_크기만.txt"
if (Test-Path $밖) { 적기 "[BIG_크기만] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [BIG_크기만] 결과 파일이 없다" }
적기 "===== queue_big 끝 ====="
