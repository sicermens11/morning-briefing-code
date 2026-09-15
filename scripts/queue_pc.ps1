# ==============================================================
#  queue_pc.ps1 — **종목마다 배운 규칙을 돈으로** (2026-09-15)
#
#  216차(percode_lab)는 앞 기간(~2018-04-25)에서 종목마다 규칙을 골라
#  뒤 기간 **이길 확률**만 봤다 (62.4% vs 56.7% · 72가지로 흩어짐). 돈으로는 안 갔다.
#  판이 _labs_old 에 보관돼 있었다 — scripts/ 로 되돌리고 규칙 표 저장을 붙였다.
#
#  두 단계:
#   ① percode_lab  → data/percode-rules.json  (+ 「상위 5 규칙이 종목의 몇 % 를 덮나」)
#   ② gate7_lab    → 「종목마다 배운 규칙을 돈으로」 절 · 2019~ 만 (앞 기간 밖)
#      SIZE_HI 없음 (소형만 · 빠른 판). ㉡㉢·㉤ 절은 스스로 건너뛴다
#
#  ⚠️ 앞줄(queue_combo)이 끝나길 기다린다 · 07:20~09:10 은 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_pc_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_combo_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_combo 끝')
}

적기 "[0] 앞줄(queue_combo)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 480)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }

적기 "[PC1_종목규칙표] percode_lab — 종목마다 규칙 고르고 표 저장 - 시작"
$env:LAB_OUT = "2026-09-15_PC1_종목규칙표.txt"
try { & $py "scripts\percode_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [PC1] 터졌다: $($_.Exception.Message)" }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
if (-not (Test-Path "data\percode-rules.json")) { 적기 "⚠️ 표가 안 만들어졌다 — ② 건너뜀"; 적기 "===== queue_pc 끝 ====="; exit 0 }
적기 "[PC1] 끝 — 표 $('{0:N0}' -f (Get-Item 'data\percode-rules.json').Length) B"

if (아침인가) { 적기 "⚠️ 아침 시간대 — ② 시작하지 않는다"; exit 0 }
적기 "[PC2_종목규칙돈] gate7_lab — 종목규칙 혼자 · 기존 OR · 해마다 (2019~) - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:LAB_OUT = "2026-09-15_PC2_종목규칙돈.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [PC2] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-15_PC2_종목규칙돈.txt"
if (Test-Path $밖) { 적기 "[PC2] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [PC2] 결과 파일이 없다" }
적기 "===== queue_pc 끝 ====="
