# ==============================================================
#  밤 판 둘 — 후보 **80** · **120** (㉯ + 매도 40:60 바탕) (2026-09-14 밤)
#
#  왜
#  ---
#  L판 261차 A절(제약없음): 40개 36.5억 · 60개 82.6억 · 80개 146.9억(−5.6%) · 120개 284억(−6.6%)
#  60 은 4관문을 지나 오늘 저녁 실전에 넣었다. 80·120 은 **A절만** 봤다.
#  사용자 원칙 1번이 「기회」다 — 더 넓혀도 낙폭이 −10% 안이면 기회를 더 잡는다.
#  판정은 오차 ±0.5 포함 낙폭(264차 D)으로.
#
#      BASE_GAP=표본만+실전표본  BASE_RELGAP=-3.5  BASE_SELL=0.4,15,40 / 0.6,40,90
#      BASE_PICKS=80  →  BASE_PICKS=120  (차례로)
#
#  ⚠️ 21:30 전에는 시작하지 않는다 (19:00 저녁 수집 · 20:30 빈칸 채우기와 안 겹치게).
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 파이썬이 크면 기다린다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_picks_wide_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}

# -- 0 . 21:30 까지 기다린다 -----------------------------------------
$시작 = Get-Date -Hour 21 -Minute 30 -Second 0
while ((Get-Date) -lt $시작) { Start-Sleep -Seconds 60 }
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 120)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] 시작 (큰 파이썬 기다림 $분 분)"

function 판($이름, $설명, $환경) {
    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = "2026-09-14_$이름.txt"
    & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    $결과 = "data\_labs\2026-09-14_$이름.txt"
    if (Test-Path $결과) { 적기 "[$이름] 끝 — $('{0:N0}' -f (Get-Item $결과).Length) B" }
    else { 적기 "⚠️ [$이름] 결과 파일이 없다" }
}

$바탕 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"; BASE_SELL = "0.4,15,40 / 0.6,40,90" }
$a = @{} + $바탕; $a["BASE_PICKS"] = "80"
판 "P_후보80_4060" "㉯ + 후보 80 + 40:60" $a
$b = @{} + $바탕; $b["BASE_PICKS"] = "120"
판 "Q_후보120_4060" "㉯ + 후보 120 + 40:60" $b
적기 "모두 끝"
