# ==============================================================
#  queue_own.ps1 — **무리 전용 규칙 판을 하나씩** (2026-09-30)
#  설계: docs/2026-09-30_무리전용_시험설계.md · 코드: scripts/own_lab.py
#  사용자: 「바로 코드 짜고 테스트 시작해. 메모리 안 터지게 조심해.」
#
#  · 한 프로세스가 무리를 **차례로** 돌린다 — 판이 겹치지 않는다 (겹치면 조용히 죽었다)
#  · 판마다: 아침 07:20~09:10 피함 · 커밋 여유 18GB 관문(최대 12시간 기다림) · 멈춤 깃발
#  · 결과 파일에 「[대조] 무리」 줄이 없으면 **터진 것** → 깃발 세우고 멈춘다
#  · 판마다 verify_own.py 대조표를 로그에 남긴다
#  쓰는 법:  powershell -File scripts\queue_own.ps1 -Which 시험     (작은 무리 빠른 판 하나)
#            powershell -File scripts\queue_own.ps1 -Which 전부
# ==============================================================
param([string]$Which = "전부", [string]$After = "")
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_own_$Which`_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) {
    $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"
    Write-Output $줄
    try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { }
}
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    if (-not ((($h -eq 7) -and ($m -ge 20)) -or ($h -eq 8) -or (($h -eq 9) -and ($m -lt 10)))) { return $false }
    & $py "scripts\krx_calendar.py" *> $null
    return ($LASTEXITCODE -eq 0)
}
$깃발 = "data\_labs\_STOP.txt"

# 무리 목록 — (번호, 종류, 값, BIG_LO, BIG_HI, 이름표)
$시험 = @(@("B157", "섹터", "원전 기자재", "", "", "시험판_원전", "1"))
$전부 = @(
    @("B158", "규모", "", "10000", "", "대형1조", ""),
    @("B159", "규모", "", "2000", "10000", "중형", "")
)
$섹터들 = @("조선 기자재", "조선 본선", "방산", "원전 기자재", "전력 인프라/변압기", "2차전지 소부장", "휴머노이드/로봇",
          "바이오 CDMO", "의료기기/디지털헬스", "사이버보안", "AI 소프트웨어", "우주/스페이스X", "반도체/HBM 소부장", "해운")
$업종들 = @("IT 서비스", "건설", "금속", "금융", "기계·장비", "기타제조", "비금속", "섬유·의류", "오락·문화", "운송·창고",
          "운송장비·부품", "유통", "음식료·담배", "의료·정밀기기", "일반서비스", "전기전자", "제약", "종이·목재", "출판·매체복제", "통신", "화학")
$n = 161
foreach ($s in $섹터들) { $전부 += , @("B$n", "섹터", $s, "", "", ("섹터_" + ($s -replace '[/ ]', '')), ""); $n++ }
foreach ($u in $업종들) { $전부 += , @("B$n", "업종", $u, "", "", ("업종_" + ($u -replace '[/ ·]', '')), ""); $n++ }
# ⚠️ 소형(300억~2천억 · 2010~)은 사건 약 440만 · 메모리 약 30GB 로 어림 (9/30 독립 검사) — 대형·중형 실측을 보고 따로 정한다
$목록 = if ($Which -eq "시험") { $시험 } else { $전부 }

if ($After) {
    적기 "[0] 앞 판($After) 끝을 기다린다"
    $w = 0
    while ($w -lt 720) {
        $앞 = @(Get-ChildItem "run-logs\queue_$After`_*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1)
        if ($앞.Count -gt 0 -and (Select-String -Path $앞[0].FullName -Pattern "queue_$After 끝 =====" -Quiet) -and ((큰파이썬) -eq 0)) { break }
        Start-Sleep -Seconds 60; $w++
    }
}
적기 "===== queue_own ($Which) 시작 · 무리 $($목록.Count)개 ====="
foreach ($g in $목록) {
    $번, $종, $값, $lo, $hi, $표, $빠른 = $g
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 여기서 멈춘다: $((Get-Content $깃발 -Raw) -replace "`r`n", ' ')"; break }
    $ㅇ = 0
    while ((아침인가) -and ($ㅇ -lt 180)) { if ($ㅇ -eq 0) { 적기 "[$번] 아침 시간대 — 09:10 지나가길 기다린다" }; Start-Sleep 60; $ㅇ++ }
    $ㅁ = 0
    while ((((여유GB) -lt 18) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[$번] 메모리 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    if ((여유GB) -lt 18) { 적기 "🛑 [$번] 12시간 기다려도 여유 $(여유GB)GB — 멈춘다"; Set-Content $깃발 "queue_own $번 메모리 부족" -Encoding UTF8; break }
    $밖 = "2026-09-30_$번`_무리전용_$표.txt"
    적기 "[$번] 시작 — $종 $값 $lo~$hi · 여유 $(여유GB)GB"
    $env:OWN_KIND = $종; $env:OWN_VALUE = $값; $env:BIG_LO = $lo; $env:BIG_HI = $hi; $env:LAB_OUT = $밖; $env:MAXDD = "-12"
    if ($빠른) { $env:OWN_FAST = "1" } else { Remove-Item env:OWN_FAST -ErrorAction SilentlyContinue }
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
    }
    foreach ($k in "OWN_KIND", "OWN_VALUE", "BIG_LO", "BIG_HI", "LAB_OUT", "OWN_FAST", "MAXDD") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $f = Join-Path "data\_labs" $밖
    $끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] 무리" -Quiet)
    $터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback" -Quiet)
    적기 ("[$번] 끝 — 코드 {0} · 최대 메모리 {1:N1}GB · 결과 {2:N0}B · {3}" -f $p.ExitCode, $최대, ((Get-Item $f -ErrorAction SilentlyContinue).Length), ($(if ($끝 -and -not $터) { "끝까지 ✅" } else { "터짐 ❌" })))
    $vo = & $py "scripts\verify_own.py" $f 2>&1
    $vo | Select-Object -Last 14 | ForEach-Object { 적기 "    $_" }
    if (-not $끝 -or $터) {
        Set-Content $깃발 "queue_own $번 ($종 $값) 이 터졌다 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8
        적기 "🛑 [$번] 터졌다 — 깃발을 세우고 멈춘다"
        break
    }
}
적기 "===== queue_own_$Which 끝 ====="
