# ==============================================================
#  queue_big4.ps1 — ㉠-3 사라짐 종류 · ㉣ 섹터 무제한 · ㉤ 대형주 컨센서스 (2026-09-15)
#
#  사용자: 「예정 — 아직 코드 없음은 뭐야 어떻게 하겠다는 거야?」 → 코드를 썼고 이 판이 돈다.
#
#  한 판에 셋 (전부 SIZE_HI 가 있어야 뜻이 있다):
#   ㉠-3  VANISH_KIND=1 — 합병·공개매수로 사라진 종목은 −50% 대신 **마지막 종가에 판 것**으로.
#         vanish_kind.py 실측: 소형 상장폐지 424 vs 합병 119 · **대형 합병 24 vs 상장폐지 2**.
#         2023 용의자 6개 중 5개가 합병·공개매수(메리츠화재·증권·우리종금·오스템·…).
#         big3(POLESON=0) 가 「사라짐이 범인」을, 이 판이 「가르면 고쳐진다」를 답한다
#   ㉣    _H소형 OR 섹터규칙(크기 무제한) — 섹터규칙 6개가 시총 문 뒤라 대형주에 안 걸렸다
#   ㉤    대형주(1조↑) 빠짐 AND 컨센서스(새 리포트 20일 · 목표주가 올림). 2020~ · 기존도 2020~
#
#  ⚠️ 견줌은 **_H소형**(2,000억 문 그대로)이다. SIZE_HI 를 주면 _H 가 열려
#     BIG판의 「소형 · 견줌」 줄이 사실은 무제한이었다 — 이 판에서 고쳤다
#  ⚠️ 앞줄(queue_big3)이 끝나길 기다린다 · 07:20~09:10 은 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_big4_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_big3_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_big3 끝')
}

적기 "[0] 앞줄(queue_big3 · POLESON=0)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 360)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f $여유) GB)"
if ($여유 -lt 8) { 적기 "⚠️ 램 여유가 8GB 미만 — 시작하지 않는다"; exit 0 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[BIG4_사라짐가름] ㉠-3 VANISH_KIND=1 · ㉣ 섹터 무제한 · ㉤ 대형주 컨센서스 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:VANISH_KIND = "1"
$env:LAB_OUT = "2026-09-15_BIG4_사라짐가름_섹터_컨센서스.txt"
try {
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [BIG4] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "VANISH_KIND", "LAB_OUT") {
    Remove-Item "env:$k" -ErrorAction SilentlyContinue
}
$밖 = Join-Path "data\_labs" "2026-09-15_BIG4_사라짐가름_섹터_컨센서스.txt"
if (Test-Path $밖) { 적기 "[BIG4] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [BIG4] 결과 파일이 없다" }
적기 "===== queue_big4 끝 ====="
