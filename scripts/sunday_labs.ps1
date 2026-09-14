# ==============================================================
#  일요일 판 (2026-09-13 09:00)
#
#  ⭐ **토요일 결과를 사람이 안 봐도 이어진다.**
#     pick_base.py 가 토요일 판 일곱을 읽고 **이긴 기준선**을 뽑아,
#     그 바탕으로 다시 돈다. 이긴 게 없으면 기준선을 안 바꾼다
#
#  ⚠️ 한 번에 하나만 돌린다 (램 9GB)
#  ⚠️ LAB_OUT 은 필수 · 이미 있으면 gate7_lab 이 스스로 멈춘다
#  ⚠️ 00:00~01:30 은 수집 시각이라 비켜 간다 — **수집이 시험보다 먼저**다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
# ⚠️⚠️ **python 이 UTF-8 로 내는 한글을 PowerShell 이 cp949 로 읽는다** (2026-09-13 사고).
#    `pick_base.py` 가 낸 "표본만+실전표본" 이 "?쒕낯留??ㅼ쟾?쒕낯" 이 되어
#    gate7_lab 이 **조용히 「후보만」으로** 떨어졌고 판 셋이 헛돌았다.
#    `PYTHONIOENCODING` 은 **보내는 쪽**만 맞춘 것이다 — 받는 쪽도 맞춘다
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\sunday_labs_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 수집비키기 {
    while ($true) {
        $지금 = Get-Date
        $분 = $지금.Hour * 60 + $지금.Minute
        if (($분 -ge 1395) -or ($분 -lt 90)) {
            적기 "   수집 시각이다 - 01:30 까지 기다린다"
            Start-Sleep -Seconds 300
        } else { break }
    }
}

function 판($이름, $설명, $환경) {
    수집비키기
    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = "2026-09-13_$이름.txt"
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    적기 "[$이름] 끝"
}

# -- 0 . 앞 시험이 돌고 있으면 기다린다 -----------------------------
적기 "[0] 앞 시험 확인"
$분 = 0
while ((Get-Process python -ErrorAction SilentlyContinue) -and ($분 -lt 240)) {
    Start-Sleep -Seconds 60; $분 = $분 + 1
}
적기 "[0] $분 분 기다림"

# -- 1 . 토요일 결과에서 **이긴 기준선**을 뽑는다 -------------------
적기 "[1] 토요일 판을 읽는다"
$밑 = & $py "scripts\pick_base.py" "2026-09-12_*.txt" 2>&1 |
       Tee-Object $log -Append |
       Where-Object { $_ -notmatch '^#' } | Select-Object -Last 1
$밑 = "$밑".Trim()
적기 "[1] 고른 기준선: $(if ($밑) { $밑 } else { '(안 바꾼다)' })"

# 문자열을 환경 해시로
$바탕 = @{}
if ($밑) {
    foreach ($조각 in $밑 -split ' ') {
        if ($조각 -match '^([A-Z_]+)=(.+)$') { $바탕[$Matches[1]] = $Matches[2] }
    }
}

# -- 2 . 그 바탕으로 절 29개를 다시 --------------------------------
판 "H_이긴기준선" "토요일이 고른 기준선" $바탕

# -- 3 . 그 바탕 x 크기 무제한 -------------------------------------
$큰 = @{} + $바탕; $큰["SIZE_HI"] = "999999"
판 "I_이긴기준선_크기무제한" "+ 대형주까지" $큰

# -- 4 . 그 바탕 x 매도 기준선 -------------------------------------
적기 "[4] 매도 기준선 고르는 중"
$H판 = "data\_labs\2026-09-13_H_이긴기준선.txt"
if (Test-Path $H판) {
    $매도 = & $py "scripts\pick_sell.py" $H판 2>&1 | Tee-Object $log -Append |
            Where-Object { $_ -notmatch '^#' } | Select-Object -Last 1
    $매도 = "$매도".Trim()
    if ($매도) {
        $팔 = @{} + $바탕; $팔["BASE_SELL"] = $매도
        판 "J_이긴기준선_매도" "+ 매도 기준선 $매도" $팔
    } else { 적기 "[4] 바꿀 매도 설정이 없다 - 건너뛴다" }
} else { 적기 "[4] H판 결과가 없다 - 건너뛴다" }

# -- 5 . 뒷정리 ---------------------------------------------------
적기 "[5] 시험 대조"
& $py "scripts\check_tests.py" 2>&1 | Select-Object -Last 8 | Tee-Object $log -Append
적기 "모두 끝"
