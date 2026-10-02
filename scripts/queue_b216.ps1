# ==============================================================
#  queue_b216.ps1 — **무리 규칙 다시 찾기 · 계좌 낙폭 체 없이** (2026-10-02) · 자름 20 → 10 → 30 차례로
#  사용자: 「그렇다」(② 계좌 낙폭은 체가 아니라 정보) · 「어 너 권고대로 진행하자. 멈추고 다시 걸어」
#  B215(자름 10·30 · −12% 체)를 껐다 → queue_own -Batch -NoDD (own_lab MAXDD=-999 · 결과 이름 …_자름N_낙폭체없음)
#  판 사이 밤 0~7시면 밤샘 옛 시험이 끝나길 기다린다(10/2 02:55 틈에 끼어 겹쳤다)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$log = "run-logs\queue_b216_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 밤샘기다리기 {
    $h = (Get-Date).Hour
    if ($h -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B216] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*===== 시험 끝 =====" -Quiet -Encoding UTF8
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
foreach ($자름 in "20", "10", "30") {
    if (Test-Path "data\_labs\_STOP.txt") { 적기 "🛑 멈춤 깃발 — 자름 $자름 부터 안 함"; 적기 "===== queue_b216 끝 ====="; exit 1 }
    밤샘기다리기
    적기 "[B216] 자름 $자름 · 낙폭 체 없이 시작"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\queue_own.ps1" -Which 전부 -Batch -Cut $자름 -NoDD | Out-Null
    적기 "[B216] 자름 $자름 대기열 끝"
}
적기 "===== queue_b216 끝 ====="
