# ==============================================================
#  b_morning.ps1 — **B(업종·섹터·규모 전용 규칙 8개) 아침 후보 계산 → 오늘 기록에 합치기** (2026-10-12)
#  사용자 10/7 B 반영 결정 · 10/12 「응」(두 프로세스 · 끝난 규칙은 넣기 · 늦은 것은 화면에만)
#  run-briefing.ps1 이 「종가 기준일 맞음」 바로 뒤에 기다리지 않고 띄운다 (record_pick 08:02 를 늦추지 않는다)
#  ① own_lab OWN_LIVE — BV1(한 프로세스 46분)·BV2(두 프로세스 26분) 대조에서 보통 방식과 하나도 안 다름
#  ② 08:48 에 끝난 규칙만 record_pick --B합치기 (08:55 판정 전) · 그 뒤 끝나면 --B합치기 --늦음 + 다시 게시
#  ⚠️ 주문 API 는 어디에도 없다(조회도 안 함 · 로컬 계산만)
#  시험: -끝날 20261007 -기록 <forward-log 사본> -마감분 3 (임시 사본 · 게시 안 함)
# ==============================================================
param(
    [string]$끝날 = "",
    [string]$기록 = "",
    [int]$마감분 = 0
)
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$오늘 = Get-Date -f "yyyyMMdd"
$날 = Get-Date -f "yyyy-MM-dd"
$시험 = [bool]$끝날
$꼬리 = if ($시험) { "_시험$끝날" } else { "" }
$log = "run-logs\b_morning_${오늘}_$(Get-Date -f HHmm)$꼬리.log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm:ss')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$마감 = if ($마감분 -gt 0) { (Get-Date).AddMinutes($마감분) } else { (Get-Date).Date.AddHours(8).AddMinutes(48) }
$늦은끝 = if ($마감분 -gt 0) { (Get-Date).AddMinutes($마감분 + 60) } else { (Get-Date).Date.AddHours(9).AddMinutes(40) }
New-Item -ItemType Directory -Force "data\b-live" | Out-Null
$표 = "data\b-live\$오늘$꼬리"
$합 = "$표.jsonl"
if ($기록) { $env:RP_LOG = (Resolve-Path $기록).Path }
적기 "===== B 아침 계산 시작 · 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 · 마감 $($마감.ToString('HH:mm'))$(if ($시험) { " · 시험 OWN_END=$끝날" })"

# ⚠️ 10/12 발견: ETF(etf-krx)는 저녁 20:37(collect_evening)에야 전날 것을 받는다 — 아침엔 마지막 날 ETF 가 없어
#    조선 본선 규칙(ETF시총20)이 마지막 날을 못 본다. KRX 는 08:00 에 이미 준다(10/12 11:04 실측) — 여기서 받는다(몇 초)
if (-not $시험) {
    $e = & $py "scripts\collect_krx_etf.py" "--최근" "3" 2>&1
    적기 "    ETF 받기: $($e | Select-Object -Last 1)"
}

# 7무리 — 소형(22분)은 따로. 한 프로세스로 돌 땐 맨 뒤(늦으면 그것만 빠지게)
$소형 = @("규모||700|1000|${날}_B아침${꼬리}_소형_700_1000.txt")
$나머지 = @(
    "섹터|조선 본선|||${날}_B아침${꼬리}_조선본선.txt", "섹터|휴머노이드/로봇|||${날}_B아침${꼬리}_로봇.txt",
    "섹터|해운|||${날}_B아침${꼬리}_해운.txt",
    "업종|비금속|||${날}_B아침${꼬리}_비금속.txt", "업종|섬유·의류|||${날}_B아침${꼬리}_섬유의류.txt",
    "업종|종이·목재|||${날}_B아침${꼬리}_종이목재.txt"
)
function 띄우기($칸들, $밖, $묶음) {
    $env:OWN_GROUPS = ($칸들 -join ';'); $env:OWN_EXPORT = "data\forward-groups-spec.json"; $env:OWN_EXPORT_OUT = ($밖 -replace '^data\\', '')
    $env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:OWN_LIVE = "1"; $env:LAB_OUT = $묶음
    if ($끝날) { $env:OWN_END = $끝날 } else { Remove-Item env:OWN_END -ErrorAction SilentlyContinue }
    $p = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    $null = $p.Handle
    foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "OWN_LIVE", "LAB_OUT", "OWN_END") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    return $p
}
$밖A = "${표}_A.jsonl"; $밖B = "${표}_B.jsonl"
foreach ($f in $밖A, $밖B, $합) { Remove-Item $f -ErrorAction SilentlyContinue }
$들 = @()
$여 = 여유GB
if (($여 -ge 28) -and ((큰파이썬) -eq 0)) {
    적기 "두 프로세스 (소형 혼자 / 나머지 6무리) · 여유 ${여}GB"
    $들 += 띄우기 $소형 $밖A "${날}_B아침${꼬리}_묶음A.txt"
    Start-Sleep 5
    $들 += 띄우기 $나머지 $밖B "${날}_B아침${꼬리}_묶음B.txt"
} elseif ($여 -ge 15) {
    적기 "⚠️ 여유 ${여}GB · 큰 파이썬 $(큰파이썬)개 — 한 프로세스(46분 · 소형을 맨 뒤로)"
    $들 += 띄우기 ($나머지 + $소형) $밖B "${날}_B아침${꼬리}_묶음.txt"
} else {
    적기 "🛑 여유 ${여}GB — B 를 못 돌린다 · 오늘 B 는 빠진다(화면에 한 줄 알림)"
    적기 "===== B 아침 계산 끝 (못 돌림) ====="
    exit 1
}
$t0 = Get-Date; $최대 = 0.0

