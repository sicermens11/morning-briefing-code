#!/usr/bin/env python3
r"""
publish_pages.py — 만들어진 사이트를 GitHub Pages에 올린다 (고정 링크 · 항상 최신)

⚠️ **왜 Artifact에서 옮겼나** (2026-08-27).
   Artifact 공유 링크는 **공유한 시점의 버전이 고정**돼 나간다. 매일 새로 올려도
   링크로 들어온 사람에게는 옛날 것이 계속 보인다. "고정 링크로 매일 아침 최신을
   본다"는 목적 자체가 성립하지 않았다. 정적 호스팅은 주소가 그대로고 파일만 바뀐다.

⚠️ **왜 git·gh를 안 쓰나** (2026-08-27).
   git+gh 경로는 `gh auth login` 브라우저 인증이 필요한데, 그건 사람이 터미널에서
   직접 해야 한다. GitHub API로 파일만 PUT 하면 그 단계가 통째로 없어진다.
   자동 실행에서 부품이 줄어드는 것도 이득이다 — git이 깨질 일 자체가 없다.

⚠️ **내용이 공개된다.** 주소를 아는 사람은 로그인 없이 누구나 본다. 검색 수집은
   두 겹으로 막는다(`robots.txt` + 페이지 안의 `noindex`). 다만 "검색에 안 뜬다"이지
   "비공개"가 아니다. 종목·등급·진입가가 인터넷에 놓인다. 그걸 알고 고른 경로다.

한 번만 해 두면 되는 준비(전부 웹에서 한다):
   1. github.com 에서 저장소를 **public** 으로 만든다 (이름 예: morning-briefing)
   2. Settings → Developer settings → Personal access tokens → Fine-grained tokens
      · Repository access : 그 저장소 하나만
      · Permissions       : Contents = Read and write, Pages = Read and write
   3. 받은 토큰을 `data\secrets.json` 에 `"GITHUB_TOKEN": "..."` 로 넣는다
      ⚠️ 토큰을 채팅에 붙여넣지 않는다. 대화 기록에 남는다.

⚠️ 미세 토큰(fine-grained)은 **만료된다.** 만료되면 어느 날 조용히 게시가 멈춘다.
   그래서 만료가 30일 안으로 들어오면 여기서 경고를 찍는다.
"""
import argparse
import base64
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

API = "https://api.github.com"

# 검색 차단의 한 겹. 나머지 한 겹은 `build_site.py`가 넣는 페이지 안의 noindex 태그다.
# ⚠️ robots.txt 만으로는 부족하다 — 다른 데서 링크가 걸리면 본문 없이 색인될 수 있다.
ROBOTS = "User-agent: *\nDisallow: /\n"


