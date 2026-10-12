# ==============================================================
#  night_rebuild.ps1 — **화면 성적표(rule-capital·rule-cases)와 빈도를 고친 시험 규칙으로 다시 만든다** (2026-10-12 · 밤)
#  ① 사용자 「규칙 한 줄 요약을 … 다시 쓰는 게 실제 적용되고 있는 규칙과 맞는 거잖아? 맞다면 "응"」 — 성적표 「규칙」 글을 새 한 줄로
#  ② 10/12 발견: 화면 「과거에 이 규칙으로 했다면」 은 gate7 CARDLIVE(10/6)가 만들었는데 그 「지금 규칙」(_H)에 **업종 갈래가 없었다** → _H 고친 뒤 다시
#  ⚠️ after_labs_rebuild.ps1(build_rule_cases.py = 옛날식 단순 계산)은 쓰지 않는다 — CARDLIVE 가 만든 화면 파일을 덮어쓴다
#  ⚠️ 이름에 queue_ 를 안 쓴다(예측 기록 C 가 queue_* 를 기다린다) · mix_night 가 끝나고 큰 파이썬 0 · 06:30 넘으면 그냥 돈다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\night_rebuild_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { $줄 = "$(Get-Date -f 'MM-dd HH:mm')  $s"; Write-Output $줄; Add-Content -Path $log -Value $줄 -Encoding UTF8 }
$한계 = (Get-Date).Date.AddDays(1).AddHours(6).AddMinutes(30)
적기 "[REBUILD] mix_night 끝 · 큰 파이썬 0 을 기다린다"
while ((Get-Date) -lt $한계) {
    $믹스 = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'mix_night\.ps1' }).Count
    $큰 = @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count
    if ($믹스 -eq 0 -and $큰 -eq 0) { break }
    Start-Sleep 60
}
적기 "[REBUILD] CARDLIVE 시작 (고친 _H = 업종 갈래 OR · 새 규칙 한 줄)"
$env:BASE_GAP = "표본만+실전표본"; $env:BASE_RELGAP = "-3.5"; $env:BASE_SELL = "0.4,15,40 / 0.6,40,90"
$env:BASE_PICKS = "120"; $env:SIZE_HI = "999999"; $env:ONLY = "CARDLIVE"; $env:LAB_OUT = "$(Get-Date -f yyyy-MM-dd)_REBUILD_CARDLIVE.txt"
& $py "scripts\gate7_lab.py" 2>&1 | Select-Object -Last 6 | ForEach-Object { 적기 "    $_" }
foreach ($k in "BASE_GAP", "BASE_RELGAP", "BASE_SELL", "BASE_PICKS", "SIZE_HI", "ONLY", "LAB_OUT") { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
적기 "[REBUILD] 빈도(how_often)"
& $py "scripts\how_often.py" 2>&1 | Select-Object -Last 3 | ForEach-Object { 적기 "    $_" }
적기 "[REBUILD] rule_align"
& $py "scripts\rule_align.py" 2>&1 | Select-Object -Last 8 | ForEach-Object { 적기 "    $_" }
적기 "===== night_rebuild 끝 ====="
