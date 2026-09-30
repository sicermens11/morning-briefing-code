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
param([string]$Which = "전부", [string]$After = "", [switch]$Dry, [string]$Skip = "", [string]$Kinds = "", [switch]$Batch)
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8   # verify_own 대조표가 로그에서 깨졌다 (9/30 13:26)
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
# ⚠️ 9/30 16:01 대기열 둘을 같은 분에 띄워 로그 이름이 겹쳤다 — 초와 종류를 넣는다
$log = "run-logs\queue_own_$Which`_$(Get-Date -f yyyyMMdd_HHmmss)$(if ($Kinds) { '_' + ($Kinds -replace ',', '') }).log"
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
$시험 = @(,@("B157", "섹터", "원전 기자재", "", "", "시험판5_원전_원천시작일", ""))
$전부 = @(
    @("B158", "규모", "", "10000", "", "대형1조", "")
)
# ⚠️ 9/30 18:56 — 중형(2천억~1조 · 사건 약 190만)을 관문 24GB 로 걸었는데, 브라우저를 꺼도 여유가 18.7GB 라
#    **영영 시작 못 했다**(윈도우·상주 프로그램이 약 15GB). 띠마다 사건을 어림(krx-daily 분기 표본 · 대형 어림 83만 ↔ 실측 80만)해
#    **판마다 사건 약 100만**(≈12~13GB)이 되게 나눈다. B159·B196·B197 은 안 쓴다
$전부 += , @("B198", "규모", "", "2000", "3500", "중형_2000_3500", "")
$전부 += , @("B199", "규모", "", "3500", "10000", "중형_3500_10000", "")
$섹터들 = @("조선 기자재", "조선 본선", "방산", "원전 기자재", "전력 인프라/변압기", "2차전지 소부장", "휴머노이드/로봇",
          "바이오 CDMO", "의료기기/디지털헬스", "사이버보안", "AI 소프트웨어", "우주/스페이스X", "반도체/HBM 소부장", "해운")
$업종들 = @("IT 서비스", "건설", "금속", "금융", "기계·장비", "기타제조", "비금속", "섬유·의류", "오락·문화", "운송·창고",
          "운송장비·부품", "유통", "음식료·담배", "의료·정밀기기", "일반서비스", "전기전자", "제약", "종이·목재", "출판·매체복제", "통신", "화학")
$n = 161
foreach ($s in $섹터들) { $전부 += , @("B$n", "섹터", $s, "", "", ("섹터_" + ($s -replace '[/ ]', '')), ""); $n++ }
foreach ($u in $업종들) { $전부 += , @("B$n", "업종", $u, "", "", ("업종_" + ($u -replace '[/ ·]', '')), ""); $n++ }
# ⭐ 소형 — 사용자 9/30 「정리하면 1·2·3·4는 「하자」 … 이대로 가자. 메모리 안 넘치게 조심해.」 (3번: 소형은 두 띠로 나눠 꼭 한다)
#    한 덩이(300억~2천억)는 사건 약 460만 · 약 30GB 어림 → 300~700억 · 700억~2천억 두 판. 맨 뒤에 둔다(중형 실측을 보고 관문을 고칠 수 있게)
#    ⚠️ 9/30 18:56 두 띠(각 230만 건)도 너무 커서 다섯 띠로 (각 약 70~110만)
$전부 += , @("B200", "규모", "", "300", "500", "소형_300_500", "")
$전부 += , @("B201", "규모", "", "500", "700", "소형_500_700", "")
$전부 += , @("B202", "규모", "", "700", "1000", "소형_700_1000", "")
$전부 += , @("B203", "규모", "", "1000", "1500", "소형_1000_1500", "")
$전부 += , @("B204", "규모", "", "1500", "2000", "소형_1500_2000", "")
# ⚠️ `$목록 = if (…) { $시험 }` 은 한 줄짜리 목록을 풀어 「무리 7개」로 만들었다 (9/30 두 번) — if 안에서 대입한다
if ($Which -eq "시험") { $목록 = $시험 } else { $목록 = $전부 }
# ⭐ 9/30 16:10 — 낮엔 브라우저 몫 때문에 중형(관문 24GB)이 못 시작한다 → -Kinds 섹터 로 섹터만 먼저,
#    -Skip B158 로 끝난 판을 뺀다. (순서는 내가 정한다 — [[when-to-stop-testing]])
if ($Skip) { $뺄 = $Skip -split ','; $목록 = @($목록 | Where-Object { $뺄 -notcontains $_[0] }) }
if ($Kinds) { $종류들 = $Kinds -split ','; $목록 = @($목록 | Where-Object { $종류들 -contains $_[1] }) }
if ($Dry) {
    Write-Output "무리 $($목록.Count)개"
    foreach ($g in $목록) { $번, $종, $값, $lo, $hi, $표, $빠른 = $g; Write-Output "$번 | $종 | $값 | $lo~$hi | $표 | 빠른=$빠른" }
    exit 0
}

