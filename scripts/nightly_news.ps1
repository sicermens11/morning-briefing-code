# ==============================================================
#  nightly_news.ps1 — 밤마다 종목뉴스를 **전 종목(시총 300억↑)** 갱신한다 (2026-09-14 신설)
#
#  왜
#  ---
#  네이버 종목뉴스 API 는 약 **1년치**만 들고 있다 (2026-09-14 실측). 2010년 백필은 불가.
#  깊이를 쌓는 길은 하나 — **매일 받아 두는 것.** 1년이 2년, 3년이 된다.
#  지금 저녁 수집(19:00)은 후보 69종목만 받아서 나머지 2,200종목은 깊이가 안 쌓인다.
#
#  · 시총 300억↑ · --갱신 (있는 것에 새 기사만 덧붙임)
#  ⭐ 2026-09-28 — `--쪽 30` 고정을 **`--채움`** 으로 바꿨다.
#     저장된 마지막 날에 **닿으면 바로 멈춘다.** 두 가지를 한꺼번에 고친다:
#       ① 최신인 종목도 30쪽을 다 훑던 낭비   → 1~3쪽이면 끝 (5~10배 빠름)
#       ② 기사 많은 종목은 30쪽으로 모자라던 것 → 닿을 때까지 판다
#     실측(2026-09-28): 한미반도체 10초→1초 · 신영증권 10초→2초
#     ⚠️ 네이버는 **100쪽(2,000건)까지만** 준다 (2026-09-28 실측 · p150부터 HTTP 오류).
#        삼성전자는 하루 270건이라 100쪽 = **8일치**가 벽이다. 8일 넘게 빠지면 그만큼은 못 받는다.
#        ⇒ **매일 도는 것이 유일한 방법이다** (하루치 = 11쪽이면 충분하다)
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
& $py "scripts\collect_news.py" --시총 300 --갱신 --채움 --쪽 3 --최대쪽수 100 --쉼 0.35 2>&1 |
    Select-Object -Last 4 | Tee-Object $log -Append
"$(Get-Date -f 'MM-dd HH:mm')  ===== 끝 · 코드 $LASTEXITCODE =====" | Tee-Object $log -Append
