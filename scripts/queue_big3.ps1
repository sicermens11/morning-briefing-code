# ==============================================================
#  queue_big3.ps1 — ㉠-2 **「사라짐 = −50%」가 범인인가** (2026-09-15)
#
#  BIG판(크기 하나만 바꿈)이 답을 좁혔다:
#      Z판(3,000억)   Ⓗ 2.541억 · −5.8%  · 263 · 2023 낙폭 −0.0%
#      BIG판(무제한)  Ⓗ 0.539억 · −61.9% · 269 · 2023 낙폭 **−79.1%**
#  산 것이 거의 같으니(263→269) **몇 건이 자산을 날렸다.**
#  수정주가 오염은 아니었다(why2023b · 자국 4건 전부 진짜 사건).
#
#  용의자 — `결과()` 는 보유 중 자료가 끊기면 `_사라짐` 이면 **−50%** 로 친다.
#  2023 에 사라진 2,000억↑ 12개 중 **8개가 사라지기 직전에 규칙에 걸렸다** (why2023c · 34일):
#      069110  마지막 날까지 6일 연속 · 064510·138690·015540  0~1일 전 · 메리츠증권  합병 20일 전
#  이건 합병·지주전환·공개매수라 실제로는 **이익**이었다. 소형주의 사라짐은 진짜 상장폐지라
#  −50% 가 맞지만, 대형주의 사라짐은 대부분 회사 사건이다.
#  중복금지가 없어 연속 걸린 날에 4자리가 같은 종목으로 차고 전부 −50% 가 된다.
#
#  ⇒ **POLESON=0** (폐지손실 0) 로 BIG판과 똑같이 돌린다.
#     2023 낙폭이 −79% → 한 자리수로 내려가면 **확정**. 그러면 고칠 것은 전략이 아니라
#     「사라짐」을 합병/공개매수(값 보존)와 상장폐지(−50%)로 **가르는 것**이다 (dart 공시명으로).
#  ⚠️ POLESON=0 은 **진단용**이다. 소형주 상장폐지까지 0 으로 치면 성적이 부푼다(09-08 고침의 반대).
#     이 판의 절대 숫자를 기준선으로 쓰지 않는다 — **2023 낙폭 하나**만 본다
#
#  ⚠️ 앞줄(queue_big2)이 끝나길 기다린다 · 07:20~09:10 은 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_big3_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_big2_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_big2 끝')
}

적기 "[0] 앞줄(queue_big2 · ㉡㉢)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 240)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f $여유) GB)"
if ($여유 -lt 8) { 적기 "⚠️ 램 여유가 8GB 미만 — 시작하지 않는다"; exit 0 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[BIG3_폐지손실0] BIG판과 똑같이 두고 **POLESON=0** 만 — 2023 낙폭이 사라지나 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:POLESON = "0"
$env:LAB_OUT = "2026-09-15_BIG3_폐지손실0.txt"
try {
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [BIG3_폐지손실0] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "POLESON", "LAB_OUT") {
    Remove-Item "env:$k" -ErrorAction SilentlyContinue
}
$밖 = Join-Path "data\_labs" "2026-09-15_BIG3_폐지손실0.txt"
if (Test-Path $밖) { 적기 "[BIG3_폐지손실0] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [BIG3_폐지손실0] 결과 파일이 없다" }
적기 "===== queue_big3 끝 ====="
