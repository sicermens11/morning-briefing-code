#!/usr/bin/env python3
r"""
kakao_setup.py — 카카오 알림 처음 한 번 연결 (2026-10-19)

순서: 카카오 개발자 사이트에서 앱 등록 → secrets.json 에 KAKAO_REST_KEY 넣기 → 이 파일 실행
  python scripts\kakao_setup.py
  → 브라우저가 카카오 로그인·동의 화면을 연다 → 「동의하고 계속하기」
  → 이 PC 의 http://localhost:8765/kakao 로 돌아오면 토큰을 받아 data/_kakao_token.json 에 둔다
  → 시험 카톡 한 통을 보낸다
⚠️ 토큰 파일은 저장소에 안 올린다(.gitignore). 열쇠·토큰을 화면이나 채팅에 찍지 않는다.
"""
import http.server
import json
import os
import sys
import threading
import time
import urllib.parse
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import kakao_notify as K  # noqa: E402

REDIRECT = "http://localhost:8765/kakao"
받은 = {}


class _받기(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        받은["code"] = (q.get("code") or [None])[0]
        받은["error"] = (q.get("error_description") or q.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        글 = "연결됐습니다. 이 창은 닫아도 됩니다." if 받은.get("code") else f"실패: {받은.get('error')}"
        self.wfile.write(f"<meta charset='utf-8'><p style='font:20px sans-serif'>{글}</p>".encode("utf-8"))

    def log_message(self, *a):  # 조용히
        pass


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    key = config.get("KAKAO_REST_KEY")
    if not key:
        print("❌ secrets.json 에 KAKAO_REST_KEY 가 없습니다 — 넣고 다시 실행하세요")
        return 1
    srv = http.server.HTTPServer(("127.0.0.1", 8765), _받기)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = ("https://kauth.kakao.com/oauth/authorize?" + urllib.parse.urlencode(
        {"client_id": key, "redirect_uri": REDIRECT, "response_type": "code", "scope": "talk_message"}))
    print("브라우저에서 카카오 로그인·동의를 해 주세요 (5분 기다립니다)…", flush=True)
    # 10/19 — webbrowser.open 이 배경 셸에서 창을 안 띄웠다 → 윈도 기본 브라우저로 직접 연다
    try:
        os.startfile(url)  # noqa: S606
    except Exception:  # noqa: BLE001
        webbrowser.open(url)
    for _ in range(600):
        if 받은:
            break
        time.sleep(0.5)
    srv.shutdown()
    if not 받은.get("code"):
        print(f"❌ 동의 코드를 못 받았습니다: {받은.get('error') or '시간 초과'}")
        return 1
    d = {"grant_type": "authorization_code", "client_id": key, "redirect_uri": REDIRECT, "code": 받은["code"]}
    sec = config.get("KAKAO_CLIENT_SECRET")
    if sec:
        d["client_secret"] = sec
    try:
        r = K._post("https://kauth.kakao.com/oauth/token", d)
    except Exception as e:  # noqa: BLE001
        print(f"❌ 토큰 받기 실패: {type(e).__name__} — 앱의 Redirect URI·동의항목을 확인하세요")
        return 1
    t = {"access_token": r["access_token"], "access_until": time.time() + int(r.get("expires_in", 3600)) - 120,
         "refresh_token": r["refresh_token"], "refresh_until": time.time() + int(r.get("refresh_token_expires_in", 0)),
         "scope": r.get("scope"), "만든때": time.strftime("%Y-%m-%d %H:%M")}
    K._토큰쓰기(t)
    print(f"✅ 토큰 저장 (refresh 약 {int(r.get('refresh_token_expires_in', 0)) // 86400}일) · 동의 범위 {r.get('scope')}")
    ok = K.보내기("[브리핑 알림] PC 에서 직접 보내는 카톡 알림이 연결됐습니다.")
    print("✅ 시험 카톡 보냄" if ok else "❌ 시험 카톡 실패 — data/_kakao.log")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
