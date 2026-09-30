#!/usr/bin/env python3
r"""
build_qt_states.py — 퀀트 화면을 **상태별로 강제로** 그린다 (2026-09-29)

QUANT-ANSWER-0929 답 5: 「pre · buy · none 세 상태 — 네가 만들어 올려라.
오늘 값으로 세 상태 화면을 강제로 그려 게시 폴더에 올리고 (`qt-pre.html` ·
`qt-buy.html` · `qt-none.html`처럼 이름만 다르게), 경로를 알려줘. **buy를 제일 먼저.**」

## 왜 필요한가
퀀트 장은 **상태에 따라 모양이 다르다** (제목·배지·4행 라벨·칩). 그런데 그날의
실제 상태 하나만 게시되므로 나머지 셋은 **한 번도 아무도 못 봤다.**
특히 buy 는 **돈이 나가는 날 화면**인데 실측된 적이 없다.

## 어떻게
오늘 사이트(`data/briefing-site.html`)를 그대로 쓰고 **퀀트 칸 하나만** 갈아 끼운다.
그래야 글꼴·배율·JS 가 게시본과 **똑같이** 돌아 디자인이 떠서 잰 값이 믿을 만하다.
  · buy  — 08:55 확정 + 앞 8종목에 「오늘산다」
  · pre  — 08:55 전 (예상시장갭·상대갭·문턱가를 지운다)
  · none — 후보 0개

⚠️ **강제로 그린 화면이다.** 공개 주소에 「오늘 살 것: 8개 · 지정가 주문」이 뜨면
   진짜 매수 신호로 읽힌다. 카드 **바깥** 맨 위에 「디자인 점검용 · 실제 신호 아님」
   띠를 붙인다 — 카드 치수에는 영향이 없다.
⚠️ 기록(`forward-log.jsonl`)은 **읽기만** 한다. 강제 상태는 메모리 안 사본에만 만든다.

쓰기
    python scripts/build_qt_states.py            -> data/qt-buy.html · qt-pre.html · qt-none.html
    python scripts/build_qt_states.py --only buy
"""
import argparse
import copy
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
_DATA = os.path.join(os.path.dirname(_HERE), "data")

import quant_cards  # noqa: E402
import rule_def as R  # noqa: E402

상태들 = ("buy", "pre", "none")   # ⭐ buy 먼저 (디자인 답 5)

_띠 = {
    "buy": "BUY · 사는 날",
    "pre": "PRE · 08:00~08:55 후보",
    "none": "NONE · 후보 0개",
}


def _강제(q, 상태):
    r"""기록 한 줄의 **사본**을 그 상태로 바꾼다. 원본은 안 건드린다"""
    q = copy.deepcopy(q)
    후보 = q.get("후보") or []
    동 = q.setdefault("동시호가", {})
    if 상태 == "none":
        q["후보"] = []
        return q
    if 상태 == "pre":
        # 08:55 전 — 예상체결가를 아직 안 받았다. 상대갭·문턱가도 없다
        동["예상시장갭"] = None
        for x in 후보:
            for k in ("상대갭", "문턱가", "주문가", "규칙매수", "오늘산다"):
                x.pop(k, None)
        return q
    if 상태 == "buy":
        # 08:55 확정 + 앞에서부터 최대 자리만큼 「산다」
        if 동.get("예상시장갭") is None:
            동["예상시장갭"] = 0.0
        _최 = (R.하루최대종목 + getattr(R, "섹터전용자리", 0)
          + sum(v["자리"] for v in getattr(R, "바구니전용", {}).values()))   # ⭐ 9/30 원전 자리
        for i, x in enumerate(후보):
            산다 = i < _최
            x["규칙매수"] = 산다
            x["오늘산다"] = 산다
            if 산다:
                _문 = x.get("문턱가") or x.get("어제종가")
                x["문턱가"] = _문
                x["주문가"] = _문
                if x.get("상대갭") is None:
                    x["상대갭"] = R.상대갭문턱 - 0.5
        return q
    raise ValueError(상태)


