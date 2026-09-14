# ==============================================================
#  헛돈 판 넷을 다시 (2026-09-14)
#
#  주말에 열 판을 돌렸는데 **넷이 헛돌았다**:
#    G  BASE_SELL 이 안 먹혔다 — `_바탕c` 에 "나눔" 이 박혀 있어서
#    H·I·J  PowerShell 이 한글을 cp949 로 넘겨 갭잣대가 깨졌고,
#           gate7_lab 이 **조용히 「후보만」으로** 떨어졌다
#
#  고친 것
#    · `_바탕c` 에서 "나눔" 뺌 -> BASE_SELL 이 먹는다
#    · 모르는 갭잣대면 **멈춘다** (조용히 안 떨어진다)
#    · [Console]::OutputEncoding = UTF8
#
#  ⚠️ 한 번에 하나만 (램 9GB) · LAB_OUT 필수 · 이미 있으면 스스로 멈춘다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
# ⚠️ 받는 쪽도 맞춘다 — PYTHONIOENCODING 은 보내는 쪽만이다 (2026-09-13 사고)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\redo_labs_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 판($이름, $설명, $환경) {
    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = "2026-09-14_$이름.txt"
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    적기 "[$이름] 끝"
}

# -- 0 . 앞 시험이 돌고 있으면 기다린다 -----------------------------
적기 "[0] 앞 시험 확인"
$분 = 0
while ((Get-Process python -ErrorAction SilentlyContinue) -and ($분 -lt 180)) {
    Start-Sleep -Seconds 60; $분 = $분 + 1
}
적기 "[0] $분 분 기다림"

# -- 1 . 토요일이 고른 기준선 (= B ㉯) ------------------------------
적기 "[1] 토요일 판을 읽는다"
$밑 = & $py "scripts\pick_base.py" "2026-09-12_*.txt" 2>&1 |
       Tee-Object $log -Append |
       Where-Object { $_ -notmatch '^#' } | Select-Object -Last 1
$밑 = "$밑".Trim()
적기 "[1] 고른 기준선: $(if ($밑) { $밑 } else { '(안 바꾼다)' })"
$바탕 = @{}
if ($밑) {
    foreach ($조각 in $밑 -split ' ') {
        if ($조각 -match '^([A-Z_]+)=(.+)$') { $바탕[$Matches[1]] = $Matches[2] }
    }
}

# -- 2 . G 다시 — 매도 기준선 (이번엔 진짜 먹는다) ------------------
적기 "[2] 매도 기준선 고르는 중"
$A판 = "data\_labs\2026-09-12_A_지금기준선.txt"
$매도 = & $py "scripts\pick_sell.py" $A판 2>&1 | Tee-Object $log -Append |
        Where-Object { $_ -notmatch '^#' } | Select-Object -Last 1
$매도 = "$매도".Trim()
if ($매도) { 판 "G2_매도기준선" "매도 = $매도" @{ BASE_SELL = $매도 } }
else { 적기 "[2] 바꿀 매도 설정이 없다" }

# -- 3 . H 다시 — 이긴 기준선 --------------------------------------
판 "H2_이긴기준선" "토요일이 고른 기준선" $바탕

# -- 4 . I 다시 — 이긴 기준선 x 크기 무제한 -------------------------
$큰 = @{} + $바탕; $큰["SIZE_HI"] = "999999"
판 "I2_이긴기준선_크기무제한" "+ 대형주까지" $큰

# -- 5 . J 다시 — 이긴 기준선 x 매도 -------------------------------
$H판 = "data\_labs\2026-09-14_H2_이긴기준선.txt"
if (Test-Path $H판) {
    $매도2 = & $py "scripts\pick_sell.py" $H판 2>&1 | Tee-Object $log -Append |
             Where-Object { $_ -notmatch '^#' } | Select-Object -Last 1
    $매도2 = "$매도2".Trim()
    if ($매도2) {
        $팔 = @{} + $바탕; $팔["BASE_SELL"] = $매도2
        판 "J2_이긴기준선_매도" "+ 매도 $매도2" $팔
    } else { 적기 "[5] 바꿀 매도 설정이 없다" }
} else { 적기 "[5] H2 결과가 없다" }

적기 "모두 끝"
