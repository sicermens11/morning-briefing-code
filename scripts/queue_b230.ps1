# ==============================================================
#  queue_b230.ps1 — **B224 후보 40 규칙들을 한 계좌로** (2026-10-06)
#  사용자 10/6: 「B224도 테스트 끝나고 균형표 작성해주면 거기서 고르면 돼?」 → 균형 표의 다른 줄과 견주려면 「한 계좌」 값이 있어야 한다
#  ① make_spec (B224 결과 · 자름 20 · 후보 40) → multi_rules_spec_k40.json ② own_lab OWN_EXPORT (OWN_K=40) → multi_cand_own_k40.jsonl
#  ③ multi_lab (실전 후보는 B222 ③ 의 multi_cand_live.jsonl 그대로) — 돈만 관문 · 500만 N년
#  B226 · B227 · B228 뒤 · 판은 하나씩 · 실패해도 멈춤 깃발은 안 세운다(뒤 판 B229 를 막지 않게)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\queue_b230_$(Get-Date -f yyyyMMdd_HHmmss).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; try { Add-Content -Path $log -Value $줄 -Encoding UTF8 -ErrorAction Stop } catch { } }
function 큰파이썬 { @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count }
function 여유GB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
$깃발 = "data\_labs\_STOP.txt"
$날 = Get-Date -f "yyyy-MM-dd"
function 그만($s) { 적기 $s; 적기 "===== queue_b230 끝 ====="; exit 1 }
function 밤샘기다리기 {
    if ((Get-Date).Hour -ge 7) { return }
    $오늘 = Get-Date -f "yyyy-MM-dd"
    적기 "[B230] 밤 시간 — 밤샘 옛 시험이 끝나길 기다린다"
    while ($true) {
        $끝 = Select-String -Path "data\_overnight.log" -Pattern "^$오늘 .*(===== 시험 끝 =====|시험을 건너뛴다)" -Quiet -Encoding UTF8   # 10/4: 새 자료가 없으면 시험을 건너뛰고 「시험 끝」 을 안 찍는다
        $n = Get-Date
        if ($끝 -or ($n.Hour -ge 8) -or ($n.Hour -eq 7 -and $n.Minute -ge 5)) { break }
        Start-Sleep 60
    }
    Start-Sleep 120
}
function 아침인가 {
    $n = Get-Date; $m = $n.Hour * 60 + $n.Minute
    return (([int]$n.DayOfWeek -ge 1) -and ([int]$n.DayOfWeek -le 5) -and ($m -ge 440) -and ($m -lt 550))
}
function 기다리기($이름, $문GB) {
    $ㅁ = 0
    while (((아침인가) -or ((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)) -and ($ㅁ -lt 720)) {
        if ($ㅁ -eq 0) { 적기 "[B230] $이름 — 여유 $(여유GB)GB · 큰 파이썬 $(큰파이썬)개 — 기다린다" }
        Start-Sleep 60; $ㅁ++
    }
    return (-not (((여유GB) -lt $문GB) -or ((큰파이썬) -gt 0)))
}
function 돌리기($이름, $스크립트) {
    $최대 = 0.0
    $p = Start-Process -FilePath $py -ArgumentList $스크립트 -PassThru -WindowStyle Hidden
    $null = $p.Handle
    while (-not $p.HasExited) {
        Start-Sleep 30
        try { $ws = (Get-Process -Id $p.Id -ErrorAction Stop).WorkingSet64 / 1GB; if ($ws -gt $최대) { $최대 = $ws } } catch { }
        if ((여유GB) -lt 3) { 적기 "🛑 [B230] $이름 여유 $(여유GB)GB — 끈다"; try { Stop-Process -Id $p.Id -Force } catch { }; Set-Content $깃발 "queue_b230 메모리 3GB 밑 $(Get-Date -f 'MM-dd HH:mm')" -Encoding UTF8; break }
    }
    적기 ("[B230] {0} 끝 — 코드 {1} · 최대 메모리 {2:N1}GB" -f $이름, $p.ExitCode, $최대)
}
function 끝났나($f, $무늬) { return ((Test-Path $f) -and (Select-String -Path $f -Pattern $무늬 -Quiet) -and -not (Select-String -Path $f -Pattern "Traceback" -Quiet)) }
적기 "[B230] B226 · B227 · B228 이 끝나길 기다린다"
while (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'queue_b226|queue_b227|queue_b228|queue_own' }).Count -gt 0) { Start-Sleep 60 }
Start-Sleep 60
if (Test-Path $깃발) { 그만 "🛑 멈춤 깃발: $(Get-Content $깃발 -Raw -Encoding UTF8) — 안 돈다" }
$날 = Get-Date -f "yyyy-MM-dd"
# ── ① 통과 규칙 목록 ──
$env:SPEC_GLOB = "2026-10-05_B*_무리전용_*_자름20_낙폭체없음_후보40.txt"; $env:SPEC_OUT = "multi_rules_spec_k40.json"; $env:SPEC_OUTPRE = "${날}_B230_내보내기_"
$ms = & $py "scripts\make_spec.py" 2>&1
foreach ($k in "SPEC_GLOB", "SPEC_OUT", "SPEC_OUTPRE") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$ms | Select-String "파일 .*개 · 통과 규칙" | ForEach-Object { 적기 "    $_" }
$무리줄 = (Get-Content "data\_labs\multi_rules_spec_k40_groups.txt" -Raw -Encoding UTF8).Trim()
if (-not $무리줄) { 그만 "❌ multi_rules_spec_k40_groups.txt 가 비었다" }
# ── ② 무리 후보 (후보 40) ──
Remove-Item "data\_labs\multi_cand_own_k40.jsonl" -ErrorAction SilentlyContinue
밤샘기다리기
if (-not (기다리기 "② OWN_EXPORT" 20)) { 그만 "🛑 ② 12시간 기다려도 모자라다" }
$칸들 = $무리줄 -split ';'
적기 "[B230] ② OWN_EXPORT 시작 (무리 $($칸들.Count)개 · 후보 40) · 여유 $(여유GB)GB"
$env:OWN_GROUPS = $무리줄; $env:OWN_EXPORT = "data\_labs\multi_rules_spec_k40.json"; $env:OWN_EXPORT_OUT = "multi_cand_own_k40.jsonl"
$env:MAXDD = "-999"; $env:OWN_CUT = "20"; $env:OWN_K = "40"; $env:LAB_OUT = "${날}_B230_2_무리후보_묶음.txt"
돌리기 "② OWN_EXPORT" "scripts\own_lab.py"
foreach ($k in "OWN_GROUPS", "OWN_EXPORT", "OWN_EXPORT_OUT", "MAXDD", "OWN_CUT", "OWN_K", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
$빠짐 = @()
foreach ($칸 in $칸들) { $f = Join-Path "data\_labs" ($칸.Split("|")[4]); if (-not (끝났나 $f "\[대조\] MULTI 내보내기 .* 끝")) { $빠짐 += $칸.Split("|")[4] } }
if ($빠짐.Count -gt 0) { 그만 "❌ ② 끝까지 안 간 무리 $($빠짐.Count)개: $($빠짐 -join ', ')" }
# ── ③ 한 계좌로 ──
if (-not (기다리기 "③ multi_lab" 12)) { 그만 "🛑 ③ 12시간 기다려도 모자라다" }
적기 "[B230] ③ multi_lab 시작"
$밖 = "${날}_B230_여러규칙_한계좌_후보40.txt"; $env:LAB_OUT = $밖
$env:MULTI_SPEC = "multi_rules_spec_k40.json"; $env:MULTI_CAND = "multi_cand_own_k40.jsonl"
$env:MULTI_NODD = "1"; $env:MULTI_HORIZON = "1"; $env:MULTI_FAST = "1"
돌리기 "③ multi_lab" "scripts\multi_lab.py"
foreach ($k in "LAB_OUT", "MULTI_SPEC", "MULTI_CAND", "MULTI_NODD", "MULTI_HORIZON", "MULTI_FAST") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
if (끝났나 (Join-Path "data\_labs" $밖) "\[대조\] MULTI 끝") { 적기 "[B230] ③ 표 ✅ — data\_labs\$밖" } else { 적기 "❌ [B230] ③ 합치기가 끝까지 안 갔다" }
적기 "===== queue_b230 끝 ====="
