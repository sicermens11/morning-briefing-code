# ==============================================================
#  queue_news.ps1 — **뉴스는 달력을 안 기다린다** (2026-09-15)
#
#  사용자: 「**2027년 9월이면 너무 늦는데..**」 — 맞다. 내가 게을렀다.
#
#  왜 기간 분할이 안 되나
#  ---------------------
#      data/news  2,752 종목 · 2025-09-03 ~ 2026-09-15 = **정확히 1년**
#      10.4년 판에서 1년만 겹치니 앞뒤를 쪼개면 「앞 0건」이 나온다
#
#  ⭐ 그런데 **시장 상승은 이미 빠져 있다**
#  --------------------------------------
#  「강세장이라 판단 불가」는 **절대 수익**을 볼 때만 맞는 말이다.
#  이 판은 **같은 날 같은 후보 안에서** A vs B 를 견주므로
#  코스피 +58.6% 는 **양쪽에 똑같이** 들어가 저절로 상쇄된다.
#  남는 걱정은 시장이 아니라 **과적합 하나**뿐이고,
#  그건 시간이 아니라 **쪼개기**로 잡는다.
#
#  그래서 — 기간을 못 쪼개면 **종목을 쪼갠다**
#  ------------------------------------------
#      B-3  종목 분할   2,752 종목을 **무작위 반반**. 씨를 **10번** 바꾼다
#                      판정: 10번 중 **8번 이상** 양쪽 다 바탕 +5%p ⇒ ✅
#      B-4  달마다 승패  12달 중 **3분의 2 이상**을 이겨야 ⇒ ✅
#      (B-2 앞뒤 분할은 1년치라 뜻이 없다 — 그래서 B-3 을 만들었다)
#
#  ⚠️ **못 잡는 것 하나** — 「폭락장에서 신호가 **뒤집히나**」는
#     약세장 자료 없이는 못 안다. 통과해도 **비중을 크게 싣지 않는 것**으로 막는다.
#
#  ⚠️ 앞줄 둘(queue_big · queue_big2)이 끝나길 기다린다 — 램 때문이다
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_news_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    Add-Content -Path $log -Value $줄 -Encoding UTF8
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -eq 8) -or ($h -eq 9 -and $m -lt 10))
}
function 앞줄끝났나 {
    $l = Get-ChildItem "run-logs\queue_big2_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_big2 끝')
}

적기 "[0] 앞줄(queue_big2 · ㉡㉢ 규모별제규칙)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 240)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f $여유) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[NEWS_종목분할] 기간을 못 쪼개면 **종목**을 쪼갠다 - 시작"
$env:LAB_OUT = "2026-09-15_NEWS_종목분할.txt"
try {
    & $py "scripts\combo4_lab.py" "--최근1년" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [NEWS_종목분할] 터졌다: $($_.Exception.Message)" }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
$밖 = Join-Path "data\_labs" "2026-09-15_NEWS_종목분할.txt"
if (Test-Path $밖) { 적기 "[NEWS_종목분할] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [NEWS_종목분할] 결과 파일이 없다" }
적기 "===== queue_news 끝 ====="
