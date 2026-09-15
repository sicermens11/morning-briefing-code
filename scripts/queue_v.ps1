# ==============================================================
#  queue_v.ps1 — **「빠진 뒤 공시가 뜨면 산다」를 자본 시뮬로** (2026-09-15)
#
#  왜
#  ---
#  반등 판(이길 확률)에서 **유일하게 살아남았고 앞뒤 분할도 지났다**:
#                        전체      앞(2016~21)  뒤(2021~26)
#      [지금] 다음 날 시가  61.2%     63.6%       58.8%
#      장중공시            **69.9%** **75.0%**   **65.6%**   산 것 1,214
#
#  ⚠️ 그런데 **분할 매수도 ①②를 지나고 ③(자본 시뮬)에서 죽었다**(-0.2%).
#     「평균 수익은 돈이 아니다」 — 같은 함정일 수 있다. **돈으로 확인한다.**
#
#  ⚠️ **고르기는 안 건드렸다.** 묶음 열쇠를 그대로 두어 그날 중앙갭 ·
#     하루상한 · 자르기가 전부 지금과 같다. **산 날과 산 값만** 밀었다.
#     돈은 고른 날부터 묶인다 — 우리 쪽에 **불리한** 어림이다.
#
#  ⚠️ 「공시가 안 뜨면 **안 산다**」가 결과의 절반이다 —
#     **산 것이 얼마나 주는지**를 끝 자산과 같이 본다. 사용자 1순위는 **기회**다.
#
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_v_$(Get-Date -f yyyyMMdd_HHmm).log"
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
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[V_공시자본] **빠진 뒤 공시가 뜨면 산다** 를 자본 시뮬로 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:LAB_OUT = "2026-09-15_V_공시자본.txt"
try {
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [V_공시자본] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "LAB_OUT") {
    Remove-Item "env:$k" -ErrorAction SilentlyContinue
}
$밖 = Join-Path "data\_labs" "2026-09-15_V_공시자본.txt"
if (Test-Path $밖) { 적기 "[V_공시자본] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [V_공시자본] 결과 파일이 없다" }
적기 "===== queue_v 끝 ====="
