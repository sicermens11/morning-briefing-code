# ==============================================================
#  retry_RSU.ps1 — R·S·U 판을 **다시** 돌린다 (2026-09-14 밤 · 메모리 두 번 고친 뒤)
#
#  무엇이 있었나
#  -------------
#  ① 20:28 R판 `MemoryError` — 조건 110개를 `set(사건 자리)` 으로 들었다.
#     set 하나 ~65MB × 110 = **7GB**.
#     ⇒ 조건을 **int 비트마스크**로 (110 × 136KB = 15MB)
#  ② 21:43 U판이 **25GB** (여유 램 1.8GB) — 고친 비트마스크를 `아래 |= 1 << i2` 로
#     만들고 있었다. 파이썬 int 는 불변이라 그 한 줄이 **136KB 짜리 int 를 새로 만든다.**
#     108만 번이면 총 140GB 를 복사하는 셈이다.
#     ⇒ `bytearray` 에 제자리로 비트를 세우고 **마지막에 한 번만** int 로
#        (실측: 100만 개 1.35초 · 피크 0.4MB · 값은 옛 방식과 같음)
#
#  그 사이 R·S·U 셋이 다 작은 파일로 죽었다 — 셋 다 다시 돌린다.
#
#  ⚠️ 밤 줄(P·Q·T)이 **다 끝난 뒤**에 시작한다 — 로그의 「모두 끝」을 기다린다.
#  ⚠️ 판 하나가 또 죽어도 다음으로 넘어간다. 07:20 을 넘기면 시작하지 않는다.
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\retry_RSU_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 밤줄끝났나 {
    $l = Get-ChildItem "run-logs\night_queue_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw) -match '밤 줄 모두 끝')
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -ge 8 -and $h -lt 10))
}

적기 "[0] 밤 줄(P·Q·T)이 끝나길 기다린다"
$분 = 0
while (-not (밤줄끝났나) -and ($분 -lt 660)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"

function 판돌리기($이름, $설명, $인자) {
    $결과 = "data\_labs\2026-09-14_$이름.txt"
    if ((Test-Path $결과) -and ((Get-Item $결과).Length -gt 50000)) {
        적기 "[$이름] 이미 제대로 있다 — 건너뛴다"; return
    }
    $ㄱ = 0
    while ((큰파이썬) -gt 0 -and ($ㄱ -lt 600)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
    if (아침인가) { 적기 "⚠️ [$이름] 아침 시간대라 시작하지 않는다"; return }
    적기 "[$이름] $설명 - 시작"
    $env:LAB_OUT = "2026-09-14_$이름.txt"
    try {
        if ($인자) { & $py "scripts\combo4_lab.py" $인자 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append }
        else { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    if (Test-Path $결과) {
        $크기 = (Get-Item $결과).Length
        적기 "[$이름] 끝 — $('{0:N0}' -f $크기) B"
        if ($크기 -lt 50000) { 적기 "  ⚠️ 또 작다 — 로그를 봐라" }
    }
    else { 적기 "⚠️ [$이름] 결과 파일이 없다" }
    Start-Sleep -Seconds 60
}

적기 "===== R·S·U 다시 (메모리 고친 뒤) ====="
판돌리기 "R_새재료_전체기간" "재료 27가지 · 단독/둘씩/셋씩 (10.4년)" $null
판돌리기 "S_새재료_최근1년" "+ 뉴스 (최근 1년)" "--최근1년"
판돌리기 "U_새재료_최근2년" "+ 배당·소액주주 (최근 2년)" "--최근2년"
적기 "===== 다시 돌리기 끝 ====="
