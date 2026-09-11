<#
publish_pages.ps1 — 사이트를 GitHub Pages에 올린다 (고정 링크 · 로그인 불필요 · 항상 최신)

⚠️ **왜 Artifact에서 옮겼나** (2026-08-27).
   Artifact 공유 링크는 **공유 시점에 고정된 버전**을 내보낸다. 매일 새로 올려도
   링크로 들어온 사람에게는 옛 버전이 계속 나가서, "고정 링크로 매일 아침 최신을
   본다"는 목적 자체가 성립하지 않았다. 로그인하면 최신이 보이지만 지인 공유가 죽는다.
   정적 호스팅은 그 문제가 없다 — 주소는 그대로고 파일만 갈아 끼운다.

⚠️ **내용이 공개된다.** 주소를 아는 사람은 누구나 본다. 검색 수집은 두 겹으로 막았다
   (`robots.txt` + 페이지의 `noindex`) — 다만 "검색에 안 뜬다"이지 "비공개"가 아니다.
   종목·등급·진입가가 인터넷에 놓인다는 뜻이다. 그걸 알고 고른 경로다.

⚠️ **git·gh를 쓰지 않는다** (2026-08-27 변경). 그 경로는 `gh auth login` 브라우저
   인증이 필요해서 사람이 터미널에 붙어 있어야 했다. 지금은 `publish_pages.py`가
   GitHub API로 파일만 올린다 — 터미널 인증이 없고, 자동 실행에서 깨질 부품도 없다.

한 번만 해 두면 되는 준비(전부 **웹에서** 한다):
   1. github.com/new 에서 저장소를 **public**으로 만든다 (이름 예: morning-briefing)
   2. Settings → Developer settings → Personal access tokens → Fine-grained tokens
      · Repository access : 그 저장소 하나
      · Permissions       : Contents = Read and write, Pages = Read and write
   3. 토큰을 `data\secrets.json` 의 `"GITHUB_TOKEN"` 에 넣는다
      ⚠️ 토큰을 채팅에 붙여넣지 않는다. 대화 기록에 남는다.

그다음부터는 매일 `run-briefing.ps1`이 알아서 부른다.
#>
param(
    # 저장소 이름. 주소가 이걸로 정해진다: https://<계정>.github.io/<Repo>/
    [string]$Repo = 'morning-briefing',
    # 무엇을 할지 보여주기만 하고 실제로는 안 올린다.
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$siteHtml = Join-Path $root 'data\briefing-site.html'

function Say($m) { Write-Output "  $m" }

# --- 사이트 만들기 -----------------------------------------------------------
# ⚠️⚠️ **빌드가 실패하면 여기서 멈춘다.** 2026-08-28에 `build_site.py`가 예외로 죽었는데도
#    파일이 **어제 것으로 남아 있어서** Test-Path를 통과했고, 그대로 올라갔다.
#    화면은 멀쩡해 보이고 주소도 정상이라 **틀린 줄을 아무도 모른다** — 새로 만든 것이
#    안 올라간 게 아니라 **옛날 것이 새것인 척** 올라간 것이라 더 나쁘다.
#    그래서 두 가지를 같이 본다: 빌드가 ok를 냈는가, 그리고 **파일이 방금 쓰였는가.**
$t0 = Get-Date
Say "사이트 생성 중..."
$build = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'build_site.py' -Args @('--out', $siteHtml)
Say $build
if (-not (Test-Path $siteHtml)) { Write-Output "사이트 파일이 안 만들어졌다"; exit 1 }
$ok = $false
try { $ok = [bool](($build | Where-Object { $_ -match '"ok"' } | Select-Object -Last 1) `
        | ConvertFrom-Json).ok } catch { $ok = $false }
if (-not $ok) {
    Write-Output "사이트 생성이 실패했다 — 올리지 않는다(어제 페이지 유지). 위 오류를 본다."
    exit 1
}
if ((Get-Item $siteHtml).LastWriteTime -lt $t0) {
    Write-Output "사이트 파일이 이번에 안 쓰였다(어제 것이 남아 있다) — 올리지 않는다"
    exit 1
}

# --- 서술 파일 검사 -----------------------------------------------------------
# ⚠️ 레이아웃보다 **먼저** 본다. 키가 빠지면 화면이 안 깨지고 **조용히 빈다** —
#    레이아웃 검사는 빈 화면을 통과시킨다. 그래서 이쪽이 앞에 있어야 한다.
$copyChk = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'check_copy.py'
Say $copyChk
try {
    $cc = $copyChk | ConvertFrom-Json
    if ($cc.경고) { $cc.경고 | ForEach-Object { Write-Output "    · $_" } }
    if (-not $cc.ok) {
        Write-Output "서술 파일이 모자라 게시하지 않는다(어제 페이지 유지):"
        $cc.오류 | ForEach-Object { Write-Output "    · $_" }
        exit 1
    }
} catch { Say "서술 검사 결과를 못 읽었다 — 그대로 진행한다" }

# --- 레이아웃 검사 -----------------------------------------------------------
# ⚠️ 깨진 페이지를 공개된 주소에 올리지 않는다. 여기는 지인도 보는 곳이다.
$cardsHtml = Join-Path $root 'data\briefing-cards.html'
& (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'build_cards.py' `
    -Args @('--date', 'all', '--out', $cardsHtml) | Out-Null
$chk = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'check_layout.py' `
    -Args @('--cards', $cardsHtml, '--site', $siteHtml)
try {
    $cj = $chk | ConvertFrom-Json
    # ⚠️ 경고(카드 넘침·작은 글자)는 **막지 않는다.** 보기 나쁠 뿐 읽을 수는 있고,
    #    그걸로 그날 웹 전체를 어제 것으로 남기는 편이 더 나쁘다(2026-08-28 판단).
    if ($cj.경고) {
        Write-Output "레이아웃 경고 — 올리되 고칠 것:"
        $cj.경고 | ForEach-Object { Write-Output "    · $_" }
    }
    if (-not $cj.ok) {
        Write-Output "레이아웃 **치명** 실패 — 올리지 않는다(어제 페이지 유지):"
        $cj.실패 | ForEach-Object { Write-Output "    · $_" }
        exit 1
    }
    Say "레이아웃 검사 통과"
} catch { Say "레이아웃 검사 결과를 못 읽었다($chk) — 그대로 진행한다" }

# --- 올리기 ------------------------------------------------------------------
# 여기서부터는 파이썬이 GitHub API로 직접 올린다. `index.html` `robots.txt` `.nojekyll`
# 세 개뿐이고, 내용이 그대로면 건너뛴다(빈 커밋을 안 남긴다).
$pubArgs = @('--site', $siteHtml, '--repo', $Repo)
if ($DryRun) { $pubArgs += '--dry-run' }
$pub = & (Join-Path $PSScriptRoot 'run-py.ps1') -Script 'publish_pages.py' -Args $pubArgs
Say $pub

try {
    $pj = $pub | ConvertFrom-Json
    if ($pj.경고) { Write-Output "  $($pj.경고)" }
    if (-not $pj.ok) { Write-Output "게시 실패: $($pj.오류)"; exit 1 }
    if ($pj.안내) { $pj.안내 | ForEach-Object { Write-Output "  $_" } }
    if ($pj.주소) {
        Say "올림 완료 → $($pj.주소)"
        # 런처와 스킬이 읽는 고정 주소. 여기 한 곳만 보면 된다.
        Set-Content (Join-Path $root 'data\site-url.txt') $pj.주소 -Encoding utf8
    }
} catch {
    Write-Output "게시 결과를 못 읽었다 — 위 출력을 확인한다"
    exit 1
}
