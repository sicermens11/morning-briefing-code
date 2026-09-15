# ==============================================================
#  after_labs2.ps1 — 판이 끝나면 **반등 시험 → 성적표·빈도 → 검사** (2026-09-15)
#
#  줄
#  ---
#   1 반등 시험   세 AI 가 공통으로 말한 「반등이 시작된 뒤 산다」를 직접 잰다
#   2 대금 하한   1억 → 2·3·5·10억 (114차는 **옛 규칙**이라 다시 잰다)
#   3 성적표      후보수 120 을 반영해 rule-cases.json 을 다시 만든다
#   4 빈도        how_often 도 같이
#   5 검사        rule_align 으로 **진짜 맞아졌나** 본다 — 「돌렸다」로 끝내지 않는다
#
#  ⚠️ 지금 R3 판이 **21.2GB** 를 쓰고 여유가 1.2GB 다. 하나씩, 앞이 끝나야 다음.
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\after2_$(Get-Date -f yyyyMMdd_HHmm).log"
# ⚠️ `Tee-Object` 는 PS 5.1 에서 UTF-16LE 로 쓴다 — grep 이 한글을 못 맞춘다
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
function 기다리기 {
    $분 = 0
    while ((큰파이썬) -gt 0 -and ($분 -lt 480)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
    적기 "   ($분 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"
}
function 돌리기($이름, $스크립트, $밖) {
    기다리기
    if (아침인가) { 적기 "⚠️ [$이름] 아침 시간대 — 시작하지 않는다"; return }
    적기 "[$이름] 시작"
    try {
        if ($밖) {
            & $py $스크립트 2>&1 | Tee-Object -Variable 나옴 | Out-Null
            $나옴 | Out-File -FilePath $밖 -Encoding utf8
            적기 "   → $밖"
            $나옴 | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
        }
        else {
            & $py $스크립트 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
        }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    Start-Sleep -Seconds 30
}

적기 "===== 반등 시험 → 성적표·빈도 → 검사 ====="
돌리기 "반등 시험" "scripts\rebound_lab.py" "data\_labs\2026-09-15_반등진입.txt"
돌리기 "성적표" "scripts\build_rule_cases.py" $null
돌리기 "빈도" "scripts\how_often.py" $null

기다리기
적기 "[검사] rule_align — 후보수 120 이 산출물까지 닿았나"
& $py "scripts\rule_align.py" 2>&1 | Select-Object -Last 10 | ForEach-Object { 적기 "    $_" }
적기 "===== 끝 ====="
