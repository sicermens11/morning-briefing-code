#!/usr/bin/env python3
r"""
kakao_notify.py — 카카오톡 「나에게 보내기」 알림 (2026-10-19 · 사용자 「알림은 카톡으로 하자.」)

왜: 계정 잠김·Claude 인증 만료로 09:05 확인 같은 예약이 안 돌아도 아무도 몰랐다(9거래일 중 5일).
    Claude 의 카카오 도구는 Claude 가 깨어 있을 때만 된다 → PC 파이썬이 카카오 공식 API 로 **직접** 보낸다.

열쇠: secrets.json 의 KAKAO_REST_KEY (config.get 으로만 읽는다 · 채팅에 붙이지 않는다)
토큰: data/_kakao_token.json (저장소에 안 올린다 · .gitignore) — 처음 한 번 kakao_setup.py 로 만든다
      access 토큰은 몇 시간, refresh 토큰은 두 달쯤 산다 → 보낼 때마다 필요하면 스스로 새로 받는다

쓰는 법:
    python scripts\kakao_notify.py "보낼 말"          (200자 안쪽 권장)
    from kakao_notify import 보내기; 보내기("…")      → True/False (실패해도 예외를 안 던진다)
⚠️ 조회·알림만. 주문은 없다.
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.path.join(_BASE, "data", "_kakao_token.json")
LOG = os.path.join(_BASE, "data", "_kakao.log")
SITE = "https://sicermens11.github.io/morning-briefing/"


def _기록(s):
    try:
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {s}\n")
    except Exception:  # noqa: BLE001
        pass


def _post(url, data, headers=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode("utf-8"),
                                 headers=dict({"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _토큰읽기():
    try:
        return json.load(io.open(TOKEN, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _토큰쓰기(t):
    io.open(TOKEN, "w", encoding="utf-8").write(json.dumps(t, ensure_ascii=False))


def _새토큰(t):
    """access 토큰이 낡았으면 refresh 로 새로 받는다 (refresh 가 새로 오면 그것도 바꿔 둔다)"""
    key = config.get("KAKAO_REST_KEY")
    d = {"grant_type": "refresh_token", "client_id": key, "refresh_token": t["refresh_token"]}
    sec = config.get("KAKAO_CLIENT_SECRET")
    if sec:
        d["client_secret"] = sec
    r = _post("https://kauth.kakao.com/oauth/token", d)
    t["access_token"] = r["access_token"]
    t["access_until"] = time.time() + int(r.get("expires_in", 3600)) - 120
    if r.get("refresh_token"):
        t["refresh_token"] = r["refresh_token"]
        t["refresh_until"] = time.time() + int(r.get("refresh_token_expires_in", 0))
    _토큰쓰기(t)
    return t


def 보내기(말, 링크=SITE):
    r"""카톡 나에게 보내기. 성공 True · 실패 False (예외를 밖으로 안 던진다 — 알림이 일을 막으면 안 된다)"""
    try:
        t = _토큰읽기()
        if not t or not config.get("KAKAO_REST_KEY"):
            _기록("❌ 토큰·열쇠 없음 — kakao_setup.py 를 먼저")
            return False
        if time.time() >= float(t.get("access_until") or 0):
            t = _새토큰(t)
        tpl = {"object_type": "text", "text": str(말)[:990],
               "link": {"web_url": 링크, "mobile_web_url": 링크}, "button_title": "브리핑 열기"}
        r = _post("https://kapi.kakao.com/v2/api/talk/memo/default/send",
                  {"template_object": json.dumps(tpl, ensure_ascii=False)},
                  {"Authorization": f"Bearer {t['access_token']}"})
        ok = r.get("result_code") == 0
        _기록(("✅ " if ok else "❌ ") + str(말)[:80].replace("\n", " ") + ("" if ok else f" · {r}"))
        return ok
    except Exception as e:  # noqa: BLE001
        _몸 = ""
        try:
            _몸 = e.read().decode("utf-8", "replace")[:200]   # HTTPError 면 카카오가 준 까닭(토큰·열쇠는 안 들어 있다)
        except Exception:  # noqa: BLE001
            pass
        _기록(f"❌ 보내기 실패 {type(e).__name__}: {str(e)[:120]} {_몸}")
        return False


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    말 = " ".join(sys.argv[1:]) or "[브리핑 알림 시험] PC 에서 직접 보낸 카톡입니다."
    print("보냄" if 보내기(말) else "실패 — data/_kakao.log 를 보세요")
