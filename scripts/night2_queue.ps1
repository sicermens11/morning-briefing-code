# ==============================================================
#  night2_queue.ps1 — **고친 뒤 다시 재는 줄** (2026-09-15 새벽 신설)
#
#  왜 다시 짜나 — 새벽에 세 가지가 드러났다
#  ----------------------------------------
#  ① 재료 이름이 **겹쳤다**
#     사건엔 이미 **연간** `영업이익률`·`순이익률` 이 있는데 **분기** 재무를
#     같은 이름으로 넣어 `x.update()` 가 연간 값을 덮었다. 오류도 안 났다.
#     -> 분기 쪽에 「분기」를 붙이고, 겹치면 **판 시작 전에 터지게** 했다
#  ② `--최근N년` 이 **한 번도 안 먹었다**
#     `_a[3:-1]` 인데 `--최근` 은 **네 글자**다. 「근1」이 되고 `int()` 가 터지는데
#     `pass` 로 삼켰다. **S판(1년)도 U판(2년)도 전체 10.4년으로 돌았다.**
#     어젯밤 U판이 25GB 를 먹은 것도 이것 때문이다 — 2년인 줄 알았는데 10.4년
#  ③ `재기()` 가 109만짜리 리스트를 **넷씩** 만들었다 -> S판 MemoryError
#     -> `array("i")` + 중간 리스트 없이 바로 합산 (값은 그대로, 실측 확인)
#
#  줄 (앞이 끝나야 다음 · 07:20 넘으면 더 시작 안 한다)
#  ----------------------------------------------------
#    1 R2  재료 전체     10.4년   이름 겹침 고친 뒤
#    2 S2  + 뉴스        **진짜 1년**   ← 여태 한 번도 1년으로 안 돌았다
#    3 U2  + 배당·소액주주 **진짜 2년**   ← 여태 한 번도 2년으로 안 돌았다
#    4 T2  규칙 Ⓖ                 밑규칙 샘 막은 뒤
#
#  ⚠️ 크기 문턱은 판마다 다르다. `combo4_lab` 은 20~30KB (옛 163차 19,881 B),
#     `gate7_lab` 은 210KB 다. 50KB 하나로 재면 멀쩡한 판을 「죽었다」고 읽는다 —
#     실제로 R판을 그렇게 오해했다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\night2_$(Get-Date -f yyyyMMdd_HHmm).log"
# ⚠️ `Tee-Object` 는 PS 5.1 에서 **UTF-16LE** 로 쓴다 — 감시 grep 이 한글을 못 맞춘다
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
    return (($h -eq 7 -and $m -ge 20) -or ($h -ge 8 -and $h -lt 10))
}

function 판돌리기($이름, $설명, $스크립트, $환경, $인자, $작으면) {
    $결과 = "data\_labs\2026-09-15_$이름.txt"
    if ((Test-Path $결과) -and ((Get-Item $결과).Length -gt $작으면)) {
        적기 "[$이름] 이미 제대로 있다 — 건너뛴다"; return
    }
    $ㄱ = 0
    while ((큰파이썬) -gt 0 -and ($ㄱ -lt 240)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
    if (아침인가) { 적기 "⚠️ [$이름] 아침 시간대라 시작하지 않는다"; return }
    적기 "[$이름] $설명 - 시작"
    foreach ($k in $환경.Keys) { Set-Item "env:$k" $환경[$k] }
    $env:LAB_OUT = "2026-09-15_$이름.txt"
    try {
        if ($인자) { & $py $스크립트 $인자 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
        else { & $py $스크립트 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    foreach ($k in $환경.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    if (Test-Path $결과) {
        $크기 = (Get-Item $결과).Length
        적기 "[$이름] 끝 — $('{0:N0}' -f $크기) B"
        if ($크기 -lt $작으면) { 적기 "  ⚠️ $('{0:N0}' -f $작으면) B 보다 작다 — 로그를 봐라" }
    }
    else { 적기 "⚠️ [$이름] 결과 파일이 없다" }
    Start-Sleep -Seconds 60
}

적기 "===== 다시 재는 줄 시작 (이름 겹침 · --최근N년 · 재기 메모리 고친 뒤) ====="
적기 "[0] 앞 판(죽일 수 없던 U판)이 끝나길 기다린다"

판돌리기 "R2_새재료_전체기간" "재료 전체 · 10.4년 (이름 고친 뒤)" `
         "scripts\combo4_lab.py" @{} $null 18000
판돌리기 "S2_새재료_최근1년" "+ 뉴스 · **진짜 1년**" `
         "scripts\combo4_lab.py" @{} "--최근1년" 12000
판돌리기 "U2_새재료_최근2년" "+ 배당·소액주주 · **진짜 2년**" `
         "scripts\combo4_lab.py" @{} "--최근2년" 12000

$a = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"
        BASE_SELL = "0.4,15,40 / 0.6,40,90"; BASE_PICKS = "60"; BASE_RULE = "G" }
판돌리기 "T2_규칙G_샘막은뒤" "규칙 Ⓖ — 밑규칙 샘 막은 뒤 다시" `
         "scripts\gate7_lab.py" $a $null 150000

적기 "===== 다시 재는 줄 모두 끝 ====="
