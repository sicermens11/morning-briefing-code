# ==============================================================
#  queue_combo.ps1 — ㉥㉦ **②를 지난 쌍을 돈으로** (2026-09-15)
#
#  사용자: 「셋 다 지금 한다고 했으면 테스트에 반영된 거야? 왜 자꾸 반복되는 거지?」
#
#  왜
#  ---
#  W판(13:21) B-2 가 「앞뒤 둘 다 지난 것 12개」를 찍고 **거기서 끝났다.**
#  combo4_lab 에는 시뮬() 이 처음부터 있었는데 **한 번도 안 불렸다** — 길이 없었다.
#  E절을 붙여 쌍마다 「혼자 · 기존 OR 쌍」을 자본 시뮬로 넘긴다.
#  같은 판에서 B-2 를 30→200쌍, C 를 40→100쌍으로 넓힌다.
#
#  ⚠️ **전체 기간**이다 (--최근N년 없음). W판과 같은 조건이라 12쌍이 그대로 나와야 한다
#  ⚠️ 앞줄(queue_news)이 끝나길 기다린다 — 램
#  ⚠️ 07:20~09:10 은 아침 브리핑·판정 구간이라 시작하지 않는다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_combo_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    $l = Get-ChildItem "run-logs\queue_news_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $true }
    return ((Get-Content $l.FullName -Raw -Encoding UTF8) -match 'queue_news 끝')
}

적기 "[0] 앞줄(queue_news · 뉴스 종목분할)이 끝나길 기다린다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 360)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㄱ = 0
while ((큰파이썬) -gt 0 -and ($ㄱ -lt 180)) { Start-Sleep -Seconds 60; $ㄱ = $ㄱ + 1 }
$여유 = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
적기 "   (큰 파이썬 $ㄱ 분 기다림 · 여유 $('{0:N1}' -f $여유) GB)"

if (아침인가) { 적기 "⚠️ 아침 시간대 — 시작하지 않는다"; exit 0 }
적기 "[COMBO_돈으로] ②를 지난 쌍을 **③ 자본 시뮬**로 · B-2 200쌍 · C 100쌍 - 시작"
$env:LAB_OUT = "2026-09-15_COMBO_돈으로.txt"
try {
    & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 4 | ForEach-Object { 적기 "    $_" }
}
catch { 적기 "⚠️ [COMBO_돈으로] 터졌다: $($_.Exception.Message)" }
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
$밖 = Join-Path "data\_labs" "2026-09-15_COMBO_돈으로.txt"
if (Test-Path $밖) { 적기 "[COMBO_돈으로] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" }
else { 적기 "⚠️ [COMBO_돈으로] 결과 파일이 없다" }
적기 "===== queue_combo 끝 ====="
