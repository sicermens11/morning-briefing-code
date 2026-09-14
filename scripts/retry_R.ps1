# ==============================================================
#  retry_R.ps1 — R판을 **다시** 돌린다 (2026-09-14 밤 · MemoryError 고친 뒤)
#
#  왜
#  ---
#  R판이 20:28 에 `MemoryError` 로 죽었다:
#      s = 조건[라1] & 조건[라2]      ← B절 「둘씩 5,356쌍」
#  재료를 27가지 더해 조건이 **110개**가 됐는데, 조건 하나가 `set(사건 자리)` 이고
#  사건이 **108만 건** — set 하나 ~65MB × 110 = **7GB**. 거기에 통과한 쌍마다
#  교집합 set 을 또 담았다.
#
#  고침 (combo4_lab)
#    · 조건을 **int 비트마스크**로 — 110 × 136KB = 15MB (7GB → 15MB)
#    · 개수는 `.bit_count()` · 자리는 필요할 때만 바이트 표로 뽑는다
#    · 쌍에는 이름만 담고, C절이 쓰는 상위 40개만 마스크를 다시 만든다
#    ⚠️ 집합이 바뀐 게 아니라 **그릇만** 바뀌었다 (단위 시험으로 확인: 교집합 40 = 40)
#
#  ⚠️ 밤 줄(S→U→P→Q→T)이 **다 끝난 뒤**에 시작한다 — 로그의 「모두 끝」을 기다린다.
#     둘이 같이 깨어나 9GB 가 겹치는 것을 막으려고 큰파이썬 검사가 아니라
#     **로그 문구**를 본다 (그게 확실하다)
# ==============================================================
$ErrorActionPreference = "Continue"
Set-Location "C:\Users\mrblue\Claude\morning breifing_code"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$py = "C:\Users\mrblue\AppData\Local\Programs\Python\Python313\python.exe"
$log = "run-logs\retry_R_$(Get-Date -f yyyyMMdd_HHmm).log"
function 적기($s) { "$(Get-Date -f 'MM-dd HH:mm')  $s" | Tee-Object $log -Append }

function 밤줄끝났나 {
    $l = Get-ChildItem "run-logs\night_queue_*.log" -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $l) { return $false }
    return ((Get-Content $l.FullName -Raw) -match '밤 줄 모두 끝')
}
function 큰파이썬 {
    @(Get-Process python -ErrorAction SilentlyContinue |
      Where-Object { $_.WorkingSet64 -gt 1GB }).Count
}
function 아침인가 {
    $h = (Get-Date).Hour; $m = (Get-Date).Minute
    return (($h -eq 7 -and $m -ge 20) -or ($h -ge 8 -and $h -lt 10))
}

적기 "[0] 밤 줄이 끝나길 기다린다"
$분 = 0
while (-not (밤줄끝났나) -and ($분 -lt 660)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
적기 "[0] $분 분 기다림 (밤 줄 끝: $(밤줄끝났나))"
while ((큰파이썬) -gt 0 -and ($분 -lt 720)) { Start-Sleep -Seconds 60; $분 = $분 + 1 }
if (아침인가) { 적기 "⚠️ 아침 시간대라 시작하지 않는다 — 낮에 사람이 돌린다"; exit 0 }

$이름 = "R_새재료_전체기간"
$결과 = "data\_labs\2026-09-14_$이름.txt"
if ((Test-Path $결과) -and ((Get-Item $결과).Length -gt 50000)) {
    적기 "[$이름] 이미 제대로 있다 — 건너뛴다"; exit 0
}
적기 "[$이름] 다시 시작 (비트마스크로 고친 뒤)"
$env:LAB_OUT = "2026-09-14_$이름.txt"
& $py "scripts\combo4_lab.py" 2>&1 | Select-Object -Last 3 | Tee-Object $log -Append
Remove-Item env:LAB_OUT -ErrorAction SilentlyContinue
if (Test-Path $결과) {
    $크기 = (Get-Item $결과).Length
    적기 "[$이름] 끝 — $('{0:N0}' -f $크기) B"
    if ($크기 -lt 50000) { 적기 "⚠️ 또 작다 — 로그를 봐라" }
}
else { 적기 "⚠️ 결과 파일이 없다" }
적기 "끝"
