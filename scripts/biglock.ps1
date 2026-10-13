# ==============================================================
#  biglock.ps1 — **큰 계산은 한 번에 하나** · 자물쇠 파일 (2026-10-13)
#  왜: 「큰 파이썬이 0개면 시작」 을 두 쪽이 같은 분에 보고 같이 출발했다
#      (10/13 13:09 BRANCH2 + 예측 기록 · 14:44 C + 현금 찾기 → 15:41 C 가 메모리로 꺼짐)
#  어떻게: data\_labs\_BIG.lock 을 **CreateNew**(이미 있으면 실패 = 한 쪽만 성공)로 만든 쪽만 큰 계산을 띄운다
#          · 자물쇠 주인(PowerShell PID)이 죽었으면 낡은 자물쇠로 보고 지운다
#  쓰는 법: . "$PSScriptRoot\biglock.ps1"  →  if (큰판잡기 "이름") { … 큰 파이썬 … ; 큰판놓기 }
# ==============================================================
$큰판자물쇠 = Join-Path (Split-Path $PSScriptRoot -Parent) "data\_labs\_BIG.lock"

function 큰판잡기($이름, $최대분 = 1440) {
    $끝 = (Get-Date).AddMinutes($최대분)
    $알림 = $false
    while ((Get-Date) -lt $끝) {
        try {
            $fs = [IO.File]::Open($큰판자물쇠, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            $b = [Text.Encoding]::UTF8.GetBytes("$PID|$이름|$(Get-Date -f 'MM-dd HH:mm')")
            $fs.Write($b, 0, $b.Length)
            $fs.Close()
            return $true
        } catch {
            $글 = ""
            try { $글 = [IO.File]::ReadAllText($큰판자물쇠, [Text.Encoding]::UTF8) } catch { }
            $주인 = ($글 -split '\|')[0]
            if ($주인 -match '^\d+$' -and -not (Get-Process -Id ([int]$주인) -ErrorAction SilentlyContinue)) {
                Remove-Item $큰판자물쇠 -Force -ErrorAction SilentlyContinue      # 주인이 죽은 낡은 자물쇠
                continue
            }
            if (-not $알림 -and (Get-Command 적기 -ErrorAction SilentlyContinue)) { 적기 "  [자물쇠] $이름 — 다른 큰 계산이 돈다($글) — 기다린다" | Out-Null; $알림 = $true }
            Start-Sleep 30
        }
    }
    return $false
}

function 큰판놓기 {
    try {
        $글 = [IO.File]::ReadAllText($큰판자물쇠, [Text.Encoding]::UTF8)
        if (($글 -split '\|')[0] -eq "$PID") { Remove-Item $큰판자물쇠 -Force -ErrorAction SilentlyContinue }
    } catch { }
}
