# ==============================================================
#  queue_next.ps1 — `queue_now` 뒤에 **안 걸려 있던 것**을 잇는다 (2026-09-15)
#
#  왜
#  ---
#  사용자: 「밤새 테스트 멈춘거, 9월15일 테스트 논의한거 **그럼 다 테스트 걸린거야?**」
#  맞춰 보니 **다섯이 안 걸려 있었다.** 특히 거래대금 하한은
#  「같은 줄에 넣겠다」고 말해 놓고 `after_labs2.ps1` **주석에만** 적고
#  코드엔 안 넣었다(그 스크립트마저 죽었다). [[claim-full-coverage-only-after-diff]]
#
#  줄
#  ---
#   1 V  **거래대금 하한** 1·2·3·5·10억   (세 AI 공통 지적 · 114차는 옛 규칙이었다)
#        ⭐ 3억은 **돈도 늘고 낙폭도 얕아지는** 유일한 후보였다 — 다른 건 전부 맞바꿈
#   2 W  **새 재료 셋** (combo4 · 10.4년)
#        ⭐ 뉴스평소배   「평소의 몇 배」 — 절대 수로는 큰 회사와 구별이 안 된다
#        ⭐ 목표주가변화 · 투자의견변화  수준이 아니라 **변화** (덮는 범위 24%)
#        ⭐ 뉴스 낱말 13·12개 -> 38·38개로 넓힘
#   3 W2 같은 것을 **최근 2년**으로 (컨센서스·뉴스가 최근에만 있다)
#
#  ⚠️ `queue_now` 가 끝나길 기다린다 — 줄이 겹치면 램이 터진다.
#     오늘 아침에 줄 셋이 같이 깨어나 그 꼴을 봤다
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_next_$(Get-Date -f yyyyMMdd_HHmm).log"
# ⚠️ `Tee-Object` 는 PS 5.1 에서 UTF-16LE 로 쓴다 — grep 이 한글을 못 맞춘다
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
    $l = Get-ChildItem "run-logs\queue_now_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match '===== 끝 =====')
}

function 판돌리기($이름, $설명, $스크립트, $환경, $인자, $밖, $작으면) {
    if ((Test-Path $밖) -and ((Get-Item $밖).Length -gt $작으면)) {
        적기 "[$이름] 이미 제대로 있다 — 건너뛴다"; return
    }
    $분 = 0
    while ((큰파이썬) -gt 0 -and ($분 -lt 480)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
    적기 "   ($분 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"
    if (아침인가) { 적기 "⚠️ [$이름] 아침 시간대 — 시작하지 않는다"; return }
    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = (Split-Path $밖 -Leaf)
    try {
        if ($인자) { & $py $스크립트 $인자 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
        else { & $py $스크립트 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    if (Test-Path $밖) {
        $크기 = (Get-Item $밖).Length
        적기 "[$이름] 끝 — $('{0:N0}' -f $크기) B"
        if ($크기 -lt $작으면) { 적기 "  ⚠️ $('{0:N0}' -f $작으면) B 보다 작다 — 로그를 봐라" }
    }
    else { 적기 "⚠️ [$이름] 결과 파일이 없다" }
    Start-Sleep -Seconds 45
}

적기 "[0] 앞줄(queue_now · U3·반등·분할)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"

$밑 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"
         BASE_SELL = "0.4,15,40 / 0.6,40,90"; BASE_PICKS = "120" }

판돌리기 "V_대금하한" "거래대금 하한 1·2·3·5·10억 (세 AI 지적)" `
         "scripts\gate7_lab.py" $밑 $null "data\_labs\2026-09-15_V_대금하한.txt" 150000
판돌리기 "W_재료각도_전체" "뉴스평소배 · 목표주가변화 · 낱말 넓힘 (10.4년)" `
         "scripts\combo4_lab.py" @{} $null "data\_labs\2026-09-15_W_재료각도_전체.txt" 18000
판돌리기 "W2_재료각도_최근2년" "같은 것을 **최근 2년**으로 (컨센서스·뉴스가 최근에만)" `
         "scripts\combo4_lab.py" @{} "--최근2년" "data\_labs\2026-09-15_W2_재료각도_최근2년.txt" 12000

적기 "===== queue_next 끝 ====="
