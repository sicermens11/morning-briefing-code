# ==============================================================
#  N2 판 — ㉯ + 후보 60 + 매도 **40:60** (2026-09-14 저녁 · 사용자 요청)
#
#  N판(㉯ + 60 + 30:70): 149.3억 · 낙폭 -8.2% · 오차 ±0.5 에서 **-10.5%** (한계 밖)
#  60만: 82.6억 · -5.1% · ±0.5 -8.2%          <- 낙폭을 밀어 올리는 건 30:70 이다
#  ⇒ 30:70 과 50:50 사이 40:60 이면 낙폭이 어디 서나. 판정은 **오차 ±0.5 값**으로.
#
#      BASE_GAP=표본만+실전표본  BASE_RELGAP=-3.5  BASE_PICKS=60
#      BASE_SELL=0.4,15,40 / 0.6,40,90
#
#  ⚠️ 한 번에 하나만 (램 9GB). build_rule_cases 나 앞 시험이 돌면 기다린다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_4060_$(Get-Date -f yyyyMMdd_HHmm).log"
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
if ((큰파이썬) -gt 0) { 적기 "⚠️ 180분을 기다려도 앞 작업이 안 끝났다 — 멈춘다"; exit 1 }

$이름 = "N2_합침_표본만_후보60_4060"
$환경 = @{
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "60"
    BASE_SELL   = "0.4,15,40 / 0.6,40,90"
}
적기 "[1] $이름 - 시작 (㉯ + 후보 60 + 매도 40:60)"
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
