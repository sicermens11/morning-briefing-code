# ==============================================================
#  cf_night.ps1 — **현금흐름 나머지 해(2021~2015)를 밤에 이어 받는다** (2026-10-12 · B251)
#  OpenDART 하루 한도(약 2만)가 0시에 새로 찬다 — 00:20 까지 기다렸다가 한 해씩 · 한도에 닿으면 collect_cashflow 가 스스로 멈춘다
#  다 받은 해는 건너뛴다(이어받기) · 남으면 다음 날 같은 스크립트를 다시 걸면 된다
#  ⚠️ 이름에 queue_ 를 안 쓴다 — 가벼운 수집이라 예측 기록(forward_daily)을 막을 이유가 없다
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$시작 = (Get-Date).Date.AddDays(1).AddMinutes(20)
if ((Get-Date) -lt $시작) { Start-Sleep -Seconds ([int]($시작 - (Get-Date)).TotalSeconds) }
foreach ($y in 2021, 2020, 2019, 2018, 2017, 2016, 2015) {
    & $py "scripts\collect_cashflow.py" --해 $y --최대 2700
    if (Select-String -Path "data\_cashflow.log" -Pattern "하루 한도에 닿았다" -Quiet -Encoding UTF8 -SimpleMatch) {
        $끝줄 = Get-Content "data\_cashflow.log" -Encoding UTF8 -Tail 1
        if ($끝줄 -match "하루 한도") { break }
    }
}
