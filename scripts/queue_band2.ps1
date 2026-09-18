# ==============================================================
#  queue_combo2.ps1 — **이긴 건 OR** (2026-09-15 21:30)
#
#  사용자: 「여태까지 테스트에서 벌었거나 이긴 건 OR 를 하면 기회가 많아지는 것 같은데!
#          이 얘기 처음이 아니라 몇 번 했었는데!」
#  combo4_lab 에 둘을 붙였다:
#   ① B-3 종목 분할 — 뉴스만 보던 것을 **앞 기간 표본 80 미만 재료 전부**로 (임원·대주주·ETF·분기…)
#   ② E절 — ②를 지난 쌍만 돈으로 넘기던 것에 **단독으로 바탕 +3%p 넘긴 재료** 12개를 「기존 OR 재료」로
#  전체 기간. 앞줄(없음) 뒤 · 07:20~09:10 은 시작 안 함
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_band2_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_band2_dummy_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match '없음')
}

적기 "[0] 앞줄(없음)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 720)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[BAND2_상한없이] 단독 이긴 재료 OR · 앞 0건 재료 종목 분할 - 시작"
$env:LAB_OUT = "2026-09-18_BAND2_상한없이.txt"
try { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [BAND2_상한없이] 터졌다: $($_.Exception.Message)" }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
Remove-Item env:BIG_LO -ErrorAction SilentlyContinue
$밖 = Join-Path "data\_labs" "2026-09-18_BAND2_상한없이.txt"
if (Test-Path $밖) { 적기 "[BAND2_상한없이] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [BAND2_상한없이] 결과 파일이 없다" }
적기 "===== queue_band2 끝 ====="
