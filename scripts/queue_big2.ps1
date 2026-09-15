# ==============================================================
#  queue_big2.ps1 — ㉡㉢ **규모대마다 제 규칙 · 더하기 판정** (2026-09-15)
#
#  왜
#  ---
#  사용자: 「**대형주는 대형주 만의 규칙으로 적용해도 되지 않아?**」
#  227차가 규모대마다 **이길 확률**을 쟀고 세 구간 검증도 지났는데
#  **자본 시뮬(③)까지는 한 번도 안 갔다.**
#  유일한 돈 판(M판)은 **지금 소형주 규칙을 대형주에 얹은 것**이라 답이 아니다.
#
#  ⚠️ 앞줄(queue_big · ㉠)은 **옛 코드**로 돌고 있어 ㉡㉢ 절이 없다.
#     그 판은 「크기 문만 바꾸면 어떻게 되나」(㉠)에 답하고 끝난다.
#     이 판이 ㉠ 결과도 같이 다시 낸다 — 설정이 똑같기 때문이다.
#
#  ⚠️ `SIZE_HI=999999` 가 없으면 ㉡㉢ 절이 **스스로 건너뛴다**
#     (사건 그물이 3,000억이라 중형 위가 아예 없다)
#
#  판정 — ⚠️ **바꾸는 게 아니라 더한다**
#      기존(Ⓗ·소형) OR 중형규칙 OR 대형규칙 이 기존 혼자보다
#      ① 산 것 늘고 ② 돈 늘고 ③ 낙폭 -10% 안 — **셋 다**여야 통과
#
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_big2_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_big_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_big 끝')
}

적기 "[0] 앞줄(queue_big · ㉠ 크기문만)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 120)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 120)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f $여유) GB)"
if ($여유 -lt 8) { 적기 "⚠️ 램 여유가 8GB 미만 — 시작하지 않는다"; exit 0 }

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[BIG2_규모별제규칙] ㉡㉢ 규모대마다 제 규칙 + 더하기 판정 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:LAB_OUT = "2026-09-15_BIG2_규모별제규칙.txt"
try {
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [BIG2_규모별제규칙] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT") {
    Remove-Item "env:$k" -ErrorAction SilentlyContinue
}
$밖 = Join-Path "data\_labs" "2026-09-15_BIG2_규모별제규칙.txt"
if (Test-Path $밖) { 적기 "[BIG2_규모별제규칙] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [BIG2_규모별제규칙] 결과 파일이 없다" }
적기 "===== queue_big2 끝 ====="
