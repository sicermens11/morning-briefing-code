# ==============================================================
#  30:70 **다시** — 관문 B(해마다) 와 고친 D 로 (2026-09-14 · K2)
#
#  K_30대70(14:17~14:50)에서 나온 것
#  -------------------------------
#  기준선 재현  1.73억·-7.6% / 61.6억·-8.8%   (BASE_SELL 이 먹었다)
#  관문 A 앞뒤  앞 +40% (낙폭 -2.3 vs -2.5)  뒤 +19% (낙폭 -8.8 vs -5.4)  -> 통과
#              ⚠️ 그 판은 기준선이 30:70 이라 「[견줌] 50:50」 줄이 실은 30:70 이었다.
#                 「규모별 매도」 줄(= 50:50 과 동일, H2 에서 확인)로 읽었다
#  관문 C 무작위 20번 — 제일 좋았던 것 23.6억 < 61.6억               -> 통과
#  관문 B 해마다 — **258차에 재는 절이 없었다**                        -> 못 잼
#  관문 D 오차   — 옛 코드(1원 계좌 버그)                              -> 못 읽음
#
#  고친 것 (2026-09-14 오후)
#  ------------------------
#  · 258차 G 절 신설: 해마다 끝 자산, 50:50 vs 30:70 / 40:60 — **둘 다 나눔 명시**
#  · 264차 D: 시뮬(씨=) 로 잡음 씨앗을 제대로 넘긴다
#  이 판에서 B·D 가 처음 찍힌다. A·C 는 K 판 값 그대로다.
#
#  바탕은 H2 와 같고 BASE_SELL 만 30:70:
#      BASE_GAP=표본만+실전표본  BASE_RELGAP=-3.5  BASE_PICKS=40
#      BASE_SELL=0.3,15,40 / 0.7,40,90
#
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 시험(M_크기무제한)이 **시작한 뒤** 건다 —
#     둘이 같이 기다리다 같이 깨면 9GB 둘이 겹친다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_3070b_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

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

$이름 = "K2_30대70_해마다"
$환경 = @{
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "40"
    BASE_SELL   = "0.3,15,40 / 0.7,40,90"
}
적기 "[1] $이름 - 시작 (258차 G 해마다 + 고친 D · 바탕은 H2 와 같다)"
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
