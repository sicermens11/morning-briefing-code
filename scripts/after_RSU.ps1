# ==============================================================
#  after_RSU.ps1 — R·S·U 가 끝난 뒤 **T2 · R2 · S2** 를 돌린다
#                  (2026-09-14 밤 신설 · 09-15 새벽 R2·S2 추가)
#
#  ① T2 — T판이 **반은 Ⓖ, 반은 Ⓗ** 였다
#  ------------------------------------
#  `BASE_RULE=G` 가 `_H` 안에만 들어 있고 여섯 곳이 `_시낙(x,60,-10)` 으로
#  박혀 있었다. 그중 하나가 하필 **`_겹친`** 이다 —
#  실전 고르는 순서가 「겹친 수 → 낙폭」이라, 갈래 정의가 어긋나면
#  **어느 종목을 사는지가 달라진다.** 「Ⓖ 규칙에 Ⓗ 순서」로 돈 셈이다.
#  23:2x 에 `_밑끝갈래` 하나로 모았다. 이제 제대로 잰다.
#
#  ② R2·S2 — 재료 이름이 **겹쳐서 하나가 사라졌다**
#  ------------------------------------------------
#  사건에는 이미 **연간** 재무에서 온 `영업이익률`·`순이익률` 이 있는데,
#  분기 재무를 **같은 이름**으로 넣었다. `x.update(값)` 이 연간 값을 덮어썼고,
#  재료 목록엔 같은 이름이 두 번 들어가 조건이 서로 덮였다.
#  오류는 안 나고 결과는 그럴듯했다 — 제일 나쁜 종류다.
#  ⇒ 분기 쪽에 「분기」를 붙였다(분기영업이익률 …). 그리고 겹치면
#     **판을 시작하기 전에 터지도록** 검사를 넣었다.
#  R판(00:10 끝)과 S판(00:11 시작)은 **옛 이름으로 돌았다** — 다시 잰다.
#  U판은 고친 뒤에 시작하므로 그대로 둔다.
#
#  규칙
#  ----
#  · retry_RSU 로그에 「다시 돌리기 끝」이 찍힐 때까지 기다린다
#  · 큰 파이썬이 남아 있으면 더 기다린다 (램이 겹치면 죽는다)
#  · 07:20 을 넘기면 **더 시작하지 않는다** — 아침 브리핑과 안 겹치게
#  · ⚠️ 크기 문턱은 판마다 다르다. `gate7_lab` 은 210KB, `combo4_lab` 은
#       20~30KB 다 (옛 163차가 19,881 B). 50KB 하나로 재면 멀쩡한 판을
#       「죽었다」고 읽는다 — 실제로 R판을 그렇게 오해했다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\after_RSU_$(Get-Date -f yyyyMMdd_HHmm).log"
# ⚠️⚠️ **`Tee-Object` 로 적으면 안 된다** (2026-09-14 밤에 당했다).
#    PowerShell 5.1 의 Tee-Object 는 `-Encoding` 이 없고 **UTF-16LE** 로 쓴다.
#    밤 줄 로그가 UTF-8 로 나온 건 그걸 띄운 껍데기가 기본값을 바꿔 놨기 때문이고,
#    이 스크립트는 그 껍데기 없이 띄워서 **혼자만 UTF-16** 이 됐다.
#    그러면 로그를 grep 하는 감시가 한글을 못 맞춘다.
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    Add-Content -Path $log -Value $줄 -Encoding UTF8
}

function RSU끝났나 {
    $l = Get-ChildItem "run-logs\retry_RSU_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $false }
    return ((Get-Content $l.FullName -Raw) -match '다시 돌리기 끝')
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

적기 "[0] R·S·U 가 끝나길 기다린다"
$분 = 0
while (-not (RSU끝났나) -and ($분 -lt 420)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"

$밑 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"
         BASE_SELL = "0.4,15,40 / 0.6,40,90"; BASE_PICKS = "60" }

# ① T2 — 밑규칙 샘 막은 뒤 다시 (gate7_lab 은 210KB 쯤 나온다)
$a = @{} + $밑; $a["BASE_RULE"] = "G"
판돌리기 "T2_규칙G_샘막은뒤" "규칙 Ⓖ — 밑규칙 샘 막은 뒤 다시" `
         "scripts\gate7_lab.py" $a $null 150000

# ② R2·S2 — 재료 이름 겹침 고친 뒤 다시 (combo4_lab 은 20~30KB 다)
판돌리기 "R2_새재료_전체기간" "재료 이름 고친 뒤 · 10.4년" `
         "scripts\combo4_lab.py" @{} $null 18000
판돌리기 "S2_새재료_최근1년" "재료 이름 고친 뒤 · 최근 1년 (뉴스)" `
         "scripts\combo4_lab.py" @{} "--최근1년" 18000

적기 "===== T2 · R2 · S2 끝 ====="
