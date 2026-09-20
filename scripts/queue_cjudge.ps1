# ==============================================================
#  queue_cjudge.ps1 — **combo4 도 새 잣대로** (2026-09-20 · 판정 장치 전수조사 이어서)
#
#  gate7 만 고치고 combo4 를 안 보면 전수조사가 반쪽이다. 같은 병이 있었다:
#    · 「바탕 +3%p 넘으면 좋은 재료」 — **건수를 안 봤다.**
#      500건짜리 +3%p 와 50만건짜리 +3%p 를 같이 셌다 (앞의 것은 잡음)
#    · 「앞뒤 같은 방향」 — 효과가 없어도 2분의 1 확률로 같은 방향이다
#    · 「달마다 3분의 2」 — 승패 세기, 유의성 없음
#
#  고친 것: _z(이김, 바탕, 건수) 를 넣고
#    · 띠별 표에 **z 칸**을 같이 찍는다
#    · 「바탕+3%p」 고르기에 **|z| ≥ 2** 를 AND 로 건다
#    · 달마다는 「참고로만 읽는다」고 못 박았다 (표본이 작아 t 가 안 선다)
#
#  앞줄(REJUDGE)이 끝난 뒤 · 메모리 18GB 관문 · 07:20~09:10 은 기다렸다 시작
#  ⚠️ combo4 는 25GB · 3~9시간짜리다. 월요일 아침 브리핑과 안 겹치게 아침 창을 피한다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_cjudge_$(Get-Date -f yyyyMMdd_HHmm).log"
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
function 메모리여유GB {
    return [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1)
}
function 메모리적기($때) {
    $o = Get-CimInstance Win32_OperatingSystem
    적기 ("[메모리] $때 — 물리 남음 {0} GB · 커밋 여유 {1} GB" -f
          [math]::Round($o.FreePhysicalMemory / 1MB, 1), [math]::Round($o.FreeVirtualMemory / 1MB, 1))
}
function 메모리관문($필요GB = 18) {
    $ㅁ = 0
    while ((메모리여유GB) -lt $필요GB -and $ㅁ -lt 40) {
        if ($ㅁ -eq 0) { 적기 ("[메모리] 여유 {0} GB — {1} GB 될 때까지 기다린다" -f (메모리여유GB), $필요GB) }
        Start-Sleep -Seconds 60; $ㅁ = $ㅁ + 1
    }
    if ($ㅁ -gt 0) { 적기 "[메모리] $ㅁ 분 기다렸다" }
}
$앞파일 = "data\_labs\2026-09-20_REJUDGE_새잣대.txt"
function 앞줄끝났나 {
    if (-not (Test-Path $앞파일)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}

적기 "[0] 앞줄(REJUDGE)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 420)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
메모리관문 18
메모리적기 "판 시작 전"

적기 "[CJUDGE] combo4 를 새 잣대(z)로 - 시작"
$env:DECIDE = "1"
$env:LAB_OUT = "2026-09-21_CJUDGE_combo새잣대.txt"
try { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [CJUDGE] 터졌다: $($_.Exception.Message)" }
foreach ($k in "DECIDE", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-21_CJUDGE_combo새잣대.txt"
if (Test-Path $밖) { 적기 "[CJUDGE] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [CJUDGE] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
적기 "===== queue_cjudge 끝 ====="
