# ==============================================================
#  queue_y.ps1 — **뉴스평소배를 1년 판에서 다시** (2026-09-15 오후)
#
#  왜 다시 도나
#  ------------
#  W판에서 **뉴스평소배↑ 40.8%** 가 나왔다. `뉴스5↑`(40.9%)와 **거의 같다** —
#  같은 것을 두 번 잰 셈이었다.
#
#  원인: 뉴스 **건수가 0 이어도** 값을 0 으로 넣었다. 그러면 대부분이 0 이라
#        오분위가 「한 곳에 몰렸다 -> 0 보다 큰가」로 갈려
#        결국 **「뉴스가 있나 없나」** 가 됐다. 「평소의 **몇 배**」라는 뜻이 죽었다.
#
#  고침: **뉴스가 있는 사건만** 값을 갖게 했다. 그 안에서 오분위가 갈리면
#        「평소의 3배」 같은 구분이 산다.
#        ⚠️ 그러면 값이 있는 사건이 10.4년 판에서 **5% 뿐**이라 30% 문턱에 걸린다 —
#           **1년 판**에서만 뜻이 산다(뉴스가 2025-09~ 1년치뿐이므로)
#
#  ⚠️ 앞줄(queue_final · X 악재매도)이 끝나길 기다린다. 줄이 겹치면 램이 터진다
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_y_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_final_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_final 끝')
}

적기 "[0] 앞줄(queue_final · X 악재매도)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 600)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[Y_뉴스평소배_1년] 뉴스가 **있는 사건 안에서** 평소의 몇 배인가 - 시작"
$밖 = Join-Path "data\_labs" "2026-09-15_Y_뉴스평소배_1년.txt"
$env:LAB_OUT = "2026-09-15_Y_뉴스평소배_1년.txt"
try {
    & $py "scripts\combo4_lab.py" "--최근1년" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [Y] 터졌다: $($_.Exception.Message)" }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
if (Test-Path $밖) { 적기 "[Y_뉴스평소배_1년] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [Y] 결과 파일이 없다" }
적기 "===== queue_y 끝 ====="
