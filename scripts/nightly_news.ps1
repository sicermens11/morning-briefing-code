# ==============================================================
#  nightly_news.ps1 — 밤마다 종목뉴스를 **전 종목(시총 300억↑)** 갱신한다 (2026-09-14 신설)
#
#  왜
#  ---
#  네이버 종목뉴스 API 는 약 **1년치**만 들고 있다 (2026-09-14 실측). 2010년 백필은 불가.
#  깊이를 쌓는 길은 하나 — **매일 받아 두는 것.** 1년이 2년, 3년이 된다.
#  지금 저녁 수집(19:00)은 후보 69종목만 받아서 나머지 2,200종목은 깊이가 안 쌓인다.
#
#  · 시총 300억↑ (규칙 하한과 같다) · --갱신 (있는 것에 새 기사만 덧붙임) · --쪽 30 (하루치면 충분)
#  · 0.35초 간격 · 429/403 이면 5초 쉰다. 봇 차단을 우회하지 않는다
#  · 예약: AddNightlyNews (23:30 매일) — scripts\add-nightly-news.ps1 로 등록 (관리자)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\nightly_news_$(Get-Date -f yyyyMMdd).log"
"$(Get-Date -f 'MM-dd HH:mm')  ===== 밤 종목뉴스 갱신 시작 =====" | Tee-Object $log -Append
& $py "scripts\collect_news.py" --시총 300 --갱신 --쪽 30 --쉼 0.35 2>&1 |
    Select-Object -Last 4 | Tee-Object $log -Append
"$(Get-Date -f 'MM-dd HH:mm')  ===== 끝 · 코드 $LASTEXITCODE =====" | Tee-Object $log -Append
