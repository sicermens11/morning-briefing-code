# ==============================================================
#  크기 무제한 — **이번엔 진짜로** (2026-09-14)
#
#  왜 다시 도나
#  -----------
#  I2(2026-09-14 오전 · SIZE_HI=999999)가 H2 와 **한 푼도 안 달랐다.**
#  「2,000억↑ 만 → 0건」이 나와 「크기 상한은 무의미하다」로 읽을 뻔했는데,
#  코드를 보니 SIZE_HI 는 **사건 그물(①)만** 열고 있었다:
#      ② 시뮬 바깥 거름   _바탕c["시총상한"] = R.시총상한억 (2,000)   <- 안 열림
#      ③ 규칙 안          크기통과(): < R.시총상한억 (2,000)          <- 안 열림
#  `_H` 는 첫 줄에서 문통과 -> 크기통과 를 지난다. **큰 종목은 규칙에 든 적이 없다.**
#  2026-09-14 14:40 에 `_규칙크기상한`(SIZE_HI or R.시총상한억) 하나로 ②·③ 을 묶었다.
#  이 판이 **큰 종목이 처음으로 규칙을 지나는 판**이다.
#
#  바탕은 H2 와 같고 **SIZE_HI 만** 다르다:
#      BASE_GAP=표본만+실전표본  BASE_RELGAP=-3.5  BASE_PICKS=40  SIZE_HI=999999
#
#  읽을 때
#  ------
#  · 239차 B절 「2,000억↑ 만」「1조↑ 만」이 이제 **0건이 아니어야** 한다.
#    여전히 0건이면 다른 겹이 더 있다 — 그때는 코드부터 본다.
#  · 큰 종목이 들어오면 후보 40개 안에 **작은 종목을 밀어낸다**. 끝 자산·낙폭이
#    H2(1.59억·-4.5% / 36.5억·-5.4%)보다 나쁘면 상한 2,000억이 **맞는 것**이다.
#  · 관문 D 는 고친 코드다(14:30). 이 판의 D 는 믿어도 된다.
#
#  ⚠️ 한 번에 하나만 (램 9GB). 앞 시험(L_후보60)이 돌고 있으면 기다린다.
#  ⚠️ 이 스크립트는 **L_후보60 이 시작한 뒤** 건다 — 둘이 같이 기다리다 같이
#     깨어나면 9GB 둘이 겹친다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\lab_size_$(Get-Date -f yyyyMMdd_HHmm).log"
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

$이름 = "M_크기무제한"
$환경 = @{
    BASE_GAP    = "표본만+실전표본"
    BASE_RELGAP = "-3.5"
    BASE_PICKS  = "40"
    SIZE_HI     = "999999"
}
적기 "[1] $이름 - 시작 (SIZE_HI 가 규칙 안까지 닿는 첫 판)"
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
