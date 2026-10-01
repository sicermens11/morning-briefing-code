# ==============================================================
#  queue_b214.ps1 — **⑮ 나누는 해 흔들기** (2026-10-01) · 통과 무리 규칙 20개를 앞/뒤 나누는 해 2017 · 2019 · 2021 로
#  own_lab OWN_EXPORT + OWN_SPLIT (설정 고정 · 오분위 문턱만 새 앞 기간 값) → split_shake.py 가 통과 판정
#  사용자: 「1,3,5는 너말대로 알아서해.」(⑬⑭⑮) · 「혹시 테스트 결과에서 추가로 테스트가 필요하면 허락없이 진행해.」
#  판은 하나씩 · 07:20~09:10 피함 · 여유 3GB 밑이면 끈다 · 화면 파일 안 건드림
# ==============================================================
param([switch]$Dry)
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b214_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    if (-not ((($h -eq 7) -and ($m -ge 20)) -or ($h -eq 8) -or (($h -eq 9) -and ($m -lt 10)))) { return $false }
    & $py "scripts\krx_calendar.py" *> $null
    return ($LASTEXITCODE -eq 0)
}
$깃발 = "data\_labs\_STOP.txt"
$무리들 = @(
    "규모||10000||대형1조", "규모||700|1000|소형_700_1000",
    "섹터|조선 기자재|||조선기자재", "섹터|조선 본선|||조선본선", "섹터|휴머노이드/로봇|||로봇", "섹터|바이오 CDMO|||CDMO",
    "섹터|우주/스페이스X|||우주", "섹터|해운|||해운",
    "업종|건설|||건설", "업종|비금속|||비금속", "업종|섬유·의류|||섬유의류", "업종|운송·창고|||운송창고",
    "업종|음식료·담배|||음식료", "업종|제약|||제약", "업종|종이·목재|||종이목재"
)
if ($Dry) { $무리들 | ForEach-Object { Write-Output $_ }; Write-Output "무리 $($무리들.Count)개"; exit 0 }
if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 안 돈다"; 적기 "===== queue_b214 끝 ====="; exit 1 }

function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B214] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    return (-not (((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)))
}
function 그만($s) { 적기 $s; Set-Content $깃발 "queue_b214 $s $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; 적기 "===== queue_b214 끝 ====="; exit 1 }

foreach ($해 in "2017", "2019", "2021") {
    if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발" }
    if (-not (기다리기 "나눔 $해" 20)) { 그만 "🛑 나눔 $해 12시간 기다려도 모자라다" }
    $받 = "data\_labs\multi_cand_split$해.jsonl"
    Remove-Item $받 -ErrorAction SilentlyContinue
    $칸들 = $무리들 | ForEach-Object { $z = $_.Split("|"); "{0}|{1}|{2}|{3}|2026-10-01_B214_나눔{4}_{5}.txt" -f $z[0], $z[1], $z[2], $z[3], $해, $z[4] }
    적기 "[B214] 나눔 $해 시작 (무리 $($칸들.Count)개 한 프로세스) · 여유 $(여유GB)GB"
    $env:OWN_GROUPS = ($칸들 -join ';'); $env:OWN_EXPORT = "data\_labs\multi_rules_spec.json"; $env:MAXDD = "-12"
    $env:OWN_SPLIT = "${해}0101"; $env:OWN_EXPORT_OUT = "multi_cand_split$해.jsonl"
    $env:LAB_OUT = "2026-10-01_B214_나눔${해}_묶음.txt"
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    $null = $p.Handle      # PS 5.1 — 이걸 안 잡으면 ExitCode 가 비는 일이 있다 (독립 검사)
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [B214] 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b214 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "MAXDD", "OWN_SPLIT", "OWN_EXPORT_OUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    적기 ("[B214] 나눔 {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $해, $p.ExitCode, $최대)
    # 「끝」 줄이 없다 = 그 무리가 터졌다(규칙을 못 만든 것은 「못만듦」 줄을 남기고 끝까지 간다 · 독립 검사)
    $빠짐 = @()
    foreach ($칸 in $칸들) { $f = Join-Path "data\_labs" ($칸.Split("|")[4]); if (-not ((Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] MULTI 내보내기 .* 끝" -Quiet))) { $빠짐 += $칸.Split("|")[4] } }
    if ($빠짐.Count -gt 0) { 적기 "❌❌ [B214] 나눔 $해 터진 무리 $($빠짐.Count)개 — 결과 파일 Traceback 확인: $($빠짐 -join ', ')" }
    if (-not (Test-Path $받)) { 그만 "❌ 나눔 $해 후보 파일이 없다" }
}
if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발 — 판정 안 함(앞 판이 꺼졌을 수 있다)" }
적기 "[B214] 판정 시작"
$env:LAB_OUT = "2026-10-01_B214_나누는해_흔들기.txt"
& $py "scripts\split_shake.py" *> $null
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
$f = "data\_labs\2026-10-01_B214_나누는해_흔들기.txt"
if ((Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] SPLIT 흔들기 끝" -Quiet)) { 적기 "[B214] 끝까지 ✅ — 결과 $f" } else { 그만 "❌ 판정이 끝까지 안 갔다" }
적기 "===== queue_b214 끝 ====="
