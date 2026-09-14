# ==============================================================
#  후보수 40 -> 60 을 **관문 C·D** 에 (2026-09-14)
#
#  왜
#  ---
#  261차(2026-09-14_H2 판): 후보를 60개로 늘리면
#      제약있음  1.59억 -> 1.78억   낙폭 -4.5% -> -4.6%
#      제약없음  36.5억 -> 82.6억   낙폭 -5.4% -> -5.1%   (돈 2.3배 · 낙폭 개선)
#  관문 A(앞뒤 분할)  앞 +34% · 뒤 +69% · 낙폭 같거나 개선  -> **통과**
#  관문 B(해마다)     9승 2패 (진 해는 -2.1% · -0.8%)      -> **통과**
#  남은 것: C 무작위 대조 · D 오차 시뮬 — 이 둘은 264차가 **기준선**에 건다.
#  그래서 후보수 60 을 기준선으로 한 판을 돌린다.
#
#  ⚠️ 관문 D 는 2026-09-14 14:30 에 고쳤다(`시뮬(시드=)` 를 시작 자본으로 오용).
#     이 판이 **고친 D 가 처음 제대로 찍히는 판**이다.
#
#  바탕은 H2 와 같고 **후보수만** 다르다:
#      BASE_GAP=표본만+실전표본  BASE_RELGAP=-3.5  BASE_PICKS=60  <- 이것만
#
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 시험(K_30대70)이 돌고 있으면 기다린다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_picks60_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

# -- 0 . 앞 시험이 돌고 있으면 기다린다 -----------------------------
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 180)) {
    Start-Sleep -Seconds 60; $분 = $분 + 1
}
적기 "[0] $분 분 기다림"
if ((큰파이썬) -gt 0) { 적기 "⚠️ 180분을 기다려도 앞 시험이 안 끝났다 — 멈춘다"; exit 1 }

# -- 1 . 돌린다 ----------------------------------------------------
$이름 = "L_후보60"
$환경 = @{
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "60"
}
적기 "[1] $이름 - 시작 (후보수 60 · 바탕은 H2 와 같다 · 고친 D 첫 판)"
foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
$env:LAB_OUT = "2026-09-14_$이름.txt"

& $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append

foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue

$결과 = "data\_labs\2026-09-14_$이름.txt"
if (Test-Path $결과) {
    $크기 = (Get-Item $결과).Length
    적기 "[1] 끝 — $결과 ($('{0:N0}' -f $크기) B)"
    if ($크기 -lt 50000) { 적기 "⚠️ 파일이 너무 작다 — 중간에 죽었을 수 있다" }
}
else { 적기 "⚠️ 결과 파일이 없다 — 로그를 봐라" }
적기 "모두 끝"