if ($After) {
    적기 "[0] 앞 판($After) 끝을 기다린다"
    $w = 0
    while ($w -lt 720) {
        # ⚠️ 제 로그(queue_own_…)가 앞 판 로그로 잡히지 않게 뺀다
        $앞 = @(Get-ChildItem "run-logs\queue_$After`_*.log" -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -ne (Resolve-Path $log -ErrorAction SilentlyContinue).Path } |
                Sort-Object LastWriteTime | Select-Object -Last 1)
        if ($앞.Count -gt 0 -and (Select-String -Path $앞[0].FullName -Pattern "queue_$After 끝 =====" -Quiet) -and ((큰파이썬) -eq 0)) { break }
        Start-Sleep -Seconds 60; $w++
    }
}
적기 "===== queue_own ($Which) 시작 · 무리 $($목록.Count)개 ====="

# ⭐ 10/1 -Batch — 「한 번 읽기」: 한 프로세스가 공통 준비를 한 번 하고 무리를 차례로 (own_lab OWN_GROUPS)
#    판마다 7~9분 같은 자료를 다시 읽던 것을 없앤다. 끝나면 무리마다 결과를 따로 대조한다
function 뜻한무리($종, $값, $lo, $hi) {
    if ($종 -eq "규모") { return ("규모 {0:N0}억~{1}" -f [double]$lo, $(if ($hi) { ("{0:N0}억" -f [double]$hi) } else { "(상한 없음)" })) }
    return "$종 = $값"
}
if ($Batch) {
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 시작 안 함"; 적기 "===== queue_own_$Which 끝 ====="; exit 1 }
    $ㅇ = 0
    while ((아침인가) -and ($ㅇ -lt 180)) { if ($ㅇ -eq 0) { 적기 "[묶음] 아침 시간대 — 09:10 지나가길 기다린다" }; Start-Sleep 60; $ㅇ++ }
    $ㅁ = 0
    while ((((여유GB) -lt 18) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[묶음] 메모리 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    # ⚠️ 10/1 독립 검사: 한 무리 모드처럼 12시간 기다려도 모자라면 멈춘다 (그냥 시작하면 겹쳐 죽는다)
    if (((여유GB) -lt 18) -or ((큰파이썬) -gt 0)) {
        적기 "🛑 [묶음] 12시간 기다려도 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 멈춘다"
        Set-Content $깃발 "queue_own 묶음 메모리 부족 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8
        적기 "===== queue_own_$Which 끝 ====="; exit 1
    }
    $칸들 = @(); $파일들 = @()
    foreach ($g in $목록) {
        $번, $종, $값, $lo, $hi, $표, $빠른 = $g
        $밖 = "$(Get-Date -f yyyy-MM-dd)_$번`_무리전용_$표.txt"
        $칸들 += "$종|$값|$lo|$hi|$밖"; $파일들 += , @($번, $밖, (뜻한무리 $종 $값 $lo $hi))
    }
    $env:OWN_GROUPS = ($칸들 -join ';'); $env:LAB_OUT = "$(Get-Date -f yyyy-MM-dd)_묶음_$($목록[0][0])-$($목록[-1][0]).txt"; $env:MAXDD = "-12"
    적기 "[묶음] 시작 — 무리 $($목록.Count)개 한 프로세스 · 여유 $(여유GB)GB"
    $최대 = 0.0; $끔 = $false
    $p = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) {
            적기 "🛑 [묶음] 메모리 여유 $(여유GB)GB — 이 판을 끈다"
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch { }
            $끔 = $true
            Set-Content $깃발 "queue_own 묶음 메모리 여유 3GB 밑 — 스스로 껐다 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8
            break
        }
    }
    foreach ($k in "OWN_GROUPS", "LAB_OUT", "MAXDD") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    적기 ("[묶음] 끝 — 코드 {0} · 최대 메모리 {1:N1}GB" -f $p.ExitCode, $최대)
    $터진것 = 0
    foreach ($x in $파일들) {
        $번, $밖, $뜻 = $x
        $f = Join-Path "data\_labs" $밖
        $끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] 무리" -Quiet)
        $터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback" -Quiet)
        $env:OWN_EXPECT = $뜻
        $vo = & $py "scripts\verify_own.py" $f 2>&1
        Remove-Item env:OWN_EXPECT -ErrorAction SilentlyContinue
        $요 = ($vo | Select-String "⑨ 뒤 기간" | Select-Object -First 1)
        적기 ("[$번] {0} · {1}" -f $(if ($끝 -and -not $터) { "끝까지 ✅" } else { "터짐 ❌" }), ($요 -replace '^\s+', ''))
        if (($vo | Out-String) -match "❌") { $vo | Select-String "❌" | ForEach-Object { 적기 "    $_" } }
        if (-not $끝 -or $터) { $터진것++ }
        # ⚠️ 10/1 독립 검사: 뜻한 무리와 다르게 돌았으면 한 무리 모드처럼 깃발 조건에 넣는다
        if (($vo | Out-String) -match "뜻한 무리") { 적기 "🛑 [$번] 뜻한 무리와 다르다"; $터진것++ }
    }
    if ($터진것 -gt 0 -or $끔) { Set-Content $깃발 "queue_own 묶음 — 터진 무리 $터진것 개 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; 적기 "🛑 [묶음] 터진 무리 $터진것 개 — 깃발" }
    적기 "===== queue_own_$Which 끝 ====="
    exit 0
}
foreach ($g in $목록) {
    $번, $종, $값, $lo, $hi, $표, $빠른 = $g
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발 — 여기서 멈춘다: $((Get-Content $깃발 -Raw) -replace "`r`n", ' ')"; break }
    $ㅇ = 0
    while ((아침인가) -and ($ㅇ -lt 180)) { if ($ㅇ -eq 0) { 적기 "[$번] 아침 시간대 — 09:10 지나가길 기다린다" }; Start-Sleep 60; $ㅇ++ }
    # ⚠️ 9/30 독립 검사: 중형은 사건 189만 · 어림 17~21GB — 18GB 관문으로는 모자란다
    $관문 = 18      # 판마다 사건 약 100만 이하로 나눴다 (9/30 18:56)
    $ㅁ = 0
    while ((((여유GB) -lt $관문) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[$번] 메모리 여유 $(여유GB)GB (관문 $관문) · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    if ((여유GB) -lt $관문) { 적기 "🛑 [$번] 12시간 기다려도 여유 $(여유GB)GB — 멈춘다"; Set-Content $깃발 "queue_own $번 메모리 부족" -Encoding UTF8; break }
    $밖 = "$(Get-Date -f yyyy-MM-dd)_$번`_무리전용_$표.txt"
    # 판이 뜻한 무리로 돌았나 verify_own 이 본다 (9/30 무리 값 빠진 채 전 종목으로 두 번 돌았다)
    if ($종 -eq "규모") {
        $env:OWN_EXPECT = "규모 {0:N0}억~{1}" -f [double]$lo, $(if ($hi) { ("{0:N0}억" -f [double]$hi) } else { "(상한 없음)" })
    } else { $env:OWN_EXPECT = "$종 = $값" }
    적기 "[$번] 시작 — $종 $값 $lo~$hi · 여유 $(여유GB)GB"
    $env:OWN_KIND = $종; $env:OWN_VALUE = $값; $env:BIG_LO = $lo; $env:BIG_HI = $hi; $env:LAB_OUT = $밖; $env:MAXDD = "-12"
    if ($빠른) { $env:OWN_FAST = "1" } else { Remove-Item env:OWN_FAST -ErrorAction SilentlyContinue }
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList "scripts\own_lab.py" -PassThru -WindowStyle Hidden
    $끔 = $false
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        # ⚠️ 9/30 13:24 잘못 걸린 판이 여유 5.6GB 까지 먹었고 사장님이 손으로 꺼야 했다 —
        #    여유 3GB 밑이면 **이 대기열이 띄운 판만** 스스로 끄고 깃발을 세운다 (다른 프로그램은 안 건드린다)
        if ((여유GB) -lt 3) {
            적기 "🛑 [$번] 메모리 여유 $(여유GB)GB · 판 메모리 $([math]::Round($ws,1))GB — 이 판을 끈다"
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop } catch { }
            $끔 = $true
            Set-Content $깃발 "queue_own $번 ($종 $값) 메모리 여유 3GB 밑 — 스스로 껐다 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8
            break
        }
    }
    if ($끔) { 적기 "🛑 [$번] 메모리로 껐다 — 깃발을 세우고 멈춘다"; break }
    foreach ($k in "OWN_KIND", "OWN_VALUE", "BIG_LO", "BIG_HI", "LAB_OUT", "OWN_FAST", "MAXDD") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    $f = Join-Path "data\_labs" $밖
    $끝 = (Test-Path $f) -and (Select-String -Path $f -Pattern "\[대조\] 무리" -Quiet)
    $터 = (Test-Path $f) -and (Select-String -Path $f -Pattern "Traceback" -Quiet)
    적기 ("[$번] 끝 — 코드 {0} · 최대 메모리 {1:N1}GB · 결과 {2:N0}B · {3}" -f $p.ExitCode, $최대, ((Get-Item $f -ErrorAction SilentlyContinue).Length), ($(if ($끝 -and -not $터) { "끝까지 ✅" } else { "터짐 ❌" })))
    $vo = & $py "scripts\verify_own.py" $f 2>&1
    $vo | Select-Object -Last 14 | ForEach-Object { 적기 "    $_" }
    Remove-Item env:OWN_EXPECT -ErrorAction SilentlyContinue
    # ⚠️ 9/30 재검사: verify ❌ 가 로그에만 남았다 — **뜻한 무리와 다르게 돌았으면** 멈춘다 (다른 ❌ 는 로그에 남기고 사람이 본다)
    if (($vo | Out-String) -match "뜻한 무리") {
        Set-Content $깃발 "queue_own $번 뜻한 무리와 다른 무리로 돌았다 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8
        적기 "🛑 [$번] 뜻한 무리와 다르다 — 깃발을 세우고 멈춘다"
        break
    }
    if (-not $끝 -or $터) {
        Set-Content $깃발 "queue_own $번 ($종 $값) 이 터졌다 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8
        적기 "🛑 [$번] 터졌다 — 깃발을 세우고 멈춘다"
        break
    }
}
적기 "===== queue_own_$Which 끝 ====="
