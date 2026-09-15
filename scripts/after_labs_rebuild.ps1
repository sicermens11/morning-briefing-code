# ==============================================================
#  after_labs_rebuild.ps1 — 판이 끝나면 **성적표·빈도를 다시 만든다**
#                           (2026-09-15 신설)
#
#  왜
#  ---
#  2026-09-15 에 실전 규칙을 바꿨다 (후보수 60->120 · 시장 갈래 Ⓗ->Ⓖ).
#  그런데 **성적표(rule-cases.json)와 빈도를 자동으로 다시 만드는 것이 없다.**
#  아침 브리핑도 안 만든다 — 손으로 돌려야 한다(마지막이 09-14 18:57).
#  안 만들면 `rule_align` 이 「성적표 · 규칙 문구 ❌」를 계속 뱉는다.
#
#  ⚠️ 지금 바로 못 돌린다 — R3 판이 10.7GB 를 쓰고 여유가 9.1GB 다.
#     **판이 다 끝난 뒤**에 돌린다.
#
#  ⚠️ 화면(briefing-site.html)은 **여기서 안 건드린다.**
#     오늘 08:55 판정은 **옛 규칙**으로 났다 — 화면만 새 규칙으로 바꾸면
#     판정과 어긋난다. 내일 08:02 브리핑이 새 규칙으로 다시 만든다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\rebuild_$(Get-Date -f yyyyMMdd_HHmm).log"
# ⚠️ `Tee-Object` 는 PS 5.1 에서 UTF-16LE 로 쓴다 — 감시 grep 이 한글을 못 맞춘다
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    Add-Content -Path $log -Value $줄 -Encoding UTF8
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}

적기 "[0] 판이 끝나길 기다린다 (성적표는 램을 많이 쓴다)"
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 480)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림 · 여유 램 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB"

function 돌리기($이름, $스크립트) {
    적기 "[$이름] 시작"
    try {
        & $py $스크립트 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    Start-Sleep -Seconds 30
}

돌리기 "성적표" "scripts\build_rule_cases.py"
돌리기 "빈도" "scripts\how_often.py"

# ⭐ 진짜 맞아졌나 — 검사기로 확인한다. 「돌렸다」로 끝내지 않는다
적기 "[검사] rule_align"
& $py "scripts\rule_align.py" 2>&1 | Select-Object -Last 12 | ForEach-Object { 적기 "    $_" }
적기 "===== 다시 만들기 끝 ====="
