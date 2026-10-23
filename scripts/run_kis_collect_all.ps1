# run_kis_collect_all.ps1 — 한국투자증권 재료를 **전 종목**으로 넓혀 받는다 (2026-10-23 · 조회만)
#   사용자 10/23 「실전 열쇠를 일주일 두는 건 문제가 아니야. 전종목을 받고 테스트가 의미가 있으면 실전 열쇠는 계속 있어도 상관없어」
#   왜: 후보가 났던 973종목만으로 독립 규칙을 찾으면 「나중에 후보가 될 종목」 을 미리 고른 셈(미래를 본다)
#   차례: ① 지금 도는 대차+의견 끝 기다림 → ② 신용공매도+대차 (전 종목 · 약 47시간) → ③ 시장투자자+투자자+프로그램+체결량 (전 종목 · 약 100시간)
#   같은 열쇠로 6개를 동시에 돌리면 초당 한도(10/22) → 앞 3조각이 다 끝나야 다음 3조각
#   대신하는 것: run_kis_collect_next.ps1(후보 종목만 ③) — 이 스크립트를 띄울 때 그것은 멈춘다
$root = Split-Path -Parent $PSScriptRoot
$log = "$root\data\_kis_collect.log"
function 적기($s) { try { Add-Content -Path $log -Value "$(Get-Date -f 'MM-dd HH:mm:ss')  $s" -Encoding UTF8 -ErrorAction Stop } catch { } }
function 도는수 { @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "collect_kis_hist" }).Count }
function 차례($종류) {
    while ((도는수) -gt 0) { Start-Sleep 60 }
    적기 "  (전 종목) $종류 — 시작"
    $env:KIS_ALL = "1"
    & "$root\scripts\run_kis_collect.ps1" $종류
    Start-Sleep 120
    while ((도는수) -gt 0) { Start-Sleep 60 }
    적기 "  (전 종목) $종류 — 끝"
}
차례 "신용공매도+대차"
차례 "시장투자자+투자자+프로그램+체결량"
적기 "  (전 종목) 다 받음"
