# run_kis_collect_next.ps1 — 대차+의견 받기가 끝나면 투자자 세부·프로그램·체결량·시장 투자자를 이어 받는다 (2026-10-23 · 조회만)
#   사용자 10/23 「재료가 받을 만큼 의미 있냐가 중요해 … 필요하면 받고 필요없으면 안 받고!」
#   같은 열쇠로 동시에 6개를 돌리면 초당 한도에 걸린다(10/22) → 앞 3조각이 다 끝날 때까지 기다린다
$root = Split-Path -Parent $PSScriptRoot
$log = "$root\data\_kis_collect.log"
function 적기($s) { Add-Content -Path $log -Value "$(Get-Date -f 'MM-dd HH:mm:ss')  $s" -Encoding UTF8 }
function 도는수 { @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "collect_kis_hist" }).Count }
적기 "  (다음 차례) 투자자+프로그램+체결량+시장투자자 — 앞 받기 끝나길 기다린다"
while ((도는수) -gt 0) { Start-Sleep 60 }
적기 "  (다음 차례) 앞 받기 끝 — 이어 받는다"
& "$root\scripts\run_kis_collect.ps1" "시장투자자+투자자+프로그램+체결량"
