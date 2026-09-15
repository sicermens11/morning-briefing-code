# ==============================================================
#  queue_last.ps1 — 반등·분할을 **다시** (2026-09-15 · 수정주가 버그)
#
#  왜 다시 도나
#  ------------
#  첫 판이 「20일 평균 수익 **+110%**」라는 말도 안 되는 값을 냈다.
#  `종계`(종가)는 **수정주가**(액면분할·배당 반영)인데
#  `시계`(시가)는 krx-daily **원본**을 그대로 썼다. 둘을 나누면 기준이 달라 튄다.
#  실측: 24만 개를 견주니 **54.66%** 가 2% 넘게 달랐다 — 절반 이상이 틀린 값이었다.
#  ⇒ `gate7_lab` 처럼 **비율(시/종)을 수정 종가에 곱한다**. [[suspect-data-first]]
#
#  ⚠️ 줄이 겹치면 램이 터진다 — `queue_next` 가 끝나길 기다린다.
#     오늘만 세 번 겹쳤다(아침에 셋, 11:27 에 U3 가 두 번 돌아 결과가 덮였다)
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_last_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_next_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_next 끝')
}

적기 "[0] 앞줄(queue_next · V·W·W2)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[반등2] 반등 12가지 + 분할 9가지 — **수정주가 고친 뒤** 시작"
$밖 = "data\_labs\2026-09-15_반등진입2.txt"
try {
    & $py "scripts\rebound_lab.py" 2>&1 | Tee-Object -Variable 나옴 | Out-Null
    $나옴 | Out-File -FilePath $밖 -Encoding utf8
    $나옴 | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
    적기 "[반등2] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B"
}
catch { 적기 "⚠️ [반등2] 터졌다: $($_.Exception.Message)" }
적기 "===== queue_last 끝 ====="
