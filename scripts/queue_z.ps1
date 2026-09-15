# ==============================================================
#  queue_z.ps1 — 반등·분할에 **앞뒤 분할(4관문 ①)** 을 붙여 다시 (2026-09-15)
#
#  왜
#  ---
#  반등2 판에서 좋은 것 둘이 나왔다:
#      장중공시        20일 **69.9%** (지금 61.2%) · 산 것 1,214 (5%)
#      가격 분할 -5%   20일 **66.9%** (지금 61.2%) · 산 것 25,690 (**기회 그대로**)
#  그런데 **한 국면짜리일 수 있다.** R3판에서 어젯밤 상위 5개 중
#  **4개가 「앞 0건」**이었다 — 앞 절반에서 재본 적이 없는 값이었다.
#  ⇒ 사건을 반으로 갈라 **앞뒤 둘 다** 지금보다 나은지 본다.
#
#  ⚠️ 앞줄(queue_y · Y 뉴스평소배)이 끝나길 기다린다. 줄이 겹치면 램이 터진다
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_z_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_y_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_y 끝')
}

적기 "[0] 앞줄(queue_y · Y 뉴스평소배)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[반등3] 반등·분할 + **앞뒤 분할(4관문 ①)** - 시작"
$밖 = Join-Path "data\_labs" "2026-09-15_반등진입3_앞뒤.txt"
try {
    & $py "scripts\rebound_lab.py" 2>&1 | Tee-Object -Variable 나옴 | Out-Null
    $나옴 | Out-File -FilePath $밖 -Encoding utf8
    $나옴 | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
    적기 "[반등3] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B"
}
catch { 적기 "⚠️ [반등3] 터졌다: $($_.Exception.Message)" }
적기 "===== queue_z 끝 ====="
