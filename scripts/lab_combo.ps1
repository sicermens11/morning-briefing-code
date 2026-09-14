# ==============================================================
#  N 판 — **셋을 합치면** (2026-09-14)
#
#  오늘 오후 넷 중 셋이 4관문(D 는 ±0.5 까지)을 지났다. 각 판은 **한 가지씩만**
#  바꿨다:
#      ㉯ 실전표본30 혼자     36.5억 · -5.4%   (H2 판)
#      후보수 40 -> 60        82.6억 · -5.1%   (L 판 · ㉯ 바탕)
#      매도 30:70            61.6억 · -8.8%   (K/K2 판 · ㉯ 바탕)
#  셋이 **겹쳐서 더 좋아지나**, 아니면 낙폭이 **-10% 를 넘나**는 안 쟀다.
#  이 판이 그것이다. 한 가지도 짐작하지 않는다.
#
#  읽을 때
#  ------
#  · 239차 A 기준선 줄이 답이다. 낙폭 -10% 를 넘으면 셋 다는 못 쓴다 —
#    그때는 L(60 만)·K2(30:70 만) 값으로 **둘 중 하나**를 고른다.
#  · 264차 C·D 는 이 합친 기준선에 걸린다.
#  · 258차 G 해마다는 이 판에선 「50:50 vs 30:70」 이라 뜻이 다르다 — 안 읽는다.
#
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 시험이 돌고 있으면 기다린다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_combo_$(Get-Date -f yyyyMMdd_HHmm).log"
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

$이름 = "N_합침_표본만_후보60_3070"
$환경 = @{
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "60"
    BASE_SELL   = "0.3,15,40 / 0.7,40,90"
}
적기 "[1] $이름 - 시작 (㉯ + 후보 60 + 매도 30:70 동시)"
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
