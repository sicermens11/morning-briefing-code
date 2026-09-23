# ==============================================================
#  queue_cases.ps1 — **규칙이 바뀌었으니 사례·빈도를 다시 만든다** (2026-09-23)
#
#  selfcheck 가 잡았다: `rule-cases.json`(09-21 17:54) 이 `record_pick.py`(09-23 09:24) 보다 낡았다.
#  9/22 의료 · 9/23 금속·운송장비 를 넣고도 화면의 「과거에 어땠나」·「며칠에 한 번」은 옛 규칙 것이다.
#  docs/규칙바뀌면.md 의 ③ 사례 · ⑤ 빈도 를 다시 만든다 (④ 자본 시뮬은 월요일 보고 뒤에).
#
#  ⚠️ 백테스트 전체를 도는 무거운 작업이다 — **판 사슬이 비었을 때만** 돈다 (큰 파이썬 0).
#  ⚠️ 게시는 안 한다. 내일 08:02 브리핑이 새 파일을 읽는다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_cases_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { }
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -eq 8) -or ($h -eq 9 -and $m -lt 10))
}
function 메모리여유GB {
    return [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1)
}

$앞파일 = "data\_labs\2026-09-25_B54_RK_손잡이넷.txt"
적기 "[0] 앞줄(B54)이 끝났나 본다 — 판이 비면 간다"
$분 = 0
while ((-not (Test-Path $앞파일) -or (큰파이썬) -gt 0) -and ($분 -lt 2880)) {
    Start-Sleep -Seconds 60; $분 = $분 + 1
}
적기 "[0] $분 분 기다림 · 메모리 여유 $(메모리여유GB) GB"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) { Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1 }

# 되돌릴 수 있게 옛 파일을 남긴다
foreach ($f in "data\rule-cases.json", "data\rule-frequency.json") {
    if (Test-Path $f) { Copy-Item $f "$f.bak-20260923" -Force }
}
적기 "[사례] build_rule_cases.py 시작 (옛 파일은 .bak-20260923 로 남겼다)"
try { & $py "scripts\build_rule_cases.py" 2>&1 | Select-Object -Last 8 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [사례] 터졌다: $($_.Exception.Message)" }
적기 "[빈도] how_often.py 시작"
try { & $py "scripts\how_often.py" 2>&1 | Select-Object -Last 8 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [빈도] 터졌다: $($_.Exception.Message)" }
foreach ($f in "data\rule-cases.json", "data\rule-frequency.json") {
    if (Test-Path $f) { 적기 "  $f — $('{0:N0}' -f (Get-Item $f).Length) B · $((Get-Item $f).LastWriteTime)" }
}
적기 "===== queue_cases 끝 ====="
