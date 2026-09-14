# ==============================================================
#  안 써본 재료 넷 — **단독과 조합** (2026-09-14 밤 · 사용자 요청)
#
#  사용자: 「기존 규칙에 얹혀서 테스트 하는 게 아니라, **단독 재료로서의 효과**,
#          다른 재료와의 **다양한 조합**일 때 효과를 측정해야 해」
#          「어차피 뉴스 1년밖에 수집 못 하는 거라면, **1년치라도** 테스트해보는 게 좋을 것 같아」
#
#  163차(combo4_lab)가 그 틀이다 — 우리 규칙을 **안 깔고** 재료를 오분위로 잘라
#      A 하나씩 · B 둘씩(전수 378쌍) · C 셋씩
#  을 잰다. 거기에 새 재료 10가지를 더했다 (`newmat.py`):
#      공시장중 · 공시장후 · 공시건수 · 임원매수율20 · 임원매수율60
#      대주주변화60 · 뉴스5 · 뉴스20 · 뉴스호재5 · 뉴스악재5
#
#  판 둘
#  -----
#  R  **전체 기간(10.4년)**  — 공시시각 · 임원매매 · 대주주. 뉴스는 1년치뿐이라
#                            오분위에서 저절로 걸러진다(값이 30% 미만이면 건너뜀)
#  S  **최근 1년(--최근1년)** — 뉴스까지 포함. 표본이 얕으니 **참고**로만 읽는다
#
#  ⚠️ 378쌍을 훑으면 **우연히 좋은 게 나온다.** 상위는 반드시 4관문으로 넘긴다.
#  ⚠️ 한 번에 하나만 (램). 앞 판(후보 80·120)이 끝나길 기다린다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_newmat_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 300)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] 앞 판 기다림 $분 분"
if ((큰파이썬) -gt 0) { 적기 "⚠️ 300분을 기다려도 앞 판이 안 끝났다 — 멈춘다"; exit 1 }

function 판($이름, $설명, $더할인자) {
    적기 "[$이름] $설명 - 시작"
    $env:LAB_OUT = "2026-09-14_$이름.txt"
    if ($더할인자) { & $py "scripts\combo4_lab.py" $더할인자 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append }
    else { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    $결과 = "data\_labs\2026-09-14_$이름.txt"
    if (Test-Path $결과) { 적기 "[$이름] 끝 — $('{0:N0}' -f (Get-Item $결과).Length) B" }
    else { 적기 "⚠️ [$이름] 결과 파일이 없다 — 로그를 봐라" }
}

판 "R_새재료_전체기간" "공시시각·임원매매·대주주 (10.4년 · 단독/둘씩/셋씩)" $null
판 "S_새재료_최근1년" "+ 뉴스까지 (최근 1년)" "--최근1년"
적기 "모두 끝"
