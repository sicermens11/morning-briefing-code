#!/usr/bin/env python3
r"""
collect_yahoo.py — **미국 지수·ETF 일별 시세 (Yahoo Finance)** (2026-09-03 신설)

⚠️⚠️ **사용자 요구.** *"QQQ·SOXX 이거 꼭 써야 해. 다른 방법 찾아봐"*
   → 찾았다. **Yahoo Finance가 키 없이 27년 일별을 준다.**

## 왜 여기인가 — 다른 곳이 다 막혔다 (2026-09-03 실측)
```
FMP 무료         SPY만 20년 · QQQ·SOXX·DIA·IWM·GLD·TLT 전부 **402 프리미엄**
Alpha Vantage    TIME_SERIES_DAILY `outputsize=full`이 **프리미엄** (compact 100일만)
국내 상장 미국ETF  ❌ **두 가지 이유로 못 쓴다**
                 ① 시차 — 08:00 브리핑 시점에 오늘 값이 없다 (하루 늦은 값만)
                 ② 환율 — 미국과 방향이 다른 날이 **19.3%** (헤지 상품도 11.6%)
✅ **Yahoo Finance**  키 불필요 · **QQQ 6,791일(1999~)** 확인
```

⚠️ **`range=max`는 월별로 준다.** `period1`/`period2`(유닉스 초)를 줘야 **일별**이 온다.
```
range=max         331일  ← 27년치 **월별**
period1/period2   6,791일 ← 27년치 **일별** ✅
```

## 받는 것
```
지수·ETF   QQQ(나스닥100) · SOXX·SMH(반도체) · SPY(S&P500) · DIA(다우) · IWM(소형주)
           XLK(기술) · GLD(금) · TLT(장기국채) · ^VIX(공포지수)
한국 참고   ^KS11(코스피) · ^KQ11(코스닥)
```
⚠️ **시차가 핵심이다.** 미국 T-1일 밤 종가는 한국 시간 T일 **새벽 06:00**에 확정된다.
   ⇒ 08:00 브리핑이 **이미 안다.** look-ahead가 아니다.

저장: `data/yahoo/{심볼}.json` → `{"심볼":..., "종가": {YYYYMMDD: 값}, "거래량": {...}}`

쓰는 법:
    python scripts\collect_yahoo.py
    python scripts\collect_yahoo.py --심볼 QQQ,SOXX
"""
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_BASE, "data", "yahoo")
LOG = os.path.join(_BASE, "data", "_yahoo.log")
_H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_쉼 = 0.5

# ⚠️⚠️ **2026-09-03 대폭 확장.** 내가 「못 구한다」고 한 것들이 **전부 Yahoo에 있었다.**
#   유가·금 「KRX만 2.6년」 -> **6,500일(26년)** · 미국금리 「KRX만」 -> **7,952일(31년)**
#   환율 「네이버만」 -> 달러인덱스 8,039일 · 해외 지수는 아예 안 봤다
# ⚠️ **시차를 구분해야 한다** (브리핑은 한국 08:00):
#   ✅ 쓸 수 있음  미국(새벽06:00) · 유럽(새벽01:00) · 유가·금(선물, 거의 24시간)
#   ⚠️ 하루 늦음  일본·중국·홍콩·대만 — **한국과 같은 시간대**라 전날 종가만
기본 = (
    ("QQQ", "나스닥100"),
    ("SOXX", "반도체(iShares)"),
    ("SMH", "반도체(VanEck)"),
    ("SPY", "S&P500"),
    ("DIA", "다우"),
    ("IWM", "미국 소형주"),
    ("XLK", "미국 기술"),
    ("GLD", "금"),
    ("TLT", "미국 장기국채"),
    ("^VIX", "공포지수"),
    ("^KS11", "코스피(참고)"),
    ("^KQ11", "코스닥(참고)"),
    # ── 원자재 (「2.6년뿐」이라 했던 것들) ──
    ("CL=F", "WTI 유가"), ("BZ=F", "브렌트유"), ("GC=F", "금 선물"),
    ("SI=F", "은"), ("HG=F", "구리"), ("NG=F", "천연가스"),
    # ── 미국 금리 (「KRX만」이라 했던 것) ──
    ("^TNX", "미국10년물"), ("^TYX", "미국30년물"),
    ("^FVX", "미국5년물"), ("^IRX", "미국13주"),
    # ── 환율 ──
    ("KRW=X", "원달러"), ("JPYKRW=X", "엔원"),
    ("DX-Y.NYB", "달러인덱스"), ("EURUSD=X", "유로달러"),
    # ── 해외 지수 ──
    #   ⚠️ 아시아(일본·중국·홍콩·대만)는 **한국과 같은 시간대** — 하루 늦게 써야 한다
    #   ⭐ 대만은 한국과 산업 구조가 가장 비슷하다 (반도체·전자 · TSMC)
    ("^N225", "일본"), ("000001.SS", "중국"), ("^HSI", "홍콩"),
    ("^TWII", "대만⭐"), ("^GDAXI", "독일"), ("^FTSE", "영국"),
)


