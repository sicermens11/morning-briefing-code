#!/usr/bin/env python3
r"""
collect_us_symbols.py — **미국 종목 목록을 시점별로 받는다 (생존편향 제거용)** (2026-09-03 신설)

⚠️⚠️⚠️ **왜 이게 먼저인가 — 생존편향 때문이다.**
```
FMP는 종목 목록을 안 준다(402). 그래서 목록을 사람이 만들어야 하는데,
「지금 아는 대형주」로 짜면 **지금까지 살아남은 종목만** 담긴다.
망한 회사·상장폐지된 회사가 빠져 **수익률이 반드시 부풀려진다.**

Alpha Vantage `LISTING_STATUS`가 이걸 푼다 (**무료**):
  state=delisted           상장폐지 종목 **9,456개** (ipoDate·delistingDate 포함)
  date=2015-01-02&state=active   **그 시점**에 상장돼 있던 7,518종목
```

⚠️ **Alpha Vantage 시세는 못 쓴다.** `TIME_SERIES_DAILY&outputsize=full`이
   2024년에 **프리미엄**이 됐다(compact 100일만 무료). 시세는 **FMP**로 받는다.
⚠️ Alpha Vantage 무료 한도는 **하루 25회**다. 목록은 몇 번이면 되니 충분하다.

저장: `data/us-symbols/{YYYYMMDD}.json` (시점별 상장 목록)
      `data/us-symbols/delisted.json`   (상장폐지 전체)

쓰는 법:
    python scripts\collect_us_symbols.py                       # 기본 시점들
    python scripts\collect_us_symbols.py --시점 2018-01-02
"""
import csv
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "us-symbols")
_H = {"User-Agent": "Mozilla/5.0"}
# ⚠️ 우리 한국 시험이 2016-04부터라 그 언저리부터 잡는다. 3년 간격이면 25회 한도에 여유가 있다
기본시점 = ("2010-01-04", "2013-01-02", "2016-01-04", "2019-01-02",
            "2022-01-03", "2025-01-02")


def 받(**kw):
    q = "&".join(f"{a}={b}" for a, b in kw.items())
    key = config.require("ALPHAVANTAGE_API_KEY")
    u = f"https://www.alphavantage.co/query?{q}&apikey={key}"
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H),
                                timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def 표로(t):
    if not t.startswith("symbol"):
        raise RuntimeError(t[:180])
    rows = list(csv.reader(io.StringIO(t)))
    머 = rows[0]
    out = []
    for r in rows[1:]:
        if len(r) < len(머):
            continue
        out.append(dict(zip(머, r)))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    시점들 = list(기본시점)
    if "--시점" in sys.argv:
        시점들 = [sys.argv[sys.argv.index("--시점") + 1]]

    # ── 상장폐지 목록 (한 번만) ──
    p = os.path.join(OUT, "delisted.json")
    if not os.path.exists(p):
        try:
            a = 표로(받(function="LISTING_STATUS", state="delisted"))
            io.open(p, "w", encoding="utf-8").write(json.dumps(
                {"받은날": dt.date.today().strftime("%Y%m%d"),
                 "건수": len(a), "목록": a}, ensure_ascii=False))
            주 = sum(1 for x in a if x.get("assetType") == "Stock")
            print(f"  delisted  **{len(a):,}종목** (주식 {주:,} · ETF {len(a)-주:,})",
                  flush=True)
            time.sleep(1.2)
        except Exception as e:
            print(f"  ⚠️ delisted 실패: {str(e)[:150]}", flush=True)
    else:
        d = json.load(io.open(p, encoding="utf-8-sig"))
        print(f"  delisted  이미 있음 ({d.get('건수'):,}종목)", flush=True)

    # ── 시점별 상장 목록 ──
    for 시점 in 시점들:
        p = os.path.join(OUT, 시점.replace("-", "") + ".json")
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8-sig"))
            print(f"  {시점}  이미 있음 ({d.get('건수'):,}종목)", flush=True)
            continue
        try:
            a = 표로(받(function="LISTING_STATUS", date=시점, state="active"))
        except Exception as e:
            print(f"  ⚠️ {시점} 실패: {str(e)[:150]}", flush=True)
            # ⚠️ 한도(25회/일)에 걸리면 더 두드려도 소용없다
            if "premium" in str(e).lower() or "rate limit" in str(e).lower():
                break
            time.sleep(2)
            continue
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"시점": 시점, "받은날": dt.date.today().strftime("%Y%m%d"),
             "건수": len(a), "목록": a}, ensure_ascii=False))
        주 = sum(1 for x in a if x.get("assetType") == "Stock")
        거래소 = {}
        for x in a:
            거래소[x.get("exchange")] = 거래소.get(x.get("exchange"), 0) + 1
        print(f"  {시점}  **{len(a):,}종목** (주식 {주:,} · ETF {len(a)-주:,}) "
              f"· {dict(sorted(거래소.items(), key=lambda z: -z[1])[:3])}", flush=True)
        time.sleep(1.2)

    print("\n  ⚠️ 시세는 **FMP**로 받는다 (`collect_us.py`).")
    print("     Alpha Vantage는 `outputsize=full`이 프리미엄이라 시세를 못 준다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