def _req(method, path, token, body=None):
    """GitHub API 한 번. 토큰은 **절대 출력하지 않는다.**"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = Request(API + path, data=data, method=method)
    r.add_header("Authorization", "Bearer " + token)
    r.add_header("Accept", "application/vnd.github+json")
    r.add_header("X-GitHub-Api-Version", "2022-11-28")
    r.add_header("User-Agent", "morning-briefing")
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urlopen(r, timeout=60) as res:
            raw = res.read().decode("utf-8")
            return res.status, (json.loads(raw) if raw else {}), dict(res.headers)
    except HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:  # noqa: BLE001
            payload = {"message": raw[:300]}
        return e.code, payload, dict(e.headers or {})


def _blob_sha(data: bytes) -> str:
    """git이 파일에 매기는 해시. 이걸 비교해서 **안 바뀐 파일은 안 올린다**(빈 커밋 방지)."""
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def put_file(owner, repo, path, data: bytes, token, message):
    """파일 하나를 올린다. 내용이 같으면 건너뛴다. 반환: 'olim' | 'gatta' | 오류문자열"""
    code, cur, _ = _req("GET", f"/repos/{owner}/{repo}/contents/{path}", token)
    sha = None
    if code == 200 and isinstance(cur, dict):
        sha = cur.get("sha")
        if sha == _blob_sha(data):
            return "gatta"
    elif code not in (404, 200):
        return f"기존 파일 확인 실패({code}): {cur.get('message', '')}"

    body = {"message": message,
            "content": base64.b64encode(data).decode("ascii")}
    if sha:
        body["sha"] = sha
    code, res, _ = _req("PUT", f"/repos/{owner}/{repo}/contents/{path}", token, body)
    if code in (200, 201):
        return "olim"
    return f"올리기 실패({code}): {res.get('message', '')}"


def ensure_pages(owner, repo, token, branch="main"):
    """Pages를 켠다. 이미 켜져 있으면 조용히 넘어간다.

    ⚠️ 브랜치 이름을 `main`으로 박지 않는다. 계정 설정에 따라 `master`일 수 있고,
       그러면 Pages가 빈 브랜치를 보게 돼서 페이지가 영원히 안 뜬다.
    """
    code, res, _ = _req("GET", f"/repos/{owner}/{repo}/pages", token)
    if code == 200:
        return None
    code, res, _ = _req("POST", f"/repos/{owner}/{repo}/pages", token,
                        {"source": {"branch": branch, "path": "/"}})
    if code in (201, 204, 409):
        return None
    # ⚠️ 여기서 죽이지 않는다. 파일은 이미 올라갔고, Pages는 웹에서 켤 수 있다.
    return (f"Pages 자동 활성화 실패({code}: {res.get('message', '')}). "
            f"저장소 Settings → Pages 에서 Branch를 main / (root)로 두고 Save 하면 된다.")


def token_expiry_note(headers):
    """미세 토큰 만료일이 임박하면 알린다. 조용히 멈추는 게 제일 나쁜 실패다."""
    exp = headers.get("github-authentication-token-expiration")
    if not exp:
        return None
    try:
        d = datetime.fromisoformat(exp.replace(" UTC", "+00:00").replace(" ", "T", 1))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        left = (d - datetime.now(timezone.utc)).days
    except Exception:  # noqa: BLE001
        return None
    if left <= 30:
        return f"⚠️ GitHub 토큰이 {left}일 뒤 만료된다({exp}). 새로 발급해 secrets.json을 바꿔야 게시가 계속된다."
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="올릴 사이트 HTML")
    ap.add_argument("--repo", default="morning-briefing")
    ap.add_argument("--owner", default=None, help="비우면 토큰 주인으로 잡는다")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    out = {"ok": False}

    token = config.get("GITHUB_TOKEN")
    if not token:
        out["오류"] = ("GITHUB_TOKEN이 없다. data\\secrets.json 에 넣거나 환경변수로 준다. "
                     "(이 파일 맨 위 설명 참고)")
        print(json.dumps(out, ensure_ascii=False))
        return 2

    if not os.path.exists(a.site):
        out["오류"] = f"사이트 파일이 없다: {a.site}"
        print(json.dumps(out, ensure_ascii=False))
        return 2

    code, me, hdr = _req("GET", "/user", token)
    if code != 200:
        out["오류"] = f"토큰이 안 먹는다({code}): {me.get('message', '')}"
        print(json.dumps(out, ensure_ascii=False))
        return 2
    owner = a.owner or me.get("login")
    out["계정"] = owner
    note = token_expiry_note(hdr)
    if note:
        out["경고"] = note

    code, repo_info, _ = _req("GET", f"/repos/{owner}/{a.repo}", token)
    branch = (repo_info or {}).get("default_branch") or "main"
    if code == 200 and repo_info.get("private"):
        # ⚠️ 비공개 저장소의 Pages는 유료 요금제에서만 켜진다. 미리 말해준다.
        out.setdefault("안내", []).append(
            "저장소가 private이다. Pages는 public 저장소에서만 무료로 켜진다 — "
            "Settings → General 맨 아래에서 public으로 바꾸면 된다.")
    if code != 200:
        out["오류"] = (f"저장소를 못 찾는다: {owner}/{a.repo}. "
                     f"github.com/new 에서 public으로 만들고, 토큰 권한에 그 저장소가 들어있는지 본다.")
        print(json.dumps(out, ensure_ascii=False))
        return 2

    with open(a.site, "rb") as f:
        html = f.read()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    files = [("index.html", html),
             ("robots.txt", ROBOTS.encode("utf-8")),
             (".nojekyll", b"")]

    if a.dry_run:
        out.update(ok=True, dry_run=True,
                   올릴것=[p for p, _ in files], 크기KB=round(len(html) / 1024, 1))
        print(json.dumps(out, ensure_ascii=False))
        return 0

    결과 = {}
    for path, data in files:
        r = put_file(owner, a.repo, path, data, token, f"브리핑 {stamp}")
        결과[path] = r
        if r not in ("olim", "gatta"):
            out["오류"] = r
            out["부분결과"] = 결과
            print(json.dumps(out, ensure_ascii=False))
            return 1
    out["파일"] = 결과

    pg = ensure_pages(owner, a.repo, token, branch)
    if pg:
        out.setdefault("안내", []).append(pg)

    out["ok"] = True
    out["주소"] = f"https://{owner}.github.io/{a.repo}/"
    out["크기KB"] = round(len(html) / 1024, 1)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
