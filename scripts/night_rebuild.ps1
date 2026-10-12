# ==============================================================
#  night_rebuild.ps1 — **규칙 한 줄을 고친 뒤 성적표·빈도 파일을 다시 만든다** (2026-10-12 · 밤)
#  사용자 「규칙 한 줄 요약을 「공통 조건 → 갈래별 조건」 순서로 다시 쓰는 게 실제 적용되고 있는 규칙과 맞는 거잖아? 맞다면 "응"」
#  rule-cases.json · rule-frequency.json 의 「규칙」 글이 R.한줄() 과 같아야 rule_align 이 통과한다 — after_labs_rebuild.ps1 을 돌린다
#  ⚠️ 이름에 queue_ 를 안 쓴다(예측 기록 C 가 queue_* 를 기다린다) · mix_night 가 끝나고 큰 파이썬 0 일 때 · 06:40 넘으면 그냥 돈다(가볍다)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$한계 = (Get-Date).Date.AddDays(1).AddHours(6).AddMinutes(40)
while ((Get-Date) -lt $한계) {
    $믹스 = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -match 'mix_night\.ps1' }).Count
    $큰 = @(Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.WorkingSet64 -gt 1GB }).Count
    if ($믹스 -eq 0 -and $큰 -eq 0) { break }
    Start-Sleep 60
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\after_labs_rebuild.ps1"