function 합치기파일 {
    $여기 = (Get-Location).Path; $t = ""
    foreach ($f in $밖A, $밖B) { $p2 = Join-Path $여기 $f; if (Test-Path $p2) { $x = [IO.File]::ReadAllText($p2); if ($x -and -not $x.EndsWith("`n")) { $x += "`n" }; $t += $x } }
    [IO.File]::WriteAllText((Join-Path $여기 $합), $t, (New-Object Text.UTF8Encoding $false))
}
function 붙이기($늦음) {
    합치기파일
    $a = @("scripts\record_pick.py", "--B합치기", $합); if ($늦음) { $a += "--늦음" }
    $o = & $py @a 2>&1
    $o | ForEach-Object { 적기 "    [record_pick] $_" }
    return $LASTEXITCODE
}
$붙임 = $false
while ($true) {
    Start-Sleep 15
    $합GB = 0.0
    foreach ($p in $들) { try { $합GB += (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB } catch { } }
    if ($합GB -gt $최대) { $최대 = $합GB }
    $다끝 = -not ($들 | Where-Object { -not $_.HasExited })
    if (-not $붙임 -and ($다끝 -or (Get-Date) -ge $마감)) {
        적기 ("{0} — {1:N0}분 · 최대 {2:N1}GB · 08:55 판정 전에 붙인다" -f $(if ($다끝) { "다 끝남" } else { "⚠️ 마감 — 끝난 규칙만" }), ((Get-Date) - $t0).TotalMinutes, $최대)
        $null = 붙이기 $false
        $붙임 = $true
        if (-not $시험) {
            # 08:02 「퀀트 먼저 게시」 뒤라 화면에 B 후보·상태를 한 번 더 올린다 (08:55 확정 게시는 fetch_antc 가 한다)
            $pub = & ".\scripts\publish_pages.ps1" 2>&1
            적기 "    다시 게시: $($pub | Select-Object -Last 1)"
        }
    }
    if ($다끝) { break }
    if ((Get-Date) -ge $늦은끝) { 적기 "⚠️ $($늦은끝.ToString('HH:mm')) 까지도 안 끝났다 — 기다림을 그만둔다(프로세스는 그대로 둔다)"; break }
    if ((여유GB) -lt 3) {
        적기 "🛑 여유 $(여유GB)GB — B 계산을 끈다"
        foreach ($p in $들) { try { Stop-Process -Id $p.Id -Force } catch { } }
        break
    }
}
$늦게끝 = $붙임 -and ((Get-Date) -gt $마감.AddMinutes(1)) -and -not ($들 | Where-Object { -not $_.HasExited })
if ($늦게끝) {
    적기 "08:48 뒤에 끝났다 — 늦게 나온 B 후보로 적고(사지 않음) 다시 게시"
    $null = 붙이기 $true
    if (-not $시험) { $pub = & ".\scripts\publish_pages.ps1" 2>&1; 적기 "    다시 게시: $($pub | Select-Object -Last 1)" }
}
$코드 = ($들 | ForEach-Object { $_.ExitCode }) -join ","
적기 ("===== B 아침 계산 끝 · 코드 {0} · {1:N0}분 · 최대 {2:N1}GB =====" -f $코드, ((Get-Date) - $t0).TotalMinutes, $최대)
