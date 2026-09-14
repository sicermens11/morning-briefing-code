# ==============================================================
#  night_queue.ps1 — 밤새 판을 **하나씩 차례로** 돌린다 (2026-09-14 밤 신설)
#
#  왜
#  ---
#  판 스크립트를 따로따로 걸었더니 「큰 파이썬 없으면 시작」 조건이 겹쳤다.
#  앞 판이 끝나는 **그 순간** 둘이 같이 깨어나면 9GB 짜리 둘이 겹쳐 램 지킴이가 죽인다.
#  ⇒ 한 스크립트가 **줄을 쥐고** 하나씩 돌린다. 사람이 없어도 알아서 굴러가게.
#
#  줄 (앞이 끝나야 다음)
#  ---------------------
#    1 R_새재료_전체기간   재료 27가지 단독·둘씩(전수)·셋씩      10.4년
#    2 S_새재료_최근1년    + 뉴스                                1년
#    3 U_새재료_최근2년    + 배당·소액주주                        2년
#    4 P_후보80_4060       후보를 80 으로 (4관문)                10.4년
#    5 Q_후보120_4060      후보를 120 으로                       10.4년
#    6 T_규칙G_…           끝 갈래를 120일선 −8%↓ 로 (Ⓖ)        10.4년
#
#  규칙
#  ----
#  · 결과 파일이 이미 있고 50KB 넘으면 **건너뛴다** (다시 돌려도 헛일 안 함)
#  · 한 판이 죽으면 **다음 판으로 넘어간다** (줄 전체가 멈추지 않게)
#  · 판 사이에 60초 쉰다 — 램이 풀릴 틈을 준다
#  · 07:20 을 넘기면 **더 시작하지 않는다** — 아침 브리핑(07:30~09:05)과 안 겹치게
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\night_queue_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}

# 아침 작업과 안 겹치게 — 07:20 넘으면 새 판을 시작하지 않는다
function 아침인가 {
    $h = (Get-Date).Hour
    $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -ge 8 -and $h -lt 10))
}

function 판돌리기($이름, $설명, $스크립트, $환경, $인자) {
    $결과 = "data\_labs\2026-09-14_$이름.txt"
    if ((Test-Path $결과) -and ((Get-Item $결과).Length -gt 50000)) {
        적기 "[$이름] 이미 있다 ($('{0:N0}' -f (Get-Item $결과).Length) B) — 건너뛴다"
        return
    }
    # 앞 판이 남아 있으면 기다린다
    $분 = 0
    while ((큰파이썬) -gt 0 -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
    if ((큰파이썬) -gt 0) { 적기 "⚠️ [$이름] 600분 기다려도 앞 판이 안 끝났다 — 건너뛴다"; return }
    if (아침인가) { 적기 "⚠️ [$이름] 아침 시간대라 시작하지 않는다 (브리핑과 겹침 방지)"; return }

    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = "2026-09-14_$이름.txt"
    try {
        if ($인자) { & $py $스크립트 $인자 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append }
        else { & $py $스크립트 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue

    if (Test-Path $결과) {
        $크기 = (Get-Item $결과).Length
        적기 "[$이름] 끝 — $('{0:N0}' -f $크기) B"
        if ($크기 -lt 50000) { 적기 "  ⚠️ 파일이 작다 — 중간에 죽었을 수 있다" }
    }
    else { 적기 "⚠️ [$이름] 결과 파일이 없다" }
    Start-Sleep -Seconds 60      # 램이 풀릴 틈
}

적기 "===== 밤 줄 시작 ====="
$바탕 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"; BASE_SELL = "0.4,15,40 / 0.6,40,90" }

판돌리기 "R_새재료_전체기간" "재료 27가지 · 단독/둘씩/셋씩 (10.4년)" "scripts\combo4_lab.py" @{} $null
판돌리기 "S_새재료_최근1년" "+ 뉴스 (최근 1년)" "scripts\combo4_lab.py" @{} "--최근1년"
판돌리기 "U_새재료_최근2년" "+ 배당·소액주주 (최근 2년)" "scripts\combo4_lab.py" @{} "--최근2년"

$a = @{} + $바탕; $a["BASE_PICKS"] = "80"
판돌리기 "P_후보80_4060" "㉯ + 후보 80 + 40:60" "scripts\gate7_lab.py" $a $null
$b = @{} + $바탕; $b["BASE_PICKS"] = "120"
판돌리기 "Q_후보120_4060" "㉯ + 후보 120 + 40:60" "scripts\gate7_lab.py" $b $null
$c = @{} + $바탕; $c["BASE_PICKS"] = "60"; $c["BASE_RULE"] = "G"
판돌리기 "T_규칙G_표본만_후보60_4060" "끝 갈래를 120일선 −8%↓ 로 (Ⓖ)" "scripts\gate7_lab.py" $c $null

적기 "===== 밤 줄 모두 끝 ====="
