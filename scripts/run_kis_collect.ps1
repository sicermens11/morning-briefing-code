# run_kis_collect.ps1 — 한국투자증권 신용잔고·공매도 2010~ 받기를 6조각으로 떼어 띄운다 (2026-10-22 · 조회만)
#   각 조각은 세션이 죽어도 산다(Start-Process) · 로그 data/_kis_collect.log · 조각별 stdout data/_kis_collect_N.out
#   이어 받기 되므로 다시 돌려도 받은 종목은 건너뛴다
$root = Split-Path -Parent $PSScriptRoot
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
if (-not (Test-Path $py)) { $py = (Get-Command python).Source }
$n = 3   # 6개는 초당 한도(EGW00201)에 바로 걸렸다(10/22 17:57)
$종류 = if ($args.Count -gt 0) { $args[0] } else { "신용공매도" }   # 10/23 「대차+의견」
for ($i = 0; $i -lt $n; $i++) {
    Start-Process -FilePath $py -ArgumentList @("`"$root\scripts\collect_kis_hist.py`"", "--조각", "$i/$n", "--종류", $종류) `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput "$root\data\_kis_collect_$i.out" -RedirectStandardError "$root\data\_kis_collect_$i.err"
    Start-Sleep -Seconds 2
}
Write-Output "조각 $n 개 띄움 — 로그 data\_kis_collect.log"
