#!/usr/bin/env python3
r"""
market_fix.py — **아침 스냅샷의 「개장 전 0」 을 화면에 내기 전에 고친다** (2026-10-08)

독립 검사(10/8): 아침 08:0x 에 받은 fetch_market 스냅샷은 장이 열리기 전이라
  · 코스피 등락률 0.00 (같은 화면 표지·본문은 −1.98% — 한 화면에서 숫자가 어긋났다)
  · 업종·테마 순위 전부 0.00% (엿새 내내 같은 다섯 줄이 「어제 오른 업종」 으로 나갔다)
  · 외국인 순매수 상위 등락률 0.00
fetch_market 은 10/8 부터 받을 때 고친다. 하지만 화면은 **지난 날 스냅샷으로 매번 다시 만든다** — 여기서도 고친다.

쓰는 곳: build_cards · build_scroll — `mk = 시장정리(mk, o["date"])`
"""
import datetime as dt
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_HERE), "data")


def _영(v):
    try:
        return abs(float(str(v).replace(",", "").replace("+", ""))) < 1e-9
    except (TypeError, ValueError):
        return False


def _전거래일코스피(날짜):
    try:
        sys.path.insert(0, _HERE)
        from krx_calendar import 직전거래일
        d0 = 직전거래일(dt.date.fromisoformat(날짜[:10]))
        p = os.path.join(_DATA, "index-daily", f"{d0:%Y%m%d}.json")
        z = (json.load(io.open(p, encoding="utf-8-sig")).get("지수") or {}).get("코스피") or {}
        종, 률 = z.get("종가"), z.get("등락률")
        if 종 is None or 률 is None:
            return None
        return {"지수": f"{종:,.2f}", "전일대비": f"{종 - 종 / (1 + 률 / 100):+.2f}", "등락률": f"{률:+.2f}",
                "방향": "상승" if 률 > 0 else ("하락" if 률 < 0 else "보합"),
                "기준": f"{d0:%m/%d} 종가 (KRX 공식)"}
    except Exception:  # noqa: BLE001
        return None


def 시장정리(mk, 날짜):
    r"""mk = fetch_market summary · 날짜 = 'YYYY-MM-DD'(브리핑 날). 바뀐 사본을 돌려준다"""
    if not mk:
        return mk
    mk = dict(mk)
    k = mk.get("코스피") or {}
    if k and not k.get("기준") and _영(k.get("등락률")):
        공 = _전거래일코스피(날짜)
        if 공:
            mk["코스피"] = 공
    for 칸 in ("업종랭킹", "테마랭킹"):
        lst = mk.get(칸) or []
        if lst and all(_영(x.get("등락률")) for x in lst):
            mk[칸] = []
    lst = mk.get("외국인순매수상위") or []
    if lst and all(_영(x.get("등락률")) for x in lst):
        mk["외국인순매수상위"] = [dict(x, 등락률=None) for x in lst]
    return mk
