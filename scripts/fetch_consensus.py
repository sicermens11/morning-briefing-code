#!/usr/bin/env python3
r"""
fetch_consensus.py — 증권가 컨센서스를 **매일 쌓아 변화를 만든다**

⚠️⚠️ **왜 필요한가** (2026-08-28 신설).
   점수표에는 이미 **투자의견 강등 −1 · 목표주가 하향 −2**가 있다(2026-08-27 신설).
   그런데 **판정 근거가 없다.** 규칙은 `fetch_stock.py`의 `리서치` 제목·미리보기에서
   "매수→중립"을 읽으라고 하는데, 그 필드에는 제목·증권사·작성일·미리보기뿐이고
   **투자의견이 없다.** 규칙만 있고 발동할 재료가 없는 상태였다.

   네이버는 **현재값만** 준다(`recommMean` 4.00 같은 의견점수, `priceTargetMean` 목표주가).
   이력 API가 없다. 그래서 **우리가 매일 저장한다.** 어제 4.00이 오늘 3.80이면
   그 차이가 곧 강등이다. **이력이 없으면 만들면 된다.**

⚠️ **그날 후보만 보면 안 된다.** 오늘 후보가 내일도 후보일 확률은 낮아서, 그러면
   같은 종목을 두 번 볼 일이 거의 없고 차분이 영영 안 생긴다. 그래서 **최근 N일에
   한 번이라도 후보였던 종목 전부**를 매일 다시 본다.

⚠️ **MCP 예산에 안 잡힌다.** 네이버 직접 호출이라 8종목에 0.4초다. 종목 수를 늘려도
   비용이 붙지 않는다 — 그래서 넓게 본다.

⚠️ **커버리지 구멍이 있다.** 증권사가 안 보는 종목(안랩·지니언스)은 값 자체가 없다.
   그런 날은 `없음`으로 남긴다 — **0으로 채우지 않는다.** 0으로 채우면 나중에
   "의견이 0점인 종목"과 "아무도 안 보는 종목"이 섞여 계산이 거짓말이 된다.

쓰는 법:
    python scripts\fetch_consensus.py              # 최근 20일 픽 전부
    python scripts\fetch_consensus.py --days 40
"""
import argparse
import concurrent.futures as cf
import io
import json
import os
import sys
import urllib.request
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(_BASE, "data", "briefing-daily-log.jsonl")
HIST = os.path.join(_BASE, "data", "consensus-history.jsonl")
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}


def _codes(days):
    """최근 `days`일 로그에 한 번이라도 나온 픽 코드 — 이름도 같이 들고 온다."""
    out = {}
    if not os.path.exists(LOG):
        return out
    rows = [json.loads(l) for l in io.open(LOG, encoding="utf-8") if l.strip()]
    rows.sort(key=lambda x: x.get("date", ""))
    for o in rows[-days:]:
        for p in (o.get("picks") or []):
            out[p["code"]] = p.get("name", "")
    return out


def _one(code):
    try:
        r = urllib.request.Request(
            f"https://m.stock.naver.com/api/stock/{code}/integration", headers=UA)
        d = json.loads(urllib.request.urlopen(r, timeout=8).read().decode("utf-8"))
        ci = d.get("consensusInfo") or {}
        if not ci:
            return {"code": code, "커버리지": False}
        return {"code": code, "커버리지": True,
                "의견점수": _f(ci.get("recommMean")),
                "목표주가": _f(ci.get("priceTargetMean")),
                "컨센기준일": ci.get("createDate")}
    except Exception as e:  # noqa: BLE001
        return {"code": code, "error": f"{type(e).__name__}"}


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def load_history():
    """{(날짜, 코드): 행}"""
    h = {}
    if os.path.exists(HIST):
        for l in io.open(HIST, encoding="utf-8"):
            l = l.strip()
            if not l:
                continue
            try:
                o = json.loads(l)
                h[(o.get("date"), o.get("code"))] = o
            except Exception:  # noqa: BLE001
                pass
    return h


def change_for(code, date, hist=None):
    r"""그 종목의 **직전 관측 대비 변화**. 없으면 `None`.

    ⚠️ 직전 관측이 어제가 아닐 수 있다(휴장·수집 실패). 그래서 며칠 전인지도 같이 준다 —
       "열흘 만에 0.2 내렸다"와 "하루 만에 0.2 내렸다"는 무게가 다르다.
    """
    hist = hist if hist is not None else load_history()
    mine = sorted((d, o) for (d, c), o in hist.items()
                  if c == code and o.get("커버리지") and d <= date)
    if len(mine) < 2:
        return None
    (d0, prev), (d1, cur) = mine[-2], mine[-1]
    if d1 != date:
        return None
    out = {"직전관측일": d0, "간격일": (datetime.strptime(d1, "%Y-%m-%d")
                                 - datetime.strptime(d0, "%Y-%m-%d")).days}
    if cur.get("의견점수") is not None and prev.get("의견점수") is not None:
        out["의견점수_변화"] = round(cur["의견점수"] - prev["의견점수"], 3)
    if cur.get("목표주가") and prev.get("목표주가"):
        out["목표주가_변화pct"] = round(
            (cur["목표주가"] / prev["목표주가"] - 1) * 100, 2)
    return out or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=20, help="최근 며칠치 픽을 볼지")
    ap.add_argument("--date", default=None, help="기록할 날짜(기본 오늘)")
    a = ap.parse_args()
    date = a.date or datetime.now().strftime("%Y-%m-%d")

    codes = _codes(a.days)
    if not codes:
        print(json.dumps({"ok": False, "이유": "로그에 픽이 없다"}, ensure_ascii=False))
        return 0

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(_one, codes))

    hist = load_history()
    새로, 갱신 = 0, 0
    with io.open(HIST, "a", encoding="utf-8") as fp:
        for r in rows:
            if (date, r["code"]) in hist:
                갱신 += 1
                continue
            r.update({"date": date, "name": codes.get(r["code"], "")})
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
            새로 += 1

    covered = sum(1 for r in rows if r.get("커버리지"))
    print(json.dumps({"ok": True, "date": date, "종목": len(rows),
                      "커버리지있음": covered, "새로": 새로, "이미있음": 갱신},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
