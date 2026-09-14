# ==============================================================
#  Ⓖ 판 — **기준선 규칙을 Ⓖ 로** 바꿔 절 29개를 다시 (2026-09-14 밤 · 사용자 요청)
#
#  왜
#  ---
#  지금 실전은 Ⓗ = 기존 OR 섹터 OR 시낙7 OR **지수 60일 ≤−10%**.
#  N2 판정표에서 Ⓖ = 기존 OR 섹터 OR 시낙7 OR **120일선 −8%↓** 도 4관문을 지났는데,
#  H2 자본 시뮬을 보면
#      Ⓗ  1.59억 · 낙폭 −4.5% · 191건
#      Ⓖ  1.52억 · 낙폭 **−3.6%** · 189건    ← 돈 4%↓ · 낙폭 0.9%p 얕다
#  예전엔 **돈만** 보고 Ⓗ 를 골랐다. 지금 잣대는 「낙폭 −10% 한계」이고, 오늘 저녁
#  셋(㉯·후보60·40:60)을 넣으며 낙폭이 −4.5 → −6.2% 로 깊어졌다. 다시 볼 자리다.
#
#  같은 바탕에서 **끝 갈래만** 바꾼다 (BASE_RULE=G):
#      BASE_GAP=표본만+실전표본 · BASE_PICKS=60 · BASE_SELL=0.4,15,40 / 0.6,40,90
#  ⇒ N2(Ⓗ · 111.4억 · −6.7% · 오차±0.5 −8.9%)와 **한 줄로 견줄 수 있다**
#
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 판(R·S·후보80·120)이 끝나길 기다린다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_rule_g_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] 앞 판 기다림 $분 분"
if ((큰파이썬) -gt 0) { 적기 "⚠️ 600분을 기다려도 앞 판이 안 끝났다 — 멈춘다"; exit 1 }

$이름 = "T_규칙G_표본만_후보60_4060"
$결과 = "data\_labs\2026-09-14_$이름.txt"
if ((Test-Path $결과) -and ((Get-Item $결과).Length -gt 50000)) {
    적기 "[$이름] 이미 있다 — 건너뛴다"; exit 0
}
$환경 = @{
    BASE_RULE   = "G"
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "60"
    BASE_SELL   = "0.4,15,40 / 0.6,40,90"
}
적기 "[$이름] 시작 — 끝 갈래를 120일선 −8%↓ 로 (나머지는 N2 와 같다)"
foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
$env:LAB_OUT = "2026-09-14_$이름.txt"

& $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append

foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
if (Test-Path $결과) { 적기 "[$이름] 끝 — $('{0:N0}' -f (Get-Item $결과).Length) B" }
else { 적기 "⚠️ 결과 파일이 없다 — 로그를 봐라" }
적기 "모두 끝"
