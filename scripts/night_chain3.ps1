# ==============================================================
#  night_chain3.ps1 — night_chain2 + BRANCHCHK 뒤에 ADDCHK 다시(기준금리 몰림 고침 · 사건 수 찍기) (2026-10-13 06:35) · BRANCHCHK 를 90분으로 잡아 아침(07:20)과 안 겹치게 (2026-10-13 05:45)
#  왜: ① NEW18 첫 판이 1시간 35분째 「하나씩」 단계 — 예상(1시간)보다 훨씬 길어 뒤가 아침으로 밀린다
#      ② night_rebuild 와 night_cf251 이 「mix_night 끝 · 큰 파이썬 0」 을 **같이** 기다려 같은 분에 둘 다 시작할 수 있었다(메모리 넘침)
#      ③ queue_addchk·queue_branchchk 는 이름에 queue_ 가 있어 C 예측 기록을 막는다(C 는 queue_* 가 0 일 때만)
#  ⇒ 그 넷의 기다리는 껍데기를 끄고 이 줄 하나로: (NEW18·C·mix_night 끝) → 화면 다시 → ADDCHK → BRANCHCHK → 현금흐름 겹침 → 현금흐름 규칙 찾기
#  ⚠️ 이름에 queue_ 를 안 쓴다 · 시험마다 걸리는 시간을 보고 07:20 전에 못 끝나면 09:10 뒤로 미룬다(아침 브리핑과 안 겹치게)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\night_chain3_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
function 껍데기($무늬) { @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match $무늬 }).Count }
$깃발 = "data\_labs\_STOP.txt"
# 걸리는 분을 받아 「지금 시작하면 07:20 전에 못 끝나거나 아침 시간(07:20~09:10)인가」
function 아침과겹치나($걸림분) {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    $평일 = ([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5)
    return ($평일 -and (($m + $걸림분) -gt 440) -and ($m -lt 550))
}
function 차례기다리기($이름, $문GB, $걸림분) {
    $ㅁ = 0
    while ((아침과겹치나 $걸림분) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) {
        if ($ㅁ % 60 -eq 0) { 적기 "[CHAIN] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 · 아침과 겹침 $(아침과겹치나 $걸림분) (약 ${걸림분}분 걸림) — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    if (Test-Path $깃발) { 적기 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8)"; 적기 "===== night_chain 끝 ====="; exit 1 }
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [CHAIN] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "night_chain 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[CHAIN] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback|터졌다" -Quiet)) }
$표준 = @{ BASE_GAP = "표본만+실전표본"; BASE_RELGAP = "-3.5"; BASE_SELL = "0.4,15,40 / 0.6,40,90"; BASE_PICKS = "120"; SIZE_HI = "999999" }
function gate7($이름, $only, $밖, $대조, $걸림분) {
    차례기다리기 $이름 15 $걸림분
    적기 "[CHAIN] $이름 시작 · 여유 $(여유GB)GB"
    foreach ($k in $표준.Keys) { Set-Item "env:$k" $표준[$k] }
    $env:ONLY = $only; $env:LAB_OUT = $밖
    돌리기 $이름 "scripts\gate7_lab.py"
    foreach ($k in @($표준.Keys) + @("ONLY", "LAB_OUT")) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
    if (끝났나 (Join-Path "data\_labs" $밖) $대조) { 적기 "[CHAIN] $이름 ✅ — data\_labs\$밖" } else { 적기 "❌ [CHAIN] $이름 끝까지 안 갔다 — data\_labs\$밖" }
}

