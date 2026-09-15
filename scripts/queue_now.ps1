# ==============================================================
#  queue_now.ps1 — **남은 것 하나의 줄로** (2026-09-15 10:40 신설)
#
#  왜 다시 짜나
#  ------------
#  줄을 셋(night3_queue · after_labs_rebuild · after_labs2)이나 걸어 뒀더니
#  R3 가 끝난 **그 순간** 셋이 같이 깨어났다. 어젯밤 `night_queue` 를 만든 이유가
#  정확히 이건데(「따로 걸면 조건이 겹친다」) **같은 실수를 반복했다.**
#  게다가 PowerShell 줄이 전부 죽어 S3 파이썬만 고아로 남았다 — U3 가 안 이어진다.
#
#  ⇒ **줄은 하나만 둔다.**
#
#  줄
#  ---
#   1 U3   + 배당·소액주주 · 진짜 2년 + 앞뒤 분할   (S3 는 이미 돌고 있다)
#   2 반등  「반등이 시작된 뒤 산다」 12가지
#           ⚠️ 10:25 에 `ValueError: too many values to unpack` 로 죽었다 —
#              `_컨센서스표` 는 **[(날짜,목표가,의견), …] 리스트**인데 3벌로 풀었다.
#              고쳤고 표 모양을 실제로 확인했다
#
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
#  ⚠️ 성적표·빈도는 **이미 다시 만들었다** (10:33 · rule_align 16항목 ✅) — 여기 없다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_now_$(Get-Date -f yyyyMMdd_HHmm).log"
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
function 판돌리기($이름, $설명, $스크립트, $인자, $밖, $작으면) {
    if ($밖 -and (Test-Path $밖) -and ((Get-Item $밖).Length -gt $작으면)) {
        적기 "[$이름] 이미 제대로 있다 — 건너뛴다"; return
    }
    $분 = 0
    while ((큰파이썬) -gt 0 -and ($분 -lt 480)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
    적기 "   ($분 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"
    if (아침인가) { 적기 "⚠️ [$이름] 아침 시간대 — 시작하지 않는다"; return }
    적기 "[$이름] $설명 - 시작"
    if ($밖) { $env:LAB_OUT = (Split-Path $밖 -Leaf) }
    try {
        if ($인자) { & $py $스크립트 $인자 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
        else { & $py $스크립트 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" } }
    }
    catch { 적기 "⚠️ [$이름] 터졌다: $($_.Exception.Message)" }
    Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
    if ($밖 -and (Test-Path $밖)) {
        $크기 = (Get-Item $밖).Length
        적기 "[$이름] 끝 — $('{0:N0}' -f $크기) B"
        if ($크기 -lt $작으면) { 적기 "  ⚠️ $('{0:N0}' -f $작으면) B 보다 작다 — 로그를 봐라" }
    }
    Start-Sleep -Seconds 45
}

적기 "===== 남은 줄 (U3 · 반등) ====="
판돌리기 "U3_새재료_최근2년_앞뒤" "+ 배당·소액주주 · 진짜 2년 + 앞뒤 분할" `
         "scripts\combo4_lab.py" "--최근2년" "data\_labs\2026-09-15_U3_새재료_최근2년_앞뒤.txt" 12000

# 반등 시험은 LAB_OUT 을 안 쓴다 — 화면으로 찍고 파일로 받는다
$분 = 0
while ((큰파이썬) -gt 0 -and ($분 -lt 480)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "   ($분 분 기다림 · 여유 $('{0:N1}' -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)) GB)"
if (아침인가) { 적기 "⚠️ [반등] 아침 시간대 — 시작하지 않는다" }
else {
    적기 "[반등] 「반등이 시작된 뒤 산다」 12가지 - 시작"
    $밖2 = "data\_labs\2026-09-15_반등진입.txt"
    try {
        & $py "scripts\rebound_lab.py" 2>&1 | Tee-Object -Variable 나옴 | Out-Null
        $나옴 | Out-File -FilePath $밖2 -Encoding utf8
        $나옴 | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
        적기 "[반등] 끝 — $('{0:N0}' -f (Get-Item $밖2).Length) B"
    }
    catch { 적기 "⚠️ [반등] 터졌다: $($_.Exception.Message)" }
}
적기 "===== 끝 ====="
