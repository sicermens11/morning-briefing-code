# ==============================================================
#  30:70 매도를 **4관문**에 돌린다 (2026-09-14)
#
#  왜
#  ---
#  낙폭 −10% 를 한계로 두면, 그 안에서 돈이 가장 많은 매도 설정이 **30:70**
#  이었다(제약없음 61.6억 · 낙폭 −8.8%). 지금 50:50 은 36.5억 · −5.4%.
#  J2(+40%/90일 통짜)는 126.7억이지만 낙폭 −16.0% 라 한계 밖이다.
#
#  ⚠️ 그 표는 **관문 A(전체 기간 자본 시뮬)** 하나뿐이다.
#     앞뒤 분할 · 해마다 승패 · 무작위 대조 · 오차 시뮬을 안 거쳤다.
#     **A만 통과한 걸 「통과」라 적지 않는다.**
#
#  바탕은 H2 와 똑같이 두고 **매도만** 바꾼다 — 그래야 차이가 매도 때문임이
#  분명해진다.
#      BASE_GAP=표본만+실전표본  BASE_RELGAP=-3.5  BASE_PICKS=40
#      BASE_SELL=0.3,15,40 / 0.7,40,90     <- 이것만 다르다
#
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 시험이 돌고 있으면 기다린다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
# ⚠️ 받는 쪽도 맞춘다 — PYTHONIOENCODING 은 보내는 쪽만이다 (2026-09-13 사고)
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_3070_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

# -- 0 . 앞 시험이 돌고 있으면 기다린다 -----------------------------
# ⚠️ **파이썬이면 무조건 기다리면 안 된다** — 11MB 짜리 관측기에 막혔던 적이
#    있다. 막아야 하는 건 **9GB 짜리 gate7_lab 이 둘 겹치는 것**이다
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 180)) {
    Start-Sleep -Seconds 60; $분 = $분 + 1
}
적기 "[0] $분 분 기다림"

# -- 1 . 돌린다 ----------------------------------------------------
$이름 = "K_30대70"
$환경 = @{
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "40"
    BASE_SELL   = "0.3,15,40 / 0.7,40,90"
}
적기 "[1] $이름 - 시작 (매도 30:70 · 바탕은 H2 와 같다)"
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
