# ==============================================================
#  queue_w.ps1 — **분할 매수를 자본 시뮬로** (2026-09-15)
#
#  왜
#  ---
#  반등2 판(이길 확률)에서 가격 분할이 셌다:
#      지금 (한 번에 100%)         61.2%  +5.58   산 것 25,690
#      가격 50:50 · -5% 더 빠지면  **66.9%**  **+7.51**   25,690  마저삼 41%
#  **기회를 하나도 안 버리고** 이김 +5.7%p · 평균 +35%.
#  그런데 「마저삼 41%」 = 59% 는 **절반만 샀다**(자산의 10%).
#  **자본 효율은 이길 확률로 안 드러난다** — 돈으로 확인한다.
#
#  ⚠️ **양 끝을 같이 잰다** — 평균 단가는 정확한데 「절반만 샀다」가 주수로는
#     안 드러난다. 비중 20%(낙관)와 10%(비관)를 나란히 본다. 실제는 그 사이다.
#     **낙관이 지금보다 못하면 볼 것도 없고, 비관이 나으면 확실하다.**
#
#  ⚠️ 앞줄(queue_z · 반등3)이 끝나길 기다린다
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_w_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_z_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_z 끝')
}

적기 "[0] 앞줄(queue_z · 반등3)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[Z_분할자본] 분할 매수를 **자본 시뮬**로 (낙관·비관 양 끝) - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:LAB_OUT = "2026-09-15_Z_분할자본.txt"
try {
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [Z_분할자본] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "LAB_OUT") {
    Remove-Item "env:$k" -ErrorAction SilentlyContinue
}
$밖 = Join-Path "data\_labs" "2026-09-15_Z_분할자본.txt"
if (Test-Path $밖) { 적기 "[Z_분할자본] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [Z_분할자본] 결과 파일이 없다" }
적기 "===== queue_w 끝 ====="
