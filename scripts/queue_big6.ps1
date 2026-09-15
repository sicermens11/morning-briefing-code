# ==============================================================
#  queue_big6.ps1 — **거래 기록 — 2022·2023 큰 회사 최악 거래** (2026-09-15)
#
#  BIG5: 연속 하한가 방어를 넣어도 크기 무제한 낙폭 −61.9% → −26.8% 에 그쳤다.
#  해마다(OR 큰 것 셋) 2022 −62.4% · 2023 −73.1%. 중복금지는 거의 효과 없음(−54.2%).
#  4자리 × 20% 로 한 해 −62% 면 −40% 거래가 대여섯 번 연달아야 한다 — 어느 거래인지 직접 본다.
#  gate7 시뮬(기록=) 로 거래를 모아 2022~23 최악 25건 + 2,000억↑/미만 요약을 찍는다.
#  설정은 BIG5 와 같다 (SIZE_HI · VANISH_KIND=1). 앞줄(queue_combo2) 뒤 · 07:20~09:10 은 시작 안 함
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_big6_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_combo2_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_combo2 끝')
}

적기 "[0] 앞줄(queue_combo2)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 900)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
if ($여유 -lt 8) { 적기 "⚠️ 램 여유가 8GB 미만 — 시작하지 않는다"; exit 0 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[BIG6_거래기록] 크기 무제한 거래 기록 · 2022·2023 최악 25건 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:VANISH_KIND = "1"
$env:LAB_OUT = "2026-09-15_BIG6_거래기록.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [BIG6] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "VANISH_KIND", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-15_BIG6_거래기록.txt"
if (Test-Path $밖) { 적기 "[BIG6] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [BIG6] 결과 파일이 없다" }
적기 "===== queue_big6 끝 ====="