적기 "[CHAIN2] ADDCHK(05:40 시작 · night_chain 이 띄움) 가 끝나길 기다린다 — 큰 파이썬 0"
while ((큰파이썬) -gt 0) { Start-Sleep 60 }
$밖A = "2026-10-13_ADDCHK_고친지금에_더하기.txt"
if (끝났나 (Join-Path "data\_labs" $밖A) "\[대조\] ADDCHK 끝") { 적기 "[CHAIN2] ADDCHK ✅ — data\_labs\$밖A" } else { 적기 "❌ [CHAIN2] ADDCHK 끝까지 안 갔다 — data\_labs\$밖A" }
Start-Sleep 60
$날 = Get-Date -f "yyyy-MM-dd"
gate7 "갈래 조합 해마다(BRANCHCHK)" "BRANCHCHK" "${날}_BRANCHCHK_조합_해마다.txt" "\[대조\] BRANCHCHK 끝" 90
$날 = Get-Date -f "yyyy-MM-dd"
gate7 "결정 없이 멈춘 후보 다시 · 기준금리 고침(ADDCHK2)" "ADDCHK" "${날}_ADDCHK2_기준금리고침.txt" "\[대조\] ADDCHK 끝" 50

# ④ 현금흐름 재료 — 10해 다 받았을 때만 · 겹침(약 35분) → 규칙 찾기(300~2,000억 · 3시간 넘게 걸릴 수 있다)
$해수 = @(Get-ChildItem "data\dart-cf\[0-9][0-9][0-9][0-9].json" -ErrorAction SilentlyContinue).Count
while ($해수 -lt 10 -and (껍데기 'cf_night\.ps1') -gt 0) { Start-Sleep 300; $해수 = @(Get-ChildItem "data\dart-cf\[0-9][0-9][0-9][0-9].json" -ErrorAction SilentlyContinue).Count }
if ($해수 -lt 10) { 적기 "⚠️ [CHAIN] 현금흐름 $해수 해뿐 — 현금흐름 시험은 다 받은 뒤에(cf_night 다시)"; 적기 "===== night_chain 끝 ====="; exit 0 }
$날 = Get-Date -f "yyyy-MM-dd"
$밖C = "${날}_CF251_현금재료_겹침.txt"
차례기다리기 "현금 재료 겹침" 25 40
적기 "[CHAIN] 현금 재료 겹침 시작 · 여유 $(여유GB)GB"
$env:OWN_GROUPS = "규모||300|2000|$밖C"; $env:OWN_NEWCF = "1"; $env:OWN_CORR = "1"; $env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_CF251_묶음.txt"
돌리기 "현금 재료 겹침" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_NEWCF", "OWN_CORR", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$뺄 = @()
foreach ($m in (Select-String -Path (Join-Path "data\_labs" $밖C) -Pattern "^\s+(\S+)\s+값 .*❌ 뺀다" -Encoding UTF8 -ErrorAction SilentlyContinue)) { $뺄 += $m.Matches[0].Groups[1].Value }
if (-not (끝났나 (Join-Path "data\_labs" $밖C) "뺀다|남긴다")) { 적기 "❌ [CHAIN] 현금 재료 겹침이 끝까지 안 갔다 — 규칙 찾기 안 함"; 적기 "===== night_chain 끝 ====="; exit 1 }
적기 "[CHAIN] 겹침 끝 — 빼는 재료 $($뺄.Count)개: $($뺄 -join ', ')"
$밖S = "${날}_CF251_규모300_2000.txt"
차례기다리기 "현금 재료 규칙 찾기" 25 240
적기 "[CHAIN] 현금 재료 규칙 찾기 시작(300~2,000억) · 여유 $(여유GB)GB"
$env:OWN_GROUPS = "규모||300|2000|$밖S"; $env:OWN_NEWCF = "1"; $env:OWN_NEW_DROP = ($뺄 -join ","); $env:MAXDD = "-12"; $env:OWN_CUT = "20"; $env:LAB_OUT = "${날}_CF251_묶음2.txt"
돌리기 "현금 재료 규칙 찾기" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_NEWCF", "OWN_NEW_DROP", "MAXDD", "OWN_CUT", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (끝났나 (Join-Path "data\_labs" $밖S) "\[대조\] 무리 규모") { 적기 "[CHAIN] 현금 재료 규칙 찾기 ✅ — data\_labs\$밖S" } else { 적기 "❌ [CHAIN] 현금 재료 규칙 찾기 끝까지 안 갔다 — data\_labs\$밖S" }
적기 "===== night_chain 끝 ====="
