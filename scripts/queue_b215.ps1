# ==============================================================
#  queue_b215.ps1 — **⑬ 자름 10% → 30% 를 차례로** (2026-10-02)
#  02:55 첫 걸음이 밤샘 옛 시험(18개) 사이 틈에서 시작해 겹쳤다 → 껐다.
#  ⇒ 밤샘 로그에 오늘 「===== 시험 끝 =====」 이 찍히거나 07:05 가 지나야 시작한다 · 두 판은 **한 프로세스에서 차례로**
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$log = "run-logs\queue_b215_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
$오늘 = Get-Date -f "yyyy-MM-dd"
적기 "[B215] 밤샘 옛 시험이 끝나길 기다린다"
while ($true) {
    $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*===== 시험 끝 =====" -Quiet -Encoding UTF8
    if ($끝 -or ((Get-Date).Hour -ge 7 -and (Get-Date).Minute -ge 5) -or (Get-Date).Hour -ge 8) { break }
    Start-Sleep 60
}
Start-Sleep 120   # 마지막 시험 파이썬이 다 내려가길
적기 "[B215] 밤샘 끝 확인 — 자름 10 시작"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut 10 | Out-Null
적기 "[B215] 자름 10 대기열 끝"
if (Test-Path "data\_labs\_STOP.txt") { 적기 "🛑 멈춤 깃발 — 자름 30 안 함"; 적기 "===== queue_b215 끝 ====="; exit 1 }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut 30 | Out-Null
적기 "[B215] 자름 30 대기열 끝"
적기 "===== queue_b215 끝 ====="
