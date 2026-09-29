# ==============================================================
#  queue_b152.ps1 — **무리 전용 규칙 · 업종 화학** (2026-09-29 밤 전수조사)
#  사용자: 「기존 규칙에 얹어서가 아니라 새로운 규칙을 찾는 모든 테스트를 다 했는지 체크해」
#  combo4_lab OWN — 재료 180가지 단독·쌍·셋·넷을 이 무리 안에서 · 기존 규칙 안 씀 ·
#  상대갭·자리·파는 규칙도 이 무리에서 · 낙폭 한계 −12% (사용자 9/21)
#  앞줄 B151 · 메모리 18GB 관문 · 07:20~09:10 은 기다렸다 시작
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b152_$(Get-Date -f yyyyMMdd_HHmm).log"
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
    # ⭐ 2026-09-23 — 휴장일엔 브리핑이 안 돈다. 연휴 나흘 × 1시간 50분을 그냥 버리고 있었다
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    if (-not ((($h -eq 7) -and ($m -ge 20)) -or ($h -eq 8) -or (($h -eq 9) -and ($m -lt 10)))) { return $false }
    & $py "scripts\krx_calendar.py" *> $null
    if ($LASTEXITCODE -ne 0) { return $false }   # 휴장 — 비켜 줄 이유가 없다
    return $true
}
function 메모리여유GB {
    return [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1)
}
function 메모리적기($때) {
    $o = Get-CimInstance Win32_OperatingSystem
    적기 ("[메모리] $때 — 물리 남음 {0} GB · 커밋 여유 {1} GB" -f
          [math]::Round($o.FreePhysicalMemory / 1MB, 1), [math]::Round($o.FreeVirtualMemory / 1MB, 1))
}
function 메모리관문($필요GB = 18, $최대분 = 40) {
    $ㅁ = 0
    # ⭐ 2026-09-29 — 기다리는 동안 **아침 시간대면 여유가 돼도 안 뜬다.**
    #    밤새 기다리다 07:20~09:10 에 메모리가 풀리면 브리핑과 겹쳐 뜬다. 브리핑이 먼저다
    while ((((메모리여유GB) -lt $필요GB) -or (아침인가)) -and $ㅁ -lt $최대분) {
        if ($ㅁ -eq 0) { 적기 ("[메모리] 여유 {0} GB — {1} GB 될 때까지 기다린다" -f (메모리여유GB), $필요GB) }
        Start-Sleep -Seconds 60; $ㅁ = $ㅁ + 1
    }
    if ($ㅁ -gt 0) { 적기 "[메모리] $ㅁ 분 기다렸다" }
    # ⭐⭐⭐ 2026-09-29 — **끝까지 모자라면 돌지 않는다.** 전에는 40분 기다린 뒤
    #    여유가 그대로여도 **그냥 떴다** (늦추기만 하고 막지 않았다).
    #    재부팅으로 커밋 한도가 45 -> 33.9GB 가 된 날 B142 이 여유 16.5GB 에서 뜰 참이었다
    if ((메모리여유GB) -lt $필요GB) {
        적기 ("🛑 [메모리] {0}분 기다려도 여유 {1} GB — {2} GB 가 안 된다. 이 판은 돌지 않는다" -f
              $ㅁ, (메모리여유GB), $필요GB)
        exit 1
    }
}
# ⚠️ 메모리 — 판 하나가 24GB 다. 앞줄이 끝나고 커밋이 돌아온 뒤에만 시작한다
$앞파일 = "data\_labs\2026-09-29_B151_무리전용_전기전자.txt"
function 앞줄끝났나 {
    # ⚠️ 2026-09-29 밤 — 결과 파일은 판이 **시작할 때** 생긴다. 파일만 보면 앞 판이 막 뜬 순간
    #    같이 떠서 메모리를 다툰다 (9/17 BIG7 이 BAND 와 4분 차로 떠서 조용히 죽었다).
    #    ⇒ 앞 큐 로그에 「끝 =====」 줄이 찍혔는지로 본다
    $앞로그 = @(Get-ChildItem "run-logs\queue_b151_*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1)
    if ($앞로그.Count -eq 0) { return $false }
    if (-not (Select-String -Path $앞로그[0].FullName -Pattern "queue_b151 끝 =====" -Quiet)) { return $false }
    if ((큰파이썬) -gt 0) { return $false }
    return $true
}
# ⭐ 2026-09-24 — **멈춤 깃발**. 앞 판이 터졌으면 같은 벽에 또 부딪히지 않는다
#    (12:15 에 건 다섯 판이 전부 같은 UnboundLocalError 로 죽었는데 사슬이 그냥 돌았다)
$멈춤깃발 = "data\_labs\_STOP.txt"
if (Test-Path $멈춤깃발) {
    적기 "🛑 멈춤 깃발이 있다 — 이 판은 돌지 않는다. 먼저 고치고 깃발을 지워라"
    적기 ("   " + ((Get-Content $멈춤깃발 -Raw -ErrorAction SilentlyContinue) -replace "`r`n", " "))
    적기 "===== queue_b49 비켜남 ====="
    exit 0
}
적기 "[0] 앞줄(B151)이 끝났나 본다 — 이미 끝났으면 바로 간다"
$분 = 0
while (-not (앞줄끝났나) -and ($분 -lt 2880)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림"
$ㅇ = 0
while ((아침인가) -and ($ㅇ -lt 180)) {
    if ($ㅇ -eq 0) { 적기 "[0] 아침 시간대다 — 09:10 지나가길 기다린다" }
    Start-Sleep -Seconds 60; $ㅇ = $ㅇ + 1
}
# ⭐ 2026-09-29 (사용자 「B142은 메모리 괜찮을 때 바로 돌려」) — 720분(12시간)까지 기다린다
메모리관문 18 720
메모리적기 "판 시작 전"

적기 "[B152] combo4 OWN — 업종 화학 - 시작"
$env:OWN_GROUP = "섹터=화학"
$env:OWN = "1"
$env:MAXDD = "-12"
$env:LAB_OUT = "2026-09-29_B152_무리전용_화학.txt"
try { & $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" } }
catch { 적기 "⚠️ [B152] 터졌다: $($_.Exception.Message)" }
foreach ($k in "BIG_LO", "BIG_HI", "OWN_GROUP", "OWN", "MAXDD", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$밖 = Join-Path "data\_labs" "2026-09-29_B152_무리전용_화학.txt"
if (Test-Path $밖) { 적기 "[B152] 끝 — $('{0:N0}' -f (Get-Item $밖).Length) B" } else { 적기 "⚠️ [B152] 결과 파일이 없다" }
메모리적기 "판 끝난 뒤"
# ⭐ 2026-09-24 — 제 로그를 제가 읽는다. 터졌으면 깃발을 세워 **뒤 판을 멈춘다**
$끝줄 = @(Get-Content $log -Tail 40 -ErrorAction SilentlyContinue)
$터짐 = @($끝줄 | Where-Object { $_ -match "Traceback|[A-Za-z]+Error|터졌다" })
if ($터짐.Count -gt 0) {
    $쪽지 = "B152 이 터졌다 ($(Get-Date -f 'MM-dd HH:mm')) — " + ($터짐[-1])
    Set-Content -Path "data\_labs\_STOP.txt" -Value $쪽지 -Encoding UTF8
    적기 "🛑 이 판이 터졌다 — 멈춤 깃발을 세웠다 (뒤 판은 안 돈다)"
    적기 "   $($터짐[-1])"
}
적기 "===== queue_b152 끝 ====="
