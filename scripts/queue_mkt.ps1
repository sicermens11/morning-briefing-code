# ==============================================================
#  queue_mkt.ps1 — **시장표 버그를 고친 뒤 다시 재기** (2026-09-19)
#
#  ## 무엇이 틀렸나
#  stock-base.json 은  {"받은날":.., "종목수":.., "종목":{코드:{...}}}  로 한 겹 안에 있다.
#  13개 판이 겉을 돌아 시장표가 **텅 빈 채** 돌았다 → 「닥이 들었나」가 늘 거짓
#  → **코스닥 1,823종목(전체의 66%)이 코스피 지수로** 시장낙폭·시장낙60·시장변동성을 봤다.
#
#  실전(record_pick)은 O._기본() 이 ["종목"] 을 꺼내 **제대로 보고 있었다.**
#  ⇒ 시험과 실전이 서로 다른 지수를 보고 있었다.
#
#  ## 그래서 다시 봐야 하는 것
#    ㉢ 시장 갈래   지수 20일 −7% / 60일 −10%   ← 지수 값 위에 세운 갈래
#    ㉤ 변동성·자사주  지수 20일 변동성 ≥ 1.42%    ← 역시 지수 값 위
#  둘 다 잘못된 지수로 검증됐다. 같은 판에서 ㉢ 끔 · ㉤ 끔 · 소형만(㉣ 끔) 을 나란히 찍는다.
#
#  앞줄 없음 (주말 판은 06:20 에 전부 끝났다) · 07:20~09:10 은 시작 안 함
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_mkt_$(Get-Date -f yyyyMMdd_HHmm).log"
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

$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "[0] 큰 파이썬이 비기를 $ㄱ 분 기다렸다"
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[MKT] 시장표 고친 뒤 4관문 + ㉢/㉤/㉣ 끔 견줌 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:LAB_OUT = "2026-09-19_MKT_시장표고침.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [MKT] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-19_MKT_시장표고침.txt"
if (Test-Path $밖) { 적기 "[MKT] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [MKT] 결과 파일이 없다" }
적기 "===== queue_mkt 끝 ====="
