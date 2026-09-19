# ==============================================================
#  queue_decide.ps1 — **내가 임의로 정한 기준이 결론을 바꾸나** (2026-09-20 일요일 · 사용자)
#
#  사용자: 「월요일 확인 목록인데 테스트 해봐야 하는 안건이면 그냥 일요일 빈자리에 돌려」
#
#  월요일에 「정해 달라」고 올렸던 셋 중 **둘이 combo4 쪽**이고, 둘 다 내가 임의로 정한 값이다.
#  정하기 전에 **「정할 필요가 있는지」**부터 잰다 — 바꿔도 결론이 같으면 정할 게 없다.
#
#    ① 띠 경계      10배씩 어림(지금) vs 종목 수 등분(285/548/971/1,935/5,330억)
#                   -> 두 방식이 같은 재료를 집으면 **정할 필요 없음**
#    ② 국면 문턱    ±3 · ±5(지금) · ±7 · ±10
#                   -> 어디로 잡아도 「빠지는 장이 제일 좋다」면 **정할 필요 없음**
#    ③ 표본 바닥    절마다 5만/2만/500 으로 달라서 「표본 부족」 칸이 절마다 다르다
#
#  (나머지 하나 「낙폭 -10% 의 근거」와 보류 중인 후보 3호는 gate7 쪽이라 KNOB 의 Q-8·Q-9 가 본다)
#
#  ## 메모리
#  combo4 는 25GB 를 쓴다 (전체 32GB). 앞줄이 **완전히 끝난 뒤**에만 시작한다.
#
#  앞줄(queue_knob)이 끝난 뒤 · 07:20~09:10 은 기다렸다 시작
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_decide_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { }
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -eq 8) -or ($h -eq 9 -and $m -lt 10))
}
# ⚠️ 앞줄 판정은 **결과 파일 크기가 멈췄나**로 본다.
#    로그 글귀로 보면 내가 tail 로 로그를 잡고 있을 때 완료 줄이 안 써져 영영 기다린다
#    (2026-09-19 23:08 에 실제로 그렇게 됐다). 파일은 시작할 때 생기므로 **크기가 안 변하면** 끝난 것이다
$앞파일 = "data\_labs\2026-09-20_KNOB_문턱다시.txt"
function 메모리여유GB {
    # ⚠️ **물리 메모리가 아니라 「커밋 여유」가 진짜 벽이다.**
    #    2026-09-20 00:19 에 물리는 1.4GB 였는데 커밋이 43.8/45.3GB 로 1.5GB 밖에 안 남았었다.
    #    커밋 한도를 넘으면 파이썬이 MemoryError 로 죽는다 (판 하나가 24~32GB 를 쓴다)
    $o = Get-CimInstance Win32_OperatingSystem
    return [math]::Round(($o.FreeVirtualMemory) / 1MB, 1)
}
function 메모리적기($때) {
    $o = Get-CimInstance Win32_OperatingSystem
    $물 = [math]::Round($o.FreePhysicalMemory / 1MB, 1)
    $커 = [math]::Round($o.FreeVirtualMemory / 1MB, 1)
    적기 ("[메모리] $때 — 물리 남음 {0} GB · 커밋 여유 {1} GB" -f $물, $커)
}
function 메모리관문($필요GB = 18) {
    # 앞 판이 끝나도 OS 가 커밋을 바로 안 놓을 수 있다. 실제로 돌아올 때까지 기다린다
    $ㅁ = 0
    while ((메모리여유GB) -lt $필요GB -and $ㅁ -lt 40) {
        if ($ㅁ -eq 0) { 적기 ("[메모리] 여유 {0} GB — {1} GB 될 때까지 기다린다" -f (메모리여유GB), $필요GB) }
        Start-Sleep -Seconds 60
        $ㅁ = $ㅁ + 1
    }
    if ($ㅁ -gt 0) { 적기 "[메모리] $ㅁ 분 기다렸다" }
    if ((메모리여유GB) -lt $필요GB) {
        적기 ("⚠️ [메모리] 40분 기다려도 여유가 {0} GB 뿐이다 — 그래도 간다 (안 도는 것보다 낫다)" -f (메모리여유GB))
    }
}

function 앞줄끝났나 {
    if (-not (Test-Path $앞파일)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}

적기 "[0] 앞줄(KNOB)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 900)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "[0] 큰 파이썬이 비기를 $ㄱ 분 더 기다렸다"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 끝내지 않고 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
if ($ㅇ -gt 0) { 적기 "[0] 아침 창을 $ㅇ 분 기다렸다" }

메모리관문 18
메모리적기 "판 시작 전"
적기 "[DECIDE] 띠 경계 · 국면 문턱 · 표본 바닥 - 시작"
$env:DECIDE = "1"
$env:LAB_OUT = "2026-09-20_DECIDE_임의기준.txt"
try { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [DECIDE] 터졌다: $($_.Exception.Message)" }
foreach ($k in "DECIDE", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-20_DECIDE_임의기준.txt"
if (Test-Path $밖) { 적기 "[DECIDE] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [DECIDE] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
적기 "===== queue_decide 끝 ====="
