# ==============================================================
#  queue_short.ps1 — **짧게 팔면 — 당일 단타 ~ 20일** (2026-09-15)
#
#  사용자: 「지금 규칙이 꽤나 장기적으로 … **단기적으로** 계산해볼 수도 있어?
#          그냥 **오늘 하루 단타**든 이런 식으로」
#
#  145차는 재료마다 1~90일 이길 확률을 쟀지만 ① 지금 규칙 후보로는 안 쟀고
#  ② 당일(0일)이 없고 ③ 돈으로 안 갔다. 이 판이 셋 다 한다.
#  ⚠️ 일봉뿐이라 「장중 몇 시」는 못 잰다 — 가장 짧은 것 = 시가에 사서 그날 종가/고가
#
#  SIZE_HI 없음 · VANISH_KIND 없음 (지금 기준선 그대로). 앞줄(queue_pc)이 끝나길 기다린다
#  07:20~09:10 은 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_short_$(Get-Date -f yyyyMMdd_HHmm).log"
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
function 앞줄끝났나 {
    $l = Get-ChildItem "run-logs\queue_pc_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_pc 끝')
}

적기 "[0] 앞줄(queue_pc)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[SHORT_짧게팔면] 당일 단타 ~ 20일 · ① 이김 · ③ 자본 시뮬 · 해마다 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:LAB_OUT = "2026-09-15_SHORT_짧게팔면.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [SHORT] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-15_SHORT_짧게팔면.txt"
if (Test-Path $밖) { 적기 "[SHORT] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [SHORT] 결과 파일이 없다" }
적기 "===== queue_short 끝 ====="
