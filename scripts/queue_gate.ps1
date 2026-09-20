# ==============================================================
#  queue_knob.ps1 — **㉢·㉤ 문턱을 제대로 된 지수로 다시 훑는다** (2026-09-20 일요일 판)
#
#  ## 왜
#  ㉢(지수 20일 -7% / 60일 -10%) 도 ㉤(지수 20일 변동성 ≥1.42%) 도
#  **지수 값 위에 세운 갈래**인데, 그 지수가 틀렸었다 —
#  코스닥 1,823종목(사건의 63%)이 코스피 지수로 계산됐다.
#  ⇒ 지금 문턱 넷은 **코스피만 보고 고른 값**이다.
#
#  ## 이 판이 찍는 것
#    Q-1  ㉢ 문턱 격자      지수 20일 -4 ~ -12%  x  60일 -6 ~ -16%
#    Q-2  ㉤ 문턱 격자      변동성 1.0 ~ 2.0%    x  자사주 창 3·5·10·20·60·120일
#    Q-3  변동성 분포        코스닥이 섞인 뒤 위20% 컷이 1.42 에서 얼마나 움직였나
#    Q-4  시장별 문턱        코스피 x 코스닥을 **따로** (같은 -7% 인데 넘는 날이 두 배 차이)
#    Q-5  한 시장만 사면     9/19 판에서 코스피 칸 하나만 나와 못 봤던 물음
#
#  ## 메모리
#  시험 하나가 18~23GB 를 쓴다 (전체 32GB). 앞줄이 **완전히 끝난 뒤**에만 시작한다.
#  자사주 캐시는 창이 바뀔 때마다 비운다 (창 여섯 배로 안 불어나게).
#
#  앞줄(queue_mkt2)이 끝난 뒤 · 07:20~09:10 은 시작 안 함
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_gate_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    # ⚠️ 로그를 누가 잡고 있어도 판이 멈추면 안 된다 — 적는 데 실패해도 그냥 간다
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
# ⚠️ 앞줄 판정을 **로그 글귀에서 결과 파일로** 바꿨다 (2026-09-20 00:20).
#    2026-09-19 23:08 에 내가 tail 로 로그를 잡고 있어서 앞 판의 완료 줄이 **안 써졌다**
#    (Add-Content: The process cannot access the file). 로그로 기다리면 영영 안 끝난 걸로 본다.
#    결과 파일은 시작할 때 생기므로 「파일이 있고 + 큰 파이썬이 없다」가 끝난 것이다
$앞파일 = "data\_labs\2026-09-19_MKT2_코스피코스닥.txt"
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

$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 300)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
적기 "[0] 큰 파이썬이 비기를 $ㄱ 분 더 기다렸다"
# ⚠️ **끝내지 말고 기다린다** (2026-09-19 22:35 고침)
#    앞줄(combo4)은 9시간짜리라 일요일 아침 07:20~09:10 에 끝날 공산이 크다.
#    예전처럼 exit 하면 **일요일 판이 통째로 날아간다.** 창이 지나가길 기다렸다 시작한다
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 끝내지 않고 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
if ($ㅇ -gt 0) { 적기 "[0] 아침 창을 $ㅇ 분 기다렸다" }

메모리관문 18
메모리적기 "판 시작 전"
적기 "[GATE] ㉢ 문턱 후보 넷 4관문 (Q-10) · ㉢·㉤ 문턱 다시 + 시장별 문턱 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:LAB_OUT = "2026-09-20_GATE_문턱4관문.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [KNOB] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-20_GATE_문턱4관문.txt"
if (Test-Path $밖) { 적기 "[KNOB] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [KNOB] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
적기 "===== queue_knob 끝 ====="