def _퀀트칸_자리(h):
    r"""사이트 HTML 안 퀀트 칸의 **시작·끝**. 칸 안에 카드 `<section>` 이 겹겹이라
    짝을 세어 닫는 자리를 찾는다 (정규식 `.*?</section>` 은 첫 카드에서 멈춘다)"""
    s = h.find('<section class="view" id="qt"')
    if s < 0:
        return None
    깊이, i = 0, s
    while True:
        a = h.find("<section", i)
        b = h.find("</section>", i)
        if b < 0:
            return None
        if 0 <= a < b:
            깊이 += 1
            i = a + 8
        else:
            깊이 -= 1
            i = b + len("</section>")
            if 깊이 == 0:
                return s, i


def 그리기(상태, 사이트, 줄):
    import build_site  # 보유 목록을 같은 방식으로 만든다
    q = _강제(줄[-1], 상태)
    try:
        보유 = build_site._보유(줄)
    except Exception:  # noqa: BLE001
        보유 = []
    칸 = quant_cards.quant_view(q, 보유)
    # ⚠️⚠️ 2026-09-29 — **게시본과 똑같이 다듬는다.** `build_site` 는 내보낼 때
    #    `—` 를 `·` 로 바꾸는데, 여기서는 퀀트 칸을 **날것으로** 끼워 그 단계를 건너뛰었다.
    #    그래서 디자인이 잰 화면에만 「—」 둘이 있었다(게시본엔 0곳).
    #    강제 화면이 게시본과 **글자까지** 같아야 잰 값이 믿을 만하다
    칸 = 칸.replace("—", "·")
    자리 = _퀀트칸_자리(사이트)
    if not 자리:
        raise SystemExit("사이트에서 퀀트 칸(#qt)을 못 찾았다")
    a, b = 자리
    h = 사이트[:a] + 칸 + 사이트[b:]
    # 카드 **바깥** 맨 위 띠 — 카드 치수에는 영향이 없다
    _경고 = (f'<div style="position:sticky;top:0;z-index:99;background:#1c1813;color:#fff;'
             f'font:600 14px/1.5 sans-serif;text-align:center;padding:8px 12px">'
             f'디자인 점검용 강제 화면 · {_띠[상태]} · 실제 매수 신호가 아닙니다</div>')
    # 열자마자 퀀트 화면을 연다 — 단추를 누르는 것과 똑같이
    _열기 = ('<script>window.addEventListener("load",function(){'
             'var b=document.getElementById("btn-qt");'
             'if(b){b.click();}else if(typeof show==="function"){show("qt");}'
             'var q=document.getElementById("qt");if(q)q.hidden=false;'
             '});</script>')
    # ⚠️ 이 사이트 파일에는 `<body>` 태그가 **없다** (`</body>` 도 없다).
    #    `<body` 를 찾아 넣었더니 띠가 **조용히 안 붙었다** — 퀀트 칸 여는 태그 바로 뒤에 넣는다
    _k = h.index(">", h.index('<section class="view" id="qt"')) + 1
    h = h[:_k] + _경고 + h[_k:]
    assert "실제 매수 신호가 아닙니다" in h, "경고 띠가 안 붙었다"
    h = h + _열기
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=상태들)
    ap.add_argument("--site", default=os.path.join(_DATA, "briefing-site.html"))
    a = ap.parse_args()
    사이트 = io.open(a.site, encoding="utf-8-sig").read()
    줄 = [json.loads(x) for x in
         io.open(os.path.join(_DATA, "forward-log.jsonl"), encoding="utf-8") if x.strip()]
    나온 = {}
    for 상태 in ([a.only] if a.only else 상태들):
        h = 그리기(상태, 사이트, 줄)
        p = os.path.join(_DATA, f"qt-{상태}.html")
        io.open(p, "w", encoding="utf-8").write(h)
        나온[상태] = {"파일": p, "크기KB": round(len(h.encode("utf-8")) / 1024, 1)}
    print(json.dumps({"ok": True, "만든것": 나온}, ensure_ascii=False))


if __name__ == "__main__":
    main()
