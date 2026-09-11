# run_queue10.ps1 — 185차가 끝나면 **190차 → 189차**를 이어 돌린다 (2026-09-09 밤)
#
# 왜 줄을 세우나
#   185차가 램을 19.3GB 쓴다. 남은 게 5.8GB 뿐이라 같이 못 돌린다.
#   ⚠️ 실제로 오늘 두 번 당했다 —
#      · 190차는 램 0.1GB 에서 시작해 **곧바로 죽었다** (파일 0바이트)
#      · 189차는 「재료 붙이는 중」에서 램이 터졌다 (파일 729바이트)
#
# ⚠️ 중복 실행 막기
#   오늘 취소한 대기 스크립트가 이미 group_lab 을 하나 띄운 뒤여서
#   같은 시험이 둘 돌았다 (19184 을 죽여야 했다). 그래서 자물쇠를 둔다.

$ErrorActionPreference = "Stop"
$뿌리 = Split-Path -Parent $PSScriptRoot
$자물쇠 = Join-Path $뿌리 "data\_queue10.lock"
if (Test-Path $자물쇠) {
    Write-Host "이미 대기 중이다 ($자물쇠) — 그만둔다"
    exit 0
}
New-Item -ItemType File $자물쇠 | Out-Null
$기록 = Join-Path $뿌리 "data\_queue10.log"

function 찍기($s) {
    $줄 = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $s
    Write-Host $줄
    Add-Content -Path $기록 -Value $줄 -Encoding utf8
}

try {
    찍기 "===== 185차를 기다린다 ====="
    while ($true) {
        $돎 = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
              Where-Object { $_.CommandLine -like "*group_lab*" }
        if (-not $돎) { break }
        Start-Sleep -Seconds 120
    }
    찍기 "185차 끝났다"

    # 램이 풀릴 틈을 준다
    Start-Sleep -Seconds 30

    $줄 = @(
        @{ 번 = 190; 것 = "gate6_lab.py";  나 = "2026-09-09_190차_4관문_같이빠진것.txt" },
        @{ 번 = 189; 것 = "info_lab2.py";  나 = "2026-09-09_189차_정보재료.txt" }
    )
    foreach ($t in $줄) {
        $여 = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)
        찍기 ("{0}차 시작 — 램 {1}GB 남음" -f $t.번, $여)
        if ($여 -lt 4) {
            찍기 ("  ⚠️ 램이 {0}GB 뿐이다. 5분 더 기다린다" -f $여)
            Start-Sleep -Seconds 300
        }
        $env:LAB_OUT = $t.나
        & python (Join-Path $PSScriptRoot $t.것)
        $크 = (Get-Item (Join-Path $뿌리 ("data\_labs\" + $t.나))).Length
        # ⚠️ 「끝났다」가 아니라 **파일 크기**로 판정한다.
        #    오늘 0바이트·729바이트짜리를 「돌았다」고 읽을 뻔했다
        if ($크 -lt 2000) {
            찍기 ("  ❌ {0}차가 {1}바이트뿐이다 — 죽었다" -f $t.번, $크)
        } else {
            찍기 ("  ✅ {0}차 끝 — {1:N0}바이트" -f $t.번, $크)
        }
        Start-Sleep -Seconds 30
    }
    찍기 "===== 줄 끝 ====="
}
finally {
    Remove-Item $자물쇠 -ErrorAction SilentlyContinue
}