def 찍기(s):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {s}"
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as fp:
        fp.write(line + "\n")


def 받(심볼, 부터년=1995):
    p1 = int(dt.datetime(부터년, 1, 1).timestamp())
    p2 = int(dt.datetime.now().timestamp())
    u = (f"https://query2.finance.yahoo.com/v8/finance/chart/{심볼}"
         f"?period1={p1}&period2={p2}&interval=1d")
    with urllib.request.urlopen(urllib.request.Request(u, headers=_H),
                                timeout=40) as r:
        d = json.loads(r.read().decode("utf-8", errors="replace"))
    res = (d.get("chart") or {}).get("result") or []
    if not res:
        err = (d.get("chart") or {}).get("error")
        raise RuntimeError(str(err)[:120])
    ts = res[0].get("timestamp") or []
    q = ((res[0].get("indicators") or {}).get("quote") or [{}])[0]
    cl = q.get("close") or []
    vol = q.get("volume") or []
    종, 량 = {}, {}
    for i, t in enumerate(ts):
        c = cl[i] if i < len(cl) else None
        if c is None:
            continue
        # ⚠️ Yahoo는 UTC 초를 준다. 미국 장 마감 시각이라 UTC 날짜가 맞다
        d8 = dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y%m%d")
        종[d8] = float(c)
        v = vol[i] if i < len(vol) else None
        if v is not None:
            량[d8] = float(v)
    # ⚠️⚠️ **가장 최근 일봉이 비어 있는 일이 잦다** (2026-09-04 실측)
    #    Yahoo가 일봉을 확정하기 전에는 close가 None이다.
    #    그런데 meta에는 마감가가 이미 들어 있다.
    #    ⇒ 이걸 안 채우면 **아침 브리핑에서 「어젯밤 미국」을 못 쓴다.**
    #       보조 전략이 통째로 못 돈다 (백테스트에선 과거 자료라 안 보였다)
    #    ⚠️ 장중(REGULAR·PRE)이면 종가가 아니라 현재가라 **쓰지 않는다**
    meta = res[0].get("meta") or {}
    상태 = str(meta.get("marketState") or "").upper()
    끝값 = meta.get("regularMarketPrice")
    끝시 = meta.get("regularMarketTime")
    if 끝값 and 끝시 and 상태 in ("CLOSED", "POST", "POSTPOST", "PREPRE", ""):
        d8 = dt.datetime.fromtimestamp(int(끝시), dt.UTC).strftime("%Y%m%d")
        if d8 not in 종:
            종[d8] = float(끝값)
    return 종, 량


def main():
    심볼들 = 기본
    if "--심볼" in sys.argv:
        골 = [s.strip().upper()
              for s in sys.argv[sys.argv.index("--심볼") + 1].split(",")]
        심볼들 = tuple((s, "") for s in 골)
    os.makedirs(OUT, exist_ok=True)
    찍기(f"===== Yahoo 시세 수집 · {len(심볼들)}종목 =====")
    ok = 실패 = 0
    for 심, 이름 in 심볼들:
        p = os.path.join(OUT, 심.replace("^", "IDX_") + ".json")
        옛 = {}
        if os.path.exists(p):
            try:
                옛 = json.load(io.open(p, encoding="utf-8-sig"))
            except Exception:
                옛 = {}
        try:
            종, 량 = 받(심)
        except urllib.error.HTTPError as e:
            실패 += 1
            찍기(f"  ⚠️ {심}: HTTP {e.code}")
            time.sleep(2)
            continue
        except Exception as e:
            실패 += 1
            찍기(f"  ⚠️ {심}: {type(e).__name__} {str(e)[:80]}")
            time.sleep(2)
            continue
        if not 종:
            실패 += 1
            찍기(f"  ⚠️ {심}: 빈 응답")
            continue
        옛종 = 옛.get("종가") or {}
        옛종.update(종)
        옛량 = 옛.get("거래량") or {}
        옛량.update(량)
        io.open(p, "w", encoding="utf-8").write(json.dumps(
            {"심볼": 심, "이름": 이름 or 옛.get("이름", ""),
             "받은날": dt.date.today().strftime("%Y%m%d"),
             "종가": 옛종, "거래량": 옛량}, ensure_ascii=False))
        k = sorted(옛종)
        ok += 1
        찍기(f"  {심:<8}{이름:<16}{k[0]} ~ {k[-1]} · {len(옛종):,}일")
        time.sleep(_쉼)
    찍기(f"  끝 · 받음 {ok} · 실패 {실패}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
