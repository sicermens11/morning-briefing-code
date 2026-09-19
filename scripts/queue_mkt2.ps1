# ==============================================================
#  queue_mkt2.ps1 — **버그 둘을 고친 뒤 재료 판을 다시** (2026-09-19)
#
#  ## 고친 버그 둘
#  ① 시장표가 텅 빔 — stock-base.json 의 종목이 한 겹 안에 있는데 겉을 돌았다.
#     ⇒ 코스닥 1,823종목(66%)이 **코스피 지수로** 시장낙폭·변동성을 봤다.
#     ⇒ 9/19 「시장으로 쪼개면」에 **코스피 칸 하나만** 나온 것도 이 탓이다.
#  ② E-2 문턱 조이기가 이진 재료를 못 쟀다 — 거의 다 0 이라 위 20% 컷도 0 이 되고
#     `z >= 0` 이 전 사건 546만 건을 통과시켰다. 미국선거전5·자사주직후3 이
#     20/10/5% **전부 5,464,982건**으로 똑같이 찍힌 게 그것이다.
#
#  ## 이 판에서 볼 것
#    · 코스피 / 코스닥 을 **처음으로 갈라서** 재료를 잰다 (원래 이 판의 목적이었다)
#    · 국면(오르는 장/빠지는 장/횡보)도 지수가 제대로 붙은 값으로 다시
#    · 이진 재료는 「분위수로 못 조인다」고 찍고 건너뛴다
#
#  앞줄(queue_mkt)이 끝난 뒤 · 07:20~09:10 은 시작 안 함
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_mkt2_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_mkt_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_mkt 끝')
}

적기 "[0] 앞줄(queue_mkt)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[MKT2] 코스피/코스닥 갈라서 · 국면 다시 · 이진 재료 건너뛰기 - 시작"
$env:LAB_OUT = "2026-09-19_MKT2_코스피코스닥.txt"
try { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [MKT2] 터졌다: $($_.Exception.Message)" }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
$밖 = Join-Path "data\_labs" "2026-09-19_MKT2_코스피코스닥.txt"
if (Test-Path $밖) { 적기 "[MKT2] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [MKT2] 결과 파일이 없다" }
적기 "===== queue_mkt2 끝 ====="
