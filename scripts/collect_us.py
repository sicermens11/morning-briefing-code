#!/usr/bin/env python3
r"""
collect_us.py — **미국 주식·ETF 일별 시세를 받는다 (FMP)** (2026-09-03 신설)

⚠️⚠️ **사용자 요청.** *"내가 말한 미장신호는, 미장 직접 투자를 말하는거야.
   미장의 상승 신호를 포착해서 미장 종목을 매수하는거!"*

## FMP 무료 플랜에서 실측한 것 (2026-09-03)
```
✅ 개별 주식 (AAPL·NVDA·MSFT…)   **5,000행 = 20년** · `from`을 주면 다 준다
✅ SPY                          5,000행 = 20년 (ETF 중 **유일하게** 허용)
❌ QQQ·DIA·IWM·SOXX·VOO·XLK·GLD·TLT   전부 **402 프리미엄**
❌ stock-list · etf-list          **402** — 종목 목록을 못 받는다
⚠️ `from`을 안 주면 **5년(1,254행)**만 준다. 반드시 준다
```

⚠️⚠️⚠️ **생존편향 경고 — 이게 이 파일의 가장 중요한 주의사항이다.**
```
FMP가 종목 목록을 안 주므로 **목록을 사람이(또는 모델이) 만들어야 한다.**
그런데 「지금 아는 대형주」로 목록을 짜면 **지금까지 살아남은 종목만** 담긴다.
망한 회사·상장폐지된 회사가 빠져 **수익률이 반드시 부풀려진다.**

⇒ **개별종목은 Alpha Vantage `LISTING_STATUS`로 목록을 받은 뒤에 채운다.**
   `state=delisted`로 상장폐지 종목을, `date=2015-01-01`로 그 시점 목록을 준다(무료).
⇒ 그 전까지는 **SPY(지수 전체)만** 받는다. 지수는 편입·편출이 반영돼 생존편향이 없다.
```

저장: `data/us-daily/{심볼}.json` → `{"심볼":..., "종가": {날짜: 값}, "거래량": {...}}`

쓰는 법:
    python scripts\collect_us.py                    # 기본 목록(SPY)
    python scripts\collect_us.py --심볼 AAPL,MSFT   # 지정
    python scripts\collect_us.py --목록 data\us-symbols.txt
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "us-daily")
LOG = os.path.join(_BASE, "data", "_us.log")
_H = {"User-Agent": "Mozilla/5.0"}
_쉼 = 0.25
# ⚠️ **여기에 개별종목을 함부로 넣지 않는다.** 위 생존편향 경고를 읽을 것.
#    지수 대리(SPY)는 편입·편출이 반영돼 안전하다.
기본목록 = ("SPY",)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 받(심볼, key, 부터="2004-01-01"):
    u = ("https://financialmodelingprep.com/stable/historical-price-eod/light"
         f"?symbol={심볼}&from={부터}"
         f"&to={dt.date.today():%Y-%m-%d}&apikey={key}")
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H),
                                timeout=40) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    if not isinstance(d, list):
        raise RuntimeError(str(d)[:150])
    종, 량 = {}, {}
    for x in d:
        날 = str(x.get("date") or "").replace("-", "")
        p = x.get("price")
        if len(날) == 8 and isinstance(p, (int, float)) and p > 0:
            종[날] = float(p)
            v = x.get("volume")
            if isinstance(v, (int, float)):
                량[날] = float(v)
    return 종, 량


def main():
    key = config.require("FMP_API_KEY")
    심볼들 = list(기본목록)
    if "--심볼" in sys.argv:
        심볼들 = [s.strip().upper()
                  for s in sys.argv[sys.argv.index("--심볼") + 1].split(",")
                  if s.strip()]
    elif "--목록" in sys.argv:
        p = sys.argv[sys.argv.index("--목록") + 1]
        심볼들 = [l.strip().upper() for l in io.open(p, encoding="utf-8")
                  if l.strip() and not l.startswith("#")]
    os.makedirs(OUT, exist_ok=True)
    찍기(f"===== 미국 시세 수집 (FMP) · {len(심볼들)}종목 =====")
    if len(심볼들) > 1:
        찍기("  ⚠️⚠️ **생존편향 주의** — 목록이 「지금 살아남은 종목」이면 결과가 부풀려진다.")
        찍기("     Alpha Vantage LISTING_STATUS로 목록을 받은 뒤 쓰는 것이 옳다.")
    ok = 실패 = 0
    for i, s in enumerate(심볼들, 1):
        p = os.path.join(OUT, s + ".json")
        옛 = {}
        if os.path.exists(p):
            try:
                옛 = json.load(io.open(p, encoding="utf-8-sig"))
            except Exception:
                옛 = {}
        try:
            종, 량 = 받(s, key)
        except urllib.error.HTTPError as e:
            실패 += 1
            msg = e.read()[:110].decode("utf-8", errors="replace")
            찍기(f"  ⚠️ {s}: HTTP {e.code} · {msg}")
            # ⚠️ 429면 한도다 — 더 두드리지 않는다
            if e.code == 429:
                찍기("  ⚠️⚠️ 하루 한도에 걸렸다 — 멈춘다. 내일 다시 돌리면 이어받는다")
                break
            time.sleep(0.5)
            continue
        except Exception as e:
            실패 += 1
            찍기(f"  ⚠️ {s}: {type(e).__name__} {str(e)[:90]}")
            time.sleep(0.5)
            continue
        if not 종:
            실패 += 1
            찍기(f"  ⚠️ {s}: 빈 응답")
            continue
        옛종 = (옛.get("종가") or {})
        옛종.update(종)
        옛량 = (옛.get("거래량") or {})
        옛량.update(량)
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"심볼": s, "받은날": dt.date.today().strftime("%Y%m%d"),
             "종가": 옛종, "거래량": 옛량}, ensure_ascii=False))
        k = sorted(옛종)
        ok += 1
        찍기(f"  {s:8} {k[0]} ~ {k[-1]} · {len(옛종):,}일")
        time.sleep(_쉼)
    찍기(f"  끝 · 받음 {ok} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
