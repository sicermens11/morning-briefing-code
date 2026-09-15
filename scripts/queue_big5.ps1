# ==============================================================
#  queue_big5.ps1 — **BIG4 다시** — 그림자 버그 고침 + 연속 하한가 방어 (2026-09-15)
#
#  BIG2·3·4 가 걷기 검증 직전에 죽었다 — 루프 변수 `_시7` 이 함수 `_시7(x)` 를 덮어썼다.
#  A·B절(혼자 · 더하기)은 유효. 걷기 · 해마다 · ㉤ 대형 컨센서스는 못 돌았다 → 이 판이 낸다.
#
#  ⭐ 2023 −79% 의 진짜 범인 — **연속 하한가** (사라짐 아님):
#     BIG3(손실 0%)·BIG4(이유 가름) 둘 다 53,949,708원 · −61.9% 그대로.
#     SG증권 사태 8종목이 2023-04-24~28 에 「빠진 것」으로 39번 걸렸고 20일 뒤 −21.8%.
#     같은 종목을 다음 날 또 산다 → 4자리가 무너지는 종목으로 찬다.
#  ⇒ 방어 둘을 잰다: 「전날 하한가(−28%↓)면 안 산다」 · 「같은 종목 중복금지」 (+ 소형에도 도움 되나)
#
#  볼 것: ㉣ 「_H소형 OR 섹터규칙(크기 무제한)」 = A·B 에서 2.796억 · −5.8% · 266 (셋 다 통과) → 걷기·해마다
#  설정은 BIG4 와 같다 (SIZE_HI=999999 · VANISH_KIND=1). 앞줄(queue_short) 뒤 · 07:20~09:10 은 시작 안 함
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_big5_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_short_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_short 끝')
}

적기 "[0] 앞줄(queue_short)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
if ($여유 -lt 8) { 적기 "⚠️ 램 여유가 8GB 미만 — 시작하지 않는다"; exit 0 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[BIG5_다시] 그림자 버그 고침 · 연속 하한가 방어 · ㉣ 걷기/해마다 · ㉤ - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:VANISH_KIND = "1"
$env:LAB_OUT = "2026-09-15_BIG5_하한가방어_섹터걷기_컨센서스.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [BIG5] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "VANISH_KIND", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-15_BIG5_하한가방어_섹터걷기_컨센서스.txt"
if (Test-Path $밖) { 적기 "[BIG5] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [BIG5] 결과 파일이 없다" }
적기 "===== queue_big5 끝 ====="
