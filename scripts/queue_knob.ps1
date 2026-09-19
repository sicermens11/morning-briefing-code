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
$log = "run-logs\queue_knob_$(Get-Date -f yyyyMMdd_HHmm).log"
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
function 앞줄끝났나 {
    if (-not (Test-Path $앞파일)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}

적기 "[0] 앞줄(queue_mkt2)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 900)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
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

적기 "[KNOB] Q-1~Q-5 · ㉢·㉤ 문턱 다시 + 시장별 문턱 - 시작"
$env:BASE_GAP = "표본만+실전표본"
$env:BASE_RELGAP = "-3.5"
$env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"
$env:SIZE_HI = "999999"
$env:LAB_OUT = "2026-09-20_KNOB_문턱다시.txt"
try { & $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [KNOB] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-20_KNOB_문턱다시.txt"
if (Test-Path $밖) { 적기 "[KNOB] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [KNOB] 결과 파일이 없다" }
적기 "===== queue_knob 끝 ====="
