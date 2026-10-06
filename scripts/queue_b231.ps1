# ==============================================================
#  queue_b231.ps1 — **예측 기록(끼워 넣기) → 오르는 걸 사는 규칙 찾기(추세 청산)** (2026-10-06)
#  사용자 10/6: 「우리가 빠지는 것을 산다라는 규칙이 있는데, 상승 신호를 잡는다는 것도 테스트하기로 했던거 같은데 그건 어떻게 됐어?」
#  그동안: 신고가60·20/60일선 돌파·정배열·수익률120/250↑ 같은 오르는 쪽 재료도 무리 찾기에 늘 들어갔지만
#          ① 20일 평균으로 먼저 거르고 ② 빠진 걸 산 규칙의 파는 법(+10/20 · +20/60 · 20일선 회복)으로만 쟀다 → 거의 다 떨어졌다(177개 중 0 · 207개 중 1)
#  이번: own_lab OWN_TREND — 오르는 쪽 재료가 든 조건만 · 20일 평균 문 없음 · 파는 법 = 20일선 깨지면(최대 120일) · 60일선 깨지면(최대 250일) · 견줌 +20%/60일
#  ① forward_daily 를 먼저 한 번(대기열이 다 끝나길 기다리는 예약이 오늘 못 돌 수 있어 판 사이에 끼운다)
#  ② queue_own -Which 전부 -Batch -Cut 20 -NoDD -Trend (무리 43개 · 약 15시간)
#  B229 · B230 뒤 · 판은 하나씩
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$log = "run-logs\queue_b231_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
$깃발 = "data\_labs\_STOP.txt"
적기 "[B231] B229 · B230 · B232 · B233 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b229|queue_b230|queue_b232|queue_b233|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다"; 적기 "===== queue_b231 끝 ====="; exit 1 }
적기 "[B231] ① 예측 기록 (끼워 넣기) 시작"
$env:FD_INLINE = "1"
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\forward_daily.ps1" | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
Remove-Item env:FD_INLINE -ErrorAction SilentlyContinue
적기 "[B231] ① 끝"
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — ② 안 함"; 적기 "===== queue_b231 끝 ====="; exit 1 }
적기 "[B231] ② 오르는 걸 사는 규칙 찾기 (추세 청산 · 무리 43개) 시작"
& powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut 20 -NoDD -Trend | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
적기 "[B231] ② 끝"
적기 "===== queue_b231 끝 ====="
